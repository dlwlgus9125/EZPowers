---
name: frontend-design
description: Use when frontend, UI, UX, design system, screen structure, component taxonomy, design tokens, responsive behavior, accessibility, or visual QA decisions must be settled before implementation. Not for directly coding UI.
---

# Frontend Design

Create or update `docs/ux/frontend-design.md` before implementation must make
product appearance or interaction decisions.

## Load and inspect

Read `.ezpowers/contracts/frontend-design-contract.md` when installed, or the
same contract in the plugin distribution's `docs/reference/` directory. It is
the source of truth for the artifact, state matrix, token/component policy,
accessibility, mock/prototype handling, and tool-conditional visual lanes.

Inspect manifests, routes, views, components, styles, tests, visual tooling,
and existing design evidence. Reuse the repository's established design system
and conventions.

## Decide and record

1. Propose 2-3 distinct design directions with concrete tradeoffs.
2. Ask for the selected direction or record that the user delegated it.
3. Apply the canonical contract to write the frontend design artifact.
4. Run the installed readiness detector in advisory mode when available.
5. Hand the artifact path and unresolved decisions to `spec`.

Do not implement product UI code. Do not require Storybook, Playwright
screenshots, visual diff, or another global executable unless project-local
evidence or an explicit prerequisite activates that lane. A normative
mock/prototype must retain its declared mapping and freshness rule.

Report `NEEDS_USER` when audience, surface, or design direction remains unknown
and the user has not delegated the choice.
