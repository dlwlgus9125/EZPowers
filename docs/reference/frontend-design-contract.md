# Frontend Design Contract

This contract makes frontend design readiness a first-class gate before UI
implementation. It complements `docs/reference/app-delivery-contract.md` and
the UI Adapter Evidence section of `docs/reference/verification-contract.md`.

## Required Artifact

When `.harness/config.json` declares a UI surface, the project must contain:

```text
docs/ux/frontend-design.md
```

The artifact records decisions that implementation agents must not invent.
Each decision must also be reflected in the project-level Decision Ledger so
`/spec` and `/prepare-execute` can carry it forward by ID.

Required sections:

- Product surface and audience.
- Decision Ledger with `ID`, `Question/Trigger`, `Decision`, `Source`,
  `Artifacts Updated`, and `Open Follow-up`.
- Design direction decision: 2-3 options, selected option or hybrid, rejected
  tradeoffs, and user confirmation or delegated choice.
- Screen inventory.
- Information architecture and navigation.
- UX state matrix for loading, empty, error, permission, offline, validation,
  cancellation, success, and long-running states when applicable.
- Design system source.
- Token policy.
- Component taxonomy.
- Responsive rules.
- Accessibility target.
- Asset policy.
- Visual QA strategy.
- Mock/prototype artifact handling: path or link, fidelity, owner,
  normative/reference-only status, token/component mapping, and freshness rule
  when mockups or prototypes influence implementation.
- Visual readiness lanes: Storybook/component isolation, Playwright or
  equivalent screenshots, visual diff baselines, and screenshot/visual review
  loop status when the project has or plans those tools.

If a section is not applicable, state `not applicable` and the reason.

## Config Fields

`/setup` records frontend design readiness under
`.harness/config.json` `app_delivery.frontend`:

```json
{
  "design_readiness_required": true,
  "design_artifact": "docs/ux/frontend-design.md",
  "token_source": "",
  "component_inventory": "",
  "visual_qa": "",
  "mock_prototype_artifacts": "",
  "visual_baseline": ""
}
```

Rules:

- `design_readiness_required` is `true` for web, mobile, desktop, TUI, or any
  declared user-facing UI.
- Figma or another design file may be recorded as a design source, but it is
  optional. When absent, repo-owned tokens and components are the default.
- Setup creates slots and config only. It must not synthesize a design brief.

## V2 Visual Readiness Gate

`frontend-design` uses this interaction model:

1. Read repo evidence before asking.
2. Offer 2-3 distinct design directions with tradeoffs.
3. Record the user's selected direction or hybrid. If the user delegates the
   choice, record that delegation.
4. Produce `docs/ux/frontend-design.md`.
5. Hand off unresolved questions to `/spec`.

Full visual automation is tool-conditional. Storybook or equivalent component
isolation, Playwright screenshot baselines, visual diff tooling, or generated
mock/prototype artifacts are required only when already available or when the
plan adds them as prerequisite tasks.

Tool-conditional means project-local tooling evidence, not global PATH availability.
Evidence includes repo config files, package scripts/dependencies, checked-in
Storybook or equivalent component-isolation configuration, Playwright
screenshot usage, visual regression config, workspace package evidence, or
explicit plan tasks that install or configure those tools.

Playwright availability alone is not enough to require the screenshot/visual
baseline lane. The lane becomes required when project evidence or the plan
mentions screenshot-specific Playwright use, such as `toHaveScreenshot`,
snapshot baselines, screenshot review, or visual snapshots. Ordinary Playwright
e2e is handled by the UI Adapter Evidence section of the verification contract.

When a mock or prototype artifact is normative, the artifact must state how it
maps to tokens and components plus a freshness rule. Reference-only artifacts
may be recorded as inspiration, but implementation must follow the repo-owned
frontend design artifact.

When Storybook or an equivalent component isolation tool is available or
planned, the plan must include component state/story coverage before screen
integration. When Playwright screenshots, visual diff tooling, or an equivalent
browser visual adapter is available or planned, the plan must include a
screenshot/visual baseline location and a screenshot/visual review loop.
Equivalent tooling includes Storybook-compatible or component-isolation tools
such as Ladle or Histoire, and visual tooling such as Chromatic, Percy, Loki,
reg-suit, BackstopJS, Argos, Applitools, jest-image-snapshot, pixelmatch, or
lost-pixel when configured in the project.

`scripts/frontend-visual-readiness.py` provides the non-installing detector for
these lanes. It scans the project root plus workspace frontend roots, accepts
`--frontend-root` for explicit monorepo roots, emits `schema_version`,
`warnings`, `errors`, `tools`, and `lanes` in JSON output, and never installs
tools or generates screenshots. `--mode detect` is advisory and always exits
0; use `--mode check` for pipeline gating.

## Pipeline Integration

- `/setup`: detect UI presence, create `docs/ux/`, create the
  `docs/ux/frontend-design.md` slot, and populate frontend design config
  fields.
- `/design-architecture`: invoke `frontend-design` when UI is present and
  record the selected design direction, artifact path, QA strategy, and
  tool-conditional visual readiness lanes.
- `/spec`: App Experience And Delivery Baseline must reference the frontend
  design artifact, design system source, token policy, component taxonomy,
  state matrix, responsive rules, accessibility target, and visual QA strategy.
- `/prepare-execute`: UI plans that need a new design system sequence work as
  `tokens -> primitives -> component states/stories -> screens -> e2e/visual`.
- `internal pipeline audit`: D9 fails UI work when frontend design readiness is
  missing or when implementation agents would still need to invent design
  structure.

## Review Rules

`ezpowers:frontend-experience-reviewer` checks the artifact, spec, plan, and
config when present.

FAIL when:

- UI is present but `docs/ux/frontend-design.md` is missing.
- The design direction decision is missing for new or redesigned UI.
- Design system source, token policy, component taxonomy, UX state matrix,
  responsive rules, accessibility target, or visual QA strategy is empty.
- The plan starts screen implementation before tokens, primitives, and
  component states when no suitable design system already exists.
- Storybook/component state-story coverage is missing when Storybook or an
  equivalent component isolation tool exists or is planned.
- Screenshot/visual baseline and screenshot/visual review loop coverage is
  missing when Playwright screenshots, visual diff tooling, or an equivalent
  visual adapter exists or is planned.
- A normative mock/prototype artifact lacks token/component mapping or a
  freshness rule.
- Visual or accessibility evidence is advisory-only for an acceptance criterion
  that depends on visual design or accessibility.
