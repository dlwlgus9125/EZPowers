# Matt Pocock Harness Adapter

This document maps useful Matt Pocock engineering skill principles onto the
EZPowers workflow. It is a reference adapter, not a command replacement.

EZPowers automation wins whenever there is a conflict. Matt Pocock skills
contribute vocabulary and engineering discipline; EZPowers keeps ownership of
state, routing, reviewers, phase files, and automated gates.

## Adopted Skills

| Matt skill | EZPowers position | Adopted rule |
|------------|-------------------|--------------|
| `engineering/tdd` | `/prepare_execute` task shape | Each task is one vertical red-green slice through a public interface. Do not write all tests first and then all implementation. |
| `engineering/tdd` | Verify evidence | Tests and Verify commands must assert observable behavior through the public interface, not internal call shape. |
| `engineering/diagnose` | `/choice_execute Path 2` failure recovery | Build or identify a fast pass/fail signal before resetting steps or redispatching agents. |
| `engineering/diagnose` | Harness helper scripts | Prefer deterministic, narrow, agent-runnable feedback loops such as `harness-smoke.ps1`, `harness-doctor.ps1`, `harness-run.ps1`, and `harness-gate.ps1`. |
| `engineering/improve-codebase-architecture` | Architecture baseline and plan invariants | Use Module, Interface, Depth, Seam, Adapter, Locality, and Deletion test language when reviewing architecture and task boundaries. |
| `engineering/improve-codebase-architecture` | Test surface selection | The interface is the test surface; tests should survive internal refactors. |
| `engineering/to-issues` | `/prepare_execute` task decomposition | EZPowers plan tasks are the issue analogue. They must be independently grabbable vertical slices with explicit blockers. |
| `engineering/grill-with-docs` | `CONTEXT.md` generation and maintenance | Target projects get a domain glossary at `CONTEXT.md`. Skills that challenge terminology (`grill-with-docs`, `improve-codebase-architecture`) update it inline. |
| `misc/setup-pre-commit` | `.githooks/pre-commit` | Keep commit-time checks fast and targeted. Harness-only edits use the PowerShell harness docs gate instead of the heavier Python eval gate. |

## Rejected Or Deferred Skills

| Matt skill idea | EZPowers decision |
|-----------------|-------------------|
| Local/GitHub/GitLab issue tracker setup | Deferred. EZPowers already tracks workflow state in `phases/index.json`, plan files, and harness phase directories. |
| Human approval before every TDD cycle | Rejected for harness execution. EZPowers requires automated verification and only escalates on missing information, blocked state, or repeated failure. |
| Bulk issue publication from a plan | Replaced by `/prepare_execute` tasks plus `/choice_execute` or `/choice_execute Path 2` routing. |
| Direct Husky/npm pre-commit setup | Replaced by the existing `.githooks/pre-commit` shell hook and PowerShell/Python split gates. |

## Position Rules

### `/setup`

- Keep setup as a small controller over generated project state.
- Build a fast runtime smoke loop early: executable artifacts need a real
  command and GUI strategy instead of a vague "manual check".
- Keep config schemas and generated document templates in
  `docs/reference/setup-contract.md`, not in the prompt body.
- Install only the verified local kit. Do not synthesize skill bodies during
  setup or reset setup.
- Ask for missing project facts one at a time after reading repo evidence.
- Generate `CONTEXT.md` slot when domain terms are detected or user-confirmed.

### `/design_architecture`

- Define architecture, testing methodology, project structure, and roadmap
  before feature-level specs.
- Select UI verification by capability and user-observable oracle, not by a
  hard-coded tool.
- Use current web research only when local project evidence is insufficient.

### `/spec`

- Treat design as the public interface for downstream agents.
- Prefer short architecture options, explicit tradeoffs, and stop conditions
  over a long procedure manual.
- Use `grill-with-docs` as the stress test before requirements are frozen.
- Keep requirement schema, ADR rules, and vague-language exceptions in
  `docs/reference/spec-contract.md`.

### `/prepare_execute`

- Convert requirements into vertical slices, not layer batches.
- Each behavior-bearing task must name its public interface, behavior under
  test, oracle, setup, minimal implementation boundary, and non-goals.
- Task tests and Verify commands must prove behavior visible at the interface.
- Integration milestones and the Full-Feature Wiring Gate cover cross-task
  wiring when a feature spans layers or executable entry points.

### `/choice_execute Path 2`

- Treat the harness as the strict path for step logs, runtime smoke, recovery,
  and wiring evidence.
- Run `harness-doctor.ps1` before execution so failure starts from a concrete
  environment signal.
- Use `harness-phase.ps1` for status and reset so operators do not manually edit
  phase state.
- Use `harness-run.ps1` for step execution so Python executor calls have an
  explicit timeout, progress check, and attempt log.
- Use `harness-gate.ps1` for full-feature evidence. A completed step table is
  not enough.
- Before any reset or redispatch, identify the failing Verify, runtime, or
  wiring signal.

### Architecture Review

- Name workflow units as Modules and define their Interfaces.
- Prefer deep modules: a small interface hiding meaningful behavior.
- Apply the Deletion test to pass-through workflow modules and helper scripts.
- Add Structural Invariants when architecture rules can be checked by command.

### Pre-Commit

- Harness contract changes use `scripts/check-harness-docs.ps1`.
- General command, agent, skill, and eval changes keep using the Python eval
  gate unless scoped out by the harness-only path.
- The split is intentional: fast feedback loops are part of the harness design.

## Evidence Requirements

This adapter is covered when:

- `commands/setup.md`, `commands/design_architecture.md`, and
  `commands/spec.md` read this adapter directly.
- Controller commands use Purpose, Read, Rules, Stop conditions, and
  Outputs as their visible prompt surface.
- `commands/prepare_execute.md` contains vertical red-green slice task rules.
- `docs/reference/strict-execution-adapter.md` routes status, reset, preflight, conversion, and
  step/gate work through the PowerShell helpers.
- `docs/reference/setup-contract.md`, `docs/reference/spec-contract.md`,
  `docs/reference/plan-contract.md`, and
  `docs/reference/harness-execution-contract.md` hold the long templates,
  schemas, and exception rules.
- `docs/reference/architecture-readiness-contract.md` defines the architecture
  vocabulary and Deletion test.
- `.githooks/pre-commit` runs `check-harness-docs.ps1` for harness-only changes.
- `scripts/check-harness-docs.ps1` runs helper-level checks and the end-to-end
  `harness-smoke.ps1` flow.
