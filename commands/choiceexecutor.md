---
description: Select and run execution path for plan tasks
allowed-tools: [Bash, Read, Write, Edit, Agent, AskUserQuestion]
---

# /choiceexecutor — Execution Path Selection

Execute tasks from the plan document. Choose an execution mode (subagent / harness / inline), then run tasks + AC verification + conditional security review + final code review.

## 1. Pre-flight Checks

Verify the following first:
1. `.harness/config.json` exists
2. Plan document exists (priority: argument > `phases/index.json` plan.artifact > latest file at config `defaults.plan_location`)
3. Spec document referenced by the plan exists

If missing, direct the user to the required step:
- No config -> `/setup`
- No plan -> `/plan`
- No spec -> `/brainstorm`

If `phases/index.json` exists, update the build phase to `in_progress`:
```json
{ "current_phase": "build", "phases": { "...": "...", "build": { "status": "in_progress" } } }
```

### Previous Session Re-entry Detection

If the build phase in `phases/index.json` is already `in_progress` and the plan has tasks checked with `- [x]`, treat it as a resumed session.

Present options to the user:

> **Previous session: Tasks 1-{N} complete, Task {N+1} incomplete.**
>
> **1. Resume** — skip completed tasks, continue from Task {N+1}
>
> **2. Re-run that task** — reset Task {N+1} checkbox, re-implement from scratch (existing commits kept; implementer reworks on current state)
>
> **3. Full re-run** — reset all checkboxes (`- [x]` → `- [ ]`), update `first-task-start-hash`, re-run everything
>
> **4. Abort** — keep current state

Option behavior:
- **Resume:** Apply Resume Protocol (Section 13). Treat `- [x]` tasks as PASS.
- **Re-run that task:** Reset the incomplete task's `- [x]` to `- [ ]`. No git revert — implementer re-implements on existing code without conflicts.
- **Full re-run:** Reset all checkboxes to `- [ ]`. Remove `**Resume hash:**` marker. Record new `first-task-start-hash`.
- **Abort:** No action.

## 2. Execution Path Selection

Ask the user for the execution mode:

> **Plan: `<plan-path>` — {task-count} tasks**
>
> **1. Subagent-driven (recommended)** — fresh agent per task, fast iteration
>
> **2. Harness execution** — step-by-step execution via EasyPowersHarness Python executor (`harness.root` required)
>
> **3. Inline execution** — sequential execution in the current session
>
> **Which mode?**

**Recommendation guide:**
- 1-3 tasks, independent → **inline** (fast and lightweight)
- 4+ tasks → **subagent-driven** (context isolation)
- `harness.root` configured + step-level execution logs needed → **harness**

Path 2 follows the `/executeharness` command procedure.

## 3. Task Graph Analysis

Analyze task dependencies before execution to determine execution strategy.

### Step 1: Parse Dependencies

Identify per task:
- **Explicit dependency:** `Depends on: Task N` marker
- **File overlap dependency:** `**File overlap with:** Task N` marker — pre-computed file overlap from /plan. Trust over implicit when present.
- **Implicit dependency:** Same file modified (`Modify:` items match) — fallback when no `File overlap with` marker
  - Detection: normalize each task's `Modify:` paths (strip trailing slash, unify case), then exact string comparison. No partial path matching.

### Step 2: Build Directed Graph

Construct directed graph: Task A -> Task B = "B depends on A"

### Step 3: Classify Task Groups

| Classification | Condition | Execution Strategy |
|----------------|-----------|-------------------|
| **Independent cluster** | No intra-group dependencies | Order-agnostic sequential dispatch |
| **Linear chain** | A->B->C strict order | Pipeline (sequential execution) |
| **Mixed** | Independent + chain | Independent in any order, chains sequential |

### Step 4: Execute by Classification

> **Note:** Claude Code's Agent tool supports sequential execution only. "Independent" means tasks can run in any order without dependency constraints, not that they dispatch concurrently.

- **Independent cluster (2+ tasks):** Sequential dispatch in any order. Per-task AC verification + security review after each.
- **Pipeline:** Strict sequential execution.
- **Single independent task:** Sequential dispatch.

### Edge Cases

- No dependency markers and different files modified -> treat as independent
- **All tasks modify the same file -> force sequential**
- **Cycle detection:** Perform topological sort. If not all tasks are visited, a cycle exists. Warn the user with the list of tasks in the cycle and fall back to sequential.
- **Analysis uncertain -> sequential fallback (safe)**

