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
import concurrent.futures
import contextlib
import datetime as dt
import hashlib
import json
import os
import pathlib
import re
import shlex
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
import unicodedata
import uuid
from dataclasses import dataclass
from typing import Any, Iterable, Iterator


SCHEMA_VERSION = 1
PLANNING_SCHEMA_VERSION = 3
PLAN_SCHEMA_VERSIONS = {1, 2, PLANNING_SCHEMA_VERSION}
CONFIG_SCHEMA_VERSIONS = {1, 2, PLANNING_SCHEMA_VERSION}
ASSURANCE_GRAPH_SCHEMA_VERSION = 1
PLANNING_ASSURANCE_GRAPH_SCHEMA_VERSION = 2
GRAPH_BOUND_SCHEMA_VERSION = 2
PLANNING_EVIDENCE_SCHEMA_VERSION = 3
KIT_RELATIVE_PATH = pathlib.Path("project-kit/v5.8.0/manifest.json")
CONFIG_RELATIVE_PATH = pathlib.Path(".ezpowers/config.json")
STATE_RELATIVE_PATH = pathlib.Path(".ezpowers/state.json")
LEDGER_RELATIVE_PATH = pathlib.Path(".ezpowers/ledger.json")
CHAIN_RELATIVE_PATH = pathlib.Path(".ezpowers/chain.json")
CHAIN_APPROVALS_RELATIVE_PATH = pathlib.Path(".ezpowers/approvals")
CHAIN_EVIDENCE_RELATIVE_PATH = pathlib.Path(".ezpowers/evidence/chain")
DOCS_RELATIVE_PATH = pathlib.Path(".ezpowers/docs.json")
DOCS_STAGING_RELATIVE_PATH = pathlib.Path(".ezpowers/staging")
DOCS_BACKUP_RELATIVE_PATH = pathlib.Path(".ezpowers/backups/docs")
WIKI_RELATIVE_PATH = pathlib.Path(".ezpowers/wiki")
INSTALLED_MANIFEST_RELATIVE_PATH = pathlib.Path(".ezpowers/kit/manifest.json")
EVIDENCE_RELATIVE_PATH = pathlib.Path(".ezpowers/evidence")
LOCK_RELATIVE_PATH = pathlib.Path(".ezpowers/runtime.lock")
LOCK_TIMEOUT_SECONDS = 1.0
LOCK_POLL_SECONDS = 0.05
ID_RE = re.compile(r"^[A-Za-z][A-Za-z0-9._-]{0,63}$")
RESOURCE_LOCK_RE = re.compile(r"^[A-Za-z][A-Za-z0-9._-]{0,127}$")
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
DOCS_CHECK_ID = "ezpowers.docs"
DESIGN_CHECK_ID = "ezpowers.design"
DEFAULT_DESIGN_PROFILE = "google-alpha-0.4.0-ezpowers-1"
DOCS_ALLOWED_ROOT_FILES = {"AGENTS.md", "ARCHITECTURE.md", "CLAUDE.md"}
DOCS_AUTHORITIES = {"canonical", "supporting", "derived"}
DOCS_STATUSES = {"draft", "active"}
DOCS_OWNERS = {"ezpowers", "external"}
DOCS_VALIDATORS = {"markdown", "spec", "plan", "design-md"}
DOCS_LINK_RELATIONS = {"imports", "indexes", "parent", "references"}
DOCS_RESERVED_DESIGN_PARTS = {
    ".git",
    ".ezpowers",
    ".agents",
    ".claude",
    ".cache",
    "node_modules",
    "dist",
    "build",
    "target",
}
WIKI_CATEGORIES = {
    "architecture",
    "decision",
    "convention",
    "debugging",
    "environment",
    "verification",
    "reference",
    "session-log",
}
WIKI_PAGE_STATUSES = {"candidate", "promoted", "archived"}
WIKI_RESERVED_FILES = {"index.md", "log.md"}
CHAIN_OPTIONAL_STAGES = {
    "deep_interview",
    "frontend_design",
    "design_architecture",
}
CHAIN_STAGE_MODES = {"auto", "always"}
CHAIN_HOSTS = {"claude", "codex"}
CHAIN_RISKS = {
    "user_facing",
    "integration",
    "regression_risk",
    "security",
    "delivery",
}
CHAIN_QA_RISKS = {"user_facing", "integration", "regression_risk"}
CHAIN_GATE_KINDS = {
    "oracle-audit",
    "artifact-review",
    "code-review",
    "adversarial-qa",
    "blocker-review",
}
CHAIN_NON_OBSERVABLE_BOUNDARIES = {
    "file presence",
    "model assertion",
    "prose",
    "self report",
    "source",
    "source code",
    "source presence",
    "source-presence",
    "string",
    "string presence",
    "string-presence",
    "test name",
    "test-name",
}
CHAIN_TERMINAL_STATUSES = {
    "NEEDS_REAPPROVAL",
    "BLOCKED",
    "FAILED",
    "CERTIFIED",
}
CHAIN_LIMIT_DEFAULTS = {
    "total_iterations": 10,
    "qa_cycles": 5,
    "validation_retries": 3,
    "review_retries": 3,
    "identical_error_repeats": 3,
}
CHAIN_LIMIT_RANGES = {
    "total_iterations": (1, 100),
    "qa_cycles": (1, 50),
    "validation_retries": (1, 25),
    "review_retries": (1, 25),
    "identical_error_repeats": (1, 25),
}
HOST_MIN_VERSIONS = {
    "claude": (2, 1, 217),
    "codex": (0, 145, 0),
}
HOST_VERSION_RE = re.compile(r"(?<!\d)(\d+)\.(\d+)\.(\d+)(?!\d)")


class EZPowersError(RuntimeError):
    """Expected user-facing runtime error."""


class InstallConflict(EZPowersError):
    """A managed target contains user-owned changes."""


@dataclass(frozen=True)
class ProjectProfilePolicy:
    """Profile variation hidden from the shared execution/evidence core."""

    name: str
    plan_schema_versions: frozenset[int]
    primary_review_kind: str
    assurance_graph_schema_version: int
    chain_bundle_schema_version: int
    chain_approval_schema_version: int


SOFTWARE_PROFILE = ProjectProfilePolicy(
    name="software",
    plan_schema_versions=frozenset({1, 2}),
    primary_review_kind="code-review",
    assurance_graph_schema_version=ASSURANCE_GRAPH_SCHEMA_VERSION,
    chain_bundle_schema_version=SCHEMA_VERSION,
    chain_approval_schema_version=GRAPH_BOUND_SCHEMA_VERSION,
)
PLANNING_PROFILE = ProjectProfilePolicy(
    name="planning",
    plan_schema_versions=frozenset({PLANNING_SCHEMA_VERSION}),
    primary_review_kind="artifact-review",
    assurance_graph_schema_version=PLANNING_ASSURANCE_GRAPH_SCHEMA_VERSION,
    chain_bundle_schema_version=2,
    chain_approval_schema_version=PLANNING_SCHEMA_VERSION,
)
PROJECT_PROFILE_POLICIES = {
    SOFTWARE_PROFILE.name: SOFTWARE_PROFILE,
    PLANNING_PROFILE.name: PLANNING_PROFILE,
}


@dataclass
class Flow:
    root: pathlib.Path
    plan_path: pathlib.Path
    plan_rel: str
    spec_path: pathlib.Path
    config_path: pathlib.Path
    config: dict[str, Any]
    profile: ProjectProfilePolicy
    spec: dict[str, Any]
    plan: dict[str, Any]
    inputs: list[dict[str, Any]]
    deliverables: list[dict[str, Any]]
    tasks: list[dict[str, Any]]
    project_checks: dict[str, dict[str, Any]]
    required_checks: list[str]
    plan_schema_version: int
    config_schema_version: int
    max_parallel_checks: int
    task_waves: list[list[str]]
    assurance_graph: dict[str, Any]
    assurance_graph_sha256: str
    errors: list[str]


def _flow_graph_bound(flow: Flow) -> bool:
    return flow.plan_schema_version >= 2


def _flow_evidence_schema_version(flow: Flow) -> int:
    if flow.profile.name == "planning":
        return PLANNING_EVIDENCE_SCHEMA_VERSION
    return GRAPH_BOUND_SCHEMA_VERSION if _flow_graph_bound(flow) else SCHEMA_VERSION


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


def _read_json_argument(value: str, label: str) -> dict[str, Any]:
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as exc:
        raise EZPowersError(f"{label} must be a JSON object: {exc}") from exc
    if not isinstance(parsed, dict):
        raise EZPowersError(f"{label} must be a JSON object")
    return parsed


def _parse_markdown_frontmatter(text: str, label: str) -> tuple[dict[str, Any], str]:
    normalized = text.replace("\r\n", "\n")
    if not normalized.startswith("---\n"):
        raise EZPowersError(f"{label} must start with YAML frontmatter")
    end = normalized.find("\n---\n", 4)
    if end < 0:
        raise EZPowersError(f"{label} frontmatter is not closed")
    values: dict[str, Any] = {}
    for line in normalized[4:end].splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if ":" not in line:
            raise EZPowersError(f"{label} frontmatter line is invalid: {line!r}")
        key, raw = line.split(":", 1)
        key = key.strip()
        raw = raw.strip()
        if not re.fullmatch(r"[a-z][a-z0-9_]*", key):
            raise EZPowersError(f"{label} frontmatter key is invalid: {key!r}")
        if key in values:
            raise EZPowersError(f"{label} frontmatter key is duplicated: {key}")
        try:
            values[key] = json.loads(raw)
        except json.JSONDecodeError:
            values[key] = raw
    return values, normalized[end + 5 :]


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
        "chain_hosts": {},
        "chain_gates": {"pending": None, "receipts": {}, "consumed": {}},
        "chain_run": None,
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
    chain_hosts = state.setdefault("chain_hosts", {})
    if not isinstance(chain_hosts, dict):
        raise EZPowersError(".ezpowers/state.json chain_hosts must be an object")
    chain_gates = state.setdefault(
        "chain_gates",
        {"pending": None, "receipts": {}},
    )
    if not isinstance(chain_gates, dict):
        raise EZPowersError(".ezpowers/state.json chain_gates must be an object")
    chain_gates.setdefault("pending", None)
    receipts = chain_gates.setdefault("receipts", {})
    if not isinstance(receipts, dict):
        raise EZPowersError(".ezpowers/state.json chain_gates.receipts must be an object")
    consumed = chain_gates.setdefault("consumed", {})
    if not isinstance(consumed, dict):
        raise EZPowersError(".ezpowers/state.json chain_gates.consumed must be an object")
    state.setdefault("chain_run", None)
    if state["chain_run"] is not None and not isinstance(state["chain_run"], dict):
        raise EZPowersError(".ezpowers/state.json chain_run must be an object or null")
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


def _prepare_config(
    project_root: pathlib.Path,
    requested_profile: str | None,
) -> tuple[dict[str, Any] | None, bool]:
    config_path = project_root / CONFIG_RELATIVE_PATH
    if not config_path.exists():
        config: dict[str, Any] = {
            "schema_version": 2,
            "project_name": project_root.name,
            "verification": {"max_parallel_checks": 4},
            "checks": {},
            "required_checks": [],
        }
        if requested_profile == PLANNING_PROFILE.name:
            config["schema_version"] = PLANNING_SCHEMA_VERSION
            config["project_profile"] = PLANNING_PROFILE.name
        return config, False

    current = _read_json(config_path)
    errors: list[str] = []
    _, _, _, _, current_profile = _validate_config_value(
        project_root,
        current,
        errors,
    )
    if errors:
        raise EZPowersError(
            "invalid .ezpowers/config.json:\n- " + "\n- ".join(errors)
        )
    if requested_profile is None or requested_profile == current_profile.name:
        return None, False

    updated = dict(current)
    updated["schema_version"] = PLANNING_SCHEMA_VERSION
    updated["project_profile"] = requested_profile
    if "verification" not in updated:
        updated["verification"] = {"max_parallel_checks": 1}
    return updated, True


def _invalidate_profile_transition(
    project_root: pathlib.Path,
    *,
    requested_profile: str,
) -> None:
    state_path = project_root / STATE_RELATIVE_PATH
    if not state_path.is_file():
        return
    state = _load_state(project_root)
    state["latest_evidence"] = {"all": None, "tasks": {}}
    state["latest_certificate"] = None
    run = state.get("chain_run")
    if (
        isinstance(run, dict)
        and run.get("status") not in CHAIN_TERMINAL_STATUSES
    ):
        _chain_mark_reapproval(
            state,
            [
                "project profile changed to "
                f"{requested_profile}; explicit chain reapproval is required"
            ],
        )
    _save_state(project_root, state)


def _owned_hook(entry: Any, host: str, feature: str) -> bool:
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
        if feature == "completion":
            has_feature = (
                isinstance(args, list) and "hook" in args
            ) or any(
                isinstance(command, str)
                and re.search(r"(?:^|\s)hook(?:\s|$)", command)
                for command in command_fields
            )
        else:
            has_feature = (
                isinstance(args, list)
                and any(
                    args[index : index + 2] == ["wiki", "capture"]
                    for index in range(max(0, len(args) - 1))
                )
            ) or any(
                isinstance(command, str)
                and re.search(r"(?:^|\s)wiki\s+capture(?:\s|$)", command)
                for command in command_fields
            )
        if not has_feature:
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


def _hook_update(
    project_root: pathlib.Path,
    host: str,
    features: set[str],
) -> tuple[pathlib.Path, bytes]:
    path = project_root / (".claude/settings.json" if host == "claude" else ".codex/hooks.json")
    value = _read_json(path, required=False) if path.exists() else {}
    hooks = value.setdefault("hooks", {})
    if not isinstance(hooks, dict):
        raise InstallConflict(f"conflict: {path} hooks field is not an object")
    definitions = {
        "completion": ("Stop", ["hook"], 30),
        "wiki": ("SessionEnd", ["wiki", "capture"], 5),
    }
    for feature in sorted(features):
        event_name, command_args, timeout = definitions[feature]
        event_hooks = hooks.setdefault(event_name, [])
        if not isinstance(event_hooks, list):
            raise InstallConflict(f"conflict: {path} hooks.{event_name} field is not an array")
        argv = [
            sys.executable,
            str((project_root / ".ezpowers" / "ezpowers.py").resolve()),
            *command_args,
            "--host",
            host,
        ]
        if host == "claude":
            handler = {
                "type": "command",
                "command": argv[0],
                "args": argv[1:],
                "timeout": timeout,
            }
            desired: dict[str, Any] = {"matcher": "", "hooks": [handler]}
        else:
            handler = {
                "type": "command",
                "command": shlex.join(argv),
                "commandWindows": subprocess.list2cmdline(argv),
                "timeout": timeout,
            }
            desired = {"hooks": [handler]}
        owned_indices = [
            index
            for index, item in enumerate(event_hooks)
            if _owned_hook(item, host, feature)
        ]
        if owned_indices:
            event_hooks[owned_indices[0]] = desired
            for index in reversed(owned_indices[1:]):
                event_hooks.pop(index)
        else:
            event_hooks.append(desired)
    return path, _json_bytes(value)


def _command_mentions_chain_hook(candidate: Any, host: str) -> bool:
    if not isinstance(candidate, dict):
        return False
    candidates = [candidate]
    nested = candidate.get("hooks")
    if isinstance(nested, list):
        candidates.extend(item for item in nested if isinstance(item, dict))
    for item in candidates:
        args = item.get("args")
        commands = (item.get("command"), item.get("commandWindows"))
        if isinstance(args, list):
            joined = "\0".join(str(value) for value in args)
            if (
                "ezpowers.py" in joined
                and "\0chain\0hook\0" in f"\0{joined}\0"
                and f"\0--host\0{host}\0" in f"\0{joined}\0"
            ):
                return True
        for command in commands:
            if (
                isinstance(command, str)
                and "ezpowers.py" in command
                and re.search(r"(?:^|\s)chain\s+hook(?:\s|$)", command)
                and re.search(rf"--host\s+{re.escape(host)}(?:\s|$)", command)
            ):
                return True
    return False


def _chain_hook_handler(project_root: pathlib.Path, host: str) -> dict[str, Any]:
    argv = [
        sys.executable,
        str((project_root / ".ezpowers" / "ezpowers.py").resolve()),
        "chain",
        "hook",
        "--host",
        host,
    ]
    if host == "claude":
        return {
            "type": "command",
            "command": argv[0],
            "args": argv[1:],
            "timeout": 30,
        }
    return {
        "type": "command",
        "command": shlex.join(argv),
        "commandWindows": subprocess.list2cmdline(argv),
        "timeout": 30,
    }


def _chain_hook_matcher(host: str, event_name: str) -> str | None:
    if event_name == "SessionStart":
        return "startup|resume|clear|compact"
    if event_name == "PreToolUse":
        return "Bash|Write|Edit|apply_patch"
    if event_name in {"SubagentStart", "SubagentStop"}:
        return ""
    if host == "claude":
        return ""
    return None


def _chain_hook_update(
    project_root: pathlib.Path,
    host: str,
) -> tuple[pathlib.Path, bytes, list[str]]:
    path = project_root / (
        ".claude/settings.json" if host == "claude" else ".codex/hooks.json"
    )
    value = _read_json(path, required=False) if path.exists() else {}
    hooks = value.setdefault("hooks", {})
    if not isinstance(hooks, dict):
        raise InstallConflict(f"conflict: {path} hooks field is not an object")

    conflicts: list[str] = []
    handler = _chain_hook_handler(project_root, host)
    for event_name in (
        "SessionStart",
        "Stop",
        "PreToolUse",
        "SubagentStart",
        "SubagentStop",
    ):
        event_hooks = hooks.setdefault(event_name, [])
        if not isinstance(event_hooks, list):
            raise InstallConflict(
                f"conflict: {path} hooks.{event_name} field is not an array"
            )
        preserved: list[Any] = []
        for entry in event_hooks:
            if _command_mentions_chain_hook(entry, host):
                continue
            if event_name == "Stop" and _owned_hook(entry, host, "completion"):
                continue
            preserved.append(entry)
            if event_name == "Stop":
                conflicts.append(
                    f"{_relative(project_root, path)} contains a non-EZPowers Stop hook"
                )
        matcher = _chain_hook_matcher(host, event_name)
        desired: dict[str, Any] = {"hooks": [dict(handler)]}
        if matcher is not None:
            desired["matcher"] = matcher
        preserved.append(desired)
        hooks[event_name] = preserved
    return path, _json_bytes(value), sorted(set(conflicts))


def _chain_hook_remove(
    project_root: pathlib.Path,
    host: str,
) -> tuple[pathlib.Path, bytes] | None:
    path = project_root / (
        ".claude/settings.json" if host == "claude" else ".codex/hooks.json"
    )
    if not path.is_file():
        return None
    value = _read_json(path)
    hooks = value.get("hooks")
    if not isinstance(hooks, dict):
        raise InstallConflict(f"conflict: {path} hooks field is not an object")
    changed = False
    for event_name in (
        "SessionStart",
        "Stop",
        "PreToolUse",
        "SubagentStart",
        "SubagentStop",
    ):
        entries = hooks.get(event_name)
        if entries is None:
            continue
        if not isinstance(entries, list):
            raise InstallConflict(
                f"conflict: {path} hooks.{event_name} field is not an array"
            )
        preserved = [
            entry
            for entry in entries
            if not _command_mentions_chain_hook(entry, host)
        ]
        if len(preserved) == len(entries):
            continue
        changed = True
        if preserved:
            hooks[event_name] = preserved
        else:
            hooks.pop(event_name, None)
    if not changed:
        return None
    if not hooks:
        value.pop("hooks", None)
    return path, _json_bytes(value)


def _chain_owned_hook_entries(
    project_root: pathlib.Path,
    host: str,
) -> dict[str, Any]:
    path, data, _ = _chain_hook_update(project_root, host)
    del path
    value = json.loads(data.decode("utf-8"))
    result: dict[str, Any] = {}
    for event_name in (
        "SessionStart",
        "Stop",
        "PreToolUse",
        "SubagentStart",
        "SubagentStop",
    ):
        entries = value.get("hooks", {}).get(event_name, [])
        result[event_name] = [
            item
            for item in entries
            if _command_mentions_chain_hook(item, host)
        ]
    return result


def _chain_hook_identity(
    project_root: pathlib.Path,
    host: str,
    chain_sha256: str,
) -> str:
    payload = {
        "host": host,
        "chain_sha256": chain_sha256,
        "hooks": _chain_owned_hook_entries(project_root, host),
    }
    return _sha256_bytes(_json_bytes(payload))


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


def _host_prerequisite(host: str) -> dict[str, Any]:
    minimum = HOST_MIN_VERSIONS[host]
    required = ".".join(str(part) for part in minimum)
    executable = shutil.which(host)
    if executable is None:
        return {
            "host": host,
            "required": required,
            "installed": None,
            "status": "MISSING",
            "message": f"{host} CLI {required} or newer is required",
        }
    try:
        result = subprocess.run(
            [executable, "--version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=15,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {
            "host": host,
            "required": required,
            "installed": None,
            "status": "UNAVAILABLE",
            "message": f"cannot inspect {host} CLI version: {exc}",
        }
    output = "\n".join(
        part for part in (result.stdout, result.stderr) if part
    ).strip()
    match = HOST_VERSION_RE.search(output)
    if result.returncode != 0 or match is None:
        return {
            "host": host,
            "required": required,
            "installed": None,
            "status": "UNPARSEABLE",
            "message": (
                f"cannot parse {host} CLI version from "
                f"{output or 'empty output'}"
            ),
        }
    installed_tuple = tuple(int(part) for part in match.groups())
    installed = ".".join(str(part) for part in installed_tuple)
    if installed_tuple < minimum:
        return {
            "host": host,
            "required": required,
            "installed": installed,
            "status": "OUTDATED",
            "message": (
                f"{host} CLI {installed} is older than required {required}"
            ),
        }
    return {
        "host": host,
        "required": required,
        "installed": installed,
        "status": "PASS",
        "message": f"{host} CLI {installed} satisfies the minimum",
    }


def _host_prerequisites(hosts: Iterable[str]) -> list[dict[str, Any]]:
    return [_host_prerequisite(host) for host in sorted(set(hosts))]


def _require_host_prerequisites(hosts: Iterable[str]) -> None:
    prerequisites = _host_prerequisites(hosts)
    failures = [
        str(item["message"])
        for item in prerequisites
        if item["status"] != "PASS"
    ]
    if failures:
        raise EZPowersError(
            "host prerequisite check failed:\n- " + "\n- ".join(failures)
        )


def _install(args: argparse.Namespace) -> int:
    project_root = pathlib.Path(args.project_root).resolve()
    if not project_root.is_dir():
        raise EZPowersError(f"project root does not exist: {project_root}")
    _require_git_worktree_root(project_root)
    requested_hosts = {
        host
        for host in CHAIN_HOSTS
        if args.enable_hooks in {host, "both"}
        or args.enable_wiki_hooks in {host, "both"}
    }
    _require_host_prerequisites(requested_hosts)
    with _runtime_lock(project_root):
        return _install_locked(args, project_root)


def _mark_legacy_chain_reapproval_after_refresh(project_root: pathlib.Path) -> None:
    state_path = project_root / STATE_RELATIVE_PATH
    if not state_path.is_file():
        return
    state = _load_state(project_root)
    run = state.get("chain_run")
    if (
        not isinstance(run, dict)
        or run.get("status") in CHAIN_TERMINAL_STATUSES
    ):
        return
    approval_name = run.get("approval_path")
    if not isinstance(approval_name, str):
        return
    try:
        approval_path = _contained_path(
            project_root,
            approval_name,
            label="legacy chain approval",
            must_exist=True,
        )
        approval = _read_json(approval_path)
    except EZPowersError:
        return
    if isinstance(approval.get("assurance_graph_sha256"), str):
        return
    _chain_mark_reapproval(
        state,
        [
            "chain approval predates assurance graph binding; explicit reapproval is required"
        ],
    )
    _save_state(project_root, state)


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

    config_value, profile_changed = _prepare_config(
        project_root,
        args.project_profile,
    )
    config_candidate = (
        config_value
        if config_value is not None
        else _read_json(project_root / CONFIG_RELATIVE_PATH)
    )
    config_errors: list[str] = []
    _, _, _, _, selected_profile = _validate_config_value(
        project_root,
        config_candidate,
        config_errors,
    )
    if config_errors:
        raise EZPowersError(
            "invalid .ezpowers/config.json:\n- " + "\n- ".join(config_errors)
        )
    state_path = project_root / STATE_RELATIVE_PATH
    if state_path.exists():
        _load_state(project_root)

    hook_updates: list[tuple[pathlib.Path, bytes]] = []
    configured_chain_hosts: set[str] = set()
    if (project_root / CHAIN_RELATIVE_PATH).is_file():
        chain_value, _ = _load_chain_value(project_root)
        configured_chain_hosts = set(chain_value["hosts"])
    for host in ("claude", "codex"):
        features: set[str] = set()
        if args.enable_hooks in {host, "both"}:
            if host in configured_chain_hosts:
                raise EZPowersError(
                    f"{host} already uses the explicit harness-chain Stop "
                    "adapter; the ordinary completion hook would create a "
                    "second EZPowers continuation authority"
                )
            features.add("completion")
        if args.enable_wiki_hooks in {host, "both"}:
            features.add("wiki")
        if features:
            hook_updates.append(_hook_update(project_root, host, features))

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
        for path, data in hook_updates:
            _atomic_write(path, data)
        if config_value is not None:
            _write_json(project_root / CONFIG_RELATIVE_PATH, config_value)
        if profile_changed:
            _invalidate_profile_transition(
                project_root,
                requested_profile=str(args.project_profile),
            )
        installed_version = str(ledger.get("version") or "unknown")
        message = (
            f"EZPowers project kit already installed ({installed_version}); "
            "use --refresh to update or repair it"
        )
        if selected_profile.name == PLANNING_PROFILE.name:
            message += f"; project profile: {selected_profile.name}"
        print(message)
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
    elif profile_changed:
        _invalidate_profile_transition(
            project_root,
            requested_profile=str(args.project_profile),
        )
    for path, data in hook_updates:
        _atomic_write(path, data)

    if args.refresh:
        _mark_legacy_chain_reapproval_after_refresh(project_root)

    new_ledger = {
        "schema_version": SCHEMA_VERSION,
        "version": manifest["version"],
        "installed_at": _utc_now(),
        "source": "installed-kit" if installed_mode else "plugin-distribution",
        "files": {
            name: {"sha256": _sha256_bytes(data)}
            for name, data in sorted(desired.items())
        },
    }
    _write_json(ledger_path, new_ledger)
    verb = "refreshed" if args.refresh else "installed"
    message = f"EZPowers project kit {verb}: {manifest['version']} ({len(desired)} managed files)"
    if selected_profile.name == PLANNING_PROFILE.name:
        message += f"; project profile: {selected_profile.name}"
    print(message)
    return 0


def _default_docs_registry() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "uninitialized",
        "documents": {},
        "links": [],
        "hooks": {},
        "required_check": None,
        "updated_at": _utc_now(),
    }


def _load_docs_registry(root: pathlib.Path) -> dict[str, Any]:
    path = root / DOCS_RELATIVE_PATH
    if not path.exists():
        return _default_docs_registry()
    value = _read_json(path)
    if value.get("schema_version") != SCHEMA_VERSION:
        raise EZPowersError(".ezpowers/docs.json schema_version must be 1")
    if value.get("status") not in {"uninitialized", "incomplete", "ready"}:
        raise EZPowersError(".ezpowers/docs.json status is invalid")
    if not isinstance(value.get("documents"), dict):
        raise EZPowersError(".ezpowers/docs.json documents must be an object")
    if not isinstance(value.get("links"), list):
        raise EZPowersError(".ezpowers/docs.json links must be an array")
    if not isinstance(value.get("hooks"), dict):
        raise EZPowersError(".ezpowers/docs.json hooks must be an object")
    if value.get("required_check") is not None and not isinstance(
        value.get("required_check"), dict
    ):
        raise EZPowersError(".ezpowers/docs.json required_check must be an object or null")
    return value


def _safe_document_path(root: pathlib.Path, value: str, label: str) -> pathlib.Path:
    normalized = pathlib.PurePosixPath(value.replace("\\", "/")).as_posix()
    pure = pathlib.PurePosixPath(normalized)
    design_md = (
        pure.name == "DESIGN.md"
        and not pure.is_absolute()
        and ".." not in pure.parts
        and not any(part.lower() in DOCS_RESERVED_DESIGN_PARTS for part in pure.parts)
    )
    allowed = normalized in DOCS_ALLOWED_ROOT_FILES or (
        len(pure.parts) >= 2 and pure.parts[0] == "docs" and pure.suffix.lower() == ".md"
    ) or design_md
    if not allowed:
        raise EZPowersError(
            f"{label} must be AGENTS.md, CLAUDE.md, Markdown under docs/, "
            f"or a safe root/app DESIGN.md: {value}"
        )
    return _safe_target(root, normalized, label)


