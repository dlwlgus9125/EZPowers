# EZPowers Agent Guide

EZPowers is a personal workflow plugin for spec-driven agent work. The repo is
itself managed as a harness: project state lives in files, completion requires
machine evidence, and long-running work resumes from explicit state instead of
conversation memory.

## Start Here

- Read this file first.
- Read `CLAUDE.md` for the full plugin workflow and command inventory.
- Read `PROGRESS.md` before continuing active work.
- Read `feature_list.json` to find the single active improvement item.
- Use `docs/INDEX.md` to navigate reference contracts and reports.

## Current Workflow

Primary flow:

```text
/setup -> /design-architecture -> /spec -> internal pipeline audit -> /prepare-execute -> internal pipeline audit -> /choice-execute
```

Codex discovery note: EZPowers Codex plugins expose skills through the skill
surface, for example `$ezpowers:diagnose`, not as guaranteed `/` palette
entries. The slash-style workflow names above are skill documents under
`skills/<name>/SKILL.md`; read `docs/reference/codex-plugin-discovery.md` before
changing plugin discovery or install behavior.

Utility commands:

- `/reset-setup` reinstalls the verified local kit after plugin changes.
- `/maintain` routes bug, refactor, and issue-response work.
- `/deploy` prepares release and deployment verification.
- `/review` checks implementation against a spec or diff.
- `/sync-docs` updates docs after implementation.

## Steering Paths

- Specs: `docs/specs/`
- Plans: `docs/plans/`
- Phase state: `phases/index.json`
- Harness config: `.harness/config.json`
- Progress log: `PROGRESS.md`
- Feature state machine: `feature_list.json`
- ADRs: `docs/decisions/`

## Stack

- Markdown prompt and contract documents
- PowerShell harness runtime in `scripts/*.ps1`
- Python verify/model-router helpers in `scripts/*.py`
- Claude plugin metadata in `.claude-plugin/plugin.json`
- Codex plugin metadata in `.codex-plugin/plugin.json`

## Conventions

- Keep controller command files short; move long schemas and rules into
  `docs/reference/`.
- Preserve exact Verify commands unless the spec or plan is revised.
- Treat `docs/reference/*-contract.md` files as canonical when command text
  conflicts with local wording.
- Use the Reviewer Placement section of `docs/reference/dispatch-protocol.md`
  for the load-bearing review moments (wiring gate, final code review,
  pre-approval design review, conditional security review).
- For UI work, use `docs/reference/frontend-design-contract.md` and
  `docs/ux/frontend-design.md` so implementers do not invent design structure
  during coding.
- Prefer small, measured changes. Prompt or command behavior changes must be
  justified by a concrete defect or a stated design goal.
- Do not claim completion from passing tests alone. Completion requires the
  relevant Verify, smoke, wiring, or review evidence.

## No-Change Boundaries

- Do not weaken a Verify command, wiring gate, or runtime evidence check to make
  a change pass.

## Review Skip Patterns

None.

## Verification

Use these local checks for repo-level changes:

```powershell
python -m unittest discover -s tests
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/check-repo.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/harness-runtime-smoke.ps1
```

Use `scripts/harness-doctor.ps1` for strict harness-path preflight. An empty
`harness.root` means `/choice-execute Path 2` is intentionally disabled until an
external EasyPowersHarness executor is configured.