### Failure Handling

- **Failure propagation:** On task failure, mark all downstream dependent tasks as `SKIPPED` and do not execute. Recursively SKIP downstream of downstream.
- 3 failures on one task -> escalate that task to user
- Independent task failure does not block other independent tasks
- **Partial failure report:** On completion, present per-task PASS/FAIL/SKIPPED summary to user

## 4. Per-Task Execution Loop (Subagent-Driven)

```
Record git hash (git rev-parse HEAD)
  -> Assess task complexity
  -> Dispatch subagent (agents/implementer-prompt.md)
  -> Handle implementer status
  -> Controller: AC verification (run Verify commands)
    -> ALL PASS -> Runtime probe (if applicable)
      -> PASS -> AC Arbiter (integration/e2e tasks only)
        -> PASS -> conditional security review
        -> TEST_GAP/CODE_GAP/SPEC_GAP -> re-dispatch or return to /plan
      -> FAIL -> re-dispatch with runtime error
    -> FAIL -> re-dispatch with failure details (max 3)
    -> 3 failures -> escalate to user
  -> Compute changed-files -> next task
```

### Git Hash Recording

- **Before each task:** `git rev-parse HEAD` -> store as `<task-start-hash>`
- **First task:** also store `<first-task-start-hash>` (for final review)
- **No commits yet:** if `git rev-parse HEAD` fails, use empty tree hash `4b825dc642cb6eb9a060e54bf899d8b2306e7304`. This is git's empty tree; `git diff <empty-tree>..HEAD` shows all changes.
- **After each task:** changed-files = `git diff --name-only <task-start-hash>..HEAD` + `git ls-files --others --exclude-standard` (union, deduplicated)

### Task Complexity Assessment

Assess complexity on 3 dimensions before dispatch:

| Dimension | Low | Medium | High |
|-----------|-----|--------|------|
| **Scope** | 1-2 files, <50 lines | 3-5 files, 50-200 lines | 6+ files, 200+ lines |
| **Coupling** | Independent files | 2-3 interdependent | Tightly coupled modules |
| **Context breadth** | <5 files to read | 5-10 files | 10+ files |

- **Simple** (all low): dispatch as-is
- **Medium** (2+ medium): dispatch with extra context — architecture notes, interface contracts, dependency descriptions
- **Complex** (any high): recommend splitting

### Implementer Status Handling

- **DONE:** Proceed to AC verification
- **DONE_WITH_CONCERNS:** If accuracy-impacting, address first; if cosmetic, proceed to AC verification
- **BLOCKED:** Controller resolves (additional context, task split, user escalation). **Never skip**
- **NEEDS_CONTEXT:** Re-dispatch with requested context

## 5. Acceptance Criteria Verification (Controller)

**Passing unit tests is NOT the completion condition.** Completion requires executing the plan's Verify commands and confirming exit 0.

**Primary verification — run Verify commands:**

1. Extract Verify commands from the task's completion criteria
2. Execute each Verify command, check exit code (exit 0 = PASS)
3. **Timeout by Verify-type:**
   - `pure` / `cli`: 30s
   - `e2e`: 120s
   - `api`: 30s
   - `data`: 60s

   **Bash tool timeout mapping:**
   | Verify-type | Timeout | Bash tool timeout param |
   |-------------|---------|------------------------|
   | `pure` / `cli` | 30s | `timeout: 30000` |
   | `api` | 30s | `timeout: 30000` |
   | `data` | 60s | `timeout: 60000` |
   | `e2e` | 120s | `timeout: 120000` |

4. **Server management (e2e/api):**
   - If `config.server.start_command` is empty, skip server management
   - Start server: run `config.server.start_command` (background)
   - Health check: poll GET on `config.server.health_check_url` (max `config.server.health_check_timeout` seconds, default 15s)
   - If health check URL not set, fall back to 5s wait
   - Run Verify
   - Stop server: run `config.server.stop_command` (if not set, kill the started process)
5. No Verify commands: fall back to plan's verification method
6. ALL PASS -> conditional security review
7. ANY FAIL -> re-dispatch with failure details

**Re-dispatch loop:** max 3. Then escalate to user.

**Runtime probe (executable artifacts only):**

