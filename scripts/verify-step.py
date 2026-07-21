#!/usr/bin/env python3
"""Multi-dimensional step verification for EZPowers harness.

Replaces flat shell exit-0 verification with four assertion dimensions:
  structural  -- file existence, format validation, markdown section presence
  content     -- regex patterns, count thresholds, banned expression scan
  relational  -- cross-file reference integrity (R-ids, file references)
  command     -- backwards-compatible shell command execution (exit 0 = pass)

Usage:
  python scripts/verify-step.py \\
    --step-md phases/my-feature/step0.md \\
    --project-root /path/to/project \\
    --phase my-feature \\
    [--timeout 30]

Output: JSON to stdout. Exit 0 if all dimensions pass, 1 if any fail.
"""

import argparse
import glob
import json
import os
import pathlib
import re
import shlex
import shutil
import signal
import subprocess
import sys

# ---------------------------------------------------------------------------
# Self-contained helpers
#
# This script is installed into target projects by harness-kit, which does NOT
# ship run_baseline.py or shared.py. The shell-execution stack and banned-
# expression constants below are therefore inlined here (previously imported
# from those sibling scripts) so verify-step.py depends only on the standard
# library.
# ---------------------------------------------------------------------------
REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent


# --- Ported from scripts/run_baseline.py -----------------------------------
class InfraError(RuntimeError):
    """Raised when a grader command could not be measured by local infrastructure."""


def _is_access_denied_spawn_error(exc: BaseException) -> bool:
    text = str(exc).lower()
    winerror = getattr(exc, "winerror", None)
    errno = getattr(exc, "errno", None)
    return (
        winerror == 5
        or errno == 13
        or "winerror 5" in text
        or "access is denied" in text
        or "permission denied" in text
    )


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


PYTHON_LAUNCHERS = {"python", "python.exe", "python3", "python3.exe", "py", "py.exe"}
SHELL_CONTROL_TOKENS = {"&&", "||", ";", "|", "|&", "&", "<", ">", ">>", "2>", "2>>"}


def _has_shell_control(token: str) -> bool:
    return token in SHELL_CONTROL_TOKENS or any(ch in token for ch in "<>|&;")


def _python_inline_argv(command: str) -> list[str] | None:
    """Return argv for a simple Python -c command that should bypass shell parsing."""
    try:
        parts = shlex.split(command, posix=True)
    except ValueError:
        return None
    if len(parts) < 3:
        return None
    launcher = pathlib.PurePath(parts[0]).name.lower()
    if launcher not in PYTHON_LAUNCHERS or "-c" not in parts:
        return None
    code_index = parts.index("-c")
    if code_index + 1 >= len(parts):
        return None
    surrounding_tokens = parts[1:code_index] + parts[code_index + 2:]
    if any(_has_shell_control(token) for token in surrounding_tokens):
        return None
    return parts


def run_shell_command_with_timeout(
    command: str,
    *,
    timeout: float,
    cwd: str | pathlib.Path,
) -> subprocess.CompletedProcess:
    """Run a grader shell command, avoiding shell expansion for simple Python -c."""
    python_argv = _python_inline_argv(command)
    if python_argv:
        try:
            return run_command_with_timeout(python_argv, timeout=timeout, cwd=cwd)
        except OSError as exc:
            if _is_access_denied_spawn_error(exc):
                raise InfraError(f"command spawn failed: {exc}") from exc
            raise

    bash_path = find_bash()
    if bash_path:
        try:
            return run_command_with_timeout(
                [bash_path, "-c", command],
                timeout=timeout, cwd=cwd,
            )
        except OSError as exc:
            if not _is_access_denied_spawn_error(exc):
                raise
            try:
                return run_command_with_timeout(
                    command,
                    shell=True,
                    timeout=timeout,
                    cwd=cwd,
                )
            except OSError as fallback_exc:
                if _is_access_denied_spawn_error(fallback_exc):
                    raise InfraError(
                        f"bash and platform shell spawn failed: {fallback_exc}"
                    ) from fallback_exc
                raise
    try:
        return run_command_with_timeout(
            command,
            shell=True,
            timeout=timeout,
            cwd=cwd,
        )
    except OSError as exc:
        if _is_access_denied_spawn_error(exc):
            raise InfraError(f"platform shell spawn failed: {exc}") from exc
        raise