def _design_tool_path(root: pathlib.Path) -> pathlib.Path:
    candidates = [
        root / ".ezpowers" / "tools" / "design-md.py",
        pathlib.Path(__file__).resolve().parent / "design-md.py",
        pathlib.Path(__file__).resolve().parent / "tools" / "design-md.py",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise EZPowersError("installed DESIGN.md validator is missing")


def _design_tool_payload(
    root: pathlib.Path,
    arguments: list[str],
    *,
    accepted_codes: set[int] | None = None,
) -> tuple[dict[str, Any], int]:
    accepted_codes = {0, 1} if accepted_codes is None else accepted_codes
    tool = _design_tool_path(root)
    try:
        completed = subprocess.run(
            [sys.executable, str(tool), *arguments, "--json"],
            cwd=root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=90,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise EZPowersError(f"DESIGN.md validator could not run: {exc}") from exc
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise EZPowersError(
            f"DESIGN.md validator returned invalid JSON (exit {completed.returncode}): {detail[:1000]}"
        ) from exc
    if not isinstance(payload, dict):
        raise EZPowersError("DESIGN.md validator JSON root must be an object")
    if completed.returncode not in accepted_codes:
        detail = payload.get("error") or completed.stderr.strip() or payload.get("status")
        raise EZPowersError(
            f"DESIGN.md validator failed with exit {completed.returncode}: {detail}"
        )
    return payload, completed.returncode


def _validate_design_document(
    root: pathlib.Path,
    path: pathlib.Path,
    profile: str,
    *,
    label: str,
) -> dict[str, Any]:
    payload, _ = _design_tool_payload(
        root,
        ["lint", "--file", str(path), "--profile", profile],
    )
    if payload.get("status") != "PASS":
        messages = [
            f"{item.get('rule')} {item.get('path')}: {item.get('message')}"
            for item in payload.get("findings", [])
            if isinstance(item, dict) and item.get("severity") == "error"
        ]
        raise EZPowersError(
            f"{label} does not pass DESIGN.md profile {profile}"
            + (":\n- " + "\n- ".join(messages) if messages else "")
        )
    return payload


def _valid_evidence_reference(
    root: pathlib.Path,
    value: str,
    proposed_paths: set[str],
) -> bool:
    if value.startswith(("user:", "default:")):
        return len(value.split(":", 1)[1].strip()) > 0
    if not _is_project_relative_text(value):
        return False
    normalized = pathlib.PurePosixPath(value.replace("\\", "/")).as_posix()
    if normalized in proposed_paths:
        return True
    try:
        return _safe_target(root, normalized, "document evidence").exists()
    except EZPowersError:
        return False


def _validate_generated_markdown(
    text: str,
    *,
    label: str,
) -> None:
    if label == "CLAUDE.md":
        if text.replace("\r\n", "\n").strip() != "@AGENTS.md":
            raise EZPowersError("CLAUDE.md must contain only the canonical @AGENTS.md import")
        return
    frontmatter, body = _parse_markdown_frontmatter(text, label)
    required = {
        "doc_type": str,
        "authority": str,
        "status": str,
        "generated_by": str,
    }
    for key, expected_type in required.items():
        if not isinstance(frontmatter.get(key), expected_type) or not str(frontmatter[key]).strip():
            raise EZPowersError(f"{label} frontmatter.{key} must be a non-empty string")
    if frontmatter["authority"] not in DOCS_AUTHORITIES:
        raise EZPowersError(f"{label} frontmatter.authority is invalid")
    if frontmatter["status"] not in DOCS_STATUSES:
        raise EZPowersError(f"{label} frontmatter.status is invalid")
    if frontmatter["generated_by"] != "ezpowers":
        raise EZPowersError(f"{label} frontmatter.generated_by must be ezpowers")
    if not re.search(r"(?m)^#\s+\S", body):
        raise EZPowersError(f"{label} must contain a Markdown title")
    if not re.search(r"(?m)^##\s+Evidence\s*$", body):
        raise EZPowersError(f"{label} must contain an Evidence section")
    if re.search(r"\[(?:TODO|TBD|PLACEHOLDER):[^\]]*\]", body, re.IGNORECASE):
        raise EZPowersError(f"{label} contains an unresolved template marker")


def _load_docs_bundle(
    root: pathlib.Path,
    bundle_argument: str,
) -> tuple[pathlib.Path, dict[str, Any], list[dict[str, Any]], list[dict[str, str]]]:
    bundle = _contained_path(
        root,
        bundle_argument,
        label="documentation bundle",
        must_exist=True,
        directory=True,
    )
    staging_root = (root / DOCS_STAGING_RELATIVE_PATH).resolve()
    try:
        bundle.relative_to(staging_root)
    except ValueError as exc:
        raise EZPowersError(
            f"documentation bundle must be under {DOCS_STAGING_RELATIVE_PATH.as_posix()}"
        ) from exc
    manifest = _read_json(bundle / "bundle.json")
    if manifest.get("schema_version") != SCHEMA_VERSION:
        raise EZPowersError("documentation bundle schema_version must be 1")
    if manifest.get("status", "ready") not in {"incomplete", "ready"}:
        raise EZPowersError("documentation bundle status must be incomplete or ready")
    raw_documents = manifest.get("documents")
    if not isinstance(raw_documents, list) or not raw_documents:
        raise EZPowersError("documentation bundle documents must be a non-empty array")

    normalized_documents: list[dict[str, Any]] = []
    proposed_paths: set[str] = set()
    for raw in raw_documents:
        if not isinstance(raw, dict):
            raise EZPowersError("documentation bundle entries must be objects")
        target_name = pathlib.PurePosixPath(str(raw.get("path", "")).replace("\\", "/")).as_posix()
        _safe_document_path(root, target_name, "documentation target")
        if target_name in proposed_paths:
            raise EZPowersError(f"duplicate documentation target: {target_name}")
        proposed_paths.add(target_name)
        role = str(raw.get("role", ""))
        if not ID_RE.fullmatch(role):
            raise EZPowersError(f"documentation role is invalid: {role!r}")
        ownership = str(raw.get("ownership", "ezpowers"))
        authority = str(raw.get("authority", ""))
        status = str(raw.get("status", ""))
        validator = str(raw.get("validator", "markdown"))
        if ownership not in DOCS_OWNERS:
            raise EZPowersError(f"documentation ownership is invalid: {ownership!r}")
        if authority not in DOCS_AUTHORITIES:
            raise EZPowersError(f"documentation authority is invalid: {authority!r}")
        if status not in DOCS_STATUSES:
            raise EZPowersError(f"documentation status is invalid: {status!r}")
        if validator not in DOCS_VALIDATORS:
            raise EZPowersError(f"documentation validator is invalid: {validator!r}")
        evidence = raw.get("evidence", [])
        if not isinstance(evidence, list) or any(not isinstance(item, str) for item in evidence):
            raise EZPowersError(f"documentation evidence must be a string array: {target_name}")
        if not evidence:
            raise EZPowersError(f"documentation evidence must not be empty: {target_name}")
        normalized: dict[str, Any] = {
            "path": target_name,
            "role": role,
            "ownership": ownership,
            "authority": authority,
            "status": status,
            "validator": validator,
            "evidence": list(evidence),
            "adopt": raw.get("adopt") is True,
        }
        validator_profile = raw.get("validator_profile")
        if validator == "design-md":
            if not isinstance(validator_profile, str) or not ID_RE.fullmatch(validator_profile):
                raise EZPowersError(
                    f"documentation validator_profile is required for DESIGN.md: {target_name}"
                )
            normalized["validator_profile"] = validator_profile
        elif validator_profile is not None:
            raise EZPowersError(
                f"documentation validator_profile is only valid with design-md: {target_name}"
            )
        if ownership == "ezpowers":
            source_name = pathlib.PurePosixPath(
                str(raw.get("source", "")).replace("\\", "/")
            ).as_posix()
            source = _safe_target(bundle, source_name, "documentation bundle source")
            if not source.is_file():
                raise EZPowersError(f"documentation bundle source is missing: {source_name}")
            try:
                data = source.read_bytes()
                text = data.decode("utf-8")
            except (OSError, UnicodeDecodeError) as exc:
                raise EZPowersError(f"cannot read documentation source {source_name}: {exc}") from exc
            if validator == "markdown":
                _validate_generated_markdown(text, label=target_name)
                if target_name != "CLAUDE.md":
                    frontmatter, _ = _parse_markdown_frontmatter(text, target_name)
                    if frontmatter.get("authority") != authority:
                        raise EZPowersError(
                            f"{target_name} frontmatter.authority must match its bundle entry"
                        )
                    if frontmatter.get("status") != status:
                        raise EZPowersError(
                            f"{target_name} frontmatter.status must match its bundle entry"
                        )
            elif validator in {"spec", "plan"}:
                _extract_block(source, validator)
            else:
                _validate_design_document(
                    root,
                    source,
                    normalized["validator_profile"],
                    label=target_name,
                )
            normalized["source"] = source_name
            normalized["data"] = data
            normalized["sha256"] = _sha256_bytes(data)
        else:
            target = _safe_document_path(root, target_name, "external documentation target")
            if not target.is_file():
                raise EZPowersError(f"external documentation target is missing: {target_name}")
            if validator in {"spec", "plan"}:
                _extract_block(target, validator)
            elif validator == "design-md":
                _validate_design_document(
                    root,
                    target,
                    normalized["validator_profile"],
                    label=target_name,
                )
        normalized_documents.append(normalized)

    for entry in normalized_documents:
        for evidence in entry["evidence"]:
            if not _valid_evidence_reference(root, evidence, proposed_paths):
                raise EZPowersError(
                    f"documentation evidence is not a valid project source: "
                    f"{entry['path']}: {evidence}"
                )

    raw_links = manifest.get("links", [])
    if not isinstance(raw_links, list):
        raise EZPowersError("documentation bundle links must be an array")
    normalized_links: list[dict[str, str]] = []
    seen_links: set[tuple[str, str, str]] = set()
    for raw in raw_links:
        if not isinstance(raw, dict):
            raise EZPowersError("documentation links must be objects")
        source_name = pathlib.PurePosixPath(str(raw.get("from", "")).replace("\\", "/")).as_posix()
        target_name = pathlib.PurePosixPath(str(raw.get("to", "")).replace("\\", "/")).as_posix()
        relation = str(raw.get("relation", ""))
        _safe_document_path(root, source_name, "documentation link source")
        _safe_document_path(root, target_name, "documentation link target")
        if relation not in DOCS_LINK_RELATIONS:
            raise EZPowersError(f"documentation link relation is invalid: {relation!r}")
        key = (source_name, target_name, relation)
        if key in seen_links:
            continue
        seen_links.add(key)
        normalized_links.append({"from": source_name, "to": target_name, "relation": relation})
    return bundle, manifest, normalized_documents, normalized_links


def _docs_preview(
    root: pathlib.Path,
    bundle_argument: str,
) -> tuple[
    dict[str, Any],
    pathlib.Path,
    dict[str, Any],
    list[dict[str, Any]],
    list[dict[str, str]],
]:
    bundle, manifest, documents, links = _load_docs_bundle(root, bundle_argument)
    registry = _load_docs_registry(root)
    registered = registry["documents"]
    actions: list[dict[str, Any]] = []
    conflicts: list[str] = []
    target_states: list[dict[str, Any]] = []
    token_documents: list[dict[str, Any]] = []

    for entry in documents:
        target = _safe_document_path(root, entry["path"], "documentation target")
        exists = target.is_file()
        current_sha = _sha256_file(target) if exists else None
        registered_entry = registered.get(entry["path"])
        action = "external"
        reason: str | None = None
        if entry["ownership"] == "ezpowers":
            if not exists:
                action = "create"
                if isinstance(registered_entry, dict) and registered_entry.get("ownership") == "ezpowers":
                    reason = "managed document is missing"
                    conflicts.append(f"{entry['path']}: {reason}")
            elif isinstance(registered_entry, dict) and registered_entry.get("ownership") == "ezpowers":
                recorded_sha = registered_entry.get("sha256")
                if not isinstance(recorded_sha, str) or current_sha != recorded_sha:
                    action = "replace"
                    reason = "managed document was modified"
                    conflicts.append(f"{entry['path']}: {reason}")
                elif current_sha == entry["sha256"]:
                    action = "unchanged"
                else:
                    action = "update"
            elif entry["adopt"]:
                action = "adopt"
                reason = "unmanaged document requires explicit forced adoption"
                conflicts.append(f"{entry['path']}: {reason}")
            else:
                action = "conflict"
                reason = "unmanaged document exists"
                conflicts.append(f"{entry['path']}: {reason}")
        action_entry: dict[str, Any] = {
            "path": entry["path"],
            "action": action,
            **({"reason": reason} if reason else {}),
        }
        if entry["validator"] == "design-md" and entry["ownership"] == "ezpowers":
            proposed = _safe_target(
                bundle,
                entry["source"],
                "documentation bundle source",
            )
            if exists:
                design_review, _ = _design_tool_payload(
                    root,
                    [
                        "diff",
                        "--before",
                        str(target),
                        "--after",
                        str(proposed),
                        "--profile",
                        entry["validator_profile"],
                    ],
                )
            else:
                design_review, _ = _design_tool_payload(
                    root,
                    [
                        "lint",
                        "--file",
                        str(proposed),
                        "--profile",
                        entry["validator_profile"],
                    ],
                )
            action_entry["design_review"] = design_review
        actions.append(action_entry)
        target_states.append({"path": entry["path"], "sha256": current_sha})
        token_documents.append(
            {
                key: value
                for key, value in entry.items()
                if key not in {"data"}
            }
        )

    registry_path = root / DOCS_RELATIVE_PATH
    config_path = root / CONFIG_RELATIVE_PATH
    token_payload = {
        "schema_version": SCHEMA_VERSION,
        "registry_sha256": _sha256_file(registry_path) if registry_path.is_file() else None,
        "config_sha256": _sha256_file(config_path) if config_path.is_file() else None,
        "manifest": {
            "status": manifest.get("status", "ready"),
            "replace_links": manifest.get("replace_links") is True,
            "hooks": manifest.get("hooks", {}),
        },
        "documents": token_documents,
        "links": links,
        "targets": target_states,
    }
    preview_sha256 = _sha256_bytes(_json_bytes(token_payload))
    payload = {
        "status": "CONFLICT" if conflicts else "READY",
        "preview_sha256": preview_sha256,
        "actions": actions,
        "conflicts": conflicts,
        "document_count": len(documents),
    }
    return payload, bundle, manifest, documents, links


def _docs_desired_check() -> dict[str, Any]:
    return {
        "argv": [
            sys.executable,
            ".ezpowers/ezpowers.py",
            "docs",
            "lint",
            "--json",
        ],
        "cwd": ".",
        "timeout_seconds": 30,
        "kind": "static",
    }


def _design_desired_check(frontend_design: str) -> dict[str, Any]:
    return {
        "argv": [
            sys.executable,
            ".ezpowers/tools/design-md.py",
            "check-project",
            "--project-root",
            ".",
            "--frontend-design",
            frontend_design,
            "--json",
        ],
        "cwd": ".",
        "timeout_seconds": 90,
        "kind": "static",
    }


def _frontend_design_for_documents(documents: dict[str, Any]) -> str | None:
    if not any(
        isinstance(node, dict) and node.get("validator") == "design-md"
        for node in documents.values()
    ):
        return None
    candidates = sorted(
        path
        for path, node in documents.items()
        if isinstance(path, str)
        and isinstance(node, dict)
        and node.get("role") == "frontend-design"
    )
    if len(candidates) != 1:
        raise EZPowersError(
            "a documentation graph with DESIGN.md entries requires exactly one "
            "frontend-design role"
        )
    return candidates[0]


def _config_with_docs_check(root: pathlib.Path, documents: dict[str, Any]) -> dict[str, Any]:
    config_path = root / CONFIG_RELATIVE_PATH
    config = _read_json(config_path)
    checks = config.setdefault("checks", {})
    required = config.setdefault("required_checks", [])
    if not isinstance(checks, dict) or not isinstance(required, list):
        raise EZPowersError("invalid config checks container while registering docs lint")
    desired = _docs_desired_check()
    existing = checks.get(DOCS_CHECK_ID)
    if existing is not None and existing != desired:
        raise InstallConflict(
            f"conflict: config check {DOCS_CHECK_ID} already has a different definition"
        )
    checks[DOCS_CHECK_ID] = desired
    if DOCS_CHECK_ID not in required:
        required.append(DOCS_CHECK_ID)
    frontend_design = _frontend_design_for_documents(documents)
    if frontend_design is not None:
        design_desired = _design_desired_check(frontend_design)
        design_existing = checks.get(DESIGN_CHECK_ID)
        if design_existing is not None and design_existing != design_desired:
            raise InstallConflict(
                f"conflict: config check {DESIGN_CHECK_ID} already has a different definition"
            )
        checks[DESIGN_CHECK_ID] = design_desired
        if DESIGN_CHECK_ID not in required:
            required.append(DESIGN_CHECK_ID)
    errors: list[str] = []
    _validate_config_value(root, config, errors)
    if errors:
        raise EZPowersError("invalid config after docs check registration:\n- " + "\n- ".join(errors))
    return config


def _docs_preview_command(args: argparse.Namespace) -> int:
    root = _runtime_project_root()
    payload, _, _, _, _ = _docs_preview(root, args.bundle)
    _emit(payload, args.json)
    return 0 if payload["status"] == "READY" else 3


def _docs_apply_command(args: argparse.Namespace) -> int:
    root = _runtime_project_root()
    with _runtime_lock(root):
        return _docs_apply_locked(args, root)


def _docs_apply_locked(args: argparse.Namespace, root: pathlib.Path) -> int:
    payload, bundle, manifest, documents, links = _docs_preview(root, args.bundle)
    if args.preview_sha256 != payload["preview_sha256"]:
        raise InstallConflict("conflict: documentation preview is stale or belongs to another bundle")
    if payload["conflicts"] and not args.force:
        raise InstallConflict(
            "conflict: documentation apply preserved existing files:\n- "
            + "\n- ".join(payload["conflicts"])
        )
    if any(item["action"] == "conflict" for item in payload["actions"]):
        raise InstallConflict(
            "conflict: unmanaged documentation cannot be overwritten without explicit adoption"
        )

    registry_path = root / DOCS_RELATIVE_PATH
    config_path = root / CONFIG_RELATIVE_PATH
    registry = _load_docs_registry(root)
    original_registry = registry_path.read_bytes() if registry_path.is_file() else None
    original_config = config_path.read_bytes() if config_path.is_file() else None
    originals: dict[pathlib.Path, bytes | None] = {}
    backup_root: pathlib.Path | None = None
    action_by_path = {item["path"]: item for item in payload["actions"]}
    if args.force and payload["conflicts"]:
        timestamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        backup_root = (
            root / DOCS_BACKUP_RELATIVE_PATH / f"{timestamp}-{uuid.uuid4().hex[:8]}"
        )

    try:
        for entry in documents:
            target = _safe_document_path(root, entry["path"], "documentation target")
            originals[target] = target.read_bytes() if target.is_file() else None
            action = action_by_path[entry["path"]]["action"]
            if (
                backup_root is not None
                and target.is_file()
                and action in {"adopt", "replace"}
            ):
                backup = _safe_target(
                    root,
                    (DOCS_BACKUP_RELATIVE_PATH / backup_root.name / entry["path"]).as_posix(),
                    "documentation backup",
                )
                _atomic_write(backup, target.read_bytes())
            if entry["ownership"] == "ezpowers" and action != "unchanged":
                _atomic_write(target, entry["data"])

        updated_documents = dict(registry["documents"])
        for entry in documents:
            node = {
                "role": entry["role"],
                "ownership": entry["ownership"],
                "authority": entry["authority"],
                "status": entry["status"],
                "validator": entry["validator"],
                "evidence": entry["evidence"],
            }
            if entry["validator"] == "design-md":
                node["validator_profile"] = entry["validator_profile"]
            if entry["ownership"] == "ezpowers":
                node["sha256"] = entry["sha256"]
            updated_documents[entry["path"]] = node

        if manifest.get("replace_links") is True:
            updated_links = links
        else:
            updated_links = list(registry["links"])
            seen = {
                (str(item.get("from")), str(item.get("to")), str(item.get("relation")))
                for item in updated_links
                if isinstance(item, dict)
            }
            for link in links:
                key = (link["from"], link["to"], link["relation"])
                if key not in seen:
                    updated_links.append(link)
                    seen.add(key)
        config_update: dict[str, Any] | None = None
        required_check: dict[str, Any] | None = registry.get("required_check")
        if manifest.get("status", "ready") == "ready":
            config_update = _config_with_docs_check(root, updated_documents)
            required_check = config_update["checks"][DOCS_CHECK_ID]
        registry.update(
            {
                "schema_version": SCHEMA_VERSION,
                "status": manifest.get("status", "ready"),
                "documents": updated_documents,
                "links": updated_links,
                "hooks": manifest.get("hooks", registry.get("hooks", {})),
                "required_check": required_check,
                "updated_at": _utc_now(),
            }
        )
        _write_json(registry_path, registry)
        if registry["status"] == "ready":
            assert config_update is not None
            _write_json(config_path, config_update)
            lint_payload, lint_code = _docs_lint_payload(root)
            if lint_code != 0:
                raise EZPowersError(
                    "documentation graph did not pass its required lint:\n- "
                    + "\n- ".join(lint_payload.get("errors", []))
                )
    except Exception:
        for target, original in originals.items():
            if original is None:
                with contextlib.suppress(FileNotFoundError):
                    target.unlink()
            else:
                _atomic_write(target, original)
        if original_registry is None:
            with contextlib.suppress(FileNotFoundError):
                registry_path.unlink()
        else:
            _atomic_write(registry_path, original_registry)
        if original_config is None:
            with contextlib.suppress(FileNotFoundError):
                config_path.unlink()
        else:
            _atomic_write(config_path, original_config)
        raise

    with contextlib.suppress(OSError):
        shutil.rmtree(bundle)
    result = {
        "status": "PASS",
        "preview_sha256": payload["preview_sha256"],
        "actions": payload["actions"],
        "backup_path": (
            _relative(root, backup_root) if backup_root is not None and backup_root.exists() else None
        ),
        "registry": DOCS_RELATIVE_PATH.as_posix(),
    }
    _emit(result, args.json)
    return 0


def _markdown_link_targets(
    root: pathlib.Path,
    source_path: pathlib.Path,
    text: str,
) -> tuple[set[str], list[str]]:
    targets: set[str] = set()
    errors: list[str] = []
    for match in re.finditer(r"!?\[[^\]]*\]\(([^)]+)\)", text):
        raw = match.group(1).strip().strip("<>")
        if not raw or raw.startswith(("#", "http://", "https://", "mailto:")):
            continue
        path_text = raw.split("#", 1)[0].replace("\\", "/")
        candidate = source_path.parent / path_text
        try:
            resolved = candidate.resolve()
            resolved.relative_to(root.resolve())
        except (OSError, ValueError):
            errors.append(f"{_relative(root, source_path)}: link escapes project root: {raw}")
            continue
        if not resolved.exists():
            errors.append(f"{_relative(root, source_path)}: broken Markdown link: {raw}")
            continue
        targets.add(_relative(root, resolved))
    return targets, errors


def _docs_lint_payload(root: pathlib.Path) -> tuple[dict[str, Any], int]:
    errors: list[str] = []
    registry_path = root / DOCS_RELATIVE_PATH
    if not registry_path.is_file():
        return {
            "status": "FAIL",
            "errors": [f"missing documentation registry: {DOCS_RELATIVE_PATH.as_posix()}"],
        }, 1
    try:
        registry = _load_docs_registry(root)
    except EZPowersError as exc:
        return {"status": "FAIL", "errors": [str(exc)]}, 1
    if registry["status"] != "ready":
        errors.append(f"documentation status is not ready: {registry['status']}")
    documents = registry["documents"]
    if not documents:
        errors.append("documentation registry has no documents")
    for required_path in ("AGENTS.md", "CLAUDE.md", "docs/INDEX.md"):
        if required_path not in documents:
            errors.append(f"documentation registry is missing required document: {required_path}")
    agents_node = documents.get("AGENTS.md")
    if isinstance(agents_node, dict) and agents_node.get("authority") != "canonical":
        errors.append("AGENTS.md must be the canonical documentation authority")
    contents: dict[str, str] = {}
    resolved_links: dict[str, set[str]] = {}
    for path_name, raw in sorted(documents.items()):
        if not isinstance(path_name, str) or not isinstance(raw, dict):
            errors.append(f"invalid documentation registry entry: {path_name!r}")
            continue
        try:
            path = _safe_document_path(root, path_name, "registered documentation")
        except EZPowersError as exc:
            errors.append(str(exc))
            continue
        ownership = raw.get("ownership")
        if ownership not in DOCS_OWNERS:
            errors.append(f"{path_name}: invalid ownership")
            continue
        if not path.is_file():
            errors.append(f"{path_name}: registered document is missing")
            continue
        if ownership == "ezpowers":
            expected = raw.get("sha256")
            if not isinstance(expected, str) or not re.fullmatch(r"[0-9a-f]{64}", expected):
                errors.append(f"{path_name}: managed sha256 is invalid")
            elif _sha256_file(path) != expected:
                errors.append(f"{path_name}: managed document hash drift")
        try:
            text = path.read_text(encoding="utf-8")
            contents[path_name] = text
        except (OSError, UnicodeDecodeError) as exc:
            errors.append(f"{path_name}: cannot read Markdown: {exc}")
            continue
        validator = raw.get("validator")
        role = raw.get("role")
        authority = raw.get("authority")
        document_status = raw.get("status")
        if not isinstance(role, str) or not ID_RE.fullmatch(role):
            errors.append(f"{path_name}: invalid role")
        if authority not in DOCS_AUTHORITIES:
            errors.append(f"{path_name}: invalid authority")
        if document_status not in DOCS_STATUSES:
            errors.append(f"{path_name}: invalid document status")
        if validator not in DOCS_VALIDATORS:
            errors.append(f"{path_name}: invalid validator")
        elif validator in {"spec", "plan"}:
            try:
                _extract_block(path, str(validator))
            except EZPowersError as exc:
                errors.append(str(exc))
        elif validator == "design-md":
            validator_profile = raw.get("validator_profile")
            if not isinstance(validator_profile, str) or not ID_RE.fullmatch(validator_profile):
                errors.append(f"{path_name}: invalid DESIGN.md validator_profile")
            else:
                try:
                    _validate_design_document(
                        root,
                        path,
                        validator_profile,
                        label=path_name,
                    )
                except EZPowersError as exc:
                    errors.append(str(exc))
        elif ownership == "ezpowers":
            try:
                _validate_generated_markdown(text, label=path_name)
                if path_name != "CLAUDE.md":
                    frontmatter, _ = _parse_markdown_frontmatter(text, path_name)
                    if frontmatter.get("authority") != authority:
                        errors.append(
                            f"{path_name}: frontmatter authority differs from registry"
                        )
                    if frontmatter.get("status") != document_status:
                        errors.append(
                            f"{path_name}: frontmatter status differs from registry"
                        )
            except EZPowersError as exc:
                errors.append(str(exc))
        evidence = raw.get("evidence")
        if (
            not isinstance(evidence, list)
            or not evidence
            or any(not isinstance(item, str) for item in evidence)
        ):
            errors.append(f"{path_name}: evidence must be a non-empty string array")
        else:
            for item in evidence:
                if not _valid_evidence_reference(root, item, set(documents)):
                    errors.append(f"{path_name}: evidence source is missing or unsafe: {item}")
        if validator == "markdown":
            targets, link_errors = _markdown_link_targets(root, path, text)
            resolved_links[path_name] = targets
            if ownership == "ezpowers":
                errors.extend(link_errors)

    seen_links: set[tuple[str, str, str]] = set()
    for raw in registry["links"]:
        if not isinstance(raw, dict):
            errors.append("documentation link entry must be an object")
            continue
        source_name = raw.get("from")
        target_name = raw.get("to")
        relation = raw.get("relation")
        if (
            not isinstance(source_name, str)
            or not isinstance(target_name, str)
            or relation not in DOCS_LINK_RELATIONS
        ):
            errors.append(f"invalid documentation link: {raw!r}")
            continue
        key = (source_name, target_name, str(relation))
        if key in seen_links:
            errors.append(f"duplicate documentation link: {key}")
            continue
        seen_links.add(key)
        if source_name not in documents or target_name not in documents:
            errors.append(f"documentation link endpoint is not registered: {key}")
            continue
        text = contents.get(source_name, "")
        source_path = root / source_name
        relative_target = pathlib.PurePosixPath(
            os.path.relpath(root / target_name, source_path.parent).replace("\\", "/")
        ).as_posix()
        if relation == "imports" and f"@{relative_target}" not in text:
            errors.append(f"{source_name}: missing import for {target_name}")
        elif relation == "parent" and f"<!-- Parent: {relative_target} -->" not in text:
            errors.append(f"{source_name}: missing parent marker for {target_name}")
        elif relation in {"indexes", "references"} and target_name not in resolved_links.get(
            source_name, set()
        ):
            errors.append(f"{source_name}: missing Markdown link to {target_name}")

    claude_text = contents.get("CLAUDE.md")
    if isinstance(claude_text, str) and claude_text.replace("\r\n", "\n").strip() != "@AGENTS.md":
        errors.append("CLAUDE.md must contain only the canonical @AGENTS.md import")
    if ("CLAUDE.md", "AGENTS.md", "imports") not in seen_links:
        errors.append("documentation graph must declare CLAUDE.md imports AGENTS.md")

    try:
        config = _read_json(root / CONFIG_RELATIVE_PATH)
        checks = config.get("checks", {})
        required = config.get("required_checks", [])
        expected_check = registry.get("required_check")
        valid_expected = (
            isinstance(expected_check, dict)
            and isinstance(expected_check.get("argv"), list)
            and len(expected_check["argv"]) == 5
            and isinstance(expected_check["argv"][0], str)
            and bool(expected_check["argv"][0])
            and expected_check["argv"][1:] == [
                ".ezpowers/ezpowers.py",
                "docs",
                "lint",
                "--json",
            ]
            and expected_check.get("cwd") == "."
            and expected_check.get("timeout_seconds") == 30
            and expected_check.get("kind") == "static"
        )
        if not valid_expected:
            errors.append("documentation registry required_check is invalid")
        if not isinstance(checks, dict) or checks.get(DOCS_CHECK_ID) != expected_check:
            errors.append(f"config check {DOCS_CHECK_ID} is missing or changed")
        if not isinstance(required, list) or DOCS_CHECK_ID not in required:
            errors.append(f"config required_checks is missing {DOCS_CHECK_ID}")
        try:
            frontend_design = _frontend_design_for_documents(documents)
        except EZPowersError as exc:
            errors.append(str(exc))
            frontend_design = None
        if frontend_design is not None:
            expected_design_check = _design_desired_check(frontend_design)
            if (
                not isinstance(checks, dict)
                or checks.get(DESIGN_CHECK_ID) != expected_design_check
            ):
                errors.append(f"config check {DESIGN_CHECK_ID} is missing or changed")
            if not isinstance(required, list) or DESIGN_CHECK_ID not in required:
                errors.append(f"config required_checks is missing {DESIGN_CHECK_ID}")
            try:
                design_payload, _ = _design_tool_payload(
                    root,
                    [
                        "check-project",
                        "--project-root",
                        ".",
                        "--frontend-design",
                        frontend_design,
                    ],
                )
                if design_payload.get("status") != "PASS":
                    errors.extend(
                        f"{DESIGN_CHECK_ID}: {message}"
                        for message in design_payload.get("errors", [])
                        if isinstance(message, str)
                    )
            except EZPowersError as exc:
                errors.append(str(exc))
    except EZPowersError as exc:
        errors.append(str(exc))
    payload = {
        "status": "PASS" if not errors else "FAIL",
        "errors": errors,
        "document_count": len(documents),
        "link_count": len(registry["links"]),
        "registry": DOCS_RELATIVE_PATH.as_posix(),
    }
    return payload, 0 if not errors else 1


def _docs_lint_command(args: argparse.Namespace) -> int:
    root = _runtime_project_root()
    payload, code = _docs_lint_payload(root)
    _emit(payload, args.json)
    return code


def _docs_status_command(args: argparse.Namespace) -> int:
    root = _runtime_project_root()
    payload, code = _docs_lint_payload(root)
    payload["configured"] = (root / DOCS_RELATIVE_PATH).is_file()
    _emit(payload, args.json)
    return code


def _wiki_page_path(root: pathlib.Path, page_id: str) -> pathlib.Path:
    if not ID_RE.fullmatch(page_id):
        raise EZPowersError(f"wiki page id is invalid: {page_id!r}")
    return _safe_target(
        root,
        (WIKI_RELATIVE_PATH / "pages" / f"{page_id}.md").as_posix(),
        "wiki page",
    )


def _wiki_render_page(metadata: dict[str, Any], body: str) -> bytes:
    ordered_keys = (
        "id",
        "title",
        "category",
        "status",
        "tags",
        "source",
        "created_at",
        "updated_at",
        "promoted_to",
        "promoted_sha256",
        "promoted_at",
    )
    lines = ["---"]
    for key in ordered_keys:
        if key in metadata:
            lines.append(
                f"{key}: {json.dumps(metadata[key], ensure_ascii=False, separators=(',', ':'))}"
            )
    lines.extend(["---", "", body.strip(), ""])
    return "\n".join(lines).encode("utf-8")


def _wiki_parse_page(path: pathlib.Path) -> tuple[dict[str, Any], str]:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise EZPowersError(f"cannot read wiki page {path}: {exc}") from exc
    metadata, body = _parse_markdown_frontmatter(text, str(path))
    required = {
        "id": str,
        "title": str,
        "category": str,
        "status": str,
        "tags": list,
        "source": str,
        "created_at": str,
        "updated_at": str,
    }
    allowed = {
        *required,
        "promoted_to",
        "promoted_sha256",
        "promoted_at",
    }
    unknown = sorted(set(metadata) - allowed)
    if unknown:
        raise EZPowersError(
            f"{path}: unsupported wiki frontmatter fields: {', '.join(unknown)}"
        )
    for key, expected in required.items():
        if not isinstance(metadata.get(key), expected):
            raise EZPowersError(f"{path}: wiki frontmatter.{key} has the wrong type")
    page_id = metadata["id"]
    if not ID_RE.fullmatch(page_id) or path.stem != page_id:
        raise EZPowersError(f"{path}: wiki page id does not match its file name")
    if (
        not metadata["title"].strip()
        or len(metadata["title"]) > 200
        or any(character in metadata["title"] for character in "\r\n")
    ):
        raise EZPowersError(f"{path}: wiki title must contain 1-200 characters")
    if metadata["category"] not in WIKI_CATEGORIES:
        raise EZPowersError(f"{path}: wiki category is invalid")
    if metadata["status"] not in WIKI_PAGE_STATUSES:
        raise EZPowersError(f"{path}: wiki status is invalid")
    tags = metadata["tags"]
    if len(tags) > 32 or any(
        not isinstance(tag, str)
        or not tag.strip()
        or len(tag) > 80
        or any(character in tag for character in "\r\n")
        for tag in tags
    ):
        raise EZPowersError(f"{path}: wiki tags must be 1-80 character strings")
    if len(set(tags)) != len(tags):
        raise EZPowersError(f"{path}: wiki tags must be unique")
    if not metadata["source"].strip() or len(metadata["source"]) > 120:
        raise EZPowersError(f"{path}: wiki source must contain 1-120 characters")
    if not re.search(r"(?m)^#\s+\S", body):
        raise EZPowersError(f"{path}: wiki body must contain a Markdown title")
    if metadata["status"] == "promoted":
        target = metadata.get("promoted_to")
        digest = metadata.get("promoted_sha256")
        if (
            not isinstance(target, str)
            or not isinstance(digest, str)
            or re.fullmatch(r"[0-9a-f]{64}", digest) is None
        ):
            raise EZPowersError(f"{path}: promoted wiki page is missing its target binding")
    return metadata, body


def _wiki_pages(root: pathlib.Path) -> list[tuple[pathlib.Path, dict[str, Any], str]]:
    pages_root = root / WIKI_RELATIVE_PATH / "pages"
    if not pages_root.is_dir():
        return []
    pages: list[tuple[pathlib.Path, dict[str, Any], str]] = []
    for path in sorted(pages_root.glob("*.md")):
        if path.is_symlink() or not path.is_file():
            raise EZPowersError(f"wiki pages must be regular files: {path}")
        metadata, body = _wiki_parse_page(path)
        pages.append((path, metadata, body))
    return pages


def _wiki_summary(root: pathlib.Path, path: pathlib.Path, metadata: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": metadata["id"],
        "title": metadata["title"],
        "category": metadata["category"],
        "status": metadata["status"],
        "tags": metadata["tags"],
        "source": metadata["source"],
        "updated_at": metadata["updated_at"],
        "path": _relative(root, path),
        **(
            {"promoted_to": metadata["promoted_to"]}
            if isinstance(metadata.get("promoted_to"), str)
            else {}
        ),
    }


def _wiki_index_bytes(
    root: pathlib.Path,
    pages: list[tuple[pathlib.Path, dict[str, Any], str]],
) -> bytes:
    lines = [
        "# EZPowers Local Wiki",
        "",
        "This index is generated from local wiki pages. Do not edit it by hand.",
        "",
    ]
    if not pages:
        lines.extend(["_No pages yet._", ""])
    else:
        for path, metadata, _ in sorted(
            pages,
            key=lambda item: (item[1]["category"], item[1]["title"].casefold(), item[1]["id"]),
        ):
            relative = pathlib.PurePosixPath(
                os.path.relpath(path, root / WIKI_RELATIVE_PATH).replace("\\", "/")
            ).as_posix()
            title = metadata["title"].replace("[", r"\[").replace("]", r"\]")
            tags = ", ".join(
                tag.replace("[", r"\[").replace("]", r"\]")
                for tag in metadata["tags"]
            ) or "-"
            lines.append(
                f"- [{title}]({relative}) — "
                f"{metadata['category']} / {metadata['status']} / {tags}"
            )
        lines.append("")
    return "\n".join(lines).encode("utf-8")


def _wiki_log(root: pathlib.Path, event: str, details: str) -> None:
    path = root / WIKI_RELATIVE_PATH / "log.md"
    if path.is_file():
        try:
            current = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            raise EZPowersError(f"cannot read wiki log: {exc}") from exc
    else:
        current = "# EZPowers Wiki Log\n\n"
    safe_details = " ".join(details.replace("\r", " ").replace("\n", " ").split())
    updated = f"{current.rstrip()}\n\n- `{_utc_now()}` **{event}** {safe_details}\n"
    _atomic_write(path, updated.encode("utf-8"))


def _wiki_refresh_locked(root: pathlib.Path, *, log_event: bool = True) -> dict[str, Any]:
    wiki_root = root / WIKI_RELATIVE_PATH
    (wiki_root / "pages").mkdir(parents=True, exist_ok=True)
    (wiki_root / "errors").mkdir(parents=True, exist_ok=True)
    (wiki_root / "backups").mkdir(parents=True, exist_ok=True)
    pages = _wiki_pages(root)
    _atomic_write(wiki_root / "index.md", _wiki_index_bytes(root, pages))
    if not (wiki_root / "log.md").is_file():
        _atomic_write(wiki_root / "log.md", b"# EZPowers Wiki Log\n")
    if log_event:
        _wiki_log(root, "refresh", f"{len(pages)} pages indexed")
    return {
        "status": "PASS",
        "page_count": len(pages),
        "index": (WIKI_RELATIVE_PATH / "index.md").as_posix(),
    }


def _wiki_payload(args: argparse.Namespace, *, required: bool = False) -> dict[str, Any]:
    raw = getattr(args, "input", None)
    if raw is None:
        if required:
            raise EZPowersError("--input is required")
        return {}
    return _read_json_argument(raw, "--input")


def _wiki_reject_unknown(payload: dict[str, Any], allowed: set[str], label: str) -> None:
    unknown = sorted(set(payload) - allowed)
    if unknown:
        raise EZPowersError(f"{label} contains unsupported fields: {', '.join(unknown)}")


def _wiki_normalize_tags(value: Any) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise EZPowersError("wiki tags must be an array")
    tags: list[str] = []
    seen: set[str] = set()
    for raw in value:
        if not isinstance(raw, str):
            raise EZPowersError("wiki tags must contain only strings")
        tag = unicodedata.normalize("NFKC", raw).strip().casefold()
        if not tag or len(tag) > 80 or any(character in tag for character in "\r\n"):
            raise EZPowersError("wiki tags must contain 1-80 characters")
        if tag not in seen:
            seen.add(tag)
            tags.append(tag)
    if len(tags) > 32:
        raise EZPowersError("wiki pages may have at most 32 tags")
    return tags


def _wiki_new_id(prefix: str = "note") -> str:
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d%H%M%S")
    return f"{prefix}-{stamp}-{uuid.uuid4().hex[:8]}"


def _wiki_add_locked(
    root: pathlib.Path,
    *,
    title: str,
    category: str,
    tags: list[str],
    body: str,
    source: str,
    page_id: str | None = None,
) -> tuple[pathlib.Path, dict[str, Any]]:
    title = unicodedata.normalize("NFKC", title).strip()
    body = body.strip()
    if (
        not title
        or len(title) > 200
        or any(character in title for character in "\r\n")
    ):
        raise EZPowersError("wiki title must contain 1-200 characters")
    if category not in WIKI_CATEGORIES:
        raise EZPowersError(f"wiki category is invalid: {category!r}")
    if not source.strip() or len(source) > 120:
        raise EZPowersError("wiki source must contain 1-120 characters")
    if len(body.encode("utf-8")) > 65536:
        raise EZPowersError("wiki body exceeds 64 KiB")
    if not re.search(r"(?m)^#\s+\S", body):
        body = f"# {title}\n\n{body}".rstrip()
    page_id = page_id or _wiki_new_id("session" if category == "session-log" else "note")
    path = _wiki_page_path(root, page_id)
    if path.exists():
        raise InstallConflict(f"conflict: wiki page already exists: {page_id}")
    now = _utc_now()
    metadata = {
        "id": page_id,
        "title": title,
        "category": category,
        "status": "candidate",
        "tags": tags,
        "source": source,
        "created_at": now,
        "updated_at": now,
    }
    _atomic_write(path, _wiki_render_page(metadata, body))
    _wiki_parse_page(path)
    _wiki_refresh_locked(root, log_event=False)
    _wiki_log(root, "add", f"{page_id} ({category})")
    return path, metadata


def _wiki_add_command(args: argparse.Namespace) -> int:
    root = _runtime_project_root()
    payload = _wiki_payload(args, required=True)
    _wiki_reject_unknown(
        payload,
        {"id", "title", "category", "tags", "body"},
        "wiki add input",
    )
    title = payload.get("title")
    category = payload.get("category")
    body = payload.get("body", "")
    page_id = payload.get("id")
    if not isinstance(title, str) or not isinstance(category, str) or not isinstance(body, str):
        raise EZPowersError("wiki add requires string title, category, and body fields")
    if page_id is not None and not isinstance(page_id, str):
        raise EZPowersError("wiki page id must be a string")
    tags = _wiki_normalize_tags(payload.get("tags"))
    with _runtime_lock(root):
        path, metadata = _wiki_add_locked(
            root,
            title=title,
            category=category,
            tags=tags,
            body=body,
            source="manual",
            page_id=page_id,
        )
    result = {
        "status": "PASS",
        "page": _wiki_summary(root, path, metadata),
    }
    _emit(result, args.json)
    return 0


def _wiki_read_command(args: argparse.Namespace) -> int:
    root = _runtime_project_root()
    path = _wiki_page_path(root, args.id)
    if not path.is_file():
        raise EZPowersError(f"wiki page does not exist: {args.id}")
    metadata, body = _wiki_parse_page(path)
    result = {
        "status": "PASS",
        "page": {**_wiki_summary(root, path, metadata), "body": body.strip()},
    }
    _emit(result, args.json)
    return 0


def _wiki_filter_pages(
    root: pathlib.Path,
    payload: dict[str, Any],
) -> list[tuple[pathlib.Path, dict[str, Any], str]]:
    _wiki_reject_unknown(payload, {"category", "status", "tag", "limit"}, "wiki filter")
    category = payload.get("category")
    status = payload.get("status")
    tag = payload.get("tag")
    limit = payload.get("limit", 100)
    if category is not None and category not in WIKI_CATEGORIES:
        raise EZPowersError("wiki filter category is invalid")
    if status is not None and status not in WIKI_PAGE_STATUSES:
        raise EZPowersError("wiki filter status is invalid")
    if tag is not None and not isinstance(tag, str):
        raise EZPowersError("wiki filter tag must be a string")
    if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 500:
        raise EZPowersError("wiki filter limit must be an integer from 1 to 500")
    normalized_tag = (
        unicodedata.normalize("NFKC", tag).strip().casefold()
        if isinstance(tag, str)
        else None
    )
    if normalized_tag == "":
        raise EZPowersError("wiki filter tag must not be empty")
    matches = []
    for item in _wiki_pages(root):
        metadata = item[1]
        if category is not None and metadata["category"] != category:
            continue
        if status is not None and metadata["status"] != status:
            continue
        if normalized_tag is not None and normalized_tag not in metadata["tags"]:
            continue
        matches.append(item)
    matches.sort(key=lambda item: (item[1]["updated_at"], item[1]["id"]), reverse=True)
    return matches[:limit]


def _wiki_list_command(args: argparse.Namespace) -> int:
    root = _runtime_project_root()
    payload = _wiki_payload(args)
    matches = _wiki_filter_pages(root, payload)
    result = {
        "status": "PASS",
        "configured": (root / WIKI_RELATIVE_PATH).is_dir(),
        "count": len(matches),
        "pages": [_wiki_summary(root, path, metadata) for path, metadata, _ in matches],
    }
    _emit(result, args.json)
    return 0


def _is_cjk_character(character: str) -> bool:
    value = ord(character)
    return (
        0x2E80 <= value <= 0x9FFF
        or 0xAC00 <= value <= 0xD7AF
        or 0xF900 <= value <= 0xFAFF
        or 0x3040 <= value <= 0x30FF
    )


def _wiki_search_tokens(value: str) -> set[str]:
    normalized = unicodedata.normalize("NFKC", value).casefold()
    tokens = set(re.findall(r"[a-z0-9][a-z0-9._-]*", normalized))
    run: list[str] = []

    def flush() -> None:
        if not run:
            return
        text = "".join(run)
        tokens.add(text)
        tokens.update(run)
        tokens.update(text[index : index + 2] for index in range(len(text) - 1))
        run.clear()

    for character in normalized:
        if _is_cjk_character(character):
            run.append(character)
        else:
            flush()
    flush()
    return {token for token in tokens if token}


def _wiki_query_command(args: argparse.Namespace) -> int:
    root = _runtime_project_root()
    payload = _wiki_payload(args, required=True)
    _wiki_reject_unknown(
        payload,
        {"query", "category", "status", "tag", "limit"},
        "wiki query input",
    )
    query = payload.pop("query", None)
    if not isinstance(query, str) or not query.strip():
        raise EZPowersError("wiki query requires a non-empty query string")
    query_normalized = unicodedata.normalize("NFKC", query).casefold().strip()
    query_tokens = _wiki_search_tokens(query)
    matches: list[tuple[int, pathlib.Path, dict[str, Any]]] = []
    for path, metadata, body in _wiki_filter_pages(root, payload):
        searchable = "\n".join(
            [
                metadata["title"],
                metadata["category"],
                " ".join(metadata["tags"]),
                body,
            ]
        )
        normalized = unicodedata.normalize("NFKC", searchable).casefold()
        tokens = _wiki_search_tokens(searchable)
        overlap = query_tokens & tokens
        if not overlap and query_normalized not in normalized:
            continue
        score = len(overlap)
        if query_normalized in normalized:
            score += 10
        if query_normalized in metadata["tags"]:
            score += 5
        matches.append((score, path, metadata))
    matches.sort(
        key=lambda item: (item[0], item[2]["updated_at"], item[2]["id"]),
        reverse=True,
    )
    result = {
        "status": "PASS",
        "query": query,
        "count": len(matches),
        "pages": [
            {**_wiki_summary(root, path, metadata), "score": score}
            for score, path, metadata in matches
        ],
    }
    _emit(result, args.json)
    return 0


def _wiki_lint_payload(root: pathlib.Path) -> tuple[dict[str, Any], int]:
    wiki_root = root / WIKI_RELATIVE_PATH
    if not wiki_root.exists():
        return {
            "status": "UNCONFIGURED",
            "configured": False,
            "page_count": 0,
            "errors": [],
        }, 0
    errors: list[str] = []
    pages: list[tuple[pathlib.Path, dict[str, Any], str]] = []
    pages_root = wiki_root / "pages"
    if not pages_root.is_dir():
        errors.append("wiki pages directory is missing")
    else:
        for path in sorted(pages_root.iterdir()):
            if path.suffix.lower() != ".md" or path.is_symlink() or not path.is_file():
                errors.append(
                    "unsupported wiki page entry: "
                    + path.relative_to(root).as_posix()
                )
                continue
            try:
                metadata, body = _wiki_parse_page(path)
                pages.append((path, metadata, body))
                if metadata["status"] == "promoted":
                    target = _safe_document_path(
                        root,
                        metadata["promoted_to"],
                        "promoted wiki target",
                    )
                    if not target.is_file():
                        errors.append(f"{metadata['id']}: promoted target is missing")
                    elif _sha256_file(target) != metadata["promoted_sha256"]:
                        errors.append(f"{metadata['id']}: promoted target hash drift")
            except EZPowersError as exc:
                errors.append(str(exc))
    index_path = wiki_root / "index.md"
    expected_index = _wiki_index_bytes(root, pages)
    if not index_path.is_file():
        errors.append("wiki index.md is missing")
    else:
        try:
            if index_path.read_bytes() != expected_index:
                errors.append("wiki index.md is stale; run wiki refresh")
        except OSError as exc:
            errors.append(f"cannot read wiki index.md: {exc}")
    if not (wiki_root / "log.md").is_file():
        errors.append("wiki log.md is missing")
    return {
        "status": "PASS" if not errors else "FAIL",
        "configured": True,
        "page_count": len(pages),
        "errors": errors,
    }, 0 if not errors else 1


def _wiki_lint_command(args: argparse.Namespace) -> int:
    root = _runtime_project_root()
    payload, code = _wiki_lint_payload(root)
    _emit(payload, args.json)
    return code


def _wiki_refresh_command(args: argparse.Namespace) -> int:
    root = _runtime_project_root()
    with _runtime_lock(root):
        payload = _wiki_refresh_locked(root)
    _emit(payload, args.json)
    return 0


def _wiki_promotion_state(
    root: pathlib.Path,
    payload: dict[str, Any],
) -> tuple[pathlib.Path, dict[str, Any], str, pathlib.Path, str, str]:
    _wiki_reject_unknown(payload, {"id", "target"}, "wiki promote input")
    page_id = payload.get("id")
    target_name = payload.get("target")
    if not isinstance(page_id, str) or not isinstance(target_name, str):
        raise EZPowersError("wiki promote requires string id and target fields")
    page_path = _wiki_page_path(root, page_id)
    if not page_path.is_file():
        raise EZPowersError(f"wiki page does not exist: {page_id}")
    metadata, body = _wiki_parse_page(page_path)
    target_path = _safe_document_path(root, target_name, "wiki promotion target")
    if not target_path.is_file():
        raise EZPowersError(
            "wiki promotion target must already exist; author it through the documentation workflow first"
        )
    target_sha = _sha256_file(target_path)
    token = _sha256_bytes(
        _json_bytes(
            {
                "schema_version": SCHEMA_VERSION,
                "page": _relative(root, page_path),
                "page_sha256": _sha256_file(page_path),
                "target": _relative(root, target_path),
                "target_sha256": target_sha,
            }
        )
    )
    return page_path, metadata, body, target_path, target_sha, token


def _wiki_promote_command(args: argparse.Namespace) -> int:
    root = _runtime_project_root()
    payload = _wiki_payload(args, required=True)
    if not args.confirm:
        page_path, metadata, _, target_path, target_sha, token = _wiki_promotion_state(
            root, payload
        )
        result = {
            "status": "READY",
            "preview_sha256": token,
            "page": _wiki_summary(root, page_path, metadata),
            "target": _relative(root, target_path),
            "target_sha256": target_sha,
        }
        _emit(result, args.json)
        return 0
    if not args.preview_sha256:
        raise EZPowersError("--confirm requires --preview-sha256")
    with _runtime_lock(root):
        page_path, metadata, body, target_path, target_sha, token = _wiki_promotion_state(
            root, payload
        )
        if token != args.preview_sha256:
            raise InstallConflict("conflict: wiki promotion preview is stale")
        changed = not (
            metadata["status"] == "promoted"
            and metadata.get("promoted_to") == _relative(root, target_path)
            and metadata.get("promoted_sha256") == target_sha
        )
        if changed:
            metadata.update(
                {
                    "status": "promoted",
                    "updated_at": _utc_now(),
                    "promoted_to": _relative(root, target_path),
                    "promoted_sha256": target_sha,
                    "promoted_at": _utc_now(),
                }
            )
            _atomic_write(page_path, _wiki_render_page(metadata, body))
            _wiki_refresh_locked(root, log_event=False)
            _wiki_log(root, "promote", f"{metadata['id']} -> {_relative(root, target_path)}")
    result = {
        "status": "PASS",
        "changed": changed,
        "page": _wiki_summary(root, page_path, metadata),
        "target_sha256": target_sha,
    }
    _emit(result, args.json)
    return 0


def _wiki_prune_state(
    root: pathlib.Path,
    payload: dict[str, Any],
) -> tuple[list[tuple[pathlib.Path, dict[str, Any]]], str]:
    _wiki_reject_unknown(payload, {"ids"}, "wiki prune input")
    ids = payload.get("ids")
    if (
        not isinstance(ids, list)
        or not ids
        or any(not isinstance(page_id, str) for page_id in ids)
    ):
        raise EZPowersError("wiki prune requires a non-empty string ids array")
    if len(ids) != len(set(ids)):
        raise EZPowersError("wiki prune ids must be unique")
    pages: list[tuple[pathlib.Path, dict[str, Any]]] = []
    token_pages = []
    for page_id in sorted(ids):
        path = _wiki_page_path(root, page_id)
        if not path.is_file():
            raise EZPowersError(f"wiki page does not exist: {page_id}")
        metadata, _ = _wiki_parse_page(path)
        if metadata["status"] == "promoted":
            raise EZPowersError(f"promoted wiki page cannot be pruned: {page_id}")
        digest = _sha256_file(path)
        pages.append((path, metadata))
        token_pages.append({"id": page_id, "sha256": digest, "status": metadata["status"]})
    token = _sha256_bytes(
        _json_bytes({"schema_version": SCHEMA_VERSION, "pages": token_pages})
    )
    return pages, token


def _wiki_prune_command(args: argparse.Namespace) -> int:
    root = _runtime_project_root()
    payload = _wiki_payload(args, required=True)
    if not args.confirm:
        pages, token = _wiki_prune_state(root, payload)
        result = {
            "status": "READY",
            "preview_sha256": token,
            "pages": [
                _wiki_summary(root, path, metadata) for path, metadata in pages
            ],
        }
        _emit(result, args.json)
        return 0
    if not args.preview_sha256:
        raise EZPowersError("--confirm requires --preview-sha256")
    with _runtime_lock(root):
        pages, token = _wiki_prune_state(root, payload)
        if token != args.preview_sha256:
            raise InstallConflict("conflict: wiki prune preview is stale")
        stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        backup_root = (
            root
            / WIKI_RELATIVE_PATH
            / "backups"
            / f"prune-{stamp}-{uuid.uuid4().hex[:8]}"
        )
        backup_root.mkdir(parents=True, exist_ok=False)
        manifest = {"schema_version": SCHEMA_VERSION, "created_at": _utc_now(), "pages": []}
        for path, metadata in pages:
            backup = backup_root / path.name
            shutil.copy2(path, backup)
            manifest["pages"].append(
                {"id": metadata["id"], "sha256": _sha256_file(path)}
            )
        _write_json(backup_root / "manifest.json", manifest)
        for path, _ in pages:
            path.unlink()
        _wiki_refresh_locked(root, log_event=False)
        _wiki_log(root, "prune", f"{len(pages)} pages; backup {_relative(root, backup_root)}")
    result = {
        "status": "PASS",
        "pruned": [metadata["id"] for _, metadata in pages],
        "backup_path": _relative(root, backup_root),
    }
    _emit(result, args.json)
    return 0


def _wiki_changed_paths(root: pathlib.Path) -> list[str]:
    try:
        tracked = _git_bytes(root, "diff", "--name-only", "-z", "HEAD")
    except EZPowersError:
        tracked = _git_bytes(root, "ls-files", "-z")
    untracked = _git_bytes(root, "ls-files", "--others", "--exclude-standard", "-z")
    names = {
        os.fsdecode(raw).replace("\\", "/")
        for raw in [*tracked.split(b"\0"), *untracked.split(b"\0")]
        if raw
    }
    return sorted(name for name in names if not _excluded_runtime_path(name))[:200]


def _wiki_evidence_summary(root: pathlib.Path, state: dict[str, Any]) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "active_plan": state.get("active_plan")
        if isinstance(state.get("active_plan"), str)
        else None,
        "checks": [],
    }
    latest = state.get("latest_evidence", {})
    pointer = latest.get("all") if isinstance(latest, dict) else None
    if not isinstance(pointer, dict) or not isinstance(pointer.get("path"), str):
        return summary
    try:
        evidence_path = _contained_path(
            root,
            pointer["path"],
            label="wiki evidence",
            must_exist=True,
        )
        evidence = _read_json(evidence_path)
    except EZPowersError:
        return summary
    summary["evidence_status"] = (
        evidence.get("status") if evidence.get("status") in {"PASS", "FAIL"} else None
    )
    checks = []
    for check in _iter_check_results(evidence):
        check_id = check.get("id")
        status = check.get("status")
        if isinstance(check_id, str) and status in {"PASS", "FAIL", "ERROR", "TIMEOUT"}:
            checks.append({"id": check_id, "status": status})
    summary["checks"] = checks[:200]
    return summary


def _wiki_capture_page(
    root: pathlib.Path,
    host: str,
    event: dict[str, Any],
) -> None:
    session_value = event.get("session_id")
    if not isinstance(session_value, str):
        session_value = ""
    session_value = session_value[:256]
    event_name = event.get("hook_event_name")
    if event_name not in {"SessionEnd", "session_end"}:
        event_name = "SessionEnd"
    session_hash = hashlib.sha256(session_value.encode("utf-8", "replace")).hexdigest()[:12]
    changed_paths = _wiki_changed_paths(root)
    state = _load_state(root)
    evidence = _wiki_evidence_summary(root, state)
    title = f"{host} session {dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}"
    lines = [
        f"# {title}",
        "",
        "## Session",
        "",
        f"- Host: `{host}`",
        f"- Event: `{event_name}`",
        f"- Session fingerprint: `{session_hash}`",
        f"- Active plan: `{evidence.get('active_plan') or '-'}`",
        f"- Evidence status: `{evidence.get('evidence_status') or '-'}`",
        "",
        "## Changed paths",
        "",
    ]
    if changed_paths:
        lines.extend(f"- `{name}`" for name in changed_paths)
    else:
        lines.append("- None")
    lines.extend(["", "## Check outcomes", ""])
    checks = evidence.get("checks", [])
    if checks:
        lines.extend(f"- `{item['id']}`: {item['status']}" for item in checks)
    else:
        lines.append("- None")
    _wiki_add_locked(
        root,
        title=title,
        category="session-log",
        tags=["session", host],
        body="\n".join(lines),
        source=f"session-end:{host}",
    )


def _wiki_capture_command(args: argparse.Namespace) -> int:
    # SessionEnd capture is deliberately best effort. It consumes bounded JSON
    # input, persists only an allowlisted summary, and never blocks the host.
    root = _runtime_project_root()
    try:
        raw = sys.stdin.buffer.read(262145)
        if len(raw) > 262144:
            raise EZPowersError("SessionEnd payload exceeds 256 KiB")
        event = json.loads(raw.decode("utf-8")) if raw.strip() else {}
        if not isinstance(event, dict):
            raise EZPowersError("SessionEnd payload must be a JSON object")
        with _runtime_lock(root):
            _wiki_capture_page(root, args.host, event)
    except Exception as exc:
        with contextlib.suppress(Exception):
            errors_root = root / WIKI_RELATIVE_PATH / "errors"
            errors_root.mkdir(parents=True, exist_ok=True)
            error_id = f"{dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{uuid.uuid4().hex[:8]}"
            _write_json(
                errors_root / f"{error_id}.json",
                {
                    "schema_version": SCHEMA_VERSION,
                    "recorded_at": _utc_now(),
                    "host": args.host,
                    "error_type": type(exc).__name__,
                    "message": str(exc)[:1000],
                },
            )
    print("{}")
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


def _validate_design_context(
    root: pathlib.Path,
    spec: dict[str, Any],
    errors: list[str],
) -> dict[str, Any] | None:
    """Validate the additive v5.5 design context while accepting legacy specs."""
    if "design_context" not in spec:
        return None
    value = spec.get("design_context")
    if not isinstance(value, dict) or not isinstance(value.get("required"), bool):
        errors.append("spec.design_context must be an object with boolean required")
        return None
    if value["required"] is False:
        reason = value.get("reason")
        if not isinstance(reason, str) or not reason.strip():
            errors.append("spec.design_context.reason is required when UI design is not required")
        if "frontend_artifact" in value or "systems" in value:
            errors.append(
                "spec.design_context must not name frontend artifacts when required is false"
            )
        return value

    frontend_artifact = value.get("frontend_artifact")
    systems = value.get("systems")
    if not isinstance(frontend_artifact, str) or not frontend_artifact:
        errors.append(
            "spec.design_context.frontend_artifact is required for UI work"
        )
    else:
        try:
            path = _safe_document_path(
                root,
                frontend_artifact,
                "spec.design_context.frontend_artifact",
            )
            if path.name == "DESIGN.md":
                errors.append(
                    "spec.design_context.frontend_artifact must name the broader frontend design artifact"
                )
        except EZPowersError as exc:
            errors.append(str(exc))
    if (
        not isinstance(systems, list)
        or not systems
        or any(not isinstance(item, str) or not item for item in systems)
    ):
        errors.append(
            "spec.design_context.systems must be a non-empty DESIGN.md path array"
        )
    else:
        normalized: set[str] = set()
        for item in systems:
            try:
                path = _safe_document_path(root, item, "spec.design_context.system")
                relative = _relative(root, path)
                if pathlib.PurePosixPath(relative).name != "DESIGN.md":
                    errors.append(
                        f"spec.design_context system must end in DESIGN.md: {item}"
                    )
                if relative in normalized:
                    errors.append(
                        f"spec.design_context contains duplicate system: {relative}"
                    )
                normalized.add(relative)
            except EZPowersError as exc:
                errors.append(str(exc))
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
    criteria_by_id = _validate_spec_value(root, spec, errors)
    return spec_path, spec, criteria_by_id


def _validate_spec_value(
    root: pathlib.Path,
    spec: dict[str, Any],
    errors: list[str],
    *,
    validate_design_context: bool = True,
) -> dict[str, dict[str, Any]]:
    """Normalize the shared spec value used by ordinary and staged flows."""
    if spec.get("schema_version") != SCHEMA_VERSION:
        errors.append("spec schema_version must be 1")
    if validate_design_context:
        _validate_design_context(root, spec, errors)

    criteria_by_id: dict[str, dict[str, Any]] = {}
    criteria = spec.get("criteria", [])
    if not isinstance(criteria, list) or not criteria:
        errors.append("spec.criteria must be a non-empty array")
        return criteria_by_id
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
    return criteria_by_id


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
    allow_concurrency: bool = False,
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
    concurrency = {"safe": False, "resource_locks": []}
    if "concurrency" in raw:
        raw_concurrency = raw.get("concurrency")
        if not allow_concurrency:
            errors.append(f"{label}.concurrency requires schema_version 2")
        if not isinstance(raw_concurrency, dict):
            errors.append(f"{label}.concurrency must be an object")
        else:
            unknown = set(raw_concurrency) - {"safe", "resource_locks"}
            if unknown:
                errors.append(
                    f"{label}.concurrency contains unknown fields: "
                    + ", ".join(sorted(unknown))
                )
            safe = raw_concurrency.get("safe")
            locks = raw_concurrency.get("resource_locks")
            if not isinstance(safe, bool):
                errors.append(f"{label}.concurrency.safe must be a boolean")
                safe = False
            if (
                not isinstance(locks, list)
                or any(
                    not isinstance(item, str)
                    or not RESOURCE_LOCK_RE.fullmatch(item)
                    for item in locks
                )
            ):
                errors.append(
                    f"{label}.concurrency.resource_locks must be a valid string array"
                )
                locks = []
            elif len(set(locks)) != len(locks):
                errors.append(
                    f"{label}.concurrency.resource_locks must not contain duplicates"
                )
            concurrency = {
                "safe": bool(safe),
                "resource_locks": list(locks),
            }
    return {
        "id": check_id,
        "argv": list(argv),
        "cwd": cwd,
        "timeout_seconds": timeout,
        "kind": kind,
        "concurrency": concurrency,
    }


def _validate_config_value(
    root: pathlib.Path,
    config: dict[str, Any],
    errors: list[str],
) -> tuple[
    dict[str, dict[str, Any]],
    list[str],
    int,
    int,
    ProjectProfilePolicy,
]:
    raw_version = config.get("schema_version")
    if raw_version not in CONFIG_SCHEMA_VERSIONS:
        errors.append("config schema_version must be 1, 2, or 3")
    config_version = raw_version if raw_version in CONFIG_SCHEMA_VERSIONS else 1
    profile = SOFTWARE_PROFILE
    raw_profile = config.get("project_profile")
    if config_version == PLANNING_SCHEMA_VERSION:
        if raw_profile not in PROJECT_PROFILE_POLICIES:
            errors.append("config.project_profile must be software or planning for schema_version 3")
        else:
            profile = PROJECT_PROFILE_POLICIES[str(raw_profile)]
    elif "project_profile" in config:
        errors.append("config.project_profile requires schema_version 3")
    max_parallel_checks = 1
    if config_version >= 2:
        verification = config.get("verification")
        if not isinstance(verification, dict):
            errors.append(
                f"config.verification must be an object for schema_version {config_version}"
            )
        else:
            unknown = set(verification) - {"max_parallel_checks"}
            if unknown:
                errors.append(
                    "config.verification contains unknown fields: "
                    + ", ".join(sorted(unknown))
                )
            raw_max = verification.get("max_parallel_checks")
            if (
                not isinstance(raw_max, int)
                or isinstance(raw_max, bool)
                or not 1 <= raw_max <= 32
            ):
                errors.append(
                    "config.verification.max_parallel_checks must be an integer from 1 to 32"
                )
            else:
                max_parallel_checks = raw_max
    elif "verification" in config:
        errors.append("config.verification requires schema_version 2 or 3")
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
            allow_concurrency=config_version >= 2,
        )
        if normalized:
            project_checks[str(check_id)] = normalized
    required_checks = config.get("required_checks", [])
    if not isinstance(required_checks, list) or any(
        not isinstance(item, str) for item in required_checks
    ):
        errors.append("config.required_checks must be a string array")
        required_checks = []
    elif len(set(required_checks)) != len(required_checks):
        errors.append("config.required_checks must not contain duplicates")
    for check_id in required_checks:
        if check_id not in project_checks:
            errors.append(f"config.required_checks references unknown check: {check_id}")
    return (
        project_checks,
        list(required_checks),
        int(config_version),
        int(max_parallel_checks),
        profile,
    )


