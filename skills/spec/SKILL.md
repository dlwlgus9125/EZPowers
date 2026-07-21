---
name: spec
description: Deepen architecture decisions into detailed feature specs
disable-model-invocation: true
allowed-tools: [Bash, Read, Write, Agent, AskUserQuestion]
shell: powershell
---

# /spec - Detailed Spec Generation

## Purpose

Turn an approved architecture baseline into detailed feature specs. Extract
requirements, update affected roadmap or structure docs, write the spec
artifact, run reviewers, and trigger the internal post-spec audit. Do not
implement code.

Harness state (injected on Claude Code; on Codex read the files directly):

```!
if (Test-Path .harness/config.json) { "CONFIG: present" } else { "CONFIG: MISSING" }
if (Test-Path phases/index.json) { "PHASES_INDEX:"; Get-Content phases/index.json -Raw } else { "PHASES_INDEX: MISSING" }
"HEAD: $(git rev-parse HEAD 2>$null)"
```

## Read

- `docs/reference/mattpocock-harness-adapter.md`
- `docs/reference/spec-contract.md`
- `docs/reference/design-architecture-contract.md`
- `docs/reference/architecture-readiness-contract.md`
- `docs/reference/verification-contract.md`
- `docs/reference/ui-verification-adapter-contract.md`
- `docs/reference/dispatch-protocol.md`
- `docs/reference/reviewer-placement-contract.md`
- `docs/reference/domain-language.md`
- `AGENTS.md`, `.harness/config.json`, `phases/index.json`
- Existing `docs/reference/`, `docs/decisions/`, specs, and recent git changes

## Rules

- If `.harness/config.json` is missing, route to `/setup` and stop.
- If architecture baselines are missing or stale, route to
  `/design-architecture` and stop.
- Set spec `in_progress` in `phases/index.json`; remove stale audit data.
- Read project context before asking. Ask one question at a time.
- Do not weaken architecture, verification, or UI-adapter decisions recorded by
  `/design-architecture`.
- For UI work, carry `docs/ux/frontend-design.md` readiness into the App Experience And Delivery Baseline; route missing readiness back to `/design-architecture`.
- Before extracting requirements, re-check the Operational Requirements
  Checklist in `docs/reference/spec-contract.md`; route material architecture
  changes back to `/design-architecture`.
- For executable artifacts, ask about entry points, component registration
  approach, and cross-module data flow before finalizing the architecture
  baseline. Populate the Wiring Map with unique IDs (WM-EP, WM-REG, WM-DF,
  WM-C) as part of the baseline. For each WM-REG entry, specify the
  recommended Wiring Probe strategy (`import-chain` for pure module imports,
  `runtime-load` for DI/IPC/event registration, `e2e-touch` for user-facing
  feature wiring). This strategy propagates to `/prepare-execute` task Wiring Probes.
- Use `grill-with-docs` before requirement extraction; unresolved architecture
  issues return to `/design-architecture`.
- Use `docs/reference/spec-contract.md` for required spec sections,
  requirement schema, banned vague wording, ADR handling, verify script, and
  docs index updates.
- Dispatch spec, architecture, and UI-triggered frontend experience reviewers
  through `docs/reference/dispatch-protocol.md`; pass paths, not pasted
  artifacts.
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
- Reviewer verdict summaries, including frontend experience review when UI is present.
- Updated `phases/index.json` spec state and audit result.
- Next command: `/prepare-execute` only when audit status is `PASS` or `WARN`.
