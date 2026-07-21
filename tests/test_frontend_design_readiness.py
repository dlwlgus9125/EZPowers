import pathlib
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]


def workflow_doc(skill_name: str, command_name: str) -> str:
    for candidate in (f"skills/{skill_name}/SKILL.md", f"commands/{command_name}.md"):
        if (REPO_ROOT / candidate).exists():
            return candidate
    return f"commands/{command_name}.md"


class FrontendDesignReadinessTests(unittest.TestCase):
    def read(self, path: str) -> str:
        return (REPO_ROOT / path).read_text(encoding="utf-8")

    def test_frontend_design_contract_is_indexed_and_routed(self):
        index = self.read("docs/INDEX.md")
        protocol = self.read("docs/reference/protocol.md")
        dispatch = self.read("docs/reference/dispatch-protocol.md")

        self.assertIn("reference/frontend-design-contract.md", index)
        self.assertIn("docs/reference/frontend-design-contract.md", protocol)
        self.assertIn("frontend-experience-reviewer", dispatch)
        self.assertIn("frontend-experience-reviewer | `frontend-visual`", dispatch)

    def test_setup_and_design_architecture_require_design_artifact(self):
        setup = self.read("docs/reference/setup-contract.md")
        design = self.read("docs/reference/design-architecture-contract.md")
        setup_command = self.read(workflow_doc("setup", "setup"))
        design_command = self.read(workflow_doc("design-architecture", "design_architecture"))

        for text in (setup, design, setup_command, design_command):
            self.assertIn("frontend-design", text)
            self.assertIn("docs/ux/frontend-design.md", text)

        self.assertIn('"design_readiness_required": true', setup)
        self.assertIn("2-3 design directions", design)

    def test_spec_plan_and_d9_carry_frontend_readiness(self):
        app_delivery = self.read("docs/reference/app-delivery-contract.md")
        spec = self.read("docs/reference/spec-contract.md")
        plan = self.read("docs/reference/plan-contract.md")
        audit = self.read("docs/reference/pipeline-audit-contract.md")

        for text in (app_delivery, spec, plan, audit):
            self.assertIn("frontend design readiness", text.lower())
            self.assertIn("docs/ux/frontend-design.md", text)

        self.assertIn("tokens -> primitives -> component states/stories -> screens -> e2e/visual", plan)
        self.assertIn("Missing Frontend Design Readiness", audit)
        self.assertIn("screen implementation before tokens", app_delivery)

    def test_frontend_v2_visual_lanes_are_tool_conditional(self):
        contract = self.read("docs/reference/frontend-design-contract.md")
        skill_ref = self.read("skills/frontend-design/references/frontend-design-readiness.md")
        reviewer = self.read("agents/frontend-experience-reviewer.md")
        plan = self.read("docs/reference/plan-contract.md")
        audit = self.read("docs/reference/pipeline-audit-contract.md")

        for text in (contract, skill_ref, reviewer, plan, audit):
            self.assertIn("mock/prototype", text)
            self.assertIn("Storybook", text)
            self.assertIn("Playwright", text)
            self.assertIn("screenshot/visual", text)

        self.assertIn("project-local tooling", contract)
        self.assertIn("global PATH", reviewer)
        self.assertIn("scripts/frontend-visual-readiness.py", contract)
        self.assertIn("--frontend-root", contract)
        self.assertIn("schema_version", contract)
        self.assertIn("Playwright availability alone is not enough", contract)
        self.assertIn("BackstopJS", contract)
        self.assertIn("token/component mapping", audit)
        self.assertIn("--mode check", audit)

    def test_frontend_reviewer_routing_and_verdict_contract_are_fixed(self):
        dispatch = self.read("docs/reference/dispatch-protocol.md")
        routing = self.read("docs/reference/model-routing-contract.md")
        router = self.read("scripts/model-router.py")

        self.assertIn("frontend-experience-reviewer | `frontend-visual`", dispatch)
        self.assertIn("frontend-experience-reviewer` uses `frontend-visual`", routing)
        self.assertIn('"frontend-visual"', router)
        self.assertIn("file does not define a narrower verdict set", dispatch)
        self.assertIn("frontend-experience-reviewer", dispatch)

    def test_frontend_skill_has_reference_and_no_codegen_shortcut(self):
        skill = self.read("skills/frontend-design/SKILL.md")
        reference = self.read("skills/frontend-design/references/frontend-design-readiness.md")

        self.assertIn("references/frontend-design-readiness.md", skill)
        self.assertIn("Do not implement product UI code", skill)
        self.assertIn("Propose 2-3 distinct design directions", skill)
        self.assertIn("UX state matrix", reference)
        self.assertIn("Visual QA strategy", reference)
        self.assertIn("mock/prototype artifacts", skill)


if __name__ == "__main__":
    unittest.main()