def _check_contract_sha256(check: dict[str, Any]) -> str:
    contract = {
        key: check[key]
        for key in (
            "id",
            "argv",
            "cwd",
            "timeout_seconds",
            "kind",
            "concurrency",
        )
    }
    return _sha256_bytes(_json_bytes(contract))


def _task_check_node_id(task_id: str, index: int, check_id: str) -> str:
    return f"check:task:{task_id}:{index}:{check_id}"


def _project_check_node_id(index: int, check_id: str) -> str:
    return f"check:project:{index}:{check_id}"


def _topological_task_waves(
    tasks: list[dict[str, Any]],
    errors: list[str],
    *,
    plan_schema_version: int,
) -> list[list[str]]:
    if plan_schema_version == 1:
        return [[str(task["id"])] for task in tasks]
    ordered_ids = [str(task["id"]) for task in tasks]
    known = set(ordered_ids)
    dependencies: dict[str, list[str]] = {}
    for task in tasks:
        task_id = str(task["id"])
        raw = task.get("depends_on", [])
        if not isinstance(raw, list) or any(not isinstance(item, str) for item in raw):
            errors.append(f"task {task_id} depends_on must be a string array")
            raw = []
        if len(set(raw)) != len(raw):
            errors.append(f"task {task_id} depends_on must not contain duplicates")
        for dependency in raw:
            if dependency == task_id:
                errors.append(f"task {task_id} cannot depend on itself")
            elif dependency not in known:
                errors.append(
                    f"task {task_id} depends_on references unknown task: {dependency}"
                )
        dependencies[task_id] = list(raw)

    remaining = list(ordered_ids)
    completed: set[str] = set()
    waves: list[list[str]] = []
    while remaining:
        wave = [
            task_id
            for task_id in remaining
            if all(dependency in completed for dependency in dependencies[task_id])
        ]
        if not wave:
            errors.append(
                "plan task dependency cycle detected: " + ", ".join(remaining)
            )
            break
        waves.append(wave)
        completed.update(wave)
        remaining = [task_id for task_id in remaining if task_id not in completed]
    return waves


def _planning_artifact_path(
    root: pathlib.Path,
    value: Any,
    *,
    label: str,
    must_exist: bool,
) -> tuple[str, pathlib.Path] | None:
    if not isinstance(value, str) or not value or not _is_project_relative_text(value):
        raise EZPowersError(f"{label} must be a project-relative file path")
    normalized = pathlib.PurePosixPath(value.replace("\\", "/"))
    if (
        normalized.is_absolute()
        or not normalized.parts
        or ".." in normalized.parts
        or normalized.parts[0] in {".git", ".ezpowers"}
    ):
        raise EZPowersError(f"{label} must be a safe project product path: {value}")
    canonical = normalized.as_posix()
    path = _safe_target(root, canonical, label)
    if must_exist and not path.exists():
        raise EZPowersError(f"{label} does not exist: {canonical}")
    if path.exists() and (path.is_symlink() or not path.is_file()):
        raise EZPowersError(f"{label} must be a regular non-symlink file: {canonical}")
    return canonical, path


def _planning_path_key(path: pathlib.Path) -> str:
    value = str(path.resolve(strict=False))
    return os.path.normcase(value) if os.name == "nt" else value


