#!/usr/bin/env python3
"""Validate the EZPowers plugin surface in isolated host fixtures."""

from __future__ import annotations

import argparse
import contextlib
import json
import os
from pathlib import Path
import queue
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from typing import Any, Iterable


PLUGIN_SKILLS = frozenset(
    {
        "setup",
        "deep-interview",
        "design-architecture",
        "spec",
        "prepare-execute",
        "execute",
        "frontend-design",
        "hud",
        "wiki",
        "harness-chain",
    }
)
PROJECT_SKILLS = PLUGIN_SKILLS - {"hud"}
# Kept as a compatibility alias for callers that import the repository validator.
RETAINED_SKILLS = PLUGIN_SKILLS

EXPLICIT_ONLY_SKILLS = frozenset(
    {
        "setup",
        "design-architecture",
        "spec",
        "prepare-execute",
        "execute",
        "hud",
        "harness-chain",
    }
)

IMPLICIT_SKILLS = PLUGIN_SKILLS - EXPLICIT_ONLY_SKILLS

REMOVED_COMPONENTS = frozenset(
    {
        "caveman",
        "choice-execute",
        "deploy",
        "diagnose",
        "grill-with-docs",
        "handoff",
        "improve-codebase-architecture",
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

CODEX_VERSION_RE = re.compile(r"^5\.2\.0\+codex\.[0-9]{14}$")
SKILL_REFERENCE_RE = re.compile(r"\$ezpowers:([a-z0-9-]+)")
HOST_MIN_VERSIONS = {
    "claude": (2, 1, 217),
    "codex": (0, 145, 0),
}
VERSION_NUMBER_RE = re.compile(r"(?<!\d)(\d+)\.(\d+)\.(\d+)(?!\d)")


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


def _metadata_scalar(
    path: Path,
    key: str,
    errors: list[str],
) -> str | None:
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        errors.append(f"missing Codex skill metadata: {path}")
        return None
    matches = re.findall(rf"(?m)^\s+{re.escape(key)}:\s*(.+?)\s*$", text)
    if len(matches) != 1:
        errors.append(f"Codex metadata must define {key} exactly once: {path}")
        return None
    raw = matches[0]
    if raw.startswith('"') and raw.endswith('"'):
        try:
            value = json.loads(raw)
        except json.JSONDecodeError:
            errors.append(f"invalid quoted {key} in Codex metadata: {path}")
            return None
        return value if isinstance(value, str) else None
    return raw.strip("'")


def _validate_skill_inventory(repo_root: Path, hosts: set[str], errors: list[str]) -> None:
    skills_root = repo_root / "skills"
    if not skills_root.is_dir():
        errors.append(f"missing skills directory: {skills_root}")
        return

    live_skills = {child.name for child in skills_root.iterdir() if child.is_dir()}
    _check(
        live_skills == PLUGIN_SKILLS,
        "live skill inventory differs from retained surface: "
        f"expected={sorted(PLUGIN_SKILLS)}, actual={sorted(live_skills)}",
        errors,
    )

    for removed in sorted(REMOVED_COMPONENTS):
        _check(
            not (skills_root / removed).exists(),
            f"removed skill directory remains: skills/{removed}",
            errors,
        )

    for name in sorted(PLUGIN_SKILLS):
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
                    policy is True,
                    "Codex implicit skill must enable implicit invocation: "
                    f"skills/{name}",
                    errors,
                )
            plugin_prompt = _metadata_scalar(
                policy_path,
                "default_prompt",
                errors,
            )
            _check(
                isinstance(plugin_prompt, str)
                and f"$ezpowers:{name}" in plugin_prompt,
                "plugin Codex metadata must use its namespaced invocation: "
                f"skills/{name}/agents/openai.yaml",
                errors,
            )

            project_policy_path = skill_root / "agents" / "project-openai.yaml"
            if name in PROJECT_SKILLS:
                project_policy = _allow_implicit_invocation(
                    project_policy_path,
                    errors,
                )
                _check(
                    project_policy is policy,
                    f"project/plugin Codex invocation policy drift: skills/{name}",
                    errors,
                )
                for field in ("display_name", "short_description"):
                    _check(
                        _metadata_scalar(project_policy_path, field, errors)
                        == _metadata_scalar(policy_path, field, errors),
                        f"project/plugin Codex {field} drift: skills/{name}",
                        errors,
                    )
                project_prompt = _metadata_scalar(
                    project_policy_path,
                    "default_prompt",
                    errors,
                )
                _check(
                    isinstance(project_prompt, str)
                    and f"${name}" in project_prompt
                    and "$ezpowers:" not in project_prompt,
                    "project Codex metadata must use its unnamespaced invocation: "
                    f"skills/{name}/agents/project-openai.yaml",
                    errors,
                )
                if isinstance(plugin_prompt, str) and isinstance(project_prompt, str):
                    _check(
                        plugin_prompt.replace(f"$ezpowers:{name}", f"${name}")
                        == project_prompt,
                        f"project/plugin Codex default prompt drift: skills/{name}",
                        errors,
                    )
            else:
                _check(
                    not project_policy_path.exists(),
                    "plugin-only HUD must not be copied into project kits: "
                    f"{project_policy_path}",
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
        advertised = re.search(
            rf"(?:[$/]ezpowers:{re.escape(name)}\b|"
            rf"\bskills[\\/]{re.escape(name)}\b)",
            serialized,
        )
        _check(
            advertised is None,
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
    _check(manifest.get("version") == "5.2.0", "Claude plugin version must be 5.2.0", errors)
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
        "Codex version must be 5.2.0 with exactly one timestamped +codex suffix",
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
                prompt_refs == {"setup", "deep-interview", "harness-chain"},
                "Codex default prompts must advertise setup, deep-interview, and harness-chain",
                errors,
            )

        long_description = interface.get("longDescription", "")
        described = set(re.findall(r"ezpowers:([a-z0-9-]+)", str(long_description)))
        _check(
            described == PLUGIN_SKILLS,
            "Codex longDescription must enumerate exactly the retained ten skills",
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
    command: list[str],
    *,
    cwd: Path,
    env: dict[str, str] | None = None,
    timeout: int = 45,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        check=False,
    )


def _host_version(
    host: str,
    executable: str,
    repo_root: Path,
) -> tuple[bool, str]:
    try:
        result = _run_command([executable, "--version"], cwd=repo_root)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, f"cannot inspect {host} version: {exc}"
    output = "\n".join(
        part for part in (result.stdout, result.stderr) if part
    ).strip()
    match = VERSION_NUMBER_RE.search(output)
    if result.returncode != 0 or match is None:
        return False, f"cannot parse {host} version from: {output or 'no output'}"
    installed = tuple(int(part) for part in match.groups())
    minimum = HOST_MIN_VERSIONS[host]
    if installed < minimum:
        return (
            False,
            f"{host} {'.'.join(map(str, installed))} is older than required "
            f"{'.'.join(map(str, minimum))}",
        )
    return True, ".".join(map(str, installed))


def _probe_claude(repo_root: Path) -> tuple[str, str]:
    executable = shutil.which("claude")
    if executable is None:
        return "skip", "Claude CLI is not installed"
    compatible, detail = _host_version("claude", executable, repo_root)
    if not compatible:
        return "fail", detail

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
    return (
        "pass",
        f"Claude {detail} accepted the plugin and marketplace manifests",
    )


def _kill_process_tree(process: subprocess.Popen[str]) -> None:
    if process.poll() is not None:
        return
    if os.name == "nt":
        with contextlib.suppress(OSError, subprocess.TimeoutExpired):
            subprocess.run(
                ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=10,
                check=False,
            )
    else:
        process.terminate()
    with contextlib.suppress(OSError, subprocess.TimeoutExpired):
        process.wait(timeout=5)
    if process.poll() is None:
        process.kill()
        with contextlib.suppress(OSError, subprocess.TimeoutExpired):
            process.wait(timeout=5)


def _codex_skills_list(
    executable: str,
    *,
    cwd: Path,
    env: dict[str, str],
) -> tuple[dict[str, Any] | None, str | None]:
    creationflags = (
        getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        if os.name == "nt"
        else 0
    )
    try:
        process = subprocess.Popen(
            [executable, "app-server", "--listen", "stdio://"],
            cwd=cwd,
            env=env,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=creationflags,
        )
    except OSError as exc:
        return None, f"cannot start Codex app-server: {exc}"

    output_lines: queue.Queue[str | None] = queue.Queue()

    def read_stdout() -> None:
        assert process.stdout is not None
        for line in process.stdout:
            output_lines.put(line)
        output_lines.put(None)

    threading.Thread(target=read_stdout, daemon=True).start()

    def send(payload: dict[str, Any]) -> None:
        if process.stdin is None:
            raise OSError("Codex app-server stdin is unavailable")
        process.stdin.write(json.dumps(payload, ensure_ascii=False) + "\n")
        process.stdin.flush()

    def receive(response_id: int) -> dict[str, Any]:
        deadline = time.monotonic() + 30
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise subprocess.TimeoutExpired(
                    [executable, "app-server"],
                    30,
                )
            try:
                line = output_lines.get(timeout=remaining)
            except queue.Empty as exc:
                raise subprocess.TimeoutExpired(
                    [executable, "app-server"],
                    30,
                ) from exc
            if line is None:
                raise OSError("Codex app-server closed before responding")
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict) and payload.get("id") == response_id:
                return payload

    try:
        send(
            {
                "method": "initialize",
                "id": 1,
                "params": {
                    "clientInfo": {
                        "name": "ezpowers-plugin-smoke",
                        "version": "1",
                    }
                },
            }
        )
        initialized = receive(1)
        if "error" in initialized:
            return None, f"Codex app-server initialize failed: {initialized['error']}"
        send({"method": "initialized", "params": {}})
        send(
            {
                "method": "skills/list",
                "id": 2,
                "params": {
                    "cwds": [str(cwd.resolve())],
                    "forceReload": True,
                },
            }
        )
        response = receive(2)
        if "error" in response:
            return None, f"Codex skills/list failed: {response['error']}"
        data = response.get("result", {}).get("data")
        if not isinstance(data, list) or len(data) != 1 or not isinstance(data[0], dict):
            return None, "Codex skills/list returned an unexpected result shape"
        return data[0], None
    except (OSError, subprocess.TimeoutExpired) as exc:
        return None, f"Codex skills/list probe failed: {exc}"
    finally:
        _kill_process_tree(process)


def _path_is_within(candidate: object, root: Path) -> bool:
    if not isinstance(candidate, str):
        return False
    try:
        Path(candidate).resolve().relative_to(root.resolve())
    except (OSError, ValueError):
        return False
    return True


def _expected_prompt(path: Path) -> str | None:
    errors: list[str] = []
    value = _metadata_scalar(path, "default_prompt", errors)
    return value if not errors else None


def _validate_codex_skills_result(
    data: dict[str, Any],
    *,
    expected_names: set[str] | frozenset[str],
    owned_root: Path,
    metadata_root: Path,
    namespaced: bool,
) -> str | None:
    errors = data.get("errors")
    if errors != []:
        return f"Codex skills/list reported skill errors: {errors!r}"
    raw_skills = data.get("skills")
    if not isinstance(raw_skills, list):
        return "Codex skills/list result has no skill array"
    owned = [
        item
        for item in raw_skills
        if isinstance(item, dict) and _path_is_within(item.get("path"), owned_root)
    ]
    actual_names = {
        str(item.get("name"))
        for item in owned
    }
    expected_runtime_names = {
        f"ezpowers:{name}" if namespaced else name
        for name in expected_names
    }
    if actual_names != expected_runtime_names:
        return (
            "Codex skills/list inventory mismatch: "
            f"expected={sorted(expected_runtime_names)}, actual={sorted(actual_names)}"
        )
    for item in owned:
        if item.get("enabled") is not True:
            return f"Codex disabled a retained skill: {item.get('name')}"
        runtime_name = str(item["name"])
        local_name = runtime_name.split(":", 1)[-1]
        metadata_name = "openai.yaml" if namespaced else "project-openai.yaml"
        expected_prompt = _expected_prompt(
            metadata_root / local_name / "agents" / metadata_name
        )
        interface = item.get("interface")
        actual_prompt = (
            interface.get("defaultPrompt")
            if isinstance(interface, dict)
            else None
        )
        if expected_prompt is None or actual_prompt != expected_prompt:
            return (
                f"Codex default prompt mismatch for {runtime_name}: "
                f"expected={expected_prompt!r}, actual={actual_prompt!r}"
            )
    return None


def _prompt_input_discovery(
    executable: str,
    *,
    project_root: Path,
    env: dict[str, str],
) -> str | None:
    try:
        result = _run_command(
            [executable, "debug", "prompt-input", "EZPowers discovery probe"],
            cwd=project_root,
            env=env,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return f"Codex prompt-input discovery probe failed to run: {exc}"
    output = "\n".join(
        part for part in (result.stdout, result.stderr) if part
    ).strip()
    if result.returncode != 0:
        return f"Codex prompt-input discovery probe failed: {output or 'no output'}"
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        return f"Codex prompt-input probe returned invalid JSON: {exc}"
    messages = payload if isinstance(payload, list) else [payload]
    sections: list[str] = []
    for message in messages:
        if not isinstance(message, dict):
            continue
        for content in message.get("content", []):
            if isinstance(content, dict):
                candidate = content.get("text")
                if isinstance(candidate, str) and "<skills_instructions>" in candidate:
                    sections.append(candidate)
    discovered: set[str] = set()
    for section in sections:
        discovered.update(re.findall(r"(?m)^- ([a-z0-9:-]+):\s", section))
    discovered_names = {name.rsplit(":", 1)[-1] for name in discovered}
    missing = sorted(IMPLICIT_SKILLS - discovered_names)
    removed = sorted(REMOVED_COMPONENTS & discovered_names)
    if missing:
        return f"Codex did not discover implicit skills: {', '.join(missing)}"
    if removed:
        return f"Codex discovered removed skills: {', '.join(removed)}"
    return None


def _probe_codex(repo_root: Path) -> tuple[str, str]:
    executable = shutil.which("codex")
    if executable is None:
        return "skip", "Codex CLI is not installed"
    compatible, version = _host_version("codex", executable, repo_root)
    if not compatible:
        return "fail", version

    with tempfile.TemporaryDirectory(
        prefix="ezpowers-plugin-smoke-",
        ignore_cleanup_errors=True,
    ) as temp_name:
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

        project_home = temp_root / "project-codex-home"
        project_home.mkdir()
        project_env = os.environ.copy()
        project_env["CODEX_HOME"] = str(project_home)
        project_data, error = _codex_skills_list(
            executable,
            cwd=project_root,
            env=project_env,
        )
        if error:
            return "fail", error
        assert project_data is not None
        error = _validate_codex_skills_result(
            project_data,
            expected_names=PROJECT_SKILLS,
            owned_root=project_root,
            metadata_root=repo_root / "skills",
            namespaced=False,
        )
        if error:
            return "fail", error
        error = _prompt_input_discovery(
            executable,
            project_root=project_root,
            env=project_env,
        )
        if error:
            return "fail", error

        plugin_source = temp_root / "plugin-source"
        plugin_source.mkdir()
        for relative in (".codex-plugin", ".agents", "skills"):
            shutil.copytree(repo_root / relative, plugin_source / relative)
        plugin_home = temp_root / "plugin-codex-home"
        plugin_home.mkdir()
        plugin_env = os.environ.copy()
        plugin_env["CODEX_HOME"] = str(plugin_home)
        for command in (
            [
                executable,
                "plugin",
                "marketplace",
                "add",
                str(plugin_source),
                "--json",
            ],
            [
                executable,
                "plugin",
                "add",
                "ezpowers@ezpowers-dev",
                "--json",
            ],
        ):
            try:
                result = _run_command(command, cwd=plugin_source, env=plugin_env)
            except (OSError, subprocess.TimeoutExpired) as exc:
                return "fail", f"isolated Codex plugin install failed to run: {exc}"
            if result.returncode != 0:
                output = "\n".join(
                    part for part in (result.stdout, result.stderr) if part
                ).strip()
                return "fail", f"isolated Codex plugin install failed: {output}"
        try:
            install_payload = json.loads(result.stdout)
            installed_path = Path(install_payload["installedPath"])
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            return "fail", f"Codex plugin install returned invalid JSON: {exc}"

        plain_root = temp_root / "plain-project"
        plain_root.mkdir()
        initialized = _run_command(["git", "init", "-q"], cwd=plain_root)
        if initialized.returncode != 0:
            return "fail", f"cannot initialize plugin fixture: {initialized.stderr.strip()}"
        plugin_data, error = _codex_skills_list(
            executable,
            cwd=plain_root,
            env=plugin_env,
        )
        if error:
            return "fail", error
        assert plugin_data is not None
        error = _validate_codex_skills_result(
            plugin_data,
            expected_names=PLUGIN_SKILLS,
            owned_root=installed_path,
            metadata_root=repo_root / "skills",
            namespaced=True,
        )
        if error:
            return "fail", error
    return (
        "pass",
        f"Codex {version} loaded all project and namespaced plugin skills "
        "with matching default prompts in isolation",
    )


def run_host_probes(repo_root: Path, hosts: Iterable[str]) -> list[str]:
    errors: list[str] = []
    probes = {"claude": _probe_claude, "codex": _probe_codex}
    for host in hosts:
        status, message = probes[host](repo_root)
        print(f"[{status.upper()}] {message}")
        if status == "fail":
            errors.append(message)
    return errors


def _one_question_response(text: str) -> bool:
    normalized = text.strip()
    lowered = normalized.lower()
    question_marks = normalized.count("?") + normalized.count("？")
    return (
        bool(normalized)
        and question_marks == 1
        and "unknown skill" not in lowered
        and "unknown command" not in lowered
        and "not found" not in lowered
    )


def _probe_live_claude(repo_root: Path) -> tuple[str, str]:
    executable = shutil.which("claude")
    if executable is None:
        return "fail", "Claude CLI is required for --live-advisory"
    compatible, detail = _host_version("claude", executable, repo_root)
    if not compatible:
        return "fail", detail
    with tempfile.TemporaryDirectory(
        prefix="ezpowers-live-claude-",
        ignore_cleanup_errors=True,
    ) as temp_name:
        fixture = Path(temp_name)
        initialized = _run_command(["git", "init", "-q"], cwd=fixture)
        if initialized.returncode != 0:
            return "fail", f"cannot initialize Claude live fixture: {initialized.stderr}"
        prompt = (
            "/ezpowers:deep-interview I want to improve this empty project. "
            "Follow the loaded skill and ask exactly one concise material "
            "clarification question now. Do not use tools or write files."
        )
        try:
            result = _run_command(
                [
                    executable,
                    "-p",
                    "--plugin-dir",
                    str(repo_root),
                    "--no-session-persistence",
                    "--permission-mode",
                    "plan",
                    "--tools",
                    "",
                    "--output-format",
                    "json",
                    prompt,
                ],
                cwd=fixture,
                timeout=180,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            return "fail", f"Claude live advisory failed to run: {exc}"
        if result.returncode != 0:
            with contextlib.suppress(json.JSONDecodeError):
                error_payload = json.loads(result.stdout)
                if isinstance(error_payload, dict):
                    error_result = error_payload.get("result")
                    error_status = error_payload.get("api_error_status")
                    if isinstance(error_result, str):
                        suffix = (
                            f" (HTTP {error_status})"
                            if isinstance(error_status, int)
                            else ""
                        )
                        return (
                            "fail",
                            f"Claude live advisory failed: {error_result}{suffix}",
                        )
            output = "\n".join(
                part for part in (result.stdout, result.stderr) if part
            ).strip()
            return "fail", f"Claude live advisory failed: {output or 'no output'}"
        try:
            payload = json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            return "fail", f"Claude live advisory returned invalid JSON: {exc}"
        response = payload.get("result") if isinstance(payload, dict) else None
        if not isinstance(response, str) or not _one_question_response(response):
            return "fail", f"Claude live advisory did not return one question: {response!r}"
    return "pass", f"Claude {detail} executed the namespaced deep-interview skill"


def _probe_live_codex(repo_root: Path) -> tuple[str, str]:
    executable = shutil.which("codex")
    if executable is None:
        return "fail", "Codex CLI is required for --live-advisory"
    compatible, detail = _host_version("codex", executable, repo_root)
    if not compatible:
        return "fail", detail
    with tempfile.TemporaryDirectory(
        prefix="ezpowers-live-codex-",
        ignore_cleanup_errors=True,
    ) as temp_name:
        fixture = Path(temp_name)
        initialized = _run_command(["git", "init", "-q"], cwd=fixture)
        if initialized.returncode != 0:
            return "fail", f"cannot initialize Codex live fixture: {initialized.stderr}"
        installed = _run_command(
            [
                sys.executable,
                str(repo_root / "scripts" / "ezpowers.py"),
                "install",
                "--project-root",
                str(fixture),
            ],
            cwd=repo_root,
        )
        if installed.returncode != 0:
            output = "\n".join(
                part for part in (installed.stdout, installed.stderr) if part
            ).strip()
            return "fail", f"cannot install Codex live fixture: {output}"
        prompt = (
            "$deep-interview I want to improve this empty project. Follow the "
            "loaded skill and ask exactly one concise material clarification "
            "question now. Do not use tools or write files."
        )
        try:
            result = _run_command(
                [
                    executable,
                    "exec",
                    "--ephemeral",
                    "--sandbox",
                    "read-only",
                    "--json",
                    prompt,
                ],
                cwd=fixture,
                timeout=180,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            return "fail", f"Codex live advisory failed to run: {exc}"
        if result.returncode != 0:
            output = "\n".join(
                part for part in (result.stdout, result.stderr) if part
            ).strip()
            return "fail", f"Codex live advisory failed: {output or 'no output'}"
        responses: list[str] = []
        for line in result.stdout.splitlines():
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(payload, dict) or payload.get("type") != "item.completed":
                continue
            item = payload.get("item")
            if isinstance(item, dict) and item.get("type") == "agent_message":
                text_value = item.get("text")
                if isinstance(text_value, str):
                    responses.append(text_value)
        response = responses[-1] if responses else ""
        if not _one_question_response(response):
            return "fail", f"Codex live advisory did not return one question: {response!r}"
    return "pass", f"Codex {detail} executed the project-local deep-interview skill"


def run_live_advisories(repo_root: Path, hosts: Iterable[str]) -> list[str]:
    errors: list[str] = []
    probes = {
        "claude": _probe_live_claude,
        "codex": _probe_live_codex,
    }
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
    parser.add_argument(
        "--live-advisory",
        action="store_true",
        help=(
            "also make one real model call per selected host in an isolated "
            "fixture; may use account quota"
        ),
    )
    args = parser.parse_args(argv)

    repo_root = args.repo_root.resolve()
    hosts = _selected_hosts(args.host)
    errors = validate_repository(repo_root, hosts)
    if not errors:
        print(f"[PASS] {args.host} plugin files match the retained EZPowers surface")
        if not args.skip_host_probes:
            errors.extend(run_host_probes(repo_root, hosts))
            if not errors and args.live_advisory:
                errors.extend(run_live_advisories(repo_root, hosts))
        elif args.live_advisory:
            errors.append("--live-advisory cannot be combined with --skip-host-probes")

    if errors:
        for error in errors:
            print(f"[FAIL] {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
