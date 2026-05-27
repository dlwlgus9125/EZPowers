#!/usr/bin/env python3
"""Detect frontend visual readiness lanes without installing visual tooling.

This runner is a non-installing frontend readiness gate. It distinguishes
project-local tool availability from lanes that are actually hard-gated, so a
repo with ordinary browser e2e tooling is not blocked unless screenshot or
visual-baseline evidence is present or explicitly planned.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
from typing import Any, Iterable


SCHEMA_VERSION = 2
DEFAULT_DESIGN_ARTIFACT = "docs/ux/frontend-design.md"
MAX_SOURCE_SCAN_FILES = 2500
SOURCE_EXTENSIONS = {
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".mjs",
    ".cjs",
    ".vue",
    ".svelte",
}
SKIP_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".next",
    ".nuxt",
    ".cache",
    ".turbo",
    ".venv",
    "coverage",
    "dist",
    "build",
    "node_modules",
    "plugins",
    "target",
}

COMPONENT_ISOLATION_TOOLS = ("storybook", "ladle", "histoire")
PLAYWRIGHT_TOOLS = ("playwright", "@playwright/test")
VISUAL_DIFF_TOOLS = (
    "chromatic",
    "@chromatic-com/storybook",
    "percy",
    "@percy/cli",
    "@percy/playwright",
    "loki",
    "reg-suit",
    "backstopjs",
    "argos",
    "@argos-ci/cli",
    "applitools",
    "@applitools/eyes-playwright",
    "jest-image-snapshot",
    "pixelmatch",
    "lost-pixel",
    "@lost-pixel/cli",
    "visual-regression",
)
NEGATION_RE = re.compile(
    r"\b(no|not|never|without|skip|skipped|avoid|missing|lacks|absent|pending|todo)\b"
    r"|do not|don't|not a prerequisite|not required|no need",
    re.I,
)


def read_text(path: pathlib.Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""


def relpath(project_root: pathlib.Path, path: pathlib.Path) -> str:
    try:
        return path.resolve().relative_to(project_root.resolve()).as_posix()
    except ValueError:
        return str(path)


def load_json(path: pathlib.Path, warnings: list[str] | None = None) -> dict[str, Any]:
    if not path.exists():
        return {}
    text = read_text(path)
    if not text:
        return {}
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        if warnings is not None:
            warnings.append(f"Invalid JSON ignored: {path} ({exc.msg})")
        return {}
    if not isinstance(data, dict):
        if warnings is not None:
            warnings.append(f"JSON root is not an object: {path}")
        return {}
    return data


def package_sections(data: dict[str, Any]) -> tuple[dict[str, str], dict[str, str]]:
    scripts = data.get("scripts", {})
    if not isinstance(scripts, dict):
        scripts = {}
    deps: dict[str, str] = {}
    for key in ("dependencies", "devDependencies", "peerDependencies", "optionalDependencies"):
        section = data.get(key, {})
        if isinstance(section, dict):
            deps.update({str(name): str(version) for name, version in section.items()})
    return ({str(k): str(v) for k, v in scripts.items()}, deps)


def evidence_item(kind: str, value: str, path: str = "") -> dict[str, str]:
    item = {"kind": kind, "value": value}
    if path:
        item["path"] = path
    return item


def has_any(items: list[dict[str, str]]) -> bool:
    return bool(items)


def non_negated(line: str) -> bool:
    return not NEGATION_RE.search(line)


def tool_token_pattern(tool: str) -> re.Pattern[str]:
    escaped = re.escape(tool)
    return re.compile(rf"(^|[^a-z0-9@/_-]){escaped}($|[^a-z0-9@/_-])", re.I)


def text_has_tool(text: str, tools: Iterable[str]) -> bool:
    return any(tool_token_pattern(tool).search(text) for tool in tools)


def dep_matches(name: str, tools: Iterable[str]) -> bool:
    lowered = name.lower()
    for tool in tools:
        tool = tool.lower()
        if lowered == tool:
            return True
        if tool == "storybook" and lowered.startswith("@storybook/"):
            return True
        if tool == "ladle" and lowered.startswith("@ladle/"):
            return True
        if tool == "histoire" and lowered.startswith("@histoire/"):
            return True
        if tool == "percy" and lowered.startswith("@percy/"):
            return True
        if tool == "applitools" and lowered.startswith("@applitools/"):
            return True
        if tool == "argos" and lowered.startswith("@argos-ci/"):
            return True
        if tool == "lost-pixel" and lowered.startswith("@lost-pixel/"):
            return True
        if tool == "reg-suit" and (lowered == "reg-suit" or lowered.startswith("reg-")):
            return True
    return False


def workspace_patterns(package: dict[str, Any]) -> list[str]:
    workspaces = package.get("workspaces", [])
    if isinstance(workspaces, dict):
        workspaces = workspaces.get("packages", [])
    if not isinstance(workspaces, list):
        return []
    return [str(pattern) for pattern in workspaces if isinstance(pattern, str) and pattern.strip()]


def discover_frontend_roots(
    project_root: pathlib.Path,
    explicit_roots: list[str] | None,
    warnings: list[str],
) -> list[pathlib.Path]:
    roots: list[pathlib.Path] = []

    def add_root(path: pathlib.Path) -> None:
        resolved = path.resolve()
        if not resolved.exists():
            warnings.append(f"Frontend root does not exist and was ignored: {path}")
            return
        if resolved not in roots:
            roots.append(resolved)

    if explicit_roots:
        for raw in explicit_roots:
            path = pathlib.Path(raw)
            add_root(path if path.is_absolute() else project_root / path)
        return roots

    add_root(project_root)
    root_package = load_json(project_root / "package.json", warnings)
    for pattern in workspace_patterns(root_package):
        for match in sorted(project_root.glob(pattern)):
            if match.is_dir():
                add_root(match)

    for pattern in ("apps/*", "packages/*"):
        for match in sorted(project_root.glob(pattern)):
            if match.is_dir() and (match / "package.json").exists():
                add_root(match)

    return roots


def package_contexts(
    project_root: pathlib.Path,
    frontend_roots: list[pathlib.Path],
    warnings: list[str],
) -> list[tuple[pathlib.Path, dict[str, str], dict[str, str]]]:
    contexts = []
    for root in frontend_roots:
        package = load_json(root / "package.json", warnings)
        scripts, deps = package_sections(package)
        contexts.append((root, scripts, deps))
    return contexts


def detect_component_isolation(
    project_root: pathlib.Path,
    contexts: list[tuple[pathlib.Path, dict[str, str], dict[str, str]]],
) -> list[dict[str, str]]:
    evidence: list[dict[str, str]] = []
    for root, scripts, deps in contexts:
        root_rel = relpath(project_root, root)
        for directory in (".storybook", ".ladle", ".histoire"):
            path = root / directory
            if path.exists():
                evidence.append(evidence_item("directory", directory, root_rel))
        for pattern in ("histoire.config.*", "ladle.config.*"):
            for path in sorted(root.glob(pattern)):
                evidence.append(evidence_item("config", path.name, relpath(project_root, path)))
        for name, command in scripts.items():
            if text_has_tool(f"{name} {command}".lower(), COMPONENT_ISOLATION_TOOLS):
                evidence.append(evidence_item("package_script", f"{name}: {command}", root_rel))
        for name in deps:
            if dep_matches(name, COMPONENT_ISOLATION_TOOLS):
                evidence.append(evidence_item("package_dependency", name, root_rel))
    return evidence


def detect_playwright(
    project_root: pathlib.Path,
    contexts: list[tuple[pathlib.Path, dict[str, str], dict[str, str]]],
) -> list[dict[str, str]]:
    evidence: list[dict[str, str]] = []
    for root, scripts, deps in contexts:
        root_rel = relpath(project_root, root)
        for pattern in ("playwright.config.*", "playwright-ct.config.*"):
            for path in sorted(root.glob(pattern)):
                evidence.append(evidence_item("config", path.name, relpath(project_root, path)))
        for name, command in scripts.items():
            if text_has_tool(f"{name} {command}".lower(), PLAYWRIGHT_TOOLS):
                evidence.append(evidence_item("package_script", f"{name}: {command}", root_rel))
        for name in deps:
            if dep_matches(name, PLAYWRIGHT_TOOLS):
                evidence.append(evidence_item("package_dependency", name, root_rel))
    return evidence


def source_files(root: pathlib.Path) -> Iterable[pathlib.Path]:
    scanned = 0
    for path in root.rglob("*"):
        if scanned >= MAX_SOURCE_SCAN_FILES:
            return
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if not path.is_file() or path.suffix.lower() not in SOURCE_EXTENSIONS:
            continue
        try:
            if path.stat().st_size > 512_000:
                continue
        except OSError:
            continue
        scanned += 1
        yield path


def detect_playwright_screenshots(
    project_root: pathlib.Path,
    contexts: list[tuple[pathlib.Path, dict[str, str], dict[str, str]]],
) -> list[dict[str, str]]:
    evidence: list[dict[str, str]] = []
    for root, scripts, _deps in contexts:
        root_rel = relpath(project_root, root)
        for name, command in scripts.items():
            lowered = f"{name} {command}".lower()
            if "playwright" in lowered and re.search(r"\b(screenshot|snapshot|visual|baseline|regression)\b", lowered):
                evidence.append(evidence_item("package_script", f"{name}: {command}", root_rel))

        for pattern in ("playwright.config.*", "playwright-ct.config.*"):
            for path in sorted(root.glob(pattern)):
                text = read_text(path).lower()
                if "tohavescreenshot" in text or "snapshotpathtemplate" in text:
                    evidence.append(
                        evidence_item("config_screenshot", path.name, relpath(project_root, path)),
                    )

        for directory in ("__screenshots__", "screenshots", "visual-baseline", "visual-baselines"):
            path = root / directory
            if path.exists():
                evidence.append(evidence_item("snapshot_directory", directory, relpath(project_root, path)))

        for path in source_files(root):
            text = read_text(path).lower()
            if "tohavescreenshot" in text:
                evidence.append(
                    evidence_item("source_match", "toHaveScreenshot", relpath(project_root, path)),
                )
                continue
            if "tomatchsnapshot" in text and "playwright" in text:
                evidence.append(
                    evidence_item("source_match", "toMatchSnapshot", relpath(project_root, path)),
                )
    return evidence


def detect_visual_diff(
    project_root: pathlib.Path,
    contexts: list[tuple[pathlib.Path, dict[str, str], dict[str, str]]],
) -> list[dict[str, str]]:
    evidence: list[dict[str, str]] = []
    config_patterns = (
        "chromatic.config.*",
        ".percy.*",
        "loki.config.*",
        "regconfig.json",
        "backstop.*",
        "backstop.config.*",
        "argos.config.*",
        "lostpixel.config.*",
    )
    for root, scripts, deps in contexts:
        root_rel = relpath(project_root, root)
        for pattern in config_patterns:
            for path in sorted(root.glob(pattern)):
                evidence.append(evidence_item("config", path.name, relpath(project_root, path)))
        for name, command in scripts.items():
            lowered = f"{name} {command}".lower()
            if text_has_tool(lowered, VISUAL_DIFF_TOOLS) or re.search(
                r"\b(visual diff|visual regression|image snapshot|pixelmatch)\b",
                lowered,
            ):
                evidence.append(evidence_item("package_script", f"{name}: {command}", root_rel))
        for name in deps:
            if dep_matches(name, VISUAL_DIFF_TOOLS):
                evidence.append(evidence_item("package_dependency", name, root_rel))
    return evidence


def planned_evidence(plan_text: str, lane: str) -> list[dict[str, str]]:
    if not plan_text:
        return []
    evidence: list[dict[str, str]] = []
    actions = r"\b(add|install|create|configure|introduce|wire|enable|adopt|setup|set up|prerequisite|task)\b"
    patterns = {
        "component_isolation": re.compile(
            rf"({actions}.{{0,120}}\b(storybook|ladle|histoire)\b)|(\b(storybook|ladle|histoire)\b.{{0,120}}\b(prerequisite|setup|task|coverage|stories?)\b)",
            re.I,
        ),
        "playwright": re.compile(
            rf"({actions}.{{0,120}}\bplaywright\b)|(\bplaywright\b.{{0,120}}\b(prerequisite|setup|task|e2e)\b)",
            re.I,
        ),
        "playwright_screenshot": re.compile(
            r"\b(playwright screenshots?|tohavescreenshot|screenshot baseline|visual snapshot|visual baseline|screenshot review|visual review|screenshot approvals?)\b",
            re.I,
        ),
        "visual_diff": re.compile(
            rf"({actions}.{{0,120}}\b(chromatic|percy|loki|reg-suit|backstopjs|argos|applitools|jest-image-snapshot|pixelmatch|lost-pixel|visual diff|visual regression)\b)",
            re.I,
        ),
    }
    pattern = patterns[lane]
    for index, raw_line in enumerate(plan_text.splitlines(), 1):
        line = raw_line.strip()
        if not line or NEGATION_RE.search(line):
            continue
        if pattern.search(line):
            evidence.append(evidence_item("plan_prerequisite", line[:180], f"line:{index}"))
    return evidence


def positive_lines(text: str, pattern: re.Pattern[str]) -> list[str]:
    result = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if line and pattern.search(line) and non_negated(line):
            result.append(line)
    return result


def contains_component_state_story(text: str) -> bool:
    story_pattern = re.compile(r"\b(storybook|stories|story coverage|state-story|states/stories)\b", re.I)
    state_pattern = re.compile(r"\b(component states?|state matrix|loading|empty|error|validation|success|offline)\b", re.I)
    return any(state_pattern.search(line) for line in positive_lines(text, story_pattern))


def contains_visual_baseline_loop(text: str) -> bool:
    baseline_pattern = re.compile(
        r"\b(screenshot baseline|visual baseline|visual regression baseline|baseline snapshots?|visual snapshots?)\b",
        re.I,
    )
    loop_pattern = re.compile(
        r"\b(review loop|visual review|screenshot review|approval loop|accepted baseline|approve visual|screenshot approval)\b",
        re.I,
    )
    has_baseline = bool(positive_lines(text, baseline_pattern))
    has_loop = bool(positive_lines(text, loop_pattern))
    return has_baseline and has_loop


def artifact_blocks(text: str) -> list[str]:
    lines = text.splitlines()
    indexes = [
        index
        for index, line in enumerate(lines)
        if re.search(r"\b(mock/prototype|prototype|mockup|mock artifact|figma|wireframe)\b", line, re.I)
    ]
    blocks: list[str] = []
    for index in indexes:
        start = max(0, index - 2)
        end = min(len(lines), index + 5)
        block = "\n".join(lines[start:end])
        if block not in blocks:
            blocks.append(block)
    return blocks


def block_has_normative_artifact(block: str) -> bool:
    for raw_line in block.splitlines():
        line = raw_line.strip()
        lowered = line.lower()
        artifact_line = re.search(r"\b(mock/prototype|prototype|mockup|mock artifact|figma|wireframe)\b", lowered)
        if not artifact_line or NEGATION_RE.search(line):
            continue
        if "reference-only" in lowered or "reference only" in lowered:
            continue
        if re.search(r"\b(normative|required reference|implementation reference)\b", lowered):
            return True
        if "source of truth" in lowered and "repo-owned design artifact" not in lowered:
            return True
    return False


def mock_prototype_state(*texts: str) -> dict[str, Any]:
    blocks = artifact_blocks("\n".join(texts))
    if not blocks:
        return {
            "required": False,
            "pass": True,
            "findings": ["No mock/prototype artifact lane declared."],
        }

    joined = "\n".join(blocks)
    normative = any(block_has_normative_artifact(block) for block in blocks)
    if not normative:
        return {
            "required": False,
            "pass": True,
            "findings": ["Mock/prototype artifacts are reference-only or advisory."],
        }

    lowered = joined.lower()
    has_mapping = "token/component mapping" in lowered or (
        "token" in lowered and "component" in lowered and "mapping" in lowered
    )
    has_freshness = (
        "freshness" in lowered
        or "expires" in lowered
        or "last updated" in lowered
        or "review by" in lowered
        or "reviewed by" in lowered
    )
    passed = has_mapping and has_freshness
    findings = []
    if not has_mapping:
        findings.append("Normative mock/prototype artifact lacks token/component mapping.")
    if not has_freshness:
        findings.append("Normative mock/prototype artifact lacks a freshness rule.")
    if not findings:
        findings.append("Normative mock/prototype artifact has mapping and freshness.")
    return {"required": True, "pass": passed, "findings": findings}


def resolve_design_artifact(config: dict[str, Any], explicit: str | None) -> str:
    if explicit:
        return explicit
    frontend = config.get("app_delivery", {}).get("frontend", {})
    if isinstance(frontend, dict):
        artifact = frontend.get("design_artifact")
        if isinstance(artifact, str) and artifact:
            return artifact
    return DEFAULT_DESIGN_ARTIFACT


def collect_errors(lanes: dict[str, dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    for lane_name, lane in lanes.items():
        if lane["required"] and not lane["pass"]:
            for finding in lane["findings"]:
                errors.append(f"{lane_name}: {finding}")
    return errors


def run_check(
    project_root: pathlib.Path,
    config_path: pathlib.Path,
    design_artifact: pathlib.Path,
    plan_path: pathlib.Path | None,
    mode: str,
    frontend_root_args: list[str] | None = None,
) -> dict[str, Any]:
    warnings: list[str] = []
    config = load_json(config_path, warnings)
    frontend_roots = discover_frontend_roots(project_root, frontend_root_args, warnings)
    contexts = package_contexts(project_root, frontend_roots, warnings)
    plan_text = read_text(plan_path) if plan_path else ""
    design_text = read_text(design_artifact)
    combined_text = "\n".join([design_text, plan_text])

    component_evidence = detect_component_isolation(project_root, contexts)
    playwright_evidence = detect_playwright(project_root, contexts)
    playwright_screenshot_evidence = detect_playwright_screenshots(project_root, contexts)
    visual_diff_evidence = detect_visual_diff(project_root, contexts)
    planned_component = planned_evidence(plan_text, "component_isolation")
    planned_playwright = planned_evidence(plan_text, "playwright")
    planned_playwright_screenshot = planned_evidence(plan_text, "playwright_screenshot")
    planned_visual_diff = planned_evidence(plan_text, "visual_diff")

    tools = {
        "storybook": {
            "available": has_any(component_evidence),
            "planned": has_any(planned_component),
            "evidence": component_evidence + planned_component,
        },
        "playwright": {
            "available": has_any(playwright_evidence),
            "planned": has_any(planned_playwright),
            "evidence": playwright_evidence + planned_playwright,
        },
        "playwright_screenshot": {
            "available": has_any(playwright_screenshot_evidence),
            "planned": has_any(planned_playwright_screenshot),
            "evidence": playwright_screenshot_evidence + planned_playwright_screenshot,
        },
        "visual_diff": {
            "available": has_any(visual_diff_evidence),
            "planned": has_any(planned_visual_diff),
            "evidence": visual_diff_evidence + planned_visual_diff,
        },
    }

    storybook_required = bool(tools["storybook"]["available"] or tools["storybook"]["planned"])
    visual_required = bool(
        tools["playwright_screenshot"]["available"]
        or tools["playwright_screenshot"]["planned"]
        or tools["visual_diff"]["available"]
        or tools["visual_diff"]["planned"]
    )

    lanes = {
        "storybook_component_states": {
            "required": storybook_required,
            "pass": True if not storybook_required else contains_component_state_story(combined_text),
            "findings": [],
        },
        "screenshot_visual_baseline": {
            "required": visual_required,
            "pass": True if not visual_required else contains_visual_baseline_loop(combined_text),
            "findings": [],
        },
        "mock_prototype_artifacts": mock_prototype_state(design_text, plan_text),
    }

    if storybook_required:
        if lanes["storybook_component_states"]["pass"]:
            lanes["storybook_component_states"]["findings"].append(
                "Component isolation lane has component state/story coverage.",
            )
        else:
            lanes["storybook_component_states"]["findings"].append(
                "Storybook or equivalent component isolation is available or planned, but component state/story coverage is missing.",
            )
    else:
        lanes["storybook_component_states"]["findings"].append(
            "Component isolation lane is advisory because no project-local Storybook/equivalent tooling or prerequisite task exists.",
        )

    if visual_required:
        if lanes["screenshot_visual_baseline"]["pass"]:
            lanes["screenshot_visual_baseline"]["findings"].append(
                "Screenshot/visual lane has baseline and review loop coverage.",
            )
        else:
            lanes["screenshot_visual_baseline"]["findings"].append(
                "Screenshot-specific Playwright, visual diff, or equivalent tooling is available or planned, but screenshot/visual baseline and review loop coverage is missing.",
            )
    else:
        lanes["screenshot_visual_baseline"]["findings"].append(
            "Screenshot/visual lane is advisory because no project-local screenshot visual tooling or prerequisite task exists.",
        )

    if not design_artifact.exists() and (storybook_required or visual_required):
        for lane in lanes.values():
            if lane["required"]:
                lane["pass"] = False
                lane["findings"].append(f"Design artifact missing: {design_artifact}")

    passed = all(bool(lane["pass"]) for lane in lanes.values())
    errors = collect_errors(lanes)
    if mode == "detect" and errors:
        warnings.append("Detect mode is advisory and exits 0 even when required lanes have gaps; use --mode check for gating.")

    return {
        "schema_version": SCHEMA_VERSION,
        "pass": passed,
        "mode": mode,
        "project_root": str(project_root),
        "frontend_roots": [str(root) for root in frontend_roots],
        "config": str(config_path),
        "design_artifact": str(design_artifact),
        "plan": str(plan_path) if plan_path else "",
        "tools": tools,
        "lanes": lanes,
        "errors": errors,
        "warnings": warnings,
        "summary": "visual readiness satisfied" if passed else "visual readiness gaps found",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Detect frontend visual readiness lanes")
    parser.add_argument("--project-root", required=True, type=pathlib.Path)
    parser.add_argument("--frontend-root", action="append", default=None, help="Frontend root relative to project root; may be repeated")
    parser.add_argument("--config", default=None, help="Config path, defaults to .harness/config.json")
    parser.add_argument("--design-artifact", default=None, help="Frontend design artifact path")
    parser.add_argument("--plan", default=None, help="Plan artifact path")
    parser.add_argument("--mode", choices=("detect", "check"), default="check")
    parser.add_argument("--json", action="store_true", help="Print JSON output")
    args = parser.parse_args()

    project_root = args.project_root.resolve()
    if not project_root.exists():
        print(f"project root not found: {project_root}", file=sys.stderr)
        return 2

    config_path = (project_root / args.config).resolve() if args.config else project_root / ".harness" / "config.json"
    config = load_json(config_path)
    design_rel = resolve_design_artifact(config, args.design_artifact)
    design_path = (project_root / design_rel).resolve()
    plan_path = (project_root / args.plan).resolve() if args.plan else None

    result = run_check(
        project_root,
        config_path,
        design_path,
        plan_path,
        args.mode,
        args.frontend_root,
    )
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        tag = "PASS" if result["pass"] else "FAIL"
        print(f"[{tag}] {result['summary']}")
        if args.mode == "detect":
            print("[INFO] detect mode is advisory; use --mode check for gating.")
        for warning in result["warnings"]:
            print(f"[WARN] {warning}")
        for lane_name, lane in result["lanes"].items():
            lane_tag = "PASS" if lane["pass"] else "FAIL"
            required = "required" if lane["required"] else "advisory"
            print(f"[{lane_tag}] {lane_name}: {required}")
            for finding in lane["findings"]:
                print(f"  - {finding}")

    if args.mode == "detect":
        return 0
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