def _normalize_planning_artifacts(
    root: pathlib.Path,
    *,
    plan: dict[str, Any],
    profile: ProjectProfilePolicy,
    plan_schema_version: int,
    criteria_by_id: dict[str, dict[str, Any]],
    tasks: list[dict[str, Any]],
    project_checks: dict[str, dict[str, Any]],
    top_checks: dict[str, dict[str, Any]],
    errors: list[str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if profile.name != "planning" or plan_schema_version != PLANNING_SCHEMA_VERSION:
        for field in ("inputs", "deliverables"):
            if field in plan:
                errors.append(f"plan.{field} requires the planning profile and schema_version 3")
        return [], []

    raw_inputs = plan.get("inputs")
    if not isinstance(raw_inputs, list):
        errors.append("planning plan.inputs must be an array")
        raw_inputs = []
    inputs: list[dict[str, Any]] = []
    input_ids: set[str] = set()
    input_paths: dict[str, str] = {}
    input_path_keys: set[str] = set()
    for index, raw in enumerate(raw_inputs):
        label = f"plan.inputs[{index}]"
        if not isinstance(raw, dict) or set(raw) != {"id", "path"}:
            errors.append(f"{label} must contain exactly id and path")
            continue
        input_id = raw.get("id")
        if (
            not isinstance(input_id, str)
            or not ID_RE.fullmatch(input_id)
            or input_id in input_ids
        ):
            errors.append(f"invalid or duplicate planning input id: {input_id!r}")
            continue
        input_ids.add(input_id)
        try:
            parsed = _planning_artifact_path(
                root,
                raw.get("path"),
                label=f"{label}.path",
                must_exist=True,
            )
            assert parsed is not None
            path_name, path = parsed
        except EZPowersError as exc:
            errors.append(str(exc))
            continue
        path_key = _planning_path_key(path)
        if path_key in input_path_keys:
            errors.append(f"duplicate planning input path: {path_name}")
            continue
        input_path_keys.add(path_key)
        input_paths[input_id] = path_key
        try:
            digest = _sha256_file(path)
        except OSError as exc:
            errors.append(f"cannot hash planning input {path_name}: {exc}")
            continue
        inputs.append({"id": input_id, "path": path_name, "sha256": digest})

    raw_deliverables = plan.get("deliverables")
    if not isinstance(raw_deliverables, list) or not raw_deliverables:
        errors.append("planning plan.deliverables must be a non-empty array")
        raw_deliverables = []
    deliverables: list[dict[str, Any]] = []
    deliverable_ids: set[str] = set()
    output_path_keys: set[str] = set()
    criterion_counts = {criterion_id: 0 for criterion_id in criteria_by_id}
    referenced_inputs: set[str] = set()
    known_named_checks = set(project_checks) | set(top_checks)
    task_check_criteria: dict[str, set[str]] = {}
    for task in tasks:
        for check in task.get("checks", []):
            task_check_criteria.setdefault(str(check["id"]), set()).update(
                str(item) for item in task.get("criteria", [])
            )

    for index, raw in enumerate(raw_deliverables):
        label = f"plan.deliverables[{index}]"
        required_fields = {"id", "paths", "criteria", "input_ids", "review"}
        if not isinstance(raw, dict) or set(raw) != required_fields:
            errors.append(
                f"{label} must contain exactly id, paths, criteria, input_ids, and review"
            )
            continue
        deliverable_id = raw.get("id")
        if (
            not isinstance(deliverable_id, str)
            or not ID_RE.fullmatch(deliverable_id)
            or deliverable_id in deliverable_ids
        ):
            errors.append(f"invalid or duplicate deliverable id: {deliverable_id!r}")
            continue
        deliverable_ids.add(deliverable_id)

        raw_paths = raw.get("paths")
        if (
            not isinstance(raw_paths, list)
            or not raw_paths
            or any(not isinstance(item, str) for item in raw_paths)
            or len(set(raw_paths)) != len(raw_paths)
        ):
            errors.append(f"deliverable {deliverable_id} paths must be a unique non-empty string array")
            raw_paths = []
        paths: list[str] = []
        for path_index, raw_path in enumerate(raw_paths):
            try:
                parsed = _planning_artifact_path(
                    root,
                    raw_path,
                    label=f"deliverable {deliverable_id} path {path_index}",
                    must_exist=False,
                )
                assert parsed is not None
                path_name, path = parsed
            except EZPowersError as exc:
                errors.append(str(exc))
                continue
            path_key = _planning_path_key(path)
            if path_key in output_path_keys:
                errors.append(f"duplicate deliverable output path: {path_name}")
                continue
            if path_key in input_path_keys:
                errors.append(f"planning input and deliverable output paths overlap: {path_name}")
                continue
            output_path_keys.add(path_key)
            paths.append(path_name)

        raw_criteria = raw.get("criteria")
        if (
            not isinstance(raw_criteria, list)
            or not raw_criteria
            or any(not isinstance(item, str) for item in raw_criteria)
            or len(set(raw_criteria)) != len(raw_criteria)
        ):
            errors.append(
                f"deliverable {deliverable_id} criteria must be a unique non-empty string array"
            )
            raw_criteria = []
        criteria: list[str] = []
        for criterion_id in raw_criteria:
            if criterion_id not in criteria_by_id:
                errors.append(
                    f"deliverable {deliverable_id} references unknown criterion: {criterion_id}"
                )
                continue
            criterion_counts[criterion_id] += 1
            criteria.append(criterion_id)

        raw_input_ids = raw.get("input_ids")
        if (
            not isinstance(raw_input_ids, list)
            or any(not isinstance(item, str) for item in raw_input_ids)
            or len(set(raw_input_ids)) != len(raw_input_ids)
        ):
            errors.append(f"deliverable {deliverable_id} input_ids must be a unique string array")
            raw_input_ids = []
        normalized_input_ids: list[str] = []
        for input_id in raw_input_ids:
            if input_id not in input_ids:
                errors.append(
                    f"deliverable {deliverable_id} references unknown input: {input_id}"
                )
                continue
            referenced_inputs.add(input_id)
            normalized_input_ids.append(input_id)

        raw_review = raw.get("review")
        review_mode = "direct"
        review_checks: list[str] = []
        if not isinstance(raw_review, dict) or set(raw_review) != {"mode", "checks"}:
            errors.append(
                f"deliverable {deliverable_id} review must contain exactly mode and checks"
            )
        else:
            review_mode = str(raw_review.get("mode", ""))
            raw_review_checks = raw_review.get("checks")
            if review_mode not in {"direct", "inspected"}:
                errors.append(
                    f"deliverable {deliverable_id} review.mode must be direct or inspected"
                )
            if (
                not isinstance(raw_review_checks, list)
                or any(not isinstance(item, str) for item in raw_review_checks)
                or len(set(raw_review_checks)) != len(raw_review_checks)
            ):
                errors.append(
                    f"deliverable {deliverable_id} review.checks must be a unique string array"
                )
                raw_review_checks = []
            if review_mode == "direct" and raw_review_checks:
                errors.append(f"direct deliverable {deliverable_id} must not declare review checks")
            if review_mode == "inspected" and not raw_review_checks:
                errors.append(f"inspected deliverable {deliverable_id} requires review checks")
            for check_id in raw_review_checks:
                if check_id not in known_named_checks:
                    errors.append(
                        f"deliverable {deliverable_id} references unknown review check: {check_id}"
                    )
                    continue
                if not task_check_criteria.get(check_id, set()).intersection(criteria):
                    errors.append(
                        f"deliverable {deliverable_id} review check {check_id} is not used by a task covering that deliverable"
                    )
                    continue
                review_checks.append(check_id)

        deliverables.append(
            {
                "id": deliverable_id,
                "paths": paths,
                "criteria": criteria,
                "input_ids": normalized_input_ids,
                "review": {"mode": review_mode, "checks": review_checks},
            }
        )

    for criterion_id, count in criterion_counts.items():
        if count != 1:
            errors.append(
                f"criterion must be mapped to exactly one deliverable: {criterion_id}"
            )
    for input_id in sorted(input_ids - referenced_inputs):
        errors.append(f"planning input is not referenced by any deliverable: {input_id}")
    return inputs, deliverables


def _build_assurance_graph(
    *,
    criteria_by_id: dict[str, dict[str, Any]],
    tasks: list[dict[str, Any]],
    project_checks: dict[str, dict[str, Any]],
    required_checks: list[str],
    task_waves: list[list[str]],
    plan_schema_version: int,
    config_schema_version: int,
    max_parallel_checks: int,
    profile: ProjectProfilePolicy,
    inputs: list[dict[str, Any]],
    deliverables: list[dict[str, Any]],
) -> tuple[dict[str, Any], str]:
    effective_max = (
        max_parallel_checks
        if plan_schema_version >= 2 and config_schema_version >= 2
        else 1
    )
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, str]] = []
    for criterion_id in criteria_by_id:
        nodes.append(
            {"id": f"criterion:{criterion_id}", "type": "criterion"}
        )
    for task in tasks:
        task_id = str(task["id"])
        nodes.append(
            {
                "id": f"task:{task_id}",
                "type": "task",
                "depends_on": list(task.get("depends_on", [])),
            }
        )
        for criterion_id in task["criteria"]:
            edges.append(
                {
                    "source": f"criterion:{criterion_id}",
                    "target": f"task:{task_id}",
                    "relation": "covered_by",
                }
            )
        for dependency in task.get("depends_on", []):
            edges.append(
                {
                    "source": f"task:{dependency}",
                    "target": f"task:{task_id}",
                    "relation": "precedes",
                }
            )
        for index, check in enumerate(task["checks"], 1):
            node_id = _task_check_node_id(task_id, index, str(check["id"]))
            concurrency = check["concurrency"]
            nodes.append(
                {
                    "id": node_id,
                    "type": "check",
                    "check_id": check["id"],
                    "phase": "task",
                    "kind": check["kind"],
                    "safe": bool(concurrency["safe"]),
                    "resource_locks": list(concurrency["resource_locks"]),
                    "implicit_lock": f"check-id.{check['id']}",
                    "contract_sha256": _check_contract_sha256(check),
                }
            )
            edges.append(
                {
                    "source": f"task:{task_id}",
                    "target": node_id,
                    "relation": "verified_by",
                }
            )
            edges.append(
                {
                    "source": node_id,
                    "target": "evidence:all",
                    "relation": "produces",
                }
    )
    for index, check_id in enumerate(required_checks, 1):
        check = project_checks.get(check_id)
        if check is None:
            continue
        node_id = _project_check_node_id(index, check_id)
        concurrency = check["concurrency"]
        nodes.append(
            {
                "id": node_id,
                "type": "check",
                "check_id": check_id,
                "phase": "required",
                "kind": check["kind"],
                "safe": bool(concurrency["safe"]),
                "resource_locks": list(concurrency["resource_locks"]),
                "implicit_lock": f"check-id.{check_id}",
                "contract_sha256": _check_contract_sha256(check),
            }
        )
        edges.append(
            {
                "source": node_id,
                "target": "evidence:all",
                "relation": "produces",
            }
        )
    primary_review_id = f"review:{profile.primary_review_kind}"
    if profile.name == "planning":
        task_by_criterion: dict[str, str] = {}
        check_nodes: dict[tuple[str, str], list[str]] = {}
        for task in tasks:
            task_id = str(task["id"])
            for criterion_id in task["criteria"]:
                task_by_criterion[str(criterion_id)] = task_id
            for index, check in enumerate(task["checks"], 1):
                check_nodes.setdefault((task_id, str(check["id"])), []).append(
                    _task_check_node_id(task_id, index, str(check["id"]))
                )
        for entry in inputs:
            nodes.append(
                {
                    "id": f"input:{entry['id']}",
                    "type": "input",
                    "path": entry["path"],
                    "sha256": entry["sha256"],
                }
            )
        for deliverable in deliverables:
            deliverable_node = f"deliverable:{deliverable['id']}"
            nodes.append(
                {
                    "id": deliverable_node,
                    "type": "deliverable",
                    "paths": list(deliverable["paths"]),
                    "review_mode": deliverable["review"]["mode"],
                    "inspection_checks": list(deliverable["review"]["checks"]),
                }
            )
            for criterion_id in deliverable["criteria"]:
                edges.append(
                    {
                        "source": f"criterion:{criterion_id}",
                        "target": deliverable_node,
                        "relation": "realized_in",
                    }
                )
            producer_ids = {
                task_by_criterion[criterion_id]
                for criterion_id in deliverable["criteria"]
                if criterion_id in task_by_criterion
            }
            for task_id in sorted(producer_ids):
                edges.append(
                    {
                        "source": f"task:{task_id}",
                        "target": deliverable_node,
                        "relation": "produces",
                    }
                )
                for check_id in deliverable["review"]["checks"]:
                    for node_id in check_nodes.get((task_id, check_id), []):
                        edges.append(
                            {
                                "source": deliverable_node,
                                "target": node_id,
                                "relation": "inspected_by",
                            }
                        )
            for input_id in deliverable["input_ids"]:
                edges.append(
                    {
                        "source": f"input:{input_id}",
                        "target": deliverable_node,
                        "relation": "informs",
                    }
                )
            edges.append(
                {
                    "source": deliverable_node,
                    "target": primary_review_id,
                    "relation": "reviewed_by",
                }
            )

    nodes.extend(
        [
            {"id": "evidence:all", "type": "evidence"},
            {
                "id": primary_review_id,
                "type": "independent_review",
                "required_in": "harness-chain",
            },
            {
                "id": "review:adversarial-qa",
                "type": "independent_review",
                "required_in": "conditional-harness-chain",
            },
            {"id": "certificate:completion", "type": "certificate"},
        ]
    )
    edges.extend(
        [
            {
                "source": "evidence:all",
                "target": primary_review_id,
                "relation": "reviewed_by",
            },
            {
                "source": "evidence:all",
                "target": "review:adversarial-qa",
                "relation": "conditionally_reviewed_by",
            },
            {
                "source": "evidence:all",
                "target": "certificate:completion",
                "relation": "required_for",
            },
            {
                "source": primary_review_id,
                "target": "certificate:completion",
                "relation": "gates_chain",
            },
            {
                "source": "review:adversarial-qa",
                "target": "certificate:completion",
                "relation": "conditionally_gates_chain",
            },
        ]
    )
    graph = {
        "schema_version": profile.assurance_graph_schema_version,
        "plan_schema_version": plan_schema_version,
        "config_schema_version": config_schema_version,
        "execution": {
            "mode": "parallel-opt-in" if effective_max > 1 else "serial",
            "max_parallel_checks": effective_max,
        },
        "task_waves": [list(wave) for wave in task_waves],
        "nodes": sorted(nodes, key=lambda item: str(item["id"])),
        "edges": sorted(
            edges,
            key=lambda item: (
                str(item["source"]),
                str(item["target"]),
                str(item["relation"]),
            ),
        ),
    }
    if profile.name == "planning":
        graph["project_profile"] = profile.name
    return graph, _sha256_bytes(_json_bytes(graph))


def _normalize_plan_value(
    root: pathlib.Path,
    *,
    plan: dict[str, Any],
    criteria_by_id: dict[str, dict[str, Any]],
    project_checks: dict[str, dict[str, Any]],
    required_checks: list[str],
    config_schema_version: int,
    max_parallel_checks: int,
    profile: ProjectProfilePolicy,
    errors: list[str],
) -> dict[str, Any]:
    raw_version = plan.get("schema_version")
    if raw_version not in PLAN_SCHEMA_VERSIONS:
        errors.append("plan schema_version must be 1, 2, or 3")
    plan_schema_version = raw_version if raw_version in PLAN_SCHEMA_VERSIONS else 1
    if plan_schema_version not in profile.plan_schema_versions:
        allowed = ", ".join(str(item) for item in sorted(profile.plan_schema_versions))
        errors.append(
            f"project profile {profile.name} requires plan schema_version {allowed}"
        )

    top_checks: dict[str, dict[str, Any]] = {}
    raw_top_checks = plan.get("checks", {})
    if raw_top_checks is None:
        raw_top_checks = {}
    if not isinstance(raw_top_checks, dict):
        errors.append("plan.checks must be an object when present")
        raw_top_checks = {}
    for check_id, raw in raw_top_checks.items():
        name = str(check_id)
        if name in project_checks:
            errors.append(f"plan check collides with config check: {name}")
        normalized = _validate_check(
            raw,
            check_id=name,
            root=root,
            label=f"plan.checks.{name}",
            errors=errors,
            allow_concurrency=plan_schema_version >= 2,
        )
        if normalized:
            top_checks[name] = normalized

    raw_tasks = plan.get("tasks", [])
    if not isinstance(raw_tasks, list) or not raw_tasks:
        errors.append("plan.tasks must be a non-empty array")
        raw_tasks = []
    tasks: list[dict[str, Any]] = []
    task_ids: set[str] = set()
    inline_ids: set[str] = set()
    criterion_coverage: dict[str, list[dict[str, Any]]] = {
        key: [] for key in criteria_by_id
    }
    criterion_occurrences: dict[str, int] = {
        key: 0 for key in criteria_by_id
    }
    criterion_checks: dict[str, list[str]] = {
        key: [] for key in criteria_by_id
    }
    used_top_checks: set[str] = set()
    for index, raw_task in enumerate(raw_tasks):
        if not isinstance(raw_task, dict):
            errors.append(f"plan.tasks[{index}] must be an object")
            continue
        task_id = str(raw_task.get("id", ""))
        if not ID_RE.fullmatch(task_id) or task_id in task_ids:
            errors.append(f"invalid or duplicate task id: {task_id!r}")
        task_ids.add(task_id)
        if plan_schema_version >= 2 and "depends_on" not in raw_task:
            errors.append(
                f"task {task_id or index} depends_on is required for schema_version {plan_schema_version}"
            )
        if plan_schema_version == 1 and "depends_on" in raw_task:
            errors.append(f"task {task_id or index} depends_on requires schema_version 2")
        raw_dependencies = raw_task.get("depends_on", [])
        if not isinstance(raw_dependencies, list) or any(
            not isinstance(item, str) for item in raw_dependencies
        ):
            errors.append(f"task {task_id or index} depends_on must be a string array")
            raw_dependencies = []
        raw_criteria = raw_task.get("criteria", [])
        if (
            not isinstance(raw_criteria, list)
            or not raw_criteria
            or any(not isinstance(item, str) for item in raw_criteria)
        ):
            errors.append(
                f"task {task_id or index} criteria must be a non-empty string array"
            )
            raw_criteria = []
        for criterion_id in raw_criteria:
            if criterion_id not in criteria_by_id:
                errors.append(
                    f"task {task_id} references unknown criterion: {criterion_id}"
                )
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
                    errors.append(
                        f"task {task_id} references unknown check: {raw_check}"
                    )
                continue
            if not isinstance(raw_check, dict):
                errors.append(
                    f"task {task_id} check {check_index} must be an object or check id"
                )
                continue
            check_id = str(raw_check.get("id", ""))
            if (
                check_id in project_checks
                or check_id in top_checks
                or check_id in inline_ids
            ):
                errors.append(f"duplicate check id: {check_id}")
            inline_ids.add(check_id)
            normalized = _validate_check(
                raw_check,
                check_id=check_id,
                root=root,
                label=f"task {task_id} check {check_id or check_index}",
                errors=errors,
                allow_concurrency=plan_schema_version >= 2,
            )
            if normalized:
                normalized_checks.append(normalized)
        task = {
            "id": task_id,
            "depends_on": list(raw_dependencies),
            "criteria": list(raw_criteria),
            "checks": normalized_checks,
        }
        tasks.append(task)
        for criterion_id in raw_criteria:
            if criterion_id in criterion_coverage:
                criterion_coverage[criterion_id].extend(normalized_checks)
                criterion_checks[criterion_id].extend(
                    str(check["id"]) for check in normalized_checks
                )

    for check_id in sorted(set(top_checks) - used_top_checks):
        errors.append(f"plan check is not referenced by any task: {check_id}")
    for criterion_id, mapped_checks in criterion_coverage.items():
        if criterion_occurrences[criterion_id] != 1:
            errors.append(f"criterion must be mapped exactly once: {criterion_id}")
        if not mapped_checks:
            errors.append(
                f"criterion is not mapped to an executable check: {criterion_id}"
            )
            continue
        criterion = criteria_by_id[criterion_id]
        integration = bool(criterion.get("integration")) or str(
            criterion.get("verify_type", "")
        ).lower() in {"integration", "e2e"}
        if integration and not any(
            check.get("kind") in {"integration", "e2e", "smoke"}
            for check in mapped_checks
        ):
            errors.append(
                f"integration criterion {criterion_id} requires an integration, e2e, or smoke check"
            )

    inputs, deliverables = _normalize_planning_artifacts(
        root,
        plan=plan,
        profile=profile,
        plan_schema_version=int(plan_schema_version),
        criteria_by_id=criteria_by_id,
        tasks=tasks,
        project_checks=project_checks,
        top_checks=top_checks,
        errors=errors,
    )
    task_waves = _topological_task_waves(
        tasks,
        errors,
        plan_schema_version=int(plan_schema_version),
    )
    graph, graph_sha256 = _build_assurance_graph(
        criteria_by_id=criteria_by_id,
        tasks=tasks,
        project_checks=project_checks,
        required_checks=required_checks,
        task_waves=task_waves,
        plan_schema_version=int(plan_schema_version),
        config_schema_version=config_schema_version,
        max_parallel_checks=max_parallel_checks,
        profile=profile,
        inputs=inputs,
        deliverables=deliverables,
    )
    return {
        "plan_schema_version": int(plan_schema_version),
        "top_checks": top_checks,
        "tasks": tasks,
        "inputs": inputs,
        "deliverables": deliverables,
        "criterion_checks": criterion_checks,
        "task_waves": task_waves,
        "assurance_graph": graph,
        "assurance_graph_sha256": graph_sha256,
    }


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
    (
        project_checks,
        required_checks,
        config_schema_version,
        max_parallel_checks,
        profile,
    ) = _validate_config_value(root, config, errors)
    if plan_path.is_file():
        try:
            plan = _extract_block(plan_path, "plan")
        except EZPowersError as exc:
            errors.append(str(exc))
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

    normalized_plan = _normalize_plan_value(
        root,
        plan=plan,
        criteria_by_id=criteria_by_id,
        project_checks=project_checks,
        required_checks=required_checks,
        config_schema_version=config_schema_version,
        max_parallel_checks=max_parallel_checks,
        profile=profile,
        errors=errors,
    )

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
        profile=profile,
        spec=spec,
        plan=plan,
        inputs=normalized_plan["inputs"],
        deliverables=normalized_plan["deliverables"],
        tasks=normalized_plan["tasks"],
        project_checks=project_checks,
        required_checks=list(required_checks),
        plan_schema_version=normalized_plan["plan_schema_version"],
        config_schema_version=config_schema_version,
        max_parallel_checks=max_parallel_checks,
        task_waves=normalized_plan["task_waves"],
        assurance_graph=normalized_plan["assurance_graph"],
        assurance_graph_sha256=normalized_plan["assurance_graph_sha256"],
        errors=errors,
    )


def _chain_staging_bundle(
    root: pathlib.Path,
    bundle_argument: str,
    *,
    label: str,
) -> tuple[pathlib.Path, dict[str, Any]]:
    bundle = _contained_path(
        root,
        bundle_argument,
        label=label,
        must_exist=True,
        directory=True,
    )
    staging_root = (root / DOCS_STAGING_RELATIVE_PATH).resolve()
    try:
        bundle.resolve().relative_to(staging_root)
    except ValueError as exc:
        raise EZPowersError(
            f"{label} must be under {DOCS_STAGING_RELATIVE_PATH.as_posix()}"
        ) from exc
    manifest = _read_json(bundle / "bundle.json")
    return bundle, manifest


def _normalize_chain_value(value: dict[str, Any]) -> dict[str, Any]:
    if value.get("schema_version") != SCHEMA_VERSION:
        raise EZPowersError("chain configuration schema_version must be 1")
    raw_stages = value.get("optional_stages")
    if not isinstance(raw_stages, dict) or set(raw_stages) != CHAIN_OPTIONAL_STAGES:
        raise EZPowersError(
            "chain optional_stages must contain exactly deep_interview, "
            "frontend_design, and design_architecture"
        )
    stages: dict[str, str] = {}
    for stage in sorted(CHAIN_OPTIONAL_STAGES):
        mode = raw_stages.get(stage)
        if mode not in CHAIN_STAGE_MODES:
            raise EZPowersError(
                f"chain optional stage {stage} must be auto or always"
            )
        stages[stage] = str(mode)

    raw_limits = value.get("limits")
    if not isinstance(raw_limits, dict) or set(raw_limits) != set(
        CHAIN_LIMIT_DEFAULTS
    ):
        raise EZPowersError(
            "chain limits must contain exactly total_iterations, qa_cycles, "
            "validation_retries, review_retries, and identical_error_repeats"
        )
    limits: dict[str, int] = {}
    for name, (minimum, maximum) in CHAIN_LIMIT_RANGES.items():
        raw = raw_limits.get(name)
        if (
            not isinstance(raw, int)
            or isinstance(raw, bool)
            or not minimum <= raw <= maximum
        ):
            raise EZPowersError(
                f"chain limit {name} must be an integer from {minimum} to {maximum}"
            )
        limits[name] = raw

    raw_triggers = value.get("additional_qa_triggers", [])
    if not isinstance(raw_triggers, list) or any(
        not isinstance(item, str) or not item.strip() for item in raw_triggers
    ):
        raise EZPowersError("chain additional_qa_triggers must be a string array")
    triggers = sorted({item.strip() for item in raw_triggers})

    raw_hosts = value.get("hosts")
    if (
        not isinstance(raw_hosts, list)
        or not raw_hosts
        or any(item not in CHAIN_HOSTS for item in raw_hosts)
    ):
        raise EZPowersError("chain hosts must be a non-empty claude/codex array")
    hosts = sorted(set(str(item) for item in raw_hosts))
    return {
        "schema_version": SCHEMA_VERSION,
        "optional_stages": stages,
        "additional_qa_triggers": triggers,
        "limits": limits,
        "hosts": hosts,
        "mandatory_gates": [
            "spec",
            "plan",
            "acceptance-oracle",
            "independent-review",
            "verify",
            "certify",
        ],
        "qa_risks": sorted(CHAIN_QA_RISKS),
    }


def _load_chain_value(root: pathlib.Path) -> tuple[dict[str, Any], str]:
    path = root / CHAIN_RELATIVE_PATH
    value = _read_json(path)
    normalized = _normalize_chain_value(value)
    if not isinstance(value.get("configured_at"), str):
        raise EZPowersError(".ezpowers/chain.json configured_at is missing")
    normalized["configured_at"] = value["configured_at"]
    return normalized, _sha256_file(path)


def _chain_config_preview(
    root: pathlib.Path,
    bundle_argument: str,
) -> tuple[
    dict[str, Any],
    pathlib.Path,
    dict[str, Any],
    list[tuple[str, pathlib.Path, bytes, str]],
]:
    bundle, manifest = _chain_staging_bundle(
        root,
        bundle_argument,
        label="chain configuration bundle",
    )
    normalized = _normalize_chain_value(manifest)
    chain_path = root / CHAIN_RELATIVE_PATH
    target_states = [
        {
            "path": CHAIN_RELATIVE_PATH.as_posix(),
            "sha256": _sha256_file(chain_path) if chain_path.is_file() else None,
        }
    ]
    hook_updates: list[tuple[str, pathlib.Path, bytes, str]] = []
    host_prerequisites = _host_prerequisites(normalized["hosts"])
    conflicts = [
        str(item["message"])
        for item in host_prerequisites
        if item["status"] != "PASS"
    ]
    for host in sorted(CHAIN_HOSTS):
        action = "install"
        if host in normalized["hosts"]:
            path, data, host_conflicts = _chain_hook_update(root, host)
            conflicts.extend(host_conflicts)
        else:
            removal = _chain_hook_remove(root, host)
            if removal is None:
                continue
            path, data = removal
            action = "remove"
        hook_updates.append((host, path, data, action))
        target_states.append(
            {
                "path": _relative(root, path),
                "sha256": _sha256_file(path) if path.is_file() else None,
            }
        )
    config_path = root / CONFIG_RELATIVE_PATH
    token_payload = {
        "schema_version": SCHEMA_VERSION,
        "chain": normalized,
        "project_config_sha256": (
            _sha256_file(config_path) if config_path.is_file() else None
        ),
        "installation": _installed_identity(root),
        "host_prerequisites": host_prerequisites,
        "targets": target_states,
        "hook_updates": [
            {
                "host": host,
                "action": action,
                "path": _relative(root, path),
                "sha256": _sha256_bytes(data),
            }
            for host, path, data, action in hook_updates
        ],
    }
    preview_sha256 = _sha256_bytes(_json_bytes(token_payload))
    payload = {
        "status": "CONFLICT" if conflicts else "READY",
        "preview_sha256": preview_sha256,
        "conflicts": sorted(set(conflicts)),
        "host_prerequisites": host_prerequisites,
        "chain": normalized,
        "hooks": [
            {
                "host": host,
                "path": _relative(root, path),
                "events": [
                    "SessionStart",
                    "Stop",
                    "PreToolUse",
                    "SubagentStart",
                    "SubagentStop",
                ],
            }
            for host, path, _, action in hook_updates
            if action == "install"
        ],
        "removed_hosts": [
            host
            for host, _, _, action in hook_updates
            if action == "remove"
        ],
    }
    return payload, bundle, normalized, hook_updates


def _chain_config_preview_command(args: argparse.Namespace) -> int:
    root = _runtime_project_root()
    payload, _, _, _ = _chain_config_preview(root, args.bundle)
    _emit(payload, args.json)
    return 0 if payload["status"] == "READY" else 3


def _chain_config_apply_command(args: argparse.Namespace) -> int:
    root = _runtime_project_root()
    with _runtime_lock(root):
        payload, bundle, normalized, hook_updates = _chain_config_preview(
            root,
            args.bundle,
        )
        if args.preview_sha256 != payload["preview_sha256"]:
            raise InstallConflict(
                "conflict: chain configuration preview is stale or belongs "
                "to another bundle"
            )
        if payload["conflicts"]:
            raise InstallConflict(
                "conflict: chain configuration is not ready:\n- "
                + "\n- ".join(payload["conflicts"])
            )

        chain_path = root / CHAIN_RELATIVE_PATH
        originals: dict[pathlib.Path, bytes | None] = {
            chain_path: chain_path.read_bytes() if chain_path.is_file() else None
        }
        for _, path, _, _ in hook_updates:
            originals[path] = path.read_bytes() if path.is_file() else None
        value = dict(normalized)
        value["configured_at"] = _utc_now()
        try:
            _write_json(chain_path, value)
            for _, path, data, _ in hook_updates:
                _atomic_write(path, data)
            state = _load_state(root)
            state["chain_hosts"] = {}
            run = state.get("chain_run")
            if (
                isinstance(run, dict)
                and (
                    run.get("status") not in CHAIN_TERMINAL_STATUSES
                    or run.get("status") == "CERTIFIED"
                )
            ):
                _chain_mark_reapproval(
                    state,
                    ["project chain configuration changed"],
                )
            _save_state(root, state)
        except Exception:
            for path, original in originals.items():
                if original is None:
                    with contextlib.suppress(FileNotFoundError):
                        path.unlink()
                else:
                    _atomic_write(path, original)
            raise
        with contextlib.suppress(OSError):
            shutil.rmtree(bundle)
        result = {
            "status": "PASS",
            "preview_sha256": payload["preview_sha256"],
            "chain": CHAIN_RELATIVE_PATH.as_posix(),
            "hosts": normalized["hosts"],
            "next_status": "PENDING_HOST_TRUST",
        }
        _emit(result, args.json)
        return 0


def _chain_host_hook_present(root: pathlib.Path, host: str) -> bool:
    path = root / (
        ".claude/settings.json" if host == "claude" else ".codex/hooks.json"
    )
    if not path.is_file():
        return False
    try:
        value = _read_json(path)
    except EZPowersError:
        return False
    hooks = value.get("hooks")
    if not isinstance(hooks, dict):
        return False
    for event_name in (
        "SessionStart",
        "Stop",
        "PreToolUse",
        "SubagentStart",
        "SubagentStop",
    ):
        entries = hooks.get(event_name)
        if (
            not isinstance(entries, list)
            or not any(_command_mentions_chain_hook(item, host) for item in entries)
        ):
            return False
    return True


def _chain_config_status_payload(root: pathlib.Path) -> tuple[dict[str, Any], int]:
    chain_path = root / CHAIN_RELATIVE_PATH
    if not chain_path.is_file():
        return {
            "status": "UNCONFIGURED",
            "ready": False,
            "hosts": {},
            "reasons": ["no project harness chain is configured"],
        }, 0
    try:
        chain, chain_sha256 = _load_chain_value(root)
        state = _load_state(root)
    except EZPowersError as exc:
        return {
            "status": "FAIL",
            "ready": False,
            "hosts": {},
            "reasons": [str(exc)],
        }, 2
    host_status: dict[str, Any] = {}
    reasons: list[str] = []
    for host in chain["hosts"]:
        installed = _chain_host_hook_present(root, host)
        expected = (
            _chain_hook_identity(root, host, chain_sha256) if installed else None
        )
        record = state.get("chain_hosts", {}).get(host)
        permission_mode = (
            record.get("permission_mode") if isinstance(record, dict) else None
        )
        trusted = (
            isinstance(record, dict)
            and record.get("hook_identity") == expected
            and isinstance(record.get("session_id"), str)
            and bool(record["session_id"])
        )
        unattended = trusted and permission_mode in {
            "dontAsk",
            "bypassPermissions",
        }
        host_status[host] = {
            "hooks_installed": installed,
            "handshake": trusted,
            "unattended": unattended,
            "permission_mode": permission_mode,
            "session_id": record.get("session_id") if trusted else None,
        }
        if not installed:
            reasons.append(f"{host} chain hooks are missing or changed")
        elif not trusted:
            reasons.append(
                f"{host} chain hooks have not completed a trusted SessionStart handshake"
            )
        elif not unattended:
            reasons.append(
                f"{host} permission mode {permission_mode!r} can pause for "
                "interactive approval; use dontAsk or bypassPermissions "
                "before an unattended chain"
            )
    ready = not reasons
    return {
        "status": "READY" if ready else "PENDING_HOST_TRUST",
        "ready": ready,
        "chain_sha256": chain_sha256,
        "hosts": host_status,
        "reasons": reasons,
    }, 0


def _chain_config_status_command(args: argparse.Namespace) -> int:
    root = _runtime_project_root()
    payload, code = _chain_config_status_payload(root)
    _emit(payload, args.json)
    return code


def _validate_chain_staged_flow(
    root: pathlib.Path,
    *,
    spec_path: pathlib.Path,
    spec_target: str,
    plan_path: pathlib.Path,
) -> dict[str, Any]:
    errors: list[str] = []
    try:
        spec = _extract_block(spec_path, "spec")
    except EZPowersError as exc:
        raise EZPowersError(str(exc)) from exc
    criteria_by_id = _validate_spec_value(
        root,
        spec,
        errors,
        validate_design_context=False,
    )

    try:
        plan = _extract_block(plan_path, "plan")
    except EZPowersError as exc:
        raise EZPowersError(str(exc)) from exc
    if plan.get("spec") != spec_target:
        errors.append("staged plan.spec must equal the staged spec target")

    config = _read_json(root / CONFIG_RELATIVE_PATH)
    (
        project_checks,
        required_checks,
        config_schema_version,
        max_parallel_checks,
        profile,
    ) = _validate_config_value(root, config, errors)
    normalized_plan = _normalize_plan_value(
        root,
        plan=plan,
        criteria_by_id=criteria_by_id,
        project_checks=project_checks,
        required_checks=required_checks,
        config_schema_version=config_schema_version,
        max_parallel_checks=max_parallel_checks,
        profile=profile,
        errors=errors,
    )
    if errors:
        raise EZPowersError(
            "invalid staged spec/plan:\n- " + "\n- ".join(errors)
        )
    return {
        "spec": spec,
        "plan": plan,
        "criteria": criteria_by_id,
        "criterion_checks": normalized_plan["criterion_checks"],
        "top_checks": normalized_plan["top_checks"],
        "project_checks": project_checks,
        "required_checks": required_checks,
        "tasks": normalized_plan["tasks"],
        "inputs": normalized_plan["inputs"],
        "deliverables": normalized_plan["deliverables"],
        "project_profile": profile.name,
        "profile_policy": profile,
        "plan_schema_version": normalized_plan["plan_schema_version"],
        "config_schema_version": config_schema_version,
        "max_parallel_checks": max_parallel_checks,
        "task_waves": normalized_plan["task_waves"],
        "assurance_graph": normalized_plan["assurance_graph"],
        "assurance_graph_sha256": normalized_plan["assurance_graph_sha256"],
    }


