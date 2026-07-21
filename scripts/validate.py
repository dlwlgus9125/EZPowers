#!/usr/bin/env python3
"""EZPowers eval gate -- validates commits touching workflow prompts or docs/reference/.

Checks (in order):
  1. diff_line_count   -- Diff lines <= 3 for behavior commands and agents
  2. eval_isolation     -- evals/ not modified with behavior commands/agents
  3. golden_invariants  -- Golden codebase-invariant graders all pass
  4. optimization_delta -- Optimization pass rate >= baseline (+5% if diagnostician)
  5. holdout_delta      -- Holdout pass rate not worse than -5% vs baseline
  6. banned_self_ref    -- No banned expressions in added text
  7. expected_improvements -- Diagnostician predictions realized (if applicable)
  8. doc_consistency    -- Canonical bullet coverage across CONSISTENCY_PAIRS

Each check outputs [PASS|FAIL] <check_name>: <details>.
Exit 0 if all pass, 1 if any fail.

Usage:
  python scripts/validate.py --staged    # pre-commit hook mode
  python scripts/validate.py             # working tree diff mode
  python scripts/validate.py --ci        # CI mode (auto-detects CI env vars)
  python scripts/validate.py --ci --output-format=json   # JSON output for CI
  python scripts/validate.py --ci --output-format=junit   # JUnit XML for CI dashboards
  python scripts/validate.py --ci --base-ref=origin/main  # diff against specific ref
  python scripts/validate.py --ci --changed-files a.md b.md  # explicit file list
"""

import argparse
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
EVALS_ROOT = REPO_ROOT / "evals"
GOLDEN_DIR = EVALS_ROOT / "golden"
BASELINES_DIR = EVALS_ROOT / "results" / "baselines"
COMMAND_EVAL_SPLITS = ("golden", "optimization", "holdout", "honeypot")
EVAL_TOOL_COMMANDS = {"commands/eval.md", "skills/eval/SKILL.md"}

# Workflow commands live at skills/<name>/SKILL.md after the 3.0.0 migration;
# both layouts stay behavior-gated during the transition.
WORKFLOW_SKILL_NAMES = (
    "setup", "design-architecture", "spec", "prepare-execute", "choice-execute",
    "maintain", "deploy", "reset-setup", "review", "sync-docs", "set-rules",
    "eval", "feedback",
)
WORKFLOW_SKILL_PATHS = frozenset(f"skills/{n}/SKILL.md" for n in WORKFLOW_SKILL_NAMES)
WORKFLOW_SKILL_DIR_PREFIXES = tuple(f"skills/{n}/" for n in WORKFLOW_SKILL_NAMES)

# Import run_baseline for grader execution
sys.path.insert(0, str(REPO_ROOT / "scripts"))
import run_baseline as rb  # noqa: E402

# ---------------------------------------------------------------------------
# Banned expressions — canonical source: shared.py
# ---------------------------------------------------------------------------
from shared import BANNED_KO, BANNED_EN_RE  # noqa: E402

# Mock-output variables that need live execution (skip these grader commands)
LIVE_EXEC_VARS = ("$REVIEW_OUTPUT", "$EXECUTOR_OUTPUT")

MAX_DIFF_LINES = 3

# ---------------------------------------------------------------------------
# Canonical Bullet Coverage — cross-document rule consistency (W2+W4)
# ---------------------------------------------------------------------------
CONSISTENCY_PAIRS = [
    {
        "name": "wiring_config_validation",
        "source": "docs/reference/verification-contract.md",
        "source_heading": "## Wiring Config Validation",
        "consumer": "commands/choice_execute.md",
        "consumer_candidates": [
            "skills/choice-execute/SKILL.md",
            "commands/choice_execute.md",
        ],
        "consumer_heading": "## 3.7. Wiring Config Validation",
    },
]
DEFAULT_VALIDATE_TIMEOUT_SECONDS = 300
DEFAULT_EVAL_COMMAND_TIMEOUT_SECONDS = 30
EVAL_SYNC_PATH_PREFIXES = (
    "evals/golden/",
    "evals/optimization/",
    "evals/holdout/",
    "evals/honeypot/",
    "evals/results/baselines/",
)
EVAL_SYNC_FILES = (
    "commands/eval.md",
    "skills/eval/SKILL.md",
    "evals/schema.json",
    "evals/INDEX.md",
    ".codex-plugin/plugin.json",
    "scripts/run_baseline.py",
    "scripts/validate.py",
)


# ---------------------------------------------------------------------------
# Git helpers
# ---------------------------------------------------------------------------
def _git(*args: str) -> str:
    r = subprocess.run(
        ["git", *args],
        capture_output=True, text=True, encoding="utf-8",
        errors="replace", cwd=str(REPO_ROOT),
    )
    return (r.stdout or "").strip()


def _diff_flag(staged: bool) -> list[str]:
    return ["--cached"] if staged else []


def get_changed_files(staged: bool) -> list[str]:
    out = _git("diff", *_diff_flag(staged), "--name-only")
    changed = [f.strip().replace("\\", "/") for f in out.split("\n") if f.strip()]
    if not staged:
        status = _git("status", "--porcelain")
        for raw in status.split("\n"):
            if raw.startswith("?? "):
                changed.append(raw[3:].strip().replace("\\", "/"))
    return sorted(set(changed))


