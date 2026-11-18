# F27: Current-host flow alignment

## Outcome

The explicit harness chain works on the Claude Code version users run today,
and the ordinary workflow tells the host to exercise a change, handle flaky
checks, and use its own review the way the Claude Code team's verification
practice describes. A user who configures a chain in a default Claude Code
session reaches `READY`, a bound reviewer's receipt registers in `auto` mode,
waiting for that reviewer costs no continuation budget, and the frozen-file
guard stops blocking the runtime's own commands.

## Scope

Included:

- the chain's Claude host adapter: permission-mode source and accepted modes,
  review receipt source, Stop deferral, frozen-file guard, hook matchers and
  installed-hook comparison;
- a bound on replacing a reviewer whose report was rejected, including the
  finished-run case that let a rejected oracle-audit receipt reopen the audit
  for another reviewer;
- the code-review rubric wording;
- guidance text in `execute`, `prepare-execute`, and `harness-chain`, and the
  matching contract statements;
- pruning `PROGRESS.md` history and removing kit manifests that no runtime or
  gate reads;
- the 5.11.0 plugin and project-kit release surfaces.

Excluded: the ordinary completion hook, any change to verdict, evidence,
freshness, receipt schema, configured limits, or host minimum versions, a
Codex-specific mode list, live verification of the Codex chain, reviewer
personas, model routing, and a "stop after three failed rounds" rule for
ordinary execution.

Architecture impact: `docs/reference/architecture.md` (chain host adapter
paragraph) and ADR 0011, `docs/decisions/0011-current-host-chain-adapter.md`.

## Decisions carried from design

- D27-1: the handshake happens at SessionStart; the permission mode comes from
  the first hook event of that session that reports one, and an unobserved
  mode is not a changed mode.
- D27-2: Claude Code is unattended-capable in `auto`, `dontAsk`, or
  `bypassPermissions`; Codex keeps `dontAsk` and `bypassPermissions`.
- D27-3: a receipt comes from the bound reviewer's hand-back message when it
  carries a gate marker, otherwise from its SubagentStop message. A rejected
  hand-back releases the binding for a new reviewer, because the host does
  not continue a subagent after its hand-back.
- D27-4: a Claude Stop during `RUNNING` with a running background subagent
  neither blocks nor counts; shells and monitors never defer.
- D27-5: the guard judges file tools by target and shell commands by write
  intent toward a named frozen file; both hosts share the classification.
- D27-6: installed hooks are current only when each chain event has an owned
  entry with the current matcher.
- D27-7: chain hooks decode host input as UTF-8 and answer with ASCII-only
  JSON, whatever the console encoding is.
- D27-8 (user decision, 2026-11-19): reviewer replacement is bounded. Inside a
  run every rejection counts as a review failure, so the approved review limit
  ends the run. Before a run nothing counts, so an oracle audit allows one
  replacement and a second rejected hand-back closes that preview the way an
  audit `FAIL` does. A finished run left in state does not end a pending
  oracle audit.

## Requirements

- R1: The recorded permission mode reflects the session even though
  SessionStart does not report it.
- R2: `auto` is accepted for Claude Code and the Codex set is unchanged.
- R3: A bound reviewer's hand-back creates the receipt; nobody else's does.
- R4: Waiting for a background subagent does not spend continuation budget.
- R5: The guard allows the runtime's own commands and denies direct writes
  through every inspected tool.
- R6: Outdated installed hooks are reported and block readiness until the
  configuration is applied again.
- R7: The code-review rubric separates blocking defects from nits and
  pre-existing defects without changing the receipt schema.
- R8: Skills and contracts state the same behavior and the verification
  guidance.
- R9: The 5.11.0 surfaces agree and exactly one kit manifest remains.
- R10: Replacing a reviewer after a rejected report is bounded, and a
  finished run does not reopen an oracle audit for another reviewer.

Failure behavior: every new host input is read tolerantly. A missing or
malformed field yields the earlier behavior, and a chain hook that cannot read
runtime state still degrades to the fail-safe empty response.

## Risks and accepted limitations

- Host payload facts come from `claude -p` probe runs and chain runs on Claude
  Code 2.1.327. Interactive sessions, `fork`, and compaction were not probed.
- No part of the Codex chain was run on a live host.
- A reviewer that never reports leaves the run `RUNNING` and the session
  waiting; the runtime does not time it out.
- `auto` can still deny an action or return to prompting; EZPowers does not
  prevent or count that.
- Two rejected hand-backs in a row close an oracle audit for that preview even
  when the acceptance contract is sound; the staged contract must then change.
- The replacement path is proven with recorded payload shapes. A second live
  reviewer taking over a released challenge was not run on a real host.
