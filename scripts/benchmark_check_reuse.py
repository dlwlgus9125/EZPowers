#!/usr/bin/env python3
"""Measure EZPowers content-bound check reuse through the real installed CLI.

A disposable Git project receives the kit through the real installer. After a
change that affects only some checks, re-verification with reuse is compared
with a forced full run (`verify --all --no-reuse`).
"""

from __future__ import annotations

import argparse
import json
import pathlib
import statistics
import subprocess
import sys
import tempfile
import textwrap
import time
from typing import Any


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
INSTALLER = REPO_ROOT / "scripts" / "ezpowers.py"

# name -> (seconds, directories the check reads, declares reuse)
# The slowest check is two thirds of the check time, inside the 55-86 percent
# share measured on a real project. Durations are long enough that the fixed
# per-run cost of the CLI does not decide the result.
CHECKS: dict[str, tuple[float, tuple[str, ...], bool]] = {
    "e2e": (4.2, ("app", "e2e"), True),
    "integration": (0.9, ("app", "server"), True),
    "unit": (0.6, ("lib", "tests"), True),
    "lint": (0.3, (), False),
    "feature": (0.3, ("lib",), True),
}
REQUIRED = ("e2e", "integration", "unit", "lint")
AFFECTED = ("feature", "unit")
UNAFFECTED = ("e2e", "integration")

PROBE = textwrap.dedent(
    """
    import hashlib
    import pathlib
    import sys
    import time

    name, seconds, roots = sys.argv[1], float(sys.argv[2]), sys.argv[3:]
    digest = hashlib.sha256()
    failed = False
    for root in roots:
        for path in sorted(pathlib.Path(root).rglob("*")):
            if path.is_file():
                data = path.read_bytes()
                digest.update(path.as_posix().encode("utf-8"))
                digest.update(data)
                failed = failed or b"FAIL-MARKER" in data
    time.sleep(seconds)
    print(name, digest.hexdigest())
    raise SystemExit(1 if failed else 0)
    """
).lstrip()

COUNTER = (
    "import pathlib, sys; "
    "handle = pathlib.Path(sys.argv[1]).open('a', encoding='utf-8'); "
    "handle.write('run\\n'); handle.close()"
)


def run(
    command: list[str],
    cwd: pathlib.Path,
    *,
    expect: tuple[int, ...] = (0,),
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        command,
        cwd=cwd,
        text=True,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        timeout=180,
        check=False,
    )
    if result.returncode not in expect:
        raise RuntimeError(
            f"exit {result.returncode}, expected {expect}: {command!r}\n"
            f"{result.stdout}\n{result.stderr}"
        )
    return result


def block(kind: str, value: dict[str, Any]) -> str:
    return (
        f"# Reuse benchmark {kind}\n\n"
        f"<!-- ezpowers:{kind}:start -->\n"
        "```json\n"
        f"{json.dumps(value, indent=2)}\n"
        "```\n"
        f"<!-- ezpowers:{kind}:end -->\n"
    )


def check_contract(name: str) -> dict[str, Any]:
    seconds, roots, declared = CHECKS[name]
    contract: dict[str, Any] = {
        "argv": [sys.executable, "checks/probe.py", name, str(seconds), *roots],
        "cwd": ".",
        "timeout_seconds": 60,
        "kind": "integration",
        "concurrency": {"safe": False, "resource_locks": []},
    }
    if declared:
        contract["reuse"] = {
            "paths": [*(f"{root}/**" for root in roots), "checks/**"],
        }
    return contract


def write_flow(root: pathlib.Path, slug: str, tasks: list[dict], checks: dict) -> pathlib.Path:
    criteria = [
        {
            "id": criterion,
            "requirement_id": f"R-{criterion}",
            "claim": f"The benchmark outcome {criterion} is observable.",
            "verify_type": "integration",
            "integration": True,
        }
        for task in tasks
        for criterion in task["criteria"]
    ]
    spec = {
        "schema_version": 1,
        "design_context": {
            "required": False,
            "reason": "The benchmark fixture has no UI surface.",
        },
        "criteria": criteria,
    }
    plan = {
        "schema_version": 2,
        "spec": f"docs/specs/{slug}.md",
        "checks": checks,
        "tasks": tasks,
    }
    (root / "docs" / "specs").mkdir(parents=True, exist_ok=True)
    (root / "docs" / "plans").mkdir(parents=True, exist_ok=True)
    (root / "docs" / "specs" / f"{slug}.md").write_text(block("spec", spec), encoding="utf-8")
    plan_path = root / "docs" / "plans" / f"{slug}.md"
    plan_path.write_text(block("plan", plan), encoding="utf-8")
    return plan_path


