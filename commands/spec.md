---
description: Deepen architecture decisions into detailed feature specs
allowed-tools: [Bash, Read, Write, Agent, AskUserQuestion]
---

# /spec - Detailed Spec Generation

## Purpose

Turn an approved architecture baseline into detailed feature specs. Extract
requirements, update affected roadmap or structure docs, write the spec
artifact, run reviewers, and trigger the internal post-spec audit. Do not
implement code.

## Read

- `docs/reference/mattpocock-harness-adapter.md`
- `docs/reference/spec-contract.md`
- `docs/reference/design-architecture-contract.md`
- `docs/reference/architecture-readiness-contract.md`
- `docs/reference/verification-contract.md`
- `docs/reference/ui-verification-adapter-contract.md`
- `docs/reference/dispatch-protocol.md`
- `docs/reference/domain-language.md`
- `AGENTS.md`, `.harness/config.json`, `phases/index.json`
- Existing `docs/reference/`, `docs/decisions/`, specs, and recent git changes

## Rules

- If `.harness/config.json` is missing, route to `/setup` and stop.
- If architecture baselines are missing or stale, route to
  `/design_architecture` and stop.
- Set spec `in_progress` in `phases/index.json`; remove stale audit data.
- Read project context before asking. Ask one question at a time.
- Do not weaken architecture, verification, or UI-adapter decisions recorded by
  `/design_architecture`.
- Before extracting requirements, re-check the Operational Requirements
  Checklist in `docs/reference/spec-contract.md`; route material architecture
  changes back to `/design_architecture`.
- For executable artifacts, ask about entry points, component registration
  approach, and cross-module data flow before finalizing the architecture
  baseline. Populate the Wiring Map with unique IDs (WM-EP, WM-REG, WM-DF,
  WM-C) as part of the baseline. For each WM-REG entry, specify the
  recommended Wiring Probe strategy (`import-chain` for pure module imports,
  `runtime-load` for DI/IPC/event registration, `e2e-touch` for user-facing
  feature wiring). This strategy propagates to `/prepare_execute` task Wiring Probes.
- Use `grill-with-docs` before requirement extraction; unresolved architecture
  issues return to `/design_architecture`.
- Use `docs/reference/spec-contract.md` for required spec sections,
  requirement schema, banned vague wording, ADR handling, verify script, and
  docs index updates.
- Dispatch spec and architecture reviewers through
  `docs/reference/dispatch-protocol.md`; pass paths, not pasted artifacts.
- If maintenance work changes structure, roadmap, testing method, or UI
  adapter requirements, update the corresponding docs before review.
- After user approval, dispatch `ezpowers:workflow-runner` through the dispatch
  protocol: target command `internal pipeline audit`, invocation mode
  `post-spec`, working directory project root, artifacts spec path and
  architecture docs.
- Extract negative ACs for requirements with 3+ positive ACs. Ask what must be
  rejected or fail, then specify concrete Given/When/Then/Verify outcomes.

## Stop conditions

- Missing harness config.
- Architecture baseline is unapproved or contradicted by repo evidence.
- Requirements are ambiguous after clarification.
- A required Verify command is missing or non-automatable without a replacement
  probe.
- Reviewer verdict is `FAIL` after the retry limits in the dispatch protocol.
- Pipeline audit returns `FAIL` or `NEEDS_USER`.

## Outputs

- Architecture baseline deltas or confirmation that none changed.
- Confirmed requirement list.
- Spec path, updated roadmap/structure/test docs, and any ADR or verify-script
  paths.
- Reviewer verdict summaries.
- Updated `phases/index.json` spec state and audit result.
- Next command: `/prepare_execute` only when audit status is `PASS` or `WARN`.
