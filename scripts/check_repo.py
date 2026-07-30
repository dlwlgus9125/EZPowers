#!/usr/bin/env python3
"""Cross-platform structural gate for the EZPowers v5.4 repository surface."""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import subprocess
import sys
from collections.abc import Iterable
from urllib.parse import unquote


PLUGIN_SKILLS = frozenset(
    {
        "codebase-design",
        "deep-interview",
        "design-architecture",
        "diagnose",
        "explain-with-evidence",
        "execute",
        "frontend-design",
        "hud",
        "improve-codebase-architecture",
        "prepare-execute",
        "setup",
        "spec",
        "wiki",
        "harness-chain",
    }
)
PROJECT_SKILLS = PLUGIN_SKILLS - {"hud"}
RETAINED_SKILLS = PLUGIN_SKILLS
EXPLICIT_ONLY_SKILLS = frozenset(
    {
        "design-architecture",
        "execute",
        "harness-chain",
        "hud",
        "improve-codebase-architecture",
        "prepare-execute",
        "setup",
        "spec",
    }
)
ALLOWED_SKILL_FRONTMATTER = frozenset(
    {
        "agent",
        "allowed-tools",
        "argument-hint",
        "compatibility",
        "context",
        "description",
        "disable-model-invocation",
        "hooks",
        "license",
        "metadata",
        "model",
        "name",
        "user-invocable",
    }
)

