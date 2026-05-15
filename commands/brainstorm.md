---
description: Run guided design session to produce spec documents
allowed-tools: [Bash, Read, Write, Agent, AskUserQuestion]
---

# /brainstorm - Spec Document Generation

## Purpose

Turn a request into an approved spec. Establish architecture, extract
requirements, write the spec artifact, run reviewers, and trigger the
post-brainstorm pipeline audit. Do not implement code.

## Read

- `docs/reference/mattpocock-harness-adapter.md`
- `docs/reference/spec-contract.md`
- `docs/reference/architecture-readiness-contract.md`
- `docs/reference/verification-contract.md`
- `docs/reference/dispatch-protocol.md`
- `docs/reference/domain-language.md`
- `AGENTS.md`, `.harness/config.json`, `phases/index.json`
- Existing `docs/reference/`, `docs/decisions/`, specs, and recent git changes

## Rules

- If `.harness/config.json` is missing, route to `/setup` and stop.
- Set brainstorm `in_progress` in `phases/index.json`; remove stale audit data.
- Read project context before asking. Ask one question at a time.
- Do not skip design because the request looks small.
- Produce and confirm the architecture baseline before extracting requirements.
- Before confirming the architecture baseline, evaluate the Operational
  Requirements Checklist in `docs/reference/spec-contract.md`. Ask about each
  applicable concern and record decisions in the baseline.
- For executable artifacts, ask about entry points, component registration
  approach, and cross-module data flow before finalizing the architecture
  baseline. Populate the Wiring Map with unique IDs (WM-EP, WM-REG, WM-DF,
  WM-C) as part of the baseline. For each WM-REG entry, specify the
  recommended Wiring Probe strategy (`import-chain` for pure module imports,
  `runtime-load` for DI/IPC/event registration, `e2e-touch` for user-facing
  feature wiring). This strategy propagates to `/plan` task Wiring Probes.
- Use `grill-with-docs` after architecture baseline approval and before requirement
  extraction; unresolved issues return to design.
- Use `docs/reference/spec-contract.md` for required spec sections,
  requirement schema, banned vague wording, ADR handling, verify script, and
  docs index updates.
- Dispatch spec and architecture reviewers through
  `docs/reference/dispatch-protocol.md`; pass paths, not pasted artifacts.
- After user approval, dispatch `ezpowers:workflow-runner` for `/pipeline-audit`
  in `post-brainstorm` mode.
- After extracting positive ACs for each requirement, extract negative ACs:
  - Ask: "이 요구사항에서 **거부/실패해야 하는 경우**는 무엇인가요?"
  - Focus on: invalid input, boundary violations, authorization failures,
    resource limits, timeout scenarios, concurrent access conflicts.
  - For each identified negative scenario, create an AC with:
    - **Given:** the boundary or error condition
    - **When:** the action that should be rejected
    - **Then:** the specific error response or behavior (NOT vague
      "에러가 발생한다" — specify error code, message, or state)
    - **Verify:** command that triggers the rejection and asserts the error
      response
    - **Verify-type:** same as the positive AC's type
  - **Gate:** Requirements with 3+ positive ACs MUST have at least 1 negative
    AC before spec review. This matches the spec-reviewer's negative AC
    coverage gate (check 9).

## Stop conditions

- Missing harness config.
- Architecture baseline is unapproved or contradicted by repo evidence.
- Requirements are ambiguous after clarification.
- A required Verify command is missing or non-automatable without a replacement
  probe.
- Reviewer verdict is `FAIL` after the retry limits in the dispatch protocol.
- Pipeline audit returns `FAIL` or `NEEDS_USER`.

## Outputs

- Approved architecture baseline summary.
- Confirmed requirement list.
- Spec path and any ADR or verify-script paths.
- Reviewer verdict summaries.
- Updated `phases/index.json` brainstorm state and audit result.
- Next command: `/plan` only when audit status is `PASS` or `WARN`.
