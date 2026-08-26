#!/usr/bin/env python3
"""Validate or stamp the self-contained EZPowers v5.7 project-kit manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import subprocess


VERSION = "5.7.0"
MANIFEST = "project-kit/v5.7.0/manifest.json"
PROJECT_SKILLS = {
    "codebase-design",
    "setup",
    "deep-interview",
    "design-architecture",
    "diagnose",
    "explain-with-evidence",
    "spec",
    "prepare-execute",
    "execute",
    "frontend-design",
    "wiki",
    "harness-chain",
    "improve-codebase-architecture",
}
CONTRACT_TARGETS = {
    ".ezpowers/contracts/setup-contract.md",
    ".ezpowers/contracts/design-architecture-contract.md",
    ".ezpowers/contracts/frontend-design-contract.md",
    ".ezpowers/contracts/spec-contract.md",
    ".ezpowers/contracts/plan-contract.md",
    ".ezpowers/contracts/verification-contract.md",
    ".ezpowers/contracts/documentation-contract.md",
    ".ezpowers/contracts/wiki-contract.md",
    ".ezpowers/contracts/harness-chain-contract.md",
    ".ezpowers/contracts/engineering-practices-contract.md",
    ".ezpowers/contracts/design-md-profile.json",
}
HASH_RE = re.compile(r"^[0-9a-f]{64}$")


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


def git_eol_errors(repo_root: Path, source_names: list[str]) -> list[str]:
    if not (repo_root / ".git").exists() or not source_names:
        return []
    try:
        result = subprocess.run(
            ["git", "check-attr", "eol", "--", *source_names],
            cwd=repo_root,
            text=True,
            capture_output=True,
            check=False,
        )
    except OSError as exc:
        return [f"cannot verify Git eol attributes: {exc}"]
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "no output"
        return [f"cannot verify Git eol attributes: {detail}"]

    attributes: dict[str, str] = {}
    for line in result.stdout.splitlines():
        parts = line.rsplit(": ", 2)
        if len(parts) != 3 or parts[1] != "eol":
            return [f"cannot parse Git eol attribute output: {line!r}"]
        attributes[parts[0]] = parts[2]
    return [
        f"Git eol attribute must be lf: {source_name} "
        f"(found {attributes.get(source_name, 'missing')})"
        for source_name in source_names
        if attributes.get(source_name) != "lf"
    ]


def stamp(repo_root: Path, manifest_path: Path) -> None:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    sources: list[tuple[dict, str, Path]] = []
    for item in source_entries(manifest):
        source_name = item.get("source")
        if not safe_relative(source_name):
            raise SystemExit(f"ERROR: unsafe source path: {source_name!r}")
        source = repo_root / source_name
        if not source.is_file():
            raise SystemExit(f"ERROR: cannot stamp missing source: {source_name}")
        sources.append((item, source_name, source))
    attribute_errors = git_eol_errors(
        repo_root,
        [source_name for _, source_name, _ in sources],
    )
    if attribute_errors:
        raise SystemExit("\n".join(f"ERROR: {error}" for error in attribute_errors))
    for item, source_name, source in sources:
        data = source.read_bytes()
        if b"\r" in data:
            raise SystemExit(
                f"ERROR: cannot stamp source with non-LF line endings: {source_name}"
            )
        item["sha256"] = hashlib.sha256(data).hexdigest()
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
            metadata = next(
                (
                    entry
                    for entry in files
                    if isinstance(entry, dict)
                    and entry.get("path") == "agents/openai.yaml"
                ),
                None,
            ) if isinstance(files, list) else None
            expected_metadata = (
                f"skills/{item.get('name')}/agents/project-openai.yaml"
            )
            if not isinstance(metadata, dict) or metadata.get("source") != expected_metadata:
                errors.append(
                    f"skill {item.get('name')!r} must install project-local "
                    f"metadata from {expected_metadata}"
                )

    contract_targets = {
        item.get("target") for item in manifest.get("contracts", []) if isinstance(item, dict)
    } if isinstance(manifest.get("contracts"), list) else set()
    if contract_targets != CONTRACT_TARGETS:
        errors.append(
            f"contract target mismatch: expected={sorted(CONTRACT_TARGETS)}, actual={sorted(str(name) for name in contract_targets)}"
        )

    tools = manifest.get("tools")
    expected_tool = {
        ("scripts/frontend-visual-readiness.py", ".ezpowers/tools/frontend-visual-readiness.py"),
        ("scripts/architecture-review-report.py", ".ezpowers/tools/architecture-review-report.py"),
        ("scripts/design-md.py", ".ezpowers/tools/design-md.py"),
    }
    actual_tools = {
        (item.get("source"), item.get("target"))
        for item in tools
        if isinstance(item, dict)
    } if isinstance(tools, list) else set()
    if actual_tools != expected_tool:
        errors.append(
            "tools must install frontend-visual-readiness.py, "
            "architecture-review-report.py, and design-md.py under .ezpowers/tools"
        )

    entries = source_entries(manifest)
    safe_source_names = [
        source_name
        for item in entries
        if isinstance((source_name := item.get("source")), str)
        and safe_relative(source_name)
    ]
    errors.extend(git_eol_errors(repo_root, safe_source_names))

    seen_sources: set[str] = set()
    for item in entries:
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
        data = source.read_bytes()
        if b"\r" in data:
            errors.append(f"source must use LF-only line endings: {source_name}")
        if not isinstance(expected, str) or HASH_RE.fullmatch(expected) is None:
            errors.append(f"missing or invalid sha256: {source_name}")
        elif hashlib.sha256(data).hexdigest() != expected:
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
    print("EZPowers v5.7 project kit manifest valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
