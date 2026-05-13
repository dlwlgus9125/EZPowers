---
name: grill-with-docs
description: Stress-test a plan or design through relentless questioning while updating CONTEXT.md and ADRs inline. Use when user says "grill me", wants to stress-test a plan, challenge assumptions, validate design decisions, or sharpen domain terminology before implementation.
---

# Grill With Docs

Relentlessly interview the user's plan/design until shared understanding is reached. Update domain documentation as decisions crystallise.

## Process

Walk every branch of the decision tree one by one. Resolve dependent decisions in order.

**Rules:**

1. **One question at a time** — never bundle multiple questions
2. **Provide a recommended answer with each question** — no blank questions; include a reasoned suggestion
3. **Explore the codebase first if it can answer the question** — check code before asking the user
4. **Wait for feedback before moving on** — do not proceed without user response

## What to Challenge

- **Vague terms** — "appropriately", "if needed", "etc." -> demand concrete definitions
- **Hidden assumptions** — surface unstated premises
- **Edge cases** — throw exception scenarios at designs that only cover the happy path
- **Unexplored alternatives** — "Why Y and not X?" Prevent fixation on the first idea
- **Dependency order** — identify where deciding A is prerequisite to deciding B
- **Scope boundaries** — verify inclusion/exclusion criteria are explicit

## Domain Awareness

During codebase exploration, read `CONTEXT.md` if it exists.

### Challenge against the glossary

When the user uses a term that conflicts with the existing language in `CONTEXT.md`, call it out immediately. "Your glossary defines 'cancellation' as X, but you seem to mean Y -- which is it?"

### Sharpen fuzzy language

When the user uses vague or overloaded terms, propose a precise canonical term. "You're saying 'account' -- do you mean the Customer or the User? Those are different things."

### Cross-reference with code

When the user states how something works, check whether the code agrees. If you find a contradiction, surface it.

### Update CONTEXT.md inline

When a term is resolved, update `CONTEXT.md` right there. Don't batch these up -- capture them as they happen. Use the format in [references/context-format.md](references/context-format.md).

Don't couple `CONTEXT.md` to implementation details. Only include terms meaningful to domain experts.

### Offer ADRs sparingly

Only offer to create an ADR in `docs/decisions/` when all three are true:

1. **Hard to reverse** — the cost of changing your mind later is meaningful
2. **Surprising without context** — a future reader will wonder "why did they do it this way?"
3. **The result of a real trade-off** — there were genuine alternatives and you picked one for specific reasons

If any of the three is missing, skip the ADR.

## Completion

End when all decision branches are resolved and the user expresses satisfaction. No forced termination.
