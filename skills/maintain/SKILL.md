---
name: maintain
description: Triage and plan maintenance, refactor, or issue-response work
disable-model-invocation: true
argument-hint: "[issue description]"
allowed-tools: [Bash, Read, Write, Agent, AskUserQuestion]
---

# /maintain - Maintenance And Issue Response

## Purpose

Turn bugs, regressions, refactors, or operational issues into harness-tracked
work without bypassing architecture, spec, plan, or evidence gates.

## Read

- `docs/reference/domain-language.md`
- `docs/reference/mattpocock-harness-adapter.md`
- `docs/reference/spec-contract.md`
- `docs/reference/plan-contract.md`
- `docs/reference/verification-contract.md`
- `docs/reference/reviewer-placement-contract.md`
- `docs/reference/ui-verification-adapter-contract.md`
- `.harness/config.json`, `phases/index.json`, active specs/plans, recent diffs,
  logs, failing tests, issue reports, and release notes

## Rules

- Classify the request as bug fix, refactor, dependency update, test gap,
  operational incident, or documentation maintenance.
- Reproduce or identify the failing signal before planning changes.
- For bug fixes and operational incidents, invoke the `diagnose` skill to run
  the root-cause loop before proposing any fix.
- For refactor requests, invoke the `improve-codebase-architecture` skill to
  ground the refactor in deepening opportunities before routing.
- Route architecture or verification-policy changes to `/design-architecture`.
- Route behavior changes to `/spec`; route task-only implementation changes to
  `/prepare-execute` only when an existing approved spec already covers them.
- Update roadmap, project structure, ADRs, or testing methodology when the
  maintenance work changes them.
- Preserve the same completion gates as feature work: Verify commands, smoke,
  UI adapter checks, wiring gate, and final review.

## Stop conditions

- No reproducible signal exists for a reported defect and the user cannot
  provide one.
- The requested change conflicts with current architecture decisions.
- The fix requires changing acceptance criteria without spec approval.

## Outputs

- Issue classification and failing signal.
- Route decision: `/design-architecture`, `/spec`, `/prepare-execute`, or
  `/choice-execute`.
- Updated docs or phase state when routing changes.
- Verification commands that must pass before completion.