def get_diff_line_count(staged: bool, paths: list[str]) -> int:
    out = _git("diff", *_diff_flag(staged), "--numstat", "--", *paths)
    total = 0
    for line in out.split("\n"):
        if not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) >= 2:
            added = int(parts[0]) if parts[0] != "-" else 0
            deleted = int(parts[1]) if parts[1] != "-" else 0
            total += added + deleted
    return total


def get_added_lines(staged: bool, paths: list[str]) -> str:
    """Extract added lines from diff, excluding code blocks and blockquotes."""
    out = _git("diff", *_diff_flag(staged), "-U0", "--", *paths)
    lines: list[str] = []
    in_code_block = False
    for raw in out.split("\n"):
        if not raw.startswith("+") or raw.startswith("+++"):
            continue
        text = raw[1:]
        if "```" in text:
            in_code_block = not in_code_block
            continue
        if in_code_block:
            continue
        if text.strip().startswith(">"):
            continue
        # Skip table rows that define or list banned expressions
        if re.search(r"\|.*(금지|[Bb]anned).*\|", text):
            continue
        if re.match(r"\s*\|[-\s|]+\|", text):
            continue
        # Skip markdown table body rows (header/separator already handled above).
        # Heuristic: starts with |, has 3+ pipes, and does NOT look like a shell
        # pipe chain (shell pipes don't start with |).
        if re.match(r"\s*\|[^|]", text) and text.count("|") >= 3:
            continue
        lines.append(text)
    return "\n".join(lines)


def is_behavior_prompt_path(path: str) -> bool:
    if path.startswith("agents/"):
        return True
    if path.startswith("commands/"):
        return path not in EVAL_TOOL_COMMANDS
    if path in WORKFLOW_SKILL_PATHS:
        return path not in EVAL_TOOL_COMMANDS
    return False


def behavior_prompt_targets(changed: list[str]) -> list[str]:
    return [f for f in changed if is_behavior_prompt_path(f)]


# ---------------------------------------------------------------------------
# CI environment detection
# ---------------------------------------------------------------------------
def detect_ci_environment() -> tuple[bool, dict[str, bool]]:
    """Detect CI environment from standard env vars."""
    ci_signals = {
        'CI': os.environ.get('CI', '').lower() in ('true', '1', 'yes'),
        'GITHUB_ACTIONS': bool(os.environ.get('GITHUB_ACTIONS')),
        'GITLAB_CI': bool(os.environ.get('GITLAB_CI')),
        'JENKINS_URL': bool(os.environ.get('JENKINS_URL')),
        'CIRCLECI': bool(os.environ.get('CIRCLECI')),
        'AZURE_PIPELINES': bool(os.environ.get('SYSTEM_TEAMFOUNDATIONCOLLECTIONURI')),
    }
    detected = {k: v for k, v in ci_signals.items() if v}
    return bool(detected), detected


def _git_checked(*args: str) -> str:
    """Run git command in CI context, raising on failure instead of silent empty."""
    r = subprocess.run(
        ["git", *args],
        capture_output=True, text=True, encoding="utf-8",
        errors="replace", cwd=str(REPO_ROOT),
    )
    if r.returncode != 0:
        raise RuntimeError(
            f"git {' '.join(args)} failed (exit {r.returncode}): "
            f"{(r.stderr or '').strip()}"
        )
    return (r.stdout or "").strip()


def get_changed_files_ci(base_ref: str) -> list[str]:
    """Get changed files by diffing HEAD against a base ref (for CI pipelines)."""
    # Try three-dot diff first (merge-base based, standard for PRs)
    try:
        out = _git_checked("diff", "--name-only", f"{base_ref}...HEAD")
    except RuntimeError:
        out = ""
    if not out:
        # Fallback to two-dot diff (direct comparison)
        try:
            out = _git_checked("diff", "--name-only", base_ref, "HEAD")
        except RuntimeError:
            out = ""
    if not out:
        # Shallow clone: try fetching the base ref first
        try:
            _git_checked("fetch", "--depth=1", "origin", base_ref.replace("origin/", ""))
            out = _git_checked("diff", "--name-only", f"{base_ref}...HEAD")
        except RuntimeError as e:
            print(f"[CI] ERROR: Could not determine changed files: {e}", file=sys.stderr)
            sys.exit(2)  # Fail loudly instead of silently passing with empty diff
    return sorted(set(
        f.strip().replace("\\", "/") for f in out.split("\n") if f.strip()
    ))


def _ci_diff_args(base_ref: str) -> list[str]:
    """Build git diff args for CI mode (diff against base ref)."""
    return [f"{base_ref}...HEAD"]


def get_diff_line_count_ci(base_ref: str, paths: list[str]) -> int:
    """Count diff lines against a base ref (CI mode)."""
    out = _git("diff", "--numstat", f"{base_ref}...HEAD", "--", *paths)
    total = 0
    for line in out.split("\n"):
        if not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) >= 2:
            added = int(parts[0]) if parts[0] != "-" else 0
            deleted = int(parts[1]) if parts[1] != "-" else 0
            total += added + deleted
    return total


