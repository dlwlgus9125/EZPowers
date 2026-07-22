---
name: spec
description: Use when settled decisions must be written as a project-local feature acceptance contract with traceable, machine-verifiable criteria. Not for interviewing an ambiguous request or implementing code.
disable-model-invocation: true
---

# Spec

Convert settled decisions into a feature acceptance contract. This is narrower
than general specification writing: `deep-interview` settles ambiguous intent;
`spec` records what this project must prove before a feature is complete.

## Load and inspect

Read `.ezpowers/contracts/spec-contract.md` and
`.ezpowers/contracts/verification-contract.md`; they are the source of truth
for artifact shape, managed markers, fields, identifiers, and validation. If
the local kit is absent, route to `setup`.

Read repository instructions, `CONTEXT.md`, relevant ADRs, decision briefs
under `docs/interviews/`, architecture and frontend-design artifacts, existing
specs, public entry points, and tests. Use
`deep-interview` when a material product decision remains open. Return to
`design-architecture` when implementation would otherwise invent a boundary,
data flow, lifecycle, deployment, or verification decision.

## Write and validate

Create one feature spec under `docs/specs/`. Keep purpose, scope, settled
requirements, exclusions, risks, and design references in readable Markdown.
Add exactly one managed JSON block using the canonical spec contract. Every
criterion must be binary, observable, host-independent, and traceable to one
requirement. Mark real boundary-crossing behavior as integration evidence and
include failure criteria when rejection behavior is part of the requirement.

Run:

```text
python .ezpowers/ezpowers.py validate --spec <spec-path> --json
```

Validation failure or an unresolved material decision is blocking. Report the
spec path, requirement-to-criterion mapping, integration criteria, exclusions,
design references, and remaining risks. Continue to `prepare-execute` only
with a valid spec.
