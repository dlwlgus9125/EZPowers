---
description: Decompose spec into task plans with agent assignments
disable-model-invocation: true
allowed-tools: [Bash, Read, Write, Agent, AskUserQuestion]
---

# /plan — Task Sequencing

Take the spec from /brainstorm as input, decompose it into detailed tasks, and determine agent assignments. No code is written.

> **For agentic workers:** /choiceexecutor runs tasks from this plan via subagent-driven, harness, or inline execution. Steps are tracked with checkbox syntax.

## 1. Pre-flight Checks

Verify the following first:
1. `.harness/config.json` exists
2. `AGENTS.md` exists
3. Spec document exists (priority: argument > `phases/index.json` brainstorm.artifact > latest file from config `defaults.spec_location` directory selected by `YYYY-MM-DD` prefix date, descending; ties broken by filename descending)
4. Recent git changes
5. Architecture reference exists when the spec has architecture sections (`docs/reference/architecture.md`)
6. `phases/index.json` audit gate:
   - `audit.status` is `"FAIL"` → report `"pipeline-audit에서 미해결 항목 있음. 해결 후 /pipeline-audit 재실행하세요."` and stop
   - `audit` field is missing → report `"/pipeline-audit를 먼저 실행하세요."` and stop
   - `audit.status` is `"PASS"` or `"WARN"` → proceed

If missing, direct the user to the required step and stop:
- No config -> `/setup`
- No spec -> `/brainstorm`
- No audit or audit FAIL -> `/pipeline-audit`

If `phases/index.json` exists:
1. Update the plan phase to `in_progress`:
   ```json
   { "current_phase": "plan", "phases": { ..., "plan": { "status": "in_progress" } } }
   ```
2. Delete the `audit` field if present (previous audit results are stale after plan changes)

## 2. Read Spec + Architecture Baseline + Declare Assumptions

After reading the spec, also read its Architecture Baseline, ASR Ledger,
Option Matrix, Lifecycle And Operations, Quality Budgets, and Decision Log.
Then declare assumptions:

```
ASSUMPTIONS ABOUT THIS SPEC:
1. [Assumption about interpreting ambiguous requirements]
2. [Assumption about technical approach not stated in the spec]
3. [Assumption about module boundaries or existing code behavior]
-> Correct me if any of these are wrong.
```

Clarify unclear parts with the user briefly. One question at a time.

If the spec lacks architecture sections, return to `/brainstorm`. Do not write
a plan that forces implementation agents to invent architecture.

## Scope Check

If the spec covers multiple independent subsystems, suggest splitting into separate plans. Each plan must produce independently working, testable software.

## 3. File Structure Mapping

Before defining tasks, map files to create/modify:
- Clear responsibility per file — one file, one clear purpose
- Units have well-defined boundaries and interfaces
- Files that change together are grouped together
- For existing codebases, follow existing patterns
- Prefer small, focused files — large files signal overloaded roles

## 4. Coverage Matrix (required)

Every plan must include this matrix:

```markdown
## Coverage Matrix

| Requirement | Related Tasks |
|-------------|---------------|
| R1: [Title] (ASR-1) | T1, T3 |
| R2: [Title] | T2 |
```

Rules:
- All Rs from the spec must appear in the matrix
- Every R must map to at least one T
- ASR IDs from each R must appear in the Requirement cell or be listed as `ASR: none`
- R without a matching T: add a task or justify (user approval required)
- T without an R mapping: warn (possible unnecessary work)

**Hard gate:** Plan reviewer verifies. Missing matrix or unmapped R = FAIL.

## Structural Invariants (required when ASRs or architecture rules exist)

After the Coverage Matrix, extract verifiable invariants from the ASR Ledger,
Architecture Baseline boundary map, `docs/reference/architecture.md`, and
project rules (`.claude/rules/`, AGENTS.md constraints, CLAUDE.md rules).

```markdown
## Structural Invariants

| ID | Rule | Source | Verification |
|----|------|--------|-------------|
| SI-1 | DB layer must not import from API layer | ASR-1 / architecture.md | `grep -r "from.*api/" src/db/` returns no matches |
| SI-2 | Shared module has no runtime dependencies | architecture.md | `jq '.dependencies' shared/package.json` is empty |
```