def get_added_lines_ci(base_ref: str, paths: list[str]) -> str:
    """Extract added lines from diff against a base ref (CI mode)."""
    out = _git("diff", f"{base_ref}...HEAD", "-U0", "--", *paths)
    lines: list[str] = []
    in_code_block = False
    for raw in out.split("\n"):
        if not raw.startswith("+") or raw.startswith("+++"):
            continue
        text = raw[1:]
        if "```" in text:
            in_code_block = not in_code_block
            continue
        if in_code_block:
            continue
        if text.strip().startswith(">"):
            continue
        if re.search(r"\|.*(금지|[Bb]anned).*\|", text):
            continue
        if re.match(r"\s*\|[-\s|]+\|", text):
            continue
        if re.match(r"\s*\|[^|]", text) and text.count("|") >= 3:
            continue
        lines.append(text)
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CI output formatters
# ---------------------------------------------------------------------------
def format_json_output(
    results: list[tuple[str, bool, str, float]],
    ci_mode: bool,
) -> str:
    """Format validation results as JSON for CI consumption."""
    checks = []
    for name, passed, detail, elapsed_ms in results:
        if passed:
            status = 'pass'
        else:
            status = 'fail'
        checks.append({
            'name': name,
            'status': status,
            'message': detail,
            'duration_ms': round(elapsed_ms, 1),
        })
    count_pass = sum(1 for c in checks if c['status'] == 'pass')
    count_fail = sum(1 for c in checks if c['status'] == 'fail')
    return json.dumps({
        'version': '1.0',
        'validator': 'ezpowers-validate',
        'ci_mode': ci_mode,
        'checks': checks,
        'summary': {
            'total': len(checks),
            'passed': count_pass,
            'failed': count_fail,
        },
        'exit_code': 0 if count_fail == 0 else 1,
    }, indent=2)


def format_junit_output(
    results: list[tuple[str, bool, str, float]],
) -> str:
    """Format as JUnit XML for CI test reporting (GitHub Actions / GitLab CI)."""
    count_fail = sum(1 for _, passed, _, _ in results if not passed)
    total_time = sum(ms for _, _, _, ms in results) / 1000.0

    testsuites = ET.Element('testsuites')
    testsuite = ET.SubElement(testsuites, 'testsuite', {
        'name': 'ezpowers-validate',
        'tests': str(len(results)),
        'failures': str(count_fail),
        'errors': '0',
        'time': f'{total_time:.3f}',
    })

    for name, passed, detail, elapsed_ms in results:
        testcase = ET.SubElement(testsuite, 'testcase', {
            'name': name,
            'classname': 'ezpowers.validate',
            'time': f'{elapsed_ms / 1000.0:.3f}',
        })
        if not passed:
            failure = ET.SubElement(testcase, 'failure', {
                'message': detail,
                'type': 'AssertionError',
            })
            failure.text = detail

    ET.indent(testsuites, space='  ')
    xml_str = ET.tostring(testsuites, encoding='unicode', xml_declaration=True)
    return xml_str


# ---------------------------------------------------------------------------
# Check 1: diff line count
# ---------------------------------------------------------------------------
def check_diff_lines(
    staged: bool, changed: list[str], *, base_ref: str | None = None,
) -> tuple[bool, str]:
    targets = behavior_prompt_targets(changed)
    if not targets:
        return True, "no behavior command/agent files changed"
    if base_ref:
        n = get_diff_line_count_ci(base_ref, targets)
    else:
        n = get_diff_line_count(staged, targets)
    if n > MAX_DIFF_LINES:
        return False, f"changed {n} lines in {', '.join(targets)} (max {MAX_DIFF_LINES})"
    return True, f"{n} line(s) changed"


# ---------------------------------------------------------------------------
# Check 2: eval isolation
# ---------------------------------------------------------------------------
def check_eval_isolation(changed: list[str]) -> tuple[bool, str]:
    evals = [f for f in changed if f.startswith("evals/")]
    if evals:
        return False, f"evals/ modified with behavior commands/agents: {', '.join(evals[:3])}"
    return True, "no evals/ files in this commit"


# ---------------------------------------------------------------------------
# Check 3: golden codebase invariants
# ---------------------------------------------------------------------------
def _needs_live_exec(cmd: str) -> bool:
    return any(v in cmd for v in LIVE_EXEC_VARS)


def _eval_progress_file(name: str) -> pathlib.Path:
    configured = os.environ.get("EZPOWERS_EVAL_PROGRESS_FILE")
    if configured:
        return pathlib.Path(configured)
    return EVALS_ROOT / "results" / "runs" / name


def _print_progress(message: str) -> None:
    print(f"[progress] {message}", file=sys.stderr, flush=True)


