# EZPowers Agent Guide

EZPowers is a dual-host workflow plugin that keeps project-specific intent,
verification commands, completion evidence, and resume state in the target
repository. Claude Code and Codex perform implementation and orchestration;
EZPowers supplies the same local completion verdict to both.

## Start Here

Read these files in order before changing this repository:

1. `AGENTS.md`
2. `CLAUDE.md`
3. `PROGRESS.md`
4. `feature_list.json`
5. `docs/INDEX.md`

Preserve user changes shown by `git status --short --branch`. Use repository
evidence before conversation memory.

## Current Workflow

```text
setup -> deep-interview (when decisions are unclear or need stress-testing)
      -> design-architecture (when technical boundaries are unsettled)
      -> spec -> prepare-execute -> execute
```

Plugin invocation differs by host: Claude Code uses `/ezpowers:<name>` and
Codex uses `$ezpowers:<name>`. Project-local copies use the host's normal local
skill syntax. See `docs/reference/codex-plugin-discovery.md`.

Roles are intentionally narrow:

- `deep-interview`: clarification plus the former “grill me” stress-test mode.
- `spec`: settled decisions only, expressed as traceable acceptance criteria.
- `prepare-execute`: criterion coverage and exact project checks.
- `execute`: host-native implementation followed by local verify/certify.
- `setup --refresh`: installation repair; there is no separate reset skill.

`frontend-design` and `improve-codebase-architecture` are independent advisory
skills. `hud` is an explicit, plugin-only global Codex utility and is never
installed into a project kit.

## Responsibility Boundary

- Claude Code or Codex owns editing, shell execution, subagents, worktrees,
  sandboxing, general retry policy, and code review.
- EZPowers owns managed spec/plan data, project-specific argv checks, real
  command execution, hashed evidence, certification freshness, and resume state.
- Do not reintroduce model routing, reviewer agents, plan-to-phase conversion,
  numbered execution paths, or an implicit external executor.
- Do not claim identical host capabilities. Only the core EZPowers verdict is
  host-independent; hook response schemas remain thin host adapters.

## Source of Truth

- Project config: `.ezpowers/config.json`
- Resume/evidence pointer: `.ezpowers/state.json`
- Runtime: `scripts/ezpowers.py`
- Distribution manifest: `project-kit/v5.0.0/manifest.json`
- Specs and plans: `docs/specs/`, `docs/plans/`
- Canonical contracts: `docs/reference/*-contract.md`
- Product state: `PROGRESS.md`, `feature_list.json`
- Audit record: `docs/reports/workflow-harness-audit-2026-07-22.md`

The installed runtime, manifest, skills, references, contracts, and frontend
readiness tool must be self-contained. Preserve exact check argv unless the
approved spec or plan changes. Never weaken validation, evidence, or freshness
rules merely to pass a gate.

## Repository Verification

```powershell
python -m unittest discover -s tests
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/check-repo.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/harness-runtime-smoke.ps1
python scripts/verify-harness-kit.py
python scripts/plugin_smoke.py --host both
```

Completion requires applicable command output and a clean final diff review,
not a prose claim or a test-name/string-presence check.
