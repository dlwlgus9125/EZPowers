from __future__ import annotations

import hashlib
import importlib.util
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
TOOL = ROOT / "scripts" / "design-md.py"
UPSTREAM_CHECK = ROOT / "scripts" / "check-design-md-upstream.py"
PROFILE = "google-alpha-0.4.0-ezpowers-1"


def load_tool():
    spec = importlib.util.spec_from_file_location("ezpowers_design_md", TOOL)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


DESIGN_MD = load_tool()


def design_text(name: str = "Fixture", primary: str = "#315bdc") -> str:
    return f'''---
version: alpha
name: {name}
colors:
  primary: "{primary}"
  paper: "#ffffff"
  ink: "#172033"
typography:
  body:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: 400
    lineHeight: 1.6
rounded:
  md: 12px
spacing:
  md: 16px
components:
  card:
    backgroundColor: "{{colors.paper}}"
    textColor: "{{colors.ink}}"
    rounded: "{{rounded.md}}"
    padding: "{{spacing.md}}"
---
# {name}

## Overview
Calm and direct.

## Colors
Use the primary color for actions.

## Typography
Use the body token.

## Layout
Use the spacing scale.

## Shapes
Use the radius scale.

## Components
Use the card mapping.
'''


def frontend_artifact(systems: list[dict[str, object]]) -> str:
    managed = json.dumps(
        {"schema_version": 1, "design_systems": systems},
        indent=2,
        ensure_ascii=False,
    )
    return f"""# Frontend Design

<!-- ezpowers:frontend-design:start -->
```json
{managed}
```
<!-- ezpowers:frontend-design:end -->
"""


