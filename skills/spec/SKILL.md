---
name: spec
description: Use when settled decisions must be written as a project-local feature acceptance contract with traceable, machine-verifiable criteria. Not for interviewing an ambiguous request or implementing code.
disable-model-invocation: true
---

# Spec

Convert settled decisions into a feature acceptance contract. This is narrower
than general specification writing: `deep-interview` can clarify ambiguous
intent inside the current conversation; an explicitly invoked `spec` records
what this project must prove before a feature is complete.

## Load and inspect

Read `.ezpowers/contracts/spec-contract.md` and
`.ezpowers/contracts/verification-contract.md`; they are the source of truth
for artifact shape, managed markers, fields, identifiers, and validation. If
the local kit is absent, route to `setup`.

Read settled decisions from the current conversation, repository instructions,
the registered documentation graph when present, `CONTEXT.md`, relevant ADRs,
architecture and frontend-design artifacts, every applicable nearest
`DESIGN.md`, existing specs, public entry points, and tests. Treat local wiki
candidates as hints only and verify them
against repository sources. If a material product decision remains open, stop
and recommend an explicit `deep-interview` invocation rather than interviewing
inside `spec`. Return to `design-architecture` when implementation would
otherwise invent a boundary, data flow, lifecycle, deployment, or verification
decision.

## Write and validate

Create one feature spec under `docs/specs/`. Keep purpose, scope, settled
requirements, exclusions, risks, and design references in readable Markdown.
Add exactly one managed JSON block using the canonical spec contract. Every
criterion must be binary, observable, host-independent, and traceable to one
requirement. Mark real boundary-crossing behavior as integration evidence and
include failure criteria when rejection behavior is part of the requirement.
Every new spec records `design_context`: UI work names the broad frontend
artifact and all mapped `DESIGN.md` files; non-UI work records `required:
false` with a reason. Do not treat a legacy spec's missing field as a template
for new work.

Run:

```text
python .ezpowers/ezpowers.py validate --spec <spec-path> --json
```

Validation failure or an unresolved material decision is blocking. Report the
spec path, requirement-to-criterion mapping, integration criteria, exclusions,
design references, and remaining risks. Continue to `prepare-execute` only
with a valid spec.
