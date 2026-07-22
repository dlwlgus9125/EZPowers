#!/usr/bin/env python3
"""Project-local EZPowers verification runtime.

The runtime is deliberately standard-library only.  It installs a verified
project kit, validates the managed spec/plan data, executes argv-based checks
without an implicit shell, and binds completion evidence to the current Git
workspace.
"""

from __future__ import annotations

import argparse
import ast
import contextlib
import datetime as dt
import hashlib
import json
import os
import pathlib
import re
import shlex
import signal
import subprocess
import sys
import tempfile
import time
import uuid
from dataclasses import dataclass
from typing import Any, Iterable, Iterator


SCHEMA_VERSION = 1
KIT_RELATIVE_PATH = pathlib.Path("project-kit/v5.0.0/manifest.json")
CONFIG_RELATIVE_PATH = pathlib.Path(".ezpowers/config.json")
STATE_RELATIVE_PATH = pathlib.Path(".ezpowers/state.json")
LEDGER_RELATIVE_PATH = pathlib.Path(".ezpowers/ledger.json")
INSTALLED_MANIFEST_RELATIVE_PATH = pathlib.Path(".ezpowers/kit/manifest.json")
EVIDENCE_RELATIVE_PATH = pathlib.Path(".ezpowers/evidence")
LOCK_RELATIVE_PATH = pathlib.Path(".ezpowers/runtime.lock")
LOCK_TIMEOUT_SECONDS = 1.0
LOCK_POLL_SECONDS = 0.05
ID_RE = re.compile(r"^[A-Za-z][A-Za-z0-9._-]{0,63}$")
CHECK_KINDS = {
    "build",
    "custom",
    "e2e",
    "integration",
    "lint",
    "security",
    "smoke",
    "static",
    "test",
    "typecheck",
    "visual",
}


class EZPowersError(RuntimeError):
    """Expected user-facing runtime error."""


class InstallConflict(EZPowersError):
    """A managed target contains user-owned changes."""


@dataclass
class Flow:
    root: pathlib.Path
    plan_path: pathlib.Path
    plan_rel: str
    spec_path: pathlib.Path
    config_path: pathlib.Path
    config: dict[str, Any]
    spec: dict[str, Any]
    plan: dict[str, Any]
    tasks: list[dict[str, Any]]
    project_checks: dict[str, dict[str, Any]]
    required_checks: list[str]
    errors: list[str]


