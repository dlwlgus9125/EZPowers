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
/setup -> /brainstorm -> /pipeline-audit -> /plan -> /pipeline-audit -> /choiceexecutor
```

Utility commands:

- `/eval` runs command and skill eval gates.
- `/review` checks implementation against a spec or diff.
- `/sync-docs` updates docs after implementation.
- `/feedback` attaches user signal to the current harness trace.

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
- PowerShell harness helpers in `scripts/*.ps1`
- Python eval and validation helpers in `scripts/*.py`
- Claude plugin metadata in `.claude-plugin/plugin.json`
- Codex plugin metadata in `.codex-plugin/plugin.json`
- Bash trace collector in `bin/trace.sh`

## Conventions

- Keep controller command files short; move long schemas and rules into
  `docs/reference/`.
- Preserve exact Verify commands unless the spec or plan is revised.
- Treat `docs/reference/*-contract.md` files as canonical when command text
  conflicts with local wording.
- Prefer small, measured changes. Prompt or command behavior changes must be
  justified by eval results or a concrete defect.
- Do not claim completion from passing tests alone. Completion requires the
  relevant Verify, smoke, wiring, review, or eval gate evidence.

## No-Change Boundaries

- Do not edit `evals/holdout/**`.
- Do not commit trace/run output under `evals/results/runs/**`.
- Do not rewrite generated plugin mirrors under `plugins/` unless the task is
  explicitly about packaging or publishing the plugin.
- Do not weaken golden eval cases to make a change pass.

## Review Skip Patterns

None.

## Verification

Use these local checks for repo-level changes:

```powershell
python -m unittest discover -s tests
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/check-harness-docs.ps1
python scripts/run_baseline.py --version local --splits golden optimization honeypot
```

Use `scripts/harness-doctor.ps1` for strict harness-path preflight. An empty
`harness.root` means `/executeharness` is intentionally disabled until an
external EasyPowersHarness executor is configured.
