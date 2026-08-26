from __future__ import annotations

import hashlib
import importlib.util
import json
import pathlib
import subprocess
import tempfile
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
VERIFIER_PATH = REPO_ROOT / "scripts" / "verify-harness-kit.py"
MANIFEST_PATH = REPO_ROOT / "project-kit" / "v5.7.0" / "manifest.json"


def load_verifier():
    spec = importlib.util.spec_from_file_location(
        "ezpowers_verify_harness_kit",
        VERIFIER_PATH,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {VERIFIER_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_runtime_manifest(root: pathlib.Path, source_bytes: bytes) -> pathlib.Path:
    source = root / "scripts" / "ezpowers.py"
    source.parent.mkdir(parents=True)
    source.write_bytes(source_bytes)
    manifest_path = root / "project-kit" / "v5.7.0" / "manifest.json"
    manifest_path.parent.mkdir(parents=True)
    manifest_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "version": "5.7.0",
                "no_synthesis": True,
                "runtime": {
                    "source": "scripts/ezpowers.py",
                    "target": ".ezpowers/ezpowers.py",
                    "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                },
                "tools": [],
                "skills": [],
                "contracts": [],
            }
        ),
        encoding="utf-8",
    )
    return manifest_path


class HarnessKitDistributionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.verifier = load_verifier()

    def test_validator_rejects_non_lf_manifest_sources(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = pathlib.Path(temp_dir)
            manifest_path = write_runtime_manifest(root, b"first\r\nsecond\n")

            errors = self.verifier.validate(root, manifest_path)

            self.assertIn(
                "source must use LF-only line endings: scripts/ezpowers.py",
                errors,
            )

    def test_stamp_rejects_non_lf_manifest_sources(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = pathlib.Path(temp_dir)
            manifest_path = write_runtime_manifest(root, b"first\r\nsecond\n")

            with self.assertRaisesRegex(
                SystemExit,
                "cannot stamp source with non-LF line endings: scripts/ezpowers.py",
            ):
                self.verifier.stamp(root, manifest_path)

    def test_manifest_sources_are_lf_only_and_hash_exactly(self) -> None:
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        offenders: list[str] = []
        mismatches: list[str] = []
        for entry in self.verifier.source_entries(manifest):
            source_name = entry["source"]
            data = (REPO_ROOT / source_name).read_bytes()
            if b"\r" in data:
                offenders.append(source_name)
            if hashlib.sha256(data).hexdigest() != entry["sha256"]:
                mismatches.append(source_name)

        self.assertEqual(offenders, [])
        self.assertEqual(mismatches, [])

    def test_git_attributes_force_lf_for_every_manifest_source(self) -> None:
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        sources = [entry["source"] for entry in self.verifier.source_entries(manifest)]
        result = subprocess.run(
            ["git", "check-attr", "eol", "--", *sources],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        attributes: dict[str, str] = {}
        for line in result.stdout.splitlines():
            source_name, attribute, value = line.rsplit(": ", 2)
            self.assertEqual(attribute, "eol")
            attributes[source_name] = value

        self.assertEqual(set(attributes), set(sources))
        self.assertEqual(
            [source for source in sources if attributes[source] != "lf"],
            [],
        )


if __name__ == "__main__":
    unittest.main()
