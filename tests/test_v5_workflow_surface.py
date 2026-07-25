import json
import pathlib
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]


class V5WorkflowSurfaceTests(unittest.TestCase):
    def test_live_skill_surface_is_small_and_host_metadata_is_complete(self) -> None:
        expected = {
            "codebase-design",
            "setup",
            "deep-interview",
            "diagnose",
            "design-architecture",
            "spec",
            "prepare-execute",
            "execute",
            "frontend-design",
            "hud",
            "wiki",
            "harness-chain",
            "improve-codebase-architecture",
        }
        actual = {path.name for path in (REPO_ROOT / "skills").iterdir() if path.is_dir()}
        self.assertEqual(actual, expected)
        for name in expected:
            self.assertTrue((REPO_ROOT / "skills" / name / "SKILL.md").is_file())
            self.assertTrue((REPO_ROOT / "skills" / name / "agents" / "openai.yaml").is_file())
            self.assertEqual(
                name != "hud",
                (
                    REPO_ROOT
                    / "skills"
                    / name
                    / "agents"
                    / "project-openai.yaml"
                ).is_file(),
            )

    def test_deep_interview_contract_finds_consequential_blind_spots_without_bloat(self) -> None:
        skill = (REPO_ROOT / "skills" / "deep-interview" / "SKILL.md").read_text(encoding="utf-8")
        normalized_skill = " ".join(skill.split())
        for phrase in (
            "current conversation",
            "decision-ready request",
            "stated ambiguity",
            "Explicit-gap pass",
            "Blind-spot pass",
            "Before every question and before stopping",
            "Try to falsify",
            "alternative frames",
            "omitted people, systems, or dependencies",
            "failure, misuse, or compatibility",
            "hard-to-reverse consequences",
            "reasoning lenses, not a questionnaire",
            "bare possibility",
            "internal blind-spot pass is mandatory",
            "external blind-spot question is not",
            "Rank explicit gaps and eligible blind spots together",
            "exactly one question",
            "recommended answer or alternative",
            "numerical ambiguity or risk score",
            "Do not expose the candidate list",
            "Clarified request",
            "explicit confirmation",
            "native structured question surface",
            "plain-text question",
            "Do not create or update",
            "Confirm and continue planning",
            "do not add a second continuation question",
            "source of truth for clarified user intent",
            "Immediately resume the host's native planning process",
            "Do not repeat settled product questions",
            "native final plan",
            "Plan Mode is no longer active",
        ):
            self.assertIn(phrase, normalized_skill)
        self.assertLessEqual(
            len(skill.split()),
            1000,
            "deep-interview should strengthen reasoning by restructuring, not prompt bloat",
        )
        for phrase in (
            "stress-test mode",
            "docs/interviews",
            "references/context-format.md",
            "## Stress-test",
            "Write the decision brief",
        ):
            self.assertNotIn(phrase, normalized_skill)
        self.assertFalse(
            (REPO_ROOT / "skills" / "deep-interview" / "references" / "context-format.md").exists()
        )

        spec = (REPO_ROOT / "skills" / "spec" / "SKILL.md").read_text(encoding="utf-8")
        self.assertNotIn("docs/interviews", spec)
        self.assertIn("current conversation", spec)
        self.assertIn("explicit `deep-interview` invocation", spec)
        self.assertIn("settled decisions", spec)

        for metadata_name in ("openai.yaml", "project-openai.yaml"):
            metadata = (
                REPO_ROOT
                / "skills"
                / "deep-interview"
                / "agents"
                / metadata_name
            ).read_text(encoding="utf-8")
            self.assertIn("one question at a time", metadata)
            self.assertIn("consequential blind spots", metadata)
            self.assertIn("continue planning", metadata)
            self.assertIn("Plan Mode", metadata)
            self.assertNotIn("stress-test", metadata)

        manifest = json.loads(
            (REPO_ROOT / "project-kit" / "v5.3.0" / "manifest.json").read_text(
                encoding="utf-8"
            )
        )
        deep_interview = next(
            entry for entry in manifest["skills"] if entry["name"] == "deep-interview"
        )
        self.assertEqual(
            {entry["path"] for entry in deep_interview["files"]},
            {"SKILL.md", "agents/openai.yaml"},
        )

    def test_removed_execution_and_reviewer_layers_are_absent(self) -> None:
        self.assertFalse((REPO_ROOT / "agents").exists())
        self.assertFalse((REPO_ROOT / "harness-kit").exists())
        self.assertFalse((REPO_ROOT / "phases").exists())
        self.assertFalse((REPO_ROOT / ".harness").exists())
        self.assertTrue((REPO_ROOT / "project-kit" / "v5.3.0" / "manifest.json").is_file())
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

    def test_harness_chain_is_explicit_asymmetric_and_project_installed(
        self,
    ) -> None:
        skill = (
            REPO_ROOT / "skills" / "harness-chain" / "SKILL.md"
        ).read_text(encoding="utf-8")
        metadata = (
            REPO_ROOT
            / "skills"
            / "harness-chain"
            / "agents"
            / "openai.yaml"
        ).read_text(encoding="utf-8")
        contract = (
            REPO_ROOT / "docs" / "reference" / "harness-chain-contract.md"
        ).read_text(encoding="utf-8")
        manifest = json.loads(
            (
                REPO_ROOT
                / "project-kit"
                / "v5.3.0"
                / "manifest.json"
            ).read_text(encoding="utf-8")
        )

        self.assertIn("disable-model-invocation: true", skill)
        self.assertIn("allow_implicit_invocation: false", metadata)
        self.assertIn("one native Codex goal", contract)
        self.assertIn("sole continuation loop", contract)
        self.assertIn("NEEDS_REAPPROVAL", contract)
        self.assertIn("bound independent", contract)
        self.assertEqual(12, len(manifest["skills"]))
        self.assertEqual(10, len(manifest["contracts"]))
        self.assertEqual(2, len(manifest["tools"]))
        self.assertIn(
            "harness-chain",
            {entry["name"] for entry in manifest["skills"]},
        )
        self.assertIn(
            ".ezpowers/contracts/harness-chain-contract.md",
            {entry["target"] for entry in manifest["contracts"]},
        )

    def test_specialized_engineering_skills_preserve_authority_and_safety(self) -> None:
        diagnose = (
            REPO_ROOT / "skills" / "diagnose" / "SKILL.md"
        ).read_text(encoding="utf-8")
        design = (
            REPO_ROOT / "skills" / "codebase-design" / "SKILL.md"
        ).read_text(encoding="utf-8")
        improve = (
            REPO_ROOT / "skills" / "improve-codebase-architecture" / "SKILL.md"
        ).read_text(encoding="utf-8")
        contract = (
            REPO_ROOT
            / "docs"
            / "reference"
            / "engineering-practices-contract.md"
        ).read_text(encoding="utf-8")
        normalized_diagnose = " ".join(diagnose.split())
        normalized_contract = " ".join(contract.split()).lower()

        for phrase in (
            "Root cause is a milestone, not completion",
            "FIX-COMPLETE",
            "ANALYSIS-ONLY",
            "Do not ask for another authorization",
            "Lack of a good seam does not cancel FIX-COMPLETE",
            "the original Phase 1 loop against the unminimised scenario",
            "Do not stop FIX-COMPLETE at reproduction",
            "End only with the verified fix",
        ):
            self.assertIn(phrase, normalized_diagnose)
        self.assertNotIn(
            "After three failed fix attempts, stop changing code",
            diagnose,
        )
        self.assertIn("at least two materially different", design)
        self.assertIn("deletion test", design)
        self.assertIn("one adapter as a hypothetical seam", design)
        self.assertIn("disable-model-invocation: true", improve)
        self.assertIn("Do not implement the refactor", improve)
        self.assertIn("OS temporary path", improve)

        for name in ("diagnose", "codebase-design"):
            metadata = (
                REPO_ROOT / "skills" / name / "agents" / "openai.yaml"
            ).read_text(encoding="utf-8")
            self.assertIn("allow_implicit_invocation: true", metadata)
        for metadata_name, invocation in (
            ("openai.yaml", "$ezpowers:diagnose"),
            ("project-openai.yaml", "$diagnose"),
        ):
            metadata = (
                REPO_ROOT
                / "skills"
                / "diagnose"
                / "agents"
                / metadata_name
            ).read_text(encoding="utf-8")
            self.assertIn(invocation, metadata)
            self.assertIn("implement the source-cause fix", metadata)
            self.assertIn("end to end", metadata)
        improve_metadata = (
            REPO_ROOT
            / "skills"
            / "improve-codebase-architecture"
            / "agents"
            / "openai.yaml"
        ).read_text(encoding="utf-8")
        self.assertIn("allow_implicit_invocation: false", improve_metadata)

        self.assertIn("ed37663cc5fbef691ddfecd080dff42f7e7e350d", contract)
        self.assertIn("never fetch upstream content", normalized_contract)
        self.assertIn(
            "root cause is an intermediate result",
            normalized_contract,
        )
        self.assertIn(
            "must not hand control back merely because",
            normalized_contract,
        )
        self.assertIn("1-8 candidates", contract)
        self.assertIn(
            "restrictive content security policy",
            normalized_contract,
        )

    def test_diagnose_fix_complete_path_cannot_stop_at_root_cause(self) -> None:
        diagnose = (
            REPO_ROOT / "skills" / "diagnose" / "SKILL.md"
        ).read_text(encoding="utf-8")
        execute = (
            REPO_ROOT / "skills" / "execute" / "SKILL.md"
        ).read_text(encoding="utf-8")
        chain = (
            REPO_ROOT / "skills" / "harness-chain" / "SKILL.md"
        ).read_text(encoding="utf-8")
        normalized_diagnose = " ".join(diagnose.split())

        phases = [
            "## Phase 1 — Build the red loop",
            "## Phase 2 — Reproduce and minimise",
            "## Phase 3 — Find the first divergence",
            "## Phase 4 — Lock the regression",
            "## Phase 5 — Fix and iterate",
            "## Phase 6 — Prove completion",
        ]
        positions = [diagnose.index(phase) for phase in phases]
        self.assertEqual(positions, sorted(positions))
        for required in (
            "explicitly invokes this skill",
            "red regression signal",
            "source-cause patch",
            "original, unminimised scenario",
            "relevant module, caller, integration, and configured project checks",
            "intermediate findings are progress updates",
            "Root cause is a milestone, not completion",
        ):
            self.assertIn(required, normalized_diagnose)
        self.assertIn("Root cause is not a handoff point", execute)
        self.assertIn(
            "Reproduction and root cause are intermediate chain work",
            chain,
        )

    def test_korean_skill_guide_covers_the_v53_catalog(self) -> None:
        guide = (
            REPO_ROOT / "docs" / "ezpowers-skills-guide.html"
        ).read_text(encoding="utf-8")
        expected = {
            path.name
            for path in (REPO_ROOT / "skills").iterdir()
            if path.is_dir()
        }
        for name in expected:
            self.assertIn(f'id="skill-{name}"', guide)
            self.assertIn(f"../skills/{name}/SKILL.md", guide)
        self.assertEqual(13, guide.count('class="skill-card"'))
        self.assertIn("13 plugin skills", guide)
        self.assertIn("12 project skills", guide)
        self.assertIn("../project-kit/v5.3.0/manifest.json", guide)
        self.assertNotIn("v5.2.0/manifest.json", guide)

    def test_plugin_manifests_expose_the_same_version_and_current_workflow(self) -> None:
        claude = json.loads((REPO_ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
        marketplace = json.loads((REPO_ROOT / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8"))
        codex = json.loads((REPO_ROOT / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8"))
        self.assertEqual(claude["version"], "5.3.2")
        self.assertEqual(marketplace["plugins"][0]["version"], "5.3.2")
        self.assertTrue(codex["version"].startswith("5.3.2+codex."))
        combined = json.dumps([claude, marketplace, codex])
        self.assertIn("deep-interview", combined)
        self.assertIn("execute", combined)
        self.assertIn("wiki", combined)
        self.assertIn("harness-chain", combined)
        self.assertIn("diagnose", combined)
        self.assertIn("codebase-design", combined)
        self.assertIn("improve-codebase-architecture", combined)
        self.assertNotIn("choice-execute", combined)


if __name__ == "__main__":
    unittest.main()
