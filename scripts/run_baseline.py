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
import signal
import shutil
import subprocess
import sys
import time

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML required. Install with: pip install pyyaml", file=sys.stderr)
    sys.exit(1)


DEFAULT_COMMAND_TIMEOUT_SECONDS = 30
DEFAULT_CASE_TIMEOUT_SECONDS = 300
CASE_ID_RE = re.compile(r"^[a-z]+\.[a-z0-9_]+\.[0-9]{3}$")
CASE_SPLITS = ("optimization", "holdout", "golden", "honeypot")
CASE_COMMANDS = (
    "setup",
    "brainstorm",
    "plan",
    "choiceexecutor",
    "executeharness",
    "review",
    "sync-docs",
    "pipeline-audit",
    "eval",
    "feedback",
    "set-rules",
)
CASE_DIFFICULTIES = ("single_step", "multi_step", "long_horizon")
CASE_MODEL_FAMILIES = ("sonnet_only", "opus_required", "agnostic")
CASE_LANGUAGES = ("ko", "en", "ko_en_mixed")
CASE_VERIFY_TYPES = ("api", "e2e", "cli", "lib", "data", "pure")
GRADER_TYPES = (
    "deterministic_tests",
    "banned_expression_scan",
    "llm_rubric",
    "state_check",
    "tool_calls",
)
LIVE_EXEC_VARS = ("$REVIEW_OUTPUT", "$EXECUTOR_OUTPUT")


def parse_timeout(value: str | int | None, default: int, label: str) -> int:
    """Parse a positive timeout value from CLI args or environment."""
    if value is None or value == "":
        return default
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise argparse.ArgumentTypeError(f"{label} must be an integer") from exc
    if parsed < 1:
        raise argparse.ArgumentTypeError(f"{label} must be >= 1")
    return parsed


def env_timeout(name: str, default: int) -> int:
    return parse_timeout(os.environ.get(name), default, name)


def utc_timestamp() -> str:
    return datetime.datetime.now(datetime.UTC).isoformat().replace("+00:00", "Z")


def write_progress(progress_file: str | pathlib.Path | None, payload: dict) -> None:
    if not progress_file:
        return
    path = pathlib.Path(progress_file)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {"timestamp": utc_timestamp(), **payload}
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _remaining_timeout(deadline: float | None, requested: int) -> float:
    if deadline is None:
        return float(requested)
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        return 0.0
    return min(float(requested), remaining)


def _default_progress_file(evals_root: pathlib.Path) -> pathlib.Path:
    configured = os.environ.get("EZPOWERS_EVAL_PROGRESS_FILE")
    if configured:
        return pathlib.Path(configured)
    return evals_root / "results" / "runs" / "last_eval_case.json"


def _kill_process_tree(proc: subprocess.Popen) -> None:
    if proc.poll() is not None:
        return
    if os.name == "nt":
        try:
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=5,
                check=False,
            )
            return
        except Exception:
            pass
    else:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
            return
        except Exception:
            pass
    try:
        proc.kill()
    except Exception:
        pass


