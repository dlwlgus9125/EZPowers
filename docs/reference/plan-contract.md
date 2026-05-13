# Plan Contract

This reference contains the plan structure and review details that do not
belong in the `/plan` controller prompt.

## Source Contracts

- `docs/reference/mattpocock-harness-adapter.md`
- `docs/reference/spec-contract.md`
- `docs/reference/architecture-readiness-contract.md`
- `docs/reference/verification-contract.md`
- `docs/reference/dispatch-protocol.md`
- `docs/reference/domain-language.md`

## Preflight

Require:

- `.harness/config.json`.
- `AGENTS.md`.
- Spec artifact from argument, phase state, or latest spec by date prefix.
- `phases/index.json` audit status `PASS` or `WARN`.
- Architecture reference when the spec has architecture sections.

If audit is missing or `FAIL`, route to `/pipeline-audit`. If no spec exists,
route to `/brainstorm`.

When planning starts, set plan `in_progress` and remove stale audit data.

## Assumptions

After reading the spec and architecture sections, declare assumptions:

```markdown
ASSUMPTIONS ABOUT THIS SPEC:
1. Interpretation assumption.
2. Technical approach assumption.
3. Module or boundary assumption.
-> Correct me if any of these are wrong.
```

Clarify one question at a time. Return to `/brainstorm` when requirements or
architecture are insufficient.

## Coverage Matrix

Every plan includes:

```markdown
## Coverage Matrix

| Requirement | Related Tasks |
|-------------|---------------|
| R1: Title (ASR-1) | T1, T3 |
| R2: Title (ASR: none) | T2 |
```

Rules:

- Every spec requirement appears.
- Every requirement maps to at least one task.
- ASR IDs or `ASR: none` appear in the Requirement cell.
- Unmapped requirements require a task or explicit user-approved omission.
- Tasks without requirement mapping are suspicious and must be justified.

## Structural Invariants

Add this section when ASRs, architecture rules, or project rules are verifiable:

```markdown
## Structural Invariants

| ID | Rule | Source | Verification |
|----|------|--------|-------------|
| SI-1 | DB module must not import API module | architecture.md | `command` |
```

Do not invent invariants when no rule source exists.

## Task Shape

Tasks are independently grabbable vertical slices. Use this template:

```markdown
### Task N: Name [R1, R3]

**ASR:** ASR-1 or none
**Files:**
- Create: `path`
- Modify: `path`
- Test: `path`

**TDD Slice Contract:** Public interface: ...; Behavior under test: ...; Test oracle: ...; Required setup/fixtures: ...; Minimal implementation boundary: ...; Non-goals: ...; Missing-info handling: report NEEDS_CONTEXT/BLOCKED, do not guess.

**Impact scope:**
- (a) Reference breakage: `path` reason
- (b) Call site info: `path` reason
- (c) Code preservation: `path` reason

**Depends on:** Task N or none
**File overlap with:** Task N or none

**Completion criteria (from spec):**
- [ ] Given: ... / When: ... / Then: ... / Verify: `command`

**Verification method:** Run the relevant Verify command.
**Runtime verification (executable artifacts only):** `command`

- [ ] Step 1: Write the failing test.
- [ ] Step 2: Run it and observe failure.
- [ ] Step 3: Write minimal implementation.
- [ ] Step 4: Run the test and observe pass.
- [ ] Step 5: Run Verify command.
- [ ] Step 6: Commit.
```

## TDD Slice Rules

- One behavior, one red-green cycle.
- Public interface is the test surface.
- Do not write all tests first and all implementation later.
- Do not test private shape when observable behavior is available.
- Keep non-goals explicit so implementers do not expand scope.

## Impact Scope Rules

Impact scope is required for tasks that modify files. Create-only tasks are
exempt.

Classify:

- Reference breakage: files that would break without modification.
- Call site info: behavior-dependent callers that do not need modification.
- Code preservation: validation, security, error handling, compatibility, or
  other defensive behavior that must survive.

When uncertain, classify as reference breakage.

## Completion Criteria Rules

- Copy relevant spec AC without weakening the behavior claim.
- Preserve Verify oracle strength when changing commands.
- Behavior-bearing tasks require a TDD Slice Contract.
- Executable entry-point tasks require runtime verification.
- View tasks require view wiring verification from
  `docs/reference/verification-contract.md`.

## Integration Pipeline Matrix

Add when task outputs are consumed by other tasks, when three or more layers
connect, when UI displays non-UI data, or when an executable artifact needs two
or more components.

```markdown
## Integration Pipeline Matrix

| Pipeline | Flow | First Connected | Contract Oracle | Integration Verify |
|----------|------|-----------------|-----------------|-------------------|
| P1 | A -> B -> C | T3 | emitted state equals consumed state | `command` |
```

Add an integration milestone task after the last component task when needed.

## Full-Feature Wiring Gate

Add when:

- Plan has connected tasks.
- Work changes multiple layers.
- Work creates or modifies an executable artifact.
- Task title or AC mentions integration, milestone, wiring, route,
  registration, binding, subscription, or end-to-end.

Template:

```markdown
## Full-Feature Wiring Gate

**Required:** yes
**Verify-type:** e2e
**Covers:** T1 -> T2 -> T3, P1
**Expected observation:** Observable result from the user's entry point
**Verify:** `single automated command`
```

The command must not be empty, placeholder-only, `echo`, `true`, or only a
single-component unit test. If no command exists, add a task that creates the
probe before implementation.

## Agent Assignment

```markdown
## Agent Assignment

| Task | Agent | Mode | Reason |
|------|-------|------|--------|
| T1 | subagent | isolated | Independent module creation |
```

Mode values are `isolated`, `sequential`, and `parallel`.

## Plan Artifact

Save to the plan location from `AGENTS.md`, defaulting to `docs/plans/`.

Filename: `YYYY-MM-DD-feature-name.md`.

Header:

```markdown
# Feature Name Implementation Plan

**Goal:** One sentence.
**Architecture:** Two to three sentences.
**ASR Summary:** ASRs and quality targets.
**Tech Stack:** Core technologies.
**Spec:** spec path.
```

Update `docs/INDEX.md`:

```markdown
## Plans
- [YYYY-MM-DD-feature-name](plans/YYYY-MM-DD-feature-name.md): [derived] implementation plan
```

## Review Loop

Dispatch `ezpowers:plan-reviewer` through
`docs/reference/dispatch-protocol.md` with plan path and spec path.

Fresh re-dispatch after each fix. Track issue keys privately. Escalate on
oscillation or retry limits.

## Phase And Audit Completion

After plan approval:

- Mark plan `complete`.
- Set plan `artifact` to the plan path.
- Set `completed_at`.
- Keep build `pending`.
- Dispatch `ezpowers:workflow-runner` for `/pipeline-audit` with invocation
  mode `post-plan`.

Proceed to `/choiceexecutor` only when audit status is `PASS` or `WARN`.
