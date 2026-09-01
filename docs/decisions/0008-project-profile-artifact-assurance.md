# ADR 0008: Project profile seam and artifact assurance

- Status: accepted
- Date: 2026-09-01
- Decision owners: EZPowers maintainers
- Related: `docs/reference/architecture.md`,
  `docs/decisions/0001-host-native-project-local-core.md`,
  `docs/decisions/0003-explicit-asymmetric-harness-chain.md`

## Context

The v5.7 workflow can author arbitrary Markdown but its completion path assumes
that the repository product is software: plan schemas contain only tasks and
checks, the assurance graph names code review, feature bundles decode every
frozen file as UTF-8, and chain rework language requires product-code edits.
Repositories whose product is a planning package may instead deliver Markdown,
workbooks, images, or mixed files and use project-owned scripts for structural
validation.

The change must not rename or reinterpret the existing software path. Its
graph hashes, review gate, exact commands, check scheduling, evidence, and
dual-host behavior are compatibility contracts.

## Decision

Add a project-level profile seam inside the existing self-contained runtime.
Config v1/v2 imply `software`; config v3 explicitly selects `software` or
`planning`, and planning plans use fail-closed schema v3. A small
`ProjectProfilePolicy` interface owns profile-specific validation, assurance
nodes, primary review gate, rubric, and rework vocabulary. The software
adapter returns the existing behavior unchanged. The planning adapter adds
byte-hashed named inputs, logical multi-file deliverables, direct or
project-owned inspected review, and a bound per-deliverable artifact-review
receipt.

Both adapters share the same subprocess scheduler, exact-argv contract,
workspace checks, immutable logs, evidence and certificate store, resume
state, hard limits, and host adapters. EZPowers does not parse business file
formats or install validators. The project owns validator commands and
dependencies; the runtime owns their exact invocation, output evidence,
declared-file hashes, freshness, and chain gates.

## Considered options

- A separate planning runtime would isolate vocabulary but duplicate the
  scheduler, evidence, chain, and host-hook cores and allow their verdicts to
  drift.
- Renaming the whole runtime to generic terminology would reduce visible
  special cases but change existing graph bytes, gate IDs, errors, and tests.
- Optional plan-v2 fields would be additive in the new runtime, but v5.7 would
  silently ignore them and could certify a planning plan as software.

## Consequences

Planning repositories gain ordinary and unattended evidence-gated completion
without a new executor. Older runtimes fail closed on schema v3. The runtime
and tests acquire profile branches and planning-specific receipt schema, but
the execution hot path stays shared and existing software fixtures remain
byte-compatible. Directories, globs, built-in spreadsheet/Markdown validators,
external business actions, and per-plan profile overrides remain outside the
boundary.
