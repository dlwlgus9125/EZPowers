#!/usr/bin/env python3
"""EZPowers eval gate -- validates commits touching commands/ or agents/.

Checks (in order):
  1. diff_line_count   -- Diff lines <= 3 for commands/ and agents/
  2. eval_isolation     -- evals/ not modified in same commit
  3. golden_invariants  -- Golden codebase-invariant graders all pass
  4. optimization_delta -- Optimization pass rate >= baseline (+5% if diagnostician)
  5. holdout_delta      -- Holdout pass rate not worse than -5% vs baseline
  6. banned_self_ref    -- No banned expressions in added text
  7. expected_improvements -- Diagnostician predictions realized (if applicable)

Each check outputs [PASS|FAIL] <check_name>: <details>.
Exit 0 if all pass, 1 if any fail.

Usage:
  python scripts/validate.py --staged    # pre-commit hook mode
  python scripts/validate.py             # working tree diff mode
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

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
EVALS_ROOT = REPO_ROOT / "evals"
GOLDEN_DIR = EVALS_ROOT / "golden"
BASELINES_DIR = EVALS_ROOT / "results" / "baselines"

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
DEFAULT_VALIDATE_TIMEOUT_SECONDS = 300
DEFAULT_EVAL_COMMAND_TIMEOUT_SECONDS = 30


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


# ---------------------------------------------------------------------------
# Check 1: diff line count
# ---------------------------------------------------------------------------
def check_diff_lines(staged: bool, changed: list[str]) -> tuple[bool, str]:
    targets = [f for f in changed if f.startswith(("commands/", "agents/"))]
    if not targets:
        return True, "no commands/agents files changed"
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
        return False, f"evals/ modified with commands/agents: {', '.join(evals[:3])}"
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
                        bash = shutil.which("bash")
                        if bash:
                            proc = rb.run_command_with_timeout(
                                [bash, "-c", resolved],
                                timeout=run_timeout, cwd=str(REPO_ROOT),
                            )
                        else:
                            proc = rb.run_command_with_timeout(
                                resolved, shell=True,
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
    if not BASELINES_DIR.exists():
        return None
    baselines = sorted(BASELINES_DIR.glob("*.json"), key=_version_key)
    if not baselines:
        return None
    with open(baselines[-1], encoding="utf-8") as f:
        return json.load(f)


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
def check_banned_self_ref(staged: bool, changed: list[str]) -> tuple[bool, str]:
    targets = [f for f in changed if f.startswith(("commands/", "agents/"))]
    if not targets:
        return True, "no commands/agents files changed"

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
    args = parser.parse_args()
    progress_file = pathlib.Path(args.progress_file) if args.progress_file else _eval_progress_file("validate-last-case.json")

    changed = get_changed_files(args.staged)
    target = [f for f in changed if f.startswith(("commands/", "agents/"))]
    skill_target = [
        f for f in changed
        if f.startswith(("skills/", "evals/skills/"))
        or f in ("scripts/run_skill_evals.py", "scripts/validate.py", ".githooks/pre-commit")
    ]

    if not target and not skill_target:
        print("No commands/, agents/, or skill gate files changed. Gate not applicable.")
        sys.exit(0)

    checks = []
    if target:
        checks.extend([
            ("diff_line_count", lambda: check_diff_lines(args.staged, changed)),
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
            ("banned_self_ref", lambda: check_banned_self_ref(args.staged, changed)),
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

    any_fail = False
    for name, fn in checks:
        passed, detail = fn()
        tag = "PASS" if passed else "FAIL"
        print(f"[{tag}] {name}: {detail}")
        if not passed:
            any_fail = True

    sys.exit(1 if any_fail else 0)


if __name__ == "__main__":
    main()
