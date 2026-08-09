---
name: frontend-design
description: Use when frontend, UI, UX, design system, screen structure, component taxonomy, design tokens, responsive behavior, accessibility, or visual QA decisions must be settled before implementation. Not for directly coding UI.
---

# Frontend Design

Settle the UI contract before implementation. Produce a broad frontend artifact
and, for each independent visual brand, a machine-readable `DESIGN.md`.
Do not implement product UI code.

## Ground the work

Read repository instructions. When the project kit is installed, read
`.ezpowers/contracts/frontend-design-contract.md` and
`.ezpowers/contracts/design-md-profile.json`; otherwise read
`docs/reference/frontend-design-contract.md` and
`docs/reference/design-md-profile.json` from the plugin distribution. Then
inspect existing frontend artifacts, the nearest mapped `DESIGN.md`,
implementation tokens/components, routes, assets, and tests. When
`.ezpowers/docs.json` exists, also read the documentation contract and respect
managed ownership. Repository evidence overrides mockups and conversation
memory.

Ask one question at a time only when a consequential product choice cannot be
settled from evidence. Propose 2-3 distinct design directions when visual
direction is open; compare hierarchy, density, interaction, responsive
behavior, accessibility, and implementation cost, then recommend one.

## Produce the paired contract

Keep `docs/ux/frontend-design.md` responsible for audience, information
architecture, state matrix, responsive and input behavior, accessibility,
assets, component taxonomy, and visual-QA oracles. Add its managed
`design_systems` block.

Keep each mapped `DESIGN.md` responsible for normative tokens and reusable
component styling. Prefer one root `DESIGN.md`; add a nearer file only for an
independently branded frontend root. Nearest mapping wins and mappings never
merge. Code must be aligned to `DESIGN.md`; do not weaken the document merely
to bless accidental implementation drift.

Selectively apply the installed Google-derived alpha profile. Preserve useful
unknown prose, but use its token groups, section order, references, lint, and
diff review. Do not add export/code-generation dependencies. An existing
unmanaged or older-profile document is migrated only through explicit staged
preview, approval, and backup rules.

Stage both artifacts through the documentation workflow when it is configured.
Treat mock/prototype artifacts as reference-only unless their mapping and
freshness are explicit. Storybook and Playwright/visual-diff lanes become hard
only from project-local tooling or a named prerequisite.
Validate with:

```text
python .ezpowers/tools/design-md.py lint --file <DESIGN.md> --profile <profile> --json
python .ezpowers/tools/design-md.py check-project --project-root . --frontend-design <artifact> --json
python .ezpowers/tools/frontend-visual-readiness.py --project-root . --design-artifact <artifact> --mode check --json
```

Use `design-md.py diff` for an existing design-system change. If the pinned
official CLI is already installed locally, retain its `npx --no-install`
cross-check; never install or fetch it during this workflow.

## Handoff

Report both artifact paths, profile IDs, implementation mappings, selected
direction, validation output, tool-conditional visual lanes, and remaining
risks. Hand `spec` a `design_context`: UI work names the frontend artifact and
all applicable `DESIGN.md` files; non-UI work records `required: false` and a
reason. Continue only when the user asks or the active workflow already owns
that transition.