After all Verify commands PASS, if the task has a `Runtime verification:` line in the plan:
1. Execute the runtime verification command (timeout: 30000ms)
2. Exit 0 = runtime PASS. Non-zero = runtime FAIL.
3. Runtime FAIL → re-dispatch with error output + exit code.
4. No `Runtime verification:` line → skip.

Runtime probe is separate from AC verification. AC verifies spec behavior; runtime probe verifies the artifact starts and survives. Both must pass.

**GUI runtime probe (when `config.smoke.gui_strategy` is not `skip` or absent):**

For GUI executable tasks, the runtime probe MUST include multi-layer verification:
1. **Process survival:** app starts, survives `config.smoke.survival_seconds` (default 8s)
2. **Fatal output check:** stderr/stdout must NOT match `config.smoke.stderr_fail_regex`
3. **Window existence:** main window handle != 0 (platform-specific check)
4. **Screenshot artifact:** capture to `config.smoke.screenshot_path`, verify non-blank (pixel variance > threshold)
5. **Vision oracle (optional):** if `config.smoke.vision_required: true`, send screenshot to Claude vision API with `config.smoke.vision_prompt`, require `{"verdict":"PASS"}`

All layers must PASS. Any layer FAIL → re-dispatch implementer with the specific layer and exit code.

**Manual verification items are forbidden in automated harness mode.**
If a Verify-type `e2e` item has no executable Verify command (empty or placeholder), mark AC verification as FAIL and re-dispatch implementer with: "AC [N] has Verify-type e2e but no executable verification command. Write an automated probe (process health, stdout/stderr pattern, window handle check, headless test, or integration test) and re-submit."

Do not batch for human confirmation. Do not skip. No Verify command = FAIL.

### Independent AC Arbiter (integration/e2e tasks only)

After AC verification + runtime probe PASS, dispatch a fresh Agent as an independent arbiter for tasks that meet ANY of:
- Verify-type `e2e`
- `Depends on` 2+ tasks (integration milestones)
- Task title contains "integration", "milestone", or "wiring"

Simple `pure`/`cli`/`lib` tasks skip the arbiter and proceed directly to security review.

**Arbiter input (ONLY these — no implementer narrative, no test code, no prior review results):**
- Task AC text (Given/When/Then) verbatim from plan
- Changed file list (`git diff --name-only`)
- Verify command outputs (stdout/stderr + exit codes)
- Runtime probe artifacts (logs, screenshots, exit codes)

**Arbiter verdicts:**
- **PASS** → proceed to conditional security review
- **TEST_GAP** → re-dispatch implementer: "Verification does not prove the Then clause. Write a probe that directly observes [specific Then clause]."
- **CODE_GAP** → re-dispatch implementer with verification evidence showing implementation fails
- **SPEC_GAP** → return to /plan automatically (Section 13): plan lacks an automatable oracle for this AC

**Arbiter dispatch limit:** max 2 rounds per task. If arbiter returns TEST_GAP or CODE_GAP twice, escalate to user.

## 6. Conditional Security Review

After AC verification PASS (and arbiter PASS for integration/e2e tasks), check whether security review is needed.

**Trigger:** ANY of the following is true:
- Task description/requirements contain security keywords
- Changed file content contains security keywords
- Task modifies authentication, authorization, or data validation logic

**27 Security Keywords:**
auth, login, password, token, secret, encrypt, decrypt, hash, session, cookie, permission, role, sanitize, escape, injection, CORS, CSRF, API key, credential, certificate, OAuth, JWT, bearer, privilege, access control, rate limit, brute force

**Triggered:** Dispatch `ezpowers:security-reviewer` plugin agent via `subagent_type`
**Not triggered:** Skip. Log: "Security review skipped — no security surface in Task N."

**False positive policy:** When in doubt, review. Safety > efficiency.

**Security-spec conflict:** If the security reviewer flags an issue conflicting with the spec, security overrides spec. Log: "Spec deviation: [description]. Security concern overrode spec requirement."

## 7. Review Loop Protocol

**Independent re-review:** On re-dispatch, use the same prompt. Do not pass previous results.

**Controller issue log:** Private. Record issues + fixes per iteration. Do not share with reviewers.

**Oscillation detection (from iteration 3):** Log issues by `{file}:{issue_type}` key. If a current key also appeared in 2+ prior iterations -> escalate to user.

**Tiered escalation (unified reference table):**

