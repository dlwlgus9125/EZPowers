---
name: setup
description: Use when the user explicitly asks to initialize, install, repair, refresh, or bootstrap repository documentation with EZPowers project-local workflow tooling.
disable-model-invocation: true
---

# Setup

Install a self-contained project kit, record the target project's real
completion checks, and optionally bootstrap a repository-evidenced
documentation graph. Do not create product code, select host models, configure
a global HUD, or add an external executor.

## Load the contract

Read `setup-contract.md`, `documentation-contract.md`, and
`verification-contract.md` from
`.ezpowers/contracts/` when installed. Before the first install, resolve the
same files from the plugin distribution's `docs/reference/` directory. Read
`wiki-contract.md` too when wiki storage or capture hooks are requested. Those
contracts own the config schema, allowed check kinds, pre-v5 retirement policy,
documentation graph, managed-file ownership, privacy boundary, and hook shape;
do not copy or reinterpret their rules.

## Inspect

Read repository instructions, existing Markdown, manifests, scripts, CI files,
tests, source boundaries, and any `.ezpowers/config.json` or
`.ezpowers/docs.json`. Require the target path to equal the Git worktree root.
Before invoking the runtime, run `python --version` and require Python 3.10 or
newer; if it is unavailable, stop with that prerequisite instead of attempting
installation. Infer commands and documentation claims only from repository
evidence. Ask one question at a time for a required command, authority choice,
or completion condition that cannot be established from the repository.

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
approval. Add `--enable-wiki-hooks claude`, `codex`, or `both` only after a
separate explicit approval for allowlisted SessionEnd capture. Both defaults
are `none`. Before configuring Claude features require Claude Code 2.1.217 or
newer; before configuring Codex features require Codex CLI 0.145.0 or newer.

Update `.ezpowers/config.json` with only confirmed project checks, using the
canonical exact-argv schema. Preserve unknown user fields. Pre-v5
`.harness/` and `phases/` content is retired: leave it byte-for-byte untouched,
do not inspect it as configuration, and do not translate it. Never overwrite a
managed file after the installer reports a conflict.

## Bootstrap or refresh documentation

Run this lane on first setup unless the user declines documentation, and when
the setup invocation includes `--refresh-docs`. This is a skill workflow flag;
do not pass it to the runtime's `install` command. Ordinary installer
`--refresh` repairs the kit and never rewrites project documentation.

Follow `documentation-contract.md`:

1. Map existing authority and repository evidence.
2. Select the smallest adaptive document set. Always include canonical
   `AGENTS.md`, exact `CLAUDE.md` import shim, and `docs/INDEX.md`; preserve
   existing user documents as external unless adoption is explicit.
3. Write the proposal only under `.ezpowers/staging/<unique-bundle>/`, including
   `bundle.json`.
4. Run `docs preview --json` and present every create, update, adoption,
   replacement, and conflict.
5. Apply with the returned preview hash only after the user has accepted any
   adoption or force-backed replacement. Never hand-edit `.ezpowers/docs.json`.
6. Run `docs lint --json`. A ready graph must register `ezpowers.docs` as a
   required project check.

Do not synthesize generic architecture or testing prose, generate one file per
directory, or modify specs/plans in this lane. Stage an incomplete graph or ask
one focused question when a required claim has no evidence.

## Verify and report

Run the installed runtime:

```text
python .ezpowers/ezpowers.py status --json
python .ezpowers/ezpowers.py docs status --json
```

Validate any existing spec or plan using the exact commands in the contracts.
Treat Git-root mismatch, missing runtime, manifest or ledger hash drift,
host-copy drift, invalid config, documentation lint failure, unsupported
Python, and managed-file conflict as setup failure.

Report installed and preserved paths, configured/required checks, host
prerequisite results, documentation graph status and backups, completion-hook
choice, wiki-capture choice, ledger path, and unresolved completion criteria. Use
`deep-interview` only when material ambiguity or a plausible consequential
blind spot remains. Otherwise continue to `frontend-design` for unresolved
product-surface decisions, then
`design-architecture` or `spec` as needed.
