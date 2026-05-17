# Domain Language

This document is the canonical vocabulary for EZPowers workflow design. Use
these terms in command documents, reviewer agents, eval cases, and architecture
reviews when referring to workflow modules and their interfaces.

## Workflow Modules

**Setup**
Initializes a target project harness. Its interface is the created project
configuration, steering documents, phase index, and reference document slots.

**Spec**
The design artifact produced by `/brainstorm`. Its interface is the
Architecture Baseline, ASR Ledger, Option Matrix, Lifecycle And Operations,
Quality Budgets, Decision Log, and Extracted Requirements.

**Plan**
The implementation artifact produced by `/plan`. Its interface is the Coverage
Matrix, Structural Invariants, tasks (with task categories and wiring
handoffs), dependency metadata, verification method, Integration Contract
Matrix, Full-Feature Wiring Gate, and Agent Assignment.

**Pipeline Audit**
The cross-stage completeness gate. Its interface is an audit verdict written to
`phases/index.json` plus routing recommendations back to `/brainstorm`,
`/plan`, or forward to the next command.

**Choice Executor**
The implementation controller. Its interface is the selected execution path,
per-task verification evidence, final review verdict, docs sync status, and
phase completion state.

**Execute Harness**
The strict execution adapter for EasyPowersHarness. Its interface is a
requested phase, converted step files, step status table, runtime/wiring
evidence, recovery route, and final review diff range.

**Workflow Runner**
A scoped runner agent for command-level chaining. Its interface is a target
command, invocation mode, artifact paths, status line, changed files, optional
commit hash, and routing recommendation.

**Reviewer**
A read-focused agent that checks one artifact or diff through a fixed verdict
interface. Reviewer prompts are procedures, not advisory essays.

## Evidence Terms

**Acceptance Criterion**
A user-observable behavior claim attached to one requirement. It defines the
test surface for both planning and execution.

**Verify Command**
An automated command whose exit code is the primary oracle for an acceptance
criterion. Exit 0 means pass. Non-zero means fail unless the criterion explicitly
documents a skip condition.

**Verify Type**
The category of evidence needed by a Verify Command: `pure`, `cli`, `lib`,
`api`, `e2e`, or `data`.

**Runtime Probe**
An automated startup/survival check for executable artifacts. It proves the
artifact starts and remains alive; it does not replace feature verification.

**Full-Feature Wiring Gate**
The end-to-end oracle for connected work. It proves changed parts are
registered, routed, bound, subscribed, imported, or called through the
user-facing path.

**Structural Invariant**
A verifiable architecture rule carried from architecture references, ASRs, or
project conventions into the plan and final review.

**ASR**
An Architecturally Significant Requirement. It affects structure, lifecycle,
performance, reliability, security, compatibility, cost, or operations.

**ADR**
An Architecture Decision Record. EZPowers writes ADRs only when the decision is
hard to reverse, surprising without context, and a real tradeoff.

## Interface Terms

**Interface**
Everything another workflow module must know to use an artifact correctly:
required sections, fields, allowed statuses, verdict strings, ordering, error
modes, and verification expectations.

**Seam**
The place where a workflow module can vary without editing callers. Examples:
reviewer backend selection, workflow-runner target command selection, and
harness versus inline execution.

**Adapter**
A concrete implementation behind a seam, such as `claude-code` reviewer
dispatch, `codex-cli` reviewer dispatch, harness execution, subagent execution,
or inline execution.

**Light Path**
Execution through inline work or task subagents when strict harness logs and
runtime/wiring recovery are not needed. Light Path still uses the shared
lightpath gate for Verify commands, runtime smoke, and Full-Feature Wiring Gate
completion.

**Strict Path**
Execution through `/executeharness` when the work needs external harness logs,
step-level recovery, or harness-managed recovery. Strict Path and Light Path
share the same completion verdict vocabulary.

## View Wiring Terms

**View Wiring Test**
Per-task automated verification that a view file's bindings, handlers,
dependency resolution, activation states, and templates resolve at the view
instantiation level. Runs after AC verification for tasks containing view files
(`config.wiring.view_extensions`). Layer 2 in the verification hierarchy.
The `wiring` block in `config.json` is required. A missing block is a
configuration error (FAIL), not a skip condition. `wiring.enabled: false`
requires a non-empty `exempt_reason`; only `docs`/`library` artifacts qualify.

**Wiring Defect (W1-W5)**
Five categories of view-level defects that model-only tests cannot catch:
W1 binding resolution, W2 handler connection, W3 dependency resolution,
W4 activation state, W5 template resolution.

**Integration Probe**
Post-completion automated test that exercises the full feature pipeline through
the user-facing entry point, verifying cross-task wiring. Corresponds to
Layer 3 and the Full-Feature Wiring Gate's dynamic verification.
`config.wiring.wiring_gate_command` drives this probe when configured.

## Wiring Design Terms

**Wiring Map**
Spec-level declaration within Architecture Baseline for executable artifacts.
Lists entry points (WM-EP), registration sites (WM-REG), data flow paths
(WM-DF), and integration contracts (WM-C) with unique IDs. Input to plan
decomposition and wiring coverage verification.

**Integration Contract Matrix**
Plan-level table mapping Wiring Map items to tasks, wiring handoffs, and
verify commands. Required for executable plans with 2+ tasks. Extends the
Integration Pipeline Matrix for executable artifacts with WM-ID traceability.

**Skeleton Task**
Plan Task 1 for new executable artifacts. Creates a minimal runnable vertical
slice through a real entry point — not stub scaffolding. Must pass runtime
smoke AND prove one feature path (e.g., CLI command returns expected output,
health route resolves, window renders text). All subsequent tasks extend this
slice. Maps to at least one spec requirement.

**Task Category**
Plan task classification: `skeleton`, `feature`, `wiring`, `integration-test`.
Determines verification obligations and wiring handoff requirements. Appears
in the task header as `{category}`.

**Incremental Runnability**
Post-skeleton gate that runs `config.smoke.command` after every task to
prevent regression of the running application. Separate from per-task
`Runtime verification:` which tests task-specific behavior.

**Wiring Handoff**
Per-task declaration of integration contracts produced or consumed — DI tokens,
routes, events, exports, message schemas. Mandatory for any task that publishes
something consumed by a downstream task or by the app entry point. References
Wiring Map IDs.