| Review type | Source | Max iterations | Warn at | Stop at |
|-------------|--------|----------------|---------|---------|
| Spec review | brainstorm.md | 5 | 3 | 5 |
| Plan review | plan.md | 5 | 3 | 5 |
| Implementer AC | choiceexecutor.md | 3 | — | 3 |
| Security review | choiceexecutor.md | 5 | 3 | 5 |
| Final code review | choiceexecutor.md | 10 | 5 | 10 |
| Smoke test | choiceexecutor.md | 3 | — | 3 |

If the Verdict header is missing 2 consecutive times for any review type, immediately escalate to user.

**PASS_WITH_ISSUES handling:** PASS_WITH_ISSUES is a conditional PASS. It triggers exactly 1 additional fix-and-review round for Important issues. If the second review returns PASS or PASS_WITH_ISSUES, accept. If FAIL, enter the FAIL loop at iteration count 2. Max 3 PASS_WITH_ISSUES rounds total prevents endless Important-issue churn.

**Exemption check:** Before entering the review loop:
- `AGENTS.md` has `review-skip:` pattern?
- User explicitly requested review skip?
- Auto-excluded: lock files, generated, binary, git metadata, <20-line configs
- If true, skip the review loop.

**Large output handling:** 500+ line diff or 10+ files -> split review by task boundary or directory. No splitting within a single file. All chunks must PASS.

## 8. Controller Context Hygiene

**Subagent prompt sizing:**
- Include task description + completion criteria verbatim. Extra context (architecture notes, dependency descriptions) ~2K tokens max
- **Include the task text and completion criteria directly in the prompt** (see implementer-prompt.md template)
- **Do not paste the full plan/spec** — provide paths only; subagent reads as needed
- Do not pre-read source files into the prompt — subagent reads with fresh context

**Between-task cleanup:**
- Preserve after each task: task status (pass/fail), changed files, unresolved issues only
- Do not preserve: subagent full output, review details, intermediate reasoning

**Context pressure relief:**
- Before Task 5: compact on pressure detection
- After Task 5: proactive compact unconditionally
- **Compaction method:** The controller cannot directly shrink its own context window. "Compact" means:
  1. Stop referencing prior subagent output/review details/intermediate reasoning in subsequent output
  2. Instead, proceed using only these "work notes":
     - Remaining task numbers and titles
     - Cumulative changed files list
     - Unresolved issue summary (if any)
     - PASS/FAIL status per completed task
  3. If the session continues past Task 10, suggest `/compact` or a fresh session to the user

### Context Anchoring in Subagent Prompts

Include in implementer prompts for tasks modifying existing files:

> Before writing any code:
> 1. Read the module's AGENTS.md (if it exists)
> 2. Run `git log --oneline -10 [module-directory]`
> 3. Read related files until you can describe: (a) error handling pattern, (b) naming/structure pattern, (c) recent change direction
> 4. Output a 3-line pattern summary before proceeding

### Model Selection

- **Implementer:** Best coding model
- **Security reviewer:** Model with strong analysis capability
- **Final code reviewer:** Model with strong judgment

### Parallel Reviewer Limit

3+ `.md` reviewers -> sequential execution

### Subagent Dispatch — Placeholder Substitution List

Substitute template placeholders on every subagent dispatch:

**Implementer (`agents/implementer-prompt.md`):**
| Placeholder | Substitution |
|-------------|-------------|
| `[task name]` / `Task N` | Actual task number and name |
| `[FULL TEXT of task from plan]` | Full task text copied from plan |
| `[Scene-setting...]` | Architecture context, dependencies, prior task results |
| `[PASTE COMPLETION CRITERIA FROM PLAN]` | Completion criteria verbatim from plan |
| `[PASTE FROM PLAN]` | Verification method verbatim from plan |
| `[directory]` | Absolute working directory path |
| `[module-directory]` | Target module directory path |

**Security Reviewer (`ezpowers:security-reviewer` plugin agent):**

```
Agent tool:
  subagent_type: "ezpowers:security-reviewer"
  description: "Security review for Task N"
  prompt: |
    ## Changed Files
    <git diff --name-only <task-start-hash>..HEAD output as line-separated list>
```

**Code Reviewer (`ezpowers:code-reviewer` plugin agent):**

```
Agent tool:
  subagent_type: "ezpowers:code-reviewer"
  description: "Final code review"
  prompt: |
    **Plan file:** <plan file absolute path>
    **Diff range:** <first-task-start-hash>..HEAD
```

