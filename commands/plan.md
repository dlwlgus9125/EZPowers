---
description: Decompose spec into task plans with agent assignments
allowed-tools: [Bash, Read, Write, Agent, AskUserQuestion]
---

# /plan - Task Sequencing

## Purpose

Convert an approved spec into an implementation plan that independent agents can
execute safely. Preserve requirement coverage, architecture invariants, TDD
slices, runtime evidence, and wiring gates. Do not implement code.

## Read

- `docs/reference/mattpocock-harness-adapter.md`
- `docs/reference/plan-contract.md`
- `docs/reference/spec-contract.md`
- `docs/reference/architecture-readiness-contract.md`
- `docs/reference/verification-contract.md`
- `docs/reference/dispatch-protocol.md`
- `docs/reference/domain-language.md`
- `.harness/config.json`, `AGENTS.md`, `phases/index.json`
- Spec artifact from argument, phase state, or latest spec directory entry
- Existing source tree, tests, docs, and recent git changes

## Rules

- Require `/pipeline-audit` status `PASS` or `WARN` before planning.
- Set plan `in_progress` in `phases/index.json`; remove stale audit data.
- Read the spec's architecture sections and declare assumptions before tasking.
- Return to `/brainstorm` when the spec lacks architecture, has contradictions,
  or leaves implementation agents to invent requirements.
- Use `docs/reference/plan-contract.md` for Coverage Matrix, Structural
  Invariants, task template, TDD Slice Contract, impact scope, pipeline matrix,
  Full-Feature Wiring Gate, Agent Assignment, review loop, and phase updates.
- Tasks are vertical red-green slices through public interfaces, not layer
  batches. Copy spec acceptance criteria without weakening the oracle.
- Add automated runtime and wiring evidence when work touches executable entry
  points, multiple layers, connected tasks, routes, bindings, or registrations.
- Dispatch `ezpowers:plan-reviewer` through the dispatch protocol.
- After plan approval, dispatch `ezpowers:workflow-runner` for `/pipeline-audit`
  in `post-plan` mode.

## Stop conditions

- Missing config, spec, or required audit state.
- Spec is not architecture-ready.
- Any requirement lacks task coverage and the user has not approved omission.
- Any behavior-bearing task lacks an automated Verify command.
- Required Full-Feature Wiring Gate has no non-trivial command.
- Plan reviewer or pipeline audit returns a blocking verdict.

## Outputs

- Plan path.
- Coverage Matrix and uncovered-risk summary.
- Task count, dependencies, file overlap, and risky tasks.
- Runtime, structural invariant, and wiring gate commands.
- Reviewer verdict and post-plan audit result.
- Updated `phases/index.json` plan state.
- Next command: `/choiceexecutor` when audit status is `PASS` or `WARN`.