class DesignMdToolTests(unittest.TestCase):
    def test_repository_design_passes_and_matches_html_css_tokens(self) -> None:
        result = DESIGN_MD.lint_path(ROOT / "DESIGN.md", PROFILE)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["summary"]["warning"], 0)
        html = (ROOT / "docs" / "ezpowers-skills-guide.html").read_text(encoding="utf-8")
        light = html.split(":root {", 1)[1].split("}", 1)[0]
        dark = html.split('html[data-theme="dark"] {', 1)[1].split("}", 1)[0]
        colors = result["tokens"]["colors"]
        for name, value in colors.items():
            css_name = name.removeprefix("dark-")
            block = dark if name.startswith("dark-") else light
            self.assertIn(f"--{css_name}: {value};", block, name)
        for name, value in result["tokens"]["rounded"].items():
            if name != "full":
                self.assertIn(f"--radius-{name}: {value};", light)

    def test_lint_reports_broken_reference_and_duplicate_section(self) -> None:
        bad = design_text().replace("{colors.ink}", "{colors.missing}")
        bad += "\n## Colors\nDuplicate.\n"
        profile, _ = DESIGN_MD.load_profile(PROFILE)
        result = DESIGN_MD.lint_text(
            bad,
            profile=profile,
            label="DESIGN.md",
            digest=hashlib.sha256(bad.encode()).hexdigest(),
        )
        self.assertEqual(result["status"], "FAIL")
        rules = [item["rule"] for item in result["findings"] if item["severity"] == "error"]
        self.assertIn("broken-ref", rules)
        self.assertIn("section-order", rules)

    def test_token_like_prose_is_reported_but_preserved(self) -> None:
        text = design_text() + "\n--unmanaged-accent: #ff00aa\n"
        profile, _ = DESIGN_MD.load_profile(PROFILE)
        result = DESIGN_MD.lint_text(
            text,
            profile=profile,
            label="DESIGN.md",
            digest=hashlib.sha256(text.encode()).hexdigest(),
        )
        self.assertEqual(result["status"], "PASS")
        self.assertTrue(
            any(item["rule"] == "token-like-ignored" for item in result["findings"])
        )

    def test_diff_marks_token_removal_as_regression(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            before = root / "before.md"
            after = root / "after.md"
            before.write_text(design_text(), encoding="utf-8")
            after.write_text(design_text().replace('  ink: "#172033"\n', ""), encoding="utf-8")
            result = DESIGN_MD.diff_paths(before, after, PROFILE)
            self.assertEqual(result["status"], "REGRESSION")
            self.assertIn("removed-token", result["regression_reasons"])
            self.assertTrue(any(item["path"] == "colors.ink" for item in result["tokens"]["removed"]))

    def test_diff_detects_a_new_warning_when_warning_count_is_unchanged(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            before = root / "before.md"
            after = root / "after.md"
            before.write_text(
                design_text().replace("colors:\n", "mystery: preserved\ncolors:\n", 1),
                encoding="utf-8",
            )
            after.write_text(
                design_text().replace(
                    "## Colors\nUse the primary color for actions.\n\n"
                    "## Typography\nUse the body token.",
                    "## Typography\nUse the body token.\n\n"
                    "## Colors\nUse the primary color for actions.",
                ),
                encoding="utf-8",
            )
            result = DESIGN_MD.diff_paths(before, after, PROFILE)
            self.assertEqual(result["before"]["summary"]["warning"], 1)
            self.assertEqual(result["after"]["summary"]["warning"], 1)
            self.assertEqual(result["status"], "REGRESSION")
            self.assertIn("new-warning", result["regression_reasons"])
            self.assertTrue(
                any(
                    item["rule"] == "section-order"
                    for item in result["findings"]["added"]
                )
            )

    def test_project_mapping_uses_nearest_frontend_root_without_merging(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            (root / "docs" / "ux").mkdir(parents=True)
            (root / "apps" / "admin").mkdir(parents=True)
            (root / "src").mkdir()
            (root / "DESIGN.md").write_text(design_text("Root"), encoding="utf-8")
            (root / "apps" / "admin" / "DESIGN.md").write_text(design_text("Admin", "#087c70"), encoding="utf-8")
            (root / "src" / "site.html").write_text("root", encoding="utf-8")
            (root / "apps" / "admin" / "index.html").write_text("admin", encoding="utf-8")
            systems = [
                {
                    "path": "DESIGN.md",
                    "profile": PROFILE,
                    "frontend_roots": ["."],
                    "implementation_paths": ["src/site.html"],
                },
                {
                    "path": "apps/admin/DESIGN.md",
                    "profile": PROFILE,
                    "frontend_roots": ["apps/admin"],
                    "implementation_paths": ["apps/admin/index.html"],
                },
            ]
            artifact = root / "docs" / "ux" / "frontend-design.md"
            artifact.write_text(frontend_artifact(systems), encoding="utf-8")
            result = DESIGN_MD.check_project(root, artifact)
            self.assertEqual(result["status"], "PASS", result["errors"])
            self.assertEqual(
                {item["implementation_path"]: item["design_system"] for item in result["resolutions"]},
                {"src/site.html": "DESIGN.md", "apps/admin/index.html": "apps/admin/DESIGN.md"},
            )
            systems[0]["implementation_paths"].append("apps/admin/index.html")
            artifact.write_text(frontend_artifact(systems), encoding="utf-8")
            rejected = DESIGN_MD.check_project(root, artifact)
            self.assertEqual(rejected["status"], "FAIL")
            self.assertTrue(
                any(
                    "claimed by DESIGN.md but nearest mapping is apps/admin/DESIGN.md"
                    in message
                    for message in rejected["errors"]
                )
            )

    def test_project_mapping_rejects_reserved_design_path(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            (root / "docs" / "ux").mkdir(parents=True)
            artifact = root / "docs" / "ux" / "frontend-design.md"
            artifact.write_text(
                frontend_artifact(
                    [
                        {
                            "path": ".ezpowers/DESIGN.md",
                            "profile": PROFILE,
                            "frontend_roots": ["."],
                            "implementation_paths": ["docs/ux/frontend-design.md"],
                        }
                    ]
                ),
                encoding="utf-8",
            )
            result = DESIGN_MD.check_project(root, artifact)
            self.assertEqual(result["status"], "FAIL")
            self.assertTrue(any("reserved" in message for message in result["errors"]))

    def test_upstream_checker_reports_current_review_and_unavailable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            upstream = root / "upstream"
            upstream.mkdir()
            watched = upstream / "spec.md"
            watched.write_text("reviewed bytes\n", encoding="utf-8")
            digest = hashlib.sha256(watched.read_bytes()).hexdigest()
            contract = root / "profile.json"
            contract.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "profiles": {
                            "fixture": {
                                "upstream": {
                                    "commit": "abc",
                                    "reviewed_at": "2026-08-09",
                                    "watched_files": [{"path": "spec.md", "sha256": digest}],
                                }
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            command = [
                sys.executable,
                str(UPSTREAM_CHECK),
                "--profile-contract",
                str(contract),
                "--profile",
                "fixture",
                "--base-url",
                upstream.as_uri(),
                "--json",
            ]
            current = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", check=False)
            self.assertEqual(current.returncode, 0, current.stderr)
            self.assertEqual(json.loads(current.stdout)["status"], "CURRENT")
            unavailable_command = list(command)
            unavailable_command[unavailable_command.index(upstream.as_uri())] = (
                root / "missing"
            ).as_uri()
            unavailable = subprocess.run(
                unavailable_command,
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=False,
            )
            self.assertEqual(unavailable.returncode, 2)
            self.assertEqual(json.loads(unavailable.stdout)["status"], "UNAVAILABLE")


if __name__ == "__main__":
    unittest.main()
