---
name: improve-codebase-architecture
description: Explicitly scan existing product code for evidence-backed deep-module opportunities, render a safe offline report, and explore one user-selected refactor without implementing it. Use for broad maintenance discovery of shallow modules, scattered policy, leaky seams, repeated orchestration, and hard-to-test behavior; not for new-system architecture, workflow-harness audits, or direct refactoring.
disable-model-invocation: true
---

# Improve Codebase Architecture

Find high-value product-code deepening opportunities without changing the
repository.

## Ground and freeze the scan

Resolve `<skill-root>` as the directory containing this `SKILL.md`. Read
`<skill-root>/references/report-contract.md` and use
`<skill-root>/scripts/render-report.py`. Verify both exist before scanning;
never fetch an upstream file at runtime.

Read repository instructions, the exact initial Git status, relevant history,
`CONTEXT.md` when present, applicable ADRs, architecture documents, product
code, callers, and tests. Treat documentation as context, not automatically as
an affected product file. Do not run tests, builds, formatters, or generators
during this advisory scan unless the user explicitly requests them; inspection
must not create caches or other workspace artifacts.

Use a user-named module, subsystem, or pain point as the boundary. Do not widen
a user-named scope. With no named scope, use recurring recent product-code
changes to choose a hotspot, state why, and widen only when history has no
coherent hotspot. Do not audit EZPowers workflow or harness authority with
this skill.

## Find and rank candidates

Apply the deletion test and the Module, Interface, Implementation, Depth, Seam,
Adapter, Leverage, and Locality vocabulary. Look organically for scattered
domain behavior, repeated ordering policy, interfaces nearly as complex as
implementations, pass-through modules, one-adapter false seams, caller leakage,
and behavior that cannot be tested through an honest interface.

Keep only 1–8 candidates supported by exact existing file-and-line evidence.
Every affected product or test file needs evidence. Mark glossary, architecture,
and ADR findings separately as context or decision evidence. Record the current
problem, responsibility-level deepening, locality and leverage, surviving test
surface, compatibility, migration, ADR status, recommendation strength, and
semantically styled before/after graphs.

Do not propose interfaces during the scan; selection must precede interface
design. Do not invent a candidate to satisfy the report schema. If the bounded
scope has no evidence-backed candidate, report that result and stop without a
report.

## Render and present

Write schema-version-2 JSON to an OS temporary path and run:

```text
python <skill-root>/scripts/render-report.py
  --project-root <project-root>
  --input <temporary-json>
  --open
  --json
```

Correct invalid structured input and rerun; never hand-author HTML, use a CDN,
write the report inside the repository, overwrite a report, or claim success
without a valid receipt. Delete the temporary input JSON after a successful
render and also on terminal failure. Preserve the generated HTML for the user.

Confirm the final Git status exactly matches the initial status. If this scan
changed the workspace, stop and report the drift without deleting unknown
files. Report scope and its basis, revision and dirty state, top recommendation
and rationale, candidate count, report path, report/input/source SHA-256 values,
source file count, and warnings.

Ask exactly one question at a time. At this stage ask only which candidate the
user wants to explore, then wait.

## Explore the selected candidate

After selection, inspect missing facts and ask one consequential constraint
question at a time rather than inventing a decision. When the user has answered
or delegated the choices, compare at least two materially different Interface
and Seam options. Do not vary only names.

Return **Refactor brief** with the selected candidate and evidence, settled
constraints, interface options and tradeoffs, recommendation, compatibility
and migration boundary, surviving tests, and unresolved risks.

Do not implement the refactor or automatically edit product code, `CONTEXT.md`,
ADRs, architecture documents, specs, or plans. Durable project-boundary changes
remain separate architecture work; implementation requires independent user
authority.