def build_fixture(root: pathlib.Path) -> tuple[pathlib.Path, pathlib.Path]:
    run(["git", "init", "-q"], root)
    run(["git", "config", "user.email", "benchmark@example.com"], root)
    run(["git", "config", "user.name", "EZPowers Benchmark"], root)
    run(["git", "config", "core.autocrlf", "false"], root)
    run([sys.executable, str(INSTALLER), "install", "--project-root", str(root)], REPO_ROOT)
    runtime = root / ".ezpowers" / "ezpowers.py"
    for directory in ("app", "e2e", "server", "lib", "tests", "checks"):
        (root / directory).mkdir()
        (root / directory / "seed.txt").write_text(f"{directory} seed\n", encoding="utf-8")
    (root / "checks" / "probe.py").write_text(PROBE, encoding="utf-8")
    (root / ".gitignore").write_text("__pycache__/\n*.py[cod]\n", encoding="utf-8")
    config_path = root / ".ezpowers" / "config.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    config["schema_version"] = 2
    config["verification"] = {"max_parallel_checks": 1}
    config["checks"] = {name: check_contract(name) for name in REQUIRED}
    config["required_checks"] = list(REQUIRED)
    config_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    plan = write_flow(
        root,
        "reuse-benchmark",
        [{"id": "T1", "depends_on": [], "criteria": ["AC-1"], "checks": ["feature"]}],
        {"feature": check_contract("feature")},
    )
    run(["git", "add", "-A"], root)
    run(["git", "commit", "-qm", "benchmark fixture"], root)
    return runtime, plan


def entries(payload: dict[str, Any]) -> list[dict[str, Any]]:
    values = [check for task in payload["tasks"] for check in task["checks"]]
    values.extend(payload["project_checks"])
    return values


def verify(
    runtime: pathlib.Path,
    root: pathlib.Path,
    plan: pathlib.Path,
    *,
    forced: bool,
    expect: tuple[int, ...] = (0,),
) -> tuple[float, dict[str, Any]]:
    command = [sys.executable, str(runtime), "verify", "--plan", str(plan), "--all"]
    if forced:
        command.append("--no-reuse")
    command.append("--json")
    started = time.perf_counter()
    result = run(command, root, expect=expect)
    elapsed = time.perf_counter() - started
    return elapsed, json.loads(result.stdout)


def certified(runtime: pathlib.Path, root: pathlib.Path, plan: pathlib.Path) -> bool:
    run([sys.executable, str(runtime), "certify", "--plan", str(plan), "--json"], root)
    status = run([sys.executable, str(runtime), "status", "--json"], root)
    return json.loads(status.stdout).get("status") == "CERTIFIED"


def mode_sets(payload: dict[str, Any]) -> tuple[set[str], set[str]]:
    """Return (ids whose process started, ids that were carried)."""
    started: set[str] = set()
    carried: set[str] = set()
    for entry in entries(payload):
        mode = (entry.get("reuse") or {}).get("mode")
        if mode == "carried":
            carried.add(entry["id"])
        elif mode in (None, "executed"):
            started.add(entry["id"])
    return started, carried


def outcome(entry: dict[str, Any], *, include_output: bool) -> dict[str, Any]:
    value = {
        key: entry[key]
        for key in ("id", "argv", "cwd", "timeout_seconds", "kind", "status", "exit_code", "timed_out", "spawn_error")
    }
    if include_output:
        value["stdout_sha256"] = entry["stdout_sha256"]
    return value


def equivalent(reuse: dict[str, Any], full: dict[str, Any]) -> bool:
    """Compare per-check outcomes; unaffected checks must also match in output."""
    if reuse["status"] != full["status"]:
        return False
    stable = set(UNAFFECTED) | {"lint"}
    return [
        outcome(entry, include_output=entry["id"] in stable) for entry in entries(reuse)
    ] == [
        outcome(entry, include_output=entry["id"] in stable) for entry in entries(full)
    ]


