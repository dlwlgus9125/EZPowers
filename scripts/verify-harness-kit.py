#!/usr/bin/env python3
"""Validate the bundled EZPowers harness kit manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys


WORKFLOW_SKILL_DIRS = {
    "setup": "setup",
    "design_architecture": "design-architecture",
    "spec": "spec",
    "prepare_execute": "prepare-execute",
    "choice_execute": "choice-execute",
    "maintain": "maintain",
    "deploy": "deploy",
    "reset_setup": "reset-setup",
}


def workflow_doc_path(repo_root, command):
    return repo_root / "skills" / WORKFLOW_SKILL_DIRS.get(command, command) / "SKILL.md"


REQUIRED_COMMANDS = {
    "setup",
    "design_architecture",
    "spec",
    "prepare_execute",
    "choice_execute",
    "maintain",
    "deploy",
    "reset_setup",
}

REMOVED_PUBLIC_COMMANDS = {
    "brainstorm",
    "plan",
    "choiceexecutor",
    "executeharness",
    "pipeline-audit",
}

REQUIRED_UI_CAPABILITIES = {
    "browser-e2e",
    "component-dom",
    "framework-headless",
    "desktop-gui",
    "mobile-emulator",
    "cli-tui",
    "custom",
}

REQUIRED_HELPER_TARGETS = {
    "scripts/context-injector.py",
    "scripts/frontend-visual-readiness.py",
    "scripts/harness-certify.ps1",
    "scripts/harness-common.ps1",
    "scripts/harness-convert.ps1",
    "scripts/harness-doctor.ps1",
    "scripts/harness-gate.ps1",
    "scripts/harness-phase.ps1",
    "scripts/harness-resume-proof.ps1",
    "scripts/harness-run.ps1",
    "scripts/hashline-anchor.py",
    "scripts/lightpath-gate.ps1",
    "scripts/model-router.py",
    "scripts/verify-step.py",
}


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def stamp(repo_root: pathlib.Path, manifest_path: pathlib.Path) -> None:
    """Compute and persist the sha256 of every bundled source file into the manifest."""
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for item in manifest.get("source_files", []):
        source = repo_root / item.get("source", "")
        # The manifest lists itself; it cannot carry a hash of its own content
        # (writing the hash would change the bytes the hash was taken over).
        if source.resolve() == manifest_path.resolve():
            item.pop("sha256", None)
            continue
        if not source.exists():
            raise SystemExit(f"ERROR: cannot stamp missing source file: {item.get('source')}")
        item["sha256"] = sha256(source)
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def validate(repo_root: pathlib.Path, manifest_path: pathlib.Path) -> list[str]:
    errors: list[str] = []
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    if manifest.get("no_synthesis") is not True:
        errors.append("manifest no_synthesis must be true")
    if manifest.get("install_root") != ".harness/ezpowers":
        errors.append("install_root must be .harness/ezpowers")

    commands = set(manifest.get("public_commands", []))
    missing_commands = REQUIRED_COMMANDS - commands
    if missing_commands:
        errors.append(f"missing public commands: {sorted(missing_commands)}")

    removed_commands = REMOVED_PUBLIC_COMMANDS & commands
    if removed_commands:
        errors.append(f"removed public commands still listed: {sorted(removed_commands)}")

    for command in REQUIRED_COMMANDS:
        command_path = workflow_doc_path(repo_root, command)
        if not command_path.exists():
            errors.append(f"missing command file: {command_path.relative_to(repo_root)}")

    for adapter in manifest.get("internal_adapters", []):
        if not (repo_root / adapter).exists():
            errors.append(f"missing internal adapter: {adapter}")

    capabilities = set(manifest.get("ui_verification", {}).get("capabilities", []))
    missing_capabilities = REQUIRED_UI_CAPABILITIES - capabilities
    if missing_capabilities:
        errors.append(f"missing UI capabilities: {sorted(missing_capabilities)}")
    if manifest.get("ui_verification", {}).get("adapter_fallback_task_required") is not True:
        errors.append("ui_verification.adapter_fallback_task_required must be true")

    source_file_targets = set()
    for item in manifest.get("source_files", []):
        source = repo_root / item.get("source", "")
        target = item.get("target", "")
        source_file_targets.add(target)
        if not source.exists():
            errors.append(f"missing source file: {source.relative_to(repo_root)}")
            continue
        if not target.startswith(".harness/ezpowers/") and target not in REQUIRED_HELPER_TARGETS:
            errors.append(f"target outside install root or helper allowlist: {target}")
        if source.name == "SKILL.md":
            errors.append("source_files must not include synthesized SKILL.md")
        # The manifest cannot verify a hash of its own content (see stamp()).
        if source.resolve() == manifest_path.resolve():
            continue
        expected = item.get("sha256")
        if not expected:
            errors.append(
                f"missing sha256 for source file {item.get('source')}; "
                "run: python scripts/verify-harness-kit.py --stamp"
            )
        elif sha256(source) != expected:
            errors.append(f"sha256 mismatch for source file: {item.get('source')}")

    missing_helpers = REQUIRED_HELPER_TARGETS - source_file_targets
    if missing_helpers:
        errors.append(f"missing helper script targets: {sorted(missing_helpers)}")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".", help="Repository root")
    parser.add_argument(
        "--manifest",
        default="harness-kit/v2.0.0/manifest.json",
        help="Manifest path relative to repo root",
    )
    parser.add_argument(
        "--stamp",
        action="store_true",
        help="Compute and write sha256 hashes of bundled source files into the manifest",
    )
    args = parser.parse_args()

    repo_root = pathlib.Path(args.repo_root).resolve()
    manifest_path = repo_root / args.manifest
    if args.stamp:
        stamp(repo_root, manifest_path)
        print(f"Stamped sha256 hashes into {args.manifest}")
        return 0
    errors = validate(repo_root, manifest_path)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print("Harness kit manifest valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
