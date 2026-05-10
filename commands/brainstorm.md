---
description: Run guided design session to produce spec documents
disable-model-invocation: true
allowed-tools: [Bash, Read, Write, Agent, AskUserQuestion]
---

# /brainstorm — Spec Document Generation

Turn ideas into spec documents through guided conversation. No implementation code is written.

<HARD-GATE>
Do not perform any implementation until the user approves the design document. No matter how simple the project seems, follow the order: design -> approval -> plan.
</HARD-GATE>

## Anti-Pattern: "This is too simple for a design"

Every project goes through this process. Including simple utils and config changes. "Simple" projects with unexamined assumptions cause the most rework. The design can be short, but it must exist and receive user approval.

## Process Flow

```
Understand project context
  -> Build architecture baseline (ASR, lifecycle, quality budgets)
  -> Ask one question at a time (scope, constraints, success criteria)
  -> Propose 2-3 approaches + recommendation
  -> Record architecture decision candidates + ADR triggers
  -> Present design section by section -> user approval
  -> Grill-me gate (stress-test design before requirements)
  -> Extract requirements (R1, R2, ...)
  -> User confirms requirements
  -> Write spec document + commit
  -> Spec review loop + architecture review loop (subagents)
  -> User spec review
  -> Workflow-runner invokes /pipeline-audit
  -> Next step: /plan if audit PASS/WARN
```

## 1. Understand Project Context

Read current project state first:
- `AGENTS.md` (steering information)
- `.harness/config.json` (project settings)
- `docs/reference/architecture.md` (canonical architecture)
- `docs/reference/conventions.md` (rules and boundaries)
- `docs/decisions/README.md` and existing ADRs when present
- Directory structure, recent git changes
- Existing docs under `docs/`

If `.harness/config.json` is missing, direct the user to run `/setup` first and stop.

If `phases/index.json` exists:
1. Update the brainstorm phase to `in_progress`:
   ```json
   { "current_phase": "brainstorm", "phases": { ..., "brainstorm": { "status": "in_progress" } } }
   ```
2. Delete the `audit` field if present (previous audit results are stale after spec changes)

## 2. Interactive Design

**Questioning rules:**
- **One question at a time** — do not overwhelm the user
- **Domain-defining questions before implementation questions** — "What problem are you solving?" precedes "What tech stack?"
- Present choices when possible
- Focus on purpose, constraints, success criteria
- Do not re-ask what is already known

**Scope check:**
- If the request spans multiple independent subsystems, suggest decomposition immediately
- If decomposition is needed, start with the first sub-project
- Each sub-project gets its own spec -> plan -> build cycle

**Approach proposal:**
- Present 2-3 approaches with tradeoffs
- Lead with the recommended option and explain why

**Design presentation:**
- Present in sections (architecture, components, data flow, error handling, testing)
- After each section: "Does this look right?"
- Scale explanation depth to complexity

**Design for isolation and clarity:**
- Each unit has a clear purpose, well-defined interface, independently testable
- Can you understand its role without knowing internals? Can internals change without breaking consumers?

**Working with existing codebases:**
- Explore existing structure first and follow existing patterns
- Include improvements only if they affect the current task; no unrelated refactoring

### Architecture Inception Gate

Before requirement extraction, produce and get user approval for an architecture
baseline. This gate is mandatory for greenfield, brownfield, refactor, and
bug-fix requests. Keep it short for small work, but do not skip it.

Required outputs:
- **ASR Ledger:** Architecturally Significant Requirements with measurable effect on structure, lifecycle, performance, reliability, security, compatibility, cost, or operations.
- **Option Matrix:** 2-3 architecture approaches with tradeoffs, selected approach, rejected approaches, and reason.
- **Lifecycle Plan:** startup/shutdown, deployment/runtime, migration path, backward compatibility, observability, recovery, and ownership.
- **Quality Budgets:** concrete latency, memory, throughput, bundle size, token/cost, or supportability budgets. If absent, state `none declared` and explain the risk.
- **Boundary Map:** modules/components, public interfaces, allowed dependencies, forbidden dependencies, and data ownership.
- **Decision Log:** ADR candidates for hard-to-reverse, surprising, or high-tradeoff choices.

Questioning rules for this gate:
- Ask one architecture decision at a time.
- Start from discovered repo facts. Ask only for product intent or tradeoffs not visible in files.
- Do not ask for implementation details before lifecycle, boundary, and quality priorities are known.
- If user asks for a quick fix that crosses a boundary, pause and explain the boundary risk before continuing.

