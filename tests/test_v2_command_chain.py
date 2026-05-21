import json
import pathlib
import subprocess
import sys
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]


class V2CommandChainTests(unittest.TestCase):
    def test_public_commands_are_v2_chain(self):
        expected = {
            "setup.md",
            "design_architecture.md",
            "spec.md",
            "prepare_execute.md",
            "choice_execute.md",
            "maintain.md",
            "deploy.md",
            "reset_setup.md",
            "eval.md",
            "feedback.md",
            "review.md",
            "set-rules.md",
            "sync-docs.md",
        }
        actual = {path.name for path in (REPO_ROOT / "commands").glob("*.md")}
        self.assertEqual(expected, actual)

    def test_removed_commands_are_internal_or_absent(self):
        for name in [
            "brainstorm.md",
            "plan.md",
            "choiceexecutor.md",
            "executeharness.md",
            "pipeline-audit.md",
        ]:
            self.assertFalse((REPO_ROOT / "commands" / name).exists(), name)

        self.assertTrue((REPO_ROOT / "docs/reference/pipeline-audit-contract.md").exists())
        self.assertTrue((REPO_ROOT / "docs/reference/strict-execution-adapter.md").exists())

    def test_harness_kit_manifest_is_no_synthesis_and_verified(self):
        manifest = json.loads(
            (REPO_ROOT / "harness-kit/v2.0.0/manifest.json").read_text(encoding="utf-8")
        )
        self.assertTrue(manifest["no_synthesis"])
        self.assertEqual(manifest["install_root"], ".harness/ezpowers")
        self.assertNotIn("brainstorm", manifest["public_commands"])
        self.assertIn("design_architecture", manifest["public_commands"])
        self.assertTrue(manifest["ui_verification"]["adapter_fallback_task_required"])

        result = subprocess.run(
            [sys.executable, "scripts/verify-harness-kit.py"],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            timeout=10,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_setup_and_prepare_execute_preserve_ui_adapter_contract(self):
        setup = (REPO_ROOT / "commands/setup.md").read_text(encoding="utf-8")
        prepare = (REPO_ROOT / "commands/prepare_execute.md").read_text(encoding="utf-8")
        ui_contract = (
            REPO_ROOT / "docs/reference/ui-verification-adapter-contract.md"
        ).read_text(encoding="utf-8")

        self.assertIn("Never generate, paraphrase, or merge `SKILL.md` bodies", setup)
        self.assertIn("hash ledger", setup)
        self.assertIn("insert a prerequisite", prepare)
        self.assertIn("Capability Matrix", ui_contract)
        self.assertIn("Equivalent means the replacement verifies the same observable claim", ui_contract)


if __name__ == "__main__":
    unittest.main()
