# ADR 0013: Review gate lifecycle

- Status: accepted
- Date: 2026-11-19
- Decision owners: EZPowers maintainers
- Related: `docs/reference/architecture.md`,
  `docs/decisions/0003-explicit-asymmetric-harness-chain.md`,
  `docs/decisions/0011-current-host-chain-adapter.md`

## Context

The chain keeps one pending review challenge in project state. `chain gate
begin` creates it, the next subagent of the handshaken session is bound to it,
and that reviewer's receipt resolves it. Nothing else ended a challenge, and
the challenge did not know which run or preview it belonged to.

Reproduced on the v5.11.1 runtime on 2026-11-19:

- A run that ends at the iteration limit, or through the documented emergency
  stop, while a review gate is pending leaves that gate behind. The next
  feature's oracle audit then fails with "another independent review challenge
  is already pending", and only a hand edit of the state file clears it.
- A gate bound to a reviewer that never reports stays bound. Before approval
  it also refuses an audit of a changed preview. Inside a run each Stop
  answers "Begin a fresh independent code-review gate." until the iteration
  limit ends the run.
- A rejected oracle-audit receipt that arrives while another feature's run is
  `RUNNING` is counted against that run. With a review limit of one it ended
  the running feature.
- After a rejected receipt nothing tells the main agent what happened. In
  `auto` the host does not deliver the hook's rejection to anybody, and in a
  live run the main agent inferred it from a counter in the state file.

ADR 0011 bounded the replacement of a reviewer whose report was rejected, so
that a malformed `FAIL` cannot simply be answered by another reviewer's
`PASS`. Any way of ending a challenge has to keep that property.

## Decision

A pending challenge has an owner and a defined end.

1. **Owner.** A product gate (`code-review`, `artifact-review`,
   `adversarial-qa`, `blocker-review`) belongs to the run that was `RUNNING`
   when it began. An oracle audit belongs to its preview hash.
2. **One feature at a time.** An oracle audit cannot begin while a run is
   `PENDING_LOOP` or `RUNNING`. The run status is refreshed first, so an
   emergency stop is honoured at once. A rejected audit receipt never counts
   against a run.
3. **Endings.** A challenge ends when its bound reviewer's receipt is
   accepted, when its owner ends, when `chain gate begin` names a new subject
   of the same kind, when `chain gate abandon` is run, or through the existing
   bounds: the second rejected hand-back of an audit and the review limit of a
   run.
4. **No silent ending.** Ending a challenge without a receipt is fail-closed
   once a reviewer is involved. An oracle audit that ever had a reviewer bound
   closes its preview: another audit needs a new preview hash. A product gate
   with a reviewer bound counts one review failure in its running run, at most
   once for each reviewer. A challenge that never had a reviewer, and a
   product gate whose run has already ended, leave nothing.
5. **A stored report is judged, not dropped.** When a hand-back with a gate
   marker is already stored on the challenge, abandoning or replacing the
   challenge judges that report first. A `FAIL` that has arrived cannot be
   abandoned away.
6. **Explicit abandonment.** `chain gate abandon` is for a bound reviewer that
   cannot report. Before approval it closes the preview. Inside a run it
   counts one review failure and releases the same challenge for one new
   reviewer, or ends the run at the review limit.
7. **The main agent is told.** A rejection is recorded on the challenge as
   one short ASCII line written by the runtime. `chain gate begin` repeats it
   with the next step. Inside a run the next action repeats it when the
   challenge is the one the run is waiting for, and says to wait for a bound
   reviewer before it mentions abandoning.

The receipt schema and marker, the limits, the one-replacement bound of an
audit, and the reviewer binding rules do not change.

## Considered options

- **A command that only clears the pending challenge.** Rejected. A challenge
  could be dropped before its reviewer reports and a new reviewer started on
  the same subject, which reopens the reviewer cycling ADR 0011 closed.
- **Only let a new preview hash replace a pending audit.** Declined by the
  user as a stopgap. It leaves the gate of a finished run and a lost reviewer
  inside a run unsolved.
- **Detect a lost reviewer from the host's background task list.** Rejected.
  A wrong inference counts a review failure the reviewer did not cause, and
  with a review limit of one that ends a run. The main agent knows whether the
  reviewer it started is still running; the runtime tells it what to do.
- **Keep several pending challenges so an audit and a run can overlap.**
  Rejected. A new subagent would have to be matched to one of them, and no
  workflow needs the overlap: a second feature cannot be applied while a run
  is active anyway.
- **Accept a late report from an abandoned reviewer.** Rejected for now. The
  abandonment is already counted or the preview already closed, and the
  hand-back capture would have to follow an unbound agent.

## Consequences

- A project never needs a hand edit of the state file to start the next
  feature after a run ended with a gate pending.
- An oracle audit for the next feature has to wait for the current run's
  terminal verdict. The earlier runtime allowed it and then refused the
  feature at `chain run apply`.
- Losing an audit reviewer costs a new preview hash even when the acceptance
  contract is sound. That is the price of not auditing unchanged evidence
  twice.
- Abandoning or replacing a bound review inside a run spends one of the
  approved review retries. Repeating it ends the run through the review limit
  or the identical-error limit.
- A report from an abandoned reviewer is ignored.
- A receipt that arrives while a long command holds the runtime lock is still
  dropped by the hook's fail-safe. The gate then stays bound until it is
  abandoned. That is not solved here.
- The rules apply to both hosts. No part of them was run on a live Codex host.
- Pending challenges written by an earlier kit keep working: a product gate
  without a recorded run follows the current run.
