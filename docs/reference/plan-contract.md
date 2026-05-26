# Plan Contract

This reference contains the plan structure and review details that do not
belong in the `/prepare_execute` controller prompt.

## Source Contracts

- `docs/reference/mattpocock-harness-adapter.md`
- `docs/reference/spec-contract.md`
- `docs/reference/architecture-readiness-contract.md`
- `docs/reference/verification-contract.md`
- `docs/reference/ui-verification-adapter-contract.md`
- `docs/reference/app-delivery-contract.md`
- `docs/reference/dispatch-protocol.md`
- `docs/reference/reviewer-placement-contract.md`
- `docs/reference/domain-language.md`

## Preflight

Require:

- `.harness/config.json`.
- `AGENTS.md`.
- Spec artifact from argument, phase state, or latest spec by date prefix.
- `phases/index.json` audit status `PASS` or `WARN`.
- Architecture reference when the spec has architecture sections.

If audit is missing or `FAIL`, route to `internal pipeline audit`. If no spec exists,
route to `/spec`.

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

Clarify one question at a time. Return to `/spec` when requirements or
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

## Experience/Delivery Matrix

Add this section when the spec contains App Experience And Delivery Baseline:

```markdown
## Experience/Delivery Matrix

| Surface | Requirements | Tasks | Verify |
|---------|--------------|-------|--------|
| UI route `/settings` | R1, R2 | T1, T3 | `pnpm test:e2e --grep settings` |
| API `PATCH /settings` | R2 | T2 | `pnpm test:api --grep settings` |
| Preview deploy | R3 | T4 | `vercel deploy --prebuilt --yes` |
```

Rules:

- Every surface from the spec baseline appears or is marked `omitted by user`
  with the accepted risk.
- UI rows include viewport, view wiring, browser/e2e, or visual evidence.
- API rows include status, payload, auth/session, and error-shape evidence.
- Package/deploy rows include build artifact, readiness, and rollback evidence.
- Matrix rows without mapped tasks or non-trivial Verify commands block
  execution.

## UI Verification Adapter Tasks

When `.harness/config.json` has `ui_verification.required: true`, every UI task
must include the selected adapter command or a task-local equivalent that
preserves the same user-observable oracle.

If the adapter is missing, not installed, or cannot run in the project
environment, add a prerequisite task before feature implementation:

```markdown
### Task 0: Install UI Verification Adapter {verification}

**Completion criteria (from spec):**
- [ ] Given: the configured UI surface / When: the adapter smoke command runs /
  Then: the adapter can assert visible UI behavior / Verify: `<adapter smoke>`

**UI verification adapter:** <capability, adapter, command, oracle>
```

Do not replace a UI acceptance criterion with a lower-level test unless
`docs/reference/ui-verification-adapter-contract.md` says the observable oracle
is equivalent.

## Structural Invariants

Add this section when ASRs, architecture rules, or project rules are verifiable:

```markdown
## Structural Invariants

| ID | Rule | Source | Verification |
|----|------|--------|-------------|
| SI-1 | DB module must not import API module | architecture.md | `command` |
```

Do not invent invariants when no rule source exists.

## Task Categories

- `skeleton`: Minimal runnable vertical slice through a real entry point.
  Wires WM-EP and WM-REG items from the spec's Wiring Map with real (not stub)
  minimal implementations. Must pass runtime smoke AND prove one feature path
  via its Verify command. Maps to at least one spec requirement.
- `feature`: Extends the skeleton with real behavior. Default category.
- `wiring`: Explicitly connects components from different feature tasks when
  implicit registration is insufficient.
- `integration-test`: Validates cross-task integration. Maps to Integration
  Contract Matrix milestones.

Category appears in the task header:

    ### Task 1: Project Skeleton [R1] {skeleton}

Skeleton tasks are vertical slices — they must map to a spec requirement in
the Coverage Matrix, not be requirement-free scaffolding. Assign `skeleton`
to Task 1 when the plan produces an executable artifact and the project has
no existing runnable app. Plans for existing runnable projects may omit the
skeleton.

## Task Shape

Tasks are independently grabbable vertical slices. Use this template:

