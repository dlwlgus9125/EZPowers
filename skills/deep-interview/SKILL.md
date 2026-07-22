---
name: deep-interview
description: Use when a request is ambiguous, the user asks for deep-interview or requirement clarification, or says "grill me", "그릴미", "grill-with-docs", stress-test, or challenge assumptions about an existing spec, design, or plan. Not for small concrete edits whose goal, scope, constraints, and completion criteria are already settled.
---

# Deep Interview

Turn uncertainty into explicit decisions before implementation. Keep the
interview separate from `spec`: this skill settles decisions; `spec` records
settled decisions as an acceptance contract.

## Select a mode

- Use `clarify` for a rough request whose goal, scope, constraints, or success
  criteria are unclear.
- Use `stress-test` when the user says "grill me" or "그릴미", names that mode,
  or supplies an existing spec, design, or plan to challenge.
- State the selected mode. Never silently reduce a stress test to ordinary
  requirement clarification.

## Common rules

1. Read the repository, target artifact, `CONTEXT.md`, and relevant ADRs before
   asking anything the files can answer.
2. Track resolved decisions and the highest-impact open decision.
3. Ask one question at a time. Include the current understanding, the blocked
   decision, and a recommended answer with its tradeoff.
4. Wait for the answer before advancing. Do not invent user preferences.
5. Stop when the remaining questions cannot materially change the work.

## Clarify mode

Resolve these dimensions in dependency order:

- goal and audience;
- included and excluded scope;
- constraints and compatibility boundaries;
- observable completion criteria;
- unresolved decisions that would change implementation.

Finish with a compact decision brief containing those five fields. Do not
create a spec automatically; hand the settled brief to `spec` when requested.

## Stress-test mode

Walk the target's decision branches rather than merely asking for more scope.
Challenge, in order:

1. terms that conflict with `CONTEXT.md` or have multiple meanings;
2. assumptions contradicted by repository evidence;
3. omitted failure modes and boundary cases;
4. credible alternatives and why the chosen option wins;
5. dependency order, reversibility, and explicit exclusions;
6. whether each success claim has an observable test or evidence source.

When a branch survives, record the decision and move to the next unresolved
branch. When it fails, revise the target decision before continuing.

## Durable context

Use [references/context-format.md](references/context-format.md) when domain
language changes.

- Update `CONTEXT.md` immediately after the user resolves a project-specific
  term. Do not record generic programming vocabulary or implementation names.
- Offer an ADR only when the decision is hard to reverse, surprising without
  context, and the result of a real tradeoff. All three conditions are required.
  Create or update it only after the user accepts the offer.
- Preserve existing human-authored content and ask before replacing a
  conflicting definition or ADR decision.

## Finish

Return the selected mode, settled decisions, rejected alternatives, changed
context or ADR paths, remaining open decisions, and the next appropriate
workflow step. Do not claim readiness while a material decision remains open.