def duplicate_report(runtime: pathlib.Path, root: pathlib.Path, outside: pathlib.Path) -> dict[str, int]:
    """Count process starts for one declared check referenced three times."""
    counter = outside / "repeated.count"
    repeated = {
        "argv": [sys.executable, "-c", COUNTER, str(counter)],
        "cwd": ".",
        "timeout_seconds": 30,
        "kind": "integration",
        "concurrency": {"safe": False, "resource_locks": []},
        "reuse": {"paths": ["lib/**"]},
    }
    plan = write_flow(
        root,
        "reuse-duplicates",
        [
            {"id": "T1", "depends_on": [], "criteria": ["AC-1"], "checks": ["repeated"]},
            {"id": "T2", "depends_on": ["T1"], "criteria": ["AC-2"], "checks": ["repeated"]},
            {"id": "T3", "depends_on": ["T2"], "criteria": ["AC-3"], "checks": ["repeated"]},
        ],
        {"repeated": repeated},
    )

    def starts() -> int:
        return len(counter.read_text(encoding="utf-8").splitlines()) if counter.exists() else 0

    verify(runtime, root, plan, forced=False)
    with_reuse = starts()
    verify(runtime, root, plan, forced=True)
    return {
        "references": 3,
        "process_starts_with_reuse": with_reuse,
        "process_starts_forced": starts() - with_reuse,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--minimum-improvement", type=float, default=50.0)
    args = parser.parse_args()
    if args.runs < 3:
        parser.error("--runs must be at least 3")
    if not 0 <= args.minimum_improvement < 100:
        parser.error("--minimum-improvement must be from 0 through 99.99")

    timings: dict[str, list[float]] = {"reuse": [], "full": []}
    selection_exact = True
    outcomes_equivalent = True
    all_passed = True
    try:
        with tempfile.TemporaryDirectory(prefix="ezpowers-reuse-benchmark-") as name:
            base = pathlib.Path(name)
            root = base / "project"
            outside = base / "outside"
            root.mkdir()
            outside.mkdir()
            runtime, plan = build_fixture(root)
            verify(runtime, root, plan, forced=False)

            edits = 0

            def change_lib(text: str | None = None) -> None:
                nonlocal edits
                edits += 1
                (root / "lib" / "value.txt").write_text(
                    text if text is not None else f"lib revision {edits}\n",
                    encoding="utf-8",
                )

            def timed_pair(order: tuple[bool, bool]) -> dict[bool, dict[str, Any]]:
                pair: dict[bool, dict[str, Any]] = {}
                for forced in order:
                    change_lib()
                    elapsed, payload = verify(runtime, root, plan, forced=forced)
                    timings["full" if forced else "reuse"].append(elapsed)
                    pair[forced] = payload
                return pair

            for iteration in range(args.runs):
                pair = timed_pair((False, True) if iteration % 2 == 0 else (True, False))
                reuse_started, reuse_carried = mode_sets(pair[False])
                full_started, full_carried = mode_sets(pair[True])
                selection_exact = selection_exact and (
                    reuse_started == set(AFFECTED) | {"lint"}
                    and reuse_carried == set(UNAFFECTED)
                    and full_started == set(CHECKS)
                    and not full_carried
                )
                all_passed = all_passed and all(
                    payload["status"] == "PASS" for payload in pair.values()
                )
                outcomes_equivalent = outcomes_equivalent and equivalent(
                    pair[False],
                    pair[True],
                )

            change_lib()
            verify(runtime, root, plan, forced=False)
            reuse_certified = certified(runtime, root, plan)
            change_lib()
            verify(runtime, root, plan, forced=True)
            full_certified = certified(runtime, root, plan)

            change_lib("FAIL-MARKER\n")
            _, failed_reuse = verify(runtime, root, plan, forced=False, expect=(1,))
            change_lib("FAIL-MARKER again\n")
            _, failed_full = verify(runtime, root, plan, forced=True, expect=(1,))
            failures_equivalent = equivalent(failed_reuse, failed_full) and [
                entry["id"] for entry in entries(failed_reuse) if entry["status"] != "PASS"
            ] == list(AFFECTED)

            change_lib()
            duplicates = duplicate_report(runtime, root, outside)
    except (OSError, RuntimeError, ValueError, KeyError) as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}, indent=2))
        return 2

    reuse_median = statistics.median(timings["reuse"])
    full_median = statistics.median(timings["full"])
    improvement = ((full_median - reuse_median) / full_median) * 100 if full_median else 0.0
    check_seconds = sum(seconds for seconds, _, _ in CHECKS.values())
    passed = (
        all_passed
        and selection_exact
        and outcomes_equivalent
        and failures_equivalent
        and reuse_certified
        and full_certified
        and duplicates["process_starts_with_reuse"] == 1
        and duplicates["process_starts_forced"] == 3
        and improvement >= args.minimum_improvement
    )
    payload = {
        "status": "PASS" if passed else "FAIL",
        "runs": args.runs,
        "check_ids": list(CHECKS),
        "changed_path": "lib/value.txt",
        "re_executed_with_reuse": [*AFFECTED, "lint"],
        "carried_with_reuse": list(UNAFFECTED),
        "slowest_check_share_percent": round(
            max(seconds for seconds, _, _ in CHECKS.values()) / check_seconds * 100,
            1,
        ),
        "reuse_seconds": [round(value, 6) for value in timings["reuse"]],
        "full_seconds": [round(value, 6) for value in timings["full"]],
        "reuse_median_seconds": round(reuse_median, 6),
        "full_median_seconds": round(full_median, 6),
        "median_improvement_percent": round(improvement, 2),
        "minimum_improvement_percent": args.minimum_improvement,
        "selection_exact": selection_exact,
        "outcomes_equivalent": outcomes_equivalent,
        "failures_equivalent": failures_equivalent,
        "all_checks_passed": all_passed,
        "certified_with_reuse": reuse_certified,
        "certified_forced_full": full_certified,
        "duplicate_occurrences": duplicates,
        "comparison": "installed CLI verify --all versus verify --all --no-reuse",
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