def find_bash() -> str | None:
    candidates: list[str] = []
    bash = shutil.which("bash")
    if bash:
        candidates.append(bash)
    if os.name == "nt":
        candidates.extend(str(p) for p in [
            pathlib.Path(os.environ.get("ProgramFiles", "C:/Program Files")) / "Git" / "bin" / "bash.exe",
            pathlib.Path(os.environ.get("ProgramFiles", "C:/Program Files")) / "Git" / "usr" / "bin" / "bash.exe",
            pathlib.Path(os.environ.get("ProgramFiles(x86)", "C:/Program Files (x86)")) / "Git" / "bin" / "bash.exe",
        ])
    for candidate in candidates:
        if not pathlib.Path(candidate).exists():
            continue
        try:
            proc = subprocess.run(
                [candidate, "-lc", "true"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=5,
                check=False,
            )
        except Exception:
            continue
        if proc.returncode == 0:
            return candidate
    return None


def run_command_with_timeout(
    args,
    *,
    timeout: float,
    cwd: str | pathlib.Path,
    shell: bool = False,
    input_text: str | None = None,
) -> subprocess.CompletedProcess:
    popen_kwargs = {
        "cwd": str(cwd),
        "shell": shell,
        "stdout": subprocess.PIPE,
        "stderr": subprocess.PIPE,
        "text": True,
        "encoding": "utf-8",
        "errors": "replace",
    }
    if input_text is not None:
        popen_kwargs["stdin"] = subprocess.PIPE
    if os.name != "nt":
        popen_kwargs["start_new_session"] = True
    proc = subprocess.Popen(args, **popen_kwargs)
    try:
        stdout, stderr = proc.communicate(input=input_text, timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        _kill_process_tree(proc)
        try:
            stdout, stderr = proc.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            stdout = exc.output or ""
            stderr = exc.stderr or ""
            for stream in (proc.stdin, proc.stdout, proc.stderr):
                try:
                    if stream:
                        stream.close()
                except Exception:
                    pass
        raise subprocess.TimeoutExpired(
            cmd=args,
            timeout=timeout,
            output=stdout,
            stderr=stderr,
        ) from exc
    return subprocess.CompletedProcess(args, proc.returncode, stdout, stderr)


def load_case(path: pathlib.Path) -> dict:
    """Load and return a single eval case YAML."""
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def validate_case_schema(path: pathlib.Path, case: dict) -> list[str]:
    """Validate the command-eval schema without adding a jsonschema dependency."""
    errors: list[str] = []
    if not isinstance(case, dict):
        return [f"{path}: case must be a mapping"]

    for key in ("case_id", "split", "stratum", "input", "graders", "tracked_metrics"):
        if key not in case:
            errors.append(f"missing {key}")

    case_id = str(case.get("case_id", ""))
    if not CASE_ID_RE.match(case_id):
        errors.append("case_id must match <split>.<slug_with_digits_or_underscores>.<seq>")

    split = case.get("split")
    if split not in CASE_SPLITS:
        errors.append(f"split must be one of {', '.join(CASE_SPLITS)}")
    elif case_id and not case_id.startswith(f"{split}."):
        errors.append("case_id prefix must match split")

    stratum = case.get("stratum")
    if not isinstance(stratum, dict):
        errors.append("stratum must be a mapping")
    else:
        for key in ("command", "difficulty", "pattern", "model_family", "language"):
            if key not in stratum:
                errors.append(f"stratum missing {key}")
        if stratum.get("command") not in CASE_COMMANDS:
            errors.append(f"stratum.command invalid: {stratum.get('command')!r}")
        if stratum.get("difficulty") not in CASE_DIFFICULTIES:
            errors.append(f"stratum.difficulty invalid: {stratum.get('difficulty')!r}")
        if stratum.get("model_family") not in CASE_MODEL_FAMILIES:
            errors.append(f"stratum.model_family invalid: {stratum.get('model_family')!r}")
        if stratum.get("language") not in CASE_LANGUAGES:
            errors.append(f"stratum.language invalid: {stratum.get('language')!r}")
        verify_type = stratum.get("verify_type")
        if verify_type is not None and verify_type not in CASE_VERIFY_TYPES:
            errors.append(f"stratum.verify_type invalid: {verify_type!r}")

    input_block = case.get("input")
    if not isinstance(input_block, dict):
        errors.append("input must be a mapping")
    elif "user_message" not in input_block:
        errors.append("input missing user_message")

    graders = case.get("graders")
    if not isinstance(graders, list) or not graders:
        errors.append("graders must be a non-empty list")
    else:
        for i, grader in enumerate(graders, 1):
            if not isinstance(grader, dict):
                errors.append(f"grader {i} must be a mapping")
                continue
            if grader.get("type") not in GRADER_TYPES:
                errors.append(f"grader {i} has invalid type: {grader.get('type')!r}")

    if not isinstance(case.get("tracked_metrics"), dict):
        errors.append("tracked_metrics must be a mapping")

    return [f"{path}: {error}" for error in errors]


def validate_cases(case_paths: list[pathlib.Path]) -> list[str]:
    errors: list[str] = []
    seen: dict[str, pathlib.Path] = {}
    for path in case_paths:
        case = load_case(path)
        errors.extend(validate_case_schema(path, case))
        case_id = str(case.get("case_id", path.stem)) if isinstance(case, dict) else path.stem
        if case_id in seen:
            errors.append(f"{path}: duplicate case_id also used by {seen[case_id]}")
        else:
            seen[case_id] = path
    return errors


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


def _substitute_vars_legacy(cmd: str, var_map: dict, val_map: dict) -> str:
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
            escaped = path.replace("'", "'\"'\"'")
            cmd = cmd.replace(placeholder, f"'{escaped}'")

    return cmd


def _substitute_vars(cmd: str, var_map: dict, val_map: dict) -> str:
    """Replace variable placeholders, longest first to avoid prefix collisions."""
    file_vars = sorted(var_map.items(), key=lambda item: len(item[0]), reverse=True)
    value_vars = sorted(val_map.items(), key=lambda item: len(item[0]), reverse=True)

    for placeholder, path in file_vars:
        if placeholder.startswith("$MOCK_"):
            for quote in ("'", '"'):
                echo_pat = f"echo {quote}{placeholder}{quote}"
                if echo_pat in cmd:
                    cmd = cmd.replace(echo_pat, f'cat "{path}"')
                    break

    for placeholder, value in value_vars:
        for quote in ("'", '"'):
            quoted_pat = f"{quote}{placeholder}{quote}"
            if quoted_pat in cmd:
                cmd = cmd.replace(quoted_pat, f"{quote}{value}{quote}")
                break

    for placeholder, path in file_vars:
        if placeholder in cmd:
            escaped = path.replace("'", "'\"'\"'")
            cmd = cmd.replace(placeholder, f"'{escaped}'")

    return cmd


def _needs_live_exec(cmd: str) -> bool:
    return any(var in cmd for var in LIVE_EXEC_VARS)


def run_deterministic_grader(
    commands: list[str],
    case: dict,
    *,
    command_timeout_seconds: int = DEFAULT_COMMAND_TIMEOUT_SECONDS,
    case_deadline: float | None = None,
    case_id: str = "",
    case_path: pathlib.Path | None = None,
    progress_file: str | pathlib.Path | None = None,
    progress_stream=None,
) -> dict:
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
    runnable_commands = [c for c in commands if "grader placeholder" not in c]
    command_number = 0
    executed_commands = 0

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

            command_number += 1
            resolved_cmd = _substitute_vars(cmd, var_map, val_map)
            if _needs_live_exec(resolved_cmd):
                results.append({
                    "command": cmd,
                    "status": "skipped",
                    "reason": "requires live execution output",
                })
                continue

            run_timeout = _remaining_timeout(case_deadline, command_timeout_seconds)
            if run_timeout <= 0:
                all_pass = False
                results.append({
                    "command": cmd,
                    "status": "timeout",
                    "timeout_seconds": 0,
                    "reason": "case timeout reached before command started",
                })
                break

            write_progress(progress_file, {
                "runner": "run_baseline",
                "phase": "grader_command_start",
                "case_id": case_id or case.get("case_id", ""),
                "case_path": str(case_path) if case_path else "",
                "command_index": command_number,
                "total_commands": len(runnable_commands),
                "command": cmd,
                "timeout_seconds": round(run_timeout, 3),
            })
            if progress_stream is not None:
                print(
                    f"[progress] {case_id or case.get('case_id', '')} "
                    f"command {command_number}/{len(runnable_commands)} "
                    f"timeout={run_timeout:.1f}s: {cmd}",
                    file=progress_stream,
                    flush=True,
                )
            try:
                executed_commands += 1
                # Prefer bash for Unix-style grader commands; fall back to shell=True
                bash_path = find_bash()
                if bash_path:
                    proc = run_command_with_timeout(
                        [bash_path, "-c", resolved_cmd],
                        timeout=run_timeout, cwd=os.getcwd(),
                    )
                else:
                    proc = run_command_with_timeout(
                        resolved_cmd, shell=True,
                        timeout=run_timeout, cwd=os.getcwd(),
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
            except subprocess.TimeoutExpired as exc:
                all_pass = False
                results.append({
                    "command": cmd,
                    "status": "timeout",
                    "timeout_seconds": round(run_timeout, 3),
                    "stderr": (exc.stderr or "")[:200] if isinstance(exc.stderr, str) else "",
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

    return {"pass": all_pass if executed_commands else None, "results": results}


def run_graders(
    case: dict,
    *,
    command_timeout_seconds: int = DEFAULT_COMMAND_TIMEOUT_SECONDS,
    case_deadline: float | None = None,
    case_id: str = "",
    case_path: pathlib.Path | None = None,
    progress_file: str | pathlib.Path | None = None,
    progress_stream=None,
) -> dict:
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

            result = run_deterministic_grader(
                commands,
                case,
                command_timeout_seconds=command_timeout_seconds,
                case_deadline=case_deadline,
                case_id=case_id,
                case_path=case_path,
                progress_file=progress_file,
                progress_stream=progress_stream,
            )
            if result["pass"] is None:
                grader_results.append({
                    "type": gtype,
                    "status": "skipped",
                    "reason": "requires live execution output",
                    "details": result["results"],
                })
                continue

            has_runnable = True
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


def run_case(
    case_path: pathlib.Path,
    model: str,
    n_trials: int = 1,
    *,
    command_timeout_seconds: int | None = None,
    case_timeout_seconds: int | None = None,
    progress_file: str | pathlib.Path | None = None,
    progress_stream=None,
    case_index: int | None = None,
    total_cases: int | None = None,
) -> dict:
    """Run a single eval case and return results.

    In v1, this runs graders against current codebase state.
    Live execution (spawning Claude) is not yet implemented.
    """
    command_timeout_seconds = (
        DEFAULT_COMMAND_TIMEOUT_SECONDS
        if command_timeout_seconds is None
        else command_timeout_seconds
    )
    case_timeout_seconds = (
        DEFAULT_CASE_TIMEOUT_SECONDS
        if case_timeout_seconds is None
        else case_timeout_seconds
    )
    case = load_case(case_path)

    # Extract metadata
    case_id = case.get("case_id", case_path.stem)
    split = case.get("split", "unknown")
    stratum = case.get("stratum", {})
    deadline = time.monotonic() + case_timeout_seconds

    write_progress(progress_file, {
        "runner": "run_baseline",
        "phase": "case_start",
        "case_id": case_id,
        "case_path": str(case_path),
        "case_index": case_index,
        "total_cases": total_cases,
        "timeout_seconds": case_timeout_seconds,
    })
    if progress_stream is not None:
        prefix = f"[{case_index}/{total_cases}] " if case_index and total_cases else ""
        print(
            f"[progress] {prefix}{case_id} ({case_path}) "
            f"case_timeout={case_timeout_seconds}s command_timeout={command_timeout_seconds}s",
            file=progress_stream,
            flush=True,
        )

    # Run graders
    grader_result = run_graders(
        case,
        command_timeout_seconds=command_timeout_seconds,
        case_deadline=deadline,
        case_id=case_id,
        case_path=case_path,
        progress_file=progress_file,
        progress_stream=progress_stream,
    )

    result = {
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
    write_progress(progress_file, {
        "runner": "run_baseline",
        "phase": "case_done",
        "case_id": case_id,
        "case_path": str(case_path),
        "case_index": case_index,
        "total_cases": total_cases,
        "pass": result["pass"],
        "mode": result["mode"],
    })
    return result


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


def _golden_failures(results: list[dict]) -> list[str]:
    failures = []
    for r in results:
        if r["split"] == "golden" and r["pass"] is not True:
            failures.append(r["case_id"])
    return failures


def enforce_golden_baseline_gate(
    results: list[dict],
    *,
    evals_root: pathlib.Path,
    model: str,
    command_timeout_seconds: int,
    case_timeout_seconds: int,
    progress_file: pathlib.Path,
) -> None:
    """Block baseline recording unless every current golden case passes."""
    golden_paths = discover_cases(evals_root, ["golden"])
    golden_ids = {load_case(p).get("case_id", p.stem) for p in golden_paths}
    result_ids = {r["case_id"] for r in results if r["split"] == "golden"}

    golden_results = [r for r in results if r["split"] == "golden"]
    if golden_ids - result_ids:
        golden_results = []
        for i, path in enumerate(golden_paths, 1):
            golden_results.append(
                run_case(
                    path,
                    model,
                    command_timeout_seconds=command_timeout_seconds,
                    case_timeout_seconds=case_timeout_seconds,
                    progress_file=progress_file,
                    progress_stream=sys.stderr,
                    case_index=i,
                    total_cases=len(golden_paths),
                )
            )

    failures = _golden_failures(golden_results)
    if failures:
        passed = len(golden_results) - len(failures)
        total = len(golden_results)
        print(
            f"BLOCKED: golden must pass {total}/{total}. "
            f"Currently {passed}/{total} passing. "
            f"Failures: {', '.join(failures[:5])}",
            file=sys.stderr,
        )
        raise SystemExit(1)


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
    parser.add_argument(
        "--timeout-seconds",
        type=lambda value: parse_timeout(value, DEFAULT_CASE_TIMEOUT_SECONDS, "--timeout-seconds"),
        default=env_timeout("EZPOWERS_EVAL_TIMEOUT_SECONDS", DEFAULT_CASE_TIMEOUT_SECONDS),
        help=(
            "Per-case timeout in seconds "
            "(default: env EZPOWERS_EVAL_TIMEOUT_SECONDS or 300)"
        ),
    )
    parser.add_argument(
        "--command-timeout-seconds",
        type=lambda value: parse_timeout(value, DEFAULT_COMMAND_TIMEOUT_SECONDS, "--command-timeout-seconds"),
        default=env_timeout("EZPOWERS_EVAL_COMMAND_TIMEOUT_SECONDS", DEFAULT_COMMAND_TIMEOUT_SECONDS),
        help=(
            "Per-grader-command timeout in seconds "
            "(default: env EZPOWERS_EVAL_COMMAND_TIMEOUT_SECONDS or 30)"
        ),
    )
    parser.add_argument(
        "--progress-file",
        default=None,
        help=(
            "JSON file updated before each case/command "
            "(default: env EZPOWERS_EVAL_PROGRESS_FILE or evals/results/runs/last_eval_case.json)"
        ),
    )

    args = parser.parse_args()
    evals_root = pathlib.Path(args.evals_root)
    progress_file = pathlib.Path(args.progress_file) if args.progress_file else _default_progress_file(evals_root)

    # Discover cases
    if args.cases:
        case_paths = [pathlib.Path(c) for c in args.cases]
    else:
        case_paths = discover_cases(evals_root, args.splits)

    if not case_paths:
        print("ERROR: no eval cases found", file=sys.stderr)
        sys.exit(1)

    schema_errors = validate_cases(case_paths)
    if schema_errors:
        print("ERROR: eval case schema validation failed", file=sys.stderr)
        for error in schema_errors[:20]:
            print(f"  - {error}", file=sys.stderr)
        if len(schema_errors) > 20:
            print(f"  ... {len(schema_errors) - 20} more", file=sys.stderr)
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

        result = run_case(
            path,
            args.model,
            command_timeout_seconds=args.command_timeout_seconds,
            case_timeout_seconds=args.timeout_seconds,
            progress_file=progress_file,
            progress_stream=sys.stderr,
            case_index=i,
            total_cases=len(case_paths),
        )
        results.append(result)

        status = "PASS" if result["pass"] else ("MANUAL" if result["pass"] is None else "FAIL")
        print(status)

    # Compute stats
    stats = compute_stats(results)

    # Write output
    if args.baseline:
        enforce_golden_baseline_gate(
            results,
            evals_root=evals_root,
            model=args.model,
            command_timeout_seconds=args.command_timeout_seconds,
            case_timeout_seconds=args.timeout_seconds,
            progress_file=progress_file,
        )
        baseline_path = evals_root / "results" / "baselines" / f"{args.version}.json"
        write_baseline(baseline_path, args.version, args.model, results, stats)
    else:
        runs_dir = evals_root / "results" / "runs"
        write_run(runs_dir, args.version, args.model, results, stats)

    # Print summary
    print_summary(stats)


if __name__ == "__main__":
    main()
