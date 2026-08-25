# F23 implementation plan

## Goal and constraints

Add one shared validation/graph seam and one bounded check scheduler. Preserve
the host-native implementation boundary, standard-library-only installed
runtime, exact argv and freshness semantics, immutable evidence layout,
dual-host parity, and explicit refresh. The content-only Korean guide update
must retain the existing `DESIGN.md` mapping and tokens.

## Ordered slices

1. Normalise spec/plan/config contracts once, add compatible schema v2, and
   derive a stable graph and task waves.
2. Execute v2 check occurrences through the safe lock-aware scheduler while
   retaining the v1 serial path and complete evidence order.
3. Bind graph v1 into evidence/certificates and harness-chain approvals, add
   trace/blocker state, and enforce legacy reapproval.
4. Pin regression, tamper, chain, and performance evidence; then update the
   contracts, distribution, product state, and guide.

No task authorises model selection, agent assignment, an external service, a
mutable task-state machine, or generic retry behavior.

<!-- ezpowers:plan:start -->
```json
{
  "schema_version": 2,
  "spec": "docs/specs/f23-assurance-graph.md",
  "checks": {
    "assurance-graph-tests": {
      "argv": ["python", "-m", "unittest", "tests.test_assurance_graph"],
      "cwd": ".",
      "timeout_seconds": 300,
      "kind": "integration",
      "concurrency": {
        "safe": false,
        "resource_locks": []
      }
    },
    "harness-chain-tests": {
      "argv": ["python", "-m", "unittest", "tests.test_harness_chain"],
      "cwd": ".",
      "timeout_seconds": 600,
      "kind": "integration",
      "concurrency": {
        "safe": false,
        "resource_locks": []
      }
    },
    "parallel-benchmark-fixture": {
      "argv": ["python", "scripts/benchmark_parallel_verification.py", "--mode", "fixture", "--runs", "3", "--minimum-improvement", "30"],
      "cwd": ".",
      "timeout_seconds": 120,
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
      "criteria": ["AC-1", "AC-2"],
      "checks": ["assurance-graph-tests"]
    },
    {
      "id": "T2",
      "depends_on": ["T1"],
      "criteria": ["AC-3", "AC-6"],
      "checks": ["assurance-graph-tests", "parallel-benchmark-fixture"]
    },
    {
      "id": "T3",
      "depends_on": ["T1"],
      "criteria": ["AC-4", "AC-5"],
      "checks": ["assurance-graph-tests", "harness-chain-tests"]
    },
    {
      "id": "T4",
      "depends_on": ["T2", "T3"],
      "criteria": ["AC-7"],
      "checks": ["repo-check", "kit-manifest", "plugin-files"]
    }
  ]
}
```
<!-- ezpowers:plan:end -->
