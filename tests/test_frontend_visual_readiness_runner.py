import json
import pathlib
import subprocess
import sys
import tempfile
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
RUNNER = REPO_ROOT / "scripts" / "frontend-visual-readiness.py"


class FrontendVisualReadinessRunnerTests(unittest.TestCase):
    def write(self, root: pathlib.Path, path: str, text: str) -> pathlib.Path:
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
        return target

    def make_project(self, root: pathlib.Path, design_text: str) -> None:
        self.write(
            root,
            ".ezpowers/config.json",
            json.dumps({
                "frontend": {
                    "design_artifact": "docs/ux/frontend-design.md",
                },
            }),
        )
        self.write(root, "docs/ux/frontend-design.md", design_text)

    def run_runner(self, root: pathlib.Path, *args: str) -> tuple[int, dict]:
        proc = subprocess.run(
            [
                sys.executable,
                str(RUNNER),
                "--project-root",
                str(root),
                "--json",
                *args,
            ],
            text=True,
            capture_output=True,
            timeout=10,
            check=False,
        )
        data = json.loads(proc.stdout)
        return proc.returncode, data

    def test_no_visual_tooling_keeps_lanes_advisory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            self.make_project(root, "# Frontend Design\n\nVisual QA strategy: component DOM fallback.\n")

            code, data = self.run_runner(root)

            self.assertEqual(code, 0, data)
            self.assertEqual(data["schema_version"], 2)
            self.assertFalse(data["lanes"]["storybook_component_states"]["required"])
            self.assertFalse(data["lanes"]["screenshot_visual_baseline"]["required"])

    def test_managed_design_system_mapping_is_a_required_lane(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            design = """---
version: alpha
name: Fixture
omitted: ["typography", "rounded", "spacing", "components"]
colors:
  primary: "#315bdc"
---
# Fixture

## Overview
Fixture direction.

## Colors
Primary action color.
"""
            self.write(root, "DESIGN.md", design)
            self.write(root, "index.html", "<!doctype html>")
            mapping = {
                "schema_version": 1,
                "design_systems": [
                    {
                        "path": "DESIGN.md",
                        "profile": "google-alpha-0.4.0-ezpowers-1",
                        "frontend_roots": ["."],
                        "implementation_paths": ["index.html"],
                    }
                ],
            }
            artifact = (
                "# Frontend Design\n\n"
                "<!-- ezpowers:frontend-design:start -->\n```json\n"
                + json.dumps(mapping, indent=2)
                + "\n```\n<!-- ezpowers:frontend-design:end -->\n"
            )
            self.make_project(root, artifact)

            code, data = self.run_runner(root)

            self.assertEqual(code, 0, data)
            lane = data["lanes"]["design_system_mapping"]
            self.assertTrue(lane["required"])
            self.assertTrue(lane["pass"])

    def test_existing_storybook_requires_component_state_stories(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            self.make_project(root, "# Frontend Design\n\nVisual QA strategy: Storybook.\n")
            self.write(root, "package.json", '{"scripts":{"storybook":"storybook dev -p 6006"}}')
            (root / ".storybook").mkdir()

            code, data = self.run_runner(root)

            self.assertEqual(code, 1, data)
            lane = data["lanes"]["storybook_component_states"]
            self.assertTrue(lane["required"])
            self.assertFalse(lane["pass"])

    def test_playwright_e2e_only_keeps_screenshot_lane_advisory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            self.make_project(root, "# Frontend Design\n\nVisual QA strategy: Playwright.\n")
            self.write(root, "playwright.config.ts", "export default {};\n")

            code, data = self.run_runner(root)

            self.assertEqual(code, 0, data)
            self.assertTrue(data["tools"]["playwright"]["available"])
            self.assertFalse(data["lanes"]["screenshot_visual_baseline"]["required"])

    def test_playwright_screenshots_require_baseline_loop(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            self.make_project(root, "# Frontend Design\n\nVisual QA strategy: Playwright screenshots.\n")
            self.write(root, "playwright.config.ts", "export default {};\n")
            self.write(
                root,
                "tests/visual.spec.ts",
                "import { expect } from '@playwright/test';\nawait expect(page).toHaveScreenshot();\n",
            )

            code, data = self.run_runner(root)

            self.assertEqual(code, 1, data)
            lane = data["lanes"]["screenshot_visual_baseline"]
            self.assertTrue(lane["required"])
            self.assertFalse(lane["pass"])

    def test_plan_prerequisites_make_visual_lanes_required(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            self.make_project(
                root,
                "\n".join([
                    "# Frontend Design",
                    "Component states/stories: Storybook covers loading and error states.",
                    "Visual QA strategy: screenshot baseline at tests/visual/baseline with visual review loop.",
                ]),
            )
            self.write(
                root,
                "docs/plans/visual.md",
                "Task 0: install Storybook and configure Playwright screenshot baseline as prerequisite.",
            )

            code, data = self.run_runner(root, "--plan", "docs/plans/visual.md")

            self.assertEqual(code, 0, data)
            self.assertTrue(data["lanes"]["storybook_component_states"]["required"])
            self.assertTrue(data["lanes"]["screenshot_visual_baseline"]["required"])

    def test_normative_mock_prototype_requires_mapping_and_freshness(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            self.make_project(
                root,
                "\n".join([
                    "# Frontend Design",
                    "Mock/prototype artifacts: normative docs/ux/mock.png.",
                    "Visual QA strategy: component DOM fallback.",
                ]),
            )

            code, data = self.run_runner(root)

            self.assertEqual(code, 1, data)
            lane = data["lanes"]["mock_prototype_artifacts"]
            self.assertTrue(lane["required"])
            self.assertFalse(lane["pass"])

    def test_nested_workspace_storybook_requires_component_states(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            self.make_project(root, "# Frontend Design\n\nVisual QA strategy: Storybook.\n")
            self.write(root, "package.json", '{"workspaces":["apps/*"]}')
            self.write(root, "apps/web/package.json", '{"scripts":{"storybook":"storybook dev"}}')

            code, data = self.run_runner(root)

            self.assertEqual(code, 1, data)
            self.assertIn(str(root / "apps" / "web"), data["frontend_roots"])
            self.assertTrue(data["lanes"]["storybook_component_states"]["required"])

    def test_frontend_root_option_scans_nested_app(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            self.make_project(root, "# Frontend Design\n\nVisual QA strategy: Storybook.\n")
            self.write(root, "apps/web/package.json", '{"devDependencies":{"histoire":"latest"}}')

            code, data = self.run_runner(root, "--frontend-root", "apps/web")

            self.assertEqual(code, 1, data)
            self.assertTrue(data["tools"]["storybook"]["available"])
            self.assertTrue(data["lanes"]["storybook_component_states"]["required"])

    def test_negated_plan_does_not_require_visual_lanes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            self.make_project(root, "# Frontend Design\n\nVisual QA strategy: component DOM fallback.\n")
            self.write(
                root,
                "docs/plans/visual.md",
                "Do not install Storybook. Playwright screenshots are not a prerequisite for this docs-only task.",
            )

            code, data = self.run_runner(root, "--plan", "docs/plans/visual.md")

            self.assertEqual(code, 0, data)
            self.assertFalse(data["lanes"]["storybook_component_states"]["required"])
            self.assertFalse(data["lanes"]["screenshot_visual_baseline"]["required"])

    def test_reference_only_mock_with_design_source_of_truth_is_advisory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            self.make_project(
                root,
                "\n".join([
                    "# Frontend Design",
                    "Mock/prototype artifacts: Figma link is reference-only.",
                    "Implementation follows the repo-owned design artifact as source of truth.",
                    "Visual QA strategy: component DOM fallback.",
                ]),
            )

            code, data = self.run_runner(root)

            self.assertEqual(code, 0, data)
            lane = data["lanes"]["mock_prototype_artifacts"]
            self.assertFalse(lane["required"])
            self.assertTrue(lane["pass"])

    def test_equivalent_visual_diff_tool_requires_baseline_loop(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            self.make_project(root, "# Frontend Design\n\nVisual QA strategy: browser visual regression.\n")
            self.write(root, "package.json", '{"devDependencies":{"backstopjs":"latest"}}')

            code, data = self.run_runner(root)

            self.assertEqual(code, 1, data)
            self.assertTrue(data["tools"]["visual_diff"]["available"])
            self.assertTrue(data["lanes"]["screenshot_visual_baseline"]["required"])

    def test_invalid_package_json_reports_warning_without_crashing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            self.make_project(root, "# Frontend Design\n\nVisual QA strategy: component DOM fallback.\n")
            self.write(root, "package.json", "{not-json")

            code, data = self.run_runner(root)

            self.assertEqual(code, 0, data)
            self.assertTrue(any("Invalid JSON ignored" in warning for warning in data["warnings"]))

    def test_detect_mode_exits_zero_with_required_gap(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            self.make_project(root, "# Frontend Design\n\nVisual QA strategy: Storybook.\n")
            self.write(root, "package.json", '{"scripts":{"storybook":"storybook dev"}}')

            code, data = self.run_runner(root, "--mode", "detect")

            self.assertEqual(code, 0, data)
            self.assertFalse(data["pass"])
            self.assertTrue(data["errors"])
            self.assertTrue(any("Detect mode is advisory" in warning for warning in data["warnings"]))


if __name__ == "__main__":
    unittest.main()