# --- Ported verbatim from scripts/shared.py (repo-side origin) --------------
# Banned expressions (skills/spec/SKILL.md L197-205)
BANNED_KO = [
    "적절히", "적절하게",
    "필요한 경우", "필요 시",
    "등등", "기타",
    "올바르게", "정상적으로",
    "효율적으로", "최적화하여",
    "가능하면", "가급적",
    "상황에 맞게", "상황에 따라",
]
BANNED_EN_RE = [
    r"\bappropriately\b",
    r"\bif necessary\b", r"\bif needed\b",
    r"\betc\.\b", r"\band so on\b",
    r"\bproperly\b", r"\bcorrectly\b",
    r"\befficiently\b", r"\boptimized\b",
    r"\bif possible\b", r"\bpreferably\b",
    r"\bas appropriate\b", r"\bdepending on\b",
]


# --- Placeholder / no-op Verify detection ----------------------------------
# Ported from the wiring-gate rule (scripts/harness-common.ps1
# Test-EzpTrivialCommand and scripts/harness-doctor.ps1 Test-TrivialCommand)
# so per-task Verify commands are held to the same "placeholder = failure"
# standard. `rem` (cmd/batch no-op comment) is added because it is a no-op
# Verify the audit requires to FAIL and predates that PowerShell-only rule.
def _is_placeholder_verify(command: str) -> bool:
    text = command.strip()
    if not text:
        return True
    lower = text.lower()
    lower = re.sub(
        r"^(powershell|powershell\.exe|pwsh|pwsh\.exe)\s+"
        r"(-noprofile\s+)?(-executionpolicy\s+\w+\s+)?(-command\s+)?",
        "",
        lower,
    )
    lower = lower.strip().strip('"').strip("'").strip()
    if re.match(r"^(true|:|exit\s+0)$", lower):
        return True
    if re.match(r"^(echo|write-output)\b", lower):
        return True
    if re.match(r"^rem\b", lower):
        return True
    return False

# Verify-type -> which dimensions apply
DIMENSION_MAP = {
    "pure": {"structural", "content", "command"},
    "cli":  {"structural", "content", "command"},
    "lib":  {"structural", "content", "relational", "command"},
    "api":  {"structural", "content", "relational", "command"},
    "data": {"structural", "content", "relational", "command"},
    "e2e":  {"structural", "content", "relational", "command"},
}

DEFAULT_TIMEOUT = 30


# ---------------------------------------------------------------------------
# Step markdown parser
# ---------------------------------------------------------------------------
def _dedupe_preserve_order(items: list[str]) -> list[str]:
    seen = set()
    result = []
    for item in items:
        clean = item.strip()
        if clean and clean not in seen:
            seen.add(clean)
            result.append(clean)
    return result


def _markdown_sections(text: str) -> dict[str, str]:
    matches = list(re.finditer(r"(?m)^##\s+(.+?)\s*$", text))
    sections: dict[str, str] = {}
    for index, match in enumerate(matches):
        heading = match.group(1).strip().lower()
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        sections[heading] = text[start:end]
    return sections


def _verification_text(text: str) -> str:
    sections = _markdown_sections(text)
    selected = []
    for heading, body in sections.items():
        if heading in {"acceptance criteria", "verification"}:
            selected.append(body)
    if selected:
        return "\n".join(selected)
    return text


