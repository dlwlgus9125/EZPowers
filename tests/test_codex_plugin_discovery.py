import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
SMOKE_PATH = REPO_ROOT / "scripts" / "plugin_smoke.py"

SPEC = importlib.util.spec_from_file_location("plugin_smoke", SMOKE_PATH)
assert SPEC is not None and SPEC.loader is not None
PLUGIN_SMOKE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PLUGIN_SMOKE)


class PluginDiscoveryTests(unittest.TestCase):
    def test_each_host_file_surface_passes_plugin_smoke(self):
        for host in ("claude", "codex"):
            with self.subTest(host=host):
                errors = PLUGIN_SMOKE.validate_repository(REPO_ROOT, (host,))
                self.assertEqual([], errors, "\n".join(errors))

    def test_manifests_publish_only_the_retained_v5_surface(self):
        claude = json.loads(
            (REPO_ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8")
        )
        marketplace = json.loads(
            (REPO_ROOT / ".claude-plugin" / "marketplace.json").read_text(
                encoding="utf-8"
            )
        )
        codex = json.loads(
            (REPO_ROOT / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8")
        )
        codex_marketplace = json.loads(
            (REPO_ROOT / ".agents" / "plugins" / "marketplace.json").read_text(
                encoding="utf-8"
            )
        )

        self.assertEqual("5.3.3", claude["version"])
        self.assertEqual("5.3.3", marketplace["plugins"][0]["version"])
        self.assertRegex(codex["version"], r"^5\.3\.3\+codex\.[0-9]{14}$")
        self.assertEqual(1, codex["version"].count("+codex."))
        self.assertEqual("ezpowers-dev", codex_marketplace["name"])
        self.assertEqual("ezpowers", codex_marketplace["plugins"][0]["name"])
        self.assertEqual(
            {"source": "local", "path": "./"},
            codex_marketplace["plugins"][0]["source"],
        )

        for manifest in (claude, codex):
            self.assertNotIn("agents", manifest)
            self.assertNotIn("commands", manifest)
            self.assertNotIn("hooks", manifest)

        described = set(
            re.findall(
                r"ezpowers:([a-z0-9-]+)",
                codex["interface"]["longDescription"],
            )
        )
        self.assertEqual(PLUGIN_SMOKE.RETAINED_SKILLS, described)

    def test_codex_prompts_use_live_skill_invocation(self):
        manifest = json.loads(
            (REPO_ROOT / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8")
        )
        prompts = manifest["interface"]["defaultPrompt"]
        prompt_text = "\n".join(prompts)
        referenced = set(re.findall(r"\$ezpowers:([a-z0-9-]+)", prompt_text))

        self.assertEqual({"setup", "deep-interview", "harness-chain"}, referenced)
        self.assertLessEqual(referenced, PLUGIN_SMOKE.RETAINED_SKILLS)
        self.assertLessEqual(len(prompts), 3)
        self.assertFalse(any(prompt.strip().startswith("/") for prompt in prompts))
        deep_interview_prompt = next(
            prompt for prompt in prompts if "$ezpowers:deep-interview" in prompt
        )
        self.assertIn("Plan Mode", deep_interview_prompt)
        self.assertIn("continue planning after confirmation", deep_interview_prompt)
        self.assertIn("consequential blind spots", deep_interview_prompt)

    def test_smoke_cli_validates_both_hosts_without_installing(self):
        result = subprocess.run(
            [
                sys.executable,
                str(SMOKE_PATH),
                "--host",
                "both",
                "--skip-host-probes",
            ],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )

        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertIn("[PASS] both plugin files", result.stdout)

    def test_live_advisory_requires_one_consequential_blind_spot_question(self):
        self.assertTrue(PLUGIN_SMOKE._one_question_response("Which outcome matters most?"))
        self.assertFalse(PLUGIN_SMOKE._one_question_response("Ready."))
        self.assertFalse(PLUGIN_SMOKE._one_question_response("Why? When?"))
        self.assertFalse(
            PLUGIN_SMOKE._one_question_response(
                "Unknown skill. What should I do?"
            )
        )
        self.assertTrue(
            PLUGIN_SMOKE._consequential_blind_spot_response(
                "Which legal retention obligations must survive permanent deletion?"
            )
        )
        self.assertFalse(
            PLUGIN_SMOKE._consequential_blind_spot_response(
                "What exact time should the nightly job start?"
            )
        )
        self.assertFalse(
            PLUGIN_SMOKE._consequential_blind_spot_response(
                "Which legal rules apply? Which backups remain?"
            )
        )

    def test_live_diagnose_fixed_fixture_proves_red_before_product_patch(self):
        with tempfile.TemporaryDirectory() as temp_name:
            fixture = Path(temp_name)
            baseline = PLUGIN_SMOKE._write_live_diagnose_fixture(fixture, "fixed")
            red = PLUGIN_SMOKE._run_command(
                [sys.executable, "reproduce_exact.py"],
                cwd=fixture,
            )
            self.assertEqual(1, red.returncode)
            self.assertIn("EZPOWERS_DIAGNOSE_EXACT_RED", red.stdout)
            (fixture / "event_store.py").write_text(
                "def visible_events(events, tenant_id):\n"
                "    return [event for event in events "
                'if event["tenant_id"] == tenant_id]\n',
                encoding="utf-8",
            )
            green = PLUGIN_SMOKE._run_command(
                [sys.executable, "reproduce_exact.py"],
                cwd=fixture,
            )
            self.assertEqual(0, green.returncode)
            self.assertEqual(
                [],
                PLUGIN_SMOKE._validate_live_diagnose_fixed(
                    fixture,
                    baseline,
                    red.stdout + green.stdout,
                ),
            )

    def test_live_diagnose_fixed_fixture_rejects_product_edit_before_red(self):
        with tempfile.TemporaryDirectory() as temp_name:
            fixture = Path(temp_name)
            baseline = PLUGIN_SMOKE._write_live_diagnose_fixture(fixture, "fixed")
            (fixture / "event_store.py").write_text(
                "def visible_events(events, tenant_id):\n"
                "    return []\n",
                encoding="utf-8",
            )
            red_after_edit = PLUGIN_SMOKE._run_command(
                [sys.executable, "reproduce_exact.py"],
                cwd=fixture,
            )
            errors = PLUGIN_SMOKE._validate_live_diagnose_fixed(
                fixture,
                baseline,
                red_after_edit.stdout,
            )
            self.assertTrue(
                any("before observing exact red" in error for error in errors),
                errors,
            )

    def test_live_diagnose_blocked_fixture_requires_specific_evidence(self):
        with tempfile.TemporaryDirectory() as temp_name:
            fixture = Path(temp_name)
            baseline = PLUGIN_SMOKE._write_live_diagnose_fixture(
                fixture,
                "blocked",
            )
            blocked = PLUGIN_SMOKE._run_command(
                [sys.executable, "reproduce_exact.py"],
                cwd=fixture,
            )
            self.assertEqual(2, blocked.returncode)
            self.assertIn("EZPOWERS_DIAGNOSE_REPRO_BLOCKED", blocked.stdout)
            response = (
                "The exact reproduction is blocked because "
                "production_capture.json is missing. Please provide that "
                "captured artifact or grant access for temporary instrumentation."
            )
            self.assertEqual(
                [],
                PLUGIN_SMOKE._validate_live_diagnose_blocked(
                    fixture,
                    baseline,
                    response,
                    blocked.stdout,
                ),
            )

    def test_claude_stream_json_retains_final_diagnose_response(self):
        transcript = "\n".join(
            (
                json.dumps(
                    {
                        "type": "user",
                        "message": {
                            "content": "EZPOWERS_DIAGNOSE_EXACT_RED source_sha256=abc"
                        },
                    }
                ),
                json.dumps({"type": "result", "result": "Verified fix complete."}),
            )
        )
        self.assertEqual(
            "Verified fix complete.",
            PLUGIN_SMOKE._claude_final_response(transcript),
        )

    def test_plugin_smoke_console_handles_unicode_model_output_under_cp949(self):
        probe = (
            "import importlib.util\n"
            f"path = {str(SMOKE_PATH)!r}\n"
            "spec = importlib.util.spec_from_file_location('plugin_smoke_probe', path)\n"
            "module = importlib.util.module_from_spec(spec)\n"
            "spec.loader.exec_module(module)\n"
            "module._configure_console_output()\n"
            "print('model response \\u2014 retained')\n"
        )
        environment = os.environ.copy()
        environment["PYTHONIOENCODING"] = "cp949"
        result = subprocess.run(
            [sys.executable, "-c", probe],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            encoding="cp949",
            env=environment,
            check=False,
        )
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn(r"\u2014", result.stdout)


if __name__ == "__main__":
    unittest.main()
