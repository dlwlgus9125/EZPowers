# F29 implementation plan

## Goal and constraints

Give a pending review challenge an owner and a defined end, tell the main
agent about a rejected receipt, and release both as 5.12.0. Preserve the
receipt schema and marker, the configured limits, the one-replacement bound of
an oracle audit, reviewer binding at SubagentStart, the value recorded for a
failure signature, the standard-library-only runtime with its Python 3.10
floor, and the host minimum versions. Architecture input:
`docs/reference/architecture.md` and
`docs/decisions/0013-review-gate-lifecycle.md` (decisions D29-1 to D29-7 in
the spec).

## Ordered slices

1. Add tests that fail on the current runtime for the rejection notice, then
   record the reason on the pending challenge and let the next action and the
   gate answer repeat it.
2. Add tests that fail on the current runtime for the lifecycle: a finished
   run's gate, an audit during a run, a new subject, the abandon command, a
   stored report, and the guidance for a bound challenge. Keep the states an
   earlier kit could leave by constructing them directly.
3. Change the runtime: run ownership on product gates, the dead-gate drop, the
   refresh and refusal for audits during a run, the replacement of a pending
   challenge, `chain gate abandon`, and the guidance.
4. Update the harness-chain contract and skill, with a phrase test.
5. Move the live manifest to 5.12.0, update the release surfaces, and stamp
   the manifest last.

Expected files are `scripts/ezpowers.py`, `tests/test_harness_chain.py`,
`tests/test_v5_workflow_surface.py`, the harness-chain contract and skill,
product documents, and the release surfaces.

No task authorises a change to the completion verdict, evidence, freshness,
the receipt schema, a configured limit, the ordinary completion hook, a
reviewer persona, model selection, an external service, or a mutable
task-state machine.

## Risks

The lifecycle is proven with hook payload shapes recorded from the live host.
Whether a model follows the new guidance needs a model call, so the live
sessions are a recorded manual step, not a plan check. The local interpreter
is newer than the 3.10 floor, so only APIs available in 3.10 may be used.

<!-- ezpowers:plan:start -->
```json
{
  "schema_version": 2,
  "spec": "docs/specs/f29-review-gate-lifecycle.md",
  "checks": {
    "chain-lifecycle-tests": {
      "argv": ["python", "-m", "unittest", "tests.test_harness_chain"],
      "cwd": ".",
      "timeout_seconds": 1200,
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
      "criteria": ["AC-1", "AC-2", "AC-3", "AC-4", "AC-5", "AC-6", "AC-7"],
      "checks": ["chain-lifecycle-tests", "planning-chain-tests"]
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
