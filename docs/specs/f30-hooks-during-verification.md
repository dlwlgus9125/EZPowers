# F30: Hooks during verification

## Outcome

A reviewer may report while the main agent verifies. Its report is not lost:
it becomes a receipt once the verification has ended, without a review failure
and without `chain gate abandon`. While checks run, a reviewer that starts is
still bound, frozen acceptance files are still guarded, and no verdict is
taken until the checks have finished.

## Scope

Included:

- two runtime locks: the command lock held by a state-writing command for its
  whole run, and a state lock that `verify` releases while its checks run and
  that hooks take alone;
- recording the bound reviewer's stop during a verification and judging the
  stored report when no check is running;
- the Stop answer while a command is running;
- a `PASS` receipt whose subject is no longer the run's latest all-scope
  verification;
- treating `.ezpowers/state.lock` and the temporary file of a state write as
  runtime state;
- the contract, skill, and reference statements of that behavior;
- the 5.12.1 plugin and project-kit release surfaces.

Excluded: what a verification executes and records, the evidence and
certificate schemas, the receipt schema and marker, the configured limits, the
hook wait of one second, the installed hook timeout and matchers, a retry of a
state write, the ordinary completion hook, host minimum versions, and live
verification of Codex.

Architecture impact: `docs/reference/architecture.md` (runtime locks and the
review report paragraph) and ADR 0014,
`docs/decisions/0014-hooks-during-verification.md`.

## Decisions carried from design

- D30-1 (user decision, 2026-11-19): split the lock instead of waiting longer,
  writing reports to a side file, or changing guidance only.
- D30-2: `.ezpowers/runtime.lock` stays the command lock; `.ezpowers/state.lock`
  is the state lock. Hooks keep their one second wait and their fail-safe.
- D30-3: no verdict while checks run. A verdict is taken only while holding
  the command lock. A SubagentStop of the bound reviewer that finds a command
  still holding it after one second is recorded on the challenge and judged
  later.
- D30-4: at the end of a verification the stored report is judged after the
  verification recorded its own result. It is otherwise judged by the next
  Stop, `chain gate begin`, `chain gate abandon`, `chain run apply`,
  `chain run status`, `certify`, or `verify`.
- D30-5: a rejected stored report releases its reviewer on every host, with
  the existing counting and the one-replacement bound of an audit.
- D30-6: a Stop keeps taking the command lock with its one second wait. When
  a command still holds it, the Stop is not blocked and not counted, the
  answer the single lock gave before.
- D30-7: a `PASS` receipt for superseded evidence is stored but does not
  become the run's current gate.

## Requirements

- R1: A report that arrives during a verification becomes a receipt.
- R2: No verdict is taken while checks run.
- R3: Reviewer binding and the frozen-file guard work during a verification.
- R4: A Stop during a command is a wait, and commands still exclude each other.
- R5: A stored report is judged even when its verification never finished.
- R6: A rejected stored report releases its reviewer and is counted as before.
- R7: A receipt for superseded evidence does not satisfy the run's gate.
- R8: The state lock file never changes a workspace fingerprint.
- R9: The contracts, skill, and references state the same rules.
- R10: The 5.12.1 surfaces agree and exactly one kit manifest remains.

Failure behavior: a hook that cannot take the state lock within one second
still degrades to a no-op. A project refreshed from an earlier kit needs no
chain configuration change; its first state-writing command creates the second
lock file.

## Risks and accepted limitations

- A rejected report that arrived during a verification cannot be corrected by
  the same reviewer.
- A hook that arrives while another command holds the state lock for more than
  a second is still a no-op.
- Every project gets a second runtime lock file that Git shows as untracked
  until the project ignores it.
- The POSIX lock path uses the same primitive on a second file and was not run
  on a POSIX host.
- No part of the rules was run on a live Codex host.
- This repository's own `unit` check has a timeout shorter than its run time,
  so completion evidence here is the release gates run directly, not an
  in-repository all-scope certificate.

<!-- ezpowers:spec:start -->
```json
{
  "schema_version": 1,
  "design_context": {
    "required": false,
    "reason": "The guide receives a version-only update; no UI structure, tokens, or reusable styling changes."
  },
  "criteria": [
    {
      "id": "AC-1",
      "requirement_id": "R1",
      "claim": "When the bound reviewer's hand-back with a valid PASS marker and its SubagentStop arrive while a real task-scope verify is running its check, a code-review receipt for the latest all-scope evidence exists once that verify has ended, no challenge is pending, no review failure is counted, and the next action is certification.",
      "verify_type": "e2e",
      "integration": true
    },
    {
      "id": "AC-2",
      "requirement_id": "R2",
      "claim": "After the bound reviewer's SubagentStop arrived and while the check is still running, no receipt exists, the challenge is still bound to that reviewer with its report stored, and no counter of the run has changed.",
      "verify_type": "e2e",
      "integration": true
    },
    {
      "id": "AC-3",
      "requirement_id": "R3",
      "claim": "While a real verify is running its check, a reviewer that starts is bound to the pending challenge and receives the rubric, and a write to a frozen acceptance file is denied.",
      "verify_type": "e2e",
      "integration": true
    },
    {
      "id": "AC-4",
      "requirement_id": "R4",
      "claim": "While a real verify is running its check, a Stop is answered without a block and the iteration counter does not change, and a second state-writing command fails with a busy result.",
      "verify_type": "e2e",
      "integration": true
    },
    {
      "id": "AC-5",
      "requirement_id": "R5",
      "claim": "A report stored while the command lock was held by a process that ended without judging it is judged by the next Stop event and by chain run status: the receipt is created and nothing is counted.",
      "verify_type": "e2e",
      "integration": true
    },
    {
      "id": "AC-6",
      "requirement_id": "R6",
      "claim": "A stored report without a usable gate marker is rejected when it is judged: inside a run it counts one review failure, releases the reviewer although the report came as a SubagentStop message, and the Stop reason names the rejection and asks for one new reviewer; before approval a stored audit report follows the one-replacement rule.",
      "verify_type": "e2e",
      "integration": true
    },
    {
      "id": "AC-7",
      "requirement_id": "R7",
      "claim": "When an all-scope verify runs while a review of the earlier evidence is pending, a PASS report that arrived during it is stored as a receipt but the run's gate is not satisfied and the next action asks for a fresh code-review gate, while a FAIL report requires product rework so that another all-scope verify without a workspace change is refused.",
      "verify_type": "e2e",
      "integration": true
    },
    {
      "id": "AC-8",
      "requirement_id": "R8",
      "claim": "After a hook has created the state lock file, evidence recorded before it is still fresh and certifies, and the state lock file is not copied into the chain baseline workspace.",
      "verify_type": "e2e",
      "integration": true
    },
    {
      "id": "AC-9",
      "requirement_id": "R9",
      "claim": "The verification, setup, and harness-chain contracts, the harness-chain skill, the architecture artifact, and ADR 0014 state the two locks, that hooks work during a verification, that a stored report is judged when no check is running, the Stop answer while a command runs, and the rule for a receipt for superseded evidence.",
      "verify_type": "cli",
      "integration": true
    },
    {
      "id": "AC-10",
      "requirement_id": "R10",
      "claim": "The Claude plugin, marketplace, and Codex manifests and the single project-kit manifest report 5.12.1, the kit manifest hashes match their sources, a fresh project installs from it, and no older kit manifest remains.",
      "verify_type": "cli",
      "integration": true
    }
  ]
}
```
<!-- ezpowers:spec:end -->
