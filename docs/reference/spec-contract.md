# Spec Contract

This reference contains the spec-writing and review details that do not belong
in the `/spec` controller prompt.

## Source Contracts

- `docs/reference/mattpocock-harness-adapter.md`
- `docs/reference/design-architecture-contract.md`
- `docs/reference/architecture-readiness-contract.md`
- `docs/reference/verification-contract.md`
- `docs/reference/ui-verification-adapter-contract.md`
- `docs/reference/app-delivery-contract.md`
- `docs/reference/frontend-design-contract.md`
- `docs/reference/dispatch-protocol.md`
- `docs/reference/reviewer-placement-contract.md`
- `docs/reference/domain-language.md`

## Preflight

`/spec` requires `.harness/config.json`. If it is missing, route to
`/setup`.

`/spec` also requires the architecture artifacts from `/design_architecture`.
If `docs/reference/architecture.md`, `docs/reference/testing-methodology.md`,
or the architecture phase state is missing, route to `/design_architecture`.

When `phases/index.json` exists:

- Set `current_phase` to `spec`.
- Set spec status to `in_progress`.
- Delete stale `audit` data.

## Design Flow

Use this order:

1. Read project context.
2. Declare assumptions.
3. Ask one question at a time.
4. Produce an architecture baseline and App Experience And Delivery Baseline,
   including frontend design readiness when UI is present.
5. Confirm the architecture and app delivery baseline.
6. Run `grill-with-docs`.
7. Extract requirements.
8. Confirm requirements.
9. Write spec, ADRs, verify script, and docs index entry.
10. Run spec and architecture review loops.
11. Get user approval.
12. Update phase state.
13. Dispatch `internal pipeline audit` in `post-spec` mode.

Small work may have a short design, but it still follows this order.

## Architecture Baseline

Every spec starts with these sections before requirements:

- Architecture Baseline.
- ASR Ledger.
- Option Matrix.
- Lifecycle And Operations.
- Quality Budgets.
- App Experience And Delivery Baseline (app/API artifacts only).
- Wiring Map (executable artifacts only).
- Initialization Order (executable artifacts with 2+ startup dependencies).
- Decision Ledger.
- Decision Log.
- Extracted Requirements.

**Observability detail requirements:**
When `observability` is listed in Lifecycle, the spec must declare:
- Log format: structured (JSON) or plain text
- Log levels: which events at which level (error: failures, warn: degradation, info: key operations, debug: troubleshooting)
- Metrics: what to measure (latency, throughput, error rate, queue depth) and collection method (pull/push, tool)
- Tracing: whether distributed tracing is needed, correlation ID strategy
- If `none declared`: state explicitly with rationale (e.g., "single-process CLI with no external dependencies — stdout logging sufficient")

The architecture baseline must identify modules, interfaces, allowed
dependencies, forbidden dependencies, data ownership, selected approach, and
rejected options.

## Decision Ledger

Carry forward every applicable decision from `/design_architecture` into a
`## Decision Ledger` table before requirements:

| ID | Question/Trigger | Decision | Source | Artifacts Updated | Open Follow-up |
|----|------------------|----------|--------|-------------------|----------------|

Each requirement or baseline constraint that depends on a user answer,
repo-inferred default, delegated frontend/design choice, or operational policy
must reference the relevant ledger ID or state `none applicable`. The Decision
Log may link ADRs, but it does not replace this carry-forward ledger.

Each ASR must affect structure, lifecycle, performance, reliability, security,
compatibility, cost, or operations. If a quality budget is not declared, state
`none declared` and explain the risk.

## App Experience And Delivery Baseline

Required for `web`, `mobile`, `desktop`, `cli`, and `api` surface kinds from
`.harness/config.json` `app_delivery.surface_kind`. Omit only for `docs` or
`library` with an explicit reason. Follow
`docs/reference/app-delivery-contract.md` for the required surface inventory,
UX flow map, frontend contract, backend contract, packaging contract,
deployment contract, and QA contract.

