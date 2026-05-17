import json
import pathlib
import subprocess
import sys
import tempfile
import textwrap
import time
import unittest
from unittest import mock


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPTS_DIR = REPO_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import run_baseline  # noqa: E402
import run_skill_evals  # noqa: E402
import validate  # noqa: E402


class EvalRunnerSafetyTests(unittest.TestCase):
    def test_run_baseline_case_timeout_records_command(self):
        with tempfile.TemporaryDirectory(dir=REPO_ROOT) as tmp:
            tmp_path = pathlib.Path(tmp)
            case_path = tmp_path / "slow-case.yaml"
            progress_path = tmp_path / "progress.json"
            case_path.write_text(
                textwrap.dedent(
                    """
                    case_id: safety.slow_command.001
                    split: optimization
                    stratum:
                      command: safety
                    graders:
                      - type: deterministic_tests
                        commands:
                          - "python -c \\"import time; time.sleep(5)\\""
                    """
                ).strip(),
                encoding="utf-8",
            )

            start = time.perf_counter()
            result = run_baseline.run_case(
                case_path,
                "safety-test",
                command_timeout_seconds=10,
                case_timeout_seconds=1,
                progress_file=progress_path,
            )
            elapsed = time.perf_counter() - start

            self.assertLess(elapsed, 3)
            self.assertFalse(result["pass"])
            details = result["graders"][0]["details"]
            self.assertEqual(details[0]["status"], "timeout")
            self.assertIn("time.sleep(5)", details[0]["command"])

            progress = json.loads(progress_path.read_text(encoding="utf-8"))
            self.assertEqual(progress["case_id"], "safety.slow_command.001")
            self.assertIn(progress["phase"], {"grader_command_start", "case_done"})

    def test_validate_skill_eval_subprocess_timeout_is_reported(self):
        def fake_run(cmd, **kwargs):
            raise subprocess.TimeoutExpired(cmd=cmd, timeout=kwargs.get("timeout"))

        with mock.patch.object(validate.rb, "run_command_with_timeout", side_effect=fake_run):
            passed, detail = validate.check_skill_evals(False, timeout_seconds=1)

        self.assertFalse(passed)
        self.assertIn("timed out after 1s", detail)
        self.assertIn("scripts/run_skill_evals.py", detail)

    def test_python_inline_grader_bypasses_bash_backtick_expansion(self):
        command = "python -c \"assert '`cli`' == '`cli`'\""

        with mock.patch.object(run_baseline, "find_bash", return_value="bash"), \
             mock.patch.object(run_baseline, "run_command_with_timeout") as fake_run:
            fake_run.return_value = subprocess.CompletedProcess([], 0, "", "")

            run_baseline.run_shell_command_with_timeout(
                command,
                timeout=1,
                cwd=REPO_ROOT,
            )

        args = fake_run.call_args.args[0]
        self.assertEqual(args, ["python", "-c", "assert '`cli`' == '`cli`'"])

    def test_python_inline_with_shell_control_still_uses_bash(self):
        command = "python -c \"print(1)\" && echo ok"

        with mock.patch.object(run_baseline, "find_bash", return_value="bash"), \
             mock.patch.object(run_baseline, "run_command_with_timeout") as fake_run:
            fake_run.return_value = subprocess.CompletedProcess([], 0, "", "")

            run_baseline.run_shell_command_with_timeout(
                command,
                timeout=1,
                cwd=REPO_ROOT,
            )

        args = fake_run.call_args.args[0]
        self.assertEqual(args, ["bash", "-c", command])

    def test_skill_live_smoke_is_skipped_by_default(self):
        case = {
            "case_id": "skill.diagnose.quick-fix",
            "skill": "diagnose",
            "prompt": "A failing test needs investigation.",
            "expected_first_action": "Start with a feedback loop.",
            "invariants": ["Do not run live smoke unless requested."],
            "live": {"command": "python -c \"raise SystemExit(99)\""},
        }

        result = run_skill_evals.run_case(
            REPO_ROOT / "evals" / "skills" / "diagnose-quick-fix.yaml",
            case,
            live=False,
            live_provider="claude",
        )

        self.assertTrue(result["pass"])
        self.assertIsNone(result["live_pass"])
        self.assertIn("pass --live", result["live_detail"])

    def test_case_schema_accepts_digits_and_public_command_names(self):
        case = {
            "case_id": "optimization.pipeline_audit_v2.001",
            "split": "optimization",
            "stratum": {
                "command": "pipeline-audit",
                "difficulty": "single_step",
                "pattern": "contract",
                "model_family": "agnostic",
                "language": "en",
                "verify_type": "pure",
            },
            "input": {"user_message": "Check public command coverage."},
            "graders": [{"type": "deterministic_tests", "commands": ["echo ok"]}],
            "tracked_metrics": {"transcript": []},
        }

        errors = run_baseline.validate_case_schema(
            REPO_ROOT / "evals" / "optimization" / "pipeline-audit-v2.yaml",
            case,
        )

        self.assertEqual(errors, [])

    def test_baseline_gate_blocks_golden_failures(self):
        with tempfile.TemporaryDirectory(dir=REPO_ROOT) as tmp:
            tmp_path = pathlib.Path(tmp)
            golden_dir = tmp_path / "golden"
            golden_dir.mkdir()
            (golden_dir / "fail.yaml").write_text(
                textwrap.dedent(
                    """
                    case_id: golden.fail_case.001
                    split: golden
                    stratum:
                      command: plan
                      difficulty: single_step
                      pattern: contract
                      model_family: agnostic
                      language: en
                    input:
                      user_message: must fail
                    graders:
                      - type: deterministic_tests
                        commands:
                          - "exit 1"
                    tracked_metrics:
                      transcript: []
                    """
                ).strip(),
                encoding="utf-8",
            )
            results = [{
                "case_id": "golden.fail_case.001",
                "split": "golden",
                "pass": False,
            }]

            with self.assertRaises(SystemExit):
                run_baseline.enforce_golden_baseline_gate(
                    results,
                    evals_root=tmp_path,
                    model="test",
                    command_timeout_seconds=1,
                    case_timeout_seconds=1,
                    progress_file=tmp_path / "progress.json",
                )

    def test_eval_sync_detects_baseline_case_mismatch(self):
        with tempfile.TemporaryDirectory(dir=REPO_ROOT) as tmp:
            root = pathlib.Path(tmp)
            evals = root / "evals"
            golden = evals / "golden"
            baseline_dir = evals / "results" / "baselines"
            plugin_dir = root / ".codex-plugin"
            golden.mkdir(parents=True)
            baseline_dir.mkdir(parents=True)
            plugin_dir.mkdir()

            (golden / "case.yaml").write_text(
                textwrap.dedent(
                    """
                    case_id: golden.synced_case.001
                    split: golden
                    stratum:
                      command: plan
                      difficulty: single_step
                      pattern: contract
                      model_family: agnostic
                      language: en
                    input:
                      user_message: check sync
                    graders:
                      - type: deterministic_tests
                        commands:
                          - "echo ok"
                    tracked_metrics:
                      transcript: []
                    """
                ).strip(),
                encoding="utf-8",
            )
            (evals / "INDEX.md").write_text(
                "\n".join([
                    "- Optimization: 0 cases",
                    "- Holdout: 0 cases",
                    "- Golden: 1 cases",
                    "- Honeypot: 0 cases",
                    "- Skill: 0 cases",
                ]),
                encoding="utf-8",
            )
            (baseline_dir / "1.0.0.json").write_text(
                json.dumps({"scores": {"golden": {}}}),
                encoding="utf-8",
            )
            (plugin_dir / "plugin.json").write_text(
                json.dumps({
                    "metadata": {
                        "eval_baseline_path": "evals/results/baselines/1.0.0.json"
                    }
                }),
                encoding="utf-8",
            )

            with mock.patch.object(validate, "REPO_ROOT", root), \
                 mock.patch.object(validate, "EVALS_ROOT", evals), \
                 mock.patch.object(validate, "BASELINES_DIR", baseline_dir):
                passed, detail = validate.check_eval_sync()

            self.assertFalse(passed)
            self.assertIn("case set mismatch", detail)

    def test_skill_schema_requires_static_behavior_anchor(self):
        case = {
            "case_id": "skill.diagnose.no-anchor",
            "skill": "diagnose",
            "prompt": "A test fails.",
            "expected_first_action": "Start with evidence.",
            "invariants": ["No guessing."],
            "static": {"max_words": 520},
        }

        errors = run_skill_evals.validate_case_schema(
            REPO_ROOT / "evals" / "skills" / "diagnose-no-anchor.yaml",
            case,
        )

        self.assertTrue(any("static.must_contain" in error for error in errors))

    def test_eval_command_is_not_behavior_prompt_target(self):
        changed = ["commands/eval.md", "evals/INDEX.md"]

        self.assertEqual(validate.behavior_prompt_targets(changed), [])
        self.assertEqual(validate.behavior_prompt_targets(["commands/plan.md"]), ["commands/plan.md"])

        passed, detail = validate.check_diff_lines(False, changed)

        self.assertTrue(passed)
        self.assertIn("no behavior command/agent files changed", detail)


if __name__ == "__main__":
    unittest.main()
