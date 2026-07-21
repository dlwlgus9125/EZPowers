import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
VERIFY_STEP = REPO_ROOT / "scripts" / "verify-step.py"


def _clean_env() -> dict:
    """Environment with PYTHONPATH stripped so the repo's scripts/ cannot leak
    run_baseline.py / shared.py onto sys.path during the isolation proof."""
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)
    return env


class VerifyStepParserTests(unittest.TestCase):
    def test_verify_extraction_ignores_task_body_and_dedupes(self):
        with tempfile.TemporaryDirectory(dir=REPO_ROOT) as tmp:
            root = pathlib.Path(tmp)
            phase_dir = root / "phases" / "sample"
            phase_dir.mkdir(parents=True)
            step = phase_dir / "step0.md"
            step.write_text(
                textwrap.dedent(
                    """
                    # Step 0

                    ## Task
                    Historical task text with stale Verify: `exit 9`.
                    Historical Verify-type: e2e

                    ## Acceptance Criteria
                    - [ ] Given: app / When: command runs / Then: command passes / Verify: `python -c "raise SystemExit(0)"`

                    ## Verification
                    Verify: `python -c "raise SystemExit(0)"`
                    Verify-type: cli
                    """
                ).strip(),
                encoding="utf-8",
            )

            proc = subprocess.run(
                [
                    sys.executable,
                    str(VERIFY_STEP),
                    "--step-md",
                    str(step),
                    "--project-root",
                    str(root),
                    "--phase",
                    "sample",
                    "--timeout",
                    "5",
                ],
                cwd=REPO_ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
            result = json.loads(proc.stdout)
            self.assertEqual(result["verify_type"], "cli")
            self.assertEqual(result["verify_commands"], ['python -c "raise SystemExit(0)"'])
            self.assertEqual(result["verify_commands_count"], 1)


class VerifyStepSelfContainedTests(unittest.TestCase):
    def test_imports_without_sibling_scripts(self):
        """verify-step.py is installed into target projects by harness-kit,
        which does not ship run_baseline.py / shared.py. Copying it alone into a
        directory where those siblings do not exist and running --help proves the
        module imports using only the standard library."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = pathlib.Path(tmp)
            isolated = tmp_dir / "verify-step.py"
            shutil.copy(VERIFY_STEP, isolated)

            # The siblings the old import depended on must be absent here.
            self.assertFalse((tmp_dir / "run_baseline.py").exists())
            self.assertFalse((tmp_dir / "shared.py").exists())

            proc = subprocess.run(
                [sys.executable, str(isolated), "--help"],
                cwd=tmp,
                text=True,
                capture_output=True,
                env=_clean_env(),
                check=False,
            )

            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertNotIn("ImportError", proc.stderr)
            self.assertNotIn("ModuleNotFoundError", proc.stderr)


class VerifyStepPlaceholderTests(unittest.TestCase):
    def test_placeholder_verify_command_fails(self):
        """A no-op / placeholder per-task Verify command must FAIL, not pass."""
        with tempfile.TemporaryDirectory(dir=REPO_ROOT) as tmp:
            root = pathlib.Path(tmp)
            phase_dir = root / "phases" / "sample"
            phase_dir.mkdir(parents=True)
            step = phase_dir / "step0.md"
            step.write_text(
                textwrap.dedent(
                    """
                    # Step 0

                    ## Verification
                    Verify: `echo ok`
                    Verify-type: cli
                    """
                ).strip(),
                encoding="utf-8",
            )

            proc = subprocess.run(
                [
                    sys.executable,
                    str(VERIFY_STEP),
                    "--step-md",
                    str(step),
                    "--project-root",
                    str(root),
                    "--phase",
                    "sample",
                    "--timeout",
                    "5",
                ],
                cwd=REPO_ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(proc.returncode, 1, proc.stderr + proc.stdout)
            result = json.loads(proc.stdout)
            self.assertFalse(result["pass"])
            command_checks = result["dimensions"]["command"]["checks"]
            self.assertTrue(
                any(
                    c["name"] == "placeholder_verify" and c["pass"] is False
                    for c in command_checks
                ),
                command_checks,
            )


if __name__ == "__main__":
    unittest.main()