def _load_chain_run_bundle(
    root: pathlib.Path,
    bundle_argument: str,
) -> tuple[pathlib.Path, dict[str, Any]]:
    bundle, manifest = _chain_staging_bundle(
        root,
        bundle_argument,
        label="chain run bundle",
    )
    config_errors: list[str] = []
    _, _, _, _, configured_profile = _validate_config_value(
        root,
        _read_json(root / CONFIG_RELATIVE_PATH),
        config_errors,
    )
    if config_errors:
        raise EZPowersError(
            "invalid .ezpowers/config.json:\n- " + "\n- ".join(config_errors)
        )
    if manifest.get("schema_version") != configured_profile.chain_bundle_schema_version:
        raise EZPowersError(
            "chain run bundle schema_version must be "
            f"{configured_profile.chain_bundle_schema_version} for the "
            f"{configured_profile.name} profile"
        )
    if configured_profile.name == "planning":
        if manifest.get("project_profile") != configured_profile.name:
            raise EZPowersError(
                "planning chain run bundle project_profile must be planning"
            )
    elif "project_profile" in manifest:
        raise EZPowersError(
            "chain run bundle project_profile requires the planning profile"
        )
    run_id = manifest.get("run_id")
    if not isinstance(run_id, str) or not ID_RE.fullmatch(run_id):
        raise EZPowersError("chain run_id must be a valid identifier")
    request = manifest.get("request")
    if not isinstance(request, str) or not request.strip():
        raise EZPowersError("chain request must be non-empty")
    host = manifest.get("host")
    if host not in CHAIN_HOSTS:
        raise EZPowersError("chain run host must be claude or codex")

    raw_stages = manifest.get("stage_selection")
    if not isinstance(raw_stages, dict) or set(raw_stages) != CHAIN_OPTIONAL_STAGES:
        raise EZPowersError(
            "chain stage_selection must contain all three optional stages"
        )
    stages: dict[str, Any] = {}
    for stage in sorted(CHAIN_OPTIONAL_STAGES):
        raw = raw_stages[stage]
        if (
            not isinstance(raw, dict)
            or not isinstance(raw.get("selected"), bool)
            or not isinstance(raw.get("reason"), str)
            or not raw["reason"].strip()
        ):
            raise EZPowersError(
                f"chain stage_selection.{stage} requires selected and reason"
            )
        stages[stage] = {
            "selected": raw["selected"],
            "reason": raw["reason"].strip(),
        }

    raw_risks = manifest.get("risk_classes", [])
    if not isinstance(raw_risks, list) or any(
        item not in CHAIN_RISKS for item in raw_risks
    ):
        raise EZPowersError(
            "chain risk_classes contains an unsupported risk classification"
        )
    risks = sorted(set(str(item) for item in raw_risks))

    raw_files = manifest.get("files")
    if not isinstance(raw_files, list) or not raw_files:
        raise EZPowersError("chain run files must be a non-empty array")
    files: list[dict[str, Any]] = []
    seen_targets: set[str] = set()
    role_counts: dict[str, int] = {
        "spec": 0,
        "plan": 0,
        "oracle": 0,
        "architecture": 0,
        "frontend-design": 0,
        "design-system": 0,
    }
    for index, raw in enumerate(raw_files):
        if not isinstance(raw, dict):
            raise EZPowersError(f"chain run files[{index}] must be an object")
        role = raw.get("role")
        if role not in role_counts:
            raise EZPowersError(f"unsupported chain file role: {role!r}")
        source_name = pathlib.PurePosixPath(
            str(raw.get("source", "")).replace("\\", "/")
        ).as_posix()
        target_name = pathlib.PurePosixPath(
            str(raw.get("target", "")).replace("\\", "/")
        ).as_posix()
        source = _safe_target(bundle, source_name, "chain staged source")
        target = _safe_target(root, target_name, "chain target")
        if not source.is_file():
            raise EZPowersError(f"chain staged source is missing: {source_name}")
        if target_name in seen_targets:
            raise EZPowersError(f"duplicate chain target: {target_name}")
        seen_targets.add(target_name)
        if role == "spec" and not (
            target_name.startswith("docs/specs/") and target_name.endswith(".md")
        ):
            raise EZPowersError("chain spec target must be under docs/specs/")
        if role == "plan" and not (
            target_name.startswith("docs/plans/") and target_name.endswith(".md")
        ):
            raise EZPowersError("chain plan target must be under docs/plans/")
        if role == "architecture":
            _safe_document_path(root, target_name, "chain architecture target")
            if pathlib.PurePosixPath(target_name).name == "DESIGN.md":
                raise EZPowersError(
                    "chain architecture target cannot be a DESIGN.md file"
                )
        if role == "frontend-design":
            _safe_document_path(root, target_name, "chain frontend-design target")
            if pathlib.PurePosixPath(target_name).name == "DESIGN.md":
                raise EZPowersError(
                    "chain frontend-design target must be the broader UX artifact"
                )
        if role == "design-system":
            _safe_document_path(root, target_name, "chain design-system target")
            if pathlib.PurePosixPath(target_name).name != "DESIGN.md":
                raise EZPowersError("chain design-system target must end in DESIGN.md")
        if role == "oracle" and (
            target_name.startswith(".ezpowers/")
            or target_name.startswith(".git/")
        ):
            raise EZPowersError(
                "chain oracle target cannot be runtime or Git metadata"
            )
        data = source.read_bytes()
        try:
            data.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise EZPowersError(
                f"chain staged file must be UTF-8 text: {source_name}"
            ) from exc
        role_counts[str(role)] += 1
        files.append(
            {
                "role": role,
                "source": source_name,
                "source_path": source,
                "target": target_name,
                "target_path": target,
                "data": data,
                "sha256": _sha256_bytes(data),
            }
        )
    if role_counts["spec"] != 1 or role_counts["plan"] != 1:
        raise EZPowersError("chain run requires exactly one spec and one plan")
    if role_counts["oracle"] < 1:
        raise EZPowersError("chain run requires at least one acceptance oracle file")
    architecture_selected = stages["design_architecture"]["selected"] is True
    if architecture_selected and role_counts["architecture"] < 1:
        raise EZPowersError(
            "selected design_architecture stage requires at least one "
            "architecture file"
        )
    if not architecture_selected and role_counts["architecture"]:
        raise EZPowersError(
            "chain architecture files require design_architecture to be selected"
        )

    spec_entry = next(item for item in files if item["role"] == "spec")
    plan_entry = next(item for item in files if item["role"] == "plan")
    flow = _validate_chain_staged_flow(
        root,
        spec_path=spec_entry["source_path"],
        spec_target=spec_entry["target"],
        plan_path=plan_entry["source_path"],
    )
    if flow["project_profile"] != configured_profile.name:
        raise EZPowersError(
            "staged chain flow profile differs from project configuration"
        )
    design_context = flow["spec"].get("design_context")
    design_entries = [item for item in files if item["role"] == "design-system"]
    frontend_entries = [item for item in files if item["role"] == "frontend-design"]
    if isinstance(design_context, dict) and design_context.get("required") is True:
        if len(frontend_entries) != 1 or not design_entries:
            raise EZPowersError(
                "UI chain run requires exactly one frontend-design file and at "
                "least one design-system file"
            )
        expected_frontend = design_context.get("frontend_artifact")
        expected_systems = design_context.get("systems")
        if frontend_entries[0]["target"] != expected_frontend:
            raise EZPowersError(
                "chain frontend-design target must match spec.design_context.frontend_artifact"
            )
        actual_systems = {item["target"] for item in design_entries}
        if not isinstance(expected_systems, list) or actual_systems != set(expected_systems):
            raise EZPowersError(
                "chain design-system targets must exactly match spec.design_context.systems"
            )
        frontend_value = _extract_block(
            frontend_entries[0]["source_path"],
            "frontend-design",
        )
        raw_design_systems = frontend_value.get("design_systems")
        if (
            frontend_value.get("schema_version") != SCHEMA_VERSION
            or not isinstance(raw_design_systems, list)
            or not raw_design_systems
        ):
            raise EZPowersError(
                "staged frontend-design managed block must contain design_systems"
            )
        mapped_paths: set[str] = set()
        entry_by_target = {item["target"]: item for item in design_entries}
        mapped_roots: list[tuple[str, int]] = []
        claimed_roots: set[str] = set()
        mapped_implementations: list[tuple[str, int, str]] = []
        for index, raw_system in enumerate(raw_design_systems):
            if not isinstance(raw_system, dict):
                raise EZPowersError(
                    f"frontend-design design_systems[{index}] must be an object"
                )
            design_path = raw_system.get("path")
            profile = raw_system.get("profile")
            roots = raw_system.get("frontend_roots")
            implementation_paths = raw_system.get("implementation_paths")
            if not isinstance(design_path, str) or design_path not in entry_by_target:
                raise EZPowersError(
                    "frontend-design mapping must name every staged design-system target"
                )
            if design_path in mapped_paths:
                raise EZPowersError(
                    f"duplicate frontend-design design system mapping: {design_path}"
                )
            mapped_paths.add(design_path)
            if not isinstance(profile, str) or not ID_RE.fullmatch(profile):
                raise EZPowersError(
                    f"frontend-design design_systems[{index}].profile is invalid"
                )
            if (
                not isinstance(roots, list)
                or not roots
                or any(not isinstance(item, str) for item in roots)
            ):
                raise EZPowersError(
                    f"frontend-design design_systems[{index}].frontend_roots is invalid"
                )
            if (
                not isinstance(implementation_paths, list)
                or not implementation_paths
                or any(not isinstance(item, str) for item in implementation_paths)
            ):
                raise EZPowersError(
                    f"frontend-design design_systems[{index}].implementation_paths is invalid"
                )
            normalized_roots: list[str] = []
            design_parent = pathlib.PurePosixPath(design_path).parent.as_posix()
            design_parent_parts = (
                ()
                if design_parent == "."
                else pathlib.PurePosixPath(design_parent).parts
            )
            for root_name in roots:
                root_path = _contained_path(
                    root,
                    root_name,
                    label="frontend design root",
                    must_exist=True,
                    directory=True,
                )
                root_relative = _relative(root, root_path)
                root_parts = (
                    ()
                    if root_relative == "."
                    else pathlib.PurePosixPath(root_relative).parts
                )
                if root_relative in claimed_roots:
                    raise EZPowersError(
                        f"frontend root is assigned more than once: {root_relative}"
                    )
                if root_parts[: len(design_parent_parts)] != design_parent_parts:
                    raise EZPowersError(
                        f"{design_path} must be at or above frontend root {root_relative}"
                    )
                claimed_roots.add(root_relative)
                normalized_roots.append(root_relative)
                mapped_roots.append((root_relative, index))
            for implementation in implementation_paths:
                implementation_path = _contained_path(
                    root,
                    implementation,
                    label="frontend implementation path",
                    must_exist=True,
                )
                implementation_relative = _relative(root, implementation_path)
                implementation_parts = pathlib.PurePosixPath(
                    implementation_relative
                ).parts
                implementation_is_mapped = False
                for root_name in normalized_roots:
                    root_parts = (
                        ()
                        if root_name == "."
                        else pathlib.PurePosixPath(root_name).parts
                    )
                    if implementation_parts[: len(root_parts)] == root_parts:
                        implementation_is_mapped = True
                        break
                if not implementation_is_mapped:
                    raise EZPowersError(
                        f"{implementation_relative} is outside the frontend roots for {design_path}"
                    )
                mapped_implementations.append(
                    (implementation_relative, index, design_path)
                )
            _validate_design_document(
                root,
                entry_by_target[design_path]["source_path"],
                profile,
                label=design_path,
            )
        if mapped_paths != actual_systems:
            raise EZPowersError(
                "frontend-design mappings must exactly match staged design-system targets"
            )
        for implementation, owner, design_path in mapped_implementations:
            implementation_parts = pathlib.PurePosixPath(implementation).parts
            candidates: list[tuple[str, int, int]] = []
            for root_name, candidate_owner in mapped_roots:
                root_parts = (
                    ()
                    if root_name == "."
                    else pathlib.PurePosixPath(root_name).parts
                )
                if implementation_parts[: len(root_parts)] == root_parts:
                    candidates.append((root_name, candidate_owner, len(root_parts)))
            if not candidates:
                raise EZPowersError(
                    f"no DESIGN.md mapping applies to {implementation}"
                )
            nearest_depth = max(item[2] for item in candidates)
            nearest = [item for item in candidates if item[2] == nearest_depth]
            if len(nearest) != 1 or nearest[0][1] != owner:
                selected = (
                    raw_design_systems[nearest[0][1]].get("path")
                    if len(nearest) == 1
                    and isinstance(raw_design_systems[nearest[0][1]], dict)
                    else "ambiguous mapping"
                )
                raise EZPowersError(
                    f"{implementation} is claimed by {design_path} but nearest "
                    f"mapping is {selected}"
                )
    elif design_entries or frontend_entries:
        raise EZPowersError(
            "chain design files require spec.design_context.required to be true"
        )
    oracle_targets = {
        item["target"] for item in files if item["role"] == "oracle"
    }
    raw_oracles = manifest.get("oracles")
    if not isinstance(raw_oracles, list) or not raw_oracles:
        raise EZPowersError("chain oracles must be a non-empty array")
    oracles: list[dict[str, Any]] = []
    oracle_ids: set[str] = set()
    covered_criteria: dict[str, int] = {
        criterion_id: 0 for criterion_id in flow["criteria"]
    }
    referenced_artifacts: set[str] = set()
    for index, raw in enumerate(raw_oracles):
        if not isinstance(raw, dict):
            raise EZPowersError(f"chain oracles[{index}] must be an object")
        oracle_id = raw.get("id")
        if (
            not isinstance(oracle_id, str)
            or not ID_RE.fullmatch(oracle_id)
            or oracle_id in oracle_ids
        ):
            raise EZPowersError(f"invalid or duplicate oracle id: {oracle_id!r}")
        oracle_ids.add(oracle_id)
        criteria = raw.get("criteria")
        checks = raw.get("checks")
        artifacts = raw.get("artifact_paths")
        if not isinstance(criteria, list) or not criteria or any(
            item not in flow["criteria"] for item in criteria
        ):
            raise EZPowersError(
                f"oracle {oracle_id} criteria must reference known criteria"
            )
        if not isinstance(checks, list) or not checks or any(
            not isinstance(item, str) for item in checks
        ):
            raise EZPowersError(
                f"oracle {oracle_id} checks must be a non-empty string array"
            )
        known_checks = set(flow["top_checks"]) | set(flow["project_checks"])
        if any(item not in known_checks for item in checks):
            raise EZPowersError(f"oracle {oracle_id} references an unknown check")
        for criterion_id in criteria:
            planned = set(flow["criterion_checks"][criterion_id])
            if not set(checks).issubset(planned):
                raise EZPowersError(
                    f"oracle {oracle_id} uses a check that is not mapped to "
                    f"criterion {criterion_id}"
                )
            covered_criteria[criterion_id] += 1
        if not isinstance(artifacts, list) or not artifacts or any(
            item not in oracle_targets for item in artifacts
        ):
            raise EZPowersError(
                f"oracle {oracle_id} artifact_paths must reference staged oracle files"
            )
        referenced_artifacts.update(str(item) for item in artifacts)
        boundary = raw.get("boundary")
        if (
            not isinstance(boundary, str)
            or not boundary.strip()
            or boundary.strip().lower()
            in CHAIN_NON_OBSERVABLE_BOUNDARIES
        ):
            boundary_kind = (
                "project-check or artifact-inspection"
                if configured_profile.name == "planning"
                else "runtime"
            )
            raise EZPowersError(
                f"oracle {oracle_id} must name an observable {boundary_kind} boundary"
            )
        baseline = raw.get("baseline")
        if baseline not in {"fail", "pass"}:
            raise EZPowersError(f"oracle {oracle_id} baseline must be fail or pass")
        for field in ("positive_case", "negative_case"):
            if not isinstance(raw.get(field), str) or not raw[field].strip():
                raise EZPowersError(f"oracle {oracle_id} requires {field}")
        oracles.append(
            {
                "id": oracle_id,
                "criteria": list(criteria),
                "checks": list(checks),
                "boundary": boundary.strip(),
                "artifact_paths": list(artifacts),
                "baseline": baseline,
                "positive_case": raw["positive_case"].strip(),
                "negative_case": raw["negative_case"].strip(),
            }
        )
    for criterion_id, count in covered_criteria.items():
        if count != 1:
            raise EZPowersError(
                f"criterion must have exactly one acceptance oracle: {criterion_id}"
            )
    if referenced_artifacts != oracle_targets:
        missing = sorted(oracle_targets - referenced_artifacts)
        raise EZPowersError(
            "every staged oracle file must be frozen by an oracle: "
            + ", ".join(missing)
        )

    chain, chain_sha256 = _load_chain_value(root)
    if host not in chain["hosts"]:
        raise EZPowersError(f"host {host} is not enabled by the project chain")
    for stage, mode in chain["optional_stages"].items():
        if mode == "always" and stages[stage]["selected"] is not True:
            raise EZPowersError(
                f"project chain requires optional stage {stage} for every run"
            )
    qa_triggers = [
        trigger
        for trigger in chain["additional_qa_triggers"]
        if trigger.casefold() in request.casefold()
    ]
    requires_qa = bool(set(risks) & CHAIN_QA_RISKS or qa_triggers)
    config_status, _ = _chain_config_status_payload(root)
    host_ready = config_status.get("hosts", {}).get(host, {})
    if not (
        isinstance(host_ready, dict)
        and host_ready.get("hooks_installed") is True
        and host_ready.get("handshake") is True
        and host_ready.get("unattended") is True
    ):
        raise EZPowersError(
            f"{host} hooks are not trusted and ready for an unattended chain run"
        )

    raw_overrides = manifest.get("limit_overrides", {})
    if not isinstance(raw_overrides, dict):
        raise EZPowersError("chain limit_overrides must be an object")
    unknown_overrides = set(raw_overrides) - set(chain["limits"])
    if unknown_overrides:
        raise EZPowersError(
            "chain limit_overrides contains unknown limits: "
            + ", ".join(sorted(unknown_overrides))
        )
    effective_limits = dict(chain["limits"])
    for name, raw in raw_overrides.items():
        if (
            not isinstance(raw, int)
            or isinstance(raw, bool)
            or raw < 1
            or raw > chain["limits"][name]
        ):
            raise EZPowersError(
                f"feature limit {name} must be from 1 through the project limit"
            )
        effective_limits[name] = raw

    return bundle, {
        "schema_version": configured_profile.chain_bundle_schema_version,
        "project_profile": configured_profile.name,
        "profile_policy": configured_profile,
        "run_id": run_id,
        "request": request.strip(),
        "host": host,
        "stage_selection": stages,
        "risk_classes": risks,
        "files": files,
        "oracles": oracles,
        "flow": flow,
        "chain": chain,
        "chain_sha256": chain_sha256,
        "limits": effective_limits,
        "qa_triggers": qa_triggers,
        "requires_qa": requires_qa,
    }


def _chain_overlay_ignore(root: pathlib.Path):
    root_resolved = root.resolve()

    def ignore(directory: str, names: list[str]) -> set[str]:
        path = pathlib.Path(directory).resolve()
        try:
            relative = path.relative_to(root_resolved).as_posix()
        except ValueError:
            return set()
        if relative == ".":
            return {".git"} & set(names)
        if relative == ".ezpowers":
            return {
                "evidence",
                "staging",
                "backups",
                "wiki",
                "runtime.lock",
                "state.json",
            } & set(names)
        return set()

    return ignore


def _chain_baseline(
    root: pathlib.Path,
    normalized: dict[str, Any],
) -> dict[str, Any]:
    checks_by_id = {
        **normalized["flow"]["project_checks"],
        **normalized["flow"]["top_checks"],
    }
    ordered_ids: list[str] = []
    for oracle in normalized["oracles"]:
        for check_id in oracle["checks"]:
            if check_id not in ordered_ids:
                ordered_ids.append(check_id)
    with tempfile.TemporaryDirectory(prefix="ezpowers-chain-baseline-") as temp_name:
        overlay = pathlib.Path(temp_name) / "project"
        shutil.copytree(
            root,
            overlay,
            copy_function=shutil.copy2,
            ignore=_chain_overlay_ignore(root),
        )
        for entry in normalized["files"]:
            target = _safe_target(overlay, entry["target"], "baseline target")
            _atomic_write(target, entry["data"])
        run_dir = overlay / ".ezpowers" / "baseline-evidence"
        run_dir.mkdir(parents=True, exist_ok=False)
        graph_bound = normalized["flow"]["plan_schema_version"] >= 2
        parallel_enabled = (
            graph_bound
            and normalized["flow"]["config_schema_version"] >= 2
            and normalized["flow"]["max_parallel_checks"] > 1
        )
        invocations = [
            {
                "node_id": f"check:baseline:{index}:{check_id}",
                "task_id": "baseline",
                "check": checks_by_id[check_id],
            }
            for index, check_id in enumerate(ordered_ids, 1)
        ]
        results, _ = _execute_invocations(
            overlay,
            run_dir,
            invocations,
            max_workers=(
                normalized["flow"]["max_parallel_checks"]
                if parallel_enabled
                else 1
            ),
            parallel_enabled=parallel_enabled,
            phase="baseline",
            task_wave=None,
            include_graph_fields=graph_bound,
        )
    by_id = {str(result["id"]): result for result in results}
    summary = [
        {
            "id": result["id"],
            "status": result["status"],
            "exit_code": result["exit_code"],
            "timed_out": result["timed_out"],
            "spawn_error": bool(result["spawn_error"]),
        }
        for result in results
    ]
    status = "PASS" if all(item["status"] == "PASS" for item in results) else "FAIL"
    oracle_summaries: list[dict[str, Any]] = []
    for oracle in normalized["oracles"]:
        oracle_status = (
            "PASS"
            if all(by_id[check_id]["status"] == "PASS" for check_id in oracle["checks"])
            else "FAIL"
        )
        expected_status = str(oracle["baseline"]).upper()
        if oracle_status != expected_status:
            raise EZPowersError(
                f"acceptance oracle {oracle['id']} baseline expected "
                f"{expected_status} but observed {oracle_status}"
            )
        oracle_summaries.append(
            {
                "id": oracle["id"],
                "status": oracle_status,
                "expected": expected_status,
                "checks": list(oracle["checks"]),
            }
        )
    expected_values = {item["expected"] for item in oracle_summaries}
    return {
        "status": status,
        "expected": (
            next(iter(expected_values))
            if len(expected_values) == 1
            else "MIXED"
        ),
        "checks": summary,
        "oracles": oracle_summaries,
    }


def _chain_receipt_key(kind: str, subject_sha256: str) -> str:
    return f"{kind}:{subject_sha256}"