- The guard is an early guard. Indirect writes pass it and are caught by the
  hash check before verification, review, and certification.
- This repository's own `unit` check has a timeout shorter than its run time,
  so completion evidence here is the release gates run directly, not an
  in-repository all-scope certificate.

<!-- ezpowers:spec:start -->
```json
{
  "schema_version": 1,
  "design_context": {
    "required": false,
    "reason": "The guide receives content-only updates; no UI structure, tokens, or reusable styling changes."
  },
  "criteria": [
    {
      "id": "AC-1",
      "requirement_id": "R1",
      "claim": "After a SessionStart event that reports no permission mode, the first later hook event of the same session that reports one sets the handshake mode, a later event with a different mode does not replace it, and a running chain whose session has not reported a mode yet is not moved to NEEDS_REAPPROVAL.",
      "verify_type": "e2e",
      "integration": true
    },
    {
      "id": "AC-2",
      "requirement_id": "R2",
      "claim": "Chain readiness is READY for a Claude Code session whose recorded mode is auto, dontAsk, or bypassPermissions and PENDING_HOST_TRUST with a reason naming interactive approval for any other mode, while Codex accepts only dontAsk and bypassPermissions.",
      "verify_type": "e2e",
      "integration": true
    },
    {
      "id": "AC-3",
      "requirement_id": "R3",
      "claim": "A gate marker delivered by the bound reviewer through a SubagentHandback tool call creates the receipt even when the hook process runs under a non-UTF-8 console encoding, the same call from another agent or session creates none, a rejected hand-back is discarded and frees the binding for a new reviewer on the same challenge, and without a hand-back the SubagentStop message is used.",
      "verify_type": "e2e",
      "integration": true
    },
    {
      "id": "AC-4",
      "requirement_id": "R4",
      "claim": "For Claude Code a Stop event during a RUNNING chain that reports a running background subagent returns no block and leaves every counter unchanged, while a Stop that reports none, reports only shell or monitor tasks, arrives in PENDING_LOOP, or arrives on Codex behaves as before.",
      "verify_type": "e2e",
      "integration": true
    },
    {
      "id": "AC-5",
      "requirement_id": "R5",
      "claim": "During a nonterminal chain run the PreToolUse guard allows the runtime's own verify, certify, trace, and validate commands on the frozen plan, a script or test run that names a frozen file, a copy of one to another place, and written content that only mentions one, and it denies Write, Edit, and NotebookEdit targets, apply_patch file headers, direct Bash or PowerShell mutations, redirections, copies onto a frozen file, and inline interpreter code aimed at one, on both hosts.",
      "verify_type": "e2e",
      "integration": true
    },
    {
      "id": "AC-6",
      "requirement_id": "R6",
      "claim": "Chain configuration writes Claude matchers that include fork, PowerShell, NotebookEdit, and SubagentHandback and leaves the Codex matchers unchanged, and a project whose installed matcher differs from the current definition reports its hooks as missing or changed and is not READY until the configuration is applied again.",
      "verify_type": "e2e",
      "integration": true
    },
    {
      "id": "AC-7",
      "requirement_id": "R7",
      "claim": "The code-review rubric tells the reviewer to block only on defects the change introduces or exposes and to record nits and pre-existing defects as observations, and every rubric template still parses as exactly one FAIL receipt.",
      "verify_type": "e2e",
      "integration": true
    },
    {
      "id": "AC-8",
      "requirement_id": "R8",
      "claim": "The execute, prepare-execute, and harness-chain skills and the harness-chain and verification contracts state the run-the-change step, the flaky-check rule, the host review pointer, the check selection guidance, the unattended modes, the receipt source, the Stop deferral, and the native-goal prohibition.",
      "verify_type": "cli",
      "integration": true
    },
    {
      "id": "AC-9",
      "requirement_id": "R9",
      "claim": "The Claude plugin, marketplace, and Codex manifests and the single project-kit manifest report 5.11.0, the kit manifest hashes match their sources, a fresh project installs from it, and no older kit manifest remains.",
      "verify_type": "cli",
      "integration": true
    },
    {
      "id": "AC-10",
      "requirement_id": "R10",
      "claim": "Inside a running chain every rejected hand-back counts as a review failure, admits a new reviewer on the same challenge, and ends the run at the approved review limit; before a run a second rejected hand-back on one oracle-audit challenge closes that preview so that another audit is refused until the staged contract changes; and with a finished run left in state a rejected oracle-audit receipt keeps its bound reviewer for a correction and admits no other reviewer.",
      "verify_type": "e2e",
      "integration": true
    }
  ]
}
```
<!-- ezpowers:spec:end -->
