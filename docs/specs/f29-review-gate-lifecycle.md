# F29: Review gate lifecycle

## Outcome

A harness-chain project never needs a hand edit of its state file because of
a review gate. The main agent learns at once that a receipt was rejected and
why, a finished run does not leave its gate in the next feature's way, a gate
whose reviewer cannot report can be ended explicitly, and none of this makes
it cheaper to replace a reviewer than to accept a review.

## Scope

Included:

- the rejection notice: a short reason on the pending challenge, repeated by
  `chain gate begin`, the Stop reason, and the run status;
- gate ownership and endings: a finished run's gate, a new subject of the same
  kind, the explicit `chain gate abandon` command, and the rule that a stored
  report is judged before a challenge ends;
- one feature at a time for oracle audits, and no counting of an audit
  rejection against a run;
- the contract, skill, and reference statements of that behavior;
- the 5.12.0 plugin and project-kit release surfaces.

Excluded: the receipt schema and marker, the configured limits, the
one-replacement bound of an oracle audit, reviewer binding at SubagentStart,
automatic detection of a lost reviewer, more than one pending challenge, the
runtime lock wait of hooks, the ordinary completion hook, host minimum
versions, and live verification of Codex.

Architecture impact: `docs/reference/architecture.md` (review challenge
paragraph) and ADR 0013, `docs/decisions/0013-review-gate-lifecycle.md`.

## Decisions carried from design

- D29-1: a product gate belongs to the run that was `RUNNING` when it began;
  an oracle audit belongs to its preview hash.
- D29-2 (user decision, 2026-11-19): a rejected oracle-audit receipt never
  counts against a run, and an oracle audit cannot begin while a run is
  `PENDING_LOOP` or `RUNNING`.
- D29-3 (user decision, 2026-11-19): the pending-gate dead ends are fixed by a
  lifecycle, not by a narrow patch: a finished run's gate is dropped, a new
  subject of the same kind replaces a pending challenge, and
  `chain gate abandon` ends a challenge whose bound reviewer cannot report.
- D29-4: ending a challenge without a receipt is fail-closed once a reviewer
  is involved. An audit that ever had a reviewer closes its preview; a product
  gate with a bound reviewer counts one review failure, once for each
  reviewer.
- D29-5: a stored hand-back that carries a gate marker is judged before its
  challenge is abandoned or replaced.
- D29-6: the rejection reason is one runtime-authored ASCII line of at most
  300 characters. The value recorded for the failure signature is unchanged.
- D29-7: no automatic lost-reviewer detection and no second pending
  challenge.

## Requirements

- R1: The main agent is told that a receipt was rejected, why, and what to do.
- R2: Oracle audits and runs do not interfere with each other.
- R3: A finished run does not leave a gate behind.
- R4: A new subject of the same kind replaces a pending challenge without
  opening reviewer cycling.
- R5: A bound reviewer that cannot report can be abandoned, fail-closed.
- R6: A report that has already arrived is judged, not dropped.
- R7: The guidance for a bound challenge tells the main agent to wait first.
- R8: The contract, skill, and references state the same rules.
- R9: The 5.12.0 surfaces agree and exactly one kit manifest remains.

Failure behavior: pending challenges written by an earlier kit keep working.
A product gate without a recorded run follows the current run, and a state in
which an audit is pending beside a running run is handled without counting
against that run.

## Risks and accepted limitations

- Losing an audit reviewer costs a new preview hash even when the acceptance
  contract is sound.
- An abandoned reviewer's later report is ignored.
- A receipt that arrives while a long command holds the runtime lock is still
  dropped; the gate then stays bound until it is abandoned.
- Whether a model follows the new guidance is shown by recorded live sessions,
  not by a plan check.
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
      "claim": "After a rejected hand-back inside a running chain, the Stop reason, the run status next action, and the chain gate begin answer state that the receipt was rejected, give a one-line ASCII reason, and tell the main agent to spawn one new independent reviewer; once a reviewer is bound none of them asks for another; before approval the gate answer also says it is the only replacement; and a hand-back without a gate marker is described as such.",
      "verify_type": "e2e",
      "integration": true
    },
    {
      "id": "AC-2",
      "requirement_id": "R2",
      "claim": "An oracle audit cannot begin while a harness-chain run is PENDING_LOOP or RUNNING and can begin once the run is terminal, including directly after an emergency stop with no Stop event in between, and a rejected oracle-audit receipt that arrives while a run is RUNNING leaves that run's counters and status unchanged and follows the one-replacement rule.",
      "verify_type": "e2e",
      "integration": true
    },
    {
      "id": "AC-3",
      "requirement_id": "R3",
      "claim": "A product gate left pending by a run that ended at the iteration limit or through an emergency stop does not block the next feature's oracle audit, and a subagent that starts afterwards is not bound to it.",
      "verify_type": "e2e",
      "integration": true
    },
    {
      "id": "AC-4",
      "requirement_id": "R4",
      "claim": "chain gate begin with a new subject of the same kind replaces the pending challenge; a replaced oracle audit that ever had a reviewer bound closes its preview so that returning to that preview is refused, while one that never had a reviewer leaves the preview open; and a replaced product gate with a reviewer bound counts one review failure in its run while one without a bound reviewer counts none.",
      "verify_type": "e2e",
      "integration": true
    },
    {
      "id": "AC-5",
      "requirement_id": "R5",
      "claim": "chain gate abandon refuses when no challenge is pending or the pending challenge has no bound reviewer; before approval it closes the preview so that another audit of the same preview is refused; and inside a run it counts one review failure, releases the same challenge for a new reviewer, does not count a reviewer whose rejection was already counted, and ends the run at the review limit.",
      "verify_type": "e2e",
      "integration": true
    },
    {
      "id": "AC-6",
      "requirement_id": "R6",
      "claim": "When a hand-back with a gate marker is stored on the bound challenge, chain gate abandon and a replacing chain gate begin judge that report first: a FAIL is recorded with its consequences and a PASS creates the receipt.",
      "verify_type": "e2e",
      "integration": true
    },
    {
      "id": "AC-7",
      "requirement_id": "R7",
      "claim": "While the challenge a run is waiting for is bound and no receipt has arrived, the next action tells the main agent to wait for a running reviewer and to run chain gate abandon only when that reviewer has ended, the chain gate begin answer says the same, and the refusal for a closed preview names how it was closed.",
      "verify_type": "e2e",
      "integration": true
    },
    {
      "id": "AC-8",
      "requirement_id": "R8",
      "claim": "The harness-chain contract and skill, the architecture artifact, and ADR 0013 state the owner of a challenge, its endings, the fail-closed rule, the abandon command, the one-feature-at-a-time rule, and the rejection notice.",
      "verify_type": "cli",
      "integration": true
    },
    {
      "id": "AC-9",
      "requirement_id": "R9",
      "claim": "The Claude plugin, marketplace, and Codex manifests and the single project-kit manifest report 5.12.0, the kit manifest hashes match their sources, a fresh project installs from it, and no older kit manifest remains.",
      "verify_type": "cli",
      "integration": true
    }
  ]
}
```
<!-- ezpowers:spec:end -->