**Post-substitution validation:** Before dispatch, scan the completed prompt for `[` + alpha + `]` patterns (e.g., `[SPEC_FILE_PATH]`, `[directory]`). If unsubstituted placeholders remain, do not dispatch — log the missing placeholders and fix.

## 9. Degradation Detection and Response

**5 detection signals:**
- Implementer reports NEEDS_CONTEXT 2+ times on the same task
- Same issue category recurs across multiple tasks
- Implementer self-reports reading 8+ files
- 3+ re-dispatch cycles
- Compaction checkpoint reached after Task 5

**Signal extraction rules:**
- "NEEDS_CONTEXT 2+" → controller maintains per-task NEEDS_CONTEXT counter
- "Same issue category repeats" → classify reviewer issues by `[severity]` keyword, check for cross-task duplicates
- "8+ file reads" → pattern-match "Files read:" or "read N files" in implementer report, extract count
- "3+ re-dispatch" → controller maintains per-task dispatch counter
- "After Task 5 compaction" → triggers at task completion counter ≥ 5

**Response protocol:**
1. **Immediate:** Compact controller context
2. **Per-task:** If failing after 2 dispatches, re-assess complexity + consider splitting
3. **Session-level:** Degradation across 3+ tasks -> reconsider plan decomposition
4. **Escalation:** If degradation persists after compaction + splitting -> save state + suggest fresh session

## 10. Harness Execution (Path 2)

If the user selects Path 2, delegate to the `/executeharness` command.

1. Verify `harness.root` → if not set, inform the user
2. Capture git hash (`git rev-parse HEAD` → `<harness-start-hash>`)
3. Plan → Phase conversion (tasks to stepN.md, plan header to phase-context.md)
4. Create `phases/{feature-name}/index.json` (harness schema)
5. Protect `phases/index.json` (backup EZPowers format)
6. Commit converted files
7. Step-by-step execution (`execute.py` call loop)
8. Restore `phases/index.json` (EZPowers format)
9. On completion → proceed to Section 12 (Final Code Review), diff range: `<harness-start-hash>..HEAD`

See `commands/executeharness.md` for detailed procedure.

## 11. Inline Execution (Path 3)

Execute tasks sequentially in the current session. Inline runs all work in the controller's context, consuming more context than the subagent path.

### Context Pre-check

On inline selection, estimate context consumption based on task count and expected complexity. **If estimated consumption exceeds 40% of the context window**, ask the user:

> "Inline execution is estimated to consume over 40% of the context window. Run `/compact` first?"
>
> 1. `/compact` then proceed
> 2. Proceed as-is
> 3. Switch to subagent-driven

Estimation basis:
- ~3-5K tokens per task (file reads + implementation + tests + Verify)
- Account for context already consumed in the current session

### Git Hash Recording

- **Before first task:** `git rev-parse HEAD` → store as `<first-task-start-hash>` (for final review). Do not overwrite in subsequent tasks.
- **Before each task:** `git rev-parse HEAD` → store as `<task-start-hash>`
- **No commits yet:** use empty tree hash `4b825dc642cb6eb9a060e54bf899d8b2306e7304`
- **After each task:** changed-files = `git diff --name-only <task-start-hash>..HEAD` + `git ls-files --others --exclude-standard`

### Per-Task Execution Loop

For each task:

```
Record git hash (git rev-parse HEAD)
  -> Read task content
  -> Implement in TDD order (test -> confirm failure -> implement -> confirm pass)
  -> AC verification (run Verify commands, exit 0 = PASS)
    -> PASS -> conditional security review
    -> FAIL -> analyze failure -> fix code -> re-verify (max 3)
    -> 3 failures -> escalate to user
  -> Commit
  -> Compute changed-files
  -> Next task
```

### AC Verification

Follow the same procedure as Section 5 (Acceptance Criteria Verification). Run Verify commands with Verify-type timeouts.

### Conditional Security Review

Same trigger conditions as Section 6 (27 keywords). On trigger, dispatch `ezpowers:security-reviewer` plugin agent via `subagent_type`.

### Failure Handling

Inline uses **fix-in-place → re-verify** loops instead of subagent re-dispatch:

1. Verify fails → analyze failure output
2. Fix code based on root cause
3. Re-run Verify
4. Max 3 attempts. Then escalate to user.

### Final Code Review

After all tasks complete, proceed to Section 12 (Final Code Review). Same as subagent path.

## 12. Final Code Review

After all tasks complete, dispatch `ezpowers:code-reviewer` plugin agent via `subagent_type`:

