# ADR 0012: Completion hook waits for subagents and warns on its own failure

- Status: accepted
- Date: 2026-11-19
- Decision owners: EZPowers maintainers
- Related: `docs/reference/architecture.md`,
  `docs/decisions/0001-host-native-project-local-core.md`,
  `docs/decisions/0011-current-host-chain-adapter.md`

## Context

The optional ordinary Stop adapter (`ezpowers.py hook`) blocks a stop while an
active plan has no fresh certificate. It consumed its input without reading
it. ADR 0011 gave the chain Stop hook a deferral for running background
subagents and left the ordinary adapter for a decision of its own.

Observed on Claude Code 2.1.327 on 2026-11-19, in a project whose status was
`READY` (fresh evidence, no certificate) and a session that started one
background reviewer and ended its turn to wait for it:

- The adapter blocked nine Stops in a row while the reviewer ran. Each block
  produced a turn that only repeated that the session was waiting. The host
  then overrode the hook and ended the turn, so the adapter never was an
  absolute lock.
- The Stop that followed the reviewer's report arrived with
  `stop_hook_active` false and was judged afresh.

Reproduced without a host:

- The block reason is printed in the console's locale encoding. On a Korean
  Windows console a reason that names a path with a character cp949 cannot
  encode makes the adapter exit with an error before it answers, and Claude
  Code documents a hook that fails that way as a non-blocking error: the stop
  goes ahead. A Korean path leaves an answer that is not valid UTF-8, with a
  garbled reason.
- No rule said what a failure of the adapter itself means.

## Decision

1. **Wait.** On Claude Code a Stop whose input lists a running background
   subagent is not blocked, whatever the status. The host starts the next turn
   when the subagent reports, and that Stop is judged as before. Shells,
   monitors, and other background task types never defer, because they may
   never end. Codex sends no such list and keeps blocking. An event that
   cannot be read defers nothing.
2. **Adapter failure.** If the adapter fails with an error the runtime does
   not recognise, it does not block. It answers with the host's
   `systemMessage` warning, names the error, and exits successfully. A status
   the runtime can read as invalid still blocks with its reasons: corrupt
   state, a missing or invalid plan or config, an unusable Git workspace.
3. **Encoding.** The adapter reads host input as UTF-8 bytes and answers with
   ASCII-only JSON, whatever the console encoding is.

The completion verdict, status, evidence, freshness, and certification do not
change. The adapter stays optional and off by default. Rules 2 and 3 apply to
both hosts.

## Considered options

- **Keep blocking while a subagent runs.** Rejected by the user. It cost nine
  turns and a warning per wait, and the host ended the turn anyway.
- **Block when the adapter itself fails.** Rejected by the user. The model
  cannot repair a broken hook, and the host's cap only applies when no tool is
  called between Stops.
- **Add an observe mode that reports instead of blocking.** Declined by the
  user for now. No concrete need exists yet, and it adds installer and
  contract surface.
- **Allow every Stop whose `stop_hook_active` is true.** Rejected. That is the
  host's general advice to hook authors, but it would reduce the gate to one
  reminder per turn.
- **Let a recognised invalid status pass too.** Rejected. Deleting or breaking
  the plan would open the gate.
- **Defer for every background task type.** Rejected for the reason in ADR
  0011: shells and monitors may never end.

## Consequences

- "Only a fresh certified result permits stopping" has one exception: a wait
  for a running subagent on Claude Code. A subagent that never ends leaves the
  session stopped and uncertified. Nothing records a false certificate.
- An adapter crash cannot wedge a session. The warning is the only signal. A
  crash that somebody induces on purpose opens the gate for that Stop, as it
  did before, now with a visible warning.
- Block reasons survive any console encoding.
- Codex keeps blocking in every case in which it blocked before. Its
  `systemMessage` handling is documented by the host and was not observed.
- An installed project receives the adapter with `setup --refresh`. The
  installed hook entry does not change.
