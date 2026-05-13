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
        with tempfile.TemporaryDirectory() as tmp:
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

    def test_skill_live_smoke_is_skipped_by_default(self):
        case = {
            "case_id": "skill.systematic-debugging.quick-fix",
            "skill": "systematic-debugging",
            "prompt": "A failing test needs investigation.",
            "expected_first_action": "Start with a feedback loop.",
            "invariants": ["Do not run live smoke unless requested."],
            "live": {"command": "python -c \"raise SystemExit(99)\""},
        }

        result = run_skill_evals.run_case(
            REPO_ROOT / "evals" / "skills" / "systematic-debugging-quick-fix.yaml",
            case,
            live=False,
            live_provider="claude",
        )

        self.assertTrue(result["pass"])
        self.assertIsNone(result["live_pass"])
        self.assertIn("pass --live", result["live_detail"])


if __name__ == "__main__":
    unittest.main()
