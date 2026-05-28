import json
import pathlib
import re
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]


class CodexPluginDiscoveryTests(unittest.TestCase):
    def test_codex_manifest_exposes_supported_skill_surface(self):
        manifest = json.loads(
            (REPO_ROOT / ".codex-plugin/plugin.json").read_text(encoding="utf-8")
        )

        self.assertEqual("./skills/", manifest.get("skills"))
        self.assertNotIn("commands", manifest)

        prompts = manifest["interface"]["defaultPrompt"]
        prompt_text = "\n".join(prompts)
        self.assertIn("$ezpowers:", prompt_text)
        self.assertNotIn("/setup", prompt_text)
        self.assertFalse(any(prompt.strip().startswith("/") for prompt in prompts))

        skills = {
            path.name
            for path in (REPO_ROOT / "skills").iterdir()
            if (path / "SKILL.md").exists()
        }
        referenced = set(re.findall(r"\$ezpowers:([a-z0-9-]+)", prompt_text))
        self.assertTrue(referenced)
        self.assertLessEqual(referenced, skills)

    def test_codex_discovery_reference_is_indexed(self):
        reference = REPO_ROOT / "docs/reference/codex-plugin-discovery.md"
        index = (REPO_ROOT / "docs/INDEX.md").read_text(encoding="utf-8")
        text = reference.read_text(encoding="utf-8")

        self.assertIn("reference/codex-plugin-discovery.md", index)
        self.assertIn("`ezpowers:diagnose`", text)
        self.assertIn("does not imply that Codex will list", text)
        self.assertIn("duplicate skill entries", text)


if __name__ == "__main__":
    unittest.main()
