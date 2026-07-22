#!/usr/bin/env python3
"""Validate the live EZPowers plugin surface without installing either plugin."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from typing import Any, Iterable


RETAINED_SKILLS = frozenset(
    {
        "setup",
        "deep-interview",
        "design-architecture",
        "spec",
        "prepare-execute",
        "execute",
        "frontend-design",
        "improve-codebase-architecture",
        "hud",
    }
)

EXPLICIT_ONLY_SKILLS = frozenset(
    {
        "setup",
        "design-architecture",
        "spec",
        "prepare-execute",
        "execute",
        "hud",
    }
)

IMPLICIT_SKILLS = RETAINED_SKILLS - EXPLICIT_ONLY_SKILLS

REMOVED_COMPONENTS = frozenset(
    {
        "caveman",
        "choice-execute",
        "deploy",
        "diagnose",
        "grill-with-docs",
        "handoff",
        "maintain",
        "reset-setup",
        "review",
        "set-rules",
        "sync-docs",
        "verifyself",
        "writing-skills",
        "zoom-out",
    }
)

CODEX_VERSION_RE = re.compile(r"^5\.0\.2\+codex\.[0-9]{14}$")
SKILL_REFERENCE_RE = re.compile(r"\$ezpowers:([a-z0-9-]+)")


def _check(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def _read_json(path: Path, errors: list[str]) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        errors.append(f"missing JSON file: {path}")
        return None
    except json.JSONDecodeError as exc:
        errors.append(f"invalid JSON in {path}: {exc}")
        return None

    if not isinstance(value, dict):
        errors.append(f"JSON root must be an object: {path}")
        return None
    return value


def _frontmatter(path: Path, errors: list[str]) -> dict[str, str] | None:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        errors.append(f"missing skill document: {path}")
        return None

    if not lines or lines[0].strip() != "---":
        errors.append(f"missing YAML frontmatter: {path}")
        return None

    try:
        end = next(index for index, line in enumerate(lines[1:], 1) if line.strip() == "---")
    except StopIteration:
        errors.append(f"unterminated YAML frontmatter: {path}")
        return None

    result: dict[str, str] = {}
    for line in lines[1:end]:
        if not line or line[0].isspace() or ":" not in line:
            continue
        key, value = line.split(":", 1)
        result[key.strip()] = value.strip().strip("'\"")
    return result


def _allow_implicit_invocation(path: Path, errors: list[str]) -> bool | None:
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        errors.append(f"missing Codex skill metadata: {path}")
        return None

    matches = re.findall(
        r"(?m)^\s+allow_implicit_invocation:\s*(true|false)\s*$",
        text,
    )
    if len(matches) > 1:
        errors.append(f"duplicate allow_implicit_invocation policy: {path}")
        return None
    if not matches:
        return None
    return matches[0] == "true"


def _validate_skill_inventory(repo_root: Path, hosts: set[str], errors: list[str]) -> None:
    skills_root = repo_root / "skills"
    if not skills_root.is_dir():
        errors.append(f"missing skills directory: {skills_root}")
        return

    live_skills = {child.name for child in skills_root.iterdir() if child.is_dir()}
    _check(
        live_skills == RETAINED_SKILLS,
        "live skill inventory differs from retained surface: "
        f"expected={sorted(RETAINED_SKILLS)}, actual={sorted(live_skills)}",
        errors,
    )

    for removed in sorted(REMOVED_COMPONENTS):
        _check(
            not (skills_root / removed).exists(),
            f"removed skill directory remains: skills/{removed}",
            errors,
        )

    for name in sorted(RETAINED_SKILLS):
        skill_root = skills_root / name
        metadata = _frontmatter(skill_root / "SKILL.md", errors)
        if metadata is not None:
            _check(
                metadata.get("name") == name,
                f"skill frontmatter name must match directory: skills/{name}",
                errors,
            )
            _check(
                bool(metadata.get("description")),
                f"skill description is required: skills/{name}",
                errors,
            )

            if "claude" in hosts:
                disabled = metadata.get("disable-model-invocation", "false").lower()
                expected = "true" if name in EXPLICIT_ONLY_SKILLS else "false"
                _check(
                    disabled == expected,
                    "Claude invocation policy mismatch for "
                    f"skills/{name}: expected disable-model-invocation={expected}",
                    errors,
                )

        if "codex" in hosts:
            policy_path = skill_root / "agents" / "openai.yaml"
            policy = _allow_implicit_invocation(policy_path, errors)
            if name in EXPLICIT_ONLY_SKILLS:
                _check(
                    policy is False,
                    "Codex explicit-only skill must set "
                    f"allow_implicit_invocation: false: skills/{name}",
                    errors,
                )
            else:
                _check(
                    policy is not False,
                    "Codex implicit skill must not disable implicit invocation: "
                    f"skills/{name}",
                    errors,
                )

    agents_root = repo_root / "agents"
    agent_files = list(agents_root.rglob("*")) if agents_root.exists() else []
    _check(
        not any(path.is_file() for path in agent_files),
        "removed plugin agents remain under agents/",
        errors,
    )
    _check(
        not (repo_root / "hooks" / "hooks.json").exists(),
        "removed plugin hook remains at hooks/hooks.json",
        errors,
    )


def _validate_no_removed_references(
    value: dict[str, Any], path: Path, errors: list[str]
) -> None:
    serialized = json.dumps(value, ensure_ascii=False)
    for name in sorted(REMOVED_COMPONENTS):
        _check(
            name not in serialized,
            f"removed component {name!r} is still advertised by {path}",
            errors,
        )


def _validate_claude_manifest(repo_root: Path, errors: list[str]) -> None:
    manifest_path = repo_root / ".claude-plugin" / "plugin.json"
    marketplace_path = repo_root / ".claude-plugin" / "marketplace.json"
    manifest = _read_json(manifest_path, errors)
    marketplace = _read_json(marketplace_path, errors)
    if manifest is None or marketplace is None:
        return

    _check(manifest.get("name") == "ezpowers", "Claude plugin name must be ezpowers", errors)
    _check(manifest.get("version") == "5.0.2", "Claude plugin version must be 5.0.2", errors)
    _check(bool(manifest.get("description")), "Claude plugin description is required", errors)
    _check(isinstance(manifest.get("author"), dict), "Claude plugin author must be an object", errors)
    for forbidden in ("agents", "commands", "hooks"):
        _check(forbidden not in manifest, f"Claude manifest must not declare {forbidden}", errors)
    _validate_no_removed_references(manifest, manifest_path, errors)

    _check(marketplace.get("name") == "ezpowers-dev", "marketplace name must be ezpowers-dev", errors)
    _check(bool(marketplace.get("description")), "marketplace top-level description is required", errors)
    plugins = marketplace.get("plugins")
    _check(isinstance(plugins, list) and len(plugins) == 1, "marketplace must contain one plugin", errors)
    if isinstance(plugins, list) and len(plugins) == 1 and isinstance(plugins[0], dict):
        entry = plugins[0]
        _check(entry.get("name") == manifest.get("name"), "marketplace plugin name drift", errors)
        _check(entry.get("version") == manifest.get("version"), "marketplace plugin version drift", errors)
        _check(entry.get("description") == manifest.get("description"), "marketplace description drift", errors)
        _check(entry.get("source") == "./", "marketplace source must be ./", errors)
    _validate_no_removed_references(marketplace, marketplace_path, errors)


def _validate_codex_manifest(repo_root: Path, errors: list[str]) -> None:
    manifest_path = repo_root / ".codex-plugin" / "plugin.json"
    marketplace_path = repo_root / ".agents" / "plugins" / "marketplace.json"
    manifest = _read_json(manifest_path, errors)
    marketplace = _read_json(marketplace_path, errors)
    if manifest is None or marketplace is None:
        return

    _check(manifest.get("name") == "ezpowers", "Codex plugin name must be ezpowers", errors)
    version = manifest.get("version")
    _check(
        isinstance(version, str) and CODEX_VERSION_RE.fullmatch(version) is not None,
        "Codex version must be 5.0.2 with exactly one timestamped +codex suffix",
        errors,
    )
    _check(manifest.get("skills") == "./skills/", "Codex skills root must be ./skills/", errors)
    for forbidden in ("agents", "commands", "hooks"):
        _check(forbidden not in manifest, f"Codex manifest must not declare {forbidden}", errors)

    interface = manifest.get("interface")
    _check(isinstance(interface, dict), "Codex interface must be an object", errors)
    if isinstance(interface, dict):
        prompts = interface.get("defaultPrompt")
        _check(
            isinstance(prompts, list) and all(isinstance(item, str) for item in prompts),
            "Codex defaultPrompt must be a list of strings",
            errors,
        )
        if isinstance(prompts, list) and all(isinstance(item, str) for item in prompts):
            _check(
                not any(item.strip().startswith("/") for item in prompts),
                "Codex default prompts must use skill invocation, not slash commands",
                errors,
            )
            prompt_refs = set(SKILL_REFERENCE_RE.findall("\n".join(prompts)))
            _check(
                prompt_refs == {"setup", "deep-interview", "execute", "hud"},
                "Codex default prompts must advertise setup, deep-interview, execute, and hud",
                errors,
            )

        long_description = interface.get("longDescription", "")
        described = set(re.findall(r"ezpowers:([a-z0-9-]+)", str(long_description)))
        _check(
            described == RETAINED_SKILLS,
            "Codex longDescription must enumerate exactly the retained nine skills",
            errors,
        )

    _validate_no_removed_references(manifest, manifest_path, errors)

    _check(
        marketplace.get("name") == "ezpowers-dev",
        "Codex repository marketplace name must be ezpowers-dev",
        errors,
    )
    marketplace_interface = marketplace.get("interface")
    _check(
        isinstance(marketplace_interface, dict)
        and bool(marketplace_interface.get("displayName")),
        "Codex repository marketplace requires interface.displayName",
        errors,
    )
    entries = marketplace.get("plugins")
    _check(
        isinstance(entries, list) and len(entries) == 1,
        "Codex repository marketplace must contain one plugin",
        errors,
    )
    if isinstance(entries, list) and len(entries) == 1 and isinstance(entries[0], dict):
        entry = entries[0]
        source = entry.get("source")
        policy = entry.get("policy")
        _check(entry.get("name") == "ezpowers", "Codex marketplace plugin name drift", errors)
        _check(
            source == {"source": "local", "path": "./"},
            "Codex marketplace source must be the local plugin root",
            errors,
        )
        _check(
            policy == {"installation": "AVAILABLE", "authentication": "ON_INSTALL"},
            "Codex marketplace install policy drift",
            errors,
        )
        _check(entry.get("category") == "Productivity", "Codex marketplace category drift", errors)
    _validate_no_removed_references(marketplace, marketplace_path, errors)


def validate_repository(repo_root: Path, hosts: Iterable[str]) -> list[str]:
    """Return validation errors for the selected host surfaces."""

    selected = set(hosts)
    errors: list[str] = []
    _validate_skill_inventory(repo_root, selected, errors)
    if "claude" in selected:
        _validate_claude_manifest(repo_root, errors)
    if "codex" in selected:
        _validate_codex_manifest(repo_root, errors)
    return errors


def _run_command(
    command: list[str], *, cwd: Path, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=45,
        check=False,
    )


def _probe_claude(repo_root: Path) -> tuple[str, str]:
    executable = shutil.which("claude")
    if executable is None:
        return "skip", "Claude CLI is not installed"

    for relative_path in (
        Path(".claude-plugin") / "plugin.json",
        Path(".claude-plugin") / "marketplace.json",
    ):
        try:
            result = _run_command(
                [executable, "plugin", "validate", str(repo_root / relative_path)],
                cwd=repo_root,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            return "fail", f"Claude CLI validation probe failed to run: {exc}"

        output = "\n".join(
            part for part in (result.stdout, result.stderr) if part
        ).strip()
        if result.returncode != 0:
            return (
                "fail",
                f"Claude CLI rejected {relative_path}: {output or 'no output'}",
            )
    return "pass", "Claude CLI accepted the plugin and marketplace manifests"


def _probe_codex(repo_root: Path) -> tuple[str, str]:
    executable = shutil.which("codex")
    if executable is None:
        return "skip", "Codex CLI is not installed"

    with tempfile.TemporaryDirectory(prefix="ezpowers-plugin-smoke-") as temp_name:
        temp_root = Path(temp_name)
        project_root = temp_root / "project"
        project_root.mkdir()
        initialized = _run_command(["git", "init", "-q"], cwd=project_root)
        if initialized.returncode != 0:
            return "fail", f"cannot initialize discovery fixture: {initialized.stderr.strip()}"
        installer = repo_root / "scripts" / "ezpowers.py"
        installed = _run_command(
            [
                sys.executable,
                str(installer),
                "install",
                "--project-root",
                str(project_root),
            ],
            cwd=repo_root,
        )
        if installed.returncode != 0:
            output = "\n".join(
                part for part in (installed.stdout, installed.stderr) if part
            ).strip()
            return "fail", f"project-kit install failed before Codex discovery: {output}"

        codex_home = temp_root / "codex-home"
        codex_home.mkdir()
        env = os.environ.copy()
        env["CODEX_HOME"] = str(codex_home)
        try:
            result = _run_command(
                [executable, "debug", "prompt-input", "EZPowers discovery probe"],
                cwd=project_root,
                env=env,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            return "fail", f"Codex discovery probe failed to run: {exc}"

    output = "\n".join(part for part in (result.stdout, result.stderr) if part).strip()
    lowered = output.lower()
    if result.returncode != 0:
        unsupported = "unrecognized subcommand" in lowered or "unknown subcommand" in lowered
        if unsupported:
            return "skip", "installed Codex CLI has no prompt-input discovery probe"
        return "fail", f"Codex discovery probe failed: {output or 'no output'}"

    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        return "fail", f"Codex discovery probe returned invalid JSON: {exc}"

    messages = payload if isinstance(payload, list) else [payload]
    skill_sections: list[str] = []
    for message in messages:
        if not isinstance(message, dict):
            continue
        for content in message.get("content", []):
            if not isinstance(content, dict):
                continue
            candidate = content.get("text")
            if isinstance(candidate, str) and "<skills_instructions>" in candidate:
                skill_sections.append(candidate)

    discovered = set()
    for section in skill_sections:
        discovered.update(re.findall(r"(?m)^- ([a-z0-9:-]+):\s", section))
    discovered_names = {name.rsplit(":", 1)[-1] for name in discovered}
    missing = sorted(IMPLICIT_SKILLS - discovered_names)
    removed = sorted(REMOVED_COMPONENTS & discovered_names)
    if missing:
        return "fail", f"Codex did not discover implicit skills: {', '.join(missing)}"
    if removed:
        return "fail", f"Codex discovered removed skills: {', '.join(removed)}"
    return "pass", "Codex discovered the retained implicit project skills in isolation"


def run_host_probes(repo_root: Path, hosts: Iterable[str]) -> list[str]:
    errors: list[str] = []
    probes = {"claude": _probe_claude, "codex": _probe_codex}
    for host in hosts:
        status, message = probes[host](repo_root)
        print(f"[{status.upper()}] {message}")
        if status == "fail":
            errors.append(message)
    return errors


def _selected_hosts(value: str) -> tuple[str, ...]:
    return ("claude", "codex") if value == "both" else (value,)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--host",
        choices=("claude", "codex", "both"),
        default="both",
        help="host surface to validate (default: both)",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--skip-host-probes",
        action="store_true",
        help="validate files only; intended for deterministic unit tests",
    )
    args = parser.parse_args(argv)

    repo_root = args.repo_root.resolve()
    hosts = _selected_hosts(args.host)
    errors = validate_repository(repo_root, hosts)
    if not errors:
        print(f"[PASS] {args.host} plugin files match the retained EZPowers surface")
        if not args.skip_host_probes:
            errors.extend(run_host_probes(repo_root, hosts))

    if errors:
        for error in errors:
            print(f"[FAIL] {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