def _chain_load_receipt(
    root: pathlib.Path,
    state: dict[str, Any],
    *,
    kind: str,
    subject_sha256: str,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    pointer = state.get("chain_gates", {}).get("receipts", {}).get(
        _chain_receipt_key(kind, subject_sha256)
    )
    if not isinstance(pointer, dict) or not isinstance(pointer.get("path"), str):
        return None, None
    try:
        path = _contained_path(
            root,
            pointer["path"],
            label="chain gate receipt",
            must_exist=True,
        )
        path.resolve().relative_to((root / CHAIN_EVIDENCE_RELATIVE_PATH).resolve())
    except (EZPowersError, ValueError):
        return None, None
    evidence_root = (root / CHAIN_EVIDENCE_RELATIVE_PATH).resolve()
    if (
        not path.is_file()
        or path.name != "receipt.json"
        or path.parent.parent.resolve() != evidence_root
    ):
        return None, None
    actual = _sha256_file(path)
    if actual != pointer.get("sha256"):
        return None, None
    sidecar = path.with_name("receipt.json.sha256")
    if (
        not sidecar.is_file()
        or sidecar.read_text(encoding="ascii", errors="replace").strip() != actual
    ):
        return None, None
    try:
        receipt = _read_json(path)
    except EZPowersError:
        return None, None
    if (
        receipt.get("kind") != kind
        or receipt.get("subject_sha256") != subject_sha256
        or receipt.get("challenge_id") != path.parent.name
        or pointer.get("kind") != kind
        or pointer.get("subject_sha256") != subject_sha256
        or pointer.get("verdict") != receipt.get("verdict")
    ):
        return None, None
    return receipt, pointer


def _chain_run_preview(
    root: pathlib.Path,
    bundle_argument: str,
) -> tuple[dict[str, Any], pathlib.Path, dict[str, Any]]:
    bundle, normalized = _load_chain_run_bundle(root, bundle_argument)
    baseline = _chain_baseline(root, normalized)
    target_states: list[dict[str, Any]] = []
    actions: list[dict[str, Any]] = []
    for entry in normalized["files"]:
        target = entry["target_path"]
        current_sha = _sha256_file(target) if target.is_file() else None
        if current_sha is None:
            action = "create"
        elif current_sha == entry["sha256"]:
            action = "unchanged"
        else:
            action = "replace"
        target_states.append({"path": entry["target"], "sha256": current_sha})
        actions.append({"path": entry["target"], "action": action})
    config_path = root / CONFIG_RELATIVE_PATH
    token_payload = {
        "schema_version": normalized["schema_version"],
        "run_id": normalized["run_id"],
        "request": normalized["request"],
        "host": normalized["host"],
        "stage_selection": normalized["stage_selection"],
        "risk_classes": normalized["risk_classes"],
        "requires_qa": normalized["requires_qa"],
        "qa_triggers": normalized["qa_triggers"],
        "files": [
            {
                key: value
                for key, value in entry.items()
                if key
                in {
                    "role",
                    "source",
                    "target",
                    "sha256",
                }
            }
            for entry in normalized["files"]
        ],
        "oracles": normalized["oracles"],
        "limits": normalized["limits"],
        "chain_sha256": normalized["chain_sha256"],
        "config_sha256": _sha256_file(config_path),
        "required_checks": [
            normalized["flow"]["project_checks"][check_id]
            for check_id in normalized["flow"]["required_checks"]
        ],
        "assurance_graph": normalized["flow"]["assurance_graph"],
        "assurance_graph_sha256": normalized["flow"]["assurance_graph_sha256"],
        "baseline": baseline,
        "targets": target_states,
        "installation": _installed_identity(root),
    }
    if normalized["project_profile"] == "planning":
        token_payload["project_profile"] = normalized["project_profile"]
        token_payload["inputs"] = normalized["flow"]["inputs"]
        token_payload["deliverables"] = normalized["flow"]["deliverables"]
    preview_sha256 = _sha256_bytes(_json_bytes(token_payload))
    state = _load_state(root)
    audit, audit_pointer = _chain_load_receipt(
        root,
        state,
        kind="oracle-audit",
        subject_sha256=preview_sha256,
    )
    audited = (
        isinstance(audit, dict)
        and audit.get("verdict") == "PASS"
        and audit.get("blocking_findings") == []
    )
    status = "READY" if audited else "REVIEW_REQUIRED"
    payload = {
        "status": status,
        "preview_sha256": preview_sha256,
        "run_id": normalized["run_id"],
        "host": normalized["host"],
        "actions": actions,
        "stage_selection": normalized["stage_selection"],
        "risk_classes": normalized["risk_classes"],
        "requires_qa": normalized["requires_qa"],
        "qa_triggers": normalized["qa_triggers"],
        "limits": normalized["limits"],
        "oracles": normalized["oracles"],
        "baseline": baseline,
        "assurance_graph_sha256": normalized["flow"]["assurance_graph_sha256"],
        "oracle_audit": audit_pointer if audited else None,
    }
    if normalized["project_profile"] == "planning":
        payload["project_profile"] = normalized["project_profile"]
        payload["inputs"] = normalized["flow"]["inputs"]
        payload["deliverables"] = normalized["flow"]["deliverables"]
    normalized["preview_sha256"] = preview_sha256
    normalized["baseline"] = baseline
    normalized["oracle_audit"] = audit_pointer
    return payload, bundle, normalized


def _chain_run_preview_command(args: argparse.Namespace) -> int:
    root = _runtime_project_root()
    payload, _, _ = _chain_run_preview(root, args.bundle)
    _emit(payload, args.json)
    return 0 if payload["status"] == "READY" else 4


def _chain_goal_objective(
    run_id: str,
    approval_path: str,
    approval_sha256: str,
    plan_path: str,
    project_profile: str = "software",
) -> str:
    action = "Produce the declared planning deliverables from" if project_profile == "planning" else "Implement"
    return (
        f"Complete EZPowers harness-chain run {run_id}. Treat "
        f"{approval_path} ({approval_sha256}) as frozen. {action} "
        f"{plan_path} without weakening its acceptance oracle. Continue until "
        "python .ezpowers/ezpowers.py chain run status --json reports "
        "CERTIFIED, or stop only for the runtime's terminal "
        "NEEDS_REAPPROVAL, BLOCKED, or FAILED verdict."
    )


def _chain_run_apply_command(args: argparse.Namespace) -> int:
    root = _runtime_project_root()
    with _runtime_lock(root):
        payload, bundle, normalized = _chain_run_preview(root, args.bundle)
        if args.preview_sha256 != payload["preview_sha256"]:
            raise InstallConflict(
                "conflict: chain run preview is stale or belongs to another bundle"
            )
        if payload["status"] != "READY":
            raise EZPowersError(
                "chain run requires a fresh independent oracle-audit PASS "
                "before approval"
            )
        existing_state = _load_state(root)
        existing_run = existing_state.get("chain_run")
        if (
            isinstance(existing_run, dict)
            and existing_run.get("status") not in CHAIN_TERMINAL_STATUSES
        ):
            raise InstallConflict(
                "conflict: another harness-chain feature is still active; "
                "finish its terminal verdict before applying a new run"
            )
        replacements = [
            item["path"]
            for item in payload["actions"]
            if item["action"] == "replace"
        ]
        if replacements and not args.force:
            raise InstallConflict(
                "conflict: chain run apply preserved existing files; rerun "
                "the preview and explicitly force backed replacement:\n- "
                + "\n- ".join(replacements)
            )

        approval_path = root / CHAIN_APPROVALS_RELATIVE_PATH / (
            normalized["run_id"] + ".json"
        )
        if approval_path.exists():
            raise InstallConflict(
                f"conflict: chain approval already exists: "
                f"{_relative(root, approval_path)}"
            )
        originals: dict[pathlib.Path, bytes | None] = {
            entry["target_path"]: (
                entry["target_path"].read_bytes()
                if entry["target_path"].is_file()
                else None
            )
            for entry in normalized["files"]
        }
        timestamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        backup_root = (
            root
            / ".ezpowers"
            / "backups"
            / "chain"
            / f"{timestamp}-{uuid.uuid4().hex[:8]}"
        )
        try:
            for entry in normalized["files"]:
                target = entry["target_path"]
                if (
                    args.force
                    and target.is_file()
                    and _sha256_file(target) != entry["sha256"]
                ):
                    backup = _safe_target(
                        backup_root,
                        entry["target"],
                        "chain backup target",
                    )
                    _atomic_write(backup, target.read_bytes())
                _atomic_write(target, entry["data"])

            config_path = root / CONFIG_RELATIVE_PATH
            spec_entry = next(
                item for item in normalized["files"] if item["role"] == "spec"
            )
            plan_entry = next(
                item for item in normalized["files"] if item["role"] == "plan"
            )
            required_checks = [
                normalized["flow"]["project_checks"][check_id]
                for check_id in normalized["flow"]["required_checks"]
            ]
            applied_flow = _validate_flow(root, plan_entry["target"])
            if applied_flow.errors:
                raise EZPowersError(
                    "applied chain flow differs from staged validation:\n- "
                    + "\n- ".join(applied_flow.errors)
                )
            if (
                applied_flow.assurance_graph_sha256
                != normalized["flow"]["assurance_graph_sha256"]
            ):
                raise EZPowersError(
                    "applied chain assurance graph differs from the approved preview"
                )
            approval = {
                "schema_version": normalized["profile_policy"].chain_approval_schema_version,
                "run_id": normalized["run_id"],
                "request": normalized["request"],
                "host": normalized["host"],
                "preview_sha256": normalized["preview_sha256"],
                "approved_at": _utc_now(),
                "chain_sha256": normalized["chain_sha256"],
                "config_sha256": _sha256_file(config_path),
                "spec_path": spec_entry["target"],
                "plan_path": plan_entry["target"],
                "stage_selection": normalized["stage_selection"],
                "risk_classes": normalized["risk_classes"],
                "qa_triggers": normalized["qa_triggers"],
                "requires_qa": normalized["requires_qa"],
                "limits": normalized["limits"],
                "files": [
                    {
                        "role": entry["role"],
                        "path": entry["target"],
                        "sha256": _sha256_file(entry["target_path"]),
                    }
                    for entry in normalized["files"]
                ],
                "oracles": normalized["oracles"],
                "required_checks": required_checks,
                "assurance_graph_sha256": applied_flow.assurance_graph_sha256,
                "baseline": normalized["baseline"],
                "oracle_audit": normalized["oracle_audit"],
            }
            if normalized["project_profile"] == "planning":
                approval["project_profile"] = normalized["project_profile"]
                approval["inputs"] = normalized["flow"]["inputs"]
                approval["deliverables"] = normalized["flow"]["deliverables"]
            _write_json(approval_path, approval)
            approval_sha256 = _sha256_file(approval_path)
            objective = _chain_goal_objective(
                normalized["run_id"],
                _relative(root, approval_path),
                approval_sha256,
                plan_entry["target"],
                normalized["project_profile"],
            )
            objective_sha256 = _sha256_bytes(objective.encode("utf-8"))

            state = _load_state(root)
            state["active_plan"] = plan_entry["target"]
            state["latest_evidence"] = {"all": None, "tasks": {}}
            state["latest_certificate"] = None
            state["chain_gates"]["pending"] = None
            state["chain_run"] = {
                "run_id": normalized["run_id"],
                "status": "PENDING_LOOP",
                "host": normalized["host"],
                "loop_authority": None,
                "approval_path": _relative(root, approval_path),
                "approval_sha256": approval_sha256,
                "plan_path": plan_entry["target"],
                "spec_path": spec_entry["target"],
                "project_profile": normalized["project_profile"],
                "goal_objective_sha256": objective_sha256,
                "limits": normalized["limits"],
                "risk_classes": normalized["risk_classes"],
                "requires_qa": normalized["requires_qa"],
                "qa_triggers": approval["qa_triggers"],
                "counters": {
                    "iterations": 0,
                    "qa_cycles": 0,
                    "validation_failures": 0,
                    "review_failures": 0,
                    "identical_error_repeats": 0,
                },
                "last_failure_signature": None,
                "gates": {
                    normalized["profile_policy"].primary_review_kind: None,
                    "adversarial-qa": None,
                    "blocker-review": None,
                },
                "latest_verification": None,
                "rework_required": None,
                "baseline_workspace": _workspace_snapshot(root),
                "started_at": _utc_now(),
                "terminal_reason": None,
            }
            _save_state(root, state)
        except Exception:
            for target, original in originals.items():
                if original is None:
                    with contextlib.suppress(FileNotFoundError):
                        target.unlink()
                else:
                    _atomic_write(target, original)
            with contextlib.suppress(FileNotFoundError):
                approval_path.unlink()
            raise
        with contextlib.suppress(OSError):
            shutil.rmtree(bundle)
        result = {
            "status": "PENDING_LOOP",
            "run_id": normalized["run_id"],
            "host": normalized["host"],
            "approval_path": _relative(root, approval_path),
            "approval_sha256": approval_sha256,
            "assurance_graph_sha256": applied_flow.assurance_graph_sha256,
            "plan_path": plan_entry["target"],
            "goal_objective": objective,
            "goal_objective_sha256": objective_sha256,
            "loop_authority": (
                "native-goal"
                if normalized["host"] == "codex"
                else "stop-hook"
            ),
            "backup_path": (
                _relative(root, backup_root) if backup_root.exists() else None
            ),
        }
        if normalized["project_profile"] == "planning":
            result["project_profile"] = normalized["project_profile"]
        _emit(result, args.json)
        return 0


def _chain_approval(
    root: pathlib.Path,
    state: dict[str, Any],
) -> tuple[dict[str, Any] | None, list[str]]:
    run = state.get("chain_run")
    if not isinstance(run, dict):
        return None, []
    approval_name = run.get("approval_path")
    if not isinstance(approval_name, str):
        return None, ["active chain run has no approval path"]
    try:
        path = _contained_path(
            root,
            approval_name,
            label="chain approval",
            must_exist=True,
        )
        path.resolve().relative_to(
            (root / CHAIN_APPROVALS_RELATIVE_PATH).resolve()
        )
    except (EZPowersError, ValueError) as exc:
        return None, [f"chain approval pointer is invalid: {exc}"]
    if not path.is_file() or path.suffix != ".json":
        return None, ["chain approval is not a canonical JSON file"]
    actual = _sha256_file(path)
    if actual != run.get("approval_sha256"):
        return None, ["chain approval hash changed"]
    try:
        approval = _read_json(path)
    except EZPowersError as exc:
        return None, [str(exc)]
    profile_name = run.get("project_profile", SOFTWARE_PROFILE.name)
    profile = PROJECT_PROFILE_POLICIES.get(str(profile_name))
    if profile is None:
        return None, ["chain run project profile is invalid"]
    allowed_schemas = (
        {SCHEMA_VERSION, GRAPH_BOUND_SCHEMA_VERSION}
        if profile.name == SOFTWARE_PROFILE.name
        else {profile.chain_approval_schema_version}
    )
    if (
        approval.get("schema_version") not in allowed_schemas
        or approval.get("run_id") != run.get("run_id")
    ):
        return None, ["chain approval identity is invalid"]
    if profile.name == PLANNING_PROFILE.name:
        if approval.get("project_profile") != profile.name:
            return None, ["planning chain approval profile is invalid"]
    elif "project_profile" in approval:
        return None, ["software chain approval contains a planning-only profile field"]
    return approval, []


def _chain_contract_reasons(
    root: pathlib.Path,
    state: dict[str, Any],
) -> tuple[dict[str, Any] | None, list[str]]:
    approval, reasons = _chain_approval(root, state)
    if approval is None:
        return None, reasons
    run = state.get("chain_run")
    if not isinstance(run, dict):
        return None, ["active chain run state is missing"]
    for approval_key, run_key in (
        ("run_id", "run_id"),
        ("host", "host"),
        ("plan_path", "plan_path"),
        ("spec_path", "spec_path"),
        ("limits", "limits"),
        ("risk_classes", "risk_classes"),
        ("requires_qa", "requires_qa"),
        ("qa_triggers", "qa_triggers"),
    ):
        if approval.get(approval_key) != run.get(run_key):
            reasons.append(
                f"chain run {run_key} differs from the frozen approval"
            )
    profile_name = str(run.get("project_profile", SOFTWARE_PROFILE.name))
    profile = PROJECT_PROFILE_POLICIES.get(profile_name)
    if profile is None:
        reasons.append("chain run project profile is invalid")
        profile = SOFTWARE_PROFILE
    if profile.name == PLANNING_PROFILE.name:
        if approval.get("project_profile") != profile.name:
            reasons.append("chain approval project profile changed")
    try:
        chain, chain_sha256 = _load_chain_value(root)
        if chain_sha256 != approval.get("chain_sha256"):
            reasons.append("project chain changed after feature approval")
        host = run.get("host")
        if host not in chain.get("hosts", []):
            reasons.append("approved host is no longer enabled by the chain")
        elif isinstance(host, str):
            installed = _chain_host_hook_present(root, host)
            record = state.get("chain_hosts", {}).get(host)
            expected = (
                _chain_hook_identity(root, host, chain_sha256)
                if installed
                else None
            )
            if (
                not installed
                or not isinstance(record, dict)
                or record.get("hook_identity") != expected
                or not isinstance(record.get("session_id"), str)
                or not record.get("session_id")
                or record.get("permission_mode")
                not in {"dontAsk", "bypassPermissions"}
            ):
                reasons.append(
                    f"{host} chain hook identity, session trust, or "
                    "unattended permission mode changed"
                )
    except EZPowersError as exc:
        reasons.append(str(exc))
    expected_authority = (
        "native-goal" if run.get("host") == "codex" else "stop-hook"
    )
    if (
        run.get("status") in {"RUNNING", "CERTIFIED"}
        and run.get("loop_authority") != expected_authority
    ):
        reasons.append("chain loop authority differs from the approved host")
    expected_objective = _chain_goal_objective(
        str(run.get("run_id")),
        str(run.get("approval_path")),
        str(run.get("approval_sha256")),
        str(run.get("plan_path")),
        profile.name,
    )
    if run.get("goal_objective_sha256") != _sha256_bytes(
        expected_objective.encode("utf-8")
    ):
        reasons.append("chain goal objective differs from the frozen approval")
    config_path = root / CONFIG_RELATIVE_PATH
    if (
        not config_path.is_file()
        or _sha256_file(config_path) != approval.get("config_sha256")
    ):
        reasons.append("project checks changed after feature approval")
    graph_hash = approval.get("assurance_graph_sha256")
    if not isinstance(graph_hash, str):
        if run.get("status") != "CERTIFIED":
            reasons.append(
                "chain approval predates assurance graph binding; explicit reapproval is required"
            )
    else:
        flow = _validate_flow(root, str(run.get("plan_path", "")))
        if flow.errors:
            reasons.extend(
                f"approved assurance flow is invalid: {error}"
                for error in flow.errors
            )
        elif flow.assurance_graph_sha256 != graph_hash:
            reasons.append("assurance graph changed after feature approval")
        elif flow.profile.name != profile.name:
            reasons.append("approved plan profile changed after feature approval")
        elif profile.name == PLANNING_PROFILE.name:
            if approval.get("inputs") != flow.inputs:
                reasons.append("frozen planning inputs changed after feature approval")
            if approval.get("deliverables") != flow.deliverables:
                reasons.append("planning deliverable contract changed after feature approval")
    raw_files = approval.get("files")
    if not isinstance(raw_files, list) or not raw_files:
        reasons.append("chain approval has no frozen files")
        raw_files = []
    for raw in raw_files:
        if (
            not isinstance(raw, dict)
            or not isinstance(raw.get("path"), str)
            or not isinstance(raw.get("sha256"), str)
        ):
            reasons.append("chain approval contains an invalid frozen file")
            continue
        try:
            path = _contained_path(
                root,
                raw["path"],
                label="frozen chain file",
                must_exist=True,
            )
        except EZPowersError as exc:
            reasons.append(str(exc))
            continue
        if not path.is_file() or _sha256_file(path) != raw["sha256"]:
            reasons.append(f"frozen acceptance file changed: {raw['path']}")
    return approval, reasons


def _chain_mark_reapproval(
    state: dict[str, Any],
    reasons: list[str],
) -> None:
    run = state.get("chain_run")
    if not isinstance(run, dict):
        return
    if (
        run.get("status") in CHAIN_TERMINAL_STATUSES
        and run.get("status") != "CERTIFIED"
    ):
        return
    run["status"] = "NEEDS_REAPPROVAL"
    run["terminal_reason"] = "; ".join(reasons) or "frozen approval changed"
    run["terminal_at"] = _utc_now()


def _chain_refresh_run_status(
    root: pathlib.Path,
    state: dict[str, Any],
) -> bool:
    run = state.get("chain_run")
    if not isinstance(run, dict):
        return False
    status = run.get("status")
    if status in CHAIN_TERMINAL_STATUSES and status != "CERTIFIED":
        return False
    _, reasons = _chain_contract_reasons(root, state)
    if not reasons and status == "CERTIFIED":
        core, _ = _status_payload(root)
        if core.get("status") != "CERTIFIED":
            reasons = [
                "certification is no longer fresh: "
                + (
                    "; ".join(core.get("reasons", []))
                    or str(core.get("status"))
                )
            ]
    if not reasons:
        return False
    _chain_mark_reapproval(state, reasons)
    return True


def _chain_next_action(state: dict[str, Any]) -> str:
    run = state.get("chain_run")
    if not isinstance(run, dict):
        return "Invoke harness-chain with a feature request."
    status = run.get("status")
    if status == "PENDING_LOOP":
        return "Activate the approved host-native loop authority."
    if status in CHAIN_TERMINAL_STATUSES:
        return str(run.get("terminal_reason") or status)
    latest_verification = run.get("latest_verification")
    if (
        not isinstance(latest_verification, dict)
        or latest_verification.get("status") != "PASS"
    ):
        return "Implement the approved plan, then run verify --all."
    gates = run.get("gates", {})
    profile = PROJECT_PROFILE_POLICIES.get(
        str(run.get("project_profile", SOFTWARE_PROFILE.name)),
        SOFTWARE_PROFILE,
    )
    if not isinstance(gates, dict) or not isinstance(
        gates.get(profile.primary_review_kind),
        dict,
    ):
        return (
            "Begin a fresh independent "
            f"{profile.primary_review_kind} gate."
        )
    if run.get("requires_qa") and not isinstance(
        gates.get("adversarial-qa"),
        dict,
    ):
        return "Begin a fresh adversarial-qa gate."
    return "Run certify for the fresh evidence and gate receipts."


def _chain_run_status_locked(root: pathlib.Path) -> tuple[dict[str, Any], int]:
    state = _load_state(root)
    run = state.get("chain_run")
    if not isinstance(run, dict):
        return {
            "status": "IDLE",
            "run_id": None,
            "reasons": ["no harness-chain run is active"],
        }, 0
    if _chain_refresh_run_status(root, state):
        _save_state(root, state)
        run = state["chain_run"]
    approval, _ = _chain_approval(root, state)
    payload = {
        "status": run.get("status"),
        "run_id": run.get("run_id"),
        "host": run.get("host"),
        "loop_authority": run.get("loop_authority"),
        "approval_path": run.get("approval_path"),
        "assurance_graph_sha256": (
            approval.get("assurance_graph_sha256")
            if isinstance(approval, dict)
            else None
        ),
        "plan_path": run.get("plan_path"),
        "counters": run.get("counters", {}),
        "gates": run.get("gates", {}),
        "terminal_reason": run.get("terminal_reason"),
        "next_action": _chain_next_action(state),
    }
    if run.get("project_profile") == PLANNING_PROFILE.name:
        payload["project_profile"] = PLANNING_PROFILE.name
    return payload, 0


def _chain_run_status_command(args: argparse.Namespace) -> int:
    root = _runtime_project_root()
    with _runtime_lock(root):
        payload, code = _chain_run_status_locked(root)
    _emit(payload, args.json)
    return code


def _chain_activate_command(args: argparse.Namespace) -> int:
    root = _runtime_project_root()
    with _runtime_lock(root):
        state = _load_state(root)
        run = state.get("chain_run")
        if not isinstance(run, dict):
            raise EZPowersError("no harness-chain run is awaiting activation")
        if run.get("status") != "PENDING_LOOP":
            raise EZPowersError(
                f"chain run is not awaiting activation: {run.get('status')}"
            )
        if args.host != run.get("host"):
            raise EZPowersError("chain activation host differs from the approval")
        expected_authority = (
            "native-goal" if args.host == "codex" else "stop-hook"
        )
        if args.authority != expected_authority:
            raise EZPowersError(
                f"{args.host} chain authority must be {expected_authority}"
            )
        if args.objective_sha256 != run.get("goal_objective_sha256"):
            raise EZPowersError("chain goal objective hash does not match the approval")
        config_status, _ = _chain_config_status_payload(root)
        host_status = config_status.get("hosts", {}).get(args.host, {})
        if not (
            isinstance(host_status, dict)
            and host_status.get("hooks_installed") is True
            and host_status.get("handshake") is True
            and host_status.get("unattended") is True
        ):
            raise EZPowersError(
                f"{args.host} chain hooks are not trusted and ready for "
                "unattended execution"
            )
        run["status"] = "RUNNING"
        run["loop_authority"] = expected_authority
        run["activated_at"] = _utc_now()
        _save_state(root, state)
        result = {
            "status": "RUNNING",
            "run_id": run.get("run_id"),
            "host": args.host,
            "loop_authority": expected_authority,
        }
    _emit(result, args.json)
    return 0


def _chain_fail_terminal(
    run: dict[str, Any],
    reason: str,
    *,
    status: str = "FAILED",
) -> None:
    if run.get("status") in CHAIN_TERMINAL_STATUSES:
        return
    run["status"] = status
    run["terminal_reason"] = reason
    run["terminal_at"] = _utc_now()


def _chain_failure_signature(category: str, value: Any) -> str:
    return _sha256_bytes(
        _json_bytes(
            {
                "category": category,
                "value": value,
            }
        )
    )


def _chain_record_failure(
    run: dict[str, Any],
    *,
    counter: str,
    category: str,
    value: Any,
) -> None:
    counters = run.get("counters")
    limits = run.get("limits")
    if not isinstance(counters, dict) or not isinstance(limits, dict):
        _chain_fail_terminal(run, "chain counters or limits are invalid")
        return
    counters[counter] = int(counters.get(counter, 0)) + 1
    signature = _chain_failure_signature(category, value)
    if run.get("last_failure_signature") == signature:
        counters["identical_error_repeats"] = (
            int(counters.get("identical_error_repeats", 0)) + 1
        )
    else:
        run["last_failure_signature"] = signature
        counters["identical_error_repeats"] = 1

    limit_name = {
        "validation_failures": "validation_retries",
        "review_failures": "review_retries",
    }.get(counter)
    if limit_name is not None and counters[counter] >= int(limits[limit_name]):
        _chain_fail_terminal(
            run,
            f"{counter.replace('_', ' ')} reached the approved "
            f"{limit_name.replace('_', ' ')} limit ({limits[limit_name]})",
        )
        return
    identical_limit = int(limits["identical_error_repeats"])
    if counters["identical_error_repeats"] >= identical_limit:
        _chain_fail_terminal(
            run,
            "the same failure reached the approved identical error repeat "
            f"limit ({identical_limit})",
        )


def _chain_clear_failure_repeat(run: dict[str, Any]) -> None:
    counters = run.get("counters")
    if isinstance(counters, dict):
        counters["identical_error_repeats"] = 0
    run["last_failure_signature"] = None


def _chain_require_product_rework(
    run: dict[str, Any],
    *,
    workspace: dict[str, Any],
    reason: str,
    failed_deliverables: dict[str, list[dict[str, str]]] | None = None,
) -> None:
    run["rework_required"] = {
        "reason": reason,
        "workspace": workspace,
        "required_at": _utc_now(),
    }
    if failed_deliverables is not None:
        run["rework_required"]["failed_deliverables"] = failed_deliverables
    latest = run.get("latest_verification")
    if isinstance(latest, dict) and latest.get("status") == "PASS":
        latest["status"] = "REWORK_REQUIRED"
        latest["invalidated_reason"] = reason
    gates = run.get("gates")
    if isinstance(gates, dict):
        profile = PROJECT_PROFILE_POLICIES.get(
            str(run.get("project_profile", SOFTWARE_PROFILE.name)),
            SOFTWARE_PROFILE,
        )
        gates[profile.primary_review_kind] = None
        gates["adversarial-qa"] = None


def _chain_rework_observed(
    root: pathlib.Path,
    run: dict[str, Any],
) -> tuple[bool, str | None]:
    required = run.get("rework_required")
    if not isinstance(required, dict):
        return True, None
    failed_deliverables = required.get("failed_deliverables")
    if isinstance(failed_deliverables, dict):
        plan_path = run.get("plan_path")
        if not isinstance(plan_path, str):
            return False, "planning rework state has no active plan"
        flow = _validate_flow(root, plan_path)
        if flow.errors or flow.profile.name != PLANNING_PROFILE.name:
            return False, "planning rework cannot validate the active deliverable contract"
        try:
            current_snapshot = _planning_artifact_snapshot(root, flow)
        except (EZPowersError, OSError) as exc:
            return False, f"planning rework artifacts are not ready: {exc}"
        current = _planning_failed_deliverable_hashes(
            current_snapshot,
            failed_deliverables,
        )
        unchanged = [
            deliverable_id
            for deliverable_id, before in failed_deliverables.items()
            if current.get(deliverable_id) == before
        ]
        if unchanged:
            return False, (
                "every failed logical deliverable must change bytes before "
                "another all-scope verification: " + ", ".join(sorted(unchanged))
            )
        return True, None
    previous = required.get("workspace")
    if (
        not isinstance(previous, dict)
        or not isinstance(previous.get("fingerprint"), str)
    ):
        return False, "chain rework state has no valid workspace fingerprint"
    current = _workspace_snapshot(root)
    if current.get("fingerprint") == previous.get("fingerprint"):
        return False, (
            "product rework is required before another all-scope "
            f"verification: {required.get('reason') or 'the previous gate failed'}"
        )
    return True, None


def _chain_flow_preflight(
    root: pathlib.Path,
    state: dict[str, Any],
    flow: Flow,
    *,
    operation: str,
) -> tuple[dict[str, Any] | None, list[str]]:
    run = state.get("chain_run")
    if not isinstance(run, dict):
        return None, []
    if flow.plan_rel != run.get("plan_path"):
        if run.get("status") not in CHAIN_TERMINAL_STATUSES:
            return None, [
                "another harness-chain plan is active; finish or explicitly "
                "replace that approved run before changing plans"
            ]
        return None, []
    status = run.get("status")
    if status in CHAIN_TERMINAL_STATUSES:
        return None, [
            f"harness-chain run is terminal ({status}); {operation} is rejected"
        ]
    if status != "RUNNING":
        return None, [
            "harness-chain run is not activated; activate its approved "
            "host-native loop before verification"
        ]
    approval, reasons = _chain_contract_reasons(root, state)
    if reasons:
        _chain_mark_reapproval(state, reasons)
        _save_state(root, state)
        return None, [
            "harness-chain reapproval is required: " + "; ".join(reasons)
        ]
    return approval, []


def _chain_gate_subject(
    root: pathlib.Path,
    state: dict[str, Any],
    *,
    kind: str,
    requested: str | None,
) -> tuple[str, dict[str, Any] | None]:
    if kind == "oracle-audit":
        if requested is None:
            raise EZPowersError(
                "oracle-audit requires --subject-sha256 from chain run preview"
            )
        return requested, None

    run = state.get("chain_run")
    if not isinstance(run, dict):
        raise EZPowersError(f"{kind} requires an active harness-chain run")
    if run.get("status") in CHAIN_TERMINAL_STATUSES:
        raise EZPowersError(
            f"harness-chain run is terminal ({run.get('status')})"
        )
    if run.get("status") != "RUNNING":
        raise EZPowersError("harness-chain run must be RUNNING before review")
    approval, contract_reasons = _chain_contract_reasons(root, state)
    if contract_reasons:
        _chain_mark_reapproval(state, contract_reasons)
        _save_state(root, state)
        raise EZPowersError(
            "harness-chain reapproval is required: "
            + "; ".join(contract_reasons)
        )
    if kind == "blocker-review":
        subject = str(run.get("approval_sha256", ""))
        if requested is not None and requested != subject:
            raise EZPowersError(
                "blocker-review subject must be the active approval hash"
            )
        return subject, approval

    latest = run.get("latest_verification")
    if (
        not isinstance(latest, dict)
        or latest.get("status") != "PASS"
        or isinstance(run.get("rework_required"), dict)
    ):
        raise EZPowersError(
            f"{kind} requires a new all-scope PASS after the latest "
            "implementation or rework"
        )

    plan_path = run.get("plan_path")
    if not isinstance(plan_path, str):
        raise EZPowersError("active chain run has no plan")
    flow = _validate_flow(root, plan_path)
    if flow.errors:
        raise EZPowersError(
            "active chain plan is invalid:\n- " + "\n- ".join(flow.errors)
        )
    fresh, reasons, _, evidence_hash, _ = _freshness(
        root,
        flow,
        state=state,
    )
    if not fresh:
        raise EZPowersError(
            f"{kind} requires fresh PASS evidence:\n- " + "\n- ".join(reasons)
        )
    if requested is not None and requested != evidence_hash:
        raise EZPowersError(
            f"{kind} subject does not match the latest fresh evidence"
        )
    if latest.get("sha256") != evidence_hash:
        raise EZPowersError(
            f"{kind} subject does not match the chain's latest PASS verification"
        )
    if kind == "adversarial-qa" and not run.get("requires_qa"):
        raise EZPowersError(
            "adversarial-qa is not required by this approved risk classification"
        )
    return evidence_hash, approval


def _chain_artifact_review_contract(
    root: pathlib.Path,
    state: dict[str, Any],
    run: dict[str, Any],
    subject_sha256: str,
) -> list[dict[str, Any]]:
    plan_path = run.get("plan_path")
    if not isinstance(plan_path, str):
        raise EZPowersError("artifact-review chain run has no plan")
    flow = _validate_flow(root, plan_path)
    if flow.errors or flow.profile.name != PLANNING_PROFILE.name:
        raise EZPowersError("artifact-review requires a valid planning plan")
    fresh, reasons, evidence, evidence_hash, _ = _freshness(
        root,
        flow,
        state=state,
    )
    if (
        not fresh
        or not isinstance(evidence, dict)
        or evidence_hash != subject_sha256
    ):
        raise EZPowersError(
            "artifact-review requires the latest fresh planning evidence: "
            + "; ".join(reasons)
        )
    artifact_entries = {
        str(entry.get("id")): entry
        for entry in evidence.get("artifacts", {}).get("deliverables", [])
        if isinstance(entry, dict)
    }
    check_results = list(_iter_check_results(evidence))
    contract: list[dict[str, Any]] = []
    for deliverable in flow.deliverables:
        deliverable_id = str(deliverable["id"])
        sources: list[dict[str, Any]] = []
        if deliverable["review"]["mode"] == "direct":
            artifact_entry = artifact_entries.get(deliverable_id, {})
            by_path = {
                str(item.get("path")): item
                for item in artifact_entry.get("paths", [])
                if isinstance(item, dict)
            }
            for path_name in deliverable["paths"]:
                artifact = by_path.get(str(path_name))
                if not isinstance(artifact, dict):
                    raise EZPowersError(
                        f"artifact-review evidence is missing {deliverable_id}: {path_name}"
                    )
                sources.append(
                    {
                        "id": f"artifact:{path_name}",
                        "kind": "artifact",
                        "path": path_name,
                        "sha256": artifact.get("sha256"),
                    }
                )
        else:
            for check_id in deliverable["review"]["checks"]:
                matched = [
                    result
                    for result in check_results
                    if result.get("id") == check_id
                    and result.get("status") == "PASS"
                ]
                if not matched:
                    raise EZPowersError(
                        f"artifact-review evidence has no PASS result for inspection check {check_id}"
                    )
                for result in matched:
                    node_id = result.get("node_id")
                    if not isinstance(node_id, str) or not node_id:
                        raise EZPowersError(
                            f"artifact-review inspection check {check_id} has no graph occurrence"
                        )
                    sources.append(
                        {
                            "id": f"inspection:{node_id}",
                            "kind": "inspection",
                            "check_id": check_id,
                            "node_id": node_id,
                            "stdout_log": result.get("stdout_log"),
                            "stdout_sha256": result.get("stdout_sha256"),
                            "stderr_log": result.get("stderr_log"),
                            "stderr_sha256": result.get("stderr_sha256"),
                        }
                    )
        contract.append(
            {
                "id": deliverable_id,
                "mode": deliverable["review"]["mode"],
                "paths": list(deliverable["paths"]),
                "sources": sources,
                "required_source_ids": [source["id"] for source in sources],
            }
        )
    return contract


def _chain_gate_begin_command(args: argparse.Namespace) -> int:
    root = _runtime_project_root()
    with _runtime_lock(root):
        if args.kind not in CHAIN_GATE_KINDS:
            raise EZPowersError(f"unsupported chain gate kind: {args.kind}")
        requested = args.subject_sha256
        if requested is not None and not re.fullmatch(r"[0-9a-f]{64}", requested):
            raise EZPowersError("--subject-sha256 must be 64 lowercase hex characters")
        state = _load_state(root)
        active_run = state.get("chain_run")
        if (
            args.kind in {"code-review", "artifact-review"}
            and isinstance(active_run, dict)
        ):
            profile = PROJECT_PROFILE_POLICIES.get(
                str(active_run.get("project_profile", SOFTWARE_PROFILE.name)),
                SOFTWARE_PROFILE,
            )
            if args.kind != profile.primary_review_kind:
                raise EZPowersError(
                    f"{profile.name} chain requires {profile.primary_review_kind}, "
                    f"not {args.kind}"
                )
        subject, approval = _chain_gate_subject(
            root,
            state,
            kind=args.kind,
            requested=requested,
        )
        if args.kind == "oracle-audit":
            receipt_key = _chain_receipt_key(args.kind, subject)
            consumed = state.get("chain_gates", {}).get("consumed", {})
            if (
                isinstance(consumed, dict)
                and isinstance(consumed.get(receipt_key), dict)
            ):
                raise EZPowersError(
                    "the independent oracle audit failed for this exact "
                    "preview; change the staged acceptance contract and use "
                    "its new preview hash before another audit"
                )
            prior_receipt, _ = _chain_load_receipt(
                root,
                state,
                kind=args.kind,
                subject_sha256=subject,
            )
            if isinstance(prior_receipt, dict):
                if prior_receipt.get("verdict") == "PASS":
                    raise EZPowersError(
                        "this preview already has an independent oracle-audit "
                        "PASS; rerun chain run preview"
                    )
                raise EZPowersError(
                    "the independent oracle audit failed for this exact "
                    "preview; change the staged acceptance contract and use "
                    "its new preview hash before another audit"
                )
        pending = state["chain_gates"].get("pending")
        if isinstance(pending, dict):
            if (
                pending.get("kind") == args.kind
                and pending.get("subject_sha256") == subject
                and isinstance(pending.get("challenge_id"), str)
            ):
                payload = {
                    "status": "PENDING_REVIEWER",
                    "challenge_id": pending["challenge_id"],
                    "kind": args.kind,
                    "subject_sha256": subject,
                    "bound_agent_id": pending.get("bound_agent_id"),
                }
                if args.kind == "artifact-review":
                    payload["deliverables"] = [
                        {
                            "id": item.get("id"),
                            "mode": item.get("mode"),
                            "review_sources": item.get("sources", []),
                        }
                        for item in pending.get("artifact_review", [])
                        if isinstance(item, dict)
                    ]
                _emit(payload, args.json)
                return 0
            raise EZPowersError(
                "another independent review challenge is already pending"
            )

        run = state.get("chain_run")
        if args.kind == "adversarial-qa" and isinstance(run, dict):
            counters = run.get("counters", {})
            limits = run.get("limits", {})
            if int(counters.get("qa_cycles", 0)) >= int(
                limits.get("qa_cycles", 0)
            ):
                _chain_fail_terminal(
                    run,
                    "adversarial QA reached the approved QA cycle limit "
                    f"({limits.get('qa_cycles')})",
                )
                _save_state(root, state)
                raise EZPowersError(str(run["terminal_reason"]))

        challenge_id = uuid.uuid4().hex
        pending_value: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "challenge_id": challenge_id,
            "kind": args.kind,
            "subject_sha256": subject,
            "approval_sha256": (
                None
                if args.kind == "oracle-audit"
                else str(run.get("approval_sha256"))
                if isinstance(run, dict)
                else (
                    approval.get("preview_sha256")
                    if isinstance(approval, dict)
                    else None
                )
            ),
            "host": None,
            "expected_host": (
                run.get("host")
                if (
                    isinstance(run, dict)
                    and args.kind != "oracle-audit"
                )
                else None
            ),
            "session_id": None,
            "bound_agent_id": None,
            "bound_agent_type": None,
            "created_at": _utc_now(),
        }
        if args.kind == "artifact-review":
            if not isinstance(run, dict):
                raise EZPowersError("artifact-review requires an active chain run")
            pending_value["schema_version"] = GRAPH_BOUND_SCHEMA_VERSION
            pending_value["artifact_review"] = _chain_artifact_review_contract(
                root,
                state,
                run,
                subject,
            )
        state["chain_gates"]["pending"] = pending_value
        _save_state(root, state)
        payload = {
            "status": "PENDING_REVIEWER",
            "challenge_id": challenge_id,
            "kind": args.kind,
            "subject_sha256": subject,
            "review_contract": (
                "Spawn one host-native independent subagent. The hook will bind "
                "that subagent and accept only its structured terminal receipt."
            ),
        }
        if args.kind == "artifact-review":
            payload["deliverables"] = [
                {
                    "id": item["id"],
                    "mode": item["mode"],
                    "review_sources": item["sources"],
                }
                for item in pending_value["artifact_review"]
            ]
    _emit(payload, args.json)
    return 0


def _chain_gate_rubric(pending: dict[str, Any]) -> str:
    kind = pending.get("kind")
    challenge_id = str(pending.get("challenge_id") or "")
    common = (
        "You are the bound independent reviewer. Inspect the real subject and "
        "repository evidence read-only; do not edit files. Do not accept "
        "test-name, string-presence, mocked-self-confirmation, or prose-only "
        "claims as proof. Do not leave new files or edits in the project "
        "worktree (logs, screenshots, scratch output); any workspace change "
        "invalidates your receipt at certification."
    )
    if kind == "artifact-review":
        artifact_contract = pending.get("artifact_review", [])
        template = {
            "schema_version": GRAPH_BOUND_SCHEMA_VERSION,
            "challenge_id": challenge_id,
            "deliverables": [
                {
                    "id": item.get("id"),
                    "verdict": "FAIL",
                    "blocking_findings": ["<the exact blocking defect>"],
                    "observations": ["<one concrete observation>"],
                    "reviewed_sources": list(item.get("required_source_ids", [])),
                }
                for item in artifact_contract
                if isinstance(item, dict)
            ],
        }
        receipt = (
            "Your terminal message must contain exactly one gate marker with "
            "one JSON block. The top-level object must contain exactly "
            "schema_version (2), challenge_id, and deliverables. Preserve the "
            "declared deliverable order. Each deliverable must contain exactly "
            "id, verdict (PASS or FAIL), blocking_findings, observations, and "
            "reviewed_sources. reviewed_sources must contain every required "
            "source ID for that deliverable and no others. PASS requires no "
            "blocking findings; FAIL requires at least one. Edit this template:\n"
            "<!-- ezpowers:gate:start -->\n```json\n"
            + json.dumps(template, ensure_ascii=False, indent=2)
            + "\n```\n<!-- ezpowers:gate:end -->\n\nReview-source contract:\n"
            + json.dumps(artifact_contract, ensure_ascii=False, indent=2)
        )
    else:
        receipt = (
            "Your terminal message must contain exactly one gate marker: the "
            "line <!-- ezpowers:gate:start -->, then one ```json fenced code "
            "block, then the line <!-- ezpowers:gate:end -->. The fenced JSON "
            "object must contain exactly the keys schema_version (always 1), "
            "challenge_id, verdict (PASS, FAIL, or BLOCKED), blocking_findings, "
            "and observations - no extra keys. Both arrays hold non-empty "
            "strings and observations must contain at least one entry. A PASS "
            "receipt must have an empty blocking_findings array; a FAIL or "
            "BLOCKED receipt must name at least one blocking finding. Edit the "
            "template below into your real result; an unedited copy stays "
            "FAIL:\n"
            "<!-- ezpowers:gate:start -->\n"
            "```json\n"
            "{\n"
            '  "schema_version": 1,\n'
            f'  "challenge_id": "{challenge_id}",\n'
            '  "verdict": "FAIL",\n'
            '  "blocking_findings": ["<the exact blocking defect>"],\n'
            '  "observations": ["<one concrete observation>"]\n'
            "}\n"
            "```\n"
            "<!-- ezpowers:gate:end -->"
        )
    rubrics = {
        "oracle-audit": (
            "Audit whether every acceptance criterion has an observable "
            "positive and negative oracle, whether the baseline really fails "
            "or passes as declared, and whether implementation could satisfy "
            "the oracle without satisfying the behavior."
        ),
        "code-review": (
            "Review the diff and fresh evidence for correctness, regressions, "
            "security, maintainability, and any weakening or bypass of the "
            "frozen acceptance contract."
        ),
        "artifact-review": (
            "Review each declared logical deliverable against its frozen "
            "criteria and inputs. Use only the bound direct artifact bytes or "
            "project-owned inspection logs listed for that deliverable. Return "
            "a separate verdict for every deliverable; do not infer a PASS "
            "from file presence or a check exit code alone."
        ),
        "adversarial-qa": (
            "Exercise realistic negative, boundary, integration, and user "
            "paths implicated by the approved risks. Treat unexplained skips "
            "or synthetic-only proof as blocking."
        ),
        "blocker-review": (
            "Determine whether the claimed blocker is external and genuinely "
            "prevents progress after safe in-scope alternatives are exhausted."
        ),
    }
    return (
        f"{common}\n\n{receipt}\n\n{rubrics[str(kind)]}\n"
        f"Challenge: {challenge_id}"
    )


def _chain_bound_subagent_start(
    root: pathlib.Path,
    state: dict[str, Any],
    event: dict[str, Any],
    host: str,
) -> dict[str, Any]:
    pending = state.get("chain_gates", {}).get("pending")
    if not isinstance(pending, dict):
        return {}
    agent_id = event.get("agent_id")
    agent_type = event.get("agent_type")
    session_id = event.get("session_id")
    host_record = state.get("chain_hosts", {}).get(host)
    expected_host = pending.get("expected_host")
    if (
        not isinstance(agent_id, str)
        or not agent_id
        or not isinstance(agent_type, str)
        or not agent_type
        or not isinstance(session_id, str)
        or not isinstance(host_record, dict)
        or host_record.get("session_id") != session_id
        or (
            isinstance(expected_host, str)
            and expected_host != host
        )
    ):
        return {}
    bound = pending.get("bound_agent_id")
    if isinstance(bound, str) and bound != agent_id:
        return {}
    if bound is None:
        pending["bound_agent_id"] = agent_id
        pending["bound_agent_type"] = agent_type
        pending["host"] = host
        pending["session_id"] = session_id
        pending["bound_at"] = _utc_now()
        _save_state(root, state)
    return {
        "hookSpecificOutput": {
            "hookEventName": "SubagentStart",
            "additionalContext": _chain_gate_rubric(pending),
        }
    }


