#!/usr/bin/env python3
"""Validate or stamp the self-contained EZPowers v5 project-kit manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re


VERSION = "5.0.0"
MANIFEST = "project-kit/v5.0.0/manifest.json"
PROJECT_SKILLS = {
    "setup",
    "deep-interview",
    "design-architecture",
    "spec",
    "prepare-execute",
    "execute",
    "frontend-design",
    "improve-codebase-architecture",
}
CONTRACT_TARGETS = {
    ".ezpowers/contracts/setup-contract.md",
    ".ezpowers/contracts/design-architecture-contract.md",
    ".ezpowers/contracts/frontend-design-contract.md",
    ".ezpowers/contracts/spec-contract.md",
    ".ezpowers/contracts/plan-contract.md",
    ".ezpowers/contracts/verification-contract.md",
}
HASH_RE = re.compile(r"^[0-9a-f]{64}$")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def safe_relative(value: object) -> bool:
    if not isinstance(value, str) or not value:
        return False
    path = PurePosixPath(value.replace("\\", "/"))
    return not path.is_absolute() and ".." not in path.parts


def source_entries(manifest: dict) -> list[dict]:
    entries: list[dict] = []
    runtime = manifest.get("runtime")
    if isinstance(runtime, dict):
        entries.append(runtime)
    for section in ("tools", "contracts"):
        values = manifest.get(section, [])
        if isinstance(values, list):
            entries.extend(item for item in values if isinstance(item, dict))
    skills = manifest.get("skills", [])
    if isinstance(skills, list):
        for skill in skills:
            if isinstance(skill, dict) and isinstance(skill.get("files"), list):
                entries.extend(item for item in skill["files"] if isinstance(item, dict))
    return entries


def stamp(repo_root: Path, manifest_path: Path) -> None:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for item in source_entries(manifest):
        source_name = item.get("source")
        if not safe_relative(source_name):
            raise SystemExit(f"ERROR: unsafe source path: {source_name!r}")
        source = repo_root / source_name
        if not source.is_file():
            raise SystemExit(f"ERROR: cannot stamp missing source: {source_name}")
        item["sha256"] = sha256(source)
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def validate(repo_root: Path, manifest_path: Path) -> list[str]:
    errors: list[str] = []
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"invalid manifest: {exc}"]

    if manifest.get("schema_version") != 1:
        errors.append("schema_version must be 1")
    if manifest.get("version") != VERSION:
        errors.append(f"version must be {VERSION}")
    if manifest.get("no_synthesis") is not True:
        errors.append("no_synthesis must be true")

    runtime = manifest.get("runtime")
    if not isinstance(runtime, dict):
        errors.append("runtime must be an object")
    elif runtime.get("source") != "scripts/ezpowers.py" or runtime.get("target") != ".ezpowers/ezpowers.py":
        errors.append("runtime must install scripts/ezpowers.py as .ezpowers/ezpowers.py")

    skills = manifest.get("skills")
    skill_names = {
        item.get("name") for item in skills if isinstance(item, dict)
    } if isinstance(skills, list) else set()
    if skill_names != PROJECT_SKILLS:
        errors.append(
            f"project skill inventory mismatch: expected={sorted(PROJECT_SKILLS)}, actual={sorted(str(name) for name in skill_names)}"
        )
    if isinstance(skills, list):
        for item in skills:
            if not isinstance(item, dict):
                errors.append("skill entries must be objects")
                continue
            files = item.get("files")
            paths = {entry.get("path") for entry in files if isinstance(entry, dict)} if isinstance(files, list) else set()
            if "SKILL.md" not in paths:
                errors.append(f"skill {item.get('name')!r} must include SKILL.md")
            if "agents/openai.yaml" not in paths:
                errors.append(f"skill {item.get('name')!r} must include agents/openai.yaml")

    contract_targets = {
        item.get("target") for item in manifest.get("contracts", []) if isinstance(item, dict)
    } if isinstance(manifest.get("contracts"), list) else set()
    if contract_targets != CONTRACT_TARGETS:
        errors.append(
            f"contract target mismatch: expected={sorted(CONTRACT_TARGETS)}, actual={sorted(str(name) for name in contract_targets)}"
        )

    tools = manifest.get("tools")
    expected_tool = {
        ("scripts/frontend-visual-readiness.py", ".ezpowers/tools/frontend-visual-readiness.py")
    }
    actual_tools = {
        (item.get("source"), item.get("target"))
        for item in tools
        if isinstance(item, dict)
    } if isinstance(tools, list) else set()
    if actual_tools != expected_tool:
        errors.append("tools must install only frontend-visual-readiness.py under .ezpowers/tools")

    seen_sources: set[str] = set()
    for item in source_entries(manifest):
        source_name = item.get("source")
        if not safe_relative(source_name):
            errors.append(f"unsafe source path: {source_name!r}")
            continue
        if source_name in seen_sources:
            errors.append(f"duplicate source entry: {source_name}")
        seen_sources.add(source_name)
        source = repo_root / source_name
        if not source.is_file():
            errors.append(f"missing source file: {source_name}")
            continue
        expected = item.get("sha256")
        if not isinstance(expected, str) or HASH_RE.fullmatch(expected) is None:
            errors.append(f"missing or invalid sha256: {source_name}")
        elif sha256(source) != expected:
            errors.append(f"sha256 mismatch: {source_name}")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--manifest", default=MANIFEST)
    parser.add_argument("--stamp", action="store_true")
    args = parser.parse_args()
    repo_root = Path(args.repo_root).resolve()
    manifest_path = repo_root / args.manifest
    if args.stamp:
        stamp(repo_root, manifest_path)
        print(f"Stamped project kit manifest: {args.manifest}")
        return 0
    errors = validate(repo_root, manifest_path)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("EZPowers v5 project kit manifest valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
