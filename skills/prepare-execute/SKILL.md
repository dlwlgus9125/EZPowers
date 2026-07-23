---
name: prepare-execute
description: Use when a valid EZPowers feature spec must be mapped into an ordered implementation plan with exact project-local checks and complete criterion coverage. Not for implementing the plan.
disable-model-invocation: true
---

# Prepare Execute

Map a valid acceptance contract to a small implementation plan. The plan owns
dependencies, criterion coverage, and exact checks; the active host owns how it
edits, delegates, isolates, reviews, and retries the work.

## Load and inspect

Read `.ezpowers/contracts/plan-contract.md` and
`.ezpowers/contracts/verification-contract.md`; they are the source of truth
for the managed schema and check rules. Read the selected spec, architecture
and frontend-design artifacts, repository instructions, the documentation
graph when present, source, tests, CI commands, and `.ezpowers/config.json`.

Validate the spec first with the exact command in the plan contract. Return to
`spec` when a criterion is ambiguous or cannot be automated without weakening
its observable claim.

## Plan and validate

Create one plan under `docs/plans/`. Explain ordered vertical slices,
dependencies, expected files, constraints, prerequisites, non-goals, and risks
in Markdown. Add exactly one managed JSON block using the canonical plan
contract. Map every criterion exactly once and bind it to real named or inline
project checks. Preserve frontend, accessibility, integration, and visual
oracles; missing tooling becomes an explicit prerequisite.

Run:

```text
python .ezpowers/ezpowers.py validate --plan <plan-path> --json
```

Missing, duplicate, unknown, or weakened coverage is blocking. Report the plan
path, task order, exact criterion coverage, configured and plan-local checks,
including the required `ezpowers.docs` check when documentation is ready, and
unresolved prerequisites. Continue to `execute` only with a valid plan.
