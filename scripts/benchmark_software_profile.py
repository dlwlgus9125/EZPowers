#!/usr/bin/env python3
"""Measure legacy software validation/trace compatibility against a Git ref."""

from __future__ import annotations

import argparse
import gc
import json
import pathlib
import statistics
import subprocess
import sys
import tempfile
import textwrap
import time
import types
from typing import Any


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
CANDIDATE_RUNTIME = REPO_ROOT / "scripts" / "ezpowers.py"


def managed_block(kind: str, value: dict[str, Any]) -> str:
    return textwrap.dedent(
        f"""
        # Software compatibility {kind}

        <!-- ezpowers:{kind}:start -->
        ```json
        {json.dumps(value, indent=2)}
        ```
        <!-- ezpowers:{kind}:end -->
        """
    ).strip() + "\n"


def load_source(name: str, source: str, filename: str) -> types.ModuleType:
    module = types.ModuleType(name)
    module.__file__ = filename
    module.__package__ = ""
    sys.modules[name] = module
    exec(compile(source, filename, "exec"), module.__dict__)
    module._status_payload = lambda *_args, **_kwargs: (
        {
            "status": "INACTIVE",
            "fresh": False,
            "certified": False,
            "reasons": ["plan is not the active resume target"],
        },
        0,
    )
    return module


def baseline_source(ref: str) -> str:
    result = subprocess.run(
        ["git", "show", f"{ref}:scripts/ezpowers.py"],
        cwd=REPO_ROOT,
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "no output"
        raise RuntimeError(f"cannot read baseline runtime {ref}: {detail}")
    return result.stdout


def write_fixture(root: pathlib.Path, task_count: int = 24) -> pathlib.Path:
    (root / ".ezpowers").mkdir(parents=True)
    (root / "docs" / "specs").mkdir(parents=True)
    (root / "docs" / "plans").mkdir(parents=True)
    config = {
        "schema_version": 2,
        "project_name": "software-compatibility",
        "verification": {"max_parallel_checks": 4},
        "checks": {},
        "required_checks": [],
    }
    (root / ".ezpowers" / "config.json").write_text(
        json.dumps(config, indent=2) + "\n",
        encoding="utf-8",
    )
    criteria = [
        {
            "id": f"AC-{index}",
            "requirement_id": f"R-{index}",
            "claim": f"Software compatibility behavior {index} remains observable.",
            "verify_type": "integration",
            "integration": True,
        }
        for index in range(1, task_count + 1)
    ]
    checks = {
        f"check-{index}": {
            "argv": [
                sys.executable,
                "-c",
                f"from pathlib import Path; assert Path('.').is_dir(); print({index})",
            ],
            "cwd": ".",
            "timeout_seconds": 30,
            "kind": "integration",
            "concurrency": {
                "safe": index % 3 != 0,
                "resource_locks": [f"fixture-{index % 5}"],
            },
        }
        for index in range(1, task_count + 1)
    }
    tasks = [
        {
            "id": f"T{index}",
            "depends_on": [] if index <= 3 else [f"T{index - 3}"],
            "criteria": [f"AC-{index}"],
            "checks": [f"check-{index}"],
        }
        for index in range(1, task_count + 1)
    ]
    spec = {
        "schema_version": 1,
        "design_context": {
            "required": False,
            "reason": "The compatibility fixture has no UI surface.",
        },
        "criteria": criteria,
    }
    plan = {
        "schema_version": 2,
        "spec": "docs/specs/software-compatibility.md",
        "checks": checks,
        "tasks": tasks,
    }
    (root / "docs" / "specs" / "software-compatibility.md").write_text(
        managed_block("spec", spec),
        encoding="utf-8",
    )
    plan_path = root / "docs" / "plans" / "software-compatibility.md"
    plan_path.write_text(managed_block("plan", plan), encoding="utf-8")
    return plan_path


def signature(module: types.ModuleType, root: pathlib.Path, plan: pathlib.Path) -> str:
    flow = module._validate_flow(root, plan)
    trace, code = module._trace_payload(root, plan)
    value = {
        "validation": {
            "errors": flow.errors,
            "plan": flow.plan_rel,
            "task_waves": flow.task_waves,
            "assurance_graph": flow.assurance_graph,
            "assurance_graph_sha256": flow.assurance_graph_sha256,
        },
        "trace_code": code,
        "trace": trace,
    }
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def timed_batch(
    module: types.ModuleType,
    root: pathlib.Path,
    plan: pathlib.Path,
    iterations: int,
) -> tuple[float, str]:
    gc.collect()
    started = time.perf_counter()
    last = ""
    for _ in range(iterations):
        last = signature(module, root, plan)
    return time.perf_counter() - started, last


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-ref", required=True)
    parser.add_argument("--runs", type=int, default=5)
    parser.add_argument("--maximum-regression", type=float, default=5.0)
    parser.add_argument("--iterations", type=int, default=100)
    args = parser.parse_args()
    if args.runs < 5:
        parser.error("--runs must be at least 5")
    if args.iterations < 1:
        parser.error("--iterations must be positive")
    if not 0 <= args.maximum_regression < 100:
        parser.error("--maximum-regression must be from 0 through 99.99")

    try:
        baseline = load_source(
            "ezpowers_software_baseline",
            baseline_source(args.baseline_ref),
            f"{args.baseline_ref}:scripts/ezpowers.py",
        )
        candidate = load_source(
            "ezpowers_software_candidate",
            CANDIDATE_RUNTIME.read_text(encoding="utf-8"),
            str(CANDIDATE_RUNTIME),
        )
        with tempfile.TemporaryDirectory(prefix="ezpowers-software-profile-") as temp_dir:
            root = pathlib.Path(temp_dir)
            plan = write_fixture(root)
            baseline_signature = signature(baseline, root, plan)
            candidate_signature = signature(candidate, root, plan)
            outputs_equivalent = baseline_signature == candidate_signature

            timings: dict[str, list[float]] = {"baseline": [], "candidate": []}
            for run_index in range(args.runs):
                order = (
                    (("baseline", baseline), ("candidate", candidate))
                    if run_index % 2 == 0
                    else (("candidate", candidate), ("baseline", baseline))
                )
                run_signatures: dict[str, str] = {}
                for label, module in order:
                    elapsed, observed = timed_batch(
                        module,
                        root,
                        plan,
                        args.iterations,
                    )
                    timings[label].append(elapsed)
                    run_signatures[label] = observed
                outputs_equivalent = outputs_equivalent and (
                    run_signatures["baseline"] == run_signatures["candidate"]
                )
    except (OSError, RuntimeError, ValueError) as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}, indent=2))
        return 2

    baseline_median = statistics.median(timings["baseline"])
    candidate_median = statistics.median(timings["candidate"])
    regression = (
        ((candidate_median - baseline_median) / baseline_median) * 100
        if baseline_median
        else float("inf")
    )
    passed = outputs_equivalent and regression <= args.maximum_regression
    payload = {
        "status": "PASS" if passed else "FAIL",
        "baseline_ref": args.baseline_ref,
        "runs": args.runs,
        "iterations_per_run": args.iterations,
        "outputs_equivalent": outputs_equivalent,
        "baseline_seconds": [round(value, 6) for value in timings["baseline"]],
        "candidate_seconds": [round(value, 6) for value in timings["candidate"]],
        "baseline_median_seconds": round(baseline_median, 6),
        "candidate_median_seconds": round(candidate_median, 6),
        "median_regression_percent": round(regression, 2),
        "maximum_regression_percent": args.maximum_regression,
        "comparison": "software plan-v2 normalized validation and inactive trace JSON",
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
