import json
import pathlib
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]


class V5WorkflowSurfaceTests(unittest.TestCase):
    def test_live_skill_surface_is_small_and_host_metadata_is_complete(self) -> None:
        expected = {
            "setup",
            "deep-interview",
            "design-architecture",
            "spec",
            "prepare-execute",
            "execute",
            "frontend-design",
            "improve-codebase-architecture",
            "hud",
        }
        actual = {path.name for path in (REPO_ROOT / "skills").iterdir() if path.is_dir()}
        self.assertEqual(actual, expected)
        for name in expected:
            self.assertTrue((REPO_ROOT / "skills" / name / "SKILL.md").is_file())
            self.assertTrue((REPO_ROOT / "skills" / name / "agents" / "openai.yaml").is_file())

    def test_deep_interview_contract_declares_clarify_and_stress_test(self) -> None:
        skill = (REPO_ROOT / "skills" / "deep-interview" / "SKILL.md").read_text(encoding="utf-8")
        for phrase in ("clarify", "stress-test", "grill me", "CONTEXT.md", "one question"):
            self.assertIn(phrase, skill)
        spec = (REPO_ROOT / "skills" / "spec" / "SKILL.md").read_text(encoding="utf-8")
        self.assertNotIn("grill-with-docs", spec)
        self.assertIn("settled decisions", spec)

    def test_removed_execution_and_reviewer_layers_are_absent(self) -> None:
        self.assertFalse((REPO_ROOT / "agents").exists())
        self.assertFalse((REPO_ROOT / "harness-kit").exists())
        self.assertFalse((REPO_ROOT / "phases").exists())
        self.assertFalse((REPO_ROOT / ".harness").exists())
        self.assertTrue((REPO_ROOT / "project-kit" / "v5.0.0" / "manifest.json").is_file())
        self.assertTrue((REPO_ROOT / ".ezpowers" / "config.json").is_file())
        self.assertTrue((REPO_ROOT / ".ezpowers" / "state.json").is_file())

    def test_execute_explicitly_activates_while_plan_authoring_is_read_only(self) -> None:
        execute = (REPO_ROOT / "skills" / "execute" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        prepare = (
            REPO_ROOT / "skills" / "prepare-execute" / "SKILL.md"
        ).read_text(encoding="utf-8")
        self.assertIn("validate --plan <plan-path> --activate", execute)
        self.assertIn("validate --plan <plan-path> --json", prepare)
        self.assertNotIn("--activate", prepare)

    def test_plugin_manifests_expose_the_same_version_and_current_workflow(self) -> None:
        claude = json.loads((REPO_ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
        marketplace = json.loads((REPO_ROOT / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8"))
        codex = json.loads((REPO_ROOT / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8"))
        self.assertEqual(claude["version"], "5.0.0")
        self.assertEqual(marketplace["plugins"][0]["version"], "5.0.0")
        self.assertTrue(codex["version"].startswith("5.0.0+codex."))
        combined = json.dumps([claude, marketplace, codex])
        self.assertIn("deep-interview", combined)
        self.assertIn("execute", combined)
        self.assertNotIn("choice-execute", combined)


if __name__ == "__main__":
    unittest.main()
