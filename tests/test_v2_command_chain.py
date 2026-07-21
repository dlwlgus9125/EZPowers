import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]

# (legacy command name, migrated skill directory name)
WORKFLOW_DOCS = [
    ("setup", "setup"),
    ("design_architecture", "design-architecture"),
    ("spec", "spec"),
    ("prepare_execute", "prepare-execute"),
    ("choice_execute", "choice-execute"),
    ("maintain", "maintain"),
    ("deploy", "deploy"),
    ("reset_setup", "reset-setup"),
    ("review", "review"),
    ("set-rules", "set-rules"),
    ("sync-docs", "sync-docs"),
]


def workflow_doc(command_name: str, skill_name: str) -> pathlib.Path:
    for candidate in (
        REPO_ROOT / "skills" / skill_name / "SKILL.md",
        REPO_ROOT / "commands" / f"{command_name}.md",
    ):
        if candidate.exists():
            return candidate
    return REPO_ROOT / "commands" / f"{command_name}.md"


class V2CommandChainTests(unittest.TestCase):
    def test_public_commands_are_v2_chain(self):
        missing = [
            old for old, new in WORKFLOW_DOCS
            if not workflow_doc(old, new).exists()
        ]
        self.assertEqual(missing, [])

        commands_dir = REPO_ROOT / "commands"
        if commands_dir.is_dir():
            expected = {f"{old}.md" for old, _ in WORKFLOW_DOCS}
            actual = {path.name for path in commands_dir.glob("*.md")}
            self.assertLessEqual(actual, expected)

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
        targets = {item["target"] for item in manifest["source_files"]}
        self.assertIn("scripts/lightpath-gate.ps1", targets)
        self.assertIn("scripts/harness-resume-proof.ps1", targets)
        self.assertIn("scripts/verify-step.py", targets)

        result = subprocess.run(
            [sys.executable, "scripts/verify-harness-kit.py"],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            timeout=10,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_harness_kit_manifest_installs_gate_helpers(self):
        manifest = json.loads(
            (REPO_ROOT / "harness-kit/v2.0.0/manifest.json").read_text(encoding="utf-8")
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            target_root = pathlib.Path(temp_dir)
            for item in manifest["source_files"]:
                source = REPO_ROOT / item["source"]
                target = target_root / item["target"]
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, target)

            self.assertTrue((target_root / "scripts/lightpath-gate.ps1").exists())
            self.assertTrue((target_root / "scripts/harness-resume-proof.ps1").exists())
            self.assertTrue((target_root / "scripts/verify-step.py").exists())

    def test_setup_and_prepare_execute_preserve_ui_adapter_contract(self):
        setup = workflow_doc("setup", "setup").read_text(encoding="utf-8")
        prepare = workflow_doc("prepare_execute", "prepare-execute").read_text(encoding="utf-8")
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
