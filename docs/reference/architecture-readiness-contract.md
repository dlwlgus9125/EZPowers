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
- App Experience And Delivery Baseline when the project has an app, API, or
  executable artifact
- Decision Log
- Extracted Requirements

Every requirement section must include an `ASR:` field with existing ASR IDs or
`none`.

## Architecture Baseline

The Architecture Baseline states the selected approach, existing constraints,
and boundary map. The boundary map must name modules, public interfaces,
allowed dependencies, forbidden dependencies, and data ownership when relevant.

The selected approach must be traceable to the Option Matrix.

## Architecture Vocabulary

Use these terms consistently during architecture review:

- **Module:** any unit with an interface and an implementation.
- **Interface:** everything a caller must know to use a module, including
  invariants, ordering, errors, and configuration.
- **Depth:** leverage behind the interface. A deep module hides meaningful
  behavior behind a small interface; a shallow module mostly passes complexity
  through to callers.
- **Adapter:** a concrete implementation selected at a module boundary.
- **Locality:** how much change, bug fixing, and knowledge stay concentrated in
  one module.
- **Deletion test:** if deleting a module only removes pass-through code, it is
  shallow; if deleting it spreads complexity across callers, it is earning its
  interface.

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

## Initialization Order

For executable artifacts with 2+ modules that have startup dependencies, the
spec must declare initialization order. Each entry specifies:

- Module name
- Prerequisite module (what must be ready first)
- Readiness signal (e.g., "DB connection pool open", "config loaded")

Omit for single-module projects, stateless libraries, or docs-only artifacts.
Missing initialization order for executable artifacts with runtime dependencies
is a FAIL in pipeline audit D7.

## Quality Budgets

The Quality Budgets section must cover:

- performance
- reliability
- security
- cost
- maintainability

Each budget must be a metric, rule, or `none declared` plus risk. Empty values
block planning.

### Budget Verification Commands

Each Quality Budget entry MAY include a `verify_command` field specifying how to
measure the metric at execution time.

Format:

| Category | Metric | Rule | Verify command |
|----------|--------|------|----------------|
| performance | API response p95 < 200ms | hard ceiling | `ab -n 100 -c 10 http://localhost:3000/api/health \| grep 'Percentage.*95%'` |
| reliability | zero crash in 60s stress | hard floor | `timeout 60 node dist/server.js && echo PASS` |
| security | no Critical/High SAST | hard floor | `semgrep --config=auto src/ --severity=ERROR --json` |
| cost | bundle < 500KB | hard ceiling | `du -sb dist/bundle.js \| awk '{print $1}'` |
| maintainability | cyclomatic < 15 per fn | soft ceiling | `npx complexity-report --format=json src/` |

Rules:

- `verify_command` is optional. If omitted, the budget is documentation-only
  (no runtime gate).
- If present, the command must produce parseable output (exit code, numeric
  value, or JSON).
- `hard ceiling/floor` budgets are **blocking** (FAIL at the Quality Budget
  Verification Gate). `soft ceiling/floor` budgets are **advisory** (WARN).
- The harness executes `verify_command` during the Quality Budget Verification
  Gate in `/choiceexecutor` Section 12a (after Final Code Review, before
  Completion gates).

## App Delivery Readiness

Specs with `app_delivery.surface_kind` other than `docs` or `library` must
include App Experience And Delivery Baseline. The baseline must identify the
user-facing surfaces, frontend/backend contracts, package artifact, deployment
target, QA strategy, and release verification expected by
`docs/reference/app-delivery-contract.md`. Missing baseline details are
architecture gaps because implementers would have to invent product surface,
delivery, or verification policy during coding.

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

Plans must also carry the App Experience And Delivery Baseline into an
Experience/Delivery Matrix when the baseline exists.

Structural Invariants should be used when the ASR is best enforced as a
verifiable architecture rule rather than a feature task.

Final code review must cite code, tests, invariant results, or verification
output that satisfies each referenced ASR. Missing ASR evidence has the same
blocking effect as missing requirement evidence.