def parse_step_md(path: pathlib.Path) -> dict:
    """Parse a step markdown file into structured data."""
    text = path.read_text(encoding="utf-8")
    verification_text = _verification_text(text)
    result = {
        "verify_commands": [],
        "static_commands": [],
        "verify_type": "cli",
        "files": [],
        "acceptance_criteria": [],
        "r_ids": [],
        "raw_text": text,
    }

    # Extract Verify-type
    m = re.search(r"Verify-type:\s*(\w+)", verification_text)
    if m:
        result["verify_type"] = m.group(1).lower()

    # Extract Verify commands only from AC/Verification sections when present.
    result["verify_commands"] = _dedupe_preserve_order([
        m.group(1)
        for m in re.finditer(
            r"(?:\*\*)?Verify:\s*(?:\*\*)?\s*`([^`]+)`",
            verification_text,
            re.IGNORECASE,
        )
    ])

    # Extract optional static verification commands.
    result["static_commands"] = _dedupe_preserve_order([
        m.group(1)
        for m in re.finditer(
            r"(?:\*\*)?(?:Static-verify|Ast-grep):\s*(?:\*\*)?\s*`([^`]+)`",
            verification_text,
            re.IGNORECASE,
        )
    ])

    # Extract files from ## Files to Read or **Files:** sections
    files_section = re.search(
        r"(?:## Files to Read|##\s*Files|\*\*Files:\*\*)\s*\n((?:\s*[-*].*\n)*)",
        text,
    )
    if files_section:
        for line in files_section.group(1).splitlines():
            # Only accept lines with Modify:/Test:/Create:/Read: prefixes or backtick paths
            if re.search(r"(?:Modify|Test|Create|Read):", line):
                fm = re.search(r"`([^`]+)`", line)
                if fm:
                    result["files"].append(fm.group(1))
                else:
                    clean = re.sub(r"^[\s\-*]+(?:Modify:|Test:|Create:|Read:)\s*", "", line).strip()
                    if clean and "/" in clean:
                        result["files"].append(clean)
            elif re.match(r"\s*[-*]\s*`[^`]+`", line):
                fm = re.search(r"`([^`]+)`", line)
                if fm:
                    result["files"].append(fm.group(1))

    # Extract R-ids
    result["r_ids"] = list(set(re.findall(r"\[R(\d+)\]", text)))

    # Extract acceptance criteria (Given/When/Then lines)
    for m in re.finditer(r"(?:Given|When|Then):\s*(.+)", text):
        result["acceptance_criteria"].append(m.group(1).strip())

    return result


# ---------------------------------------------------------------------------
# Dimension checkers
# ---------------------------------------------------------------------------
def _is_within(path: pathlib.Path, root: pathlib.Path) -> bool:
    """Check that resolved path stays within project root."""
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def check_structural(
    step: dict,
    project_root: pathlib.Path,
    step_md_path: pathlib.Path,
    phase_dir: pathlib.Path | None,
) -> dict:
    """Check file existence and format validity."""
    checks = []
    all_pass = True

    if phase_dir is not None:
        anchor_path = phase_dir / "anchors" / f"{step_md_path.stem}.hashline.json"
        if anchor_path.exists():
            anchor_script = REPO_ROOT / "scripts" / "hashline-anchor.py"
            try:
                proc = subprocess.run(
                    [
                        sys.executable,
                        str(anchor_script),
                        "verify",
                        "--source",
                        str(step_md_path),
                        "--anchor",
                        str(anchor_path),
                        "--json",
                    ],
                    cwd=str(project_root),
                    text=True,
                    capture_output=True,
                    timeout=10,
                    check=False,
                )
                try:
                    anchor_result = json.loads(proc.stdout)
                except json.JSONDecodeError:
                    anchor_result = {
                        "pass": False,
                        "error": (proc.stderr or proc.stdout)[:200],
                    }
                passed = proc.returncode == 0 and bool(anchor_result.get("pass"))
                checks.append({
                    "name": "hashline_anchor",
                    "target": str(anchor_path),
                    "pass": passed,
                    "result": anchor_result,
                })
                if not passed:
                    all_pass = False
            except (OSError, subprocess.TimeoutExpired) as e:
                all_pass = False
                checks.append({
                    "name": "hashline_anchor",
                    "target": str(anchor_path),
                    "pass": False,
                    "error": str(e)[:200],
                })

    for file_ref in step["files"]:
        # Reject path traversal attempts
        resolved = file_ref.replace("/", os.sep)
        candidate = project_root / resolved
        if not _is_within(candidate, project_root):
            all_pass = False
            checks.append({
                "name": "path_traversal",
                "target": file_ref,
                "pass": False,
                "error": "path escapes project root",
            })
            continue
        full_pattern = str(candidate)
        matches = glob.glob(full_pattern)

        if matches:
            checks.append({
                "name": "file_exists",
                "target": file_ref,
                "pass": True,
                "matches": len(matches),
            })
            # Validate JSON/YAML files parse correctly
            for match_path in matches:
                ext = pathlib.Path(match_path).suffix.lower()
                if ext == ".json":
                    try:
                        with open(match_path, encoding="utf-8") as f:
                            json.load(f)
                        checks.append({
                            "name": "json_valid",
                            "target": match_path,
                            "pass": True,
                        })
                    except (json.JSONDecodeError, OSError) as e:
                        all_pass = False
                        checks.append({
                            "name": "json_valid",
                            "target": match_path,
                            "pass": False,
                            "error": str(e)[:200],
                        })
        else:
            all_pass = False
            checks.append({
                "name": "file_exists",
                "target": file_ref,
                "pass": False,
            })

    return {"pass": all_pass, "checks": checks}


