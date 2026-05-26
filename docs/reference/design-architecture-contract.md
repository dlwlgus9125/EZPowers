# Design Architecture Contract

This reference owns the `/design_architecture` artifact shape. It separates
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
- `docs/release/README.md` when packaging or deployment is in scope

## Architecture Baseline

Capture:

- Project purpose and primary users.
- Backend, frontend, data, integration, and deployment boundaries.
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
- Fallback adapter and equivalence rationale when the strongest adapter cannot
  run in the project.

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

If `/design_architecture` changes verification policy after specs or plans
exist, mark affected later phases as needing review.
