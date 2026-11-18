# F26 implementation plan

## Goal and constraints

Add content-bound reuse of a declared check's recorded PASS above the
unchanged check scheduler. Preserve the host-native implementation boundary,
the standard-library-only installed runtime with its Python 3.10 floor, exact
argv and freshness semantics, the immutable evidence layout, dual-host parity,
and explicit refresh. Projects that declare no reuse must keep their exact
behavior. Architecture input: `docs/reference/architecture.md` and
`docs/decisions/0010-content-bound-check-reuse.md` (decisions D26-1 to D26-8 in
the spec). The Korean guide receives content-only updates under the existing
`DESIGN.md` mapping.

## Ordered slices

1. Pin today's undeclared behavior with characterization tests before the
   runtime changes, then add declaration validation and the conditional
   contract-hash member.
2. Add the pattern matcher, the Git-visible file universe, the content hash,
   and the reuse key; integrate carrying, in-run sharing, the stable-run rule,
   candidate bookkeeping, and `--no-reuse` into `verify` without changing
   `_execute_invocations`.
3. Teach the freshness evaluators, certificate, and status the reuse record;
   bind chain carries to the approved run, add the preview scope check, and
   bind the planning artifact inventory.
4. Add the reuse benchmark and extend the real install smoke.
5. Update contracts, skills, product documents, the guide, the 5.10.0
   manifests, and release state; stamp the kit manifest last.

Expected files are `scripts/ezpowers.py`, `tests/test_check_reuse.py`,
`tests/test_harness_chain.py`, `tests/test_planning_profile.py`,
`scripts/benchmark_check_reuse.py`, `scripts/runtime_smoke.py`, the four
verification-related contracts, four skills, and the release surfaces.

No task authorises a change-size tier, a new verification scope, a time limit
on a carried PASS, a change to chain gate or limit rules, model selection,
agent assignment, an external service, or a mutable task-state machine.

## Risks

An incomplete declaration can carry a false PASS; the tests therefore observe
real process starts through a counter outside the project instead of trusting
the new evidence fields. The local interpreter is newer than the 3.10 floor,
so only APIs available in 3.10 may be used.

<!-- ezpowers:plan:start -->
```json
{
  "schema_version": 2,
  "spec": "docs/specs/f26-check-reuse.md",
  "checks": {
    "check-reuse-tests": {
      "argv": ["python", "-m", "unittest", "tests.test_check_reuse"],
      "cwd": ".",
      "timeout_seconds": 900,
      "kind": "integration",
      "concurrency": {
        "safe": false,
        "resource_locks": []
      }
    },
    "chain-reuse-tests": {
      "argv": ["python", "-m", "unittest", "tests.test_harness_chain"],
      "cwd": ".",
      "timeout_seconds": 900,
      "kind": "e2e",
      "concurrency": {
        "safe": false,
        "resource_locks": []
      }
    },
    "planning-reuse-tests": {
      "argv": ["python", "-m", "unittest", "tests.test_planning_profile"],
      "cwd": ".",
      "timeout_seconds": 600,
      "kind": "e2e",
      "concurrency": {
        "safe": false,
        "resource_locks": []
      }
    },
    "check-reuse-benchmark": {
      "argv": ["python", "scripts/benchmark_check_reuse.py", "--runs", "3", "--minimum-improvement", "50"],
      "cwd": ".",
      "timeout_seconds": 300,
      "kind": "smoke",
      "concurrency": {
        "safe": false,
        "resource_locks": []
      }
    },
    "release-surface-tests": {
      "argv": ["python", "-m", "unittest", "tests.test_v5_workflow_surface", "tests.test_codex_plugin_discovery", "tests.test_harness_kit_distribution", "tests.test_repo_check"],
      "cwd": ".",
      "timeout_seconds": 300,
      "kind": "smoke",
      "concurrency": {
        "safe": false,
        "resource_locks": []
      }
    }
  },
  "tasks": [
    {
      "id": "T1",
      "depends_on": [],
      "criteria": ["AC-1", "AC-2", "AC-3", "AC-4", "AC-5"],
      "checks": ["check-reuse-tests"]
    },
    {
      "id": "T2",
      "depends_on": ["T1"],
      "criteria": ["AC-6"],
      "checks": ["chain-reuse-tests"]
    },
    {
      "id": "T3",
      "depends_on": ["T1"],
      "criteria": ["AC-7"],
      "checks": ["planning-reuse-tests"]
    },
    {
      "id": "T4",
      "depends_on": ["T1"],
      "criteria": ["AC-8"],
      "checks": ["check-reuse-benchmark"]
    },
    {
      "id": "T5",
      "depends_on": ["T2", "T3", "T4"],
      "criteria": ["AC-9"],
      "checks": ["release-surface-tests"]
    }
  ]
}
```
<!-- ezpowers:plan:end -->