- Provide plan path
- Full diff: `git diff <first-task-start-hash>..HEAD`
- Implementation summary
- Expect `## Verdict: PASS`, `## Verdict: PASS_WITH_ISSUES`, or `## Verdict: FAIL` output
- **Verdict parsing:** Extract full value after `## Verdict: ` to end of line. Match exactly against `PASS`, `PASS_WITH_ISSUES`, `FAIL`. Unknown value → treat as FAIL.
- PASS → complete.
- PASS_WITH_ISSUES → extract Important findings, auto-fix (1 round), then fresh code-reviewer dispatch. If re-review returns PASS or PASS_WITH_ISSUES (same or fewer issues) → accept. If FAIL → enter FAIL loop. Max 3 PASS_WITH_ISSUES rounds total.
- FAIL → fix + fresh re-dispatch. Warn@5, stop@10. Oscillation check from iteration 3.
- If `## Verdict:` pattern not found in subagent response, treat as FAIL and escalate: "Code reviewer did not return a verdict in the standard format."

## 13. Backward Transition: Return to /plan

If plan decomposition proves inadequate during execution — tasks too tightly coupled, missing dependencies, misaligned boundaries — do not force a broken plan.

**Triggers:**
- 2+ tasks modify the same file in conflicting ways
- Task prerequisites missing from the plan
- Task ordering assumptions are wrong given the actual codebase
- 2+ consecutive tasks BLOCKED for structural reasons

**Actions:**
1. Log reason: "Returning to /plan: [specific reason]"
2. Report to user
3. Save current progress:
   - Completed tasks: check the task's checkbox (`- [x]`) in the plan and commit
   - Incomplete tasks: leave checkboxes unchecked, mark as re-plan targets
   - Record `first-task-start-hash` in plan header: `**Resume hash:** <first-task-start-hash>`
   - Commit message: `wip: build progress saved before /plan return — Tasks 1-N complete`
4. Update `phases/index.json`: set build to `pending`, reset plan to `in_progress`
5. Return to `/plan` for plan revision
6. Resume `/choiceexecutor` with updated plan

### Resume Protocol (after returning from /plan)

1. Check for `**Resume hash:**` marker in plan document
2. If present: restore previous `first-task-start-hash` (preserves final review diff range)
3. Tasks checked `- [x]` are treated as PASS and skipped
4. Execute only `- [ ]` tasks (including newly added tasks)
5. Skipped tasks' artifacts (commits) already exist, so dependencies are satisfied
6. **Caution:** If the revised plan modifies files from already-completed tasks, those tasks must be manually reset to `- [ ]` — /plan notifies the user

## 14. Completion

After all tasks + final review complete:
1. Full diff summary (`git diff <first-task-start-hash>..HEAD`)
2. Completed/failed/SKIPPED task list
3. Suggest reference doc sync:

> **Sync reference docs with the codebase?** (`/sync-docs`)
>
> 1. Run
> 2. Skip

If user selects 1, follow `/sync-docs` procedure. Can also be invoked independently later.

4. **Smoke test:** If `config.smoke.command` is non-empty, run it. On failure, enter fix loop (max 3). If empty, skip.

   **GUI smoke (if `config.smoke.gui_strategy` is not `skip` and not absent):**
   Execute the gui_strategy probe after smoke command:
   - `process_probe`: start app → survive N seconds → no fatal stderr → window handle exists → kill. PASS/FAIL by exit code.
   - `screenshot_vision`: process_probe + capture screenshot → vision oracle judgment. PASS/FAIL.
   - `headless`: run `config.smoke.command` as headless test runner (Playwright, Avalonia.Headless, FlaUI). Exit 0 = PASS.
   - GUI smoke FAIL → same fix loop (max 3). No user confirmation.

   **Exit code convention:**

   | Code | Meaning |
   |------|---------|
   | 0 | Pass |
   | 10 | Start failed |
   | 11 | Exited before survival window |
   | 12 | Fatal output matched |
   | 13 | No main window |
   | 14 | Invisible/zero-size window |
   | 15 | Screenshot capture failed |
   | 16 | Blank screenshot (pixel variance below threshold) |
   | 17 | Vision oracle verdict FAIL |
   | 20 | Timeout |

5. Next recommendation: `/review`

Update `phases/index.json`:
- build: `status: "complete"`, `completed_at: "<ISO 8601>"`