```markdown
### Task N: Name [R1, R3] {feature}

**ASR:** ASR-1 or none
**Surface:** ui | api | data | package | deploy | docs | none
**Files:**
- Create: `path`
- Modify: `path`
- Test: `path`

**TDD Slice Contract:** Public interface: ...; Behavior under test: ...; Test oracle: ...; Required setup/fixtures: ...; Minimal implementation boundary: ...; Non-goals: ...; Missing-info handling: report NEEDS_CONTEXT/BLOCKED, do not guess.

**Impact scope:**
- (a) Reference breakage: `path` reason
- (b) Call site info: `path` reason
- (c) Code preservation: `path` reason

**Operational decisions:** Error handling: [pattern from baseline] | Logging: [strategy] | Config: [approach] | Init order: [relevant entry] | or `none applicable`
**Depends on:** Task N or none
**File overlap with:** Task N or none
**Wiring handoff:** (mandatory when task publishes routes, DI tokens, events, exports, or registrations consumed downstream; references WM IDs)
  WM-REG1: DI token `IFooService` registered in `startup.ts`
  WM-C1: Route `/api/foo` added in `routes.ts`, contract: `GET /api/foo -> FooResponse`

**Completion criteria (from spec):**
- [ ] Given: ... / When: ... / Then: ... / Verify: `command`

**Verification method:** Run the relevant Verify command.
**Runtime verification (executable artifacts only):** `command`
**View wiring verification (view tasks only):** `command`
**Delivery verification (package/deploy tasks only):** `command`
**Wiring probe (executable artifacts, new module tasks):**
  Entry point: `path` | Module: `path` | Probe type: `import-chain` | `runtime-load` | `e2e-touch`
  Verify: `command`

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
- Tasks creating new modules in executable artifacts require a Wiring Probe
  (`**Wiring probe:**`) per `docs/reference/verification-contract.md`
  § Incremental Wiring Probe. Probe type should match the WM-REG entry's
  recommended strategy from the spec's Wiring Map.
- View tasks require view wiring verification from
  `docs/reference/verification-contract.md`.
- UI tasks require viewport/e2e or visual verification from
  `docs/reference/app-delivery-contract.md` when the user-facing surface is
  rendered in a browser, mobile shell, or desktop window.
- Package and deploy tasks require Delivery verification with build artifact,
  readiness, and rollback evidence.

## Integration Contract Matrix

Required when the plan has two or more tasks and produces an executable
artifact (`cli`/`server`/`desktop`). Optional for single-task plans or
`docs`/`library`. Also required when task outputs are consumed by other
tasks, when three or more layers connect, or when UI displays non-UI data.

```markdown
## Integration Contract Matrix

| WM ID | Producer Task | Consumer Task | Contract | First Connected | Verify |
|-------|---------------|---------------|----------|-----------------|--------|
| WM-C1 | T1 | T3 | `CommandHandler.execute(args): Result` | T3 | `command` |
| WM-REG1 | T1 | T2 | DI token `IFooService` | T2 | `command` |
```

Rules:

- Every WM-C and WM-REG item from the spec's Wiring Map must appear.
- Unmapped WM items indicate a plan gap (plan-reviewer FAIL).
- Add an integration milestone task after the last component task when needed.
- Include runtime contracts discovered during planning: URL paths, message
  formats/schemas (JSON shape, protobuf, GraphQL type), event names, shared
  configuration keys, CLI flags/subcommands, and file format contracts that one
  task produces and another consumes, even when no file overlap or `Depends on`
  marker exists.
- Detection rule: when Task A's Create/Modify files or Wiring handoff expose a
  URL, route, event, config key, message schema, or CLI flag, and Task B's AC
  text, Verify commands, or files reference the same value, an ICM entry is
  required.

### Data Flow Trace

When the spec contains WM-DF entries, at least one plan task must have a Verify
command that asserts data arriving at the entry point reaches the output with
correct transformation. A milestone task or the Full-Feature Wiring Gate should
exercise at least one WM-DF path end-to-end. Plans with WM-DF entries but no
data flow verification is flagged by internal pipeline audit D5.

## Full-Feature Wiring Gate

Add when:

- Plan has connected tasks.
- Work changes multiple layers.
- Work creates or modifies an executable artifact.
- Work crosses UI, API, packaging, or deployment surfaces.
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
**App Delivery:** surface kind, packaging artifact, deployment target.
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
- Dispatch `ezpowers:workflow-runner` for `internal pipeline audit` with
  invocation mode `post-prepare_execute`, working directory project root, spec
  artifact, and plan artifact.

Proceed to `/choice_execute` only when audit status is `PASS` or `WARN`.
