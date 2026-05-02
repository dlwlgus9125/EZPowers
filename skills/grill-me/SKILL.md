---
name: grill-me
description: Stress-test a plan or design through relentless questioning until shared understanding is reached. Use when user says "grill me", wants to stress-test a plan, challenge assumptions, or validate design decisions before implementation.
---

# Grill Me

Relentlessly interview the user's plan/design until shared understanding is reached.

## Process

Walk every branch of the decision tree one by one. Resolve dependent decisions in order.

**Rules:**

1. **One question at a time** — never bundle multiple questions
2. **Provide a recommended answer with each question** — no blank questions; include a reasoned suggestion
3. **Explore the codebase first if it can answer the question** — check code before asking the user
4. **Wait for feedback before moving on** — do not proceed without user response

## What to Challenge

- **Vague terms** — "appropriately", "if needed", "etc." → demand concrete definitions
- **Hidden assumptions** — surface unstated premises
- **Edge cases** — throw exception scenarios at designs that only cover the happy path
- **Unexplored alternatives** — "Why Y and not X?" Prevent fixation on the first idea
- **Dependency order** — identify where deciding A is prerequisite to deciding B
- **Scope boundaries** — verify inclusion/exclusion criteria are explicit

## Completion

End when all decision branches are resolved and the user expresses satisfaction. No forced termination.
