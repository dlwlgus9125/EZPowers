---
name: prepare-execute
description: Use when a valid EZPowers feature spec must be mapped into a dependency-valid implementation plan with exact project-local checks and complete criterion coverage. Not for implementing the plan.
disable-model-invocation: true
---

# Prepare Execute

Map a valid acceptance contract to a small implementation plan. The plan owns
dependencies, criterion coverage, and exact checks; the active host owns how it
edits, delegates, isolates, reviews, and retries the work.

## Load and inspect

Read `.ezpowers/contracts/plan-contract.md` and
`.ezpowers/contracts/verification-contract.md`; they are the source of truth
for the managed schema and check rules. Read the selected spec and its
`design_context`, architecture and frontend-design artifacts, every applicable
nearest `DESIGN.md`, repository instructions, the documentation graph when
present, source, tests, CI commands, and `.ezpowers/config.json`.
When the plan changes product-code module boundaries, read
`.ezpowers/contracts/engineering-practices-contract.md` and preserve the
focused `codebase-design` seams and regression checks in the task mapping.

Validate the spec first with the exact command in the plan contract. Return to
`spec` when a criterion is ambiguous or cannot be automated without weakening
its observable claim. Return to `design-architecture` when planned work would
contradict the spec's architecture impact or introduce an unrecorded boundary.

## Plan and validate

Create one plan under `docs/plans/`. Explain ordered vertical slices,
dependencies, expected files, constraints, prerequisites, non-goals, and risks
in Markdown. Carry settled architecture paths and constraints as inputs; do
not add a tail-end task that merely makes documentation resemble the code.
Add exactly one managed JSON block using the canonical plan
contract. New software plans use schema v2 and new planning-profile plans use
schema v3. Both give every task an explicit `depends_on`
array, and declare check concurrency only when independence has reproducible
evidence; unproven checks remain unsafe barriers. Map every criterion exactly once and bind it to real named or inline
project checks. Preserve frontend, accessibility, integration, and visual
oracles; missing tooling becomes an explicit prerequisite. For UI work,
include code-to-DESIGN.md alignment and `check-project`. Reuse the exact
required `ezpowers.design` check when registered; otherwise add it as a
plan-local static check. Add the pinned official CLI command only when that
package is already installed locally, always with `npx --no-install`.

For the planning profile, declare every existing source artifact in `inputs`
and map every criterion to exactly one logical `deliverable`. A deliverable
may own multiple explicit file paths. Use `direct` review for directly
inspectable bytes and `inspected` review only with named project-owned,
read-only checks that expose the artifact through deterministic logs. Do not
add a format whitelist, directory/glob artifact, built-in spreadsheet parser,
or hidden external action. The project owns validator dependencies; EZPowers
owns their exact argv and resulting evidence.

Run:

```text
python .ezpowers/ezpowers.py validate --plan <plan-path> --json
python .ezpowers/ezpowers.py trace --plan <plan-path> --json
```

Missing, duplicate, unknown, cyclic, or weakened coverage is blocking. Report the plan
path, topological task waves, assurance-graph hash, exact criterion coverage, configured and plan-local checks,
including required `ezpowers.docs` and applicable `ezpowers.design` checks when
documentation is ready, and unresolved prerequisites. Continue to `execute`
only with a valid plan.
