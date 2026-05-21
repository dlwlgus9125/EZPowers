# Harness Kit Contract

This contract keeps `/setup` and `/reset_setup` deterministic. The plugin owns
the bundled kit; setup only installs and verifies it inside the target project.

## Install Root

Install to:

```text
.harness/ezpowers/
```

Required files:

- `manifest.json`
- `skills/README.md`
- `contracts/README.md`
- `ledger.json`

`ledger.json` is generated in the target project and records installed file
paths, SHA-256 hashes, source plugin version, install timestamp, and migration
notes.

## No Synthesis Rule

Setup must never compose `SKILL.md` bodies from prompt text, web research, or
partial command docs. It may only copy bundled files listed by the manifest.
If a skill, contract, or helper is missing from the bundle, setup stops and
reports the plugin kit as incomplete.

This prevents setup from installing a diluted or mixed version of the harness.

## Verification

Before installing:

1. Read `harness-kit/v2.0.0/manifest.json`.
2. Confirm `no_synthesis` is `true`.
3. Confirm every listed source file exists.
4. Compute SHA-256 for each bundled file.

After installing:

1. Recompute SHA-256 for each installed file.
2. Write `.harness/ezpowers/ledger.json`.
3. Fail setup if any hash differs from the copied source.

## Reset Setup

`/reset_setup` repeats installation with the current manifest and preserves
human-authored project docs. If the manifest version changes, record the prior
version and migrated fields in the ledger.

Breaking migrations must mark affected phases as needing review rather than
silently keeping stale architecture, spec, or plan state.

## Public Commands

The v2 public chain is:

```text
/setup -> /design_architecture -> /spec -> /prepare_execute -> /choice_execute
```

Lifecycle commands:

- `/maintain`
- `/deploy`
- `/reset_setup`

Internal adapters:

- `docs/reference/pipeline-audit-contract.md`
- `docs/reference/strict-execution-adapter.md`

Old public commands `/brainstorm`, `/plan`, `/choiceexecutor`,
`/executeharness`, and `/pipeline-audit` are not aliases in v2.
