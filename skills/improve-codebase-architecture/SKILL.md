---
name: improve-codebase-architecture
description: Explicitly scan existing product code for architecture deepening opportunities, render an evidence-backed offline HTML report, and explore one user-selected refactor. Use for broad maintenance analysis of shallow modules, scattered complexity, leaky seams, and hard-to-test code; not for new-system architecture, workflow-harness audits, or direct implementation.
disable-model-invocation: true
---

# Improve Codebase Architecture

Scan existing product code for high-value deepening opportunities without
changing the repository.

## Load and scope

Read `.ezpowers/contracts/engineering-practices-contract.md` and use the
installed `.ezpowers/tools/architecture-review-report.py`. When the project
kit is absent, read the matching contract and tool from the EZPowers plugin
distribution.

Read repository instructions, Git status and history, `CONTEXT.md` when
present, applicable ADRs, current architecture documents, affected code, and
tests. Preserve user changes.

Use a user-named module, subsystem, or pain point as the scan boundary. When
none is named, use recent Git history to identify recurring product-code
hotspots before widening the scan. Do not use this skill to audit EZPowers
workflow/harness authority; that requires direct tracing of installed files,
runtime callers, evidence, and host capabilities.

## Find candidates

Apply the `codebase-design` vocabulary and deletion test. Look for scattered
domain behavior, interfaces nearly as complex as implementations, pass-through
modules, false seams with one adapter, coupling that leaks into callers, and
behavior that cannot be tested through an honest interface.

Keep 1-8 evidence-backed candidates. For each one record:

- existing repository-relative files and line-specific findings;
- the current problem and proposed deepening;
- locality, leverage, and test-surface benefits;
- a `strong`, `worth_exploring`, or `speculative` recommendation;
- before and after node/edge diagrams;
- compatibility, migration, and ADR conflicts.

## Render the report

Write the renderer input JSON to an OS temporary path, then run:

```text
python .ezpowers/tools/architecture-review-report.py
  --project-root <project-root>
  --input <temporary-json>
  --open
  --json
```

Use the exact input and safety contract documented in
`engineering-practices-contract.md`. Do not hand-author HTML, load a CDN, write
the report into the repository, or overwrite an existing report. If browser
opening fails, return the absolute generated path and warning. If validation
or rendering fails, correct the structured input and rerun it; do not claim
the scan completed without a valid receipt.

Report the scan scope, Git revision and dirty state, top recommendation,
candidate count, report path, SHA-256, and renderer warnings.

## Explore one candidate

Ask which candidate the user wants to explore. After selection, apply the
`codebase-design` discipline to compare interfaces and seams, then return a
decision-ready refactor brief in the conversation.

Do not implement the refactor or automatically edit `CONTEXT.md`, ADRs,
architecture documents, specs, or plans. Durable boundary changes belong to
`design-architecture`; implementation continues only through an independently
authorized host-native plan or request.
