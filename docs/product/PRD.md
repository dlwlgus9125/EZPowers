---
doc_type: product
authority: canonical
status: active
---

# EZPowers PRD

EZPowers gives each target project a small, local workflow layer for facts that
vary by repository: canonical agent guidance, structured documentation, local
supporting knowledge, settled requirements, architecture and plan artifacts,
exact completion commands, durable evidence, and resume state. It supports
both Claude Code and Codex while leaving implementation mechanics to the host.
For users who explicitly request it, the same local facts can be composed into
one approved, unattended feature chain without adding a second Codex loop.

## User Outcome

A user can install EZPowers into a project, bootstrap a repository-evidenced
Markdown graph, optionally retain allowlisted local session knowledge, clarify
vague intent, write confirmed intent as traceable acceptance criteria, map
those criteria to real project checks, implement with either supported host,
and receive the same pass/fail completion verdict from repository evidence. A
new session can navigate project authority and determine what is fresh without
trusting conversation memory.

When a project needs unattended work, the user can answer project-level chain
questions once, inspect a real failing/passing oracle baseline and independent
audit, approve one exact feature contract, and leave. Recoverable product
failures force rework within hard limits; changed acceptance inputs, genuine
blockers, exhausted limits, or certification end the run deterministically.

## Product Boundary

EZPowers owns:

- documentation staging, whole-file ownership, graph lint, and conflict-safe
  apply/backup;
- local wiki structure, deterministic CJK keyword/tag search, promotion
  bindings, and opt-in allowlisted capture;
- project-local spec and plan schemas;
- check argv, working directories, kinds, and timeouts;
- fail-closed execution, stdout/stderr logs and hashes;
- binding evidence to spec/plan/config, the installed-kit identity, and the
  Git workspace;
- certification, staleness, tamper detection, and resume status;
- explicit chain configuration, frozen feature approvals, independent-review
  challenges and hashed receipts, hard limits, and terminal states;
- thin host adapters and optional frontend readiness detection.

Claude Code and Codex own code changes, shell UX, model choice, spawning
subagents, worktrees, sandboxing, and implementation decisions. Ordinary
execution also leaves general retries and review entirely to the host. In an
explicit chain, EZPowers binds host-native reviewer identities and counts
approved attempts, but does not supply reviewer agents or perform the review.
EZPowers does not require an external shared repository or executor.

## Success Conditions

- Installation is hash-verified, conflict-safe, and self-contained.
- Host-specific hooks are configured only with Claude Code 2.1.217 or newer
  and Codex CLI 0.145.0 or newer.
- Both hosts receive byte-identical local workflow instructions.
- `AGENTS.md` is canonical, `CLAUDE.md` imports it, and ready documentation
  graphs pass a required deterministic lint.
- Documentation replacement is preview-bound, preserves unmanaged edits, and
  backs up explicitly forced targets.
- Local wiki capture never stores transcripts or affects completion freshness.
- Every acceptance criterion is mapped exactly once to executable checks.
- Integration criteria require a real integration, end-to-end, or smoke check.
- Merely validating a candidate plan cannot alter the active resume target.
- Task evidence is revalidated for resume guidance without becoming completion.
- Only fresh, complete, untampered all-scope evidence certifies completion.
- Harness chains are explicit-only and use one continuation authority: a
  native Codex goal or a Claude Stop loop, never both.
- A chain cannot certify without a real baseline, a bound independent code
  review, conditional adversarial QA, and unchanged frozen inputs.
- A failure that reaches an approved limit is terminal immediately; no extra
  pass is granted to rationalize continuation.
- Removed orchestration concepts have no live reference or advertised flow.
