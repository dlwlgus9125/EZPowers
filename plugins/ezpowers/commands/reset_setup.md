---
description: Reinstall EZPowers local kit and refresh harness setup documents
allowed-tools: [Bash, Read, Write, Glob, Agent, AskUserQuestion]
---

# /reset_setup - Harness Setup Refresh

## Purpose

Refresh an existing project harness after EZPowers version changes. Reinstall
the verified local kit, migrate config/doc slots, and preserve project-specific
content. Do not rewrite product code or synthesize skills.

This command does not update installed Codex or Claude plugin command caches.
After changing plugin files, publish or reinstall the plugin package and start a
new agent session so the host reloads command definitions.

## Read

- `docs/reference/harness-kit-contract.md`
- `docs/reference/mattpocock-harness-adapter.md`
- `docs/reference/reviewer-placement-contract.md`
- `docs/reference/setup-contract.md`
- `harness-kit/v2.0.0/manifest.json`
- Existing `.harness/config.json`, `.harness/ezpowers/ledger.json`,
  `phases/index.json`, `AGENTS.md`, `CLAUDE.md`, `CONTEXT.md`, and `docs/`

## Rules

- Verify the bundled kit before writing.
- Copy every bundled manifest entry, including approved `scripts/` helper
  targets, plus generated setup slots. Do not generate `SKILL.md` bodies from
  prose or merge unrelated command text.
- Missing gate helpers are reset failures, not a reason to use inline
  verification.
- Preserve human-authored docs. If a canonical slot needs schema updates,
  append a migration note instead of replacing content.
- Record previous and new kit versions, file hashes, and migrated fields in
  `.harness/ezpowers/ledger.json`.
- If a migration changes verification semantics, mark architecture and spec
  phases as needing review.

## Stop conditions

- Manifest or bundle hash verification fails.
- Existing human-authored content would be overwritten.
- Current project config cannot be parsed.
- User declines migration of a breaking setup change.

## Outputs

- Reinstalled kit version and ledger path.
- Config/doc fields migrated.
- Workflow contract reviewer verdict.
- Files left for manual review.
- Updated phase state.
- Next command: `/design_architecture` when architecture or verification
  settings changed; otherwise resume the prior phase.
