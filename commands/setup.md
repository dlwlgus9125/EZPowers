---
description: Initialize project harness with config and steering docs
allowed-tools: [Bash, Read, Write, Glob, AskUserQuestion]
---

# /setup - Project Harness Initialization

## Purpose

Initialize an EZPowers harness in the target project. Create configuration,
steering docs, phase state, and reference doc slots. Do not write product code.

## Read

- `docs/reference/mattpocock-harness-adapter.md`
- `docs/reference/setup-contract.md`
- `docs/reference/domain-language.md`
- `docs/reference/verification-contract.md`
- Target repo root listing, manifests, source directories, `AGENTS.md`, `CLAUDE.md`, `CONTEXT.md`
- Existing `.harness/config.json`, `phases/index.json`, and `docs/` when present

## Rules

- Read repo evidence first. Ask only for values that cannot be inferred.
- Ask one question at a time; prefer concrete choices.
- If `.harness/config.json` already exists, ask before overwriting.
- If `CONTEXT.md` already exists, preserve it; offer to merge new terms only.
- Use `docs/reference/setup-contract.md` for generated files, config schema,
  smoke settings, optional eval/trace flags, and phase-state details.
- Preserve EZPowers automation: `.harness/config.json`, `phases/index.json`,
  docs slots, smoke config, and executor settings are first-class outputs.
- Executable artifacts require runtime smoke unless the setup contract allows
  an explicit `docs` or `library` exemption.
- Mark setup `in_progress` before writes and `complete` only after required
  files exist.
- Keep human-authored docs as slots unless the user provides real content.

## Stop conditions

- User declines overwrite of an existing harness.
- A required config value cannot be inferred and the user has not supplied it.
- A write would overwrite non-harness content without explicit approval.
- An executable artifact has no viable smoke command or GUI strategy.
- Required directories or files cannot be created.

## Outputs

- Created or updated file list (including `CONTEXT.md` when generated).
- Inferred and user-confirmed project settings.
- Smoke/runtime verification settings and any unresolved values.
- `phases/index.json` setup status.
- Human-owned docs that still need content.
- Next command: `/brainstorm`.
