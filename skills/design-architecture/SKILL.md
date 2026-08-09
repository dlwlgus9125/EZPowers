---
name: design-architecture
description: Use when a project needs durable architecture, boundary, data-flow, deployment, or verification-design decisions before a feature spec is written. Not for implementing code or for general request clarification.
disable-model-invocation: true
---

# Design Architecture

Turn settled product decisions into project-specific architecture and
verification design. `deep-interview` resolves ambiguity; this skill records
technical decisions; `spec` owns feature acceptance.

## Load and inspect

Read `.ezpowers/contracts/design-architecture-contract.md` and
`.ezpowers/contracts/verification-contract.md`. For product-code module,
interface, dependency, or seam decisions, also read
`.ezpowers/contracts/engineering-practices-contract.md` and apply the focused
`codebase-design` discipline. Read
`.ezpowers/contracts/documentation-contract.md` when `.ezpowers/docs.json`
exists. If the local kit is absent, route to `setup`. Then inspect repository
instructions, the documentation graph, `CONTEXT.md`, relevant ADRs, manifests,
entry points, public interfaces, CI/deploy files, tests, existing architecture
or frontend-design artifacts, and every applicable nearest `DESIGN.md`.

Ask one question at a time only when repository evidence cannot settle a
consequential choice. Use `deep-interview` when the uncertainty is a product or
domain decision rather than an architecture detail.

## Design

Apply the canonical contract to record only the boundaries, ownership, data
flow, lifecycle, deployment, compatibility, and verification choices this
project actually needs. Prefer existing project conventions. For UI work,
delegate design direction to `frontend-design` and carry its
`docs/ux/frontend-design.md` artifact path, mapped `DESIGN.md` paths, profile
IDs, implementation mappings, and oracle forward. Treat the pair as one design
context; architecture does not redefine visual tokens.

Use `codebase-design` only to deepen a focused product-code boundary already in
scope. This skill remains the owner of durable project architecture artifacts.
Do not invoke the broad `improve-codebase-architecture` scan implicitly.

Respect documentation ownership. Update an EZPowers-owned architecture file
through a staged docs preview/apply bundle; do not hand-edit it or silently
adopt an external document. Keep external canonical documents user-owned.

Do not prescribe model selection, subagent placement, worktrees, sandbox
settings, reviewer routing, or general retries; the active host owns those
execution choices.

## Finish

Confirm that executable behavior has a real entry-point check and that
integration/user-visible claims have an appropriate project-local oracle. If a
required adapter is absent, record it as a prerequisite rather than weakening
the claim.

Report changed artifact paths, settled decisions and evidence sources, exact
verification design, and remaining risks. Continue to `spec` only when the
architecture required by the feature is settled.
