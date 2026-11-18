# ADR 0011: Current-host chain adapter

- Status: accepted
- Date: 2026-11-18
- Decision owners: EZPowers maintainers
- Related: `docs/reference/architecture.md`,
  `docs/decisions/0001-host-native-project-local-core.md`,
  `docs/decisions/0003-explicit-asymmetric-harness-chain.md`,
  `docs/decisions/0007-evidence-gated-assurance-graph.md`

## Context

The harness chain (ADR 0003) drives Claude Code through project hooks. Those
hooks had been tested only with synthetic payloads. A probe of Claude Code
2.1.327 on 2026-11-18 recorded the real ones and found the adapter out of step
with the host:

- SessionStart carries no `permission_mode`. The runtime read the mode only
  there, so a real session recorded none and chain readiness could never be
  reached. PreToolUse, Stop, and SubagentStop do carry it.
- Terminal sessions start in `auto` by default. The runtime accepted only
  `dontAsk` and `bypassPermissions`.
- In `auto` a subagent delivers its final report through a `SubagentHandback`
  tool call. SubagentStop then has no `last_assistant_message`, which was the
  only place the runtime looked for a review receipt.
- Subagents run in the background by default. The main turn ends while the
  reviewer works, and Stop reports it in `background_tasks`. The runtime
  blocked and counted an iteration on every such Stop.
- The frozen-file early guard denied the runtime's own
  `verify --plan <frozen plan>` command and any written content that merely
  mentioned a frozen file, while it never inspected the Windows `PowerShell`
  tool or `NotebookEdit`.
- Hook presence was judged by existence, so a project whose installed matchers
  predate a kit kept looking configured.

The first full chain run on the real host then failed at the review gate and
showed two more:

- The hook decoded the host's UTF-8 input with the console's locale encoding.
  On a Korean Windows machine one ellipsis in the reviewer's report made the
  hook exit with an error, so the report was never stored. The test suite runs
  in UTF-8 mode and could not see it.
- A subagent that has handed its report back is not continued when its
  SubagentStop is blocked. The existing rule that the same reviewer corrects a
  malformed receipt therefore cannot work in `auto`; the gate stayed bound to
  a finished agent until the run reached its iteration limit.

The final review of this change found one more, older than the adapter: a
finished run left in state ended any pending gate on a rejected receipt,
including an oracle audit for the next feature. Every rejected audit report
then opened a fresh challenge for a different reviewer, in every permission
mode, although the contract says cycling reviewers is not a retry path.

The review was prompted by the Claude Code team's account of how it verifies
work (2026-11-16): a check must stay out of reach of the change it judges, and
verification means exercising the real system. This adapter exists to enforce
the first and had never been exercised by the second.

## Decision

Treat host payload shape as adapter data owned by the runtime, and align it
with the observed host. The completion verdict, the receipt schema and marker,
hard limits, and hash checks do not change. Reviewer binding changes in one
case, described in decision 3.

1. **Permission mode source.** The handshake still happens at SessionStart.
   The mode is taken from the first hook event of that session that reports
   one. A mode that has not been observed yet is not treated as a changed one.
2. **Unattended modes.** Claude Code is unattended-capable in `auto`,
   `dontAsk`, or `bypassPermissions`. `auto` is capable, not guaranteed: the
   host's classifier can deny an action and returns to prompting after
   repeated blocks. That boundary stays host-owned and is disclosed before
   feature approval.
3. **Receipt source.** Only the bound reviewer's final report creates a
   receipt: the message of its hand-back call when that carries a gate marker,
   otherwise its SubagentStop message. The two are never combined. A reviewer
   is still bound by agent ID, session, and challenge. When a handed-back
   report is rejected, the hook cannot continue that reviewer, so the binding
   is released for a new reviewer on the same challenge. Replacement is bounded.
   Inside a run every rejection counts as a review failure and the approved
   review limit ends the run. Before a run nothing counts, so an oracle audit
   allows one replacement, and a second rejected hand-back closes that
   preview for auditing the way an audit `FAIL` does. A finished run left in
   state no longer ends a pending oracle audit: a rejected audit report keeps
   its reviewer there, as the contract always said.
