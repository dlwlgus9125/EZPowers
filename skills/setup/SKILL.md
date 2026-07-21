---
name: setup
description: Initialize project harness with config and steering docs
disable-model-invocation: true
argument-hint: [--enable-traces]
allowed-tools: [Bash, Read, Write, Glob, Agent, AskUserQuestion]
---

# /setup - Project Harness Initialization

## Purpose

Initialize an EZPowers harness in the target project. Create configuration,
steering docs, phase state, reference doc slots, and a verified local EZPowers
kit. Do not write product code or synthesize skill bodies.

## Read

- `docs/reference/mattpocock-harness-adapter.md`
- `docs/reference/setup-contract.md`
- `docs/reference/harness-kit-contract.md`
- `docs/reference/reviewer-placement-contract.md`
- `docs/reference/ui-verification-adapter-contract.md`
- `docs/reference/frontend-design-contract.md`
- `docs/reference/domain-language.md`
- `docs/reference/verification-contract.md`
- `harness-kit/v2.0.0/manifest.json`
- Target repo root listing, manifests, source directories, `AGENTS.md`, `CLAUDE.md`, `CONTEXT.md`
- Existing `.harness/config.json`, `phases/index.json`, and `docs/` when present

## Rules

- Read repo evidence first. Ask only for values that cannot be inferred.
- Ask one question at a time; prefer concrete choices.
- If `.harness/config.json` already exists, ask before overwriting.
- If `CONTEXT.md` already exists, preserve it; offer to merge new terms only.
- Use `docs/reference/setup-contract.md` for generated files, config schema,
  smoke settings, optional eval/trace flags, and phase-state details.
- Install the local project kit exactly as defined by
  `docs/reference/harness-kit-contract.md`: copy bundled files only, record
  hashes, and fail if the manifest cannot be verified.
- Install every manifest entry, including approved `scripts/` helper targets.
  Missing gate helpers are setup failures, not a reason to use inline
  verification.
- Never generate, paraphrase, or merge `SKILL.md` bodies during setup. If the
  bundled kit is missing, stop and ask the user to update the plugin.
- Preserve EZPowers automation: `.harness/config.json`, `phases/index.json`,
  docs slots, smoke config, and executor settings are first-class outputs.
- For UI projects, create the `docs/ux/frontend-design.md` readiness slot and
  config fields from `docs/reference/frontend-design-contract.md`; do not
  synthesize the design brief during setup.
- Executable artifacts require runtime smoke unless the setup contract allows
  an explicit `docs` or `library` exemption.
- Use `docs/reference/setup-contract.md` Wiring Rules for auto-detecting and
  configuring `wiring` based on stack and UI presence. UI projects must have
  `wiring.enabled: true`; `docs`/`library` exemptions require `exempt_reason`.
- Mark setup `in_progress` before writes and `complete` only after required
  files exist.
- Keep human-authored docs as slots unless the user provides real content.

## Stop conditions

- User declines overwrite of an existing harness.
- A required config value cannot be inferred and the user has not supplied it.
- A write would overwrite non-harness content without explicit approval.
- An executable artifact has no viable smoke command or GUI strategy.
- The local kit manifest, bundled file, or installed hash ledger fails
  verification.
- Required directories or files cannot be created.

## Outputs

- Created or updated file list (including `CONTEXT.md` when generated).
- Inferred and user-confirmed project settings.
- Smoke/runtime verification settings and any unresolved values.
- Frontend design readiness slot, config fields, and unresolved inputs.
- `phases/index.json` setup status.
- Local kit install path, manifest version, and hash ledger path.
- Reviewer verdict summary from the reviewer placement gate.
- Human-owned docs that still need content.
- Next command: `/design-architecture`.
