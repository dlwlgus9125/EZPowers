#!/usr/bin/env python3
"""Run EZPowers eval cases and write baseline/run results.

Self-contained: requires only stdlib + PyYAML.

Usage:
  python scripts/run_baseline.py --version 0.6.0 --splits golden optimization
  python scripts/run_baseline.py --version 0.6.0 --baseline
  python scripts/run_baseline.py --version 0.6.0 --cases evals/golden/banned-expression-detection.yaml
"""

import argparse
import datetime
import json
import os
import pathlib
import re
import subprocess
import sys

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML required. Install with: pip install pyyaml", file=sys.stderr)
    sys.exit(1)


def load_case(path: pathlib.Path) -> dict:
    """Load and return a single eval case YAML."""
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def discover_cases(evals_root: pathlib.Path, splits: list[str]) -> list[pathlib.Path]:
    """Find all .yaml case files under the given splits."""
    cases = []
    for split in splits:
        split_dir = evals_root / split
        if not split_dir.exists():
            print(f"WARNING: split directory not found: {split_dir}", file=sys.stderr)
            continue
        cases.extend(sorted(split_dir.rglob("*.yaml")))
    return cases


def _flatten_mock_data(data: dict, prefix: str = "") -> dict:
    """Flatten nested mock_data dict into {key: string_value} pairs.

    Nested dicts flatten with ``_`` separator; lists serialize to YAML text;
    booleans lowercase (``true``/``false``).
    """
    result = {}
    for k, v in data.items():
        full_key = f"{prefix}_{k}" if prefix else k
        if isinstance(v, dict):
            result.update(_flatten_mock_data(v, full_key))
        elif isinstance(v, list):
            result[full_key] = yaml.dump(v, default_flow_style=False, allow_unicode=True)
        elif isinstance(v, bool):
            result[full_key] = str(v).lower()
        elif isinstance(v, str):
            result[full_key] = v
        else:
            result[full_key] = str(v)
    return result


def _prepare_mock_files(case: dict) -> tuple[dict, list]:
    """Write mock_data fields to temp files and return (var_map, temp_file_paths).

    Handles two variable conventions:
      1. Named file vars: spec_content->$SPEC_FILE, plan_content->$PLAN_FILE, etc.
      2. Generic $MOCK_<field>: any mock_data key, including nested (flattened with _).

    Returns a dict of {placeholder_string: temp_path_or_value} and temp file list.
    """
    import tempfile

    var_map = {}   # {placeholder: temp_path}
    val_map = {}   # {placeholder: raw_string_value} — for inline substitution
    temp_files = []
    mock_data = case.get("input", {}).get("mock_data", {})
    if not mock_data:
        return var_map, val_map, temp_files

    # 1. Named file variables
    field_to_var = {
        "spec_content": "$SPEC_FILE",
        "plan_content": "$PLAN_FILE",
        "review_output": "$REVIEW_OUTPUT",
        "executor_output": "$EXECUTOR_OUTPUT",
    }

    for field, placeholder in field_to_var.items():
        content = mock_data.get(field)
        if content:
            tf = tempfile.NamedTemporaryFile(
                mode="w", suffix=".md", delete=False, encoding="utf-8",
            )
            tf.write(content)
            tf.close()
            var_map[placeholder] = tf.name.replace("\\", "/")
            temp_files.append(tf.name)

    # 2. Generic $MOCK_<field> variables (flattened)
    flat = _flatten_mock_data(mock_data)
    for key, value in flat.items():
        mock_var = f"$MOCK_{key}"
        # Write multi-line or long values to temp files
        if "\n" in value or len(value) > 120:
            tf = tempfile.NamedTemporaryFile(
                mode="w", suffix=".txt", delete=False, encoding="utf-8",
            )
            tf.write(value)
            tf.close()
            var_map[mock_var] = tf.name.replace("\\", "/")
            temp_files.append(tf.name)
        else:
            val_map[mock_var] = value

    return var_map, val_map, temp_files