For UI surfaces, follow `docs/reference/frontend-design-contract.md`. The
baseline must reference `docs/ux/frontend-design.md` and carry forward the
selected design direction, design-system source, token policy, component
taxonomy, UX state matrix, responsive rules, accessibility target, and visual
QA strategy. It must also carry forward mock/prototype artifact handling and
tool-conditional visual readiness lanes for Storybook/component states,
Playwright or equivalent screenshot baselines, visual diff baselines, and
screenshot/visual review loops when those tools are available or planned.
Missing frontend design readiness routes back to `/design_architecture`.

## Wiring Map (executable artifacts only)

Required when `config.smoke.artifact_kind` is `cli`, `server`, or `desktop`.
Omit for `docs` or `library`.

Declares how components connect. Part of the Architecture Baseline.

| ID | Aspect | Value |
|----|--------|-------|
| WM-EP1 | Entry point | `main()` in `src/cli.ts` |
| WM-REG1 | Registration | `yargs.command()` in `src/commands/index.ts` |
| WM-DF1 | Data flow | CLI args → CommandHandler → FileSystem → stdout |
| WM-C1 | Contract | `CommandHandler.execute(args: ParsedArgs): Result` |

Rules:

- Every entry point, registration site, and cross-module boundary gets a unique
  ID (WM-EP, WM-REG, WM-DF, WM-C prefix).
- IDs are referenced in plan Coverage Matrix and Integration Contract Matrix.
- Contracts specify the function signature, event name, DI token, or message
  format at each boundary.
- Each WM-DF entry must name: (a) the data type at entry, (b) each
  transformation step with its input/output types, and (c) the data type at
  exit. A WM-DF that only names module names without data types is insufficient.
- For each WM-DF, the spec must include a Verify command in the relevant R's AC
  that traces data from entry to exit. This Verify command proves data flows,
  not just that modules exist.

## Architecture Approval Text

Use this shape before requirement extraction:

```markdown
Architecture baseline:
- Selected approach:
- ASRs:
- Lifecycle:
- Quality budgets:
- App delivery:
- Wiring map: (executable artifacts only)
- ADR candidates:

Confirm this architecture and app delivery baseline before I extract requirements.
```

After confirmation, invoke `grill-with-docs`. Any unresolved issue blocks
requirement extraction until the design is revised and reconfirmed.

## Requirement Extraction

Use unique IDs:

```markdown
## Extracted Requirements

- R1: Specific observable requirement.
- R2: Specific observable requirement.
```

Rules:

- Requirements must be specific and actionable.
- Ask the user to confirm the list.
- If requirements exceed 10, propose sub-project decomposition.
- If the user identifies missing requirements three times in a row, return to
  questioning.

## Operational Requirements Checklist

Before requirement extraction, evaluate these cross-cutting concerns and record
applicable decisions in the Architecture Baseline. Each item applies when the
project meets its condition.

| Concern | Condition | Record in Baseline |
|---------|-----------|-------------------|
| Error handling pattern | Any runtime code | throw/return/Result type/error boundary — pick one pattern |
| Logging strategy | Any runtime code | structured/unstructured, library, log levels |
| Configuration management | Env vars, config files, or CLI args exist | source priority, validation at startup, missing-key behavior |
| Initialization order | 2+ modules with startup dependencies | module → prerequisite → readiness signal |
| State management policy | Shared mutable state exists | global state rules, thread safety, ownership |
| External dependency handling | Network calls, DB, queues, file I/O | timeout, retry, circuit-break defaults |
| Observability strategy | `server`, `cli` (recommended), `desktop` (recommended) | logging levels (debug/info/warn/error), structured format (JSON vs plain), metric collection points, trace propagation method |
| Health & readiness signals | `server` (required), `cli` with long-running mode (recommended) | health check endpoint or command, readiness probe for dependent services, graceful shutdown signal handling |
| UX states | UI or user-facing CLI exists | loading, empty, error, permission, cancellation, responsive states |
| API contract | API/server boundary exists | endpoint/event/schema ownership, status/error shape, auth/session behavior |
| Packaging and deployment | executable app or deploy target exists | artifact, build output, target environment, required env vars, readiness, rollback |
| Accessibility baseline | UI exists | keyboard path, focus behavior, semantic labels, contrast or visual check strategy |

Rules:

- Ask the user about each applicable concern during architecture baseline
  creation. One question at a time.
- Record each decision in the Decision Ledger and summarize applicable entries under the Architecture Baseline section.
- Implementers must follow these decisions — not invent alternatives.
- If none apply (pure library, docs-only), state `none applicable` and skip.

