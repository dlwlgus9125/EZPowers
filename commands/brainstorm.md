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
- Use `grill-with-docs` after architecture baseline approval and before requirement
  extraction; unresolved issues return to design.
- Use `docs/reference/spec-contract.md` for required spec sections,
  requirement schema, banned vague wording, ADR handling, verify script, and
  docs index updates.
- Dispatch spec and architecture reviewers through
  `docs/reference/dispatch-protocol.md`; pass paths, not pasted artifacts.
- After user approval, dispatch `ezpowers:workflow-runner` for `/pipeline-audit`
  in `post-brainstorm` mode.

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
