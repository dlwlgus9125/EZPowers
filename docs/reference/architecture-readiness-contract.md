# Architecture Readiness Contract

This document is the canonical contract for deciding whether a spec is ready
for planning without forcing implementation agents to invent architecture.

## Required Spec Interface

Every spec produced by `/brainstorm` must contain:

- Architecture Baseline
- ASR Ledger
- Option Matrix
- Lifecycle And Operations
- Quality Budgets
- Decision Log
- Extracted Requirements

Every requirement section must include an `ASR:` field with existing ASR IDs or
`none`.

## Architecture Baseline

The Architecture Baseline states the selected approach, existing constraints,
and boundary map. The boundary map must name modules, public interfaces,
allowed dependencies, forbidden dependencies, and data ownership when relevant.

The selected approach must be traceable to the Option Matrix.

## ASR Ledger

Each ASR row must include:

- ASR ID
- quality attribute
- measurable target or `none declared`
- design impact
- verification command or review check

When a target is `none declared`, the spec must state the risk of having no
budget. An empty target is not allowed.

ASRs must affect structure, lifecycle, performance, reliability, security,
compatibility, cost, or operations. Ordinary functional requirements should not
be promoted to ASRs unless they shape the architecture.

## Option Matrix

The Option Matrix must compare at least two architecture options and mark
exactly one selected option. Each option must include a tradeoff, not only a
preference.

Rejected options should explain the load-bearing reason they were rejected.

## Lifecycle And Operations

The Lifecycle And Operations section must cover:

- lifecycle stage
- startup and shutdown
- deployment or runtime
- migration and compatibility
- observability
- recovery
- ownership

Fields may say `none declared` only when the risk is stated.

## Quality Budgets

The Quality Budgets section must cover:

- performance
- reliability
- security
- cost
- maintainability

Each budget must be a metric, rule, or `none declared` plus risk. Empty values
block planning.

## Decision Log And ADRs

Use the ADR policy in `docs/decisions/README.md`.

Write an ADR only when all three conditions are true:

- hard to reverse
- surprising without context
- real tradeoff

If the Decision Log says `ADR required: yes`, it must reference ADR files under
`docs/decisions/`, and those files must exist.

If a hard-to-reverse, surprising, or high-tradeoff decision appears in the spec
but the Decision Log says `ADR required: no`, architecture review must fail.

## Carry-Forward To Plan And Review

Plans must carry referenced ASRs into task `ASR:` fields, the Coverage Matrix,
or Structural Invariants.

Structural Invariants should be used when the ASR is best enforced as a
verifiable architecture rule rather than a feature task.

Final code review must cite code, tests, invariant results, or verification
output that satisfies each referenced ASR. Missing ASR evidence has the same
blocking effect as missing requirement evidence.
