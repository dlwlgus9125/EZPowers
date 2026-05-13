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
import shutil
import subprocess
import sys

# ---------------------------------------------------------------------------
# Reuse from sibling scripts
# ---------------------------------------------------------------------------
REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from run_baseline import run_command_with_timeout  # noqa: E402

BANNED_KO = [
    "\uc801\uc808\ud788", "\uc801\uc808\ud558\uac8c",
    "\ud544\uc694\ud55c \uacbd\uc6b0", "\ud544\uc694 \uc2dc",
    "\ub4f1\ub4f1", "\uae30\ud0c0",
    "\uc62c\ubc14\ub974\uac8c", "\uc815\uc0c1\uc801\uc73c\ub85c",
    "\ud6a8\uc728\uc801\uc73c\ub85c", "\ucd5c\uc801\ud654\ud558\uc5ec",
    "\uac00\ub2a5\ud558\uba74", "\uac00\uae09\uc801",
    "\uc0c1\ud669\uc5d0 \ub9de\uac8c", "\uc0c1\ud669\uc5d0 \ub530\ub77c",
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
def parse_step_md(path: pathlib.Path) -> dict:
    """Parse a step markdown file into structured data."""
    text = path.read_text(encoding="utf-8")
    result = {
        "verify_commands": [],
        "verify_type": "cli",
        "files": [],
        "acceptance_criteria": [],
        "r_ids": [],
        "raw_text": text,
    }

    # Extract Verify-type
    m = re.search(r"Verify-type:\s*(\w+)", text)
    if m:
        result["verify_type"] = m.group(1).lower()

    # Extract Verify commands (backtick-enclosed commands after Verify:)
    for m in re.finditer(r"Verify:\s*`([^`]+)`", text):
        result["verify_commands"].append(m.group(1))

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


def check_structural(step: dict, project_root: pathlib.Path) -> dict:
    """Check file existence and format validity."""
    checks = []
    all_pass = True

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

    bash_path = shutil.which("bash")
    for cmd in commands:
        try:
            if bash_path:
                proc = run_command_with_timeout(
                    [bash_path, "-c", cmd],
                    timeout=timeout,
                    cwd=str(project_root),
                )
            else:
                proc = run_command_with_timeout(
                    cmd,
                    shell=True,
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
        except Exception as e:
            all_pass = False
            checks.append({
                "name": "shell_exit",
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
        result = check_structural(step, project_root)
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

    return {
        "step": step_name,
        "verify_type": verify_type,
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
