# F28: Completion hook wait and failure rules

## Outcome

A project that enabled the ordinary completion Stop hook can wait for a
background reviewer on Claude Code without being pushed through wasted turns,
keeps a readable block reason on any console encoding, and is never wedged by
a hook that cannot run. The hook still blocks every stop it blocked before
when no subagent is running and the runtime can read the status.

## Scope

Included:

- the ordinary completion Stop adapter (`ezpowers.py hook --host <host>`): a
  wait rule for a running background subagent on Claude Code, a rule for a
  failure of the adapter itself, and UTF-8 input with ASCII-only answers;
- the contract and reference statements of that behavior;
- the 5.11.1 plugin and project-kit release surfaces.

Excluded: the completion verdict, status, evidence, freshness, and
certification; the installed hook entry and installer options; an observe mode
and a switch that removes an installed hook; any change to the chain hooks;
host minimum versions; and live verification of Codex.

Architecture impact: `docs/reference/architecture.md` (ordinary Stop adapter
paragraph) and ADR 0012,
`docs/decisions/0012-completion-hook-wait-and-failure.md`.

## Decisions carried from design

- D28-1 (user decision, 2026-11-19): on Claude Code a Stop that lists a
  running background subagent is not blocked, whatever the status. Shells,
  monitors, and other task types never defer. Codex keeps blocking. An event
  that cannot be read defers nothing.
- D28-2 (user decision, 2026-11-19): an adapter failure the runtime does not
  recognise does not block; the adapter answers with a `systemMessage` warning
  that names the error. A status the runtime can read as invalid still blocks.
- D28-3: the adapter reads host input as UTF-8 bytes and answers with
  ASCII-only JSON.
- D28-4 (user decision, 2026-11-19): no observe mode in this release.

## Requirements

- R1: Waiting for a running background subagent is not blocked on Claude Code,
  and nothing else is deferred.
- R2: A failure of the adapter itself warns and does not block, while an
  invalid status still blocks.
- R3: The answer and the event survive a console encoding that is not UTF-8.
- R4: The contracts and references state the same rules.
- R5: The 5.11.1 surfaces agree and exactly one kit manifest remains.

Failure behavior: every new input is read tolerantly. A missing or malformed
event field yields the earlier verdict.

## Risks and accepted limitations

- Host facts come from `claude -p` runs on Claude Code 2.1.327. An interactive
  session was not run.
- A subagent that never ends leaves the session stopped and uncertified. The
  runtime does not time it out.
- A crash of the adapter opens the gate for that Stop. That was already the
  effective behavior; it is now announced to the user.
- Codex's handling of a `systemMessage`-only Stop answer is documented by the
  host and was not observed.
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
      "claim": "For Claude Code the completion hook returns no block for a Stop event that lists a running background subagent, in READY and in STALE status and also when stop_hook_active is true, while a Stop that lists no task, only a shell or monitor task, a subagent that is not running, or a malformed task list blocks with the status reason, and Codex blocks for the same payload.",
      "verify_type": "e2e",
      "integration": true
    },
    {
      "id": "AC-2",
      "requirement_id": "R2",
      "claim": "When status evaluation fails with an error the runtime does not recognise, the completion hook exits 0 with a systemMessage that names the error and no decision, when it fails with a recognised runtime error the hook blocks with that error as the reason, and a status of FAIL such as unreadable state still blocks.",
      "verify_type": "e2e",
      "integration": true
    },
    {
      "id": "AC-3",
      "requirement_id": "R3",
      "claim": "When the hook process runs under a console encoding that is not UTF-8, a UTF-8 Stop event that contains non-ASCII text is still read, and the answer is ASCII-only JSON whose decoded block reason keeps a project path with characters that encoding cannot represent.",
      "verify_type": "e2e",
      "integration": true
    },
    {
      "id": "AC-4",
      "requirement_id": "R4",
      "claim": "The verification and setup contracts, the host discovery reference, the architecture artifact, and ADR 0012 state the wait rule, the adapter-failure rule, and the encoding rule.",
      "verify_type": "cli",
      "integration": true
    },
    {
      "id": "AC-5",
      "requirement_id": "R5",
      "claim": "The Claude plugin, marketplace, and Codex manifests and the single project-kit manifest report 5.11.1, the kit manifest hashes match their sources, a fresh project installs from it, and no older kit manifest remains.",
      "verify_type": "cli",
      "integration": true
    }
  ]
}
```
<!-- ezpowers:spec:end -->
