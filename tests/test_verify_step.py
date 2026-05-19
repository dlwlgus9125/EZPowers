import json
import pathlib
import subprocess
import sys
import tempfile
import textwrap
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]


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
                    str(REPO_ROOT / "scripts" / "verify-step.py"),
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


if __name__ == "__main__":
    unittest.main()
