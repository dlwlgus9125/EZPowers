import pathlib
import re
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
CONTRACT = REPO_ROOT / "docs/reference/reviewer-placement-contract.md"


def _section_rows(text: str, marker: str) -> dict[str, str]:
    start = f"<!-- {marker}-BEGIN -->"
    end = f"<!-- {marker}-END -->"
    body = text.split(start, 1)[1].split(end, 1)[0]
    rows: dict[str, str] = {}
    for raw in body.splitlines():
        line = raw.strip()
        if not line.startswith("| `"):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) >= 2:
            rows[cells[0].strip("`")] = cells[1]
    return rows


def _reviewer_names(cell: str) -> set[str]:
    return set(re.findall(r"`ezpowers:([a-z-]+)`", cell))


class ReviewerPlacementContractTests(unittest.TestCase):
    def test_every_command_has_reviewer_mapping(self):
        text = CONTRACT.read_text(encoding="utf-8")
        rows = _section_rows(text, "REVIEWER-MATRIX-COMMANDS")
        commands = {f"/{path.stem}" for path in (REPO_ROOT / "commands").glob("*.md")}

        self.assertEqual(commands, set(rows), "command reviewer matrix drifted")
        for command, reviewers in rows.items():
            self.assertTrue(_reviewer_names(reviewers), f"{command} has no reviewer")

    def test_every_skill_has_reviewer_mapping(self):
        text = CONTRACT.read_text(encoding="utf-8")
        rows = _section_rows(text, "REVIEWER-MATRIX-SKILLS")
        skills = {
            path.parent.name
            for path in (REPO_ROOT / "skills").glob("*/SKILL.md")
        }

        self.assertEqual(skills, set(rows), "skill reviewer matrix drifted")
        for skill, reviewers in rows.items():
            self.assertTrue(_reviewer_names(reviewers), f"{skill} has no reviewer")

    def test_reviewer_agents_are_registered_for_dispatch_and_routing(self):
        text = CONTRACT.read_text(encoding="utf-8")
        dispatch = (REPO_ROOT / "docs/reference/dispatch-protocol.md").read_text(
            encoding="utf-8"
        )
        routing = (REPO_ROOT / "docs/reference/model-routing-contract.md").read_text(
            encoding="utf-8"
        )
        reviewers = set()
        for marker in ("REVIEWER-MATRIX-COMMANDS", "REVIEWER-MATRIX-SKILLS"):
            for cell in _section_rows(text, marker).values():
                reviewers.update(_reviewer_names(cell))

        for reviewer in sorted(reviewers):
            agent_path = REPO_ROOT / f"agents/{reviewer}.md"
            self.assertTrue(agent_path.exists(), f"missing agent: {reviewer}")
            if reviewer == "workflow-contract-reviewer":
                self.assertIn("ezpowers:workflow-contract-reviewer", dispatch)
                self.assertIn("workflow-contract-reviewer", routing)


if __name__ == "__main__":
    unittest.main()
