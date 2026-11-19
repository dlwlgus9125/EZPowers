# ADR 0014: Hooks during verification

- Status: accepted
- Date: 2026-11-19
- Decision owners: EZPowers maintainers
- Related: `docs/reference/architecture.md`,
  `docs/decisions/0011-current-host-chain-adapter.md`,
  `docs/decisions/0013-review-gate-lifecycle.md`

## Context

One project-local lock serialized every state writer. `verify` held it for its
whole run, including every project check, and a chain hook waits one second
for it before it degrades to a no-op.

Reproduced on the v5.12.0 runtime on 2026-11-19, with a real `verify` whose
check took twelve seconds and synthetic hook events:

- The bound reviewer's hand-back with a valid `PASS` marker and its
  SubagentStop were each answered `{}` after one second. After the
  verification no receipt existed and the gate was still bound.
  `chain gate abandon` freed it at the cost of one review failure.
- A reviewer started meanwhile was not bound and received no rubric.
- A write to a frozen acceptance file was not denied.
- A Stop was not blocked and not counted.

A live Claude Code 2.1.327 session showed the same. While the main agent's
foreground `verify` ran, the host delivered the background reviewer's hooks,
each ended as a no-op, and the run certified only after one counted review
failure and a second reviewer. That session was told to run `verify` during
the review; an agent doing so by itself has not been observed.

`verify` already reads state again after its checks and applies its result to
that copy, so its design does not need state to stand still while checks run.
The installed chain hook entry has a 30 second timeout, so waiting for the
lock cannot cover a verification of ordinary length.

## Decision

1. **Two locks.** `.ezpowers/runtime.lock` remains the command lock: every
   state-writing command holds it for its whole run, so commands still exclude
   each other and a second command still fails with a busy result. A new
   `.ezpowers/state.lock` guards each read-modify-write of
   `.ezpowers/state.json`. A command holds it throughout, except that `verify`
   releases it after its preflight and takes it again before it reads state
   back. Hooks take the state lock with their one second wait and their
   fail-safe; only a Stop and a review verdict also take the command lock.
2. **Hooks work during verification.** While checks run, a hook still records
   the handshake and the permission mode, binds a reviewer and returns its
   rubric, keeps a hand-back, and applies the frozen-file guard.
3. **No verdict while checks run.** A review verdict is taken only while
   holding the command lock, which a verification holds for its whole run. The
   bound reviewer's SubagentStop waits one second for that lock. When a
   command still holds it, in practice a verification, the stop is only
   recorded on the challenge. The stored report is judged by whoever holds the
   command lock next: that verification when it ends, after it recorded its
   own result, and otherwise the next Stop, `chain gate begin`,
   `chain gate abandon`, `chain run apply`, `chain run status`, `certify`, or
   `verify`. At the end of a verification the order equals a report that
   arrived just after it, so what a verification executes and records is
   unchanged, and no receipt or rework requirement stores a workspace snapshot
   taken in the middle of a check.
4. **A stored report cannot be corrected.** Its reviewer has stopped and the
   hook's answer was already given. A rejection of a stored report therefore
   releases the reviewer on every host, as a rejected hand-back does, with the
   same counting and the same one-replacement bound of an audit.
5. **Stop during a command.** A Stop keeps taking the command lock, with the
   same one second wait as before, so a brief collision with a short command
   is still judged. When a command still holds the lock after that wait, in
   practice a verification, the Stop is neither blocked nor counted. The
   single lock gave that answer by accident; it is now a rule, so that a
   verification in a background shell does not spend the continuation budget.
6. **A receipt for superseded evidence.** A `PASS` receipt whose subject is no
   longer the run's latest all-scope verification is stored but does not
   become the run's current gate. Certification never accepted such a receipt;
   the next action now asks for a fresh gate instead of pointing at
   certification.
7. **The lock file is runtime state.** `.ezpowers/state.lock` is excluded from
   workspace fingerprints, check reuse selection, and the chain baseline
   overlay like `.ezpowers/runtime.lock`; on Windows a held lock file cannot
   even be read. The temporary file of a state write is excluded too, because
   a hook may now save state while a verification takes its snapshots. The
   installer still does not edit a project's ignore file.

The hook wait, the installed hook timeout, the hook matchers, the receipt
schema, and the limits do not change.

## Considered options

- **Wait longer for the lock.** Rejected. The wait is bounded by the 30 second
  hook timeout, a verification usually runs longer, and every tool call of a
  subagent would wait that long.
- **Write the event to a file without the lock and judge it later.** Declined
  by the user in favour of the lock split. It keeps the receipt but leaves
  reviewer binding and the guard out of action during a verification. Serving
  those from a read of the state file without the lock is not safe: on Windows
  an atomic replace of the state file fails while another handle has it open.
- **Judge the report at once and repair the end of the verification.**
  Rejected. A verdict taken in the middle of a check would store a workspace
  snapshot that may hold a check's transient files, in the receipt and in a
  rework requirement, and the end of the verification would have to tell its
  own fields from the hook's.
- **Guidance only.** Declined by the user. The loss would remain.

## Consequences

- A reviewer may report while the main agent verifies. Its report becomes a
  receipt when the verification ends.
- Every project gets a second runtime lock file. A project that hides
  `.ezpowers/runtime.lock` from Git has to add `.ezpowers/state.lock` too.
- A rejected report that arrived during a verification cannot be corrected by
  the same reviewer, also outside `auto`; one new reviewer takes over.
- During a verification a subagent's hook calls no longer wait one second for
  the lock.
- A hook that arrives while another command holds the state lock for more than
  a second is still a no-op. `verify` holds the state lock only from each read
  of state to the save that follows; every other command holds it for its
  whole run, and `chain run apply` reruns the baseline under it.
- A reviewer's stop that arrives during a verification waits one second for
  the command lock before it is recorded.
- `chain run status` and the other commands still answer busy during a
  verification.
- The POSIX lock path uses the same primitive on a second file. It was not run
  on a POSIX host.