REMOVED_SKILLS = frozenset(
    {
        "caveman",
        "choice-execute",
        "deploy",
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

REMOVED_LIVE_DIRECTORIES = (
    "agents",
    "evals",
    "harness-kit",
    ".harness",
    "phases",
)

OBSOLETE_SCRIPTS = (
    "context-injector.py",
    "harness-certify.ps1",
    "harness-common.ps1",
    "harness-convert.ps1",
    "harness-doctor.ps1",
    "harness-gate.ps1",
    "harness-phase.ps1",
    "harness-resume-proof.ps1",
    "harness-run.ps1",
    "harness-smoke.ps1",
    "hashline-anchor.py",
    "lightpath-gate.ps1",
    "model-router.py",
    "shared.py",
    "smoke-plugin.ps1",
    "statusline.py",
    "verify-step.py",
)

OBSOLETE_REFERENCES = (
    "app-delivery-contract.md",
    "config.md",
    "conventions.md",
    "dispatch-protocol.md",
    "domain-language.md",
    "harness-execution-contract.md",
    "harness-kit-contract.md",
    "model-routing-contract.md",
    "pipeline-audit-contract.md",
    "project-structure.md",
    "protocol.md",
    "schema.md",
    "testing-methodology.md",
)

PROJECT_KIT_MANIFEST = pathlib.Path("project-kit/v5.4.0/manifest.json")
PROJECT_KIT_VERIFIER = pathlib.Path("scripts/verify-harness-kit.py")

MARKDOWN_LINK_RE = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
REPO_PATH_RE = re.compile(
    r"(?<![A-Za-z0-9_./-])"
    r"(?P<path>(?:docs/reference|skills|scripts|agents|project-kit|harness-kit)/"
    r"[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)*\."
    r"(?:md|py|ps1|json|ya?ml|toml|sh))"
)

LEGACY_PATTERNS = (
    (".harness", re.compile(r"(?<![A-Za-z0-9_-])\.harness(?:[\\/]|\b)")),
    ("phases/", re.compile(r"(?<![A-Za-z0-9_-])phases[\\/]")),
    ("harness.root", re.compile(r"\bharness\.root\b")),
    ("external execute.py", re.compile(r"\bexecute\.py\b")),
    ("EasyPowersHarness", re.compile(r"\bEasyPowersHarness\b", re.IGNORECASE)),
    ("choice-execute", re.compile(r"\bchoice-execute\b")),
    ("internal pipeline audit", re.compile(r"\binternal pipeline audit\b", re.IGNORECASE)),
    ("workflow-runner", re.compile(r"\bworkflow-runner\b")),
    ("Path 2", re.compile(r"\bPath\s+2\b", re.IGNORECASE)),
)

VALIDATOR_REFERENCE_EXEMPTIONS = {
    pathlib.Path("scripts/check_repo.py"),
    pathlib.Path("scripts/plugin_smoke.py"),
}


def _read_text(path: pathlib.Path, errors: list[str], label: str) -> str | None:
    try:
        return path.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeError) as exc:
        errors.append(f"{label}: cannot read {path}: {exc}")
        return None


def _read_json(path: pathlib.Path, errors: list[str], label: str) -> object | None:
    text = _read_text(path, errors, label)
    if text is None:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        errors.append(f"{label}: invalid JSON in {path}: {exc}")
        return None


def _frontmatter(text: str) -> dict[str, str] | None:
    match = re.match(r"^\ufeff?---\s*\r?\n(.*?)\r?\n---(?:\r?\n|$)", text, re.DOTALL)
    if not match:
        return None
    lines = match.group(1).splitlines()
    result: dict[str, str] = {}
    index = 0
    while index < len(lines):
        field = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", lines[index])
        if not field:
            index += 1
            continue
        key, value = field.groups()
        if value in {"|", ">"}:
            collected: list[str] = []
            index += 1
            while index < len(lines) and (not lines[index] or lines[index][0].isspace()):
                if lines[index].strip():
                    collected.append(lines[index].strip())
                index += 1
            result[key] = " ".join(collected)
            continue
        result[key] = value.strip().strip("\"'")
        index += 1
    return result


def _yaml_value(text: str, key: str) -> str | None:
    match = re.search(rf"(?m)^\s{{2}}{re.escape(key)}:\s*(.+?)\s*$", text)
    if not match:
        return None
    return match.group(1).strip().strip("\"'")


def _validate_skill_inventory(root: pathlib.Path, errors: list[str]) -> None:
    skills_root = root / "skills"
    if not skills_root.is_dir():
        errors.append("skill inventory: missing skills directory")
        return

    actual = {
        path.name
        for path in skills_root.iterdir()
        if path.is_dir() and path.name != "__pycache__"
    }
    missing = sorted(RETAINED_SKILLS - actual)
    extra = sorted(actual - RETAINED_SKILLS)
    if missing or extra:
        errors.append(f"skill inventory mismatch: missing={missing}, extra={extra}")

    for name in sorted(RETAINED_SKILLS):
        skill_dir = skills_root / name
        skill_path = skill_dir / "SKILL.md"
        metadata_path = skill_dir / "agents" / "openai.yaml"

        if not skill_path.is_file():
            errors.append(f"skills/{name}/SKILL.md: missing retained skill body")
        else:
            text = _read_text(skill_path, errors, "skill metadata")
            if text is not None:
                front = _frontmatter(text)
                if front is None:
                    errors.append(f"skills/{name}/SKILL.md: missing or malformed frontmatter")
                else:
                    unknown = sorted(set(front) - ALLOWED_SKILL_FRONTMATTER)
                    if unknown:
                        errors.append(
                            f"skills/{name}/SKILL.md: unsupported frontmatter "
                            f"fields {unknown}"
                        )
                    if front.get("name") != name:
                        errors.append(
                            f"skills/{name}/SKILL.md: frontmatter name must be {name!r}"
                        )
                    if not front.get("description"):
                        errors.append(f"skills/{name}/SKILL.md: missing description")
                    disabled = front.get(
                        "disable-model-invocation",
                        "false",
                    ).lower()
                    if disabled not in {"true", "false"}:
                        errors.append(
                            f"skills/{name}/SKILL.md: "
                            "disable-model-invocation must be true or false"
                        )
                    expected_disabled = name in EXPLICIT_ONLY_SKILLS
                    if (disabled == "true") != expected_disabled:
                        errors.append(
                            f"skills/{name}/SKILL.md: Claude invocation policy "
                            f"must be disable-model-invocation={str(expected_disabled).lower()}"
                        )

        if not metadata_path.is_file():
            errors.append(f"skills/{name}/agents/openai.yaml: missing Codex metadata")
            continue
        metadata = _read_text(metadata_path, errors, "Codex skill metadata")
        if metadata is None:
            continue
        if not re.search(r"(?m)^interface:\s*$", metadata):
            errors.append(f"skills/{name}/agents/openai.yaml: missing interface")
        if not re.search(r"(?m)^policy:\s*$", metadata):
            errors.append(f"skills/{name}/agents/openai.yaml: missing policy")
        for field in ("display_name", "short_description", "default_prompt"):
            if not _yaml_value(metadata, field):
                errors.append(f"skills/{name}/agents/openai.yaml: missing {field}")
        prompt = _yaml_value(metadata, "default_prompt") or ""
        plugin_invocation = f"$ezpowers:{name}"
        if prompt and plugin_invocation not in prompt:
            errors.append(
                f"skills/{name}/agents/openai.yaml: default_prompt must invoke "
                f"{plugin_invocation}"
            )
        implicit = _yaml_value(metadata, "allow_implicit_invocation")
        if implicit not in {"true", "false"}:
            errors.append(
                f"skills/{name}/agents/openai.yaml: allow_implicit_invocation must be true or false"
            )
        expected_implicit = name not in EXPLICIT_ONLY_SKILLS
        if implicit in {"true", "false"} and (implicit == "true") != expected_implicit:
            errors.append(
                f"skills/{name}/agents/openai.yaml: Codex invocation policy "
                f"must be allow_implicit_invocation={str(expected_implicit).lower()}"
            )

        project_metadata_path = skill_dir / "agents" / "project-openai.yaml"
        if name not in PROJECT_SKILLS:
            if project_metadata_path.exists():
                errors.append(
                    f"skills/{name}/agents/project-openai.yaml: plugin-only "
                    "skill must not have project metadata"
                )
            continue
        if not project_metadata_path.is_file():
            errors.append(
                f"skills/{name}/agents/project-openai.yaml: missing project metadata"
            )
            continue
        project_metadata = _read_text(
            project_metadata_path,
            errors,
            "project Codex skill metadata",
        )
        if project_metadata is None:
            continue
        for field in ("display_name", "short_description"):
            if _yaml_value(project_metadata, field) != _yaml_value(metadata, field):
                errors.append(
                    f"skills/{name}/agents/project-openai.yaml: {field} "
                    "must match plugin metadata"
                )
        project_prompt = _yaml_value(project_metadata, "default_prompt") or ""
        expected_project_prompt = prompt.replace(plugin_invocation, f"${name}")
        if project_prompt != expected_project_prompt or plugin_invocation in project_prompt:
            errors.append(
                f"skills/{name}/agents/project-openai.yaml: default_prompt "
                f"must use project-local ${name} invocation"
            )
        project_implicit = _yaml_value(
            project_metadata,
            "allow_implicit_invocation",
        )
        if project_implicit != implicit:
            errors.append(
                f"skills/{name}/agents/project-openai.yaml: invocation policy "
                "must match plugin metadata"
            )


def _base_version(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    match = re.fullmatch(r"(\d+\.\d+\.\d+)(?:\+codex\.[A-Za-z0-9.-]+)?", value)
    return match.group(1) if match else None


def _validate_plugin_manifests(root: pathlib.Path, errors: list[str]) -> None:
    claude_path = root / ".claude-plugin" / "plugin.json"
    market_path = root / ".claude-plugin" / "marketplace.json"
    codex_path = root / ".codex-plugin" / "plugin.json"
    claude = _read_json(claude_path, errors, "plugin manifest")
    market = _read_json(market_path, errors, "plugin manifest")
    codex = _read_json(codex_path, errors, "plugin manifest")
    if not all(isinstance(item, dict) for item in (claude, market, codex)):
        return
    assert isinstance(claude, dict)
    assert isinstance(market, dict)
    assert isinstance(codex, dict)

    market_plugins = market.get("plugins")
    market_plugin = (
        market_plugins[0]
        if isinstance(market_plugins, list)
        and len(market_plugins) == 1
        and isinstance(market_plugins[0], dict)
        else None
    )
    if market_plugin is None:
        errors.append("plugin manifest parity: marketplace must contain one plugin")
        return

    versions = {
        "claude": _base_version(claude.get("version")),
        "marketplace": _base_version(market_plugin.get("version")),
        "codex": _base_version(codex.get("version")),
    }
    if any(value is None for value in versions.values()):
        errors.append(f"plugin manifest parity: invalid versions {versions}")
    elif len(set(versions.values())) != 1:
        errors.append(f"plugin manifest parity: version mismatch {versions}")
    elif not next(iter(versions.values())).startswith("5."):
        errors.append(f"plugin manifest parity: v5 required, found {versions}")

    for label, manifest in (("Claude", claude), ("Codex", codex)):
        if manifest.get("name") != "ezpowers":
            errors.append(f"plugin manifest parity: {label} name must be ezpowers")
    if market_plugin.get("name") != "ezpowers" or market_plugin.get("source") != "./":
        errors.append("plugin manifest parity: marketplace entry must be ezpowers from ./")
    if codex.get("skills") != "./skills/":
        errors.append("plugin manifest parity: Codex skills must be ./skills/")

    interface = codex.get("interface")
    long_description = (
        interface.get("longDescription", "") if isinstance(interface, dict) else ""
    )
    mentioned = set(re.findall(r"\bezpowers:([a-z0-9-]+)\b", str(long_description)))
    if mentioned != PLUGIN_SKILLS:
        errors.append(
            "plugin manifest parity: Codex longDescription skill inventory "
            f"must be {sorted(PLUGIN_SKILLS)}, found {sorted(mentioned)}"
        )


def _result_tail(result: subprocess.CompletedProcess[str]) -> str:
    text = "\n".join(part.strip() for part in (result.stdout, result.stderr) if part.strip())
    lines = text.splitlines()
    return " | ".join(lines[-8:]) if lines else "no output"


def _validate_project_kit(root: pathlib.Path, errors: list[str]) -> None:
    manifest = root / PROJECT_KIT_MANIFEST
    verifier = root / PROJECT_KIT_VERIFIER
    if not manifest.is_file():
        errors.append(f"project-kit manifest missing: {PROJECT_KIT_MANIFEST.as_posix()}")
        return
    if not verifier.is_file():
        errors.append(f"project-kit verifier missing: {PROJECT_KIT_VERIFIER.as_posix()}")
        return
    try:
        result = subprocess.run(
            [
                sys.executable,
                str(verifier),
                "--repo-root",
                str(root),
                "--manifest",
                PROJECT_KIT_MANIFEST.as_posix(),
            ],
            cwd=root,
            text=True,
            capture_output=True,
            timeout=60,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        errors.append(f"project-kit verifier failed to run: {exc}")
        return
    if result.returncode != 0:
        errors.append(
            f"project-kit verifier failed (exit {result.returncode}): {_result_tail(result)}"
        )


def _validate_removed_components(root: pathlib.Path, errors: list[str]) -> None:
    for relative in REMOVED_LIVE_DIRECTORIES:
        candidate = root / relative
        ignored = False
        if candidate.exists() and (root / ".git").exists():
            result = subprocess.run(
                ["git", "check-ignore", "-q", "--", relative],
                cwd=root,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
            ignored = result.returncode == 0
        if candidate.exists() and not ignored:
            errors.append(f"removed live directory remains: {relative}")
    for name in sorted(REMOVED_SKILLS):
        if (root / "skills" / name).exists():
            errors.append(f"removed skill directory remains: skills/{name}")
    for name in OBSOLETE_SCRIPTS:
        if (root / "scripts" / name).exists():
            errors.append(f"obsolete script remains: scripts/{name}")
    for name in OBSOLETE_REFERENCES:
        if (root / "docs" / "reference" / name).exists():
            errors.append(f"obsolete reference remains: docs/reference/{name}")


def _excluded_path(relative: pathlib.Path) -> bool:
    parts = relative.parts
    if not parts:
        return False
    if parts[0] in {".git", ".playwright-mcp", ".pytest-cache", "evals"}:
        return True
    if len(parts) >= 2 and parts[0] == "docs" and parts[1] in {"archive", "reports"}:
        return True
    if "__pycache__" in parts:
        return True
    return False


def _live_markdown_files(root: pathlib.Path) -> list[pathlib.Path]:
    return sorted(
        path
        for path in root.rglob("*.md")
        if path.is_file() and not _excluded_path(path.relative_to(root))
    )


def _strip_fenced_blocks(text: str) -> str:
    def blank(match: re.Match[str]) -> str:
        return "\n" * match.group(0).count("\n")

    return re.sub(r"```.*?```", blank, text, flags=re.DOTALL)


def _link_target(raw: str) -> str:
    value = raw.strip()
    if value.startswith("<") and ">" in value:
        value = value[1 : value.index(">")]
    else:
        value = value.split(maxsplit=1)[0] if value else ""
    return unquote(value).split("#", 1)[0].split("?", 1)[0]


def _skip_relative_target(target: str) -> bool:
    lowered = target.lower()
    return (
        not target
        or target.startswith("#")
        or target.startswith("/")
        or re.match(r"^[a-z]:[\\/]", target, re.IGNORECASE) is not None
        or "://" in target
        or lowered.startswith(("mailto:", "app:", "data:"))
        or any(token in target for token in ("<", ">", "{", "}", "*", "$"))
    )


def _resolve_markdown_target(
    root: pathlib.Path, source: pathlib.Path, target: str
) -> pathlib.Path:
    normalized = target.replace("\\", "/")
    repo_prefixes = (
        "docs/",
        "skills/",
        "scripts/",
        "agents/",
        "project-kit/",
        "harness-kit/",
        ".claude-plugin/",
        ".codex-plugin/",
        ".ezpowers/",
    )
    if normalized.startswith(repo_prefixes) or normalized in {
        "AGENTS.md",
        "CLAUDE.md",
        "PROGRESS.md",
        "feature_list.json",
    }:
        candidate = root / normalized
    else:
        candidate = source.parent / normalized
    if not candidate.exists():
        line_suffix = re.match(r"^(.*?):\d+$", str(candidate))
        if line_suffix:
            candidate = pathlib.Path(line_suffix.group(1))
    return candidate


def _validate_markdown_paths(root: pathlib.Path, errors: list[str]) -> None:
    seen: set[tuple[str, str, str]] = set()
    for path in _live_markdown_files(root):
        relative = path.relative_to(root).as_posix()
        text = _read_text(path, errors, "markdown path scan")
        if text is None:
            continue
        content = _strip_fenced_blocks(text)
        for match in MARKDOWN_LINK_RE.finditer(content):
            target = _link_target(match.group(1))
            if _skip_relative_target(target):
                continue
            resolved = _resolve_markdown_target(root, path, target)
            if not resolved.exists():
                key = (relative, "link", target)
                if key not in seen:
                    seen.add(key)
                    errors.append(f"dead markdown link in {relative}: {target}")

        for match in REPO_PATH_RE.finditer(content):
            target = match.group("path")
            resolved = root / target
            if not resolved.exists():
                key = (relative, "path", target)
                if key not in seen:
                    seen.add(key)
                    errors.append(f"dead repository path in {relative}: {target}")


def _live_contract_and_steering_files(root: pathlib.Path) -> list[pathlib.Path]:
    candidates: set[pathlib.Path] = set()
    for pattern in ("*.md", "*.json"):
        candidates.update(path for path in root.glob(pattern) if path.is_file())
    for directory, suffixes in (
        ("skills", {".md", ".yaml", ".yml"}),
        ("docs/reference", {".md"}),
        ("docs/product", {".md"}),
        ("docs/decisions", {".md"}),
        ("scripts", {".py", ".ps1"}),
        ("project-kit", {".md", ".json", ".py", ".yaml", ".yml"}),
        (".claude-plugin", {".json"}),
        (".codex-plugin", {".json"}),
        (".githooks", {""}),
    ):
        base = root / directory
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if path.is_file() and (path.suffix in suffixes or "" in suffixes):
                relative = path.relative_to(root)
                if not _excluded_path(relative):
                    candidates.add(path)
    return sorted(candidates)


def _explicit_retired_reference(lines: list[str], index: int) -> bool:
    window = " ".join(lines[max(0, index - 2) : min(len(lines), index + 3)])
    retired = bool(
        re.search(
            r"\b(?:remove(?:d|s)?|retire(?:d|s)?|replac(?:e|ed|es)|"
            r"do not reintroduce|no longer|is not part)\b",
            window,
            re.IGNORECASE,
        )
    )
    return retired


def _validate_obsolete_references(root: pathlib.Path, errors: list[str]) -> None:
    obsolete_name_patterns = tuple(
        (f"obsolete script {name}", re.compile(re.escape(name)))
        for name in OBSOLETE_SCRIPTS
    ) + tuple(
        (f"obsolete reference {name}", re.compile(re.escape(name)))
        for name in OBSOLETE_REFERENCES
    ) + tuple(
        (
            f"removed skill {name}",
            re.compile(
                rf"(?:\bskills[\\/]{re.escape(name)}\b|"
                rf"(?<![A-Za-z0-9_-])(?:\$|/)(?:ezpowers:)?"
                rf"{re.escape(name)}\b)"
            ),
        )
        for name in REMOVED_SKILLS
    )
    patterns = LEGACY_PATTERNS + obsolete_name_patterns
    seen: set[tuple[str, str]] = set()
    for path in _live_contract_and_steering_files(root):
        relative_path = path.relative_to(root)
        if relative_path in VALIDATOR_REFERENCE_EXEMPTIONS:
            continue
        text = _read_text(path, errors, "obsolete reference scan")
        if text is None:
            continue
        lines = text.splitlines()
        for index, line in enumerate(lines):
            for label, pattern in patterns:
                if not pattern.search(line):
                    continue
                if _explicit_retired_reference(lines, index):
                    continue
                key = (relative_path.as_posix(), label)
                if key in seen:
                    continue
                seen.add(key)
                errors.append(
                    f"obsolete live reference in {relative_path.as_posix()}:{index + 1}: {label}"
                )


def _run_tests(root: pathlib.Path, errors: list[str]) -> None:
    try:
        result = subprocess.run(
            [sys.executable, "-m", "unittest", "discover", "-s", "tests"],
            cwd=root,
            text=True,
            capture_output=True,
            timeout=900,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        errors.append(f"test suite failed to run: {exc}")
        return
    if result.returncode != 0:
        errors.append(f"test suite failed (exit {result.returncode}): {_result_tail(result)}")


def _dedupe(items: Iterable[str]) -> list[str]:
    return list(dict.fromkeys(items))


def validate_repository(root: pathlib.Path, *, with_tests: bool = False) -> list[str]:
    root = root.resolve()
    errors: list[str] = []
    _validate_skill_inventory(root, errors)
    _validate_plugin_manifests(root, errors)
    _validate_project_kit(root, errors)
    _validate_removed_components(root, errors)
    _validate_markdown_paths(root, errors)
    _validate_obsolete_references(root, errors)
    if with_tests:
        _run_tests(root, errors)
    return _dedupe(errors)


def main(argv: list[str] | None = None) -> int:
    default_root = pathlib.Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=str(default_root))
    parser.add_argument(
        "--with-tests",
        action="store_true",
        help="Run python -m unittest discover -s tests after structural checks.",
    )
    args = parser.parse_args(argv)

    errors = validate_repository(pathlib.Path(args.repo_root), with_tests=args.with_tests)
    if errors:
        for error in errors:
            print(f"[FAIL] {error}")
        print(f"check-repo: FAIL ({len(errors)} issue(s))")
        return min(len(errors), 255)
    print("check-repo: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