Approval text:

```
Architecture baseline:
- Selected approach: ...
- ASRs: ASR-1 ...
- Lifecycle: ...
- Quality budgets: ...
- ADR candidates: ...

Confirm this architecture baseline before I extract requirements.
```

After the user confirms the architecture baseline, invoke the `grill-me` skill before requirement extraction. Any unresolved issue blocks progress: revise the design or architecture baseline, confirm the affected section with the user, and rerun `grill-me` until the gate is clear.

## 3. Assumption Declaration

Explicitly declare assumptions before proposing a design:

```
ASSUMPTIONS:
1. [Assumption about scope/tech/constraints/intent]
2. [Assumption about existing code behavior or system boundaries]
-> Correct me if any of these are wrong.
```

If assumptions are wrong, revise the affected design.

## 4. Requirement Extraction

Once the user approves the design, extract all requirements from the conversation:

```
## Extracted Requirements

- R1: [Specific requirement]
- R2: [Specific requirement]
...

Anything missing or to change?
```

Rules:
- Unique ID per requirement (R1, R2, ...)
- Specific, actionable statements — not summaries
- Iterate until the user explicitly approves
- If requirements exceed 10, suggest sub-project decomposition

**Hard gate failure:** If the user points out missing requirements 3 consecutive times → "It seems there are many undiscussed requirements. Shall we return to the questioning phase for deeper exploration?"

## 5. Spec Document Writing

Write the spec document once requirements are confirmed.

**Save location:** Value of `spec location:` in `AGENTS.md`. Default: `docs/specs/`.
**Filename:** `YYYY-MM-DD-<topic>-design.md`

### Architecture Sections (required)

Every spec begins with these sections before `## Extracted Requirements`:

```markdown
## Architecture Baseline

**Selected approach:** [short name]
**Summary:** [2-4 sentences]
**Existing constraints:** [repo/docs/config facts]
**Boundary map:** [modules, public interfaces, allowed dependencies, forbidden dependencies]

## ASR Ledger

| ASR | Quality Attribute | Measurable Target | Design Impact | Verification |
|-----|-------------------|-------------------|---------------|--------------|
| ASR-1 | Maintainability | [metric or rule] | [boundary or module effect] | `[command or review check]` |

## Option Matrix

| Option | Tradeoffs | Selected |
|--------|-----------|----------|
| A | [pros/cons] | yes/no |

## Lifecycle And Operations

- Lifecycle stage:
- Startup/shutdown:
- Deployment/runtime:
- Migration/compatibility:
- Observability:
- Recovery:
- Ownership:

## Quality Budgets

- Performance:
- Reliability:
- Security:
- Cost:
- Maintainability:

## Decision Log

- ADR required: yes/no
- ADR candidates:
- Decisions deferred:
```

Rules:
- Each R must reference relevant ASR IDs or state `ASR: none`.
- Any hard-to-reverse, surprising, or high-tradeoff choice requires an ADR candidate.
- A spec with `ADR required: yes` must create an ADR file under `docs/decisions/` in the same commit.

### Extracted Requirements Section (required)

The spec file must include the requirement list from Section 4 at the top:

```markdown
## Extracted Requirements

- R1: [Requirement title]
- R2: [Requirement title]
...
```

This section is the basis for spec reviewer's requirement coverage check. `/plan`'s Coverage Matrix references this list. Omission causes spec review FAIL.

### Per-Requirement Structure

Each requirement follows this structure:

```markdown
### R[N]: [Title]

**ASR:** [ASR IDs or none]
**Input:** [Trigger or input]
**Behavior:** [Step-by-step behavior description]
**Output:** [Observable result]
**Impact scope:**
- [Module/component]: [Impact]
**Acceptance criteria:**
- [ ] Given: [Precondition — observable state before action]
      When: [Action performed by user or system]
      Then: [Observable result]
      Verify: `[Shell command where exit 0 = pass]`
      Verify-type: [api | e2e | cli | lib | data | pure]
      Automatable: [true | false]
**Edge cases:**
- [Condition]: [Expected behavior]
```

**Hard gate:** Each R requires all 7 fields: ASR, Input, Behavior, Output, Impact scope, Acceptance criteria, Edge cases. Missing any = FAIL.

### Implementation Term Ban

Given/When/Then text must not contain implementation terms (function names, class names, internal variable names). Describe only user actions and observable results.

