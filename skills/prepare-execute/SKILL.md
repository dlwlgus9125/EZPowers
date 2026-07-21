---
name: prepare-execute
description: Decompose spec into task plans with agent assignments
disable-model-invocation: true
allowed-tools: [Bash, Read, Write, Agent, AskUserQuestion]
shell: powershell
---

# /prepare-execute - Task Sequencing

## Purpose

Convert an approved spec into an implementation plan that independent agents can
execute safely. Preserve requirement coverage, architecture invariants, TDD
slices, runtime evidence, and wiring gates. Do not implement code.

Harness state (injected on Claude Code; on Codex read the files directly):

```!
if (Test-Path .harness/config.json) { "CONFIG: present" } else { "CONFIG: MISSING" }
if (Test-Path phases/index.json) { "PHASES_INDEX:"; Get-Content phases/index.json -Raw } else { "PHASES_INDEX: MISSING" }
"HEAD: $(git rev-parse HEAD 2>$null)"
```

## Read

- `docs/reference/plan-contract.md`
- `docs/reference/spec-contract.md`
- `docs/reference/design-architecture-contract.md`
- `docs/reference/verification-contract.md`
- `docs/reference/dispatch-protocol.md`
- `docs/reference/domain-language.md`
- `.harness/config.json`, `AGENTS.md`, `phases/index.json`
- Spec artifact from argument, phase state, or latest spec directory entry
- Existing source tree, tests, docs, and recent git changes

## Rules

- Require internal pipeline audit status `PASS` or `WARN` before planning.
- Set plan `in_progress` in `phases/index.json`; remove stale audit data.
- Read the spec's architecture sections and declare assumptions before tasking.
- Return to `/spec` when the spec lacks architecture, has contradictions,
  or leaves implementation agents to invent requirements.
- Return to `/spec` when UI work lacks frontend design readiness; order new UI design-system tasks as tokens, primitives, component states/stories, screens, then e2e/visual verification. Require Storybook, Playwright screenshot, visual diff, or screenshot review loop tasks only when project-local tooling exists or the plan adds it as a prerequisite.
- Use `docs/reference/plan-contract.md` for Coverage Matrix, Structural
  Invariants, task template, TDD Slice Contract, impact scope, pipeline matrix,
  Full-Feature Wiring Gate, Agent Assignment, review loop, and phase updates.
- Tasks are vertical red-green slices through public interfaces, not layer
  batches. Copy spec acceptance criteria without weakening the oracle.
- For executable artifacts with no existing runnable app, Task 1 must be
  `{skeleton}` — a minimal vertical slice through a real entry point that maps
  to at least one spec requirement. It must wire WM-EP and WM-REG items from
  the spec's Wiring Map. Runtime smoke AND one feature-path Verify must pass
  before feature tasks begin.
- Add automated runtime and wiring evidence when work touches executable entry
  points, multiple layers, connected tasks, routes, bindings, or registrations.
- Apply the UI Adapter Evidence section of
  `docs/reference/verification-contract.md`. For UI work, select the strongest
  available adapter that preserves the same user-observable oracle. If no valid adapter exists, insert a prerequisite
  task that installs or builds the adapter before feature implementation.
- For executable artifacts, every task that creates a new module must include a
  `**Wiring probe:**` section specifying: entry point path, module path, probe
  type (`import-chain` | `runtime-load` | `e2e-touch`), and a Verify command
  where exit 0 proves the module is reachable from the entry point. See
  `docs/reference/verification-contract.md` § Incremental Wiring Probe.
- Dispatch `ezpowers:plan-reviewer` and, for UI work, the
  `ezpowers:frontend-experience-reviewer` through the dispatch protocol.
- After plan approval, dispatch `ezpowers:workflow-runner` through the dispatch
  protocol: target command `internal pipeline audit`, invocation mode
  `post-prepare_execute`, working directory project root, artifacts spec path
  and plan path.

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
- Reviewer verdict, frontend experience review when UI is present, and post-prepare_execute audit result.
- Updated `phases/index.json` plan state.
- Next command: `/choice-execute` when audit status is `PASS` or `WARN`.
