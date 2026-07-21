# Design Architecture Contract

This reference owns the `/design-architecture` artifact shape. It separates
project architecture and verification policy from feature-level specs.

Source contract: `docs/reference/reviewer-placement-contract.md` requires
`ezpowers:architecture-reviewer` before architecture completion.

## Required Outputs

Update or create these project docs:

- `docs/reference/architecture.md`
- `docs/reference/testing-methodology.md`
- `docs/reference/project-structure.md`
- `docs/product/ROADMAP.md`
- `docs/ux/README.md` when UI is present
- `docs/ux/frontend-design.md` when UI is present
- `docs/release/README.md` when packaging or deployment is in scope

## Decision Ledger

Every user answer, delegated choice, repo-inferred default, and architecture or
frontend design decision that affects later implementation must be recorded in
the relevant artifact's `## Decision Ledger` table:

| ID | Question/Trigger | Decision | Source | Artifacts Updated | Open Follow-up |
|----|------------------|----------|--------|-------------------|----------------|

`Source` is `user`, `repo`, `default`, or `delegated`. `/design-architecture`
must carry ledger entries into `docs/reference/architecture.md`,
`docs/reference/testing-methodology.md`, `docs/product/ROADMAP.md`, and
`docs/ux/frontend-design.md` when UI is present. ADRs remain reserved for
hard-to-reverse or surprising tradeoff decisions.

## Architecture Baseline

Capture:

- Project purpose and primary users.
- Backend, frontend, data, integration, and deployment boundaries.
- Frontend design direction, design-system source, token policy, component
  taxonomy, UX state coverage, responsive rules, accessibility target, and
  visual QA strategy when UI is present.
- Tool-conditional visual readiness lanes for mock/prototype artifacts,
  Storybook or equivalent component states, Playwright screenshot baselines,
  visual diff baselines, and screenshot/visual review loops when project-local
  tooling exists or the plan will add it.
- Module boundaries and ownership.
- Data flow and lifecycle.
- Quality budgets and operational constraints.
- ADR triggers and existing decisions.
- Known architecture risks and follow-up questions.

## Testing Methodology

Document the test strategy by surface:

- Unit, integration, API, e2e, UI, smoke, visual, accessibility, security,
  performance, data, and release checks.
- Required commands and where they run.
- Required test data or environment variables.
- UI adapter selection from `docs/reference/ui-verification-adapter-contract.md`.
- Frontend design readiness and visual QA selection from
  `docs/reference/frontend-design-contract.md`.
- Result from `scripts/frontend-visual-readiness.py --mode detect` when the
  repository includes that non-installing detector. Use `--frontend-root` for
  monorepo app roots.
- Fallback adapter and equivalence rationale when the strongest adapter cannot
  run in the project.

## Frontend Design

When UI is present, `/design-architecture` invokes the `frontend-design` skill
after repo evidence is read and before architecture completion. The skill must
offer 2-3 design directions, record the selected option or delegated choice,
and produce `docs/ux/frontend-design.md`. The architecture bundle is incomplete
until this artifact exists or the UI surface has an explicit exemption.
Full visual automation remains tool-conditional: Storybook or equivalent
component isolation, Playwright screenshots, visual diff, and mock/prototype
gates are mandatory only from project-local tooling evidence or explicit
prerequisite tasks. Playwright e2e-only evidence does not trigger the
screenshot/visual baseline lane.

## Project Structure

Document:

- Source roots.
- Test roots.
- Generated artifacts.
- Package/build/deploy outputs.
- Files that agents may modify and no-change boundaries.
- How new modules, routes, components, or migrations should be placed.

## Roadmap

Record current phase, near-term features, maintenance priorities, deployment
milestones, and known risks. Specs and maintenance work must update the roadmap
when scope or ordering changes.

## Web Research

Use web research only for current or framework-specific guidance that local
repo evidence cannot provide. Cite URLs and the date consulted in the testing
methodology or architecture note. Local project contracts still win over
general best practices.

## Phase State

`phases/index.json` should include:

```json
{
  "architecture": {
    "status": "complete",
    "artifact": "docs/reference/architecture.md",
    "completed_at": "<ISO 8601>"
  }
}
```

If `/design-architecture` changes verification policy after specs or plans
exist, mark affected later phases as needing review.
