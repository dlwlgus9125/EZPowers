---
name: setup
description: Use when the user explicitly asks to initialize, install, repair, or refresh EZPowers project-local workflow configuration and verification tooling.
disable-model-invocation: true
---

# Setup

Install a self-contained project kit and record the target project's real
completion checks. Do not create product code, select host models, configure a
global HUD, or add an external executor.

## Load the contract

Read `setup-contract.md` and `verification-contract.md` from
`.ezpowers/contracts/` when installed. Before the first install, resolve the
same files from the plugin distribution's `docs/reference/` directory. Those
contracts own the config schema, allowed check kinds, migration policy,
managed-file ownership, and hook shape; do not copy or reinterpret their rules.

## Inspect

Read repository instructions, manifests, scripts, CI files, tests, and any
existing `.ezpowers/config.json`. Require the target path to equal the Git
worktree root. Before invoking the runtime, run `python --version` and require
Python 3.10 or newer; if it is unavailable, stop with that prerequisite instead
of attempting installation. Infer commands only from executable repository
evidence. Ask one question at a time for a required command or completion
condition that cannot be established from the repository.

## Install or refresh

For a new installation, run the plugin copy:

```text
python <plugin-root>/scripts/ezpowers.py install --project-root <project>
```

When an installed project must be upgraded from a newer plugin distribution,
run the plugin copy explicitly with refresh:

```text
python <plugin-root>/scripts/ezpowers.py install --project-root <project> --refresh
```

For a same-version repair from the already installed local kit, run:

```text
python .ezpowers/ezpowers.py install --project-root <project> --refresh
```

Add `--enable-hooks claude`, `codex`, or `both` only after explicit user
approval. The default is `none`.

Update `.ezpowers/config.json` with only confirmed project checks, using the
canonical exact-argv schema. Preserve unknown user fields. Keep legacy source
files in place; report migrated commands and every ignored execution, model,
reviewer, retry, phase, HUD, or external-path setting. Never overwrite a
managed file after the installer reports a conflict.

## Verify and report

Run the installed runtime:

```text
python .ezpowers/ezpowers.py status --json
```

Validate any existing spec or plan using the exact commands in the contracts.
Treat Git-root mismatch, missing runtime, manifest or ledger hash drift,
host-copy drift, invalid config, unsupported Python, and managed-file conflict
as setup failure.

Report installed and preserved paths, configured/required checks, migration
warnings, hook choice, ledger path, and unresolved completion criteria. Use
`deep-interview` only when decisions remain ambiguous; otherwise continue to
`frontend-design` for unresolved product-surface decisions, then
`design-architecture` or `spec` as needed.