Rules:
- Each invariant expressed as a verifiable command
- Source references the rule file/document
- If no project rules exist, omit this section — do not invent rules
- code-reviewer verifies after implementation
- ASR and boundary rules count as project rules for this section.

## 5. Task Decomposition Principles

Write each task assuming it runs in an independent agent session.

**Must follow:**
- One task, one clear goal
- Enough info in the task document alone to start work
- No external context references like "from the previous conversation"
- Specify relevant docs and file paths
- AC based on observable results

### Token Budget

- **Rule of thumb:** 100 lines ≈ 500-1000 tokens
- **Goal:** per-task context cost within ~25% of model context window
- **Split triggers:**
  - Task touches 5+ files
  - Task requires reading 10+ files
  - Mixes infrastructure changes + business logic
  - Mixes new file creation + modifying tightly coupled existing files

### Task Size

- Each step is 2-5 minute units (write test, run, implement, verify, commit)
- Do not mix infrastructure and business logic changes

### Task Structure

````markdown
### Task N: [Name] [R1, R3]

**ASR:** ASR-1, ASR-3 (or none)
**Files:**
- Create: `exact/path/to/file.py`
- Modify: `exact/path/to/existing.py:123-145`
- Test: `tests/exact/path/to/test.py`

**Impact scope:**
- (a) Reference breakage: [`path/to/consumer.py`] — imports `changed_function`; [`path/to/indirect.py`] — imports via re-export in `path/to/barrel.py`; [`path/to/caller.py`] — calls `modified_function` (signature change: added `timeout` param)
- (b) Call site info (reference only — no verdict impact): [`path/to/other.py:30`] — calls `modified_function` (behavioral dependency only)
- (c) Code preservation: [`path/to/existing.py:50-65`] — input validation logic, must be preserved

**Depends on:** Task N (if applicable)
**File overlap with:** Task N (if modifying the same file)

**Completion criteria (from spec):**
- [ ] (R1) Given: [condition] / When: [action] / Then: [result] / Verify: `[command]`

**Verification method:** Run spec's Verify commands (exit 0 = PASS)
**Runtime verification (executable artifacts only):** `<start-cmd> & sleep N && kill $! 2>/dev/null; test $? -eq 0` pattern for startup verification. Separate from build AC.

- [ ] **Step 1: Write the failing test**

```python
def test_specific_behavior():
    # Given: [precondition from completion criteria]
    result = function(input)
    # Then: [expected outcome]
    assert result == expected
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/path/test.py::test_name -v`
Expected: FAIL

- [ ] **Step 3: Write minimal implementation**

- [ ] **Step 4: Run test to verify it passes**

- [ ] **Step 5: Run Verify command**

```bash
[Verify command from completion criteria]
```
Expected: exit 0

- [ ] **Step 6: Commit**
````

### Impact Scope Rules

- Required only for tasks with Modify files. Create-only tasks are exempt.
- **(a) Reference breakage:** Files that break without modification after the change.
  - Direct imports + 1-level re-export chains
  - Signature changes (parameter add/remove/type change, return type, exceptions, renames)
  - Re-export patterns: JS/TS `export { X } from`/`export * from`, Python `__init__.py`, CommonJS `module.exports = require(...)`
  - When uncertain, classify as (a) (safety > efficiency)
- **(b) Call site info:** Depends only on behavior, no modification needed. "reference only" marker. Omission does not cause FAIL.
- **(c) Code preservation:** Defensive code within modification scope (validation, error handling, auth). If none, state "No defensive code patterns found".

### Completion Criteria Rules

- Copy spec AC **verbatim** — no paraphrasing
- If a task spans multiple Rs, copy only the relevant parts
- Every task requires a verification method
- If the artifact is an executable binary/app, the plan MUST include a `**Runtime verification (executable artifacts only):**` line in each task that produces or modifies the executable entry point. Use the pattern: `<start-cmd> & sleep N && kill $! 2>/dev/null; test $? -eq 0`. N should be 3-5 seconds for CLI/desktop apps, matched to `config.server.health_check_timeout` for servers. This line is consumed by /choiceexecutor's runtime probe and is NOT optional for executable artifacts.
  > **When to include:** ANY task whose Files section creates or modifies the project's entry point (main module, CLI binary, GUI launcher, server start script). Omit for library-only tasks with no executable artifact.

### Task Dependencies

