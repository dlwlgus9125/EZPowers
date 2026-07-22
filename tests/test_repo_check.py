from __future__ import annotations

import importlib.util
import json
import pathlib
import tempfile
import textwrap
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
MODULE_PATH = REPO_ROOT / "scripts" / "check_repo.py"


def load_gate():
    spec = importlib.util.spec_from_file_location("ezpowers_check_repo", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write(path: pathlib.Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(text).lstrip(), encoding="utf-8")


class RepositoryGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.gate = load_gate()

    def make_valid_repo(self, root: pathlib.Path) -> None:
        retained = sorted(self.gate.RETAINED_SKILLS)
        for name in retained:
            write(
                root / "skills" / name / "SKILL.md",
                f"""
                ---
                name: {name}
                description: Use when testing {name}.
                ---

                # {name}
                """,
            )
            write(
                root / "skills" / name / "agents" / "openai.yaml",
                f"""
                interface:
                  display_name: "{name}"
                  short_description: "Test {name}"
                  default_prompt: "Use ${name} for this request."
                policy:
                  allow_implicit_invocation: false
                """,
            )

        description = " ".join(f"ezpowers:{name}" for name in retained)
        plugin = {
            "name": "ezpowers",
            "version": "5.0.0",
            "description": "test",
        }
        marketplace = {
            "name": "test",
            "plugins": [
                {
                    "name": "ezpowers",
                    "version": "5.0.0",
                    "source": "./",
                }
            ],
        }
        codex = {
            "name": "ezpowers",
            "version": "5.0.0+codex.20260722000000",
            "skills": "./skills/",
            "interface": {"longDescription": description, "defaultPrompt": []},
        }
        write(root / ".claude-plugin" / "plugin.json", json.dumps(plugin))
        write(root / ".claude-plugin" / "marketplace.json", json.dumps(marketplace))
        write(root / ".codex-plugin" / "plugin.json", json.dumps(codex))

        write(root / "project-kit" / "v5.0.0" / "manifest.json", "{}")
        write(
            root / "scripts" / "verify-harness-kit.py",
            """
            import sys
            raise SystemExit(0)
            """,
        )
        write(root / "docs" / "INDEX.md", "[Guide](guide.md)\n")
        write(root / "docs" / "guide.md", "# Guide\n")
        write(root / "AGENTS.md", "# Agent guide\n")

    def test_valid_v5_surface_passes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = pathlib.Path(temp_dir)
            self.make_valid_repo(root)

            self.assertEqual(self.gate.validate_repository(root), [])

    def test_inventory_and_openai_metadata_are_exact(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = pathlib.Path(temp_dir)
            self.make_valid_repo(root)
            write(
                root / "skills" / "choice-execute" / "SKILL.md",
                "---\nname: choice-execute\ndescription: old\n---\n",
            )
            (root / "skills" / "setup" / "agents" / "openai.yaml").unlink()

            errors = self.gate.validate_repository(root)

            self.assertTrue(any("skill inventory" in error for error in errors), errors)
            self.assertTrue(any("setup/agents/openai.yaml" in error for error in errors), errors)

    def test_manifest_drift_and_removed_components_fail(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = pathlib.Path(temp_dir)
            self.make_valid_repo(root)
            codex_path = root / ".codex-plugin" / "plugin.json"
            codex = json.loads(codex_path.read_text(encoding="utf-8"))
            codex["version"] = "5.1.0+codex.20260722000000"
            write(codex_path, json.dumps(codex))
            write(root / "evals" / "README.md", "# Removed eval\n")
            write(root / "scripts" / "harness-run.ps1", "# removed\n")

            errors = self.gate.validate_repository(root)

            self.assertTrue(any("version mismatch" in error for error in errors), errors)
            self.assertTrue(any("removed live directory remains: evals" in error for error in errors), errors)
            self.assertTrue(any("obsolete script remains" in error for error in errors), errors)

    def test_dead_markdown_paths_and_live_legacy_references_fail(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = pathlib.Path(temp_dir)
            self.make_valid_repo(root)
            write(
                root / "AGENTS.md",
                """
                [Missing](docs/missing.md)
                Run `scripts/missing.py`.
                Old config: `.harness/config.json`.
                """,
            )

            errors = self.gate.validate_repository(root)

            self.assertTrue(any("dead markdown link" in error for error in errors), errors)
            self.assertTrue(any("dead repository path" in error for error in errors), errors)
            self.assertTrue(any("obsolete live reference" in error for error in errors), errors)

    def test_explicit_legacy_migration_input_is_allowed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = pathlib.Path(temp_dir)
            self.make_valid_repo(root)
            write(
                root / "scripts" / "ezpowers.py",
                "legacy_path = root / '.harness' / 'config.json'  # migrate legacy input\n",
            )
            setup = root / "skills" / "setup" / "SKILL.md"
            setup.write_text(
                setup.read_text(encoding="utf-8")
                + "\nMigrate legacy `.harness/` and `phases/` input without deleting it.\n",
                encoding="utf-8",
            )

            errors = self.gate.validate_repository(root)

            self.assertFalse(
                any("obsolete live reference" in error for error in errors), errors
            )

    def test_project_kit_verifier_failure_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = pathlib.Path(temp_dir)
            self.make_valid_repo(root)
            write(
                root / "scripts" / "verify-harness-kit.py",
                "import sys\nprint('bad kit', file=sys.stderr)\nraise SystemExit(3)\n",
            )

            errors = self.gate.validate_repository(root)

            self.assertTrue(any("project-kit verifier failed" in error for error in errors), errors)
            self.assertTrue(any("bad kit" in error for error in errors), errors)

    def test_with_tests_reports_test_suite_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = pathlib.Path(temp_dir)
            self.make_valid_repo(root)
            write(
                root / "tests" / "test_failure.py",
                "import unittest\n\nclass Failure(unittest.TestCase):\n"
                "    def test_failure(self):\n        self.fail('expected')\n",
            )

            errors = self.gate.validate_repository(root, with_tests=True)

            self.assertTrue(any("test suite failed" in error for error in errors), errors)


if __name__ == "__main__":
    unittest.main()
