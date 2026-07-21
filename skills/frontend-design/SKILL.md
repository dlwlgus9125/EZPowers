---
name: frontend-design
description: Use when frontend, UI, UX, design system, screen structure, component taxonomy, design tokens, responsive behavior, accessibility, Storybook, visual QA, or "MVP-looking UI" concerns must be resolved before implementation. Not for directly coding UI without first producing or updating the frontend design artifact.
---

# Frontend Design

## Overview

Design frontend decisions before implementation. Output
`docs/ux/frontend-design.md` for `/spec` and `/prepare-execute`.

## Workflow

1. Read manifests, routes, views, components, styles, visual tooling, tests,
   design docs, and `docs/reference/*`.
2. Propose 2-3 distinct design directions with tradeoffs.
3. Ask for the selected direction or record delegated choice.
4. Draft or update `docs/ux/frontend-design.md` with screens, IA, UX state
   matrix, repo-owned tokens, token policy, component taxonomy, responsive
   rules, accessibility, assets, mock/prototype artifacts, and visual
   QA.
5. Hand off to `/spec` with the design artifact path and unresolved questions.

For the full artifact checklist and default policies, read
`references/frontend-design-readiness.md`.

## Rules

- Do not implement product UI code from this skill.
- Reuse the repo's existing design system, tokens, components, and route
  conventions when they exist.
- If no design system exists, choose repo-owned tokens and primitives. Figma is optional input, not a blocker.
- Full visual automation is tool-conditional: require it when project-local
  tooling exists or the plan adds it; otherwise preserve the same user-visible
  oracle.
- Hard-gate Storybook, Playwright screenshots, visual diff baselines, or
  screenshot/visual review loops only from project-local tooling evidence or
  explicit plan prerequisite tasks.
- Treat Playwright e2e-only projects as browser verification, not as
  screenshot/visual baseline projects, until screenshot-specific evidence
  exists.
- Accept equivalent tools when project-local evidence exists: Ladle or Histoire
  for component isolation, and Chromatic, Percy, Loki, reg-suit, BackstopJS,
  Argos, Applitools, jest-image-snapshot, pixelmatch, or lost-pixel for visual
  diff/baseline workflows.
- Use `scripts/frontend-visual-readiness.py` to detect advisory versus
  hard-gated visual lanes. Use `--mode check` for gates; `--mode detect` is
  advisory. In monorepos, inspect workspace frontend roots or pass
  `--frontend-root`.
- If a mock/prototype artifact is normative, record token/component mapping and
  a freshness rule; if it is reference-only, say implementation follows the
  repo-owned design artifact and not as the source of truth.
- Treat placeholder or MVP visuals as unfinished unless the user explicitly
  accepts that risk in the artifact.
- Keep UX state matrix coverage and implementation sequencing compatible with:
  `tokens -> primitives -> component states/stories -> screens -> e2e/visual`.

## Stop Conditions

Report `NEEDS_USER` when audience, surface, or selected direction is unknown
and the user has not delegated the choice.
