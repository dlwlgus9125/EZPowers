# 0006. Keep architecture artifacts in the existing workflow

## Status

Accepted on 2026-08-09.

## Context

Architecture documentation must remain discoverable to developers and tools
that do not use EZPowers, while structural maintenance must not degrade into a
tail-end documentation task. A separate architecture manifest, semantic
checker, review state, and CI patcher could make freshness more mechanical,
but would duplicate the existing documentation graph, feature contracts, and
approval state without proving that the content still matches the system.

## Decision

Use the project's existing canonical architecture document, or root
`ARCHITECTURE.md` when none exists. Keep it tool-neutral Markdown with
applicable C4/arc42 concepts, real code mappings, decisions, risks,
verification strategy, and explicit maintenance triggers.

`design-architecture` owns semantic creation and updates before `spec`.
Documentation preview/apply/lint owns only safe persistence, ownership, links,
and managed-byte integrity. Specs record architecture impact in readable
Markdown. An explicit harness-chain freezes the affected architecture files
only when its `design_architecture` stage was selected.

Do not add a second architecture manifest, standalone freshness CLI, review
state machine, generic CI patcher, or new spec/plan JSON context for this
feature.

## Consequences

- Standard Markdown paths and navigation remain usable without EZPowers.
- Structural changes carry architecture forward before implementation; work
  with no structural impact does not churn the document.
- Hash checks detect drift but intentionally make no semantic-freshness claim.
- Stronger automated architecture conformance remains a future feature only
  if concrete failures justify project-specific observable checks.
