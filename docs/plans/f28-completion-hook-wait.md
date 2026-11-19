# F28 implementation plan

## Goal and constraints

Give the ordinary completion Stop adapter the wait rule, the adapter-failure
rule, and the encoding rule decided in ADR 0012, and release them as 5.11.1.
Preserve the completion verdict, status, evidence, freshness, certification,
the installed hook entry, the installer options, the chain hooks, the
standard-library-only runtime with its Python 3.10 floor, and the host minimum
versions. Architecture input: `docs/reference/architecture.md` and
`docs/decisions/0012-completion-hook-wait-and-failure.md` (decisions D28-1 to
D28-4 in the spec).

## Ordered slices

1. Add tests that fail on the current runtime for the wait rule, the
   adapter-failure rule, and the encoding rule, using the Stop payload shape
   recorded from the live host.
2. Change `_hook_command`: read the event as UTF-8 bytes, defer for a running
   background subagent on Claude Code, turn an unrecognised failure into a
   warning, and answer with ASCII-only JSON.
3. Update the verification and setup contracts and the host discovery
   reference, with a phrase test.
4. Move the live manifest to 5.11.1, update the release surfaces, and stamp
   the manifest last.

Expected files are `scripts/ezpowers.py`, `tests/test_ezpowers_runtime.py`,
`tests/test_v5_workflow_surface.py`, the verification and setup contracts, the
discovery reference, product documents, and the release surfaces.

No task authorises a change to the completion verdict, evidence, freshness,
certification, the chain hooks, an installer option, a reviewer persona, model
selection, an external service, or a mutable task-state machine.

## Risks

The wait rule is proven against the Stop payload recorded from non-interactive
runs. A real-host confirmation on the changed runtime is a recorded manual
step, not a plan check, because it needs a model call. The local interpreter
is newer than the 3.10 floor, so only APIs available in 3.10 may be used.

<!-- ezpowers:plan:start -->
```json
{
  "schema_version": 2,
  "spec": "docs/specs/f28-completion-hook-wait.md",
  "checks": {
    "completion-hook-tests": {
      "argv": ["python", "-m", "unittest", "tests.test_ezpowers_runtime"],
      "cwd": ".",
      "timeout_seconds": 900,
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
      "argv": ["python", "-m", "unittest", "tests.test_codex_plugin_discovery", "tests.test_harness_kit_distribution", "tests.test_repo_check"],
      "cwd": ".",
      "timeout_seconds": 600,
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
      "criteria": ["AC-1", "AC-2", "AC-3"],
      "checks": ["completion-hook-tests"]
    },
    {
      "id": "T2",
      "depends_on": ["T1"],
      "criteria": ["AC-4"],
      "checks": ["guidance-surface-tests"]
    },
    {
      "id": "T3",
      "depends_on": ["T1", "T2"],
      "criteria": ["AC-5"],
      "checks": ["release-surface-tests"]
    }
  ]
}
```
<!-- ezpowers:plan:end -->