Example: ~~"When `handleClick()` is called"~~ -> "When the user clicks the submit button"

### Pure-type Exception

For Verify-type `pure`, Input/Transform/Output format is allowed instead of Given/When/Then:

```markdown
- Input: [Input value]
  Transform: [Pure transformation description]
  Output: [Expected output]
  Verify: [Verification command]
  Verify-type: pure
```

### Verify-type Guide

| Verify-type | When to use | Example Verify |
|-------------|-------------|----------------|
| `api` | REST/GraphQL endpoint behavior | `curl -s localhost:3000/api/users \| jq '.status'` returns `200` |
| `e2e` | User-facing UI flow | `playwright test tests/login.spec.ts` passes |
| `cli` | CLI command behavior | `mycli --version` prints `1.2.0` |
| `lib` | Run consumer code via inline script | `node -e "const {parse} = require('./lib'); assert(parse('k=v').k === 'v')"` |
| `data` | Data migration, schema, ETL | Query `SELECT count(*) FROM users` returns expected count |
| `pure` | Pure function, no side effects | `assertEquals(add(1, 2), 3)` |

### Automatable Field

- `Automatable: true` (default, omit if true) — the Verify command can run fully automated
- `Automatable: false` — the AC requires human judgment (visual inspection, UX evaluation). `/plan` must detect these and replace with an automated probe (process health, screenshot + vision, headless test). If no automated replacement exists, `/choiceexecutor` treats the missing Verify command as FAIL and re-dispatches the implementer to write one.
- **`Automatable: false` + `Verify-type: e2e`** = mandatory probe replacement in `/plan` (linked to /choiceexecutor's "no manual verification" rule)

### Re-export Awareness

If a symbol from an affected module is re-exported by another module (barrel files, `__init__.py`, etc.), include the re-exporting module in Impact scope.

### ADR Generation

When the Decision Log says `ADR required: yes`, create one ADR per accepted
architecture decision under `docs/decisions/`:

```markdown
# ADR-NNN: [Decision title]

## Status
Accepted

## Context
[forces, constraints, lifecycle stage, ASRs]

## Decision
[chosen approach]

## Consequences
- Positive:
- Negative:
- Follow-up review trigger:
```

Add the ADR link to `docs/decisions/README.md` and `docs/INDEX.md`.

### Deletion Requirement Variant

For deletion requirements (e.g., "R5: Remove feature X"):
- Use "Before state" / "After state" instead of Input/Output
- AC: conditions proving the feature is fully removed

### Banned Expressions

The following expressions are **banned** in spec documents. Presence causes automatic FAIL:

| Banned (Korean) | Banned (English) | Reason | Alternative |
|-----------------|------------------|--------|-------------|
| 적절히/적절하게 처리한다 | handle appropriately | Implementer must guess | Describe exact behavior |
| 필요한 경우/필요 시 | if necessary/if needed | Condition undefined | Specify exact condition |
| 등등/기타/등 | etc./and so on | Unbounded scope | Full list or "this list is exhaustive" |
| 올바르게/정상적으로 | properly/correctly | No definition | Define via AC |
| 효율적으로/최적화하여 | efficiently/optimized | Unmeasurable | Specific metric or remove |
| 가능하면/가급적 | if possible/preferably | MUST vs MAY unclear | Specify MUST or MAY |
| 상황에 맞게/상황에 따라 | as appropriate/depending on | Decision deferred | Enumerate situations and responses |

**Exception:** Expressions inside code blocks (```) or blockquotes (> ) are exempt.

**Hard gate failure loop:** Banned expression found -> auto-replace with specific language -> recheck. After 3 failures, ask the user for the specific behavior of that sentence.

### Verify Script Generation

On spec commit, also generate `<spec-basename>.verify.sh`:
1. Extract all Verify commands from the spec
2. If 0 Verify commands: skip generation and warn
3. Server-dependent commands (api, e2e): wrap with server start/stop
4. External service-dependent commands: add `|| echo "SKIP: ..."` handling
5. Include in the same commit as the spec

### INDEX.md Update

On spec commit, add the spec entry to `docs/INDEX.md`:

```markdown
## Specs
- [YYYY-MM-DD-<topic>-design](specs/YYYY-MM-DD-<topic>-design.md): [authority] design document
```

If a Specs section exists, add the entry. Otherwise, create the section.

## 6. Spec + Architecture Review Loop

After writing the spec:

1. Dispatch `ezpowers:spec-reviewer` plugin agent via `subagent_type`. Pass only dynamic info in the prompt:

   ```
   Agent tool:
     subagent_type: "ezpowers:spec-reviewer"
     description: "Review spec document"
     prompt: |
       **Spec to review:** <absolute path to spec file>
   ```

2. Parse reviewer result by `## Verdict: PASS` or `## Verdict: FAIL` header only. Ignore `PASS`/`FAIL` strings elsewhere. **If Verdict header is missing or malformed:** treat as `FAIL`, but on 2 consecutive missing Verdict headers, escalate to user ("Reviewer is not returning verdicts in the standard format.")
3. Issues found -> fix issues -> fresh subagent re-dispatch (same prompt, do not pass previous review results)
4. Maintain a private issue log (not shared with reviewer) — for oscillation detection. Log each issue by `{section}:{check_number}` key (e.g., `R2:structural_completeness`, `R3:banned_expression`). This is the oscillation matching "category".
5. **Oscillation check (from iteration 3):** If a current issue's `{section}:{check_number}` key also appeared in 2+ prior iterations -> immediately escalate to user
6. **Tiered escalation:** 3 rounds without approval -> warn user. 5 rounds -> stop.

### Architecture Reviewer Dispatch

The spec is not approved until both reviewers pass.

Dispatch `ezpowers:architecture-reviewer` after writing or changing the spec:

```
Agent tool:
  subagent_type: "ezpowers:architecture-reviewer"
  description: "Review architecture baseline"
  prompt: |
    **Spec to review:** <absolute path to spec file>
    **Architecture reference:** <absolute path to docs/reference/architecture.md>
    **Config:** <absolute path to .harness/config.json>
```

Apply the same verdict parsing, fresh re-dispatch, oscillation, and escalation
rules used for `spec-reviewer`. Log architecture issues by
`architecture:{section}:{check_number}`.

## 7. User Spec Review

After passing the spec and architecture review loops:

> "Spec written and committed at `<path>`. Review it and let me know if any changes are needed."

After user approval, update `phases/index.json`:
- brainstorm: `status: "complete"`, `artifact: "<spec file path>"`, `completed_at: "<ISO 8601>"`
- plan: `status: "pending"` (verify unchanged)

Then dispatch `ezpowers:workflow-runner` to invoke
`/pipeline-audit` in `post-brainstorm` mode:

```
Agent tool:
  subagent_type: "ezpowers:workflow-runner"
  description: "Run post-brainstorm pipeline audit"
  prompt: |
    **Target command:** /pipeline-audit
    **Invocation mode:** post-brainstorm
    **Working directory:** <absolute project root>
    **Spec artifact:** <absolute path to spec file>
```

Status handling:
- `DONE` with audit `PASS` or `WARN`: next step is **`/plan`**.
- `DONE` with audit `FAIL`, or runner `FAIL`: return to `/brainstorm` using the runner's routing recommendations.
- `NEEDS_USER`: resolve the requested decision, then rerun the same workflow-runner dispatch.

## Common Rationalizations

| Rationalization | Reality |
|----------------|---------|
| "Too simple for a design" | See Anti-Pattern section. Design can be short but must exist. |
| "I already know what to build" | You know — the user may not. Confirm explicitly. |
| "Design slows us down" | Rework from misunderstood requirements is 5-10x slower than a 10-minute design conversation. |
| "Just one question then start" | One question ≠ understanding. Ask until you can predict the user's answers. |
| "User is in a rush, just code" | Delivering wrong code is slower than asking the right questions. |
| "Requirements are obvious from context" | Obvious to whom? State explicitly and get confirmation. |
| "Edge cases during implementation" | Discovering them during implementation means redesign. Find them now. |
| "Spec is detailed enough, no design needed" | Spec = WHAT, design = HOW. Both are needed. |

## Key Principles

- **One question at a time** — do not overwhelm with multiple questions
- **Prefer choices** — multiple-choice when possible, open-ended also OK
- **YAGNI** — remove unnecessary features from every design
- **Explore alternatives** — always propose 2-3 approaches before deciding
- **Incremental validation** — present design, get approval, then proceed
- **Stay flexible** — if it doesn't fit, go back and clarify

## Next Steps

After spec approval and commit:
- `ezpowers:workflow-runner` automatically invokes `/pipeline-audit` to verify spec completeness before planning
- Then proceed to `/plan` only when audit status is `PASS` or `WARN`