def _chain_gate_marker(
    message: Any,
    pending: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if pending is None:
        pending = {}
    if not isinstance(message, str):
        raise EZPowersError("bound reviewer returned no terminal message")
    pattern = re.compile(
        r"<!--\s*ezpowers:gate:start\s*-->\s*"
        r"```json\s*(\{.*?\})\s*```\s*"
        r"<!--\s*ezpowers:gate:end\s*-->",
        re.DOTALL,
    )
    matches = pattern.findall(message)
    if len(matches) != 1:
        raise EZPowersError(
            "bound reviewer must return exactly one structured gate marker"
        )
    try:
        value = json.loads(matches[0])
    except json.JSONDecodeError as exc:
        raise EZPowersError(f"bound reviewer gate JSON is invalid: {exc}") from exc
    if pending.get("kind") == "artifact-review":
        if not isinstance(value, dict) or set(value) != {
            "schema_version",
            "challenge_id",
            "deliverables",
        }:
            raise EZPowersError("bound artifact-review receipt has an invalid shape")
        if value.get("schema_version") != GRAPH_BOUND_SCHEMA_VERSION:
            raise EZPowersError("bound artifact-review schema_version must be 2")
        raw_results = value.get("deliverables")
        contract = pending.get("artifact_review")
        if not isinstance(raw_results, list) or not isinstance(contract, list):
            raise EZPowersError("bound artifact-review deliverables must be an array")
        if len(raw_results) != len(contract):
            raise EZPowersError("bound artifact-review must cover every deliverable")
        normalized_results: list[dict[str, Any]] = []
        for index, (raw, expected) in enumerate(zip(raw_results, contract)):
            if not isinstance(raw, dict) or set(raw) != {
                "id",
                "verdict",
                "blocking_findings",
                "observations",
                "reviewed_sources",
            }:
                raise EZPowersError(
                    f"bound artifact-review deliverables[{index}] has an invalid shape"
                )
            if raw.get("id") != expected.get("id"):
                raise EZPowersError(
                    "bound artifact-review deliverable identity or order changed"
                )
            verdict = raw.get("verdict")
            findings = raw.get("blocking_findings")
            observations = raw.get("observations")
            reviewed_sources = raw.get("reviewed_sources")
            if verdict not in {"PASS", "FAIL"}:
                raise EZPowersError("artifact-review verdict must be PASS or FAIL")
            if (
                not isinstance(findings, list)
                or any(not isinstance(item, str) or not item.strip() for item in findings)
                or not isinstance(observations, list)
                or not observations
                or any(not isinstance(item, str) or not item.strip() for item in observations)
                or reviewed_sources != expected.get("required_source_ids")
            ):
                raise EZPowersError(
                    f"artifact-review {raw.get('id')} findings, observations, or reviewed_sources are invalid"
                )
            if verdict == "PASS" and findings:
                raise EZPowersError("artifact-review PASS cannot contain blocking findings")
            if verdict == "FAIL" and not findings:
                raise EZPowersError("artifact-review FAIL requires a blocking finding")
            normalized_results.append(
                {
                    "id": raw["id"],
                    "verdict": verdict,
                    "blocking_findings": [item.strip() for item in findings],
                    "observations": [item.strip() for item in observations],
                    "reviewed_sources": list(reviewed_sources),
                }
            )
        failed = [item for item in normalized_results if item["verdict"] != "PASS"]
        return {
            "schema_version": GRAPH_BOUND_SCHEMA_VERSION,
            "challenge_id": value.get("challenge_id"),
            "verdict": "FAIL" if failed else "PASS",
            "blocking_findings": [
                f"{item['id']}: {finding}"
                for item in failed
                for finding in item["blocking_findings"]
            ],
            "observations": [
                f"{item['id']}: {observation}"
                for item in normalized_results
                for observation in item["observations"]
            ],
            "deliverables": normalized_results,
            "failed_deliverable_ids": [item["id"] for item in failed],
        }

    if not isinstance(value, dict) or set(value) != {
        "schema_version",
        "challenge_id",
        "verdict",
        "blocking_findings",
        "observations",
    }:
        raise EZPowersError("bound reviewer gate receipt has an invalid shape")
    if value.get("schema_version") != SCHEMA_VERSION:
        raise EZPowersError("bound reviewer gate schema_version must be 1")
    verdict = value.get("verdict")
    if verdict not in {"PASS", "FAIL", "BLOCKED"}:
        raise EZPowersError("bound reviewer verdict must be PASS, FAIL, or BLOCKED")
    findings = value.get("blocking_findings")
    observations = value.get("observations")
    if (
        not isinstance(findings, list)
        or any(not isinstance(item, str) or not item.strip() for item in findings)
        or not isinstance(observations, list)
        or not observations
        or any(
            not isinstance(item, str) or not item.strip()
            for item in observations
        )
    ):
        raise EZPowersError(
            "bound reviewer findings and observations must be string arrays "
            "with at least one observation"
        )
    if verdict == "PASS" and findings:
        raise EZPowersError("PASS gate receipt cannot contain blocking findings")
    if verdict in {"FAIL", "BLOCKED"} and not findings:
        raise EZPowersError(
            f"{verdict} gate receipt requires at least one blocking finding"
        )
    return {
        **value,
        "blocking_findings": [item.strip() for item in findings],
        "observations": [item.strip() for item in observations],
    }


def _chain_gate_receipt_pointer(
    root: pathlib.Path,
    receipt: dict[str, Any],
) -> dict[str, Any]:
    receipt_path = (
        root
        / CHAIN_EVIDENCE_RELATIVE_PATH
        / str(receipt["challenge_id"])
        / "receipt.json"
    )
    _write_json(receipt_path, receipt)
    receipt_hash = _sha256_file(receipt_path)
    _atomic_write(
        receipt_path.with_name("receipt.json.sha256"),
        (receipt_hash + "\n").encode("ascii"),
    )
    return {
        "path": _log_relative(root, receipt_path),
        "sha256": receipt_hash,
        "kind": receipt["kind"],
        "subject_sha256": receipt["subject_sha256"],
        "verdict": receipt["verdict"],
    }


def _chain_bound_subagent_stop(
    root: pathlib.Path,
    state: dict[str, Any],
    event: dict[str, Any],
    host: str,
) -> dict[str, Any]:
    pending = state.get("chain_gates", {}).get("pending")
    if not isinstance(pending, dict):
        return {}
    if (
        pending.get("host") != host
        or pending.get("bound_agent_id") != event.get("agent_id")
        or pending.get("bound_agent_type") != event.get("agent_type")
        or pending.get("session_id") != event.get("session_id")
    ):
        return {}
    try:
        marker = _chain_gate_marker(
            event.get("last_assistant_message"),
            pending,
        )
        if marker.get("challenge_id") != pending.get("challenge_id"):
            raise EZPowersError("bound reviewer challenge_id does not match")
        if (
            marker.get("verdict") == "BLOCKED"
            and pending.get("kind") != "blocker-review"
        ):
            raise EZPowersError("BLOCKED is valid only for blocker-review")
        workspace: dict[str, Any] | None
        try:
            workspace = _workspace_snapshot(root)
        except EZPowersError:
            workspace = None
        artifact_snapshot: dict[str, Any] | None = None
        if pending.get("kind") == "artifact-review":
            run_for_artifacts = state.get("chain_run")
            plan_path = (
                run_for_artifacts.get("plan_path")
                if isinstance(run_for_artifacts, dict)
                else None
            )
            if not isinstance(plan_path, str):
                raise EZPowersError("artifact-review run has no active plan")
            artifact_flow = _validate_flow(root, plan_path)
            if artifact_flow.errors:
                raise EZPowersError("artifact-review plan changed during review")
            artifact_snapshot = _planning_artifact_snapshot(root, artifact_flow)
        receipt = {
            "schema_version": (
                GRAPH_BOUND_SCHEMA_VERSION
                if pending.get("kind") == "artifact-review"
                else SCHEMA_VERSION
            ),
            "challenge_id": pending["challenge_id"],
            "kind": pending["kind"],
            "subject_sha256": pending["subject_sha256"],
            "approval_sha256": pending.get("approval_sha256"),
            "verdict": marker["verdict"],
            "blocking_findings": marker["blocking_findings"],
            "observations": marker["observations"],
            "reviewer": {
                "host": host,
                "session_id": event.get("session_id"),
                "agent_id": event.get("agent_id"),
                "agent_type": event.get("agent_type"),
            },
            "workspace": workspace,
            "completed_at": _utc_now(),
        }
        if pending.get("kind") == "artifact-review":
            receipt["deliverables"] = marker["deliverables"]
            receipt["review_sources"] = pending.get("artifact_review")
            receipt["artifacts"] = artifact_snapshot
        pointer = _chain_gate_receipt_pointer(root, receipt)
        key = _chain_receipt_key(
            str(receipt["kind"]),
            str(receipt["subject_sha256"]),
        )
        state["chain_gates"]["receipts"][key] = pointer
        if (
            receipt["kind"] == "oracle-audit"
            and receipt["verdict"] != "PASS"
        ):
            state["chain_gates"]["consumed"][key] = pointer
        state["chain_gates"]["pending"] = None

        run = state.get("chain_run")
        if isinstance(run, dict) and run.get("status") == "RUNNING":
            kind = str(receipt["kind"])
            verdict = str(receipt["verdict"])
            gates = run.get("gates")
            if not isinstance(gates, dict):
                gates = {}
                run["gates"] = gates
            if verdict == "PASS" and kind in gates:
                gates[kind] = pointer
                _chain_clear_failure_repeat(run)
            elif kind in {"code-review", "artifact-review", "adversarial-qa"}:
                failure_workspace = receipt.get("workspace")
                if not isinstance(failure_workspace, dict):
                    failure_workspace = _workspace_snapshot(root)
                _chain_require_product_rework(
                    run,
                    workspace=failure_workspace,
                    reason=(
                        f"{kind} returned {verdict}: "
                        + "; ".join(receipt["blocking_findings"])
                    ),
                    failed_deliverables=(
                        _planning_failed_deliverable_hashes(
                            artifact_snapshot or {},
                            marker.get("failed_deliverable_ids", []),
                        )
                        if kind == "artifact-review"
                        else None
                    ),
                )
                if kind == "adversarial-qa":
                    counters = run.get("counters", {})
                    counters["qa_cycles"] = int(counters.get("qa_cycles", 0)) + 1
                _chain_record_failure(
                    run,
                    counter="review_failures",
                    category=kind,
                    value={
                        "verdict": verdict,
                        "blocking_findings": receipt["blocking_findings"],
                    },
                )
                if (
                    kind == "adversarial-qa"
                    and verdict != "PASS"
                    and int(run["counters"].get("qa_cycles", 0))
                    >= int(run["limits"].get("qa_cycles", 0))
                ):
                    _chain_fail_terminal(
                        run,
                        "adversarial QA failed at the approved QA cycle "
                        f"limit ({run['limits'].get('qa_cycles')})",
                    )
            elif kind == "blocker-review" and verdict == "BLOCKED":
                _chain_fail_terminal(
                    run,
                    "; ".join(receipt["blocking_findings"]),
                    status="BLOCKED",
                )
        _save_state(root, state)
        return {}
    except EZPowersError as exc:
        run = state.get("chain_run")
        if isinstance(run, dict) and run.get("status") == "RUNNING":
            if pending.get("kind") == "adversarial-qa":
                counters = run.get("counters", {})
                counters["qa_cycles"] = int(counters.get("qa_cycles", 0)) + 1
            _chain_record_failure(
                run,
                counter="review_failures",
                category=str(pending.get("kind")),
                value={"invalid_receipt": str(exc)},
            )
            if (
                pending.get("kind") == "adversarial-qa"
                and int(run.get("counters", {}).get("qa_cycles", 0))
                >= int(run.get("limits", {}).get("qa_cycles", 0))
            ):
                _chain_fail_terminal(
                    run,
                    "adversarial QA produced an invalid receipt at the "
                    "approved QA cycle limit "
                    f"({run.get('limits', {}).get('qa_cycles')})",
                )
        terminal = (
            isinstance(run, dict)
            and run.get("status") in CHAIN_TERMINAL_STATUSES
        )
        if terminal:
            state["chain_gates"]["pending"] = None
        _save_state(root, state)
        if terminal:
            return {}
        return {
            "decision": "block",
            "reason": (
                "EZPowers rejected this independent gate receipt. Correct the "
                f"same challenge without editing repository files: {exc}"
            ),
        }


def _chain_frozen_paths(
    root: pathlib.Path,
    state: dict[str, Any],
) -> set[str]:
    run = state.get("chain_run")
    if not isinstance(run, dict):
        return set()
    paths = {
        CHAIN_RELATIVE_PATH.as_posix(),
        CONFIG_RELATIVE_PATH.as_posix(),
    }
    approval, _ = _chain_approval(root, state)
    if isinstance(run.get("approval_path"), str):
        paths.add(str(run["approval_path"]))
    if isinstance(approval, dict):
        for raw in approval.get("files", []):
            if isinstance(raw, dict) and isinstance(raw.get("path"), str):
                paths.add(raw["path"])
        for raw in approval.get("inputs", []):
            if isinstance(raw, dict) and isinstance(raw.get("path"), str):
                paths.add(raw["path"])
    return {item.replace("\\", "/") for item in paths}


def _chain_strings(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for nested in value.values():
            yield from _chain_strings(nested)
    elif isinstance(value, list):
        for nested in value:
            yield from _chain_strings(nested)


def _chain_pretool_response(
    root: pathlib.Path,
    state: dict[str, Any],
    event: dict[str, Any],
) -> dict[str, Any]:
    run = state.get("chain_run")
    if (
        not isinstance(run, dict)
        or run.get("status") in CHAIN_TERMINAL_STATUSES
    ):
        return {}
    tool_name = str(event.get("tool_name", ""))
    if tool_name not in {"Bash", "Write", "Edit", "apply_patch"}:
        return {}
    values = "\n".join(_chain_strings(event.get("tool_input", {}))).replace(
        "\\",
        "/",
    )
    lowered = values.lower()
    if tool_name == "Bash" and not re.search(
        r"(?:^|[\s;&|])(?:rm|mv|cp|sed|perl|python|powershell|pwsh|"
        r"set-content|add-content|out-file|remove-item|move-item|copy-item)"
        r"(?:\s|$)",
        lowered,
    ):
        return {}
    matched = [
        path
        for path in sorted(_chain_frozen_paths(root, state))
        if path.lower() in lowered
        or str((root / path).resolve()).replace("\\", "/").lower() in lowered
    ]
    if not matched:
        return {}
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": (
                "EZPowers froze this approved acceptance contract; start a "
                "new approval instead of editing: " + ", ".join(matched)
            ),
        }
    }


def _chain_stop_response(
    root: pathlib.Path,
    state: dict[str, Any],
    host: str,
) -> dict[str, Any]:
    run = state.get("chain_run")
    if not isinstance(run, dict):
        return {}
    _chain_refresh_run_status(root, state)
    status = run.get("status")
    if status in {"RUNNING", "PENDING_LOOP"}:
        counters = run.get("counters", {})
        limits = run.get("limits", {})
        counters["iterations"] = int(counters.get("iterations", 0)) + 1
        if int(counters["iterations"]) >= int(limits.get("total_iterations", 0)):
            _chain_fail_terminal(
                run,
                "continuation reached the approved total iteration limit "
                f"({limits.get('total_iterations')})",
            )
        status = run.get("status")
    _save_state(root, state)
    if status in CHAIN_TERMINAL_STATUSES:
        reason = str(run.get("terminal_reason") or status)
        if host == "codex":
            return {"continue": False, "stopReason": reason}
        return {}
    if status == "PENDING_LOOP":
        if host == "claude":
            return {
                "decision": "block",
                "reason": "Activate the approved harness-chain loop authority.",
            }
        return {}
    if host == "claude":
        return {
            "decision": "block",
            "reason": _chain_next_action(state),
        }
    return {}


def _chain_hook_command(args: argparse.Namespace) -> int:
    try:
        raw = sys.stdin.read()
        event = json.loads(raw) if raw.strip() else {}
    except (OSError, json.JSONDecodeError):
        event = {}
    if not isinstance(event, dict):
        event = {}
    response: dict[str, Any] = {}
    try:
        root = _runtime_project_root()
        with _runtime_lock(root):
            state = _load_state(root)
            event_name = event.get("hook_event_name")
            if event_name == "SessionStart":
                try:
                    chain, chain_sha256 = _load_chain_value(root)
                except EZPowersError:
                    chain = {}
                    chain_sha256 = ""
                if (
                    args.host in chain.get("hosts", [])
                    and _chain_host_hook_present(root, args.host)
                    and isinstance(event.get("session_id"), str)
                    and bool(event["session_id"])
                ):
                    state["chain_hosts"][args.host] = {
                        "session_id": event["session_id"],
                        "hook_identity": _chain_hook_identity(
                            root,
                            args.host,
                            chain_sha256,
                        ),
                        "permission_mode": event.get("permission_mode"),
                        "source": event.get("source"),
                        "handshake_at": _utc_now(),
                    }
                    _save_state(root, state)
            elif event_name == "PreToolUse":
                response = _chain_pretool_response(root, state, event)
            elif event_name == "SubagentStart":
                response = _chain_bound_subagent_start(
                    root,
                    state,
                    event,
                    args.host,
                )
            elif event_name == "SubagentStop":
                response = _chain_bound_subagent_stop(
                    root,
                    state,
                    event,
                    args.host,
                )
            elif event_name == "Stop":
                response = _chain_stop_response(root, state, args.host)
    except EZPowersError as exc:
        # A chain hook must never exit 2: on Stop that blocks stopping
        # forever, and on PreToolUse it denies every matched tool call.
        # Degrade to an allow/no-op response so a broken loop dies instead
        # of wedging the session; authoritative contract checks still gate
        # verify, gates, and certification.
        response = {}
        print(f"EZPowers chain hook fail-safe no-op: {exc}", file=sys.stderr)
    print(json.dumps(response, ensure_ascii=False))
    return 0


def _set_active_plan(flow: Flow) -> bool:
    state = _load_state(flow.root)
    if state.get("active_plan") == flow.plan_rel:
        return False
    run = state.get("chain_run")
    if (
        isinstance(run, dict)
        and run.get("status") not in CHAIN_TERMINAL_STATUSES
        and run.get("plan_path") != flow.plan_rel
    ):
        raise EZPowersError(
            "another harness-chain plan is active; its approved run must "
            "reach a terminal verdict before activating a different plan"
        )
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
            "assurance_graph_sha256": (
                flow.assurance_graph_sha256 if not flow.errors else None
            ),
            "task_waves": flow.task_waves if not flow.errors else [],
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
        or normalized.startswith(f"{WIKI_RELATIVE_PATH.as_posix()}/")
        or normalized.startswith(f"{DOCS_STAGING_RELATIVE_PATH.as_posix()}/")
        or normalized.startswith(".ezpowers/backups/")
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
        ":(exclude).ezpowers/wiki/**",
        ":(exclude).ezpowers/staging/**",
        ":(exclude).ezpowers/backups/**",
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


def _planning_artifact_snapshot(root: pathlib.Path, flow: Flow) -> dict[str, Any]:
    if flow.profile.name != "planning":
        return {}
    inputs: list[dict[str, Any]] = []
    for entry in flow.inputs:
        parsed = _planning_artifact_path(
            root,
            entry["path"],
            label=f"planning input {entry['id']}",
            must_exist=True,
        )
        assert parsed is not None
        path_name, path = parsed
        inputs.append(
            {"id": entry["id"], "path": path_name, "sha256": _sha256_file(path)}
        )
    deliverables: list[dict[str, Any]] = []
    for deliverable in flow.deliverables:
        paths: list[dict[str, str]] = []
        for path_name in deliverable["paths"]:
            parsed = _planning_artifact_path(
                root,
                path_name,
                label=f"deliverable {deliverable['id']}",
                must_exist=True,
            )
            assert parsed is not None
            canonical, path = parsed
            paths.append({"path": canonical, "sha256": _sha256_file(path)})
        deliverables.append({"id": deliverable["id"], "paths": paths})
    value = {"inputs": inputs, "deliverables": deliverables}
    value["sha256"] = _sha256_bytes(_json_bytes(value))
    return value