def check_golden(
    command_timeout_seconds: int = DEFAULT_EVAL_COMMAND_TIMEOUT_SECONDS,
    case_timeout_seconds: int = DEFAULT_VALIDATE_TIMEOUT_SECONDS,
    progress_file: str | pathlib.Path | None = None,
) -> tuple[bool, str]:
    """Run golden eval deterministic graders that don't need live execution."""
    if not GOLDEN_DIR.exists():
        return True, "no golden directory"

    cases = sorted(GOLDEN_DIR.glob("*.yaml"))
    if not cases:
        return True, "no golden cases"

    failures: list[str] = []
    total_run = 0
    total_pass = 0

    for case_path in cases:
        case = rb.load_case(case_path)
        case_id = case.get("case_id", case_path.stem)
        deadline = time.monotonic() + case_timeout_seconds
        rb.write_progress(progress_file, {
            "runner": "validate",
            "phase": "golden_case_start",
            "case_id": case_id,
            "case_path": str(case_path),
            "timeout_seconds": case_timeout_seconds,
        })
        _print_progress(
            f"golden {case_id} ({case_path}) "
            f"case_timeout={case_timeout_seconds}s command_timeout={command_timeout_seconds}s"
        )

        for grader in case.get("graders", []):
            if grader.get("type") != "deterministic_tests":
                continue

            var_map, val_map, temp_files = rb._prepare_mock_files(case)
            try:
                for cmd in grader.get("commands", []):
                    if "grader placeholder" in cmd:
                        continue

                    resolved = rb._substitute_vars(cmd, var_map, val_map)

                    # Skip graders needing live execution output
                    if _needs_live_exec(resolved):
                        continue

                    total_run += 1
                    run_timeout = rb._remaining_timeout(deadline, command_timeout_seconds)
                    if run_timeout <= 0:
                        failures.append(f"{case_id}: CASE TIMEOUT before {cmd}")
                        break
                    rb.write_progress(progress_file, {
                        "runner": "validate",
                        "phase": "golden_command_start",
                        "case_id": case_id,
                        "case_path": str(case_path),
                        "command": cmd,
                        "timeout_seconds": round(run_timeout, 3),
                    })
                    _print_progress(
                        f"golden {case_id} command timeout={run_timeout:.1f}s: {cmd}"
                    )
                    try:
                        proc = rb.run_shell_command_with_timeout(
                            resolved,
                            timeout=run_timeout, cwd=str(REPO_ROOT),
                        )
                        if proc.returncode == 0:
                            total_pass += 1
                        else:
                            failures.append(f"{case_id}: {cmd}")
                    except subprocess.TimeoutExpired:
                        failures.append(f"{case_id}: TIMEOUT after {run_timeout:.1f}s {cmd}")
                    except Exception as e:
                        failures.append(f"{case_id}: ERROR {e}")
            finally:
                for tf in temp_files:
                    try:
                        os.unlink(tf)
                    except OSError:
                        pass

    if total_run == 0:
        return True, "no runnable golden graders"

    if failures:
        detail = "; ".join(failures[:3])
        return False, f"{total_pass}/{total_run} passed. FAILED: {detail}"
    return True, f"{total_pass}/{total_run} passed"


# ---------------------------------------------------------------------------
# Baseline helpers
# ---------------------------------------------------------------------------
def _version_key(path: pathlib.Path) -> list[int]:
    """Parse '0.8.0.json' -> [0, 8, 0] for correct numeric sort.

    Non-numeric segments (e.g. '0.8.0-rc1') are split on '-' and the numeric
    prefix is kept; the suffix sorts after pure-numeric versions.
    Files with wholly non-numeric names (e.g. 'latest.json') are warned and
    sort to the front (all zeros) so they never accidentally become "latest".
    """
    raw = path.stem  # e.g. "0.8.0" or "0.8.0-rc1"
    # Strip pre-release suffix: "0.8.0-rc1" -> "0.8.0", tag "rc1"
    base, _, _tag = raw.partition("-")
    parts = base.split(".")
    result = []
    all_non_numeric = True
    for p in parts:
        try:
            result.append(int(p))
            all_non_numeric = False
        except ValueError:
            result.append(0)
    if all_non_numeric:
        print(f"WARNING: non-version baseline filename ignored: {path.name}",
              file=sys.stderr)
    return result


def _latest_baseline() -> dict | None:
    path = _latest_baseline_path()
    if not path:
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _latest_baseline_path() -> pathlib.Path | None:
    if not BASELINES_DIR.exists():
        return None
    baselines = sorted(BASELINES_DIR.glob("*.json"), key=_version_key)
    if not baselines:
        return None
    return baselines[-1]


def _auto_pass_rate(scores: dict) -> float | None:
    """Pass rate among automated (non-null) cases."""
    auto = {k: v for k, v in scores.items() if v is not None}
    if not auto:
        return None
    return sum(1 for v in auto.values() if v) / len(auto)


def _run_split(
    split: str,
    *,
    command_timeout_seconds: int = DEFAULT_EVAL_COMMAND_TIMEOUT_SECONDS,
    case_timeout_seconds: int = DEFAULT_VALIDATE_TIMEOUT_SECONDS,
    progress_file: str | pathlib.Path | None = None,
) -> dict[str, bool | None]:
    split_dir = EVALS_ROOT / split
    if not split_dir.exists():
        return {}
    results = {}
    paths = sorted(split_dir.rglob("*.yaml"))
    for i, p in enumerate(paths, 1):
        case = rb.load_case(p)
        case_id = case.get("case_id", p.stem)
        _print_progress(f"{split} {i}/{len(paths)} {case_id} ({p})")
        r = rb.run_case(
            p,
            model="validate",
            n_trials=1,
            command_timeout_seconds=command_timeout_seconds,
            case_timeout_seconds=case_timeout_seconds,
            progress_file=progress_file,
            progress_stream=sys.stderr,
            case_index=i,
            total_cases=len(paths),
        )
        results[r["case_id"]] = r["pass"]
    return results


# ---------------------------------------------------------------------------
# Check 4: optimization delta >= +0.05 (Blueprint B.4 checklist #2)
# ---------------------------------------------------------------------------
MIN_OPT_DELTA = 0.05


