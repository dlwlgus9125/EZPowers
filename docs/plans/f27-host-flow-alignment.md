# F27 implementation plan

## Goal and constraints

Align the chain's Claude host adapter with the hook payloads Claude Code
2.1.327 really sends, and add the verification guidance the spec names.
Preserve the host-native implementation boundary, the standard-library-only
runtime with its Python 3.10 floor, exact argv and freshness semantics, the
receipt schema and marker format, the hard limits, and the host minimum
versions. Codex keeps its matchers, accepted modes, and continuation behavior.
Architecture input: `docs/reference/architecture.md` and
`docs/decisions/0011-current-host-chain-adapter.md` (decisions D27-1 to D27-8
in the spec). The Korean guide receives content-only updates under the
existing `DESIGN.md` mapping.

## Ordered slices

1. Run the chain test module once as a baseline, then add tests that fail on
   the current runtime for each adapter criterion, using payload shapes
   recorded from the live probe.
2. Change the runtime: guard classification, hook matchers and installed-hook
   comparison, permission-mode source and accepted modes, hand-back capture,
   bounded reviewer replacement, Stop deferral, and the code-review rubric.
3. Update the three skills and the contracts that state this behavior, with a
   phrase test for the new guidance.
4. Prune `PROGRESS.md`, remove the kit manifests nothing reads, move the live
   manifest to 5.11.0, update the release surfaces, and stamp the manifest
   last.

Expected files are `scripts/ezpowers.py`, `tests/test_harness_chain.py`,
`tests/test_v5_workflow_surface.py`, three skills, the harness-chain,
verification, setup, and spec contracts, the discovery reference, product
documents, the guide, and the release surfaces.

No task authorises a change to the completion verdict, evidence, freshness,
receipt schema, configured limits, or host minimum versions, a reviewer
persona, model selection, agent assignment, an external service, a mutable
task-state machine, or a change to the ordinary completion hook.

## Risks

The adapter is proven against recorded payloads from two non-interactive probe
runs; an interactive session, a forked session, and compaction were not
probed. A real-host confirmation on the changed runtime is a recorded manual
step, not a plan check, because it needs a model call. The local interpreter
is newer than the 3.10 floor, so only APIs available in 3.10 may be used.

<!-- ezpowers:plan:start -->
```json
{
  "schema_version": 2,
  "spec": "docs/specs/f27-host-flow-alignment.md",
  "checks": {
    "chain-adapter-tests": {
      "argv": ["python", "-m", "unittest", "tests.test_harness_chain"],
      "cwd": ".",
      "timeout_seconds": 900,
      "kind": "e2e",
      "concurrency": {
        "safe": false,
        "resource_locks": []
      }
    },
    "planning-chain-tests": {
      "argv": ["python", "-m", "unittest", "tests.test_planning_profile"],
      "cwd": ".",
      "timeout_seconds": 600,
      "kind": "e2e",
      "concurrency": {
        "safe": false,
        "resource_locks": []
      }
    },
    "guidance-surface-tests": {
      "argv": ["python", "-m", "unittest", "tests.test_v5_workflow_surface", "tests.test_frontend_design_readiness"],
      "cwd": ".",
      "timeout_seconds": 300,
      "kind": "smoke",
      "concurrency": {
        "safe": false,
        "resource_locks": []
      }
    },
    "release-surface-tests": {
      "argv": ["python", "-m", "unittest", "tests.test_codex_plugin_discovery", "tests.test_harness_kit_distribution", "tests.test_repo_check", "tests.test_ezpowers_runtime"],
      "cwd": ".",
      "timeout_seconds": 900,
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
      "criteria": ["AC-1", "AC-2", "AC-3", "AC-4", "AC-5", "AC-6", "AC-7", "AC-10"],
      "checks": ["chain-adapter-tests", "planning-chain-tests"]
    },
    {
      "id": "T2",
      "depends_on": ["T1"],
      "criteria": ["AC-8"],
      "checks": ["guidance-surface-tests"]
    },
    {
      "id": "T3",
      "depends_on": ["T1", "T2"],
      "criteria": ["AC-9"],
      "checks": ["release-surface-tests"]
    }
  ]
}
```
<!-- ezpowers:plan:end -->