def _planning_failed_deliverable_hashes(
    artifact_snapshot: dict[str, Any],
    deliverable_ids: Iterable[str],
) -> dict[str, list[dict[str, str]]]:
    selected = set(deliverable_ids)
    return {
        str(entry["id"]): list(entry.get("paths", []))
        for entry in artifact_snapshot.get("deliverables", [])
        if isinstance(entry, dict) and entry.get("id") in selected
    }


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
    *,
    occurrence_id: str | None = None,
    include_graph_fields: bool = False,
    cancel_event: threading.Event | None = None,
    process_registry: set[subprocess.Popen[Any]] | None = None,
    registry_lock: threading.Lock | None = None,
) -> dict[str, Any]:
    safe_task = re.sub(r"[^A-Za-z0-9._-]+", "-", task_id) or "project"
    safe_check = re.sub(r"[^A-Za-z0-9._-]+", "-", check["id"]) or "check"
    identity_source = occurrence_id or f"{task_id}\0{check['id']}"
    identity = _sha256_bytes(identity_source.encode("utf-8"))[:12]
    prefix = run_dir / f"{safe_task}--{safe_check}--{identity}"
    stdout_path = pathlib.Path(f"{prefix}.stdout.log")
    stderr_path = pathlib.Path(f"{prefix}.stderr.log")
    cwd = _contained_path(root, check["cwd"], label=f"check {check['id']} cwd", must_exist=True, directory=True)
    started = time.monotonic()
    started_at = _utc_now()
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
            if process_registry is not None and registry_lock is not None:
                with registry_lock:
                    process_registry.add(process)
            try:
                deadline = time.monotonic() + check["timeout_seconds"]
                while True:
                    if cancel_event is not None and cancel_event.is_set():
                        spawn_error = "check execution cancelled"
                        _kill_process_tree(process)
                        with contextlib.suppress(Exception):
                            process.wait(timeout=5)
                        exit_code = 130
                        break
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        timed_out = True
                        _kill_process_tree(process)
                        with contextlib.suppress(Exception):
                            process.wait(timeout=5)
                        exit_code = 124
                        break
                    try:
                        exit_code = process.wait(timeout=min(0.1, remaining))
                        break
                    except subprocess.TimeoutExpired:
                        continue
            finally:
                if process_registry is not None and registry_lock is not None:
                    with registry_lock:
                        process_registry.discard(process)
        except (OSError, ValueError) as exc:
            spawn_error = str(exc)
            stderr.write((spawn_error + "\n").encode("utf-8", "replace"))
    duration_ms = int((time.monotonic() - started) * 1000)
    result = {
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
    if include_graph_fields:
        result.update(
            {
                "node_id": occurrence_id,
                "started_at": started_at,
                "finished_at": _utc_now(),
            }
        )
    return result


def _invocation_locks(invocation: dict[str, Any]) -> set[str]:
    check = invocation["check"]
    locks = {f"check-id.{check['id']}"}
    locks.update(
        f"resource.{item}"
        for item in check["concurrency"]["resource_locks"]
    )
    return locks


def _invocation_batches(
    invocations: list[dict[str, Any]],
    *,
    max_workers: int,
    parallel_enabled: bool,
) -> list[list[dict[str, Any]]]:
    pending = list(invocations)
    batches: list[list[dict[str, Any]]] = []
    while pending:
        first = pending.pop(0)
        first_safe = bool(first["check"]["concurrency"]["safe"])
        if not parallel_enabled or max_workers <= 1 or not first_safe:
            batches.append([first])
            continue
        batch = [first]
        held_locks = _invocation_locks(first)
        while pending and len(batch) < max_workers:
            candidate = pending[0]
            if not bool(candidate["check"]["concurrency"]["safe"]):
                break
            candidate_locks = _invocation_locks(candidate)
            if held_locks.intersection(candidate_locks):
                break
            pending.pop(0)
            batch.append(candidate)
            held_locks.update(candidate_locks)
        batches.append(batch)
    return batches


def _execute_invocations(
    root: pathlib.Path,
    run_dir: pathlib.Path,
    invocations: list[dict[str, Any]],
    *,
    max_workers: int,
    parallel_enabled: bool,
    phase: str,
    task_wave: int | None,
    include_graph_fields: bool,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Execute ready checks while keeping results in declaration order."""
    if not invocations:
        return [], []
    cancel_event = threading.Event()
    registry_lock = threading.Lock()
    process_registry: set[subprocess.Popen[Any]] = set()
    results_by_node: dict[str, dict[str, Any]] = {}
    execution_waves: list[dict[str, Any]] = []
    try:
        for batch_index, batch in enumerate(
            _invocation_batches(
                invocations,
                max_workers=max_workers,
                parallel_enabled=parallel_enabled,
            )
        ):
            wave_started = _utc_now()
            if len(batch) == 1:
                invocation = batch[0]
                results_by_node[invocation["node_id"]] = _run_check(
                    root,
                    run_dir,
                    invocation["task_id"],
                    invocation["check"],
                    occurrence_id=invocation["node_id"],
                    include_graph_fields=include_graph_fields,
                    cancel_event=cancel_event,
                    process_registry=process_registry,
                    registry_lock=registry_lock,
                )
            else:
                executor = concurrent.futures.ThreadPoolExecutor(
                    max_workers=len(batch),
                    thread_name_prefix="ezpowers-check",
                )
                futures: dict[str, concurrent.futures.Future[dict[str, Any]]] = {}
                try:
                    futures = {
                        invocation["node_id"]: executor.submit(
                            _run_check,
                            root,
                            run_dir,
                            invocation["task_id"],
                            invocation["check"],
                            occurrence_id=invocation["node_id"],
                            include_graph_fields=include_graph_fields,
                            cancel_event=cancel_event,
                            process_registry=process_registry,
                            registry_lock=registry_lock,
                        )
                        for invocation in batch
                    }
                    for invocation in batch:
                        results_by_node[invocation["node_id"]] = futures[
                            invocation["node_id"]
                        ].result()
                except BaseException:
                    cancel_event.set()
                    with registry_lock:
                        active = list(process_registry)
                    for process in active:
                        _kill_process_tree(process)
                    for future in futures.values():
                        future.cancel()
                    executor.shutdown(wait=True, cancel_futures=True)
                    raise
                else:
                    executor.shutdown(wait=True)
            execution_waves.append(
                {
                    "phase": phase,
                    "task_wave": task_wave,
                    "batch": batch_index,
                    "node_ids": [item["node_id"] for item in batch],
                    "parallel": len(batch) > 1,
                    "started_at": wave_started,
                    "finished_at": _utc_now(),
                }
            )
    except BaseException:
        cancel_event.set()
        with registry_lock:
            active = list(process_registry)
        for process in active:
            _kill_process_tree(process)
        raise
    return (
        [results_by_node[item["node_id"]] for item in invocations],
        execution_waves,
    )


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
    artifacts_before: dict[str, Any] | None = None
    if flow.profile.name == "planning":
        try:
            artifacts_before = _planning_artifact_snapshot(root, flow)
        except (EZPowersError, OSError) as exc:
            reason = f"planning artifacts are not ready for verification: {exc}"
            payload = {
                "status": "FAIL",
                "errors": [reason],
                "tasks": [],
                "reasons": [reason],
                "project_profile": flow.profile.name,
            }
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
    state_before = _load_state(root)
    chain_approval, chain_errors = _chain_flow_preflight(
        root,
        state_before,
        flow,
        operation="verification",
    )
    if chain_errors:
        payload = {
            "status": "FAIL",
            "errors": chain_errors,
            "tasks": [],
            "reasons": chain_errors,
        }
        _emit(payload, args.json)
        return 2
    chain_run_before = state_before.get("chain_run")
    if (
        chain_approval is not None
        and args.all_checks
        and isinstance(chain_run_before, dict)
    ):
        observed, rework_reason = _chain_rework_observed(
            root,
            chain_run_before,
        )
        if not observed:
            reason = str(rework_reason or "product rework has not been observed")
            _chain_record_failure(
                chain_run_before,
                counter="validation_failures",
                category="rework-not-observed",
                value=reason,
            )
            _save_state(root, state_before)
            payload = {
                "status": "FAIL",
                "errors": [reason],
                "tasks": [],
                "reasons": [reason],
                "counters": chain_run_before.get("counters", {}),
                "chain_status": chain_run_before.get("status"),
            }
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
    graph_bound = _flow_graph_bound(flow)
    parallel_enabled = (
        graph_bound
        and flow.config_schema_version >= 2
        and flow.max_parallel_checks > 1
    )
    effective_workers = flow.max_parallel_checks if parallel_enabled else 1
    task_results_by_id: dict[str, dict[str, Any]] = {
        str(task["id"]): {
            "id": task["id"],
            "criteria": task["criteria"],
            "checks": [],
            **(
                {"depends_on": list(task.get("depends_on", []))}
                if graph_bound
                else {}
            ),
        }
        for task in selected
    }
    execution_waves: list[dict[str, Any]] = []
    reasons: list[str] = []
    task_groups: list[tuple[int | None, list[dict[str, Any]]]] = []
    if args.task:
        task_groups.append((None, selected))
    else:
        selected_by_id = {str(task["id"]): task for task in selected}
        for wave_index, task_ids in enumerate(flow.task_waves):
            wave_tasks = [
                selected_by_id[task_id]
                for task_id in task_ids
                if task_id in selected_by_id
            ]
            if wave_tasks:
                task_groups.append((wave_index, wave_tasks))
    for wave_index, wave_tasks in task_groups:
        invocations: list[dict[str, Any]] = []
        for task in wave_tasks:
            for check_index, check in enumerate(task["checks"], 1):
                invocations.append(
                    {
                        "node_id": _task_check_node_id(
                            str(task["id"]),
                            check_index,
                            str(check["id"]),
                        ),
                        "task_id": str(task["id"]),
                        "check": check,
                    }
                )
        check_results, wave_records = _execute_invocations(
            root,
            run_dir,
            invocations,
            max_workers=effective_workers,
            parallel_enabled=parallel_enabled,
            phase="task",
            task_wave=wave_index,
            include_graph_fields=graph_bound,
        )
        execution_waves.extend(wave_records)
        for invocation, check_result in zip(invocations, check_results):
            task_results_by_id[invocation["task_id"]]["checks"].append(
                check_result
            )
    task_results = [
        task_results_by_id[str(task["id"])] for task in selected
    ]
    for task_result in task_results:
        if any(check["status"] != "PASS" for check in task_result["checks"]):
            reasons.append(f"task {task_result['id']} verification failed")

    project_results: list[dict[str, Any]] = []
    if args.all_checks:
        project_invocations = [
            {
                "node_id": _project_check_node_id(index, check_id),
                "task_id": "project",
                "check": flow.project_checks[check_id],
            }
            for index, check_id in enumerate(flow.required_checks, 1)
        ]
        project_results, project_waves = _execute_invocations(
            root,
            run_dir,
            project_invocations,
            max_workers=effective_workers,
            parallel_enabled=parallel_enabled,
            phase="required",
            task_wave=None,
            include_graph_fields=graph_bound,
        )
        execution_waves.extend(project_waves)
        for check_id, result in zip(flow.required_checks, project_results):
            if result["status"] != "PASS":
                reasons.append(f"required project check {check_id} failed")

    workspace_after = _workspace_snapshot(root)
    artifacts_after: dict[str, Any] | None = None
    if flow.profile.name == "planning":
        try:
            artifacts_after = _planning_artifact_snapshot(root, flow)
        except (EZPowersError, OSError) as exc:
            reasons.append(f"planning artifacts changed during verification: {exc}")
        if artifacts_before != artifacts_after:
            reasons.append("declared planning artifacts changed during verification")
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

    state_after_checks = _load_state(root)
    chain_run = state_after_checks.get("chain_run")
    chain_binding: dict[str, Any] | None = None
    if chain_approval is not None and isinstance(chain_run, dict):
        _, contract_reasons = _chain_contract_reasons(root, state_after_checks)
        if contract_reasons:
            reasons.extend(
                f"harness-chain reapproval is required: {reason}"
                for reason in contract_reasons
            )
            _chain_mark_reapproval(state_after_checks, contract_reasons)
        chain_binding = {
            "run_id": chain_run.get("run_id"),
            "approval_path": chain_run.get("approval_path"),
            "approval_sha256": chain_run.get("approval_sha256"),
            "chain_sha256": chain_approval.get("chain_sha256"),
            **(
                {
                    "assurance_graph_sha256": chain_approval.get(
                        "assurance_graph_sha256"
                    )
                }
                if isinstance(
                    chain_approval.get("assurance_graph_sha256"),
                    str,
                )
                else {}
            ),
        }

    result_path = run_dir / "result.json"
    result: dict[str, Any] = {
        "schema_version": _flow_evidence_schema_version(flow),
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
    if graph_bound:
        result["assurance_graph"] = flow.assurance_graph
        result["assurance_graph_sha256"] = flow.assurance_graph_sha256
        result["execution"] = {
            "max_parallel_checks": effective_workers,
            "waves": execution_waves,
        }
        if workspace_before["fingerprint"] != workspace_after["fingerprint"]:
            result["parallel_workspace_mutation_candidates"] = sorted(
                {
                    node_id
                    for wave in execution_waves
                    if wave["parallel"]
                    for node_id in wave["node_ids"]
                }
            )
            result["workspace_mutation_causality"] = "not-proven"
    if flow.profile.name == "planning":
        result["project_profile"] = flow.profile.name
        result["artifacts"] = artifacts_after
        result["artifacts_before"] = artifacts_before
    if chain_binding is not None:
        result["chain"] = chain_binding
    result_bytes = _json_bytes(result)
    _atomic_write(result_path, result_bytes)
    digest = _sha256_bytes(result_bytes)
    _atomic_write(result_path.with_name("result.json.sha256"), (digest + "\n").encode("ascii"))

    pointer = {"path": result["evidence_path"], "sha256": digest}
    if args.all_checks:
        state_after_checks["latest_evidence"]["all"] = pointer
    else:
        state_after_checks["latest_evidence"]["tasks"][args.task] = pointer
    if chain_binding is not None and isinstance(chain_run, dict):
        if args.all_checks:
            chain_run["latest_verification"] = {
                "status": result["status"],
                "path": pointer["path"],
                "sha256": pointer["sha256"],
                "finished_at": result["finished_at"],
            }
            gates = chain_run.get("gates")
            if isinstance(gates, dict):
                gates[flow.profile.primary_review_kind] = None
                gates["adversarial-qa"] = None
        if result["status"] == "PASS" and args.all_checks:
            _chain_clear_failure_repeat(chain_run)
            chain_run["rework_required"] = None
        elif (
            result["status"] != "PASS"
            and chain_run.get("status") == "RUNNING"
        ):
            _chain_require_product_rework(
                chain_run,
                workspace=workspace_after,
                reason="verification failed: " + "; ".join(sorted(reasons)),
            )
            failed_checks = [
                {
                    "id": check.get("id"),
                    "status": check.get("status"),
                    "exit_code": check.get("exit_code"),
                    "timed_out": check.get("timed_out"),
                    "spawn_error": check.get("spawn_error"),
                }
                for check in _iter_check_results(result)
                if check.get("status") != "PASS"
            ]
            _chain_record_failure(
                chain_run,
                counter="validation_failures",
                category="verification",
                value={
                    "scope": scope,
                    "failed_checks": failed_checks,
                    "reasons": sorted(reasons),
                },
            )
    _save_state(root, state_after_checks)
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
        if (
            _flow_graph_bound(flow)
            and recorded_task.get("depends_on") != expected_task.get("depends_on", [])
        ):
            reasons.append(
                f"evidence inventory mismatch: dependencies changed for task {expected_task_id}"
            )
        recorded_checks = recorded_task.get("checks")
        if not isinstance(recorded_checks, list) or len(recorded_checks) != len(expected_task["checks"]):
            reasons.append(
                f"evidence inventory mismatch: check count changed for task {expected_task_id}"
            )
            continue
        for check_index, (expected_check, recorded_check) in enumerate(
            zip(expected_task["checks"], recorded_checks),
            1,
        ):
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
            if (
                _flow_graph_bound(flow)
                and recorded_check.get("node_id")
                != _task_check_node_id(
                    str(expected_task_id),
                    check_index,
                    str(expected_check["id"]),
                )
            ):
                reasons.append(
                    f"evidence inventory mismatch: occurrence changed for check "
                    f"{expected_check['id']} in task {expected_task_id}"
                )

    recorded_project = evidence.get("project_checks")
    if not isinstance(recorded_project, list) or len(recorded_project) != len(expected_project):
        if task_id is None:
            reasons.append("evidence inventory mismatch: required project check count changed")
        else:
            reasons.append("evidence inventory mismatch: task evidence must not contain project checks")
    else:
        for check_index, (expected_check, recorded_check) in enumerate(
            zip(expected_project, recorded_project),
            1,
        ):
            if not isinstance(recorded_check, dict) or any(
                recorded_check.get(field) != expected_check.get(field) for field in fields
            ):
                reasons.append(
                    f"evidence inventory mismatch: required check {expected_check['id']} changed"
                )
            elif (
                _flow_graph_bound(flow)
                and recorded_check.get("node_id")
                != _project_check_node_id(
                    check_index,
                    str(expected_check["id"]),
                )
            ):
                reasons.append(
                    f"evidence inventory mismatch: required check occurrence "
                    f"{expected_check['id']} changed"
                )
    return reasons


def _execution_reasons(
    flow: Flow,
    evidence: dict[str, Any],
    *,
    task_id: str | None,
) -> list[str]:
    if not _flow_graph_bound(flow):
        return []
    reasons: list[str] = []
    execution = evidence.get("execution")
    if not isinstance(execution, dict):
        return ["evidence execution trace is missing"]
    expected_max = (
        flow.max_parallel_checks if flow.config_schema_version >= 2 else 1
    )
    if execution.get("max_parallel_checks") != expected_max:
        reasons.append("evidence execution worker cap changed")
    raw_waves = execution.get("waves")
    if not isinstance(raw_waves, list):
        return reasons + ["evidence execution waves must be an array"]

    task_by_id = {str(task["id"]): task for task in flow.tasks}
    expected_task_nodes: list[str] = []
    node_task_wave: dict[str, int | None] = {}
    if task_id is not None:
        task = task_by_id.get(task_id)
        if task is not None:
            for index, check in enumerate(task["checks"], 1):
                node_id = _task_check_node_id(task_id, index, str(check["id"]))
                expected_task_nodes.append(node_id)
                node_task_wave[node_id] = None
    else:
        for wave_index, task_ids in enumerate(flow.task_waves):
            for current_task_id in task_ids:
                task = task_by_id[current_task_id]
                for index, check in enumerate(task["checks"], 1):
                    node_id = _task_check_node_id(
                        current_task_id,
                        index,
                        str(check["id"]),
                    )
                    expected_task_nodes.append(node_id)
                    node_task_wave[node_id] = wave_index
    expected_project_nodes = (
        [
            _project_check_node_id(index, check_id)
            for index, check_id in enumerate(flow.required_checks, 1)
        ]
        if task_id is None
        else []
    )
    node_contract = {
        str(node["id"]): node
        for node in flow.assurance_graph["nodes"]
        if node.get("type") == "check"
    }
    observed_task_nodes: list[str] = []
    observed_project_nodes: list[str] = []
    saw_required = False
    for index, raw_wave in enumerate(raw_waves):
        if not isinstance(raw_wave, dict):
            reasons.append(f"evidence execution wave {index} is invalid")
            continue
        phase = raw_wave.get("phase")
        node_ids = raw_wave.get("node_ids")
        if (
            phase not in {"task", "required"}
            or not isinstance(node_ids, list)
            or not node_ids
            or any(not isinstance(item, str) for item in node_ids)
        ):
            reasons.append(f"evidence execution wave {index} has invalid nodes")
            continue
        if phase == "required":
            saw_required = True
            observed_project_nodes.extend(node_ids)
            if raw_wave.get("task_wave") is not None:
                reasons.append("required execution wave must not name a task wave")
        else:
            if saw_required:
                reasons.append("task execution occurred after the required-check phase")
            observed_task_nodes.extend(node_ids)
            expected_wave_values = {node_task_wave.get(node_id) for node_id in node_ids}
            if expected_wave_values != {raw_wave.get("task_wave")}:
                reasons.append("task execution wave does not match plan dependencies")
        if raw_wave.get("parallel") is not (len(node_ids) > 1):
            reasons.append(f"evidence execution wave {index} parallel marker is invalid")
        if len(node_ids) > expected_max:
            reasons.append(f"evidence execution wave {index} exceeds the worker cap")
        held: set[str] = set()
        for node_id in node_ids:
            contract = node_contract.get(node_id)
            if contract is None:
                reasons.append(f"evidence execution contains unknown check node: {node_id}")
                continue
            if len(node_ids) > 1 and contract.get("safe") is not True:
                reasons.append(f"unsafe check overlapped in execution wave: {node_id}")
            locks = {str(contract.get("implicit_lock"))}
            locks.update(
                f"resource.{item}"
                for item in contract.get("resource_locks", [])
            )
            if held.intersection(locks):
                reasons.append(f"conflicting checks overlapped in execution wave: {node_id}")
            held.update(locks)
        for field in ("started_at", "finished_at"):
            if not isinstance(raw_wave.get(field), str) or not raw_wave[field]:
                reasons.append(f"evidence execution wave {index} has no {field}")
    if observed_task_nodes != expected_task_nodes:
        reasons.append("evidence execution task occurrence order changed")
    if observed_project_nodes != expected_project_nodes:
        reasons.append("evidence execution required occurrence order changed")
    return reasons


def _current_bindings(
    root: pathlib.Path,
    flow: Flow,
) -> tuple[dict[str, Any], list[str]]:
    bindings: dict[str, Any] = {
        "plan_path": flow.plan_rel,
        "spec_path": _relative(root, flow.spec_path),
        "assurance_graph_sha256": flow.assurance_graph_sha256,
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
    if flow.profile.name == "planning":
        bindings["project_profile"] = flow.profile.name
        try:
            bindings["artifacts"] = _planning_artifact_snapshot(root, flow)
        except (EZPowersError, OSError) as exc:
            reasons.append(f"planning artifact freshness failed: {exc}")
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
    expected_schema_version = (
        _flow_evidence_schema_version(flow)
    )
    if evidence.get("schema_version") != expected_schema_version:
        reasons.append("evidence schema_version is unsupported")
    if _flow_graph_bound(flow):
        recorded_graph = evidence.get("assurance_graph")
        recorded_graph_sha256 = evidence.get("assurance_graph_sha256")
        if not isinstance(recorded_graph, dict):
            reasons.append("evidence assurance graph is missing")
        else:
            if _sha256_bytes(_json_bytes(recorded_graph)) != recorded_graph_sha256:
                reasons.append("evidence assurance graph hash mismatch")
            if recorded_graph != flow.assurance_graph:
                reasons.append("assurance graph changed after verification")
        if recorded_graph_sha256 != flow.assurance_graph_sha256:
            reasons.append("evidence belongs to a different assurance graph")
    if flow.profile.name == "planning":
        if evidence.get("project_profile") != flow.profile.name:
            reasons.append("evidence belongs to a different project profile")
        current_artifacts = bindings[0].get("artifacts")
        if current_artifacts is not None and evidence.get("artifacts") != current_artifacts:
            reasons.append("declared planning artifacts changed after verification")
        if evidence.get("artifacts_before") != evidence.get("artifacts"):
            reasons.append("declared planning artifacts changed during recorded verification")
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
    try:
        chain_state = _load_state(root)
        chain_run = chain_state.get("chain_run")
        if (
            isinstance(chain_run, dict)
            and chain_run.get("plan_path") == flow.plan_rel
        ):
            chain_approval, chain_reasons = _chain_contract_reasons(
                root,
                chain_state,
            )
            if chain_reasons:
                reasons.extend(
                    f"harness-chain contract is stale: {reason}"
                    for reason in chain_reasons
                )
            expected_chain = {
                "run_id": chain_run.get("run_id"),
                "approval_path": chain_run.get("approval_path"),
                "approval_sha256": chain_run.get("approval_sha256"),
                "chain_sha256": (
                    chain_approval.get("chain_sha256")
                    if isinstance(chain_approval, dict)
                    else None
                ),
                **(
                    {
                        "assurance_graph_sha256": chain_approval.get(
                            "assurance_graph_sha256"
                        )
                    }
                    if isinstance(chain_approval, dict)
                    and isinstance(
                        chain_approval.get("assurance_graph_sha256"),
                        str,
                    )
                    else {}
                ),
            }
            if evidence.get("chain") != expected_chain:
                reasons.append(
                    "evidence is not bound to the active harness-chain approval"
                )
    except EZPowersError as exc:
        reasons.append(f"harness-chain state is invalid: {exc}")
    reasons.extend(_inventory_reasons(flow, evidence, task_id=task_id))
    reasons.extend(_execution_reasons(flow, evidence, task_id=task_id))
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
        if _flow_graph_bound(flow):
            for field in ("node_id", "started_at", "finished_at"):
                if not isinstance(check.get(field), str) or not check[field]:
                    reasons.append(
                        f"check occurrence metadata is missing: "
                        f"{check.get('id', '?')} {field}"
                    )
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


def _chain_certification_gates(
    root: pathlib.Path,
    state: dict[str, Any],
    *,
    evidence_hash: str,
    evidence: dict[str, Any],
) -> tuple[dict[str, Any], list[str]]:
    run = state.get("chain_run")
    if not isinstance(run, dict):
        return {}, []
    profile = PROJECT_PROFILE_POLICIES.get(
        str(run.get("project_profile", SOFTWARE_PROFILE.name)),
        SOFTWARE_PROFILE,
    )
    required = [profile.primary_review_kind]
    if run.get("requires_qa"):
        required.append("adversarial-qa")
    bindings: dict[str, Any] = {}
    reasons: list[str] = []
    latest = run.get("latest_verification")
    if (
        not isinstance(latest, dict)
        or latest.get("status") != "PASS"
        or latest.get("sha256") != evidence_hash
    ):
        reasons.append(
            "harness-chain certification requires its latest all-scope PASS "
            "verification"
        )
    if isinstance(run.get("rework_required"), dict):
        reasons.append(
            "harness-chain certification is blocked until product rework and "
            "a new all-scope PASS"
        )
    run_gates = run.get("gates")
    if not isinstance(run_gates, dict):
        return {}, ["harness-chain gate state is invalid"]
    for kind in required:
        receipt, pointer = _chain_load_receipt(
            root,
            state,
            kind=kind,
            subject_sha256=evidence_hash,
        )
        recorded = run_gates.get(kind)
        if (
            not isinstance(receipt, dict)
            or not isinstance(pointer, dict)
            or recorded != pointer
        ):
            reasons.append(
                f"fresh bound {kind} PASS receipt is required for this evidence"
            )
            continue
        if (
            receipt.get("verdict") != "PASS"
            or receipt.get("blocking_findings") != []
            or receipt.get("approval_sha256") != run.get("approval_sha256")
        ):
            reasons.append(f"{kind} receipt does not approve the active chain")
            continue
        reviewer = receipt.get("reviewer")
        if (
            not isinstance(reviewer, dict)
            or not isinstance(reviewer.get("agent_id"), str)
            or not reviewer["agent_id"]
            or not isinstance(reviewer.get("session_id"), str)
            or not reviewer["session_id"]
        ):
            reasons.append(f"{kind} receipt has no bound independent reviewer")
            continue
        workspace = receipt.get("workspace")
        if (
            not isinstance(workspace, dict)
            or workspace.get("fingerprint")
            != evidence.get("workspace", {}).get("fingerprint")
        ):
            reasons.append(f"workspace changed before the {kind} receipt")
            continue
        if kind == "artifact-review":
            try:
                expected_sources = _chain_artifact_review_contract(
                    root,
                    state,
                    run,
                    evidence_hash,
                )
            except EZPowersError as exc:
                reasons.append(f"artifact-review source binding is invalid: {exc}")
                continue
            expected_ids = [item["id"] for item in expected_sources]
            reviewed = receipt.get("deliverables")
            if (
                receipt.get("schema_version") != GRAPH_BOUND_SCHEMA_VERSION
                or not isinstance(reviewed, list)
                or [item.get("id") for item in reviewed if isinstance(item, dict)]
                != expected_ids
                or any(
                    not isinstance(item, dict)
                    or item.get("verdict") != "PASS"
                    or item.get("blocking_findings") != []
                    for item in reviewed
                )
                or receipt.get("review_sources") != expected_sources
                or receipt.get("artifacts") != evidence.get("artifacts")
            ):
                reasons.append(
                    "artifact-review receipt does not approve every bound deliverable and source"
                )
                continue
        bindings[kind] = pointer
    return bindings, reasons


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
    chain_approval, chain_errors = _chain_flow_preflight(
        root,
        state,
        flow,
        operation="certification",
    )
    if chain_errors:
        payload = {
            "status": "FAIL",
            "plan": flow.plan_rel,
            "fresh": False,
            "reasons": chain_errors,
        }
        _emit(payload, args.json)
        return 2
    fresh, reasons, evidence, evidence_hash, validated_evidence_path = _freshness(
        root,
        flow,
        state=state,
    )
    chain_gates: dict[str, Any] = {}
    if fresh and chain_approval is not None and evidence is not None:
        chain_gates, gate_reasons = _chain_certification_gates(
            root,
            state,
            evidence_hash=evidence_hash,
            evidence=evidence,
        )
        reasons.extend(gate_reasons)
        fresh = not reasons
    payload: dict[str, Any] = {
        "status": "PASS" if fresh else "FAIL",
        "plan": flow.plan_rel,
        "fresh": fresh,
        "reasons": reasons,
    }
    if fresh and evidence is not None and validated_evidence_path is not None:
        certificate = {
            "schema_version": (
                _flow_evidence_schema_version(flow)
            ),
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
        if _flow_graph_bound(flow):
            certificate["assurance_graph_sha256"] = flow.assurance_graph_sha256
        if flow.profile.name == "planning":
            certificate["project_profile"] = flow.profile.name
            certificate["artifacts"] = evidence["artifacts"]
        if chain_approval is not None:
            certificate["chain"] = evidence.get("chain")
            certificate["gates"] = chain_gates
        certificate_path = validated_evidence_path.with_name("certificate.json")
        _write_json(certificate_path, certificate)
        certificate_hash = _sha256_file(certificate_path)
        state = _load_state(root)
        state["latest_certificate"] = {
            "path": _log_relative(root, certificate_path),
            "evidence_sha256": evidence_hash,
            "sha256": certificate_hash,
        }
        chain_run = state.get("chain_run")
        if chain_approval is not None and isinstance(chain_run, dict):
            if chain_run.get("approval_sha256") != evidence.get(
                "chain",
                {},
            ).get("approval_sha256"):
                raise EZPowersError(
                    "chain approval changed during certification"
                )
            chain_run["status"] = "CERTIFIED"
            chain_run["terminal_reason"] = (
                "fresh verification and required independent gates certified"
            )
            chain_run["terminal_at"] = _utc_now()
            chain_run["certificate"] = state["latest_certificate"]
        _save_state(root, state)
        payload["certificate_path"] = _log_relative(root, certificate_path)
    _emit(payload, args.json)
    return 0 if fresh else 1


def _assurance_runtime_view(
    flow: Flow,
    state: dict[str, Any],
    core: dict[str, Any],
    evidence: dict[str, Any] | None,
    evidence_hash: str,
) -> dict[str, Any]:
    states: dict[str, str] = {
        str(node["id"]): "PENDING"
        for node in flow.assurance_graph["nodes"]
    }
    task_checks: dict[str, list[str]] = {
        str(task["id"]): [
            _task_check_node_id(str(task["id"]), index, str(check["id"]))
            for index, check in enumerate(task["checks"], 1)
        ]
        for task in flow.tasks
    }
    if isinstance(evidence, dict):
        for task in evidence.get("tasks", []):
            if not isinstance(task, dict):
                continue
            task_id = str(task.get("id", ""))
            for index, check in enumerate(task.get("checks", []), 1):
                if not isinstance(check, dict):
                    continue
                node_id = check.get("node_id")
                if not isinstance(node_id, str):
                    node_id = _task_check_node_id(
                        task_id,
                        index,
                        str(check.get("id", "")),
                    )
                if node_id in states:
                    states[node_id] = str(check.get("status") or "UNKNOWN")
        for index, check in enumerate(evidence.get("project_checks", []), 1):
            if not isinstance(check, dict):
                continue
            node_id = check.get("node_id")
            if not isinstance(node_id, str):
                node_id = _project_check_node_id(
                    index,
                    str(check.get("id", "")),
                )
            if node_id in states:
                states[node_id] = str(check.get("status") or "UNKNOWN")

    for task in flow.tasks:
        task_id = str(task["id"])
        check_states = [states[node_id] for node_id in task_checks[task_id]]
        if any(value == "FAIL" for value in check_states):
            task_state = "FAIL"
        elif check_states and all(value == "PASS" for value in check_states):
            task_state = "PASS"
        else:
            task_state = "PENDING"
        states[f"task:{task_id}"] = task_state
        for criterion_id in task["criteria"]:
            states[f"criterion:{criterion_id}"] = task_state

    if flow.profile.name == PLANNING_PROFILE.name:
        artifact_state = (
            "PASS"
            if core.get("fresh") is True
            else "STALE"
            if isinstance(evidence, dict)
            else "MISSING"
        )
        for entry in flow.inputs:
            states[f"input:{entry['id']}"] = artifact_state
        for deliverable in flow.deliverables:
            criterion_states = [
                states.get(f"criterion:{criterion_id}", "PENDING")
                for criterion_id in deliverable["criteria"]
            ]
            states[f"deliverable:{deliverable['id']}"] = (
                "FAIL"
                if any(value == "FAIL" for value in criterion_states)
                else artifact_state
            )

    if core.get("fresh") is True:
        states["evidence:all"] = "PASS"
    elif isinstance(evidence, dict):
        states["evidence:all"] = (
            "FAIL" if evidence.get("status") == "FAIL" else "STALE"
        )
    else:
        states["evidence:all"] = "MISSING"

    run = state.get("chain_run")
    chain_matches = (
        isinstance(run, dict) and run.get("plan_path") == flow.plan_rel
    )
    primary_review_id = f"review:{flow.profile.primary_review_kind}"
    if chain_matches:
        gates = run.get("gates", {})
        primary_review = (
            gates.get(flow.profile.primary_review_kind)
            if isinstance(gates, dict)
            else None
        )
        qa = gates.get("adversarial-qa") if isinstance(gates, dict) else None
        states[primary_review_id] = (
            "PASS"
            if isinstance(primary_review, dict)
            and primary_review.get("subject_sha256") == evidence_hash
            and primary_review.get("verdict") == "PASS"
            else "BLOCKED"
        )
        if run.get("requires_qa"):
            states["review:adversarial-qa"] = (
                "PASS"
                if isinstance(qa, dict)
                and qa.get("subject_sha256") == evidence_hash
                and qa.get("verdict") == "PASS"
                else "BLOCKED"
            )
        else:
            states["review:adversarial-qa"] = "NOT_REQUIRED"
    else:
        states[primary_review_id] = "NOT_REQUIRED"
        states["review:adversarial-qa"] = "NOT_REQUIRED"
    states["certificate:completion"] = (
        "PASS"
        if core.get("status") == "CERTIFIED"
        else ("READY" if core.get("status") == "READY" else "BLOCKED")
    )

    blocking_paths: list[dict[str, Any]] = []
    task_by_id = {str(task["id"]): task for task in flow.tasks}
    for node in flow.assurance_graph["nodes"]:
        node_id = str(node["id"])
        if node.get("type") != "check" or states[node_id] == "PASS":
            continue
        if node.get("phase") == "task":
            parts = node_id.split(":", 5)
            task_id = parts[2] if len(parts) > 2 else ""
            task = task_by_id.get(task_id)
            criterion_id = (
                str(task["criteria"][0])
                if isinstance(task, dict) and task.get("criteria")
                else None
            )
            path = []
            if criterion_id is not None:
                path.append(f"criterion:{criterion_id}")
            path.extend(
                [
                    f"task:{task_id}",
                    node_id,
                    "evidence:all",
                    "certificate:completion",
                ]
            )
        else:
            path = [node_id, "evidence:all", "certificate:completion"]
        blocking_paths.append(
            {
                "reason": f"check occurrence is {states[node_id]}",
                "path": path,
                "causality": "not-proven",
            }
        )
    if states["evidence:all"] == "PASS" and chain_matches:
        for review_id in (primary_review_id, "review:adversarial-qa"):
            if states[review_id] == "BLOCKED":
                blocking_paths.append(
                    {
                        "reason": f"{review_id} is required for this chain",
                        "path": [
                            "evidence:all",
                            review_id,
                            "certificate:completion",
                        ],
                        "causality": "not-proven",
                    }
                )
    if (
        not blocking_paths
        and states["certificate:completion"] != "PASS"
    ):
        reason = (
            str(core.get("reasons", ["completion is not certified"])[0])
            if core.get("reasons")
            else "completion is not certified"
        )
        blocking_paths.append(
            {
                "reason": reason,
                "path": ["evidence:all", "certificate:completion"],
                "causality": "not-proven",
            }
        )
    blocking_paths.sort(
        key=lambda item: (tuple(item["path"]), str(item["reason"]))
    )
    return {
        "node_states": [
            {"id": node_id, "status": states[node_id]}
            for node_id in sorted(states)
        ],
        "blocking_paths": blocking_paths,
        "primary_blocker": blocking_paths[0] if blocking_paths else None,
    }


def _trace_payload(root: pathlib.Path, plan_argument: str) -> tuple[dict[str, Any], int]:
    flow = _validate_flow(root, plan_argument)
    if flow.errors:
        return {
            "status": "FAIL",
            "plan": str(plan_argument),
            "errors": flow.errors,
            "blocking_paths": [],
        }, 2
    try:
        state = _load_state(root)
    except EZPowersError as exc:
        return {
            "status": "FAIL",
            "plan": flow.plan_rel,
            "errors": [str(exc)],
            "blocking_paths": [],
        }, 2
    core, _ = _status_payload(root, include_graph_summary=False)
    evidence: dict[str, Any] | None = None
    evidence_hash = ""
    if state.get("active_plan") == flow.plan_rel:
        _, _, evidence, evidence_hash, _ = _freshness(
            root,
            flow,
            state=state,
        )
    else:
        core = {
            "status": "INACTIVE",
            "fresh": False,
            "certified": False,
            "reasons": ["plan is not the active resume target"],
        }
    runtime_view = _assurance_runtime_view(
        flow,
        state,
        core,
        evidence,
        evidence_hash,
    )
    payload = {
        "status": "PASS",
        "plan": flow.plan_rel,
        "completion_status": core.get("status"),
        "assurance_graph_sha256": flow.assurance_graph_sha256,
        "graph": flow.assurance_graph,
        **runtime_view,
    }
    if flow.profile.name == PLANNING_PROFILE.name:
        payload["project_profile"] = flow.profile.name
    return payload, 0


def _trace_command(args: argparse.Namespace) -> int:
    root = _runtime_project_root()
    payload, code = _trace_payload(root, args.plan)
    _emit(payload, args.json)
    return code


def _status_payload(
    root: pathlib.Path,
    *,
    include_graph_summary: bool = True,
) -> tuple[dict[str, Any], int]:
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
        _, _, _, _, profile = _validate_config_value(root, config, config_errors)
        if config_errors:
            return {
                "status": "FAIL",
                "fresh": False,
                "active_plan": None,
                "reasons": config_errors,
            }, 2
        payload = {
            "status": "UNCONFIGURED",
            "fresh": False,
            "active_plan": None,
            "reasons": ["no active plan"],
        }
        if profile.name == PLANNING_PROFILE.name:
            payload["project_profile"] = profile.name
        return payload, 0
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
                core_certificate_valid = (
                    _sha256_file(resolved_certificate) == certificate_pointer.get("sha256")
                    and evidence is not None
                    and certificate_pointer.get("evidence_sha256") == evidence_hash
                    and certificate.get("status") == "PASS"
                    and certificate.get("schema_version")
                    == _flow_evidence_schema_version(flow)
                    and certificate.get("plan_path") == evidence.get("plan_path")
                    and certificate.get("plan_sha256") == evidence.get("plan_sha256")
                    and certificate.get("spec_path") == evidence.get("spec_path")
                    and certificate.get("spec_sha256") == evidence.get("spec_sha256")
                    and certificate.get("config_sha256") == evidence.get("config_sha256")
                    and certificate.get("installation") == evidence.get("installation")
                    and certificate.get("workspace") == evidence.get("workspace")
                    and certificate.get("evidence_path") == evidence.get("evidence_path")
                    and certificate.get("evidence_sha256") == evidence_hash
                    and (
                        not _flow_graph_bound(flow)
                        or certificate.get("assurance_graph_sha256")
                        == evidence.get("assurance_graph_sha256")
                        == flow.assurance_graph_sha256
                    )
                    and (
                        flow.profile.name != PLANNING_PROFILE.name
                        or (
                            certificate.get("project_profile")
                            == evidence.get("project_profile")
                            == flow.profile.name
                            and certificate.get("artifacts")
                            == evidence.get("artifacts")
                        )
                    )
                )
                chain_certificate_valid = True
                if (
                    evidence is not None
                    and isinstance(evidence.get("chain"), dict)
                ):
                    current_gates, gate_reasons = _chain_certification_gates(
                        root,
                        state,
                        evidence_hash=evidence_hash,
                        evidence=evidence,
                    )
                    if gate_reasons:
                        reasons.extend(gate_reasons)
                    chain_certificate_valid = (
                        not gate_reasons
                        and certificate.get("chain") == evidence.get("chain")
                        and certificate.get("gates") == current_gates
                    )
                    if not chain_certificate_valid and not gate_reasons:
                        reasons.append(
                            "certificate tamper detected: harness-chain gate "
                            "binding mismatch"
                        )
                certified = core_certificate_valid and chain_certificate_valid
                if not core_certificate_valid:
                    reasons.append("certificate tamper detected: certificate binding mismatch")
            except (EZPowersError, ValueError) as exc:
                reasons.append(f"certificate pointer is invalid: {exc}")
        else:
            reasons.append("certificate pointer is invalid")
    elif fresh and certificate_pointer is not None:
        reasons.append("certificate pointer is invalid")
    payload = {
        "status": "CERTIFIED" if fresh and certified else ("READY" if fresh else "STALE"),
        "fresh": fresh,
        "certified": certified,
        "active_plan": active,
        "reasons": reasons,
        "task_evidence": task_evidence,
        "orphan_task_evidence": orphan_task_evidence,
    }
    if flow.profile.name == PLANNING_PROFILE.name:
        payload["project_profile"] = flow.profile.name
        payload["artifacts"] = (
            evidence.get("artifacts") if isinstance(evidence, dict) else None
        )
    if include_graph_summary:
        view = _assurance_runtime_view(
            flow,
            state,
            payload,
            evidence,
            evidence_hash,
        )
        payload["assurance_graph_sha256"] = flow.assurance_graph_sha256
        payload["primary_blocker"] = view["primary_blocker"]
    return payload, 0


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
    install.add_argument(
        "--project-profile",
        choices=tuple(sorted(PROJECT_PROFILE_POLICIES)),
        help=(
            "Select the project profile on first setup or explicitly switch "
            "an existing project; omitted projects retain software behavior"
        ),
    )
    install.add_argument("--enable-hooks", choices=("none", "claude", "codex", "both"), default="none")
    install.add_argument(
        "--enable-wiki-hooks",
        choices=("none", "claude", "codex", "both"),
        default="none",
        help="Install the opt-in SessionEnd wiki capture hook",
    )
    install.set_defaults(handler=_install)

    docs = subparsers.add_parser(
        "docs",
        help="Preview, apply, and lint the repository documentation graph",
    )
    docs_subparsers = docs.add_subparsers(dest="docs_command", required=True)

    docs_preview = docs_subparsers.add_parser(
        "preview",
        help="Validate a staged documentation bundle and report its exact changes",
    )
    docs_preview.add_argument("--bundle", required=True)
    docs_preview.add_argument("--json", action="store_true")
    docs_preview.set_defaults(handler=_docs_preview_command)

    docs_apply = docs_subparsers.add_parser(
        "apply",
        help="Apply a previously previewed documentation bundle",
    )
    docs_apply.add_argument("--bundle", required=True)
    docs_apply.add_argument("--preview-sha256", required=True)
    docs_apply.add_argument("--force", action="store_true")
    docs_apply.add_argument("--json", action="store_true")
    docs_apply.set_defaults(handler=_docs_apply_command)

    docs_lint = docs_subparsers.add_parser(
        "lint",
        help="Validate the managed documentation registry and graph",
    )
    docs_lint.add_argument("--json", action="store_true")
    docs_lint.set_defaults(handler=_docs_lint_command)

    docs_status = docs_subparsers.add_parser(
        "status",
        help="Show documentation bootstrap and lint status",
    )
    docs_status.add_argument("--json", action="store_true")
    docs_status.set_defaults(handler=_docs_status_command)

    wiki = subparsers.add_parser(
        "wiki",
        help="Manage local, untracked project knowledge",
    )
    wiki_subparsers = wiki.add_subparsers(dest="wiki_command", required=True)

    wiki_add = wiki_subparsers.add_parser("add", help="Add a local wiki candidate")
    wiki_add.add_argument("--input", required=True, help="JSON object describing the page")
    wiki_add.add_argument("--json", action="store_true")
    wiki_add.set_defaults(handler=_wiki_add_command)

    wiki_read = wiki_subparsers.add_parser("read", help="Read one local wiki page")
    wiki_read.add_argument("--id", required=True)
    wiki_read.add_argument("--json", action="store_true")
    wiki_read.set_defaults(handler=_wiki_read_command)

    wiki_list = wiki_subparsers.add_parser("list", help="List local wiki pages")
    wiki_list.add_argument("--input", help="Optional JSON filters")
    wiki_list.add_argument("--json", action="store_true")
    wiki_list.set_defaults(handler=_wiki_list_command)

    wiki_query = wiki_subparsers.add_parser(
        "query",
        help="Search wiki titles, tags, and bodies, including CJK text",
    )
    wiki_query.add_argument("--input", required=True, help="JSON query and optional filters")
    wiki_query.add_argument("--json", action="store_true")
    wiki_query.set_defaults(handler=_wiki_query_command)

    wiki_lint = wiki_subparsers.add_parser("lint", help="Validate local wiki storage")
    wiki_lint.add_argument("--json", action="store_true")
    wiki_lint.set_defaults(handler=_wiki_lint_command)

    wiki_refresh = wiki_subparsers.add_parser(
        "refresh",
        help="Regenerate the local wiki index",
    )
    wiki_refresh.add_argument("--json", action="store_true")
    wiki_refresh.set_defaults(handler=_wiki_refresh_command)

    wiki_promote = wiki_subparsers.add_parser(
        "promote",
        help="Bind a wiki page to an already-authored canonical document",
    )
    wiki_promote.add_argument("--input", required=True, help="JSON id and target")
    wiki_promote.add_argument("--confirm", action="store_true")
    wiki_promote.add_argument("--preview-sha256")
    wiki_promote.add_argument("--json", action="store_true")
    wiki_promote.set_defaults(handler=_wiki_promote_command)

    wiki_prune = wiki_subparsers.add_parser(
        "prune",
        help="Back up and remove explicitly selected unpromoted pages",
    )
    wiki_prune.add_argument("--input", required=True, help="JSON ids array")
    wiki_prune.add_argument("--confirm", action="store_true")
    wiki_prune.add_argument("--preview-sha256")
    wiki_prune.add_argument("--json", action="store_true")
    wiki_prune.set_defaults(handler=_wiki_prune_command)

    wiki_capture = wiki_subparsers.add_parser(
        "capture",
        help="Best-effort allowlisted SessionEnd capture",
    )
    wiki_capture.add_argument("--host", required=True, choices=("claude", "codex"))
    wiki_capture.set_defaults(handler=_wiki_capture_command)

    chain = subparsers.add_parser(
        "chain",
        help="Configure and run a project-local verified harness chain",
    )
    chain_subparsers = chain.add_subparsers(
        dest="chain_command",
        required=True,
    )

    chain_config = chain_subparsers.add_parser(
        "config",
        help="Preview, apply, or inspect project chain configuration",
    )
    chain_config_subparsers = chain_config.add_subparsers(
        dest="chain_config_command",
        required=True,
    )
    chain_config_preview = chain_config_subparsers.add_parser("preview")
    chain_config_preview.add_argument("--bundle", required=True)
    chain_config_preview.add_argument("--json", action="store_true")
    chain_config_preview.set_defaults(handler=_chain_config_preview_command)
    chain_config_apply = chain_config_subparsers.add_parser("apply")
    chain_config_apply.add_argument("--bundle", required=True)
    chain_config_apply.add_argument("--preview-sha256", required=True)
    chain_config_apply.add_argument("--json", action="store_true")
    chain_config_apply.set_defaults(handler=_chain_config_apply_command)
    chain_config_status = chain_config_subparsers.add_parser("status")
    chain_config_status.add_argument("--json", action="store_true")
    chain_config_status.set_defaults(handler=_chain_config_status_command)

    chain_run = chain_subparsers.add_parser(
        "run",
        help="Preview, approve, or inspect one feature chain run",
    )
    chain_run_subparsers = chain_run.add_subparsers(
        dest="chain_run_command",
        required=True,
    )
    chain_run_preview = chain_run_subparsers.add_parser("preview")
    chain_run_preview.add_argument("--bundle", required=True)
    chain_run_preview.add_argument("--json", action="store_true")
    chain_run_preview.set_defaults(handler=_chain_run_preview_command)
    chain_run_apply = chain_run_subparsers.add_parser("apply")
    chain_run_apply.add_argument("--bundle", required=True)
    chain_run_apply.add_argument("--preview-sha256", required=True)
    chain_run_apply.add_argument("--force", action="store_true")
    chain_run_apply.add_argument("--json", action="store_true")
    chain_run_apply.set_defaults(handler=_chain_run_apply_command)
    chain_run_status = chain_run_subparsers.add_parser("status")
    chain_run_status.add_argument("--json", action="store_true")
    chain_run_status.set_defaults(handler=_chain_run_status_command)

    chain_activate = chain_subparsers.add_parser(
        "activate",
        help="Bind an approved run to its single host-native loop authority",
    )
    chain_activate.add_argument("--host", required=True, choices=("claude", "codex"))
    chain_activate.add_argument(
        "--authority",
        required=True,
        choices=("stop-hook", "native-goal"),
    )
    chain_activate.add_argument("--objective-sha256", required=True)
    chain_activate.add_argument("--json", action="store_true")
    chain_activate.set_defaults(handler=_chain_activate_command)

    chain_gate = chain_subparsers.add_parser(
        "gate",
        help="Create a challenge for a host-native independent reviewer",
    )
    chain_gate_subparsers = chain_gate.add_subparsers(
        dest="chain_gate_command",
        required=True,
    )
    chain_gate_begin = chain_gate_subparsers.add_parser("begin")
    chain_gate_begin.add_argument(
        "--kind",
        required=True,
        choices=tuple(sorted(CHAIN_GATE_KINDS)),
    )
    chain_gate_begin.add_argument("--subject-sha256")
    chain_gate_begin.add_argument("--json", action="store_true")
    chain_gate_begin.set_defaults(handler=_chain_gate_begin_command)

    chain_hook = chain_subparsers.add_parser(
        "hook",
        help="Handle one thin host event for the active chain",
    )
    chain_hook.add_argument("--host", required=True, choices=("claude", "codex"))
    chain_hook.set_defaults(handler=_chain_hook_command)

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

    trace = subparsers.add_parser(
        "trace",
        help="Show the derived assurance graph and current blocking paths",
    )
    trace.add_argument("--plan", required=True)
    trace.add_argument("--json", action="store_true")
    trace.set_defaults(handler=_trace_command)

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
        if bool(getattr(args, "json", False)):
            print(
                json.dumps(
                    {
                        "status": "CONFLICT",
                        "errors": [str(exc)],
                        "reasons": [str(exc)],
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
        else:
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
