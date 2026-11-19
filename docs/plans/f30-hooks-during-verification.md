# F30 implementation plan

## Goal and constraints

Let the chain hooks work while a verification runs its checks, judge a
reviewer's report once no check is running, and release both as 5.12.1.
Preserve what a verification executes and records, the evidence and
certificate schemas, the receipt schema and marker, the configured limits, the
one second hook wait, the installed hook timeout and matchers, the
standard-library-only runtime with its Python 3.10 floor, and the host minimum
versions. Architecture input: `docs/reference/architecture.md` and
`docs/decisions/0014-hooks-during-verification.md` (decisions D30-1 to D30-7
in the spec).

## Ordered slices

1. Add tests that fail on the current runtime: a reviewer's report, a
   reviewer's start, a frozen write, and a Stop while a real verify runs a
   check that waits for a file outside the project; a stored report whose
   verification never finished; a rejected stored report; reports for
   superseded evidence; and the state lock file outside the fingerprint. Pin
   what must not change: the Stop answer and the busy result of a second
   command.
2. Change the runtime: the state lock beside the command lock, `verify`
   releasing the state lock while checks run, the probe for a running command
   in the hook, recording the reviewer's stop, judging a stored report at the
   end of `verify` and at the other named points, the release of a reviewer
   whose stored report is rejected, the gate rule for superseded evidence, and
   the fingerprint and overlay exclusions.
3. Update the verification, setup, and harness-chain contracts and the skill,
   with a phrase test.
4. Move the live manifest to 5.12.1, update the release surfaces, and stamp
   the manifest last.

Expected files are `scripts/ezpowers.py`, `tests/test_harness_chain.py`,
`tests/test_v5_workflow_surface.py`, the three contracts and the skill,
product documents, and the release surfaces.

No task authorises a change to the completion verdict, evidence, freshness,
the receipt schema, a configured limit, the hook wait, the installed hook
entries, the ordinary completion hook, a reviewer persona, model selection, an
external service, or a mutable task-state machine.

## Risks

The tests drive hooks with payload shapes recorded from the live host and hold
the locks with the operating system primitive of the platform they run on, so
the POSIX path is not exercised on this machine. Whether the host delivers a
reviewer's hooks during the main agent's command is shown by a recorded live
session, not by a plan check. The local interpreter is newer than the 3.10
floor, so only APIs available in 3.10 may be used.

<!-- ezpowers:plan:start -->
```json
{
  "schema_version": 2,
  "spec": "docs/specs/f30-hooks-during-verification.md",
  "checks": {
    "chain-hook-tests": {
      "argv": ["python", "-m", "unittest", "tests.test_harness_chain"],
      "cwd": ".",
      "timeout_seconds": 1800,
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
    "runtime-lock-tests": {
      "argv": ["python", "-m", "unittest", "tests.test_ezpowers_runtime"],
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
      "criteria": ["AC-1", "AC-2", "AC-3", "AC-4", "AC-5", "AC-6", "AC-7", "AC-8"],
      "checks": ["chain-hook-tests", "planning-chain-tests", "runtime-lock-tests"]
    },
    {
      "id": "T2",
      "depends_on": ["T1"],
      "criteria": ["AC-9"],
      "checks": ["guidance-surface-tests"]
    },
    {
      "id": "T3",
      "depends_on": ["T1", "T2"],
      "criteria": ["AC-10"],
      "checks": ["release-surface-tests"]
    }
  ]
}
```
<!-- ezpowers:plan:end -->