def _utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _atomic_write(path: pathlib.Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    temporary = pathlib.Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        with contextlib.suppress(FileNotFoundError):
            temporary.unlink()


def _read_json(path: pathlib.Path, *, required: bool = True) -> dict[str, Any]:
    if not path.is_file():
        if required:
            raise EZPowersError(f"missing JSON file: {path}")
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise EZPowersError(f"invalid JSON in {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise EZPowersError(f"JSON root must be an object: {path}")
    return value


def _write_json(path: pathlib.Path, value: Any) -> None:
    _atomic_write(path, _json_bytes(value))


def _relative(root: pathlib.Path, path: pathlib.Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def _contained_path(
    root: pathlib.Path,
    value: str | pathlib.Path,
    *,
    label: str,
    must_exist: bool = False,
    directory: bool = False,
) -> pathlib.Path:
    root = root.resolve()
    raw = pathlib.Path(value)
    candidate = raw if raw.is_absolute() else root / raw
    try:
        resolved = candidate.resolve(strict=must_exist)
        resolved.relative_to(root)
    except (OSError, ValueError) as exc:
        raise EZPowersError(f"{label} escapes project root: {value}") from exc
    if must_exist and not resolved.exists():
        raise EZPowersError(f"{label} does not exist: {value}")
    if directory and must_exist and not resolved.is_dir():
        raise EZPowersError(f"{label} is not a directory: {value}")
    return resolved


def _safe_distribution_source(root: pathlib.Path, value: str, label: str) -> pathlib.Path:
    path = _contained_path(root, value, label=label, must_exist=True)
    if not path.is_file():
        raise EZPowersError(f"{label} is not a file: {value}")
    return path


def _safe_target(root: pathlib.Path, value: str, label: str = "target") -> pathlib.Path:
    raw = pathlib.PurePosixPath(value.replace("\\", "/"))
    if raw.is_absolute() or ".." in raw.parts or not raw.parts:
        raise EZPowersError(f"{label} is not a safe project-relative path: {value}")
    root = root.resolve()
    unresolved = root.joinpath(*raw.parts)
    current = unresolved
    while current != root:
        if current.is_symlink():
            raise EZPowersError(f"{label} must not traverse a symbolic link: {value}")
        current = current.parent
    path = _contained_path(root, pathlib.Path(*raw.parts), label=label)
    return path


def _is_project_relative_text(value: str) -> bool:
    posix = pathlib.PurePosixPath(value.replace("\\", "/"))
    windows = pathlib.PureWindowsPath(value)
    return not posix.is_absolute() and not windows.is_absolute() and not windows.drive


@contextlib.contextmanager
def _runtime_lock(
    root: pathlib.Path,
    *,
    timeout_seconds: float = LOCK_TIMEOUT_SECONDS,
) -> Iterator[None]:
    """Serialize project-local state writers with an OS-released file lock."""
    path = _safe_target(root, LOCK_RELATIVE_PATH.as_posix(), "runtime lock")
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        stream = path.open("a+b")
    except OSError as exc:
        raise EZPowersError(f"cannot open runtime lock {path}: {exc}") from exc

    acquired = False
    try:
        stream.seek(0, os.SEEK_END)
        if stream.tell() == 0:
            stream.write(b"\0")
            stream.flush()
        deadline = time.monotonic() + timeout_seconds
        while True:
            try:
                stream.seek(0)
                if os.name == "nt":
                    import msvcrt

                    msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl

                    fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                acquired = True
                break
            except OSError as exc:
                if time.monotonic() >= deadline:
                    raise EZPowersError(
                        "runtime is busy: could not acquire "
                        f"{LOCK_RELATIVE_PATH.as_posix()} within {timeout_seconds:g} seconds"
                    ) from exc
                time.sleep(LOCK_POLL_SECONDS)
        yield
    finally:
        if acquired:
            with contextlib.suppress(OSError):
                stream.seek(0)
                if os.name == "nt":
                    import msvcrt

                    msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl

                    fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
        stream.close()


def _default_state() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "active_plan": None,
        "latest_evidence": {"all": None, "tasks": {}},
        "latest_certificate": None,
        "updated_at": _utc_now(),
    }


def _load_state(root: pathlib.Path) -> dict[str, Any]:
    path = root / STATE_RELATIVE_PATH
    if not path.exists():
        return _default_state()
    state = _read_json(path)
    if state.get("schema_version") != SCHEMA_VERSION:
        raise EZPowersError("unsupported .ezpowers/state.json schema_version")
    evidence = state.get("latest_evidence")
    if not isinstance(evidence, dict):
        raise EZPowersError(".ezpowers/state.json latest_evidence must be an object")
    evidence.setdefault("all", None)
    if not isinstance(evidence.get("tasks"), dict):
        raise EZPowersError(".ezpowers/state.json latest_evidence.tasks must be an object")
    if any(not isinstance(task_id, str) or not task_id for task_id in evidence["tasks"]):
        raise EZPowersError(".ezpowers/state.json task evidence keys must be non-empty strings")
    return state


def _save_state(root: pathlib.Path, state: dict[str, Any]) -> None:
    state["schema_version"] = SCHEMA_VERSION
    state["updated_at"] = _utc_now()
    _write_json(root / STATE_RELATIVE_PATH, state)


def _manifest_and_mode(project_root: pathlib.Path) -> tuple[pathlib.Path, pathlib.Path, bool]:
    installed_manifest = project_root / INSTALLED_MANIFEST_RELATIVE_PATH
    script = pathlib.Path(__file__).resolve()
    installed_runtime = project_root / ".ezpowers" / "ezpowers.py"
    if installed_manifest.is_file() and script == installed_runtime.resolve():
        return installed_manifest, project_root, True
    source_root = script.parent.parent.resolve()
    return source_root / KIT_RELATIVE_PATH, source_root, False


def _verify_manifest_hash(path: pathlib.Path, expected: Any, label: str) -> None:
    if not isinstance(expected, str) or not re.fullmatch(r"[0-9a-fA-F]{64}", expected):
        raise EZPowersError(f"{label} has an invalid sha256")
    actual = _sha256_file(path)
    if actual.lower() != expected.lower():
        raise InstallConflict(f"conflict: {label} hash mismatch ({path})")


def _distribution_files(
    project_root: pathlib.Path,
    manifest_path: pathlib.Path,
    source_root: pathlib.Path,
    installed_mode: bool,
) -> tuple[dict[str, bytes], dict[str, Any]]:
    manifest = _read_json(manifest_path)
    if manifest.get("schema_version") != SCHEMA_VERSION:
        raise EZPowersError("unsupported project-kit manifest schema_version")
    if manifest.get("no_synthesis") is not True:
        raise EZPowersError("project-kit manifest no_synthesis must be true")
    if not isinstance(manifest.get("version"), str) or not manifest["version"]:
        raise EZPowersError("project-kit manifest version is missing")

    desired: dict[str, bytes] = {}

    runtime = manifest.get("runtime")
    if not isinstance(runtime, dict):
        raise EZPowersError("project-kit manifest runtime must be an object")
    runtime_target = str(runtime.get("target", ""))
    _safe_target(project_root, runtime_target, "runtime target")
    runtime_source = (
        project_root / pathlib.PurePosixPath(runtime_target)
        if installed_mode
        else _safe_distribution_source(source_root, str(runtime.get("source", "")), "runtime source")
    )
    if not runtime_source.is_file():
        raise EZPowersError(f"runtime source missing: {runtime_source}")
    _verify_manifest_hash(runtime_source, runtime.get("sha256"), "runtime")
    desired[pathlib.PurePosixPath(runtime_target).as_posix()] = runtime_source.read_bytes()

    skills = manifest.get("skills")
    if not isinstance(skills, list) or not skills:
        raise EZPowersError("project-kit manifest skills must be a non-empty array")
    seen_skills: set[str] = set()
    for skill in skills:
        if not isinstance(skill, dict):
            raise EZPowersError("project-kit skill entry must be an object")
        name = str(skill.get("name", ""))
        if not ID_RE.fullmatch(name) or name in seen_skills:
            raise EZPowersError(f"invalid or duplicate project-kit skill name: {name!r}")
        seen_skills.add(name)
        files = skill.get("files")
        if not isinstance(files, list) or not files:
            raise EZPowersError(f"project-kit skill {name} has no files")
        for item in files:
            if not isinstance(item, dict):
                raise EZPowersError(f"project-kit skill {name} file entry must be an object")
            relative_file = str(item.get("path", ""))
            pure_file = pathlib.PurePosixPath(relative_file.replace("\\", "/"))
            if pure_file.is_absolute() or ".." in pure_file.parts or not pure_file.parts:
                raise EZPowersError(f"unsafe project-kit skill path: {name}/{relative_file}")
            canonical_rel = pathlib.PurePosixPath(".ezpowers", "kit", "skills", name, *pure_file.parts).as_posix()
            if installed_mode:
                source = _safe_target(project_root, canonical_rel, "installed skill source")
                if not source.is_file():
                    raise EZPowersError(f"installed skill source missing: {canonical_rel}")
            else:
                source = _safe_distribution_source(
                    source_root,
                    str(item.get("source", "")),
                    f"skill source {name}/{relative_file}",
                )
            _verify_manifest_hash(source, item.get("sha256"), f"skill {name}/{relative_file}")
            data = source.read_bytes()
            desired[canonical_rel] = data
            desired[pathlib.PurePosixPath(".claude", "skills", name, *pure_file.parts).as_posix()] = data
            desired[pathlib.PurePosixPath(".agents", "skills", name, *pure_file.parts).as_posix()] = data

    contracts = manifest.get("contracts", [])
    if not isinstance(contracts, list):
        raise EZPowersError("project-kit manifest contracts must be an array")
    for item in contracts:
        if not isinstance(item, dict):
            raise EZPowersError("project-kit contract entry must be an object")
        target = str(item.get("target", ""))
        pure_target = pathlib.PurePosixPath(target.replace("\\", "/"))
        if pure_target.parts[:2] != (".ezpowers", "contracts"):
            raise EZPowersError(f"contract target must be under .ezpowers/contracts: {target}")
        _safe_target(project_root, target, "contract target")
        source = (
            _safe_target(project_root, target, "installed contract source")
            if installed_mode
            else _safe_distribution_source(source_root, str(item.get("source", "")), f"contract source {target}")
        )
        if not source.is_file():
            raise EZPowersError(f"contract source missing: {source}")
        _verify_manifest_hash(source, item.get("sha256"), f"contract {target}")
        desired[pure_target.as_posix()] = source.read_bytes()

    tools = manifest.get("tools", [])
    if not isinstance(tools, list):
        raise EZPowersError("project-kit manifest tools must be an array")
    for item in tools:
        if not isinstance(item, dict):
            raise EZPowersError("project-kit tool entry must be an object")
        target = str(item.get("target", ""))
        pure_target = pathlib.PurePosixPath(target.replace("\\", "/"))
        if len(pure_target.parts) < 3 or pure_target.parts[:2] != (".ezpowers", "tools"):
            raise EZPowersError(f"tool target must be under .ezpowers/tools: {target}")
        _safe_target(project_root, target, "tool target")
        source = (
            _safe_target(project_root, target, "installed tool source")
            if installed_mode
            else _safe_distribution_source(source_root, str(item.get("source", "")), f"tool source {target}")
        )
        if not source.is_file():
            raise EZPowersError(f"tool source missing: {source}")
        _verify_manifest_hash(source, item.get("sha256"), f"tool {target}")
        desired[pure_target.as_posix()] = source.read_bytes()

    desired[INSTALLED_MANIFEST_RELATIVE_PATH.as_posix()] = manifest_path.read_bytes()
    return desired, manifest


def _ledger_hashes(ledger: dict[str, Any]) -> dict[str, str]:
    result: dict[str, str] = {}
    files = ledger.get("files", {})
    if isinstance(files, dict):
        for name, value in files.items():
            if isinstance(value, str):
                result[str(name)] = value
            elif isinstance(value, dict) and isinstance(value.get("sha256"), str):
                result[str(name)] = value["sha256"]
    return result


def _installed_identity(root: pathlib.Path) -> dict[str, Any]:
    """Validate the installed kit and return the hashes bound into evidence."""
    manifest_path = root / INSTALLED_MANIFEST_RELATIVE_PATH
    ledger_path = root / LEDGER_RELATIVE_PATH
    try:
        desired, manifest = _distribution_files(root, manifest_path, root, True)
    except InstallConflict as exc:
        raise EZPowersError(f"installed kit integrity failed: {exc}") from exc

    ledger = _read_json(ledger_path)
    if ledger.get("schema_version") != SCHEMA_VERSION:
        raise EZPowersError("installed ledger schema_version must be 1")
    if ledger.get("version") != manifest.get("version"):
        raise EZPowersError("installed ledger version does not match the kit manifest")

    expected_hashes = {
        relative_name: _sha256_bytes(data)
        for relative_name, data in desired.items()
    }
    ledger_hashes = _ledger_hashes(ledger)
    if set(ledger_hashes) != set(expected_hashes):
        raise EZPowersError("installed ledger inventory does not match the kit manifest")
    for relative_name, expected in expected_hashes.items():
        if ledger_hashes.get(relative_name, "").lower() != expected:
            raise EZPowersError(
                f"installed ledger hash does not match the kit manifest: {relative_name}"
            )
        target = _safe_target(root, relative_name, "installed managed target")
        if not target.is_file() or _sha256_file(target) != expected:
            raise EZPowersError(f"installed managed file hash mismatch: {relative_name}")

    runtime = manifest.get("runtime", {})
    runtime_target = str(runtime.get("target", "")) if isinstance(runtime, dict) else ""
    runtime_path = _safe_target(root, runtime_target, "installed runtime")
    return {
        "version": manifest["version"],
        "manifest_sha256": _sha256_file(manifest_path),
        "ledger_sha256": _sha256_file(ledger_path),
        "runtime_sha256": _sha256_file(runtime_path),
    }


LEGACY_COMMANDS = (
    (("test", "command"), "legacy-test", "test", False),
    (("build", "command"), "legacy-build", "build", False),
    (("build", "typecheck_command"), "legacy-typecheck", "typecheck", False),
    (("lint", "command"), "legacy-lint", "lint", False),
    (("security", "sast_command"), "legacy-sast", "security", False),
    (("security", "dependency_audit_command"), "legacy-dependency-audit", "security", False),
    (("quality", "duplication_command"), "legacy-duplication", "static", False),
    (("quality", "mutation_command"), "legacy-mutation", "test", False),
    (("smoke", "command"), "legacy-smoke", "smoke", True),
    (("ui_verification", "command"), "legacy-ui", "integration", True),
    (("wiring", "wiring_gate_command"), "legacy-wiring", "integration", True),
)


def _nested(value: dict[str, Any], path: Iterable[str]) -> Any:
    current: Any = value
    for name in path:
        if not isinstance(current, dict):
            return None
        current = current.get(name)
    return current


def _legacy_argv(command: str) -> list[str] | None:
    try:
        if os.name == "nt":
            import ctypes

            argc = ctypes.c_int()
            parser = ctypes.windll.shell32.CommandLineToArgvW
            parser.argtypes = [ctypes.c_wchar_p, ctypes.POINTER(ctypes.c_int)]
            parser.restype = ctypes.POINTER(ctypes.c_wchar_p)
            pointer = parser(command, ctypes.byref(argc))
            if not pointer:
                return None
            try:
                argv = [pointer[index] for index in range(argc.value)]
            finally:
                ctypes.windll.kernel32.LocalFree(pointer)
        else:
            argv = shlex.split(command, posix=True)
    except (OSError, ValueError):
        return None
    if not argv or any(token in {"&&", "||", ";", "|", "|&", "&", ">", ">>", "<"} for token in argv):
        return None
    if _placeholder(argv) or _unsafe_shell_command(argv):
        return None
    return argv


def _prepare_config(project_root: pathlib.Path) -> tuple[dict[str, Any] | None, list[str]]:
    config_path = project_root / CONFIG_RELATIVE_PATH
    if config_path.exists():
        _read_json(config_path)
        return None, []

    warnings: list[str] = []
    # Migrate only safe command fields from the legacy project config.
    legacy_path = project_root / ".harness" / "config.json"
    if not legacy_path.exists():
        return {
            "schema_version": SCHEMA_VERSION,
            "project_name": project_root.name,
            "checks": {},
            "required_checks": [],
        }, warnings

    legacy = _read_json(legacy_path)
    project_name = str(legacy.get("project") or project_root.name)
    timeout = _nested(legacy, ("defaults", "timeout"))
    if not isinstance(timeout, int) or isinstance(timeout, bool) or timeout < 1:
        timeout = 1800
    timeout = min(timeout, 86400)
    checks: dict[str, Any] = {}
    required: list[str] = []
    for field_path, check_id, kind, conditional in LEGACY_COMMANDS:
        raw = _nested(legacy, field_path)
        if not isinstance(raw, str) or not raw.strip():
            continue
        if conditional:
            parent = _nested(legacy, field_path[:-1])
            enabled = False
            if isinstance(parent, dict):
                enabled = bool(parent.get("required", parent.get("enabled", True)))
            if not enabled:
                continue
        argv = _legacy_argv(raw)
        if not argv:
            warnings.append(f"ignored legacy command that requires shell parsing: {'.'.join(field_path)}")
            continue
        checks[check_id] = {
            "argv": argv,
            "cwd": ".",
            "timeout_seconds": timeout,
            "kind": kind,
        }
        required.append(check_id)

    ignored = []
    if "harness" in legacy:
        ignored.append("external harness")
    if "executor" in legacy:
        ignored.append("executor/model/retry policy")
    defaults = legacy.get("defaults")
    if isinstance(defaults, dict) and any(
        key in defaults for key in ("max_retries", "verifier", "verifier_max_rounds", "auto_push")
    ):
        ignored.append("retry/verifier policy")
    if "statusLine" in legacy or "hud" in legacy:
        ignored.append("HUD policy")
    if ignored:
        warnings.append("ignored legacy " + ", ".join(ignored))

    return {
        "schema_version": SCHEMA_VERSION,
        "project_name": project_name,
        "checks": checks,
        "required_checks": required,
    }, warnings


def _owned_hook(entry: Any, host: str) -> bool:
    if not isinstance(entry, dict):
        return False
    candidates = [entry]
    nested = entry.get("hooks")
    if isinstance(nested, list):
        candidates.extend(item for item in nested if isinstance(item, dict))
    for candidate in candidates:
        args = candidate.get("args")
        command_fields = (candidate.get("command"), candidate.get("commandWindows"))
        has_runtime = any(
            isinstance(command, str) and "ezpowers.py" in command
            for command in command_fields
        ) or (
            isinstance(args, list)
            and any(isinstance(value, str) and "ezpowers.py" in value for value in args)
        )
        if not has_runtime:
            continue
        if isinstance(args, list):
            for index, value in enumerate(args[:-1]):
                if value == "--host" and args[index + 1] == host:
                    return True
        if any(
            isinstance(command, str)
            and re.search(rf"--host\s+{re.escape(host)}(?:\s|$)", command)
            for command in command_fields
        ):
            return True
    return False


def _hook_update(project_root: pathlib.Path, host: str) -> tuple[pathlib.Path, bytes]:
    path = project_root / (".claude/settings.json" if host == "claude" else ".codex/hooks.json")
    value = _read_json(path, required=False) if path.exists() else {}
    hooks = value.setdefault("hooks", {})
    if not isinstance(hooks, dict):
        raise InstallConflict(f"conflict: {path} hooks field is not an object")
    stop = hooks.setdefault("Stop", [])
    if not isinstance(stop, list):
        raise InstallConflict(f"conflict: {path} hooks.Stop field is not an array")
    argv = [
        sys.executable,
        str((project_root / ".ezpowers" / "ezpowers.py").resolve()),
        "hook",
        "--host",
        host,
    ]
    if host == "claude":
        handler = {
            "type": "command",
            "command": argv[0],
            "args": argv[1:],
            "timeout": 30,
        }
        desired: dict[str, Any] = {"matcher": "", "hooks": [handler]}
    else:
        handler = {
            "type": "command",
            "command": shlex.join(argv),
            "commandWindows": subprocess.list2cmdline(argv),
            "timeout": 30,
        }
        desired = {"hooks": [handler]}
    owned_indices = [index for index, item in enumerate(stop) if _owned_hook(item, host)]
    if owned_indices:
        stop[owned_indices[0]] = desired
        for index in reversed(owned_indices[1:]):
            stop.pop(index)
    else:
        stop.append(desired)
    return path, _json_bytes(value)


def _require_git_worktree_root(project_root: pathlib.Path) -> None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=project_root,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=15,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise EZPowersError(f"cannot inspect Git worktree: {exc}") from exc
    if result.returncode != 0:
        detail = result.stderr.strip() or "not a Git worktree"
        raise EZPowersError(f"project root must be a Git worktree root: {detail}")
    top = pathlib.Path(result.stdout.strip()).resolve()
    if top != project_root.resolve():
        raise EZPowersError(
            f"project root must equal the Git worktree root: {top}"
        )


def _install(args: argparse.Namespace) -> int:
    project_root = pathlib.Path(args.project_root).resolve()
    if not project_root.is_dir():
        raise EZPowersError(f"project root does not exist: {project_root}")
    _require_git_worktree_root(project_root)
    with _runtime_lock(project_root):
        return _install_locked(args, project_root)


def _install_locked(args: argparse.Namespace, project_root: pathlib.Path) -> int:
    manifest_path, source_root, installed_mode = _manifest_and_mode(project_root)
    desired, manifest = _distribution_files(project_root, manifest_path, source_root, installed_mode)
    ledger_path = project_root / LEDGER_RELATIVE_PATH
    ledger = _read_json(ledger_path, required=False) if ledger_path.exists() else {}
    old_hashes = _ledger_hashes(ledger)
    desired_hashes = {
        relative_name: _sha256_bytes(data)
        for relative_name, data in desired.items()
    }

    config_value, warnings = _prepare_config(project_root)
    config_candidate = (
        config_value
        if config_value is not None
        else _read_json(project_root / CONFIG_RELATIVE_PATH)
    )
    config_errors: list[str] = []
    _validate_config_value(project_root, config_candidate, config_errors)
    if config_errors:
        raise EZPowersError(
            "invalid .ezpowers/config.json:\n- " + "\n- ".join(config_errors)
        )
    state_path = project_root / STATE_RELATIVE_PATH
    if state_path.exists():
        _load_state(project_root)

    hook_updates: list[tuple[pathlib.Path, bytes]] = []
    if args.enable_hooks in {"claude", "both"}:
        hook_updates.append(_hook_update(project_root, "claude"))
    if args.enable_hooks in {"codex", "both"}:
        hook_updates.append(_hook_update(project_root, "codex"))

    if ledger and not args.refresh:
        drift: list[str] = []
        if not old_hashes:
            drift.append("ledger has no managed file hashes")
        for relative_name, previous in old_hashes.items():
            target = _safe_target(project_root, relative_name, "managed target")
            if not target.is_file():
                drift.append(f"{relative_name}: managed file is missing")
            elif _sha256_file(target) != previous:
                drift.append(f"{relative_name}: managed file was modified")
        if drift:
            raise InstallConflict(
                "conflict: installed project kit has managed-file drift:\n- "
                + "\n- ".join(drift)
            )
        distribution_changed = (
            ledger.get("version") != manifest.get("version")
            or {name: value.lower() for name, value in old_hashes.items()}
            != desired_hashes
        )
        if not installed_mode and distribution_changed:
            raise EZPowersError(
                "plugin distribution differs from the installed project kit; "
                "rerun the plugin installer with --refresh to update it"
            )
        for warning in warnings:
            print(f"ignored: {warning}")
        for path, data in hook_updates:
            _atomic_write(path, data)
        installed_version = str(ledger.get("version") or "unknown")
        print(
            f"EZPowers project kit already installed ({installed_version}); "
            "use --refresh to update or repair it"
        )
        return 0

    conflicts: list[str] = []
    for relative_name, data in desired.items():
        target = _safe_target(project_root, relative_name)
        if not target.exists():
            continue
        if not target.is_file():
            conflicts.append(f"{relative_name}: target is not a regular file")
            continue
        current = _sha256_file(target)
        wanted = _sha256_bytes(data)
        previous = old_hashes.get(relative_name)
        if previous is None and current != wanted:
            conflicts.append(f"{relative_name}: unmanaged file differs")
        elif installed_mode and previous is not None and current != previous:
            conflicts.append(f"{relative_name}: installed managed file was modified")
        elif previous is not None and current != previous and current != wanted:
            conflicts.append(f"{relative_name}: managed file was modified")

    obsolete: list[pathlib.Path] = []
    for relative_name, previous in old_hashes.items():
        if relative_name in desired:
            continue
        target = _safe_target(project_root, relative_name, "obsolete managed target")
        if not target.exists():
            continue
        if not target.is_file() or _sha256_file(target) != previous:
            conflicts.append(f"{relative_name}: obsolete managed file was modified")
        else:
            obsolete.append(target)

    if conflicts:
        raise InstallConflict("conflict: project kit refresh preserved user files:\n- " + "\n- ".join(conflicts))

    for relative_name, data in desired.items():
        target = _safe_target(project_root, relative_name)
        if not target.exists() or _sha256_file(target) != _sha256_bytes(data):
            _atomic_write(target, data)
    for target in obsolete:
        target.unlink()

    if config_value is not None:
        _write_json(project_root / CONFIG_RELATIVE_PATH, config_value)
    if not state_path.exists():
        _save_state(project_root, _default_state())
    for path, data in hook_updates:
        _atomic_write(path, data)

    new_ledger = {
        "schema_version": SCHEMA_VERSION,
        "version": manifest["version"],
        "installed_at": _utc_now(),
        "source": "installed-kit" if installed_mode else "plugin-distribution",
        "files": {
            name: {"sha256": _sha256_bytes(data)}
            for name, data in sorted(desired.items())
        },
        "migration_warnings": warnings,
    }
    _write_json(ledger_path, new_ledger)
    for warning in warnings:
        print(f"ignored: {warning}")
    verb = "refreshed" if args.refresh else "installed"
    print(f"EZPowers project kit {verb}: {manifest['version']} ({len(desired)} managed files)")
    return 0


def _extract_block(path: pathlib.Path, kind: str) -> dict[str, Any]:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise EZPowersError(f"cannot read {kind} document {path}: {exc}") from exc
    start = f"<!-- ezpowers:{kind}:start -->"
    end = f"<!-- ezpowers:{kind}:end -->"
    if text.count(start) != 1 or text.count(end) != 1:
        raise EZPowersError(f"{kind} document must contain exactly one managed JSON block")
    start_index = text.index(start) + len(start)
    end_index = text.index(end)
    if end_index <= start_index:
        raise EZPowersError(f"{kind} managed JSON block markers are out of order")
    body = text[start_index:end_index].strip()
    match = re.fullmatch(
        r"```json[ \t]*\n(?P<json>.*)\n[ \t]*```",
        body,
        re.DOTALL,
    )
    if not match:
        raise EZPowersError(f"{kind} managed block must contain one fenced JSON object")
    try:
        value = json.loads(match.group("json"))
    except json.JSONDecodeError as exc:
        raise EZPowersError(f"invalid JSON in {kind} managed block: {exc}") from exc
    if not isinstance(value, dict):
        raise EZPowersError(f"{kind} managed JSON root must be an object")
    return value


def _validate_spec_document(
    root: pathlib.Path,
    spec_argument: str | pathlib.Path,
    errors: list[str],
    *,
    label: str = "spec",
) -> tuple[pathlib.Path, dict[str, Any], dict[str, dict[str, Any]]]:
    """Load and validate only the host-independent managed spec contract."""
    try:
        spec_path = _contained_path(root, spec_argument, label=label, must_exist=True)
    except EZPowersError as exc:
        errors.append(str(exc))
        return root / "__invalid_spec__", {}, {}
    if not spec_path.is_file():
        errors.append(f"{label} is not a file: {spec_argument}")
        return spec_path, {}, {}
    try:
        spec = _extract_block(spec_path, "spec")
    except EZPowersError as exc:
        errors.append(str(exc))
        return spec_path, {}, {}
    if spec.get("schema_version") != SCHEMA_VERSION:
        errors.append("spec schema_version must be 1")

    criteria_by_id: dict[str, dict[str, Any]] = {}
    criteria = spec.get("criteria", [])
    if not isinstance(criteria, list) or not criteria:
        errors.append("spec.criteria must be a non-empty array")
        return spec_path, spec, criteria_by_id
    for index, criterion in enumerate(criteria):
        if not isinstance(criterion, dict):
            errors.append(f"spec.criteria[{index}] must be an object")
            continue
        criterion_id = str(criterion.get("id", ""))
        if not ID_RE.fullmatch(criterion_id) or criterion_id in criteria_by_id:
            errors.append(f"invalid or duplicate criterion id: {criterion_id!r}")
            continue
        requirement_id = criterion.get("requirement_id")
        if not isinstance(requirement_id, str) or not requirement_id.strip():
            errors.append(f"criterion {criterion_id} must have requirement_id")
        if not isinstance(criterion.get("claim"), str) or not criterion["claim"].strip():
            errors.append(f"criterion {criterion_id} must have an observable claim")
        if not isinstance(criterion.get("verify_type"), str) or not criterion["verify_type"].strip():
            errors.append(f"criterion {criterion_id} must have verify_type")
        if not isinstance(criterion.get("integration"), bool):
            errors.append(f"criterion {criterion_id} integration must be a boolean")
        criteria_by_id[criterion_id] = criterion
    return spec_path, spec, criteria_by_id


def _placeholder(argv: list[str]) -> bool:
    if not argv:
        return True
    executable = pathlib.PurePath(argv[0]).name.lower()
    if executable in {"echo", "true"}:
        return True
    if executable in {"python", "python.exe", "python3", "python3.exe", "py", "py.exe"} and "-c" in argv:
        index = argv.index("-c")
        if index + 1 < len(argv):
            source = argv[index + 1]
            code = re.sub(r"\s+", "", source).lower()
            if code in {"pass", "exit(0)", "raisesystemexit(0)", "sys.exit(0)"}:
                return True
            with contextlib.suppress(SyntaxError):
                module = ast.parse(source)
                if module.body and all(
                    isinstance(statement, ast.Expr)
                    and isinstance(statement.value, ast.Call)
                    and isinstance(statement.value.func, ast.Name)
                    and statement.value.func.id == "print"
                    for statement in module.body
                ):
                    return True
    if executable in {"powershell", "powershell.exe", "pwsh", "pwsh.exe", "sh", "bash", "cmd", "cmd.exe"}:
        command_flags = {"-c", "-command", "/c"}
        flag_index = next((index for index, value in enumerate(argv[1:], 1) if value.lower() in command_flags), None)
        if flag_index is not None and flag_index + 1 < len(argv):
            command = " ".join(argv[flag_index + 1 :]).strip().lower().strip('"\'')
            if re.fullmatch(r"(?:true|exit\s+0|write-output(?:\s+.*)?|echo(?:\s+.*)?)", command):
                return True
    return False


def _unsafe_shell_command(argv: list[str]) -> bool:
    executable = pathlib.Path(argv[0]).name.lower()
    if executable not in {
        "bash",
        "bash.exe",
        "cmd",
        "cmd.exe",
        "powershell",
        "powershell.exe",
        "pwsh",
        "pwsh.exe",
        "sh",
    }:
        return False
    lower_args = {value.lower() for value in argv[1:]}
    if executable in {"powershell", "powershell.exe", "pwsh", "pwsh.exe"} and lower_args.intersection(
        {"-encodedcommand", "-enc", "-encodedarguments", "-commandwithargs"}
    ):
        return True
    if executable in {"cmd", "cmd.exe"} and "/k" in lower_args:
        return True
    command_flags = {"-c", "-command", "/c"}
    flag_index = next(
        (index for index, value in enumerate(argv[1:], 1) if value.lower() in command_flags),
        None,
    )
    if flag_index is None or flag_index + 1 >= len(argv):
        return False
    payload = " ".join(argv[flag_index + 1 :])
    return bool(re.search(r"(?:&&|\|\||[|;&<>]|[\r\n])", payload))


def _validate_check(
    raw: Any,
    *,
    check_id: str,
    root: pathlib.Path,
    label: str,
    errors: list[str],
) -> dict[str, Any] | None:
    if not ID_RE.fullmatch(check_id):
        errors.append(f"{label} has invalid check id: {check_id!r}")
    if not isinstance(raw, dict):
        errors.append(f"{label} must be an object")
        return None
    argv = raw.get("argv")
    if not isinstance(argv, list) or not argv or any(not isinstance(item, str) or not item or "\x00" in item for item in argv):
        errors.append(f"{label}.argv must be a non-empty string array")
        argv = []
    cwd = raw.get("cwd")
    if not isinstance(cwd, str) or not cwd:
        errors.append(f"{label}.cwd must be a project-relative directory")
        cwd = "."
    elif not _is_project_relative_text(cwd):
        errors.append(f"{label}.cwd must be a project-relative directory")
    else:
        try:
            _contained_path(root, cwd, label=f"{label}.cwd", must_exist=True, directory=True)
        except EZPowersError as exc:
            errors.append(str(exc))
    timeout = raw.get("timeout_seconds")
    if not isinstance(timeout, int) or isinstance(timeout, bool) or not 1 <= timeout <= 86400:
        errors.append(f"{label}.timeout_seconds must be an integer from 1 to 86400")
        timeout = 1
    kind = raw.get("kind")
    if not isinstance(kind, str) or kind not in CHECK_KINDS:
        errors.append(f"{label}.kind must be one of: {', '.join(sorted(CHECK_KINDS))}")
        kind = "custom"
    if argv and _placeholder(argv):
        errors.append(f"{label}.argv is a placeholder/no-op command")
    if argv and _unsafe_shell_command(argv):
        errors.append(
            f"{label}.argv contains shell control operators or an opaque shell command form"
        )
    return {
        "id": check_id,
        "argv": list(argv),
        "cwd": cwd,
        "timeout_seconds": timeout,
        "kind": kind,
    }


def _validate_config_value(
    root: pathlib.Path,
    config: dict[str, Any],
    errors: list[str],
) -> tuple[dict[str, dict[str, Any]], list[str]]:
    if config.get("schema_version") != SCHEMA_VERSION:
        errors.append("config schema_version must be 1")
    project_checks: dict[str, dict[str, Any]] = {}
    raw_project_checks = config.get("checks", {})
    if not isinstance(raw_project_checks, dict):
        errors.append("config.checks must be an object")
        raw_project_checks = {}
    for check_id, raw in raw_project_checks.items():
        normalized = _validate_check(
            raw,
            check_id=str(check_id),
            root=root,
            label=f"config.checks.{check_id}",
            errors=errors,
        )
        if normalized:
            project_checks[str(check_id)] = normalized
    required_checks = config.get("required_checks", [])
    if not isinstance(required_checks, list) or any(
        not isinstance(item, str) for item in required_checks
    ):
        errors.append("config.required_checks must be a string array")
        required_checks = []
    for check_id in required_checks:
        if check_id not in project_checks:
            errors.append(f"config.required_checks references unknown check: {check_id}")
    return project_checks, list(required_checks)


def _validate_flow(root: pathlib.Path, plan_argument: str | pathlib.Path) -> Flow:
    root = root.resolve()
    errors: list[str] = []
    try:
        plan_path = _contained_path(root, plan_argument, label="plan", must_exist=True)
    except EZPowersError as exc:
        # A placeholder path lets callers return all errors in a stable shape.
        plan_path = root / "__invalid_plan__"
        errors.append(str(exc))
    plan: dict[str, Any] = {}
    spec: dict[str, Any] = {}
    config: dict[str, Any] = {}
    config_path = root / CONFIG_RELATIVE_PATH
    try:
        config = _read_json(config_path)
    except EZPowersError as exc:
        errors.append(str(exc))
    project_checks, required_checks = _validate_config_value(root, config, errors)
    if plan_path.is_file():
        try:
            plan = _extract_block(plan_path, "plan")
        except EZPowersError as exc:
            errors.append(str(exc))
    if plan and plan.get("schema_version") != SCHEMA_VERSION:
        errors.append("plan schema_version must be 1")

    spec_path = root / "__invalid_spec__"
    criteria_by_id: dict[str, dict[str, Any]] = {}
    spec_value = plan.get("spec") if isinstance(plan, dict) else None
    if not isinstance(spec_value, str) or not spec_value:
        errors.append("plan.spec must name a project-local spec document")
    elif not _is_project_relative_text(spec_value):
        errors.append("plan.spec must be a project-relative spec path")
    else:
        spec_path, spec, criteria_by_id = _validate_spec_document(
            root,
            spec_value,
            errors,
            label="plan.spec",
        )

    top_checks: dict[str, dict[str, Any]] = {}
    raw_top_checks = plan.get("checks", {}) if isinstance(plan, dict) else {}
    if raw_top_checks is None:
        raw_top_checks = {}
    if not isinstance(raw_top_checks, dict):
        errors.append("plan.checks must be an object when present")
        raw_top_checks = {}
    for check_id, raw in raw_top_checks.items():
        if check_id in project_checks:
            errors.append(f"plan check collides with config check: {check_id}")
        normalized = _validate_check(
            raw,
            check_id=str(check_id),
            root=root,
            label=f"plan.checks.{check_id}",
            errors=errors,
        )
        if normalized:
            top_checks[str(check_id)] = normalized

    raw_tasks = plan.get("tasks", []) if isinstance(plan, dict) else []
    if not isinstance(raw_tasks, list) or not raw_tasks:
        errors.append("plan.tasks must be a non-empty array")
        raw_tasks = []
    tasks: list[dict[str, Any]] = []
    task_ids: set[str] = set()
    inline_ids: set[str] = set()
    criterion_coverage: dict[str, list[dict[str, Any]]] = {key: [] for key in criteria_by_id}
    criterion_occurrences: dict[str, int] = {key: 0 for key in criteria_by_id}
    used_top_checks: set[str] = set()
    for index, raw_task in enumerate(raw_tasks):
        if not isinstance(raw_task, dict):
            errors.append(f"plan.tasks[{index}] must be an object")
            continue
        task_id = str(raw_task.get("id", ""))
        if not ID_RE.fullmatch(task_id) or task_id in task_ids:
            errors.append(f"invalid or duplicate task id: {task_id!r}")
        task_ids.add(task_id)
        raw_criteria = raw_task.get("criteria", [])
        if not isinstance(raw_criteria, list) or not raw_criteria or any(not isinstance(item, str) for item in raw_criteria):
            errors.append(f"task {task_id or index} criteria must be a non-empty string array")
            raw_criteria = []
        for criterion_id in raw_criteria:
            if criterion_id not in criteria_by_id:
                errors.append(f"task {task_id} references unknown criterion: {criterion_id}")
            else:
                criterion_occurrences[criterion_id] += 1
        raw_checks = raw_task.get("checks", [])
        if not isinstance(raw_checks, list) or not raw_checks:
            errors.append(f"task {task_id or index} checks must be a non-empty array")
            raw_checks = []
        normalized_checks: list[dict[str, Any]] = []
        for check_index, raw_check in enumerate(raw_checks):
            if isinstance(raw_check, str):
                if raw_check in project_checks:
                    normalized_checks.append(project_checks[raw_check])
                elif raw_check in top_checks:
                    normalized_checks.append(top_checks[raw_check])
                    used_top_checks.add(raw_check)
                else:
                    errors.append(f"task {task_id} references unknown check: {raw_check}")
                continue
            if not isinstance(raw_check, dict):
                errors.append(f"task {task_id} check {check_index} must be an object or check id")
                continue
            check_id = str(raw_check.get("id", ""))
            if check_id in project_checks or check_id in top_checks or check_id in inline_ids:
                errors.append(f"duplicate check id: {check_id}")
            inline_ids.add(check_id)
            normalized = _validate_check(
                raw_check,
                check_id=check_id,
                root=root,
                label=f"task {task_id} check {check_id or check_index}",
                errors=errors,
            )
            if normalized:
                normalized_checks.append(normalized)
        task = {"id": task_id, "criteria": list(raw_criteria), "checks": normalized_checks}
        tasks.append(task)
        for criterion_id in raw_criteria:
            if criterion_id in criterion_coverage:
                criterion_coverage[criterion_id].extend(normalized_checks)

    for check_id in sorted(set(top_checks) - used_top_checks):
        errors.append(f"plan check is not referenced by any task: {check_id}")
    for criterion_id, mapped_checks in criterion_coverage.items():
        if criterion_occurrences[criterion_id] > 1:
            errors.append(f"criterion must be mapped exactly once: {criterion_id}")
        if not mapped_checks:
            errors.append(f"criterion is not mapped to an executable check: {criterion_id}")
            continue
        criterion = criteria_by_id[criterion_id]
        integration = bool(criterion.get("integration")) or str(criterion.get("verify_type", "")).lower() in {"integration", "e2e"}
        if integration and not any(check.get("kind") in {"integration", "e2e", "smoke"} for check in mapped_checks):
            errors.append(f"integration criterion {criterion_id} requires an integration, e2e, or smoke check")

    plan_rel = ""
    if plan_path.exists():
        with contextlib.suppress(ValueError):
            plan_rel = _relative(root, plan_path)
    return Flow(
        root=root,
        plan_path=plan_path,
        plan_rel=plan_rel,
        spec_path=spec_path,
        config_path=config_path,
        config=config,
        spec=spec,
        plan=plan,
        tasks=tasks,
        project_checks=project_checks,
        required_checks=list(required_checks),
        errors=errors,
    )


def _set_active_plan(flow: Flow) -> bool:
    state = _load_state(flow.root)
    if state.get("active_plan") == flow.plan_rel:
        return False
    state["active_plan"] = flow.plan_rel
    state["latest_evidence"] = {"all": None, "tasks": {}}
    state["latest_certificate"] = None
    _save_state(flow.root, state)
    return True


def _emit(value: dict[str, Any], as_json: bool, *, stream: Any = sys.stdout) -> None:
    if as_json:
        print(json.dumps(value, ensure_ascii=False, indent=2), file=stream)
        return
    status = value.get("status", "")
    message = value.get("message") or "; ".join(value.get("errors", []) or value.get("reasons", []))
    print(f"EZPowers {status}: {message or '-'}", file=stream)


def _validate_command(args: argparse.Namespace) -> int:
    root = _runtime_project_root()
    if args.spec is not None:
        if args.activate:
            payload = {
                "status": "FAIL",
                "spec": str(args.spec),
                "errors": ["--activate requires --plan"],
                "activation": {
                    "requested": True,
                    "applied": False,
                    "changed": False,
                },
            }
            _emit(payload, args.json)
            return 2
        errors: list[str] = []
        spec_path, _, _ = _validate_spec_document(root, args.spec, errors)
        spec_rel = str(args.spec)
        if spec_path.exists():
            with contextlib.suppress(ValueError):
                spec_rel = _relative(root, spec_path)
        payload = {
            "status": "PASS" if not errors else "FAIL",
            "spec": spec_rel,
            "errors": errors,
            "activation": {
                "requested": False,
                "applied": False,
                "changed": False,
            },
        }
        _emit(payload, args.json)
        return 0 if not errors else 2

    def validate_plan() -> tuple[dict[str, Any], int]:
        flow = _validate_flow(root, args.plan)
        changed = False
        applied = False
        if args.activate and not flow.errors:
            changed = _set_active_plan(flow)
            applied = True
        payload = {
            "status": "PASS" if not flow.errors else "FAIL",
            "plan": flow.plan_rel or str(args.plan),
            "errors": flow.errors,
            "activation": {
                "requested": bool(args.activate),
                "applied": applied,
                "changed": changed,
            },
        }
        return payload, 0 if not flow.errors else 2

    if args.activate:
        with _runtime_lock(root):
            payload, code = validate_plan()
    else:
        payload, code = validate_plan()
    _emit(payload, args.json)
    return code


def _git_bytes(root: pathlib.Path, *arguments: str) -> bytes:
    try:
        process = subprocess.run(
            ["git", *arguments],
            cwd=root,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise EZPowersError(
            f"Git command could not run ({' '.join(arguments)}): {exc}"
        ) from exc
    if process.returncode != 0:
        message = process.stderr.decode("utf-8", "replace").strip()
        raise EZPowersError(f"Git command failed ({' '.join(arguments)}): {message}")
    return process.stdout


def _excluded_runtime_path(name: str) -> bool:
    normalized = name.replace("\\", "/")
    while normalized.startswith("./"):
        normalized = normalized[2:]
    return (
        normalized == ".ezpowers/state.json"
        or normalized == LOCK_RELATIVE_PATH.as_posix()
        or normalized.startswith(".ezpowers/evidence/")
        or normalized == ".git"
        or normalized.startswith(".git/")
    )


def _workspace_snapshot(root: pathlib.Path) -> dict[str, Any]:
    top = pathlib.Path(_git_bytes(root, "rev-parse", "--show-toplevel").decode("utf-8", "replace").strip()).resolve()
    if top != root.resolve():
        raise EZPowersError(f"project root must equal the Git worktree root: {top}")
    head = _git_bytes(root, "rev-parse", "HEAD").decode("ascii", "replace").strip()
    tracked_diff = _git_bytes(
        root,
        "diff",
        "--binary",
        "--full-index",
        "HEAD",
        "--",
        ".",
        ":(exclude).ezpowers/evidence/**",
        ":(exclude).ezpowers/state.json",
        ":(exclude).ezpowers/runtime.lock",
    )
    untracked_raw = _git_bytes(root, "ls-files", "--others", "--exclude-standard", "-z")
    names = sorted(
        os.fsdecode(item)
        for item in untracked_raw.split(b"\0")
        if item and not _excluded_runtime_path(os.fsdecode(item))
    )
    untracked_digest = hashlib.sha256()
    for name in names:
        path = _contained_path(root, name, label="untracked path", must_exist=True)
        untracked_digest.update(name.replace("\\", "/").encode("utf-8", "surrogateescape"))
        untracked_digest.update(b"\0")
        if path.is_symlink():
            untracked_digest.update(b"symlink\0")
            untracked_digest.update(os.readlink(path).encode("utf-8", "surrogateescape"))
        elif path.is_file():
            untracked_digest.update(b"file\0")
            untracked_digest.update(_sha256_file(path).encode("ascii"))
        else:
            raise EZPowersError(f"unsupported untracked filesystem entry: {name}")
        untracked_digest.update(b"\0")
    parts = {
        "git_head": head,
        "tracked_diff_sha256": _sha256_bytes(tracked_diff),
        "untracked_sha256": untracked_digest.hexdigest(),
        "untracked_count": len(names),
    }
    canonical = json.dumps(parts, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return {**parts, "fingerprint": _sha256_bytes(canonical)}


def _kill_process_tree(process: subprocess.Popen[Any]) -> None:
    if process.poll() is not None:
        return
    if os.name == "nt":
        with contextlib.suppress(Exception):
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(process.pid)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=5,
                check=False,
            )
    else:
        with contextlib.suppress(Exception):
            os.killpg(process.pid, signal.SIGKILL)
    with contextlib.suppress(Exception):
        process.kill()


def _log_relative(root: pathlib.Path, path: pathlib.Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def _run_check(
    root: pathlib.Path,
    run_dir: pathlib.Path,
    task_id: str,
    check: dict[str, Any],
) -> dict[str, Any]:
    safe_task = re.sub(r"[^A-Za-z0-9._-]+", "-", task_id) or "project"
    safe_check = re.sub(r"[^A-Za-z0-9._-]+", "-", check["id"]) or "check"
    identity = _sha256_bytes(f"{task_id}\0{check['id']}".encode("utf-8"))[:12]
    prefix = run_dir / f"{safe_task}--{safe_check}--{identity}"
    stdout_path = pathlib.Path(f"{prefix}.stdout.log")
    stderr_path = pathlib.Path(f"{prefix}.stderr.log")
    cwd = _contained_path(root, check["cwd"], label=f"check {check['id']} cwd", must_exist=True, directory=True)
    started = time.monotonic()
    timed_out = False
    spawn_error = ""
    exit_code = 127
    with stdout_path.open("wb") as stdout, stderr_path.open("wb") as stderr:
        kwargs: dict[str, Any] = {
            "cwd": cwd,
            "stdout": stdout,
            "stderr": stderr,
            "shell": False,
        }
        if os.name == "nt":
            kwargs["creationflags"] = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        else:
            kwargs["start_new_session"] = True
        try:
            process = subprocess.Popen(check["argv"], **kwargs)
            try:
                exit_code = process.wait(timeout=check["timeout_seconds"])
            except subprocess.TimeoutExpired:
                timed_out = True
                _kill_process_tree(process)
                with contextlib.suppress(Exception):
                    process.wait(timeout=5)
                exit_code = 124
        except (OSError, ValueError) as exc:
            spawn_error = str(exc)
            stderr.write((spawn_error + "\n").encode("utf-8", "replace"))
    duration_ms = int((time.monotonic() - started) * 1000)
    return {
        "id": check["id"],
        "argv": check["argv"],
        "cwd": check["cwd"],
        "timeout_seconds": check["timeout_seconds"],
        "kind": check["kind"],
        "status": "PASS" if exit_code == 0 and not timed_out and not spawn_error else "FAIL",
        "exit_code": exit_code,
        "timed_out": timed_out,
        "spawn_error": spawn_error,
        "duration_ms": duration_ms,
        "stdout_log": _log_relative(root, stdout_path),
        "stderr_log": _log_relative(root, stderr_path),
        "stdout_sha256": _sha256_file(stdout_path),
        "stderr_sha256": _sha256_file(stderr_path),
    }


def _evidence_run_id() -> str:
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    return f"{stamp}-{uuid.uuid4().hex[:8]}"


def _verify_command(args: argparse.Namespace) -> int:
    root = _runtime_project_root()
    with _runtime_lock(root):
        return _verify_command_locked(args, root)


def _verify_command_locked(args: argparse.Namespace, root: pathlib.Path) -> int:
    flow = _validate_flow(root, args.plan)
    if flow.errors:
        payload = {"status": "FAIL", "errors": flow.errors, "tasks": [], "reasons": flow.errors}
        _emit(payload, args.json)
        return 2
    selected = flow.tasks
    scope = "all"
    if args.task:
        selected = [task for task in flow.tasks if task["id"] == args.task]
        scope = f"task:{args.task}"
        if not selected:
            payload = {"status": "FAIL", "errors": [f"unknown task: {args.task}"], "tasks": []}
            _emit(payload, args.json)
            return 2
    installation_before = _installed_identity(root)
    _set_active_plan(flow)

    plan_hash_before = _sha256_file(flow.plan_path)
    spec_hash_before = _sha256_file(flow.spec_path)
    config_hash_before = _sha256_file(flow.config_path)
    workspace_before = _workspace_snapshot(root)
    run_id = _evidence_run_id()
    run_dir = root / EVIDENCE_RELATIVE_PATH / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    started_at = _utc_now()
    task_results: list[dict[str, Any]] = []
    reasons: list[str] = []
    for task in selected:
        checks = [_run_check(root, run_dir, task["id"], check) for check in task["checks"]]
        if any(check["status"] != "PASS" for check in checks):
            reasons.append(f"task {task['id']} verification failed")
        task_results.append({"id": task["id"], "criteria": task["criteria"], "checks": checks})

    project_results: list[dict[str, Any]] = []
    if args.all_checks:
        for check_id in flow.required_checks:
            result = _run_check(root, run_dir, "project", flow.project_checks[check_id])
            project_results.append(result)
            if result["status"] != "PASS":
                reasons.append(f"required project check {check_id} failed")

    workspace_after = _workspace_snapshot(root)
    plan_hash_after = _sha256_file(flow.plan_path)
    spec_hash_after = _sha256_file(flow.spec_path)
    config_hash_after = _sha256_file(flow.config_path)
    installation_after: dict[str, Any] | None
    try:
        installation_after = _installed_identity(root)
    except EZPowersError as exc:
        installation_after = None
        reasons.append(f"installed kit changed during verification: {exc}")
    if workspace_before["fingerprint"] != workspace_after["fingerprint"]:
        reasons.append("workspace changed during verification")
    if plan_hash_before != plan_hash_after:
        reasons.append("plan changed during verification")
    if spec_hash_before != spec_hash_after:
        reasons.append("spec changed during verification")
    if config_hash_before != config_hash_after:
        reasons.append("config changed during verification")
    if installation_before != installation_after:
        reasons.append("installed kit identity changed during verification")

    result_path = run_dir / "result.json"
    result: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id,
        "status": "PASS" if not reasons else "FAIL",
        "scope": scope,
        "plan_path": flow.plan_rel,
        "plan_sha256": plan_hash_after,
        "spec_path": _relative(root, flow.spec_path),
        "spec_sha256": spec_hash_after,
        "config_sha256": config_hash_after,
        "installation": installation_after,
        "installation_before": installation_before,
        "workspace": workspace_after,
        "workspace_before": workspace_before,
        "started_at": started_at,
        "finished_at": _utc_now(),
        "tasks": task_results,
        "project_checks": project_results,
        "reasons": reasons,
        "evidence_path": _log_relative(root, result_path),
    }
    result_bytes = _json_bytes(result)
    _atomic_write(result_path, result_bytes)
    digest = _sha256_bytes(result_bytes)
    _atomic_write(result_path.with_name("result.json.sha256"), (digest + "\n").encode("ascii"))

    state = _load_state(root)
    pointer = {"path": result["evidence_path"], "sha256": digest}
    if args.all_checks:
        state["latest_evidence"]["all"] = pointer
    else:
        state["latest_evidence"]["tasks"][args.task] = pointer
    _save_state(root, state)
    _emit(result, args.json)
    return 0 if result["status"] == "PASS" else 1


def _iter_check_results(evidence: dict[str, Any]) -> Iterable[dict[str, Any]]:
    for task in evidence.get("tasks", []):
        if isinstance(task, dict):
            for check in task.get("checks", []):
                if isinstance(check, dict):
                    yield check
    for check in evidence.get("project_checks", []):
        if isinstance(check, dict):
            yield check


def _inventory_reasons(
    flow: Flow,
    evidence: dict[str, Any],
    *,
    task_id: str | None = None,
) -> list[str]:
    reasons: list[str] = []
    expected_tasks = flow.tasks
    expected_project = [flow.project_checks[check_id] for check_id in flow.required_checks]
    if task_id is not None:
        expected_tasks = [task for task in flow.tasks if task["id"] == task_id]
        expected_project = []
        if not expected_tasks:
            reasons.append(f"task evidence is orphaned: {task_id} is not present in the active plan")

    recorded_tasks = evidence.get("tasks")
    if not isinstance(recorded_tasks, list):
        reasons.append("evidence inventory mismatch: tasks must be an array")
        recorded_tasks = []
    elif len(recorded_tasks) != len(expected_tasks):
        reasons.append("evidence inventory mismatch: task count changed")

    fields = ("id", "argv", "cwd", "timeout_seconds", "kind")
    for expected_task, recorded_task in zip(expected_tasks, recorded_tasks):
        if not isinstance(recorded_task, dict):
            reasons.append("evidence inventory mismatch: task result is not an object")
            continue
        expected_task_id = expected_task["id"]
        if recorded_task.get("id") != expected_task_id:
            reasons.append(f"evidence inventory mismatch: expected task {expected_task_id}")
        if recorded_task.get("criteria") != expected_task["criteria"]:
            reasons.append(
                f"evidence inventory mismatch: criteria changed for task {expected_task_id}"
            )
        recorded_checks = recorded_task.get("checks")
        if not isinstance(recorded_checks, list) or len(recorded_checks) != len(expected_task["checks"]):
            reasons.append(
                f"evidence inventory mismatch: check count changed for task {expected_task_id}"
            )
            continue
        for expected_check, recorded_check in zip(expected_task["checks"], recorded_checks):
            if not isinstance(recorded_check, dict):
                reasons.append(
                    f"evidence inventory mismatch: invalid check for task {expected_task_id}"
                )
                continue
            if any(recorded_check.get(field) != expected_check.get(field) for field in fields):
                reasons.append(
                    f"evidence inventory mismatch: metadata changed for check "
                    f"{expected_check['id']} in task {expected_task_id}"
                )

    recorded_project = evidence.get("project_checks")
    if not isinstance(recorded_project, list) or len(recorded_project) != len(expected_project):
        if task_id is None:
            reasons.append("evidence inventory mismatch: required project check count changed")
        else:
            reasons.append("evidence inventory mismatch: task evidence must not contain project checks")
    else:
        for expected_check, recorded_check in zip(expected_project, recorded_project):
            if not isinstance(recorded_check, dict) or any(
                recorded_check.get(field) != expected_check.get(field) for field in fields
            ):
                reasons.append(
                    f"evidence inventory mismatch: required check {expected_check['id']} changed"
                )
    return reasons


def _current_bindings(
    root: pathlib.Path,
    flow: Flow,
) -> tuple[dict[str, Any], list[str]]:
    bindings: dict[str, Any] = {
        "plan_path": flow.plan_rel,
        "spec_path": _relative(root, flow.spec_path),
    }
    reasons: list[str] = []
    try:
        bindings["plan_sha256"] = _sha256_file(flow.plan_path)
        bindings["spec_sha256"] = _sha256_file(flow.spec_path)
        bindings["config_sha256"] = _sha256_file(flow.config_path)
    except OSError as exc:
        reasons.append(f"current plan, spec, or config could not be hashed: {exc}")
    try:
        bindings["installation"] = _installed_identity(root)
    except EZPowersError as exc:
        reasons.append(f"installed kit integrity failed: {exc}")
    try:
        bindings["workspace"] = _workspace_snapshot(root)
    except EZPowersError as exc:
        reasons.append(str(exc))
    return bindings, reasons


def _pointer_freshness(
    root: pathlib.Path,
    flow: Flow,
    pointer: Any,
    *,
    task_id: str | None,
    bindings: tuple[dict[str, Any], list[str]],
) -> tuple[bool, list[str], dict[str, Any] | None, str, pathlib.Path | None]:
    reasons = list(bindings[1])
    if not isinstance(pointer, dict) or not isinstance(pointer.get("path"), str):
        return False, ["evidence pointer is invalid"], None, "", None
    try:
        evidence_path = _contained_path(root, pointer["path"], label="evidence", must_exist=True)
        evidence_root = (root / EVIDENCE_RELATIVE_PATH).resolve()
        evidence_path.resolve().relative_to(evidence_root)
    except (EZPowersError, ValueError) as exc:
        return False, [f"evidence pointer is invalid: {exc}"], None, "", None
    canonical_evidence_path = _log_relative(root, evidence_path)
    if (
        not evidence_path.is_file()
        or evidence_path.name != "result.json"
        or evidence_path.parent.parent.resolve() != evidence_root
        or pointer["path"] != canonical_evidence_path
    ):
        return False, ["evidence pointer is not a canonical run result"], None, "", None
    sidecar = evidence_path.with_name("result.json.sha256")
    if not sidecar.is_file():
        return False, ["evidence tamper detected: result sha256 sidecar is missing"], None, "", None
    actual_hash = _sha256_file(evidence_path)
    expected_hash = sidecar.read_text(encoding="ascii", errors="replace").strip().lower()
    pointer_hash = str(pointer.get("sha256", "")).lower()
    if not re.fullmatch(r"[0-9a-f]{64}", expected_hash) or actual_hash != expected_hash or pointer_hash != actual_hash:
        return False, ["evidence tamper detected: result.json hash mismatch"], None, actual_hash, evidence_path
    try:
        evidence = _read_json(evidence_path)
    except EZPowersError as exc:
        return False, [f"evidence tamper detected: {exc}"], None, actual_hash, evidence_path
    if evidence.get("schema_version") != SCHEMA_VERSION:
        reasons.append("evidence schema_version is unsupported")
    if evidence.get("evidence_path") != canonical_evidence_path:
        reasons.append("evidence self path does not match the state pointer")
    if evidence.get("run_id") != evidence_path.parent.name:
        reasons.append("evidence run_id does not match its run directory")
    expected_scope = "all" if task_id is None else f"task:{task_id}"
    if evidence.get("scope") != expected_scope:
        if task_id is None:
            reasons.append("completion requires all-scope verification evidence")
        else:
            reasons.append(f"evidence scope does not match task {task_id}")
    if evidence.get("status") != "PASS":
        reasons.append(
            "latest all-scope evidence did not PASS"
            if task_id is None
            else f"latest evidence for task {task_id} did not PASS"
        )
    if evidence.get("reasons") != []:
        reasons.append("PASS evidence must have no failure reasons")
    current = bindings[0]
    if evidence.get("plan_path") != current["plan_path"]:
        reasons.append("evidence belongs to a different plan")
    if "plan_sha256" in current and evidence.get("plan_sha256") != current["plan_sha256"]:
        reasons.append("plan changed after verification")
    if evidence.get("spec_path") != current["spec_path"]:
        reasons.append("evidence belongs to a different spec")
    if "spec_sha256" in current and evidence.get("spec_sha256") != current["spec_sha256"]:
        reasons.append("spec changed after verification")
    if "config_sha256" in current and evidence.get("config_sha256") != current["config_sha256"]:
        reasons.append("config changed after verification")
    if "installation" in current and evidence.get("installation") != current["installation"]:
        reasons.append("installed kit changed after verification")
    reasons.extend(_inventory_reasons(flow, evidence, task_id=task_id))
    if "workspace" in current:
        recorded_workspace = evidence.get("workspace", {})
        if (
            not isinstance(recorded_workspace, dict)
            or recorded_workspace.get("fingerprint") != current["workspace"]["fingerprint"]
        ):
            reasons.append("workspace changed after verification")
        if evidence.get("workspace_before") != recorded_workspace:
            reasons.append("workspace changed during recorded verification")
    if evidence.get("installation_before") != evidence.get("installation"):
        reasons.append("installed kit changed during recorded verification")
    seen_logs: set[str] = set()
    for check in _iter_check_results(evidence):
        if (
            check.get("status") != "PASS"
            or check.get("exit_code") != 0
            or check.get("timed_out") is not False
            or check.get("spawn_error") != ""
        ):
            reasons.append(f"check is not a recorded PASS: {check.get('id', '?')}")
        for stream_name in ("stdout", "stderr"):
            relative_name = check.get(f"{stream_name}_log")
            expected = check.get(f"{stream_name}_sha256")
            if not isinstance(relative_name, str) or not isinstance(expected, str):
                reasons.append(f"log tamper detected: missing {stream_name} metadata for {check.get('id', '?')}")
                continue
            try:
                log_path = _contained_path(root, relative_name, label=f"{stream_name} log", must_exist=True)
                log_path.resolve().relative_to((root / EVIDENCE_RELATIVE_PATH).resolve())
            except (EZPowersError, ValueError):
                reasons.append(f"log tamper detected: invalid {stream_name} log for {check.get('id', '?')}")
                continue
            if not log_path.is_file() or log_path.parent.resolve() != evidence_path.parent.resolve():
                reasons.append(f"log tamper detected: {stream_name} log is outside the evidence run")
                continue
            canonical_log = _log_relative(root, log_path)
            if relative_name != canonical_log:
                reasons.append(f"log tamper detected: {stream_name} log path is not canonical")
                continue
            if canonical_log in seen_logs:
                reasons.append(f"log tamper detected: duplicate log path {canonical_log}")
                continue
            seen_logs.add(canonical_log)
            if _sha256_file(log_path) != expected:
                reasons.append(f"log tamper detected: {stream_name} hash mismatch for {check.get('id', '?')}")
    return not reasons, reasons, evidence, actual_hash, evidence_path


def _freshness(
    root: pathlib.Path,
    flow: Flow,
    *,
    state: dict[str, Any] | None = None,
    bindings: tuple[dict[str, Any], list[str]] | None = None,
) -> tuple[bool, list[str], dict[str, Any] | None, str, pathlib.Path | None]:
    if state is None:
        try:
            state = _load_state(root)
        except EZPowersError as exc:
            return False, [str(exc)], None, "", None
    pointer = state["latest_evidence"].get("all")
    if not isinstance(pointer, dict) or not isinstance(pointer.get("path"), str):
        return False, ["no all-scope verification evidence"], None, "", None
    if bindings is None:
        bindings = _current_bindings(root, flow)
    return _pointer_freshness(
        root,
        flow,
        pointer,
        task_id=None,
        bindings=bindings,
    )


def _task_evidence_entry(
    root: pathlib.Path,
    flow: Flow,
    task_id: str,
    pointer: Any,
    bindings: tuple[dict[str, Any], list[str]],
) -> dict[str, Any]:
    scope = f"task:{task_id}"
    if pointer is None:
        return {
            "status": "MISSING",
            "fresh": False,
            "scope": scope,
            "evidence_path": None,
            "evidence_sha256": None,
            "reasons": ["no task-scope verification evidence"],
        }
    fresh, reasons, _, evidence_hash, evidence_path = _pointer_freshness(
        root,
        flow,
        pointer,
        task_id=task_id,
        bindings=bindings,
    )
    return {
        "status": "FRESH_PASS" if fresh else "STALE",
        "fresh": fresh,
        "scope": scope,
        "evidence_path": _log_relative(root, evidence_path) if evidence_path is not None else None,
        "evidence_sha256": evidence_hash or None,
        "reasons": reasons,
    }


def _task_evidence_payload(
    root: pathlib.Path,
    flow: Flow,
    state: dict[str, Any],
    bindings: tuple[dict[str, Any], list[str]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    pointers = state["latest_evidence"]["tasks"]
    current_ids = {task["id"] for task in flow.tasks}
    task_evidence: dict[str, Any] = {}
    for task in flow.tasks:
        task_id = task["id"]
        task_evidence[task_id] = _task_evidence_entry(
            root,
            flow,
            task_id,
            pointers.get(task_id),
            bindings,
        )

    orphan_evidence: dict[str, Any] = {}
    for task_id in sorted(set(pointers) - current_ids):
        entry = _task_evidence_entry(root, flow, task_id, pointers[task_id], bindings)
        entry["status"] = "ORPHAN"
        entry["fresh"] = False
        orphan_reason = f"task is not present in the active plan: {task_id}"
        if orphan_reason not in entry["reasons"]:
            entry["reasons"].insert(0, orphan_reason)
        orphan_evidence[task_id] = entry
    return task_evidence, orphan_evidence


def _certify_command(args: argparse.Namespace) -> int:
    root = _runtime_project_root()
    with _runtime_lock(root):
        return _certify_command_locked(args, root)


def _certify_command_locked(args: argparse.Namespace, root: pathlib.Path) -> int:
    flow = _validate_flow(root, args.plan)
    if flow.errors:
        payload = {"status": "FAIL", "reasons": flow.errors, "plan": str(args.plan)}
        _emit(payload, args.json)
        return 2
    state = _load_state(root)
    if state.get("active_plan") != flow.plan_rel:
        payload = {
            "status": "FAIL",
            "plan": flow.plan_rel,
            "fresh": False,
            "reasons": [
                "plan is not active; run validate --plan <plan-path> --activate "
                "or verify that plan before certification"
            ],
        }
        _emit(payload, args.json)
        return 2
    fresh, reasons, evidence, evidence_hash, validated_evidence_path = _freshness(
        root,
        flow,
        state=state,
    )
    payload: dict[str, Any] = {
        "status": "PASS" if fresh else "FAIL",
        "plan": flow.plan_rel,
        "fresh": fresh,
        "reasons": reasons,
    }
    if fresh and evidence is not None and validated_evidence_path is not None:
        certificate = {
            "schema_version": SCHEMA_VERSION,
            "status": "PASS",
            "plan_path": flow.plan_rel,
            "plan_sha256": evidence["plan_sha256"],
            "spec_path": evidence["spec_path"],
            "spec_sha256": evidence["spec_sha256"],
            "config_sha256": evidence["config_sha256"],
            "installation": evidence["installation"],
            "workspace": evidence["workspace"],
            "evidence_path": evidence["evidence_path"],
            "evidence_sha256": evidence_hash,
            "certified_at": _utc_now(),
        }
        certificate_path = validated_evidence_path.with_name("certificate.json")
        _write_json(certificate_path, certificate)
        certificate_hash = _sha256_file(certificate_path)
        state = _load_state(root)
        state["latest_certificate"] = {
            "path": _log_relative(root, certificate_path),
            "evidence_sha256": evidence_hash,
            "sha256": certificate_hash,
        }
        _save_state(root, state)
        payload["certificate_path"] = _log_relative(root, certificate_path)
    _emit(payload, args.json)
    return 0 if fresh else 1


def _status_payload(root: pathlib.Path) -> tuple[dict[str, Any], int]:
    try:
        state = _load_state(root)
    except EZPowersError as exc:
        return {"status": "FAIL", "fresh": False, "reasons": [str(exc)]}, 2
    active = state.get("active_plan")
    if not isinstance(active, str) or not active:
        try:
            _installed_identity(root)
            config = _read_json(root / CONFIG_RELATIVE_PATH)
        except EZPowersError as exc:
            return {
                "status": "FAIL",
                "fresh": False,
                "active_plan": None,
                "reasons": [str(exc)],
            }, 2
        config_errors: list[str] = []
        _validate_config_value(root, config, config_errors)
        if config_errors:
            return {
                "status": "FAIL",
                "fresh": False,
                "active_plan": None,
                "reasons": config_errors,
            }, 2
        return {
            "status": "UNCONFIGURED",
            "fresh": False,
            "active_plan": None,
            "reasons": ["no active plan"],
        }, 0
    flow = _validate_flow(root, active)
    if flow.errors:
        return {
            "status": "FAIL",
            "fresh": False,
            "active_plan": active,
            "reasons": flow.errors,
        }, 2
    bindings = _current_bindings(root, flow)
    fresh, reasons, evidence, evidence_hash, validated_evidence_path = _freshness(
        root,
        flow,
        state=state,
        bindings=bindings,
    )
    task_evidence, orphan_task_evidence = _task_evidence_payload(
        root,
        flow,
        state,
        bindings,
    )
    certified = False
    certificate_pointer = state.get("latest_certificate")
    if fresh and isinstance(certificate_pointer, dict):
        certificate_path = certificate_pointer.get("path")
        if isinstance(certificate_path, str) and validated_evidence_path is not None:
            try:
                resolved_certificate = _contained_path(root, certificate_path, label="certificate", must_exist=True)
                canonical_certificate = _log_relative(root, resolved_certificate)
                if (
                    not resolved_certificate.is_file()
                    or resolved_certificate.name != "certificate.json"
                    or resolved_certificate.parent.resolve()
                    != validated_evidence_path.parent.resolve()
                    or certificate_path != canonical_certificate
                ):
                    raise EZPowersError("certificate pointer is not the canonical evidence sibling")
                certificate = _read_json(resolved_certificate)
                certified = (
                    _sha256_file(resolved_certificate) == certificate_pointer.get("sha256")
                    and evidence is not None
                    and certificate_pointer.get("evidence_sha256") == evidence_hash
                    and certificate.get("status") == "PASS"
                    and certificate.get("plan_path") == evidence.get("plan_path")
                    and certificate.get("plan_sha256") == evidence.get("plan_sha256")
                    and certificate.get("spec_path") == evidence.get("spec_path")
                    and certificate.get("spec_sha256") == evidence.get("spec_sha256")
                    and certificate.get("config_sha256") == evidence.get("config_sha256")
                    and certificate.get("installation") == evidence.get("installation")
                    and certificate.get("workspace") == evidence.get("workspace")
                    and certificate.get("evidence_path") == evidence.get("evidence_path")
                    and certificate.get("evidence_sha256") == evidence_hash
                )
                if not certified:
                    reasons.append("certificate tamper detected: certificate binding mismatch")
            except (EZPowersError, ValueError) as exc:
                reasons.append(f"certificate pointer is invalid: {exc}")
        else:
            reasons.append("certificate pointer is invalid")
    elif fresh and certificate_pointer is not None:
        reasons.append("certificate pointer is invalid")
    return {
        "status": "CERTIFIED" if fresh and certified else ("READY" if fresh else "STALE"),
        "fresh": fresh,
        "certified": certified,
        "active_plan": active,
        "reasons": reasons,
        "task_evidence": task_evidence,
        "orphan_task_evidence": orphan_task_evidence,
    }, 0


def _status_command(args: argparse.Namespace) -> int:
    root = _runtime_project_root()
    payload, code = _status_payload(root)
    _emit(payload, args.json)
    return code


def _hook_command(args: argparse.Namespace) -> int:
    # Consume the event so a producer never blocks on a full pipe.  Completion
    # authority comes only from project-local state and evidence.
    with contextlib.suppress(Exception):
        sys.stdin.read()
    root = _runtime_project_root()
    payload, _ = _status_payload(root)
    unconfigured = payload.get("status") == "UNCONFIGURED"
    allow = unconfigured or (bool(payload.get("fresh")) and bool(payload.get("certified")))
    if unconfigured:
        reason = "no active EZPowers plan"
    elif allow:
        reason = "fresh certified EZPowers completion evidence"
    elif payload.get("fresh"):
        reason = "EZPowers completion evidence is fresh but not certified"
    else:
        reason = "; ".join(payload.get("reasons", [])) or "EZPowers completion evidence is not fresh"
    response: dict[str, Any] = {}
    if not allow:
        response["decision"] = "block"
        response["reason"] = reason
    print(json.dumps(response, ensure_ascii=False))
    return 0


def _runtime_project_root() -> pathlib.Path:
    script = pathlib.Path(__file__).resolve()
    if script.parent.name == ".ezpowers":
        return script.parent.parent.resolve()
    return pathlib.Path.cwd().resolve()


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    install = subparsers.add_parser("install", help="Install or refresh the project-local kit")
    install.add_argument("--project-root", required=True)
    install.add_argument("--refresh", action="store_true")
    install.add_argument("--enable-hooks", choices=("none", "claude", "codex", "both"), default="none")
    install.set_defaults(handler=_install)

    validate = subparsers.add_parser("validate", help="Validate a managed spec or plan")
    validate_target = validate.add_mutually_exclusive_group(required=True)
    validate_target.add_argument("--plan")
    validate_target.add_argument("--spec")
    validate.add_argument(
        "--activate",
        action="store_true",
        help="Set a valid plan as the resume target; valid only with --plan",
    )
    validate.add_argument("--json", action="store_true")
    validate.set_defaults(handler=_validate_command)

    status = subparsers.add_parser("status", help="Show current evidence freshness")
    status.add_argument("--json", action="store_true")
    status.set_defaults(handler=_status_command)

    verify = subparsers.add_parser("verify", help="Run deterministic project checks")
    verify.add_argument("--plan", required=True)
    scope = verify.add_mutually_exclusive_group(required=True)
    scope.add_argument("--task")
    scope.add_argument("--all", action="store_true", dest="all_checks")
    verify.add_argument("--json", action="store_true")
    verify.set_defaults(handler=_verify_command)

    certify = subparsers.add_parser("certify", help="Certify fresh all-scope evidence")
    certify.add_argument("--plan", required=True)
    certify.add_argument("--json", action="store_true")
    certify.set_defaults(handler=_certify_command)

    hook = subparsers.add_parser("hook", help="Map the core completion verdict to a host hook")
    hook.add_argument("--host", required=True, choices=("claude", "codex"))
    hook.set_defaults(handler=_hook_command)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        return int(args.handler(args))
    except InstallConflict as exc:
        print(str(exc), file=sys.stderr)
        return 3
    except EZPowersError as exc:
        as_json = bool(getattr(args, "json", False))
        if as_json:
            print(json.dumps({"status": "FAIL", "errors": [str(exc)], "reasons": [str(exc)]}, ensure_ascii=False, indent=2))
        else:
            print(f"EZPowers error: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("EZPowers interrupted", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
