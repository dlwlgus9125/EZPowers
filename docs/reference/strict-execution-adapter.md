---
description: Delegate plan execution to EasyPowersHarness executor
argument-hint: "[phase] [--status|--reset-step N|--push]"
allowed-tools: [Bash, Read, Write]
---

# Strict Execution Adapter - EasyPowersHarness Delegation

## Purpose

Internal adapter used by `/choice_execute` Path 2. Run the strict execution path for a plan phase when step logs, external harness
state, runtime smoke, recovery, or full-feature wiring evidence are required.
Delegate to the installed EasyPowersHarness; do not copy its executor into this
repo.

## Read

- `docs/reference/mattpocock-harness-adapter.md`
- `docs/reference/harness-execution-contract.md`
- `docs/reference/verification-contract.md`
- `docs/reference/dispatch-protocol.md`
- `docs/reference/domain-language.md`
- `.harness/config.json`, `AGENTS.md`, `phases/index.json`
- Plan artifact, `phases/{phase}/index.json`, `wiring-gate.json`, run logs
- Current git hash and recent diff

## Rules

- Use `/choice_execute Path 2` only for the strict path. Light, independent work should
  stay in `/choice_execute` Path 1 or Path 3.
- Run `scripts/harness-doctor.ps1 -ProjectRoot <project-root> -Phase <phase>`
  before conversion or execution. Stop on FAIL.
- Use `scripts/harness-phase.ps1` for `--status` and `--reset-step`.
- Use `scripts/harness-convert.ps1` for plan-to-phase conversion only when no
  usable phase exists.
- Use `scripts/harness-run.ps1 -ProjectRoot <project-root> -Phase <phase>` for
  step execution so timeout, progress, and attempt logs are controlled. If
  `/choice_execute` supplies an execution model override, add
  `-ExplicitModel <model>` to the same command.
- Use `scripts/harness-gate.ps1 -ProjectRoot <project-root> -Phase <phase>` for
  Full-Feature Wiring Gate evidence.
- Use `scripts/harness-certify.ps1 -ProjectRoot <project-root> -Phase <phase>` before reporting strict-path completion.
- If `harness-gate.ps1` records `review_pending`, stop with
  `PENDING_REVIEW` and return the artifact paths. The parent `/choice_execute`
  owns reviewer dispatch, verdict recording, and final gate rerun.
- When converting plan to phase, preserve task categories and wiring handoffs
  in step files. Skeleton step (step0) must pass runtime smoke before feature
  steps begin.
- Protect EZPowers `phases/index.json` from harness schema conflicts as defined
  in `docs/reference/harness-execution-contract.md`.
- Before reset or redispatch, identify the failing Verify, runtime, or wiring
  signal. A completed step table is not completion.
- Final success requires completed steps, wiring gate PASS, runtime evidence
  when required, and restored EZPowers phase state. Final code review remains
  owned by parent `/choice_execute`.

## Stop conditions

- `harness.root` is empty, invalid, or missing `scripts/execute.py`.
- `harness-doctor.ps1` reports FAIL.
- Prior `phases/index.ezpowers.json` backup needs user choice.
- Conversion cannot produce valid step files, phase index, or wiring gate.
- Step execution times out, makes no progress, or returns failed/blocked status.
- Wiring gate returns `fail`, `test_gap`, `code_gap`, or `spec_gap`.
- Wiring gate returns `review_pending`; report `PENDING_REVIEW` for parent
  `/choice_execute` finalization.

## Outputs

- Phase name, start hash, and execution mode.
- Per-step status table and run log path.
- Runtime smoke and wiring gate evidence, including `gate_status`.
- Recovery instruction when stopped.
- Restored `phases/index.json` build state.
- Diff range for parent `/choice_execute` final review.