4. **Stop deferral.** A Claude Stop that arrives while the run is `RUNNING`
   and a background subagent is still running neither blocks nor counts. The
   host resumes the session when the subagent reports. Background shells and
   monitors never defer a Stop, because they may never end.
5. **Guard precision.** File tools are judged by their target only. A shell
   command is denied when it names a frozen file together with a direct
   mutation, a redirection into it, a copy onto it, or inline interpreter
   code; running a script or test that names one, or copying it elsewhere, is
   allowed. The Claude matcher adds `PowerShell` and `NotebookEdit`. The
   classification reads only the tool payload, so both hosts share it.
6. **Hook currency.** A host's hooks count as installed only when each chain
   event has a runtime-owned entry with the current matcher. The Claude
   SessionStart matcher adds `fork`.
7. **Hook encoding.** Chain hooks decode host input as UTF-8 bytes and answer
   with ASCII-only JSON, whatever the console encoding is.

Codex keeps its matchers, its accepted modes, and its continuation behavior.
The changes that do not branch on the host apply to it as well: the shared
guard classification, taking the mode from a later event when SessionStart
reported none and tolerating a mode not yet observed, UTF-8 hook input with
ASCII answers, the code-review rubric wording, the comparison of installed
matchers, and a finished run no longer ending a pending oracle audit. No part
of the Codex chain was run on a live host; it stays labelled
unverified, including the earlier deferral of its terminal Stop response and
its use of Claude mode names.

## Considered options

- **Use the host's native goal as the Claude chain loop.** Rejected. It is a
  session-scoped Stop hook judged by a small model from the transcript. It
  cannot read hashes, receipts, or limits, and running it beside the project
  Stop hook would be a second continuation authority.
- **Keep reading the mode at SessionStart and only widen the accepted set.**
  Rejected: the field is absent there, so no mode would ever be accepted.
- **Stop after three failed rounds and call a human in ordinary `execute`.**
  Declined by the user. `diagnose` re-grounds on the exact-red loop after
  three failed patches instead of stopping, root cause is not a handoff point,
  and the chain already has hard limits of three for validation, review, and
  identical failures.
- **Raise the host minimum versions.** Rejected. Every new input is read
  tolerantly, so an older host keeps the earlier behavior.
- **Give the ordinary completion hook the same deferral.** Deferred. It would
  relax "only a fresh certified result permits stopping" and needs its own
  decision.
- **Leave reviewer replacement unbounded before approval, or never release
  the binding.** The user chose the bound. Unbounded replacement lets a
  malformed `FAIL` be answered by another reviewer's `PASS`. Never releasing
  leaves an `auto` gate bound to a reviewer that cannot answer: a run then
  fails only at its iteration limit, and an audit before the first run stays
  pending until state is repaired by hand.

## Consequences

- A project that already configured a chain must run `chain config preview`
  and `chain config apply` again after refreshing to this kit, then restart the
  session, because the Claude matchers changed. A nonterminal run on that host
  becomes `NEEDS_REAPPROVAL`.
- A reviewer that never reports no longer drives the run to `FAILED` at the
  iteration limit. The session waits instead; that wait is a host state, not a
  runtime verdict.
- The early guard is narrower and more exact. Indirect writes (a script that
  rewrites its argument, a whole-tree command, a target built from a
  variable) pass it and are caught by the hash check before verification,
  review, and certification, as before.
- An `auto` run can still stop for the host. EZPowers neither prevents nor
  counts that.
- Two rejected hand-backs in a row close an oracle audit for that preview even
  when the acceptance contract is sound. The staged contract must change to
  produce a new preview hash.
- With a finished run in state, a rejected oracle-audit receipt now blocks its
  reviewer for a correction instead of dropping the gate, in every permission
  mode and on both hosts.
- "Cannot be continued" describes the hook: a blocked SubagentStop is not
  honored after a hand-back. The host does offer the main agent a way to
  message a finished subagent. Whether a reviewer continued that way binds to
  the released challenge again was not checked; the supported path is a new
  reviewer.