## Requirement Section Template

Each requirement section uses:

```markdown
### R[N]: Title

**ASR:** ASR IDs or none
**Surface:** ui | api | data | package | deploy | docs | none
**Input:** Trigger or input
**Behavior:** Step-by-step behavior
**Output:** Observable result
**Impact scope:**
- Module or component: Impact
**Acceptance criteria:**
- [ ] Given: Observable precondition
      When: User or system action
      Then: Observable result
      Verify: `command where exit 0 means pass`
      Verify-type: pure | cli | lib | api | e2e | data
      Automatable: true
**Edge cases:**
- Condition: Expected behavior
```

For `Verify-type: pure`, Input/Transform/Output may replace
Given/When/Then.

Deletion requirements may use Before state and After state instead of
Input/Output.

## Verification Rules

Use `docs/reference/verification-contract.md` for Verify-type evidence. Broad
suite commands are weak evidence unless they include a feature-specific oracle
or filter. When the requirement describes specific observable behavior (concrete
Given/When/Then with values), the Verify command must include a feature-specific
filter, test name, or grep pattern. A bare `npm test` or `pytest` without
filtering is insufficient for feature-scoped requirements.

Acceptance criteria must describe observable behavior. Do not mention private
function names, class names, variables, or implementation-only files in
Given/When/Then.

`Automatable: false` requires `/prepare_execute` to replace the criterion with an
automated probe. For `api` and `e2e`, missing automation blocks execution.

## Vague Language Ban

Spec text outside code blocks and blockquotes must not use undefined vague
phrases such as:

- handle appropriately.
- if necessary.
- etc.
- properly.
- correctly.
- optimize without a metric.
- preferably.
- as appropriate.

Replace with concrete conditions and observable results.

## Re-export Awareness

When a requirement modifies a module whose symbols are re-exported through a
barrel file, package `__init__`, or equivalent, include the re-exporting module
in Impact scope.

## ADR Rules

Use the ADR policy in `docs/reference/architecture-readiness-contract.md`.

When ADRs are required:

- Create one ADR per accepted decision under `docs/decisions/`.
- Add links to `docs/decisions/README.md`.
- Add links to `docs/INDEX.md`.
- Commit ADRs with the spec.

ADR template:

```markdown
# ADR-NNN: Decision title

## Status
Accepted

## Context
Forces, constraints, lifecycle stage, ASRs.

## Decision
Chosen approach.

## Consequences
- Positive:
- Negative:
- Follow-up review trigger:
```

## Verify Script

On spec commit, generate `<spec-basename>.verify.sh` when the spec has Verify
commands.

Rules:

- Extract Verify commands from the spec.
- If none exist, warn.
- Wrap server-dependent `api` and `e2e` commands with configured start, health,
  and stop commands when available.
- Document external-service skips explicitly.
- Commit the script with the spec.

## Docs Index

Add the spec to `docs/INDEX.md`:

```markdown
## Specs
- [YYYY-MM-DD-topic-design](specs/YYYY-MM-DD-topic-design.md): [derived] design document
```

## Review Loops

Dispatch reviewers through `docs/reference/dispatch-protocol.md`:

- `ezpowers:spec-reviewer` receives the spec path.
- `ezpowers:architecture-reviewer` receives spec path, architecture reference
  path, and config path.
- `ezpowers:frontend-experience-reviewer` receives the spec path, config path,
  frontend design artifact, and post-spec audit result when UI is present.

Parse only verdict headers:

- `## Verdict: PASS`
- `## Verdict: FAIL`
- `## Verdict: PASS_WITH_ISSUES` when supported by the dispatch protocol.

Fresh re-dispatch after each fix. Do not pass previous reviewer output into the
new review. Track issue keys privately for oscillation detection.

## Phase And Audit Completion

After reviewers pass and the user approves:

- Mark spec `complete`.
- Set spec `artifact` to the spec path.
- Set `completed_at`.
- Keep plan `pending`.
- Dispatch `ezpowers:workflow-runner` for `internal pipeline audit` with
  invocation mode `post-spec`, working directory project root, spec artifact,
  and architecture reference artifacts.

Proceed to `/prepare_execute` only when audit status is `PASS` or `WARN`.