def _substitute_vars(cmd: str, var_map: dict, val_map: dict) -> str:
    """Replace variable placeholders in grader command strings.

    - ``echo '$MOCK_X'`` / ``echo "$MOCK_X"`` → ``cat "temp_file"``
    - ``'$MOCK_X'`` in comparisons → ``'value'`` (from val_map)
    - ``$SPEC_FILE`` etc. → ``"temp_path"``
    """
    # 1. echo '$MOCK_X' �� cat "tempfile"  (file-backed mock vars)
    for placeholder, path in var_map.items():
        if placeholder.startswith("$MOCK_"):
            for quote in ("'", '"'):
                echo_pat = f"echo {quote}{placeholder}{quote}"
                if echo_pat in cmd:
                    cmd = cmd.replace(echo_pat, f'cat "{path}"')
                    break

    # 2. '$MOCK_X' → 'value' (simple inline vars from val_map)
    for placeholder, value in val_map.items():
        for quote in ("'", '"'):
            quoted_pat = f"{quote}{placeholder}{quote}"
            if quoted_pat in cmd:
                cmd = cmd.replace(quoted_pat, f"{quote}{value}{quote}")
                break

    # 3. Standard file-path vars: $SPEC_FILE, $PLAN_FILE, etc.
    for placeholder, path in var_map.items():
        if placeholder in cmd:
            cmd = cmd.replace(placeholder, f'"{path}"')

    return cmd


def run_deterministic_grader(commands: list[str], case: dict) -> dict:
    """Run deterministic_tests grader commands.

    Returns dict with pass/fail and details.
    Commands are shell commands; exit 0 = pass.
    Variable substitution:
      $SPEC_FILE, $PLAN_FILE, $REVIEW_OUTPUT, $EXECUTOR_OUTPUT
      -> mock_data temp file paths (string-replaced before execution).
    """
    var_map, val_map, temp_files = _prepare_mock_files(case)
    results = []
    all_pass = True

    try:
        for cmd in commands:
            # Skip placeholder graders
            if "grader placeholder" in cmd:
                results.append({
                    "command": cmd,
                    "status": "skipped",
                    "reason": "placeholder grader",
                })
                continue

            resolved_cmd = _substitute_vars(cmd, var_map, val_map)
            try:
                proc = subprocess.run(
                    ["bash", "-c", resolved_cmd],
                    capture_output=True,
                    text=True,
                    timeout=30,
                    cwd=os.getcwd(),
                )
                passed = proc.returncode == 0
                if not passed:
                    all_pass = False
                results.append({
                    "command": cmd,
                    "status": "pass" if passed else "fail",
                    "returncode": proc.returncode,
                    "stderr": proc.stderr[:200] if proc.stderr else "",
                })
            except subprocess.TimeoutExpired:
                all_pass = False
                results.append({
                    "command": cmd,
                    "status": "timeout",
                })
            except Exception as e:
                all_pass = False
                results.append({
                    "command": cmd,
                    "status": "error",
                    "error": str(e)[:200],
                })
    finally:
        for tf_path in temp_files:
            try:
                os.unlink(tf_path)
            except OSError:
                pass

    return {"pass": all_pass, "results": results}


def run_graders(case: dict) -> dict:
    """Run all graders for a case. Returns aggregated result."""
    grader_results = []
    overall_pass = True
    has_runnable = False

    for grader in case.get("graders", []):
        gtype = grader["type"]

        if gtype == "deterministic_tests":
            commands = grader.get("commands", [])
            # Check if all commands are placeholders
            non_placeholder = [c for c in commands if "grader placeholder" not in c]
            if not non_placeholder:
                grader_results.append({
                    "type": gtype,
                    "status": "skipped",
                    "reason": "all commands are placeholders",
                })
                continue

            has_runnable = True
            result = run_deterministic_grader(commands, case)
            if not result["pass"]:
                overall_pass = False
            grader_results.append({
                "type": gtype,
                "status": "pass" if result["pass"] else "fail",
                "details": result["results"],
            })

        elif gtype == "banned_expression_scan":
            # In baseline mode, this checks if the grader is configured
            # Actual scan happens during live execution
            grader_results.append({
                "type": gtype,
                "status": "not_run",
                "reason": "requires live execution output to scan",
            })

        elif gtype == "llm_rubric":
            # Skip in v1 — requires separate Claude call
            grader_results.append({
                "type": gtype,
                "status": "not_run",
                "reason": "LLM rubric grading not implemented in v1",
                "rubric": grader.get("rubric", ""),
                "assertions": grader.get("assertions", []),
            })

        elif gtype == "state_check":
            # Check expected file existence
            expect = grader.get("expect", {})
            files_created = expect.get("files_created", [])
            if files_created:
                has_runnable = True
                missing = [f for f in files_created if not pathlib.Path(f).exists()]
                passed = len(missing) == 0
                if not passed:
                    overall_pass = False
                grader_results.append({
                    "type": gtype,
                    "status": "pass" if passed else "fail",
                    "missing_files": missing,
                })
            else:
                grader_results.append({
                    "type": gtype,
                    "status": "not_run",
                    "reason": "no files_created expectations",
                })

        elif gtype == "tool_calls":
            grader_results.append({
                "type": gtype,
                "status": "not_run",
                "reason": "requires live execution trace",
            })

        else:
            grader_results.append({
                "type": gtype,
                "status": "not_run",
                "reason": f"unknown grader type: {gtype}",
            })

    # If no runnable graders, mark as manual
    if not has_runnable:
        return {
            "pass": None,
            "mode": "manual",
            "reason": "no automated graders available — requires live execution",
            "graders": grader_results,
        }

    return {
        "pass": overall_pass,
        "mode": "automated",
        "graders": grader_results,
    }