def check_content(step: dict, project_root: pathlib.Path) -> dict:
    """Check content patterns, counts, and banned expressions."""
    checks = []
    all_pass = True
    text = step["raw_text"]

    # Scan generated output files for banned expressions
    for file_ref in step["files"]:
        resolved = file_ref.replace("/", os.sep)
        full_pattern = str(project_root / resolved)
        for match_path in glob.glob(full_pattern):
            try:
                content = pathlib.Path(match_path).read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError) as e:
                all_pass = False
                checks.append({
                    "name": "file_read",
                    "target": match_path,
                    "pass": False,
                    "error": str(e)[:200],
                })
                continue

            # Korean banned expressions
            found_banned = []
            for expr in BANNED_KO:
                if expr in content:
                    found_banned.append(expr)

            # English banned expressions
            for pattern in BANNED_EN_RE:
                if re.search(pattern, content, re.IGNORECASE):
                    found_banned.append(pattern)

            if found_banned:
                all_pass = False
                checks.append({
                    "name": "banned_expression",
                    "target": match_path,
                    "pass": False,
                    "found": found_banned[:10],
                })
            else:
                checks.append({
                    "name": "banned_expression",
                    "target": match_path,
                    "pass": True,
                })

    # Check R-id count from step criteria
    r_count = len(step["r_ids"])
    if r_count > 0:
        checks.append({
            "name": "r_id_present",
            "expected": ">=1",
            "actual": r_count,
            "pass": True,
        })

    # Check verify commands exist
    v_count = len(step["verify_commands"])
    checks.append({
        "name": "verify_commands_present",
        "expected": ">=1",
        "actual": v_count,
        "pass": v_count >= 1,
    })
    if v_count < 1:
        all_pass = False

    return {"pass": all_pass, "checks": checks}


