import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys
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

        self.assertEqual("5.0.1", claude["version"])
        self.assertEqual("5.0.1", marketplace["plugins"][0]["version"])
        self.assertRegex(codex["version"], r"^5\.0\.1\+codex\.[0-9]{14}$")
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

        self.assertEqual({"setup", "deep-interview", "execute", "hud"}, referenced)
        self.assertLessEqual(referenced, PLUGIN_SMOKE.RETAINED_SKILLS)
        self.assertFalse(any(prompt.strip().startswith("/") for prompt in prompts))

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


if __name__ == "__main__":
    unittest.main()