def run_case(case_path: pathlib.Path, model: str, n_trials: int = 1) -> dict:
    """Run a single eval case and return results.

    In v1, this runs graders against current codebase state.
    Live execution (spawning Claude) is not yet implemented.
    """
    case = load_case(case_path)

    # Extract metadata
    case_id = case.get("case_id", case_path.stem)
    split = case.get("split", "unknown")
    stratum = case.get("stratum", {})

    # Run graders
    grader_result = run_graders(case)

    return {
        "case_id": case_id,
        "split": split,
        "stratum": stratum,
        "path": str(case_path),
        "model": model,
        "n_trials": n_trials,
        "pass": grader_result["pass"],
        "mode": grader_result["mode"],
        "graders": grader_result.get("graders", []),
        "reason": grader_result.get("reason", ""),
    }


def get_git_sha() -> str:
    """Get current git short SHA."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=10,
        )
        return result.stdout.strip() if result.returncode == 0 else "unknown"
    except Exception:
        return "unknown"


def compute_stats(results: list[dict]) -> dict:
    """Compute aggregate statistics from results."""
    from collections import Counter, defaultdict

    total = len(results)
    automated = [r for r in results if r["mode"] == "automated"]
    manual = [r for r in results if r["mode"] == "manual"]

    auto_pass = sum(1 for r in automated if r["pass"])
    auto_fail = sum(1 for r in automated if not r["pass"])

    by_command = defaultdict(lambda: {"total": 0, "auto": 0, "pass": 0, "manual": 0})
    by_difficulty = defaultdict(lambda: {"total": 0, "auto": 0, "pass": 0})
    by_split = defaultdict(lambda: {"total": 0, "auto": 0, "pass": 0, "manual": 0})

    for r in results:
        cmd = r["stratum"].get("command", "unknown")
        diff = r["stratum"].get("difficulty", "unknown")
        split = r["split"]

        by_command[cmd]["total"] += 1
        by_difficulty[diff]["total"] += 1
        by_split[split]["total"] += 1

        if r["mode"] == "automated":
            by_command[cmd]["auto"] += 1
            by_difficulty[diff]["auto"] += 1
            by_split[split]["auto"] += 1
            if r["pass"]:
                by_command[cmd]["pass"] += 1
                by_difficulty[diff]["pass"] += 1
                by_split[split]["pass"] += 1
        else:
            by_command[cmd]["manual"] += 1
            by_split[split]["manual"] += 1

    return {
        "total_cases": total,
        "automated": len(automated),
        "manual": len(manual),
        "auto_pass": auto_pass,
        "auto_fail": auto_fail,
        "auto_pass_rate": auto_pass / len(automated) if automated else None,
        "by_command": dict(by_command),
        "by_difficulty": dict(by_difficulty),
        "by_split": dict(by_split),
    }


def write_baseline(output_path: pathlib.Path, version: str, model: str,
                   results: list[dict], stats: dict):
    """Write baseline JSON file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    scores = {}
    for r in results:
        split = r["split"]
        if split not in scores:
            scores[split] = {}
        scores[split][r["case_id"]] = {
            "pass": r["pass"],
            "mode": r["mode"],
            "reason": r.get("reason", ""),
        }

    baseline = {
        "version": version,
        "date": datetime.datetime.now(datetime.UTC).isoformat() + "Z",
        "model": model,
        "git_sha": get_git_sha(),
        "scores": scores,
        "stats": stats,
    }

    output_path.write_text(
        json.dumps(baseline, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"Baseline written to: {output_path}")


def write_run(output_dir: pathlib.Path, version: str, model: str,
              results: list[dict], stats: dict):
    """Write run JSONL file."""
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.datetime.now(datetime.UTC).strftime("%Y%m%dT%H%M%S")
    git_sha = get_git_sha()
    output_path = output_dir / f"{timestamp}-{git_sha}.jsonl"

    with open(output_path, "w", encoding="utf-8") as f:
        # Header line
        header = {
            "type": "run_header",
            "version": version,
            "date": datetime.datetime.now(datetime.UTC).isoformat() + "Z",
            "model": model,
            "git_sha": git_sha,
            "stats": stats,
        }
        f.write(json.dumps(header, ensure_ascii=False) + "\n")

        # Per-case lines
        for r in results:
            line = {
                "type": "case_result",
                "case_id": r["case_id"],
                "split": r["split"],
                "pass": r["pass"],
                "mode": r["mode"],
                "stratum": r["stratum"],
            }
            f.write(json.dumps(line, ensure_ascii=False) + "\n")

    print(f"Run written to: {output_path}")


def print_summary(stats: dict):
    """Print human-readable summary to stdout."""
    print("\n" + "=" * 60)
    print("EVAL RUN SUMMARY")
    print("=" * 60)
    print(f"Total cases:  {stats['total_cases']}")
    print(f"Automated:    {stats['automated']}")
    print(f"Manual only:  {stats['manual']}")

    if stats["automated"] > 0:
        rate = stats["auto_pass_rate"]
        print(f"Auto pass:    {stats['auto_pass']}/{stats['automated']}"
              f" ({rate:.0%})" if rate is not None else "")

    print("\nBy split:")
    for split, s in sorted(stats["by_split"].items()):
        auto = s["auto"]
        rate = f"{s['pass']}/{auto} ({s['pass']/auto:.0%})" if auto else "N/A"
        print(f"  {split:15s} total={s['total']:3d}  auto={rate}  manual={s['manual']}")

    print("\nBy command:")
    for cmd, s in sorted(stats["by_command"].items()):
        auto = s["auto"]
        rate = f"{s['pass']}/{auto}" if auto else "manual"
        print(f"  {cmd:20s} total={s['total']:3d}  pass={rate}  manual={s['manual']}")

    print("\nBy difficulty:")
    for diff, s in sorted(stats["by_difficulty"].items()):
        auto = s["auto"]
        rate = f"{s['pass']}/{auto}" if auto else "N/A"
        print(f"  {diff:15s} total={s['total']:3d}  pass={rate}")

    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="Run EZPowers eval cases and write results."
    )
    parser.add_argument("--version", required=True, help="Version label (e.g., 0.6.0)")
    parser.add_argument("--model", default="claude-opus-4-5",
                        help="Model used for evaluation")
    parser.add_argument("--splits", nargs="+",
                        default=["optimization", "holdout", "golden"],
                        help="Splits to run")
    parser.add_argument("--cases", nargs="+", default=None,
                        help="Specific case file paths (overrides --splits)")
    parser.add_argument("--baseline", action="store_true",
                        help="Write results as baseline (to baselines/ dir)")
    parser.add_argument("--evals-root", default="evals",
                        help="Root directory for eval cases")
    parser.add_argument("--dry-run", action="store_true",
                        help="List cases without running")

    args = parser.parse_args()
    evals_root = pathlib.Path(args.evals_root)

    # Discover cases
    if args.cases:
        case_paths = [pathlib.Path(c) for c in args.cases]
    else:
        case_paths = discover_cases(evals_root, args.splits)

    if not case_paths:
        print("ERROR: no eval cases found", file=sys.stderr)
        sys.exit(1)

    print(f"Found {len(case_paths)} eval case(s)")

    if args.dry_run:
        for p in case_paths:
            c = load_case(p)
            print(f"  {c.get('case_id', p.stem):45s} split={c.get('split'):12s} "
                  f"cmd={c.get('stratum', {}).get('command', '?')}")
        return

    # Run cases
    results = []
    for i, path in enumerate(case_paths, 1):
        case = load_case(path)
        case_id = case.get("case_id", path.stem)
        print(f"[{i}/{len(case_paths)}] {case_id} ... ", end="", flush=True)

        result = run_case(path, args.model)
        results.append(result)

        status = "PASS" if result["pass"] else ("MANUAL" if result["pass"] is None else "FAIL")
        print(status)

    # Compute stats
    stats = compute_stats(results)

    # Write output
    if args.baseline:
        baseline_path = evals_root / "results" / "baselines" / f"{args.version}.json"
        write_baseline(baseline_path, args.version, args.model, results, stats)
    else:
        runs_dir = evals_root / "results" / "runs"
        write_run(runs_dir, args.version, args.model, results, stats)

    # Print summary
    print_summary(stats)


if __name__ == "__main__":
    main()
