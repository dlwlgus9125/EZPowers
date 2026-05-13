# Spec Contract

This reference contains the spec-writing and review details that do not belong
in the `/brainstorm` controller prompt.

## Source Contracts

- `docs/reference/mattpocock-harness-adapter.md`
- `docs/reference/architecture-readiness-contract.md`
- `docs/reference/verification-contract.md`
- `docs/reference/dispatch-protocol.md`
- `docs/reference/domain-language.md`

## Preflight

`/brainstorm` requires `.harness/config.json`. If it is missing, route to
`/setup`.

When `phases/index.json` exists:

- Set `current_phase` to `brainstorm`.
- Set brainstorm status to `in_progress`.
- Delete stale `audit` data.

## Design Flow

Use this order:

1. Read project context.
2. Declare assumptions.
3. Ask one question at a time.
4. Produce an architecture baseline.
5. Confirm the architecture baseline.
6. Run `grill-with-docs`.
7. Extract requirements.
8. Confirm requirements.
9. Write spec, ADRs, verify script, and docs index entry.
10. Run spec and architecture review loops.
11. Get user approval.
12. Update phase state.
13. Dispatch `/pipeline-audit` in `post-brainstorm` mode.

Small work may have a short design, but it still follows this order.

## Architecture Baseline

Every spec starts with these sections before requirements:

- Architecture Baseline.
- ASR Ledger.
- Option Matrix.
- Lifecycle And Operations.
- Quality Budgets.
- Decision Log.
- Extracted Requirements.

The architecture baseline must identify modules, interfaces, allowed
dependencies, forbidden dependencies, data ownership, selected approach, and
rejected options.

Each ASR must affect structure, lifecycle, performance, reliability, security,
compatibility, cost, or operations. If a quality budget is not declared, state
`none declared` and explain the risk.

## Architecture Approval Text

Use this shape before requirement extraction:

```markdown
Architecture baseline:
- Selected approach:
- ASRs:
- Lifecycle:
- Quality budgets:
- ADR candidates:

Confirm this architecture baseline before I extract requirements.
```

After confirmation, invoke `grill-with-docs`. Any unresolved issue blocks requirement
extraction until the design is revised and reconfirmed.

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

## Requirement Section Template

Each requirement section uses:

```markdown
### R[N]: Title

**ASR:** ASR IDs or none
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
or filter.

Acceptance criteria must describe observable behavior. Do not mention private
function names, class names, variables, or implementation-only files in
Given/When/Then.

`Automatable: false` requires `/plan` to replace the criterion with an
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

Parse only verdict headers:

- `## Verdict: PASS`
- `## Verdict: FAIL`
- `## Verdict: PASS_WITH_ISSUES` when supported by the dispatch protocol.

Fresh re-dispatch after each fix. Do not pass previous reviewer output into the
new review. Track issue keys privately for oscillation detection.

## Phase And Audit Completion

After reviewers pass and the user approves:

- Mark brainstorm `complete`.
- Set brainstorm `artifact` to the spec path.
- Set `completed_at`.
- Keep plan `pending`.
- Dispatch `ezpowers:workflow-runner` for `/pipeline-audit` with invocation
  mode `post-brainstorm`.

Proceed to `/plan` only when audit status is `PASS` or `WARN`.
