import pathlib
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]


class FrontendDesignReadinessTests(unittest.TestCase):
    def read(self, path: str) -> str:
        return (REPO_ROOT / path).read_text(encoding="utf-8")

    def test_frontend_contract_is_indexed_and_reachable_from_workflow(self):
        index = self.read("docs/INDEX.md")
        setup = self.read("skills/setup/SKILL.md")
        design = self.read("skills/design-architecture/SKILL.md")

        self.assertIn("reference/frontend-design-contract.md", index)
        self.assertIn("reference/design-md-profile.json", index)
        for text in (setup, design):
            self.assertIn("frontend-design", text)
        self.assertIn("docs/ux/frontend-design.md", design)

    def test_spec_and_plan_preserve_frontend_oracles(self):
        spec = self.read("skills/spec/SKILL.md")
        plan = self.read("skills/prepare-execute/SKILL.md")
        contract = self.read("docs/reference/frontend-design-contract.md")

        for text in (spec, plan, contract):
            self.assertIn("frontend-design", text)
            self.assertIn("DESIGN.md", text)
        self.assertIn("design_context", spec)
        self.assertIn("accessibility", plan.lower())
        self.assertIn("visual", plan.lower())
        self.assertIn(
            "tokens -> primitives -> component states/stories -> screens -> e2e/visual",
            contract,
        )

    def test_visual_lanes_are_tool_conditional_and_locally_installable(self):
        contract = self.read("docs/reference/frontend-design-contract.md")
        skill = self.read("skills/frontend-design/SKILL.md")

        for text in (contract, skill):
            self.assertIn("mock/prototype", text)
            self.assertIn("Storybook", text)
            self.assertIn("Playwright", text)
        self.assertIn("project-local tooling", contract)
        self.assertIn(".ezpowers/tools/frontend-visual-readiness.py", contract)
        self.assertIn("--frontend-root", contract)
        self.assertIn("Playwright availability alone is not enough", contract)
        self.assertIn("BackstopJS", contract)

    def test_design_md_profile_and_offline_tools_are_maintainable(self):
        contract = self.read("docs/reference/frontend-design-contract.md")
        profile = self.read("docs/reference/design-md-profile.json")
        agents = self.read("AGENTS.md")

        self.assertIn("google-alpha-0.4.0-ezpowers-1", profile)
        self.assertIn("9bf8eae67128b6cc55ad9bf86665767deb4c11cd", profile)
        self.assertIn('"orphaned-tokens": "info"', profile)
        self.assertIn('"runtime-upstream-fetch"', profile)
        self.assertIn("design-md.py lint", contract)
        self.assertIn("check-design-md-upstream.py", contract)
        self.assertIn("never installs a package", contract)
        self.assertIn("nearest mapped `DESIGN.md`", agents)

    def test_frontend_skill_has_reference_and_no_codegen_shortcut(self):
        skill = self.read("skills/frontend-design/SKILL.md")

        self.assertIn(".ezpowers/contracts/frontend-design-contract.md", skill)
        self.assertIn("docs/reference/design-md-profile.json", skill)
        self.assertIn("Do not implement product UI code", skill)
        self.assertIn("Propose 2-3 distinct design directions", skill)
        self.assertIn("state matrix", skill)
        self.assertIn("visual", skill.lower())

    def test_frontend_core_has_no_removed_dispatch_or_model_layer(self):
        combined = "\n".join(
            [
                self.read("skills/frontend-design/SKILL.md"),
                self.read("docs/reference/frontend-design-contract.md"),
            ]
        )
        for removed in ("workflow-runner", "model-router", "frontend-experience-reviewer"):
            self.assertNotIn(removed, combined)


if __name__ == "__main__":
    unittest.main()