def check_optimization_delta(
    command_timeout_seconds: int = DEFAULT_EVAL_COMMAND_TIMEOUT_SECONDS,
    case_timeout_seconds: int = DEFAULT_VALIDATE_TIMEOUT_SECONDS,
    progress_file: str | pathlib.Path | None = None,
) -> tuple[bool, str]:
    baseline = _latest_baseline()
    if not baseline:
        return True, "no baseline found, skipping"

    bl_scores = baseline.get("scores", {}).get("optimization", {})
    bl_rate = _auto_pass_rate({k: v.get("pass") for k, v in bl_scores.items()})
    if bl_rate is None:
        return True, "no automated optimization cases in baseline"

    current = _run_split(
        "optimization",
        command_timeout_seconds=command_timeout_seconds,
        case_timeout_seconds=case_timeout_seconds,
        progress_file=progress_file,
    )
    cur_rate = _auto_pass_rate(current)
    if cur_rate is None:
        return True, "no automated optimization cases"

    delta = cur_rate - bl_rate
    if delta < 0:
        return False, (
            f"regressed {cur_rate:.0%} vs baseline {bl_rate:.0%} "
            f"(delta {delta:+.1%})"
        )
    # +5% improvement required only in diagnostician workflow (hill-climb).
    # Ad-hoc human commits just need no regression (delta >= 0).
    # The marker is checked but NOT consumed here; it is consumed once in
    # _check_expected_improvements_stub after all checks complete.
    marker = REPO_ROOT / ".expected_improvements.json"
    if marker.exists() and delta < MIN_OPT_DELTA:
        return False, (
            f"insufficient improvement {cur_rate:.0%} vs baseline {bl_rate:.0%} "
            f"(delta {delta:+.1%}, need +{MIN_OPT_DELTA:.0%})"
        )
    return True, f"{cur_rate:.0%} vs baseline {bl_rate:.0%} (delta {delta:+.1%})"


# ---------------------------------------------------------------------------
# Check 5: holdout delta >= -0.05 (Blueprint B.4 checklist #3)
# ---------------------------------------------------------------------------
MAX_HOLDOUT_DROP = -0.05


def check_holdout_delta(
    command_timeout_seconds: int = DEFAULT_EVAL_COMMAND_TIMEOUT_SECONDS,
    case_timeout_seconds: int = DEFAULT_VALIDATE_TIMEOUT_SECONDS,
    progress_file: str | pathlib.Path | None = None,
) -> tuple[bool, str]:
    baseline = _latest_baseline()
    if not baseline:
        return True, "no baseline found, skipping"

    bl_scores = baseline.get("scores", {}).get("holdout", {})
    bl_rate = _auto_pass_rate({k: v.get("pass") for k, v in bl_scores.items()})
    if bl_rate is None:
        return True, "no automated holdout cases in baseline"

    current = _run_split(
        "holdout",
        command_timeout_seconds=command_timeout_seconds,
        case_timeout_seconds=case_timeout_seconds,
        progress_file=progress_file,
    )
    cur_rate = _auto_pass_rate(current)
    if cur_rate is None:
        return True, "no automated holdout cases"

    delta = cur_rate - bl_rate
    if delta < MAX_HOLDOUT_DROP:
        return False, (
            f"holdout dropped {cur_rate:.0%} vs baseline {bl_rate:.0%} "
            f"(delta {delta:+.1%}, max {MAX_HOLDOUT_DROP:+.0%})"
        )
    return True, f"{cur_rate:.0%} vs baseline {bl_rate:.0%} (delta {delta:+.1%})"


# ---------------------------------------------------------------------------
# Check 6: banned expression self-scan
# ---------------------------------------------------------------------------
def check_banned_self_ref(
    staged: bool, changed: list[str], *, base_ref: str | None = None,
) -> tuple[bool, str]:
    targets = [
        f for f in changed
        if f.startswith(("commands/", "agents/")) or f in WORKFLOW_SKILL_PATHS
    ]
    if not targets:
        return True, "no commands/agents files changed"

    if base_ref:
        added_text = get_added_lines_ci(base_ref, targets)
    else:
        added_text = get_added_lines(staged, targets)
    if not added_text.strip():
        return True, "no added lines"

    hits: list[str] = []
    for pat in BANNED_KO:
        if pat in added_text:
            hits.append(pat)
    for pat in BANNED_EN_RE:
        if re.search(pat, added_text, re.IGNORECASE):
            hits.append(re.sub(r"\\[bB]", "", pat))

    if hits:
        return False, f"banned expressions in new text: {', '.join(hits[:5])}"
    return True, "clean"


# ---------------------------------------------------------------------------
# Check 7 (stub): expected_improvements — deferred to propose_edit.py
# ---------------------------------------------------------------------------
def _check_expected_improvements_stub(
    command_timeout_seconds: int = DEFAULT_EVAL_COMMAND_TIMEOUT_SECONDS,
    case_timeout_seconds: int = DEFAULT_VALIDATE_TIMEOUT_SECONDS,
    progress_file: str | pathlib.Path | None = None,
) -> tuple[bool, str]:
    """Blueprint B.4 checklist #6: verify diagnostician's predicted improvements.

    This check only applies when a change was proposed by eval-diagnostician
    via scripts/propose_edit.py.  In that workflow, propose_edit.py writes a
    `.expected_improvements.json` file; validate.py checks whether those case
    IDs actually flipped to pass.

    For ad-hoc human commits (no diagnostician involved), this check is N/A.
    """
    marker = REPO_ROOT / ".expected_improvements.json"
    if not marker.exists():
        return True, "no diagnostician proposal (ad-hoc commit, check N/A)"

    with open(marker, encoding="utf-8") as f:
        expected = json.load(f)

    case_ids: list[str] = expected.get("expected_improvements", [])
    if not case_ids:
        return True, "diagnostician listed no expected improvements"

    # Build case_id -> path index once (avoid O(n*m) rglob per case_id)
    case_index: dict[str, pathlib.Path] = {}
    for split in ("optimization", "holdout", "golden"):
        split_dir = EVALS_ROOT / split
        if split_dir.exists():
            for p in split_dir.rglob("*.yaml"):
                c = rb.load_case(p)
                case_index[c.get("case_id", p.stem)] = p

    missing: list[str] = []
    for cid in case_ids:
        p = case_index.get(cid)
        if not p:
            missing.append(f"{cid} (case not found)")
            continue
        result = rb.run_case(
            p,
            model="validate",
            n_trials=1,
            command_timeout_seconds=command_timeout_seconds,
            case_timeout_seconds=case_timeout_seconds,
            progress_file=progress_file,
            progress_stream=sys.stderr,
        )
        if not result["pass"]:
            missing.append(cid)

    if missing:
        return False, f"expected improvements not realized: {', '.join(missing)}"

    # Consume the marker so it does not affect subsequent ad-hoc commits.
    try:
        marker.unlink()
    except OSError:
        pass
    return True, f"{len(case_ids)} expected improvement(s) confirmed"


