#!/usr/bin/env python3
"""Run deterministic EZPowers skill regression checks.

This runner is intentionally separate from scripts/run_baseline.py because the
existing eval schema is command-focused. Skill cases check hot-path skill files,
reference links, protected paths, and optional live smoke commands.
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import time
from typing import Any

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML required. Install with: pip install pyyaml", file=sys.stderr)
    sys.exit(1)

import run_baseline as rb  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
SKILLS_ROOT = REPO_ROOT / "skills"
EVALS_ROOT = REPO_ROOT / "evals" / "skills"
PROTECTED_PATHS = (
    "skills/writing-skills/",
    "skills/grill-with-docs/",
    "skills/caveman/",
    "skills/zoom-out/",
)
from shared import (  # noqa: E402
    parse_timeout, env_timeout, utc_timestamp, write_progress, remaining_timeout,
)

DEFAULT_LIVE_PROVIDER = "claude"
LIVE_PROVIDERS = ("claude", "codex", "auto")
DEFAULT_TIMEOUT_SECONDS = 300


def default_progress_file() -> pathlib.Path:
    configured = os.environ.get("EZPOWERS_SKILL_EVAL_PROGRESS_FILE")
    if configured:
        return pathlib.Path(configured)
    configured = os.environ.get("EZPOWERS_EVAL_PROGRESS_FILE")
    if configured:
        return pathlib.Path(configured)
    return REPO_ROOT / "evals" / "results" / "runs" / "last_skill_eval_case.json"


def repo_path(path: str) -> pathlib.Path:
    return (REPO_ROOT / path).resolve()


def rel(path: pathlib.Path) -> str:
    return path.resolve().relative_to(REPO_ROOT).as_posix()


def git_changed_files(staged: bool) -> list[str]:
    cmd = ["git", "diff", "--name-only"]
    if staged:
        cmd.insert(2, "--cached")
    proc = subprocess.run(
        cmd,
        cwd=REPO_ROOT,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
    )
    changed = [line.strip().replace("\\", "/") for line in proc.stdout.splitlines() if line.strip()]
    if not staged:
        status = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=REPO_ROOT,
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            check=False,
        )
        for raw in status.stdout.splitlines():
            if raw.startswith("?? "):
                changed.append(raw[3:].strip().replace("\\", "/"))
    return sorted(set(changed))


def check_protected_paths(staged: bool) -> tuple[bool, str]:
    changed = git_changed_files(staged)
    hits = [p for p in changed if p.startswith(PROTECTED_PATHS)]
    if hits:
        return False, "protected skill paths changed: " + ", ".join(hits)
    return True, "protected skill paths unchanged"


def load_cases(case_paths: list[pathlib.Path] | None) -> list[tuple[pathlib.Path, dict[str, Any]]]:
    paths = case_paths or sorted(EVALS_ROOT.rglob("*.yaml"))
    cases: list[tuple[pathlib.Path, dict[str, Any]]] = []
    for path in paths:
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if not isinstance(data, dict):
            raise ValueError(f"{path}: case must be a mapping")
        cases.append((path, data))
    return cases


def validate_case_schema(path: pathlib.Path, case: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = ("case_id", "skill", "prompt", "expected_first_action", "invariants")
    for key in required:
        if key not in case:
            errors.append(f"missing {key}")
    if "skill" in case:
        skill_dir = SKILLS_ROOT / str(case["skill"])
        if not skill_dir.exists():
            errors.append(f"skill directory missing: {rel(skill_dir)}")
    if "invariants" in case and not isinstance(case["invariants"], list):
        errors.append("invariants must be a list")
    if "forbidden_behaviors" in case and not isinstance(case["forbidden_behaviors"], list):
        errors.append("forbidden_behaviors must be a list")
    if "static" in case and not isinstance(case["static"], dict):
        errors.append("static must be a mapping")
    if "live" in case and not isinstance(case["live"], dict):
        errors.append("live must be a mapping")
    if not re.match(r"^skill\.[a-z0-9-]+\.[a-z0-9-]+$", str(case.get("case_id", ""))):
        errors.append("case_id must match skill.<skill>.<slug>")
    return [f"{path}: {e}" for e in errors]


def read_skill(skill: str) -> str:
    skill_path = SKILLS_ROOT / skill / "SKILL.md"
    return skill_path.read_text(encoding="utf-8")


def word_count(text: str) -> int:
    body = re.sub(r"^---.*?---", "", text, flags=re.S)
    return len(re.findall(r"\S+", body))


def frontmatter(text: str) -> dict[str, str]:
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.S)
    if not match:
        return {}
    fields: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        fields[key.strip()] = value.strip().strip('"')
    return fields


def run_static_checks(case: dict[str, Any]) -> tuple[bool, list[str]]:
    skill = str(case["skill"])
    text = read_skill(skill)
    meta = frontmatter(text)
    static = case.get("static", {}) or {}
    errors: list[str] = []

    if meta.get("name") != skill:
        errors.append(f"frontmatter name is {meta.get('name')!r}, expected {skill!r}")
    if not meta.get("description"):
        errors.append("frontmatter description missing")

    max_words = static.get("max_words")
    if max_words is not None and word_count(text) > int(max_words):
        errors.append(f"word count {word_count(text)} exceeds max_words {max_words}")

    for needle in static.get("must_contain", []):
        if needle not in text:
            errors.append(f"missing required text: {needle}")

    for needle in static.get("must_not_contain", []):
        if needle in text:
            errors.append(f"forbidden text present: {needle}")

    for path in static.get("required_files", []):
        if not repo_path(path).exists():
            errors.append(f"required file missing: {path}")

    for path in static.get("required_reference_links", []):
        if path not in text:
            errors.append(f"SKILL.md does not mention reference: {path}")
        if not (SKILLS_ROOT / skill / path).exists():
            errors.append(f"referenced file missing: skills/{skill}/{path}")

    return not errors, errors


def as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    return [str(value)]


def render_bullets(values: Any) -> str:
    items = as_list(values)
    if not items:
        return "- None"
    return "\n".join(f"- {item}" for item in items)


def referenced_files(case: dict[str, Any]) -> list[str]:
    static = case.get("static", {}) or {}
    live = case.get("live", {}) or {}
    files: list[str] = []
    for path in as_list(static.get("required_reference_links")):
        files.append(f"skills/{case['skill']}/{path}")
    for path in as_list(live.get("context_files")):
        files.append(path)
    seen: set[str] = set()
    result: list[str] = []
    for path in files:
        normalized = path.replace("\\", "/")
        if normalized not in seen:
            seen.add(normalized)
            result.append(normalized)
    return result


def build_live_prompt(case: dict[str, Any]) -> str:
    live = case.get("live", {}) or {}
    skill = str(case["skill"])
    skill_path = SKILLS_ROOT / skill / "SKILL.md"
    prompt = str(live.get("prompt") or case["prompt"])
    sections = [
        "You are running a live smoke test for one EZPowers skill.",
        "Do not edit files. Follow only the skill text and the scenario below.",
        "If the scenario names a file path, read that file from disk before judging it.",
        "",
        f"# Skill under test: {skill}",
        f"## {rel(skill_path)}",
        "```markdown",
        skill_path.read_text(encoding="utf-8"),
        "```",
    ]
    for path in referenced_files(case):
        full_path = repo_path(path)
        if full_path.exists():
            sections.extend([
                "",
                f"## {path}",
                "```markdown",
                full_path.read_text(encoding="utf-8"),
                "```",
            ])
    sections.extend([
        "",
        "# Scenario",
        prompt,
        "",
        "# Expected first action",
        str(case["expected_first_action"]),
        "",
        "# Invariants",
        render_bullets(case.get("invariants")),
        "",
        "# Forbidden behaviors",
        render_bullets(case.get("forbidden_behaviors")),
        "",
        "# Output requirements",
        "Return the response you would give to the user for this scenario.",
        "Keep it concise, but include enough concrete evidence to prove the skill was applied.",
    ])
    return "\n".join(sections)


def live_provider_order(requested: str, case: dict[str, Any]) -> list[str]:
    live = case.get("live", {}) or {}
    if requested != "auto":
        return [requested]
    order = [str(live.get("agent") or ""), "codex", "claude"]
    result: list[str] = []
    for provider in order:
        if provider in ("claude", "codex") and provider not in result:
            result.append(provider)
    return result


def run_claude_live(prompt: str, live: dict[str, Any], timeout_seconds: float | None = None) -> tuple[int, str, str]:
    exe = shutil.which("claude")
    if not exe:
        return 127, "", "claude executable not found on PATH"
    tools = live.get("tools", ["Read", "Grep", "Glob"])
    if isinstance(tools, list):
        tools_arg = ",".join(str(tool) for tool in tools)
    else:
        tools_arg = str(tools)
    cmd = [
        exe,
        "--print",
        "--no-session-persistence",
        "--disable-slash-commands",
        "--setting-sources",
        "project",
        "--permission-mode",
        str(live.get("permission_mode", "plan")),
        "--max-budget-usd",
        str(live.get("max_budget_usd", "0.25")),
        "--output-format",
        "text",
        "--tools",
        tools_arg,
    ]
    proc = rb.run_command_with_timeout(
        cmd,
        cwd=REPO_ROOT,
        timeout=timeout_seconds if timeout_seconds is not None else int(live.get("timeout_seconds", 120)),
        input_text=prompt,
    )
    return proc.returncode, proc.stdout or "", proc.stderr or ""


def run_codex_live(prompt: str, live: dict[str, Any], timeout_seconds: float | None = None) -> tuple[int, str, str]:
    exe = shutil.which("codex")
    if not exe:
        return 127, "", "codex executable not found on PATH"
    cmd = [
        exe,
        "exec",
        "--ephemeral",
        "--ignore-rules",
        "-C",
        str(REPO_ROOT),
        "-s",
        "read-only",
        "-a",
        "never",
    ]
    model = live.get("model")
    if model:
        cmd.extend(["-m", str(model)])
    cmd.append("-")
    proc = rb.run_command_with_timeout(
        cmd,
        cwd=REPO_ROOT,
        timeout=timeout_seconds if timeout_seconds is not None else int(live.get("timeout_seconds", 120)),
        input_text=prompt,
    )
    return proc.returncode, proc.stdout or "", proc.stderr or ""


def run_provider(
    provider: str,
    prompt: str,
    live: dict[str, Any],
    timeout_seconds: float | None = None,
) -> tuple[int, str, str]:
    if provider == "claude":
        return run_claude_live(prompt, live, timeout_seconds)
    if provider == "codex":
        return run_codex_live(prompt, live, timeout_seconds)
    return 2, "", f"unknown live provider: {provider}"


def check_live_output(output: str, live: dict[str, Any]) -> tuple[bool, str]:
    for needle in as_list(live.get("must_contain")):
        if needle not in output:
            return False, f"live output missing: {needle}"
    for pattern in as_list(live.get("must_match")):
        if not re.search(pattern, output, re.I | re.S):
            return False, f"live output missing pattern: {pattern}"
    for needle in as_list(live.get("must_not_contain")):
        if needle in output:
            return False, f"live output contained forbidden text: {needle}"
    for pattern in as_list(live.get("must_not_match")):
        if re.search(pattern, output, re.I | re.S):
            return False, f"live output matched forbidden pattern: {pattern}"
    return True, "live smoke passed"


def run_legacy_live_command(live: dict[str, Any], timeout_seconds: float | None = None) -> tuple[bool, str]:
    proc = rb.run_command_with_timeout(
        live["command"],
        cwd=REPO_ROOT,
        shell=True,
        timeout=timeout_seconds if timeout_seconds is not None else int(live.get("timeout_seconds", 120)),
    )
    output = (proc.stdout or "") + "\n" + (proc.stderr or "")
    if proc.returncode != 0:
        return False, f"exit {proc.returncode}: {output[-500:]}"
    ok, detail = check_live_output(output, live)
    return ok, detail


def run_live_check(
    case: dict[str, Any],
    enabled: bool,
    provider: str,
    timeout_seconds: float | None = None,
) -> tuple[bool | None, str]:
    live = case.get("live") or {}
    if not live:
        return None, "no live smoke configured"
    if not enabled:
        return None, "live smoke skipped; pass --live to run"
    command = live.get("command")
    if command:
        return run_legacy_live_command(live, timeout_seconds)
    if not any(key in live for key in ("prompt", "must_contain", "must_match", "must_not_contain", "must_not_match")):
        note = live.get("note", "no live smoke command configured")
        return None, f"live smoke not configured: {note}"

    prompt = build_live_prompt(case)
    errors: list[str] = []
    for candidate in live_provider_order(provider, case):
        try:
            code, stdout, stderr = run_provider(candidate, prompt, live, timeout_seconds)
        except subprocess.TimeoutExpired:
            timeout_label = timeout_seconds if timeout_seconds is not None else live.get("timeout_seconds", 120)
            errors.append(f"{candidate}: timed out after {timeout_label}s")
            continue
        except OSError as exc:
            errors.append(f"{candidate}: execution failed: {exc}")
            continue
        output = stdout + "\n" + stderr
        if code != 0:
            errors.append(f"{candidate}: exit {code}: {output[-500:]}")
            continue
        ok, detail = check_live_output(output, live)
        if ok:
            return True, f"{detail} ({candidate})"
        errors.append(f"{candidate}: {detail}: {output[-500:]}")
    return False, " | ".join(errors)


def run_case(
    path: pathlib.Path,
    case: dict[str, Any],
    live: bool,
    live_provider: str,
    *,
    live_timeout_seconds: float | None = None,
    progress_file: str | pathlib.Path | None = None,
    case_index: int | None = None,
    total_cases: int | None = None,
) -> dict[str, Any]:
    case_id = str(case.get("case_id", path.stem))
    write_progress(progress_file, {
        "runner": "run_skill_evals",
        "phase": "case_start",
        "case_id": case_id,
        "case_path": str(path),
        "case_index": case_index,
        "total_cases": total_cases,
        "live_enabled": live,
        "live_provider": live_provider,
    })
    schema_errors = validate_case_schema(path, case)
    if schema_errors:
        result = {"case_id": case_id, "pass": False, "errors": schema_errors}
        write_progress(progress_file, {
            "runner": "run_skill_evals",
            "phase": "case_done",
            "case_id": case_id,
            "case_path": str(path),
            "pass": False,
        })
        return result

    static_pass, static_errors = run_static_checks(case)
    live_pass, live_detail = run_live_check(case, live, live_provider, live_timeout_seconds)
    passed = static_pass and live_pass is not False
    result = {
        "case_id": case_id,
        "skill": case["skill"],
        "pass": passed,
        "static_pass": static_pass,
        "static_errors": static_errors,
        "live_pass": live_pass,
        "live_detail": live_detail,
    }
    write_progress(progress_file, {
        "runner": "run_skill_evals",
        "phase": "case_done",
        "case_id": case_id,
        "case_path": str(path),
        "pass": passed,
    })
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Run EZPowers skill evals")
    parser.add_argument("--cases", nargs="*", help="Specific case YAML files")
    parser.add_argument("--live", action="store_true", help="Run optional live smoke checks")
    parser.add_argument(
        "--live-provider",
        choices=LIVE_PROVIDERS,
        default=DEFAULT_LIVE_PROVIDER,
        help="Provider for live smoke checks (default: claude)",
    )
    parser.add_argument("--staged", action="store_true", help="Check staged diff for protected paths")
    parser.add_argument("--json", action="store_true", help="Print JSON result")
    parser.add_argument(
        "--timeout-seconds",
        type=lambda value: parse_timeout(value, DEFAULT_TIMEOUT_SECONDS, "--timeout-seconds"),
        default=env_timeout("EZPOWERS_SKILL_EVAL_TIMEOUT_SECONDS", DEFAULT_TIMEOUT_SECONDS),
        help=(
            "Overall runner timeout in seconds; live commands use the remaining budget "
            "(default: env EZPOWERS_SKILL_EVAL_TIMEOUT_SECONDS or 300)"
        ),
    )
    parser.add_argument(
        "--progress-file",
        default=None,
        help=(
            "JSON file updated before each case "
            "(default: env EZPOWERS_SKILL_EVAL_PROGRESS_FILE, EZPOWERS_EVAL_PROGRESS_FILE, "
            "or evals/results/runs/last_skill_eval_case.json)"
        ),
    )
    args = parser.parse_args()

    case_paths = [repo_path(p) for p in args.cases] if args.cases else None
    cases = load_cases(case_paths)
    protected_ok, protected_detail = check_protected_paths(args.staged)
    progress_file = pathlib.Path(args.progress_file) if args.progress_file else default_progress_file()
    deadline = time.monotonic() + args.timeout_seconds
    results = []
    timed_out = False
    timeout_detail = ""

    for i, (path, case) in enumerate(cases, 1):
        live_config = case.get("live") if isinstance(case.get("live"), dict) else {}
        remaining = remaining_timeout(deadline, int(live_config.get("timeout_seconds", 120)))
        case_id = str(case.get("case_id", path.stem))
        if remaining <= 0:
            timed_out = True
            timeout_detail = f"skill eval runner timed out before {case_id}"
            break
        print(f"[progress] skill case {i}/{len(cases)} {case_id}", file=sys.stderr, flush=True)
        result = run_case(
            path,
            case,
            args.live,
            args.live_provider,
            live_timeout_seconds=remaining,
            progress_file=progress_file,
            case_index=i,
            total_cases=len(cases),
        )
        results.append(result)
        if time.monotonic() > deadline:
            timed_out = True
            timeout_detail = f"skill eval runner timed out after {case_id}"
            break
    all_pass = protected_ok and all(r["pass"] for r in results)
    if timed_out:
        all_pass = False

    summary = {
        "pass": all_pass,
        "protected_paths": {"pass": protected_ok, "detail": protected_detail},
        "total_cases": len(results),
        "passed_cases": sum(1 for r in results if r["pass"]),
        "timeout_seconds": args.timeout_seconds,
        "timed_out": timed_out,
        "timeout_detail": timeout_detail,
        "results": results,
    }

    if args.json:
        print(json.dumps(summary, indent=2, ensure_ascii=False))
    else:
        tag = "PASS" if protected_ok else "FAIL"
        print(f"[{tag}] protected_paths: {protected_detail}")
        for result in results:
            tag = "PASS" if result["pass"] else "FAIL"
            print(f"[{tag}] {result['case_id']}")
            for error in result.get("static_errors", []):
                print(f"  - {error}")
            print(f"  live: {result.get('live_detail')}")
        if timed_out:
            print(f"[FAIL] timeout: {timeout_detail}")
        print(f"Skill evals: {summary['passed_cases']}/{summary['total_cases']} passed")

    if timed_out:
        return 124
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
