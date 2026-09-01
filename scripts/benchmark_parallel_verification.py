#!/usr/bin/env python3
"""Measure EZPowers' serial and opt-in parallel check scheduler."""

from __future__ import annotations

import argparse
import importlib.util
import json
import pathlib
import shutil
import statistics
import sys
import time
import uuid
from typing import Any


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
RUNTIME_PATH = REPO_ROOT / "scripts" / "ezpowers.py"
ACTUAL_SAFE_CHECKS = ("repo-check", "kit-manifest", "plugin-files")


def load_runtime() -> dict[str, Any]:
    spec = importlib.util.spec_from_file_location(
        "ezpowers_benchmark_runtime", RUNTIME_PATH
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load EZPowers runtime")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return vars(module)


def fixture_checks() -> list[dict[str, Any]]:
    return [
        {
            "id": f"fixture-{index}",
            "argv": [
                sys.executable,
                "-c",
                "import time; time.sleep(.25)",
            ],
            "cwd": ".",
            "timeout_seconds": 10,
            "kind": "test",
            "concurrency": {
                "safe": True,
                "resource_locks": [f"fixture-{index}"],
            },
        }
        for index in range(1, 5)
    ]


def project_checks(runtime: dict[str, Any]) -> list[dict[str, Any]]:
    config_path = REPO_ROOT / ".ezpowers" / "config.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    errors: list[str] = []
    checks, required, version, _, _ = runtime["_validate_config_value"](
        REPO_ROOT,
        config,
        errors,
    )
    if errors:
        raise RuntimeError("invalid project config: " + "; ".join(errors))
    if version != 2:
        raise RuntimeError("project benchmark requires config schema_version 2")
    if any(check_id not in required for check_id in ACTUAL_SAFE_CHECKS):
        raise RuntimeError("actual benchmark checks must remain required checks")
    selected = [checks[check_id] for check_id in ACTUAL_SAFE_CHECKS]
    if any(check["concurrency"]["safe"] is not True for check in selected):
        raise RuntimeError("actual benchmark checks must be explicitly safe")
    return selected


def outcome_signature(result: dict[str, Any], *, include_logs: bool) -> dict[str, Any]:
    signature = {
        key: result[key]
        for key in (
            "id",
            "argv",
            "cwd",
            "timeout_seconds",
            "kind",
            "status",
            "exit_code",
            "timed_out",
            "spawn_error",
        )
    }
    if include_logs:
        signature["stdout_sha256"] = result["stdout_sha256"]
        signature["stderr_sha256"] = result["stderr_sha256"]
    return signature


def execute_once(
    runtime: dict[str, Any],
    checks: list[dict[str, Any]],
    *,
    parallel: bool,
    iteration: int,
) -> tuple[float, list[dict[str, Any]]]:
    run_dir = (
        REPO_ROOT
        / ".ezpowers"
        / "evidence"
        / f"benchmark-{iteration}-{uuid.uuid4().hex[:8]}"
    )
    run_dir.mkdir(parents=True, exist_ok=False)
    invocations = [
        {
            "node_id": f"check:benchmark:{index}:{check['id']}",
            "task_id": "benchmark",
            "check": check,
        }
        for index, check in enumerate(checks, 1)
    ]
    started = time.perf_counter()
    try:
        results, _ = runtime["_execute_invocations"](
            REPO_ROOT,
            run_dir,
            invocations,
            max_workers=len(checks) if parallel else 1,
            parallel_enabled=parallel,
            phase="benchmark",
            task_wave=None,
            include_graph_fields=True,
        )
        elapsed = time.perf_counter() - started
        return elapsed, results
    finally:
        resolved = run_dir.resolve()
        evidence_root = (REPO_ROOT / ".ezpowers" / "evidence").resolve()
        resolved.relative_to(evidence_root)
        shutil.rmtree(resolved, ignore_errors=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("fixture", "project"), default="fixture")
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--minimum-improvement", type=float, default=30.0)
    args = parser.parse_args()
    if args.runs < 3:
        parser.error("--runs must be at least 3")
    if not 0 <= args.minimum_improvement < 100:
        parser.error("--minimum-improvement must be from 0 through 99.99")

    runtime = load_runtime()
    checks = fixture_checks() if args.mode == "fixture" else project_checks(runtime)
    timings: dict[str, list[float]] = {"serial": [], "parallel": []}
    equivalence = True
    all_passed = True
    for iteration in range(args.runs):
        order = (False, True) if iteration % 2 == 0 else (True, False)
        pair: dict[bool, list[dict[str, Any]]] = {}
        for parallel in order:
            elapsed, results = execute_once(
                runtime,
                checks,
                parallel=parallel,
                iteration=iteration,
            )
            timings["parallel" if parallel else "serial"].append(elapsed)
            pair[parallel] = results
            all_passed = all_passed and all(
                result["status"] == "PASS" for result in results
            )
        include_logs = args.mode == "fixture"
        equivalence = equivalence and [
            outcome_signature(item, include_logs=include_logs)
            for item in pair[False]
        ] == [
            outcome_signature(item, include_logs=include_logs)
            for item in pair[True]
        ]

    serial_median = statistics.median(timings["serial"])
    parallel_median = statistics.median(timings["parallel"])
    improvement = (
        ((serial_median - parallel_median) / serial_median) * 100
        if serial_median
        else 0.0
    )
    passed = (
        all_passed
        and equivalence
        and improvement >= args.minimum_improvement
    )
    payload = {
        "status": "PASS" if passed else "FAIL",
        "mode": args.mode,
        "runs": args.runs,
        "check_ids": [check["id"] for check in checks],
        "serial_seconds": [round(value, 6) for value in timings["serial"]],
        "parallel_seconds": [round(value, 6) for value in timings["parallel"]],
        "serial_median_seconds": round(serial_median, 6),
        "parallel_median_seconds": round(parallel_median, 6),
        "median_improvement_percent": round(improvement, 2),
        "minimum_improvement_percent": args.minimum_improvement,
        "outcomes_equivalent": equivalence,
        "all_checks_passed": all_passed,
        "comparison": (
            "full output hashes" if args.mode == "fixture" else "process outcomes"
        ),
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