def check_relational(
    step: dict,
    project_root: pathlib.Path,
    phase_dir: pathlib.Path | None,
) -> dict:
    """Check cross-file reference integrity."""
    checks = []
    all_pass = True

    r_ids = step["r_ids"]
    if not r_ids:
        return {"pass": True, "checks": []}

    # Check R-ids appear in spec files
    spec_dir = project_root / "docs" / "specs"
    if spec_dir.exists():
        spec_files = list(spec_dir.glob("*.md"))
        if spec_files:
            spec_text = ""
            for sf in spec_files:
                try:
                    spec_text += sf.read_text(encoding="utf-8")
                except OSError:
                    pass

            missing_in_spec = [
                rid for rid in r_ids if f"R{rid}" not in spec_text
            ]
            passed = len(missing_in_spec) == 0
            if not passed:
                all_pass = False
            checks.append({
                "name": "r_ids_in_spec",
                "missing": missing_in_spec,
                "pass": passed,
            })

    # Check R-ids appear in plan files
    plan_dir = project_root / "docs" / "plans"
    if plan_dir.exists():
        plan_files = list(plan_dir.glob("*.md"))
        if plan_files:
            plan_text = ""
            for pf in plan_files:
                try:
                    plan_text += pf.read_text(encoding="utf-8")
                except OSError:
                    pass

            missing_in_plan = [
                rid for rid in r_ids if f"R{rid}" not in plan_text
            ]
            passed = len(missing_in_plan) == 0
            if not passed:
                all_pass = False
            checks.append({
                "name": "r_ids_in_plan",
                "missing": missing_in_plan,
                "pass": passed,
            })

    # Check files referenced in step exist in project
    for file_ref in step["files"]:
        if "*" in file_ref or "?" in file_ref:
            continue
        resolved = project_root / file_ref.replace("/", os.sep)
        exists = resolved.exists()
        checks.append({
            "name": "file_ref_exists",
            "target": file_ref,
            "pass": exists,
        })
        if not exists:
            all_pass = False

    return {"pass": all_pass, "checks": checks}


def check_command(
    step: dict,
    project_root: pathlib.Path,
    timeout: float,
) -> dict:
    """Run shell Verify commands (backwards-compatible)."""
    checks = []
    all_pass = True
    commands = step["verify_commands"]

    if not commands:
        return {"pass": True, "checks": []}

    for cmd in commands:
        if _is_placeholder_verify(cmd):
            all_pass = False
            checks.append({
                "name": "placeholder_verify",
                "command": cmd,
                "pass": False,
                "error": "placeholder/no-op Verify command is not real verification",
            })
            continue
        try:
            proc = run_shell_command_with_timeout(
                cmd,
                timeout=timeout,
                cwd=str(project_root),
            )
            passed = proc.returncode == 0
            if not passed:
                all_pass = False
            checks.append({
                "name": "shell_exit",
                "command": cmd,
                "exit_code": proc.returncode,
                "pass": passed,
                "stderr": (proc.stderr or "")[:200],
            })
        except subprocess.TimeoutExpired:
            all_pass = False
            checks.append({
                "name": "shell_exit",
                "command": cmd,
                "pass": False,
                "error": f"timeout after {timeout}s",
            })
        except InfraError as e:
            all_pass = False
            checks.append({
                "name": "shell_exit",
                "command": cmd,
                "status": "infra_error",
                "pass": False,
                "error": str(e)[:200],
            })
        except Exception as e:
            all_pass = False
            checks.append({
                "name": "shell_exit",
                "command": cmd,
                "pass": False,
                "error": str(e)[:200],
            })

    return {"pass": all_pass, "checks": checks}


def _config_static_required(project_root: pathlib.Path) -> bool:
    config_path = project_root / ".harness" / "config.json"
    if not config_path.exists():
        return False
    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return False
    verification = data.get("verification", {})
    if not isinstance(verification, dict):
        return False
    return bool(verification.get("static_required", False))