- `**Depends on:** Task N` — prerequisite task required
- `**File overlap with:** Task N` — same file modified
- If all tasks are independent, note "All tasks are independent" after Coverage Matrix

## 5.5 Integration Pipeline Matrix

After task decomposition, detect data pipelines that cross component boundaries.

### Detection Rules

A pipeline exists when:
1. Task A's output is consumed by Task B (data, events, state, rendered UI)
2. 3+ tasks form a layered chain (DB → ORM → API → Frontend)
3. A UI task displays data originating from a non-UI task
4. An executable artifact requires 2+ components to wire together

### Pipeline Matrix Template

````markdown
## Integration Pipeline Matrix
| Pipeline | Flow | First Connected | Contract Oracle | Integration Verify |
|----------|------|-----------------|-----------------|-------------------|
| P1 | PTY→Parser→Buffer→Renderer | Task 17 | DataReceived→bytes→cells→visual | `dotnet test --filter Integration` |
````

### Data Pipeline Contracts (per boundary)

- **Producer contract:** A emits [schema/event/state] with [required fields]
- **Consumer contract:** B consumes same contract without loss/reordering
- **State/render delta:** observable output changes from [before] to [after]

### Integration Milestone Task

When a pipeline is detected, add an explicit integration task after the last component task:

- **Depends on:** all component tasks in the pipeline
- **Completion criteria:** Given/When/Then that exercises the FULL pipeline (not just individual components)
- **Verify:** Integration test command (must be automated — no manual/placeholder)
- **Verify-type:** e2e
- **Contract assertions per boundary:**
  - Producer→Consumer: [data format emitted] → [data format expected]. Verify: `[assertion command]`

### Omit When

- All tasks are independent (no cross-component data flow)
- Single-task plan
- Library-only project with no executable artifact

### Coverage Matrix Integration

Integration milestone tasks must appear in the Coverage Matrix. They typically cover multiple Rs (those depending on cross-component interaction).

## 5.6 Full-Feature Wiring Gate

After the Integration Pipeline Matrix, add this section when any of these are true:
- The plan has 2+ tasks and a task consumes another task's output
- The plan changes 2+ layers such as DB/API/UI, CLI/core/output, or service/adapter/view
- The plan creates or modifies an executable artifact
- Any task title or AC contains integration, milestone, wiring, route, registration, binding, subscription, or end-to-end

Single-task library-only plans with no executable artifact may omit this section.

Template:

```markdown
## Full-Feature Wiring Gate

**Required:** yes
**Verify-type:** e2e
**Covers:** T1 -> T2 -> T3, P1
**Expected observation:** [observable result from the user's entry point]
**Verify:** `[single automated command that exercises the whole feature]`
```

Rules:
- The Verify command must run from the user-facing entry point or an integration/e2e test that drives the same wiring.
- The Verify command must not be empty, placeholder-only, `echo`, `true`, or only a unit test for one component.
- If no automated command exists, add a task that creates the probe before implementation.
- `/executeharness` treats a missing or failing gate as incomplete work even when every step is `completed`.

## 6. Agent Assignment

```markdown
## Agent Assignment

| Task | Agent | Mode | Reason |
|------|-------|------|--------|
| T1 | subagent | isolated | Independent module creation |
| T2 | subagent | isolated | Independent tests |
| T3 | inline | sequential | Depends on T1 results |
```

Mode: `isolated` / `sequential` / `parallel`

## 7. Plan Review Loop

After completing the plan:

1. Dispatch `ezpowers:plan-reviewer` plugin agent via `subagent_type`. Pass only dynamic info in the prompt:

   ```
   Agent tool:
     subagent_type: "ezpowers:plan-reviewer"
     description: "Review plan document"
     prompt: |
       **Plan to review:** <absolute path to plan file>
       **Spec for reference:** <absolute path to spec file>
   ```

2. Parse reviewer result by `## Verdict: PASS` or `## Verdict: FAIL` header only. Ignore `PASS`/`FAIL` strings elsewhere. **If Verdict header is missing or malformed:** treat as `FAIL`, but on 2 consecutive missing Verdict headers, escalate to user ("Reviewer is not returning verdicts in the standard format.")
3. Issues found -> fix -> fresh subagent re-dispatch (same prompt, do not pass previous results)
4. Maintain a private issue log — for oscillation detection. Log each issue by `{task}:{check_number}` key (e.g., `T2:coverage_matrix`, `T3:impact_scope`).
5. **Oscillation check (from iteration 3):** If a current issue's `{task}:{check_number}` key also appeared in 2+ prior iterations -> immediately escalate to user
6. **Tiered escalation:** 3 rounds -> warn. 5 rounds -> stop.