# ---------------------------------------------------------------------------
# Skill regression gate
# ---------------------------------------------------------------------------
def check_skill_evals(
    staged: bool,
    timeout_seconds: int = DEFAULT_VALIDATE_TIMEOUT_SECONDS,
    progress_file: str | pathlib.Path | None = None,
) -> tuple[bool, str]:
    cmd = [sys.executable, "scripts/run_skill_evals.py"]
    if staged:
        cmd.append("--staged")
    cmd.extend(["--timeout-seconds", str(timeout_seconds)])
    if progress_file:
        cmd.extend(["--progress-file", str(progress_file)])
    try:
        proc = rb.run_command_with_timeout(
            cmd,
            cwd=str(REPO_ROOT),
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        output = ((exc.stdout or "") + "\n" + (exc.stderr or "")).strip()
        tail = " | ".join(line.strip() for line in output.splitlines()[-4:] if line.strip())
        where = f"; last progress file: {progress_file}" if progress_file else ""
        detail = tail or "no output before timeout"
        return False, f"timed out after {timeout_seconds}s running {' '.join(cmd)}{where}. {detail}"
    if proc.returncode != 0:
        output = ((proc.stdout or "") + "\n" + (proc.stderr or "")).strip()
        tail = " | ".join(line.strip() for line in output.splitlines()[-4:] if line.strip())
        return False, tail or "skill eval runner failed"
    stdout_tail = " | ".join(line.strip() for line in (proc.stdout or "").splitlines()[-4:] if line.strip())
    stderr_tail = " | ".join(line.strip() for line in (proc.stderr or "").splitlines()[-4:] if line.strip())
    tail = stdout_tail or stderr_tail
    return True, tail or "skill evals passed"


# ---------------------------------------------------------------------------
# Canonical Bullet Coverage check (W2+W4)
# ---------------------------------------------------------------------------
_RULE_BULLET_RE = re.compile(r"^- `")


def _normalize_rule(text: str) -> str:
    """Keep condition + verdict keyword, strip trailing message/context."""
    arrow_idx = text.find("\u2192")
    if arrow_idx == -1:
        return text.strip()
    after_arrow = text[arrow_idx + 1:].strip()
    verdict = after_arrow.split(":")[0].split(".")[0].strip()
    return (text[:arrow_idx].strip() + " \u2192 " + verdict).strip()


def _extract_section_bullets(path: pathlib.Path, heading: str) -> list[str]:
    """Extract rule bullets (backtick-prefixed) from a markdown section."""
    lines = path.read_text(encoding="utf-8").splitlines()
    in_section = False
    bullets: list[str] = []
    for line in lines:
        if line.startswith(heading):
            in_section = True
            continue
        if in_section and line.startswith("## ") and not line.startswith(heading):
            break
        if in_section and line.startswith("### "):
            continue
        if in_section and _RULE_BULLET_RE.match(line):
            bullets.append(_normalize_rule(line.strip()))
    return bullets


def check_doc_consistency() -> tuple[bool, str]:
    """Bidirectional canonical bullet coverage across CONSISTENCY_PAIRS."""
    errors: list[str] = []
    for pair in CONSISTENCY_PAIRS:
        src_path = REPO_ROOT / pair["source"]
        candidates = pair.get("consumer_candidates", [pair["consumer"]])
        con_path = next(
            (REPO_ROOT / c for c in candidates if (REPO_ROOT / c).exists()),
            REPO_ROOT / pair["consumer"],
        )
        if not src_path.exists() or not con_path.exists():
            errors.append(f"{pair['name']}: missing file")
            continue
        src_bullets = _extract_section_bullets(src_path, pair["source_heading"])
        con_bullets = _extract_section_bullets(con_path, pair["consumer_heading"])
        if not src_bullets:
            errors.append(f"{pair['name']}: no source bullets found under {pair['source_heading']}")
            continue
        # Source -> Consumer: every source rule must appear in consumer
        for b in src_bullets:
            if b not in con_bullets:
                errors.append(f"{pair['name']}: source rule not in consumer: {b}")
        # Consumer -> Source: consumer-only rules are orphaned/contradicting
        for b in con_bullets:
            if b not in src_bullets:
                errors.append(f"{pair['name']}: consumer rule not in source (orphaned): {b}")
    if errors:
        return False, "; ".join(errors)
    checked = ", ".join(p["name"] for p in CONSISTENCY_PAIRS)
    return True, f"all pairs consistent ({checked})"


# ---------------------------------------------------------------------------
# Eval corpus/schema/baseline synchronization
# ---------------------------------------------------------------------------
def _command_eval_case_paths() -> list[pathlib.Path]:
    paths: list[pathlib.Path] = []
    for split in COMMAND_EVAL_SPLITS:
        split_dir = EVALS_ROOT / split
        if split_dir.exists():
            paths.extend(sorted(split_dir.rglob("*.yaml")))
    return paths


def _case_inventory() -> dict[str, list[str]]:
    inventory = {split: [] for split in COMMAND_EVAL_SPLITS}
    for path in _command_eval_case_paths():
        case = rb.load_case(path)
        split = str(case.get("split", ""))
        case_id = str(case.get("case_id", path.stem))
        inventory.setdefault(split, []).append(case_id)
    for split in inventory:
        inventory[split] = sorted(inventory[split])
    return inventory


def _parse_index_counts() -> dict[str, int]:
    index_path = EVALS_ROOT / "INDEX.md"
    if not index_path.exists():
        return {}
    text = index_path.read_text(encoding="utf-8")
    labels = {
        "optimization": "Optimization",
        "holdout": "Holdout",
        "golden": "Golden",
        "honeypot": "Honeypot",
        "skill": "Skill",
    }
    counts: dict[str, int] = {}
    for key, label in labels.items():
        match = re.search(rf"^- {re.escape(label)}:\s*(\d+)\b", text, re.M)
        if match:
            counts[key] = int(match.group(1))
    return counts


def _plugin_baseline_path() -> str | None:
    plugin_path = REPO_ROOT / ".codex-plugin" / "plugin.json"
    if not plugin_path.exists():
        return None
    with open(plugin_path, encoding="utf-8") as f:
        data = json.load(f)
    value = data.get("metadata", {}).get("eval_baseline_path")
    return str(value) if value else None


def check_eval_sync() -> tuple[bool, str]:
    paths = _command_eval_case_paths()
    errors = rb.validate_cases(paths)

    inventory = _case_inventory()
    index_counts = _parse_index_counts()
    expected_counts = {split: len(inventory.get(split, [])) for split in COMMAND_EVAL_SPLITS}
    expected_counts["skill"] = len(list((EVALS_ROOT / "skills").glob("*.yaml")))
    for key, expected in expected_counts.items():
        actual = index_counts.get(key)
        if actual != expected:
            errors.append(f"evals/INDEX.md {key} count is {actual}, expected {expected}")

    baseline_path = _latest_baseline_path()
    if not baseline_path:
        errors.append("no baseline JSON found")
    else:
        baseline_rel = baseline_path.relative_to(REPO_ROOT).as_posix()
        plugin_baseline = _plugin_baseline_path()
        if plugin_baseline is not None and plugin_baseline != baseline_rel:
            errors.append(
                f".codex-plugin metadata baseline is {plugin_baseline!r}, expected {baseline_rel!r}"
            )

        with open(baseline_path, encoding="utf-8") as f:
            baseline = json.load(f)
        scores = baseline.get("scores", {})
        for split, current_ids in inventory.items():
            current = set(current_ids)
            recorded = set(scores.get(split, {}))
            if current != recorded:
                missing = sorted(current - recorded)
                extra = sorted(recorded - current)
                details = []
                if missing:
                    details.append(f"missing {split}: {', '.join(missing[:5])}")
                if extra:
                    details.append(f"extra {split}: {', '.join(extra[:5])}")
                errors.append(f"{baseline_rel} case set mismatch ({'; '.join(details)})")

    if errors:
        return False, "; ".join(errors[:6])

    total = sum(len(v) for v in inventory.values())
    latest = baseline_path.relative_to(REPO_ROOT).as_posix() if baseline_path else "none"
    return True, f"{total} command cases synced with {latest}"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(description="EZPowers eval gate")
    parser.add_argument(
        "--staged", action="store_true",
        help="Check staged changes (pre-commit mode)",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=lambda value: rb.parse_timeout(value, DEFAULT_VALIDATE_TIMEOUT_SECONDS, "--timeout-seconds"),
        default=rb.env_timeout("EZPOWERS_VALIDATE_TIMEOUT_SECONDS", DEFAULT_VALIDATE_TIMEOUT_SECONDS),
        help=(
            "Per-case and child-runner timeout in seconds "
            "(default: env EZPOWERS_VALIDATE_TIMEOUT_SECONDS or 300)"
        ),
    )
    parser.add_argument(
        "--command-timeout-seconds",
        type=lambda value: rb.parse_timeout(value, DEFAULT_EVAL_COMMAND_TIMEOUT_SECONDS, "--command-timeout-seconds"),
        default=rb.env_timeout("EZPOWERS_EVAL_COMMAND_TIMEOUT_SECONDS", DEFAULT_EVAL_COMMAND_TIMEOUT_SECONDS),
        help=(
            "Per deterministic grader command timeout in seconds "
            "(default: env EZPOWERS_EVAL_COMMAND_TIMEOUT_SECONDS or 30)"
        ),
    )
    parser.add_argument(
        "--progress-file",
        default=None,
        help=(
            "JSON file updated before each eval case/command "
            "(default: env EZPOWERS_EVAL_PROGRESS_FILE or evals/results/runs/validate-last-case.json)"
        ),
    )
    # CI headless mode arguments
    parser.add_argument(
        '--ci', action='store_true',
        help='CI mode: auto-detected from CI env vars, or set explicitly. '
             'Enables stricter validation and machine-readable output.',
    )
    parser.add_argument(
        '--output-format', choices=['human', 'json', 'junit'],
        default='human',
        help='Output format. json/junit useful for CI dashboards.',
    )
    parser.add_argument(
        '--changed-files', nargs='*',
        help='Explicit list of changed files (bypasses git diff detection). '
             'Useful in CI where diff base may differ.',
    )
    parser.add_argument(
        '--base-ref', default=None,
        help='Git ref to diff against (default: HEAD~1 for CI, staged for local).',
    )
    args = parser.parse_args()
    progress_file = pathlib.Path(args.progress_file) if args.progress_file else _eval_progress_file("validate-last-case.json")

    # --- CI mode detection ---
    # Only use CI mode when explicitly requested via --ci flag.
    # Auto-detection is informational only — it does NOT override pre-commit behavior.
    # This prevents CI env vars from accidentally hijacking local pre-commit hooks.
    is_ci, ci_env = detect_ci_environment()
    ci_mode = args.ci  # explicit flag only, not auto-detected
    ci_base_ref: str | None = None

    if not args.ci and is_ci:
        providers = ', '.join(ci_env.keys())
        print(f"[CI] Detected CI environment ({providers}) but --ci not set. "
              f"Using local mode. Pass --ci to enable CI mode.", file=sys.stderr)

    if ci_mode:
        if args.staged:
            print("[CI] WARNING: --staged ignored in CI mode (using base-ref diff)",
                  file=sys.stderr)
        ci_base_ref = args.base_ref or 'origin/main'

    # --- Determine changed files ---
    if args.changed_files is not None:
        # Explicit file list provided (CI or local)
        changed = sorted(set(
            f.strip().replace("\\", "/") for f in args.changed_files if f.strip()
        ))
    elif ci_mode:
        assert ci_base_ref is not None
        changed = get_changed_files_ci(ci_base_ref)
    else:
        changed = get_changed_files(args.staged)

    target = behavior_prompt_targets(changed)
    skill_target = [
        f for f in changed
        if (
            f.startswith(("skills/", "evals/skills/"))
            and not f.startswith(WORKFLOW_SKILL_DIR_PREFIXES)
        )
        or f in ("scripts/run_skill_evals.py", "scripts/validate.py", ".githooks/pre-commit")
    ]
    doc_target = [f for f in changed if f.startswith("docs/reference/")]
    eval_sync_target = [
        f for f in changed
        if f.startswith(EVAL_SYNC_PATH_PREFIXES)
        or f in EVAL_SYNC_FILES
    ]

    if not target and not skill_target and not doc_target and not eval_sync_target:
        msg = "No commands/, agents/, docs/reference/, eval, or skill gate files changed. Gate not applicable."
        if args.output_format == 'json':
            print(format_json_output([], ci_mode))
        elif args.output_format == 'junit':
            print(format_junit_output([]))
        else:
            print(msg)
        sys.exit(0)

    # --- Build check list ---
    # In CI mode, pass base_ref to diff-dependent checks
    checks: list[tuple[str, object]] = []
    if target:
        checks.extend([
            ("diff_line_count", lambda: check_diff_lines(
                args.staged, changed, base_ref=ci_base_ref)),
            ("eval_isolation", lambda: check_eval_isolation(changed)),
            (
                "golden_invariants",
                lambda: check_golden(
                    args.command_timeout_seconds,
                    args.timeout_seconds,
                    progress_file,
                ),
            ),
            (
                "optimization_delta",
                lambda: check_optimization_delta(
                    args.command_timeout_seconds,
                    args.timeout_seconds,
                    progress_file,
                ),
            ),
            (
                "holdout_delta",
                lambda: check_holdout_delta(
                    args.command_timeout_seconds,
                    args.timeout_seconds,
                    progress_file,
                ),
            ),
            ("banned_self_ref", lambda: check_banned_self_ref(
                args.staged, changed, base_ref=ci_base_ref)),
            # Blueprint B.4 checklist #6 (expected_improvements) is intentionally
            # deferred: it requires eval-diagnostician output which only exists in
            # the propose_edit.py workflow, not in ad-hoc commits. When diagnostician
            # is used, propose_edit.py will enforce this check separately.
            (
                "expected_improvements",
                lambda: _check_expected_improvements_stub(
                    args.command_timeout_seconds,
                    args.timeout_seconds,
                    progress_file,
                ),
            ),
        ])
    if skill_target:
        checks.append(("skill_evals", lambda: check_skill_evals(args.staged, args.timeout_seconds, progress_file)))
    if target or doc_target:
        checks.append(("doc_consistency", lambda: check_doc_consistency()))
    if eval_sync_target:
        checks.append(("eval_sync", lambda: check_eval_sync()))

    # --- Execute checks and collect results ---
    results: list[tuple[str, bool, str, float]] = []
    any_fail = False
    for name, fn in checks:
        t0 = time.monotonic()
        passed, detail = fn()
        elapsed_ms = (time.monotonic() - t0) * 1000.0
        results.append((name, passed, detail, elapsed_ms))
        if not passed:
            any_fail = True
        # In human mode, print incrementally (same as before)
        if args.output_format == 'human':
            tag = "PASS" if passed else "FAIL"
            print(f"[{tag}] {name}: {detail}")

    # --- Formatted output for non-human modes ---
    if args.output_format == 'json':
        print(format_json_output(results, ci_mode))
    elif args.output_format == 'junit':
        print(format_junit_output(results))

    sys.exit(1 if any_fail else 0)


if __name__ == "__main__":
    main()