def check_static(
    step: dict,
    project_root: pathlib.Path,
    timeout: float,
    required: bool,
) -> dict:
    """Run optional static verification commands."""
    checks = []
    all_pass = True
    commands = step["static_commands"]

    if not commands:
        if required:
            return {
                "pass": False,
                "checks": [{
                    "name": "static_commands_present",
                    "expected": ">=1",
                    "actual": 0,
                    "pass": False,
                }],
            }
        return {"pass": True, "checks": []}

    for cmd in commands:
        executable = cmd.strip().split()[0] if cmd.strip() else ""
        if executable and shutil.which(executable) is None and executable.lower() in {"ast-grep", "sg"}:
            passed = not required
            if not passed:
                all_pass = False
            checks.append({
                "name": "static_tool_available",
                "command": cmd,
                "tool": executable,
                "pass": passed,
                "warning": None if required else f"{executable} not found; optional static check skipped",
            })
            if not required:
                continue
        try:
            proc = run_shell_command_with_timeout(
                cmd,
                timeout=timeout,
                cwd=str(project_root),
            )
            passed = proc.returncode == 0
            if not passed:
                all_pass = False
            checks.append({
                "name": "static_exit",
                "command": cmd,
                "exit_code": proc.returncode,
                "pass": passed,
                "stderr": (proc.stderr or "")[:200],
            })
        except subprocess.TimeoutExpired:
            all_pass = False
            checks.append({
                "name": "static_exit",
                "command": cmd,
                "pass": False,
                "error": f"timeout after {timeout}s",
            })
        except InfraError as e:
            all_pass = False
            checks.append({
                "name": "static_exit",
                "command": cmd,
                "status": "infra_error",
                "pass": False,
                "error": str(e)[:200],
            })
        except Exception as e:
            all_pass = False
            checks.append({
                "name": "static_exit",
                "command": cmd,
                "pass": False,
                "error": str(e)[:200],
            })

    return {"pass": all_pass, "checks": checks}


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------
def run_verify(
    step_md_path: pathlib.Path,
    project_root: pathlib.Path,
    phase: str,
    timeout: float,
) -> dict:
    """Run multi-dimensional verification for a single step."""
    step = parse_step_md(step_md_path)
    verify_type = step["verify_type"]
    enabled = DIMENSION_MAP.get(verify_type, DIMENSION_MAP["cli"])

    step_name = step_md_path.stem
    phase_dir = project_root / "phases" / phase if phase else None

    dimensions = {}
    overall_pass = True

    if "structural" in enabled:
        result = check_structural(step, project_root, step_md_path, phase_dir)
        dimensions["structural"] = result
        if not result["pass"]:
            overall_pass = False

    if "content" in enabled:
        result = check_content(step, project_root)
        dimensions["content"] = result
        if not result["pass"]:
            overall_pass = False

    if "relational" in enabled:
        result = check_relational(step, project_root, phase_dir)
        dimensions["relational"] = result
        if not result["pass"]:
            overall_pass = False

    if "command" in enabled:
        result = check_command(step, project_root, timeout)
        dimensions["command"] = result
        if not result["pass"]:
            overall_pass = False

    static_required = _config_static_required(project_root)
    if step["static_commands"] or static_required:
        result = check_static(step, project_root, timeout, static_required)
        dimensions["static"] = result
        if not result["pass"]:
            overall_pass = False

    return {
        "step": step_name,
        "verify_type": verify_type,
        "verify_commands": step["verify_commands"],
        "verify_commands_count": len(step["verify_commands"]),
        "static_commands": step["static_commands"],
        "pass": overall_pass,
        "dimensions": dimensions,
    }


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------
def main() -> int:
    parser = argparse.ArgumentParser(
        description="Multi-dimensional step verification for EZPowers harness",
    )
    parser.add_argument(
        "--step-md", required=True, type=pathlib.Path,
        help="Path to the step markdown file",
    )
    parser.add_argument(
        "--project-root", required=True, type=pathlib.Path,
        help="Project root directory",
    )
    parser.add_argument(
        "--phase", default="",
        help="Phase name for relational checks",
    )
    parser.add_argument(
        "--timeout", type=float, default=DEFAULT_TIMEOUT,
        help=f"Timeout for shell commands in seconds (default: {DEFAULT_TIMEOUT})",
    )
    args = parser.parse_args()

    if not args.step_md.exists():
        result = {
            "step": args.step_md.stem,
            "verify_type": "unknown",
            "pass": False,
            "dimensions": {},
            "error": f"step file not found: {args.step_md}",
        }
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 1

    result = run_verify(args.step_md, args.project_root, args.phase, args.timeout)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