## Backward Transition: Return to /brainstorm

If the spec is insufficient during planning — missing requirements, contradictory constraints, unclear scope — do not continue writing a plan against a broken spec.

**Triggers:**
- Requirements are ambiguous during task decomposition
- Two spec requirements contradict each other
- A critical technical constraint was not explored in the spec

**Actions:**
1. Log reason: "Returning to /brainstorm: [specific reason]"
2. Report to user: what is insufficient and why planning cannot proceed
3. Return to `/brainstorm` to resolve spec gaps
4. Resume `/plan` after spec update

## 8. Artifacts

**Save location:** Value of `plan location:` in `AGENTS.md`. Default: `docs/plans/`.
**Filename:** `YYYY-MM-DD-<feature-name>.md`

Plan header:
```markdown
# [Feature Name] Implementation Plan

**Goal:** [One sentence]
**Architecture:** [2-3 sentences]
**ASR Summary:** [ASR IDs and quality targets carried from spec]
**Tech Stack:** [Core technologies]
**Spec:** [Spec file path]

---
```

### INDEX.md Update

On plan commit, add the plan entry to `docs/INDEX.md`:

```markdown
## Plans
- [YYYY-MM-DD-<feature-name>](plans/YYYY-MM-DD-<feature-name>.md): [derived] implementation plan
```

If a Plans section exists, add the entry. Otherwise, create the section.

## 9. Completion

After the plan is written:
1. Task count, dependency summary
2. Risky tasks
3. Workflow-runner `/pipeline-audit` result
4. Next command: `/choiceexecutor` when audit status is `PASS` or `WARN`

Update `phases/index.json`:
- plan: `status: "complete"`, `artifact: "<plan file path>"`, `completed_at: "<ISO 8601>"`
- build: `status: "pending"` (verify unchanged)

Then dispatch `ezpowers:workflow-runner` to invoke `/pipeline-audit` in
`post-plan` mode:

```
Agent tool:
  subagent_type: "ezpowers:workflow-runner"
  description: "Run post-plan pipeline audit"
  prompt: |
    **Target command:** /pipeline-audit
    **Invocation mode:** post-plan
    **Working directory:** <absolute project root>
    **Spec artifact:** <absolute path to spec file>
    **Plan artifact:** <absolute path to plan file>
```

Status handling:
- `DONE` with audit `PASS` or `WARN`: next step is **`/choiceexecutor`**.
- `DONE` with audit `FAIL`, or runner `FAIL`: return to `/plan` using the runner's routing recommendations.
- `NEEDS_USER`: resolve the requested decision, then rerun the same workflow-runner dispatch.

## Remember

- Always use exact file paths
- Complete code in the plan ("add validation" is banned)
- Exact commands with expected output
- DRY, YAGNI, TDD, frequent commits

## Common Rationalizations

| Rationalization | Reality |
|----------------|---------|
| "Spec is clear enough, no plan needed" | Spec = WHAT, Plan = HOW + order + files. Both needed. |
| "Task order during implementation" | Wrong order = blocking, context switches, conflicts. Plan now. |
| "Too many tasks, let's group them" | Grouping hides complexity. If a task takes >5 min, split it. |
| "Impact scope analysis takes too long" | Finding broken callers during implementation takes longer. 5 min of analysis saves hours of debugging. |
| "Tests are obvious, don't need them in plan" | Obvious to whom? Implementer needs exact test code and commands. |
| "File structure will emerge naturally" | Natural emergence = inconsistent boundaries. Decide boundaries upfront. |
| "Coverage matrix is bureaucracy" | Unmapped requirement = forgotten requirement. Matrix is the safety net. |
| "This task is too small for steps" | Small tasks with missing steps get misimplemented. Be explicit. |

## Next Steps

After plan approval and commit:
- `ezpowers:workflow-runner` automatically invokes `/pipeline-audit` to verify full pipeline readiness
- Then proceed to `/choiceexecutor` only when audit status is `PASS` or `WARN`
