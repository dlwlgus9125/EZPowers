import json
import pathlib
import subprocess
import sys
import tempfile
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
CODEX_HUD = REPO_ROOT / "scripts" / "codex-hud.py"
HUD_SKILL = REPO_ROOT / "skills" / "hud" / "SKILL.md"
HUD_POLICY = REPO_ROOT / "skills" / "hud" / "agents" / "openai.yaml"
HUD_CONTRACT = REPO_ROOT / "docs" / "reference" / "codex-hud.md"

START_MARKER = "# >>> ezpowers:managed-codex-hud >>>"
END_MARKER = "# <<< ezpowers:managed-codex-hud <<<"
STATUS_LINE = 'status_line = ["five-hour-limit", "weekly-limit", "context-used"]'
USE_COLORS = "status_line_use_colors = true"


class CodexHudProcessTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.config = pathlib.Path(self.temp_dir.name) / ".codex" / "config.toml"

    def _run(self, action: str, *extra: str) -> tuple[subprocess.CompletedProcess, dict]:
        proc = subprocess.run(
            [
                sys.executable,
                str(CODEX_HUD),
                action,
                "--config",
                str(self.config),
                "--json",
                *extra,
            ],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )
        payload = json.loads(proc.stdout) if proc.stdout.strip() else {}
        return proc, payload

    def _write(self, text: str, *, encoding: str = "utf-8") -> None:
        self.config.parent.mkdir(parents=True, exist_ok=True)
        self.config.write_text(text, encoding=encoding, newline="")

    def test_preview_is_read_only_and_shows_exact_managed_fragment(self):
        proc, payload = self._run("preview")

        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertFalse(self.config.exists())
        self.assertEqual(payload["status"], "absent")
        self.assertTrue(payload["changed"])
        self.assertEqual(
            payload["managed_fragment"],
            [START_MARKER, STATUS_LINE, USE_COLORS, END_MARKER],
        )

    def test_install_requires_explicit_approval(self):
        proc, payload = self._run("install")

        self.assertEqual(proc.returncode, 2)
        self.assertEqual(payload["status"], "approval_required")
        self.assertFalse(self.config.exists())

    def test_install_creates_global_tui_section(self):
        proc, payload = self._run("install", "--approve")

        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(payload["status"], "installed")
        self.assertTrue(payload["changed"])
        self.assertEqual(
            self.config.read_text(encoding="utf-8"),
            "\n".join(["[tui]", START_MARKER, STATUS_LINE, USE_COLORS, END_MARKER, ""]),
        )

    def test_install_merges_into_existing_tui_section_and_preserves_other_keys(self):
        original = "\n".join(
            [
                'model = "gpt-5.6-sol"',
                "",
                "[tui]",
                "notifications = true",
                "",
                "[features]",
                "goals = true",
                "",
            ]
        )
        self._write(original)

        proc, payload = self._run("install", "--approve")

        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertTrue(payload["changed"])
        updated = self.config.read_text(encoding="utf-8")
        self.assertIn('model = "gpt-5.6-sol"', updated)
        self.assertIn("notifications = true", updated)
        self.assertIn("[features]\ngoals = true", updated)
        self.assertLess(updated.index(START_MARKER), updated.index("[features]"))

    def test_repeated_install_is_byte_idempotent(self):
        first, _ = self._run("install", "--approve")
        self.assertEqual(first.returncode, 0, first.stderr)
        before = self.config.read_bytes()

        second, payload = self._run("install", "--approve")

        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertEqual(payload["status"], "installed")
        self.assertFalse(payload["changed"])
        self.assertEqual(self.config.read_bytes(), before)

    def test_unowned_status_line_is_a_non_destructive_conflict(self):
        original = "[tui]\nstatus_line = [\"model\", \"git-branch\"]\n"
        self._write(original)

        proc, payload = self._run("install", "--approve")

        self.assertEqual(proc.returncode, 3)
        self.assertEqual(payload["status"], "conflict")
        self.assertEqual(payload["conflict_keys"], ["status_line"])
        self.assertEqual(self.config.read_text(encoding="utf-8"), original)

    def test_root_dotted_tui_status_line_is_a_non_destructive_conflict(self):
        original = 'tui.status_line = ["model", "git-branch"]\n'
        self._write(original)

        proc, payload = self._run("install", "--approve")

        self.assertEqual(proc.returncode, 3)
        self.assertEqual(payload["status"], "conflict")
        self.assertEqual(payload["conflict_keys"], ["status_line"])
        self.assertEqual(self.config.read_text(encoding="utf-8"), original)

    def test_root_inline_tui_table_is_rejected_without_writing(self):
        original = 'tui = { status_line = ["model"] }\n'
        self._write(original)

        proc, payload = self._run("install", "--approve")

        self.assertEqual(proc.returncode, 4)
        self.assertEqual(payload["status"], "malformed")
        self.assertEqual(self.config.read_text(encoding="utf-8"), original)
    def test_replace_existing_requires_explicit_flag_and_handles_multiline_array(self):
        self._write(
            "\n".join(
                [
                    "[tui]",
                    "status_line = [",
                    '  "model",',
                    '  "git-branch",',
                    "]",
                    "status_line_use_colors = false",
                    "notifications = true",
                    "",
                ]
            )
        )

        proc, payload = self._run(
            "install", "--approve", "--replace-existing"
        )

        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(payload["status"], "installed")
        updated = self.config.read_text(encoding="utf-8")
        self.assertIn(STATUS_LINE, updated)
        self.assertIn(USE_COLORS, updated)
        self.assertIn("notifications = true", updated)
        self.assertNotIn('  "model",', updated)
        self.assertNotIn("status_line_use_colors = false", updated)

    def test_install_preserves_a_user_edited_managed_block(self):
        self._run("install", "--approve")
        customized = self.config.read_text(encoding="utf-8").replace(
            "context-used", "context-remaining"
        )
        self._write(customized)

        proc, payload = self._run("install", "--approve")

        self.assertEqual(proc.returncode, 3)
        self.assertEqual(payload["status"], "customized")
        self.assertEqual(self.config.read_text(encoding="utf-8"), customized)

    def test_uninstall_removes_only_the_exact_owned_block(self):
        self._write("[tui]\nnotifications = true\n")
        installed, _ = self._run("install", "--approve")
        self.assertEqual(installed.returncode, 0, installed.stderr)

        proc, payload = self._run("uninstall", "--approve")

        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(payload["status"], "absent")
        self.assertTrue(payload["changed"])
        updated = self.config.read_text(encoding="utf-8")
        self.assertEqual(updated, "[tui]\nnotifications = true\n")

    def test_uninstall_requires_explicit_approval(self):
        installed, _ = self._run("install", "--approve")
        self.assertEqual(installed.returncode, 0, installed.stderr)
        before = self.config.read_bytes()

        proc, payload = self._run("uninstall")

        self.assertEqual(proc.returncode, 2)
        self.assertEqual(payload["status"], "approval_required")
        self.assertEqual(self.config.read_bytes(), before)

    def test_install_and_uninstall_preserve_utf8_bom_and_crlf(self):
        self.config.parent.mkdir(parents=True, exist_ok=True)
        original = b"\xef\xbb\xbfmodel = \"gpt-5.6-sol\"\r\n"
        self.config.write_bytes(original)

        installed, _ = self._run("install", "--approve")
        self.assertEqual(installed.returncode, 0, installed.stderr)
        installed_bytes = self.config.read_bytes()
        self.assertTrue(installed_bytes.startswith(b"\xef\xbb\xbf"))
        self.assertNotIn(b"\n", installed_bytes.replace(b"\r\n", b""))

        removed, _ = self._run("uninstall", "--approve")
        self.assertEqual(removed.returncode, 0, removed.stderr)
        removed_bytes = self.config.read_bytes()
        self.assertTrue(removed_bytes.startswith(b"\xef\xbb\xbf"))
        self.assertNotIn(b"\n", removed_bytes.replace(b"\r\n", b""))
        self.assertIn(b'model = "gpt-5.6-sol"', removed_bytes)

    def test_duplicate_tui_sections_are_rejected_without_writing(self):
        original = "[tui]\nnotifications = true\n[tui]\nanimations = false\n"
        self._write(original)

        proc, payload = self._run("install", "--approve")

        self.assertEqual(proc.returncode, 4)
        self.assertEqual(payload["status"], "malformed")
        self.assertEqual(self.config.read_text(encoding="utf-8"), original)


class CodexHudContractTests(unittest.TestCase):
    def test_skill_is_explicit_and_separate_from_harness_setup(self):
        skill = HUD_SKILL.read_text(encoding="utf-8")
        policy = HUD_POLICY.read_text(encoding="utf-8")

        self.assertIn("disable-model-invocation: true", skill)
        self.assertIn("description: Use when", skill)
        self.assertIn("do not install or refresh a project harness", skill)
        self.assertIn("allow_implicit_invocation: false", policy)
        self.assertIn("default_prompt: \"Use $ezpowers:hud", policy)
        self.assertIn("scripts/codex-hud.py", skill)

    def test_contract_and_script_use_the_same_owned_fragment(self):
        contract = HUD_CONTRACT.read_text(encoding="utf-8")

        for line in (START_MARKER, STATUS_LINE, USE_COLORS, END_MARKER):
            self.assertIn(line, contract)

    def test_codex_manifest_surfaces_the_hud_skill(self):
        manifest = json.loads(
            (REPO_ROOT / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8")
        )
        prompts = manifest["interface"]["defaultPrompt"]

        self.assertTrue(any(prompt.startswith("$ezpowers:hud ") for prompt in prompts))


if __name__ == "__main__":
    unittest.main()
