---
description: Select and run execution path for plan tasks
allowed-tools: [Bash, Read, Write, Edit, Agent, AskUserQuestion]
---

# /choiceexecutor — Execution Path Selection

Source contracts: `docs/reference/domain-language.md`, `docs/reference/verification-contract.md`, `docs/reference/dispatch-protocol.md`.
Execute tasks from the plan document. Choose an execution mode (subagent / harness / inline), then run tasks + AC verification + conditional security review + final code review.

## 1. Pre-flight Checks

Verify the following first:
1. `.harness/config.json` exists
2. Plan document exists (priority: argument > `phases/index.json` plan.artifact > latest file at config `defaults.plan_location`)
3. Spec document referenced by the plan exists
4. `phases/index.json` audit gate:
   - `audit.status` is `"FAIL"` → report `"pipeline-audit에서 미해결 항목 있음. 해결 후 /pipeline-audit 재실행하세요."` and stop
   - `audit` field is missing → report `"/pipeline-audit를 먼저 실행하세요."` and stop
   - `audit.status` is `"PASS"` or `"WARN"` → proceed

If missing, direct the user to the required step:
- No config -> `/setup`
- No plan -> `/plan`
- No spec -> `/brainstorm`
- No audit or audit FAIL -> `/pipeline-audit`

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
- `harness.root` configured + external harness logs or step-level recovery needed → **harness**
- All paths are fail-closed for Verify, runtime smoke, and Full-Feature Wiring Gate. Harness is the external executor/recovery path, not the only strict verification path.

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

### Step 3.5: Integration Checkpoint

After each task completes, check the Integration Contract Matrix for newly
completable rows:

1. Identify ICM rows where both Producer and Consumer tasks are now done.
2. Run each newly completed row's Verify command.
3. Any FAIL → re-dispatch the Consumer task with the failure details.
4. All PASS → proceed to next task or Step 4.

This runs regardless of cluster boundaries — linear chains, independent
clusters, and mixed graphs all trigger ICM verification as soon as both sides
of a contract are complete.

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

- Before re-dispatch or fix-in-place, identify the failing Verify/runtime/wiring signal that will prove the fix.
- **Failure propagation:** On task failure, mark all downstream dependent tasks as `SKIPPED` and do not execute. Recursively SKIP downstream of downstream.
- 3 failures on one task -> escalate that task to user
- Independent task failure does not block other independent tasks
- **Partial failure report:** On completion, present per-task PASS/FAIL/SKIPPED summary to user

## 3.6. Git Hash Recording Protocol

Apply this protocol in every execution path (subagent, inline, harness).

- **Before each task:** `git rev-parse HEAD` -> store as `<task-start-hash>`
- **First task only:** also store as `<first-task-start-hash>` (for final review). Do not overwrite in subsequent tasks.
- **No commits yet:** if `git rev-parse HEAD` fails, use empty tree hash `4b825dc642cb6eb9a060e54bf899d8b2306e7304`. This is git's empty tree; `git diff <empty-tree>..HEAD` shows all changes.
- **After each task:** changed-files = `git diff --name-only <task-start-hash>..HEAD` + `git ls-files --others --exclude-standard` (union, deduplicated)

## 3.7. Wiring Config Validation (fail-closed)

Apply this validation whenever wiring state is checked (View Wiring Test, Wiring Gate Test).
Canonical definition: `docs/reference/verification-contract.md` § Wiring Config Validation.

- `wiring` block missing → FAIL: `"config.json has no wiring block. Run /setup to regenerate."`
- `wiring.enabled: false` + `wiring.exempt_reason` empty → FAIL: `"wiring disabled without exempt_reason."`
- `wiring.enabled: false` + `wiring.exempt_reason` non-empty + `artifact_kind` not `docs` or `library` → FAIL: `"wiring exemption not allowed for artifact_kind: {kind}"`
- `wiring.enabled: false` + `wiring.exempt_reason` non-empty + `artifact_kind` is `docs` or `library` → skip/exempt. Log: `"View wiring exempt: [reason]"`
- `wiring.enabled: true` + `wiring.view_extensions` empty → skip only View Wiring Test. CLI/server/headless projects may have an empty `view_extensions` array. The Full-Feature Wiring Gate still runs when required.

## 4. Per-Task Execution Loop (Subagent-Driven)

Before the first task in Path 1, prepare machine-checkable lightpath artifacts:

```powershell
scripts/lightpath-gate.ps1 -Scope prepare -ProjectRoot <project-root> -PlanPath <plan-path> -Phase <phase>
```

This converts the plan into `phases/<phase>/step*.md`, `wiring-gate.json`, and
`lightpath-gate.json`. The parent/controller keeps only task status,
changed-files, diff range, artifact paths, verdict enums, and short failure
tails. It does not keep full subagent output, full logs, or reviewer reasoning
in context.

```
Record git hash (Section 3.6)
  -> Assess task complexity
  -> Extract Verify Command Baseline from plan file
  -> Construct implementer prompt + Verify Fidelity Check
     (mismatch -> HALT, correct prompt, re-check)
  -> Dispatch subagent (agents/implementer-prompt.md)
  -> Handle implementer status
  -> 4a. Test Baseline Protection (PASS_TO_PASS invariant)
  -> 4b. Lint & Typecheck Gate
  -> 4b+. Dependency Audit Gate (if manifest changed)
  -> 4c. SAST Gate (changed files only)
  -> Controller: Lightpath task gate (`scripts/lightpath-gate.ps1 -Scope task -TaskNumber N`)
    -> PASS -> 4d. Structural Invariant Gate (if plan has invariants)
      -> PASS -> AC Arbiter (integration/e2e/logic-dense tasks)
        -> PASS -> View Wiring Test (view tasks only)
          -> PASS -> conditional security review (keyword-triggered, no SAST — already ran at 4c)
        -> TEST_GAP/CODE_GAP/SPEC_GAP -> re-dispatch or return to /plan
      -> hard FAIL -> re-dispatch with invariant violation details
      -> soft FAIL -> WARN (log, continue)
    -> FAIL -> re-dispatch with verify/runtime failure details (max 3)
    -> 3 failures -> escalate to user
  -> Compute changed-files -> next task
```

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

### Wiring Context Injection

When constructing the implementer prompt for a task with `Depends on:` another
task, include in the "Prior Task Wiring" section:
1. The dependency's `**Wiring handoff:**` field (verbatim from plan).
2. Relevant Integration Contract Matrix rows where this task is the Consumer.
3. Referenced Wiring Map entries from the spec.
If no dependency or no wiring handoff exists, state "No wiring handoff from
dependency."

### Cross-Cutting Concern Injection

When constructing the implementer prompt, populate the "Cross-Cutting Concerns"
section from `agents/implementer-prompt.md`:
1. Read the task's `**Operational decisions:**` field from the plan.
2. If `none applicable`, omit the section.
3. Otherwise, paste the field values into the implementer prompt's
   Cross-Cutting Concerns section verbatim.

### Implementer Status Handling

- **DONE:** Proceed to AC verification
- **DONE_WITH_CONCERNS:** If accuracy-impacting, address first; if cosmetic, proceed to AC verification
- **BLOCKED:** Controller resolves (additional context, task split, user escalation). **Never skip**
- **NEEDS_CONTEXT:** Re-dispatch with requested context

### Verify Command Baseline (mandatory per-task)

Before every dispatch (initial and re-dispatch), extract and record the Verify Command Baseline for the current task.

**Extraction (mechanical — no interpretation or substitution):**

1. Read the plan file (not memory, not implementer output, not cached context)
2. Navigate to the current task's `**Completion criteria (from spec):**` section
3. Extract every `Verify: \`...\`` value verbatim — preserve flags, paths, grep patterns
4. Extract the `**Verification method:**` line
5. Extract the `**Runtime verification:**` line (if present)
6. Extract Verify commands from the `**View wiring verification**` section (if present)
7. Store as the **Verify Command Baseline** for this task

**Verify Fidelity Check (between prompt construction and dispatch):**

After constructing the implementer prompt, before dispatch:
1. Extract every Verify command from the constructed prompt — scan Acceptance Criteria, Verification method, Runtime verification, and View wiring verification sections
2. Compare each extracted command against the corresponding Baseline entry (exact string match; leading/trailing whitespace trimmed, internal whitespace within the command preserved as-is)
3. Confirm every Baseline entry has a matching prompt entry and vice versa (no additions, no omissions)
4. **Mismatch → HALT.** Log: `Verify Fidelity FAIL: plan=\`<plan>\`, prompt=\`<prompt>\`. Correct prompt.`
5. **All match → dispatch**

This is a hard gate, not advisory.

**Predictive elimination ban:** If a Verify command appears impractical (e.g., e2e requires a running app), the controller must not remove or replace it. Instead: make infrastructure available (start the app, configure the environment) or escalate to user. Difficulty is not a reason to weaken the oracle.

### 4a. Test Baseline & Protection Gate

Canonical procedure: `docs/reference/verification-contract.md` § Test Baseline Protection.
Phase 1 (baseline snapshot) runs before implementer dispatch. Phase 2 (protection check) runs after implementer completes, before AC verification. Max 3 re-dispatch attempts.

### 4b. Per-Task Lint & Typecheck Gate

Canonical procedure: `docs/reference/verification-contract.md` § Lint & Typecheck Gate.
Trigger: every task. Catches hallucinated APIs and undefined references. Max 2 retries per sub-gate.

### 4b+. Dependency Audit Gate

Canonical procedure: `docs/reference/verification-contract.md` § Dependency Audit Gate.
Trigger: task diff includes dependency manifest changes. Hallucinated dependency = FAIL. Critical/High CVE = FAIL (max 2 retries).

**Ordering within per-task loop:**
```
Implementer dispatch -> Implementer completes ->
  4a. Test Baseline Protection ->
  4b. Lint & Typecheck Gate ->
  4b+. Dependency Audit Gate (if manifest changed) ->
  4c. SAST Gate ->
  5. AC Verification (Verify commands) ->
  6. Conditional Security Review (keyword-triggered, no SAST) ->
  ...
```

## 5. Acceptance Criteria Verification (Controller)

**Passing unit tests is NOT the completion condition.** Completion requires executing the plan's Verify commands and confirming exit 0.

**Primary verification — run Verify commands:**

For Path 1 and Path 3, the controller may execute this section through the
shared gate script:

```powershell
scripts/lightpath-gate.ps1 -Scope task -ProjectRoot <project-root> -Phase <phase> -TaskNumber <N>
```

The script reuses `scripts/verify-step.py` and writes `lightpath-gate.json`.
The implementer subagent's `DONE` report is only a claim; this gate is the
completion verdict for task Verify and runtime smoke.

1. Re-read the plan file and extract Verify commands from the current task's `**Completion criteria (from spec):**` section. Do not use commands from the implementer report, dispatch prompt, or memory. The plan file is the only source at this step.
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

**GUI runtime probe (desktop executable artifacts):**

For GUI executable tasks, the runtime probe MUST include multi-layer verification:
1. **Process survival:** app starts, survives `config.smoke.survival_seconds` (default 8s)
2. **Fatal output check:** stderr/stdout must NOT match `config.smoke.stderr_fail_regex`
3. **Window existence:** main window handle != 0 (platform-specific check)
4. **Screenshot artifact:** capture to `config.smoke.screenshot_path`, verify non-blank (pixel variance > threshold)
5. **UI oracle:** if `expected_text_regex` or `expected_automation_name_regex` is configured, the UI Automation tree must match it.

All layers must PASS. Any layer FAIL → re-dispatch implementer with the specific layer and exit code.

Desktop/server/CLI artifacts may not skip runtime smoke. Only `artifact_kind: docs|library` with `config.smoke.required: false` may skip.

**Manual verification items are forbidden in automated harness mode.**
If a Verify-type `e2e` item has no executable Verify command (empty or placeholder), mark AC verification as FAIL and re-dispatch implementer with: "AC [N] has Verify-type e2e but no executable verification command. Write an automated probe (process health, stdout/stderr pattern, window handle check, headless test, or integration test) and re-submit."

Do not batch for human confirmation. Do not skip. No Verify command = FAIL.

### Independent AC Arbiter

After AC verification + runtime probe PASS, dispatch a fresh Agent as an independent arbiter for tasks that meet ANY of:
- Verify-type `e2e`
- `Depends on` 2+ tasks (integration milestones)
- Task title contains "integration", "milestone", or "wiring"
- Task has 3+ Given/When/Then acceptance criteria
- Task AC text contains calculation/comparison keywords: discount, total, rate,
  percent, threshold, limit, quota, balance, score, calculate, compare, price,
  amount, fee, tax, weight, rank

Simple `pure`/`cli` tasks with 1-2 AC and no calculation keywords are exempt.

Simple `pure`/`cli`/`lib` tasks skip the arbiter and proceed directly to security review.

**Arbiter input (ONLY these — no implementer narrative, no test code, no prior review results):**
- Task AC text (Given/When/Then) re-read from plan file at arbiter dispatch time (not from memory or prior context)
- Changed file list (`git diff --name-only`)
- Verify command outputs (stdout/stderr + exit codes)
- Runtime probe artifacts (logs, screenshots, exit codes)

**Arbiter verdicts:**
- **PASS** → proceed to conditional security review
- **TEST_GAP** → re-dispatch implementer: "Verification does not prove the Then clause. Write a probe that directly observes [specific Then clause]."
- **CODE_GAP** → re-dispatch implementer with verification evidence showing implementation fails
- **SPEC_GAP** → return to /plan automatically (Section 13): plan lacks an automatable oracle for this AC

**Arbiter dispatch limit:** max 2 rounds per task. If arbiter returns TEST_GAP or CODE_GAP twice, escalate to user.

### View Wiring Test (Per-Task, fail-closed)
**Config validation:** Apply Wiring Config Validation (Section 3.7).

**감지:** `wiring.enabled: true` → Task changed-files에 `config.wiring.view_extensions` 매칭 확장자 포함 여부.
**실행:** Task의 `**View wiring verification**` 섹션에서 Verify 커맨드 추출. 섹션 없으나 view 파일이 changed-files에 있음 → FAIL (plan에 wiring verification 누락).
Verify 커맨드 실행 (timeout: 120s). Exit 0 = PASS. Non-zero = FAIL.
FAIL → 테스트 출력에서 W1-W5 결함 유형 분류. implementer 재디스패치: "View Wiring Test failed. Defect type: [W1-W5]. [출력 발췌]. Fix the wiring defect."
Max 3 retries → user 에스컬레이션. `wiring.enabled: true` with non-empty `view_extensions` and changed view files → skip 불가.
**Inline execution (Path 3):** 동일 감지/실행. 재디스패치 대신 fix-in-place.

### Incremental Runnability (executable artifacts, post-skeleton)

After Task 1 `{skeleton}` passes runtime smoke, every subsequent task must
also pass `config.smoke.command` before proceeding to the next task.

**Trigger:** `config.smoke.artifact_kind` is `cli`/`server`/`desktop` AND at
least one `{skeleton}` task has completed and passed runtime smoke.

**Execution:** Run `config.smoke.command` (same timeout as Section 14 smoke
gate). Exit 0 = PASS.

**Failure:** Re-dispatch implementer: "Runtime smoke failed after your changes.
The app no longer starts. Fix the regression before proceeding." Max 2 retries
→ escalate to user.

**GUI smoke:** If `config.smoke.gui_strategy` is configured, run the same GUI
probe as Section 14.

Skeleton task itself already requires runtime smoke in its AC — this gate
applies to tasks AFTER the skeleton.

### Incremental Wiring Probe (executable artifacts, post-skeleton)

After Incremental Runnability passes, verify the task's module is reachable
from the app's entry point. Incremental Runnability proves the app starts;
this probe proves the task's work is actually connected.

**Trigger:** Task has a `**Wiring probe:**` section in the plan AND at least
one `{skeleton}` task has completed.

**Execution:** Extract the Wiring Probe Verify command from the plan file
(not from implementer reports or cached context). Run it (timeout: 120s).
Exit 0 = PASS.

**Failure classification:**
- `IMPORT_UNREACHABLE`: module not imported from entry point chain
- `REGISTRATION_MISSING`: handler/service not registered in DI/IPC/router
- `RUNTIME_UNREACHABLE`: module imported but not initialized at runtime

FAIL → re-dispatch implementer: "Wiring Probe failed: [type]. Module [path]
is not reachable from entry point [path]. Add the missing
import/registration." Max 2 retries → escalate to user.

**Missing probe detection:** Task creates a new module file (not in
pre-task file list) but plan has no `**Wiring probe:**` section →
log WARNING: `"Task N creates [path] but has no Wiring Probe. Plan defect."`.
Execution continues but the warning is surfaced in the completion report.

**Refactoring probe detection:** Task has both `Create:` and `Delete:` entries
for module files (rename/split pattern), OR task's `Modify:` files include
path changes detected by `git diff --diff-filter=R` (rename). In either
case, treat as a wiring-affecting change and require a Wiring Probe section
in the plan. If missing, log WARNING with the same message as above. If
present, execute the probe (same as new module flow).

**Inline execution (Path 3):** Same detection/execution. Fix-in-place
instead of re-dispatch.

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

### 4c. Automated SAST Gate

Canonical procedure: `docs/reference/verification-contract.md` § SAST Evidence Layer.
Timing: after 4b, before AC Verification. Trigger: every task. Critical/High = FAIL (max 2 retries), Medium/Low = WARN.

### 4d. Structural Invariant Gate (per-task)

**Trigger:** Plan has a `## Structural Invariants` section with verification
commands. Runs after lightpath task gate PASS.

**Execution:** Parse each row from the plan's Structural Invariants table.
Execute each row's verification command (timeout: 30s).

**Classification:**
- Invariants marked `hard` (or unmarked — default): exit non-zero = **FAIL**.
  Re-dispatch implementer with: "Structural Invariant violated: [rule]. Fix
  before proceeding." Max 2 retries → escalate to user.
- Invariants marked `soft`: exit non-zero = **WARN**. Log violation but
  continue. Soft invariants are for rules that may be temporarily violated
  during multi-task builds (e.g., layer dependency during migration).

**Skip:** No Structural Invariants section in plan → skip entirely.

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
| Test protection | verification-contract.md | 3 | — | 3 |
| Lint/typecheck | verification-contract.md | 2 | — | 2 |

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
- Preserve lightpath evidence as paths and verdicts only: `lightpath-gate.json`,
  `wiring-gate.json`, runtime artifact names, and short failure tails
- Do not preserve: subagent full output, review details, intermediate reasoning

The parent/controller owns the final completion decision, but it does not
perform evidence-heavy review in its own context. It delegates mechanical checks
to gate scripts and qualitative checks to reviewer/arbiter subagents, then
parses only their status lines and verdict enums.

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

> **Dispatch protocol:** Read `docs/reference/dispatch-protocol.md` and follow the backend-appropriate dispatch path for each reviewer below. Implementer dispatch is not affected.

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
| `[PLAN_FILE_PATH]` | Absolute path to the plan file |
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

**Post-substitution validation:** Before dispatch:
1. **Placeholder check:** Scan the completed prompt for `[` + alpha + `]` patterns (e.g., `[SPEC_FILE_PATH]`, `[directory]`). Unsubstituted → do not dispatch.
2. **Verify Fidelity Check:** Execute the fidelity check from Section 4.1. Any Verify command mismatch between prompt and plan = HALT dispatch.

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

When the user selects Path 2, load `commands/executeharness.md` and follow that
command as the source of truth for all harness conversion, execution, recovery,
and restoration behavior. Do not duplicate the harness procedure here.

After `/executeharness` reports all steps complete, require its full-feature
wiring gate verdict before continuing:

- Read `phases/<phase>/wiring-gate.json` directly. Do not rely only on the
  `/executeharness` status line or process exit code.
- `PASS` or `pass` -> continue at Section 12 (Final Code Review) using the diff range
  returned by `/executeharness` (`<harness-start-hash>..HEAD`)
- `review_pending` -> dispatch `ezpowers:wiring-reviewer` with plan path,
  diff range, `wiring-gate.json`, runtime artifacts, and run log path. Write
  the verdict to `wiring-gate.json.reviewer_verdict`, rerun
  `scripts/harness-gate.ps1 -ProjectRoot <project-root> -Phase <phase>`, then
  reread `wiring-gate.json`. Continue only if status becomes `pass`.
- `TEST_GAP` -> stop and return to `/plan` or reset the probe-writing step
- `CODE_GAP` -> reset the related harness step and rerun `/executeharness`
- `SPEC_GAP` -> return to `/plan`
- `fail`, `pending`, or any unknown status -> do not complete; report the gate
  status and recovery route
- Missing or malformed wiring verdict -> treat as `TEST_GAP`

Path 2 completion requires `all steps completed + wiring gate PASS + Final Code
Review PASS`. Step completion alone is not enough.

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

Apply Git Hash Recording Protocol (Section 3.6).

Prepare the same lightpath gate artifacts used by the subagent path:

```powershell
scripts/lightpath-gate.ps1 -Scope prepare -ProjectRoot <project-root> -PlanPath <plan-path> -Phase <phase>
```

### Per-Task Execution Loop

For each task:

```
Record git hash (git rev-parse HEAD)
  -> Read task content
  -> Implement in TDD order (test -> confirm failure -> implement -> confirm pass)
  -> Test Baseline Protection (Section 4a, fix-in-place)
  -> Lint & Typecheck Gate (Section 4b, fix-in-place)
  -> Lightpath task gate (scripts/lightpath-gate.ps1 -Scope task -TaskNumber N)
    -> PASS -> conditional security review
    -> FAIL -> analyze failure -> fix code -> re-verify (max 3)
    -> 3 failures -> escalate to user
  -> Commit
  -> Compute changed-files
  -> Next task
```

### Test Baseline Protection & Lint/Typecheck (Inline)

Follow the same procedures as Section 4a (Test Baseline & Protection Gate) and Section 4b (Per-Task Lint & Typecheck Gate). All detection logic, thresholds, and FAIL/WARN outcomes are identical. The only difference: re-dispatch is replaced by fix-in-place -> re-check loops with the same max retry counts (test protection: max 3, lint/typecheck: max 2).

### AC Verification

Follow the same procedure as Section 5 (Acceptance Criteria Verification) by
running `scripts/lightpath-gate.ps1 -Scope task`. Re-read the plan file through
the converted step artifact; do not use commands from earlier in the session
context. If the gate fails, fix the code or plan gap; do not weaken or replace
the Verify command.

### Conditional Security Review

Same trigger conditions as Section 6 (27 keywords). On trigger, dispatch `ezpowers:security-reviewer` plugin agent via `subagent_type`.

### Failure Handling

Inline uses **fix-in-place → re-verify** loops instead of subagent re-dispatch:

1. Verify fails → analyze failure output
2. Fix code based on root cause
3. Re-run Verify
4. Max 3 attempts. Then escalate to user.

### Quality Budget & Final Code Review

After all tasks complete, proceed to Section 11a (Quality Budget) then Section 12 (Final Code Review). Same as subagent path.

## 11a. Quality Budget Verification Gate

**Purpose:** Enforce Quality Budget targets declared in the spec at execution time, not just as documentation.

**Trigger:** After all tasks complete, before Final Code Review. Only for budgets where `verify_command` is specified.

**Extraction:**
- Read spec file → Architecture Baseline → Quality Budgets section.
- For each budget category (performance, reliability, security, cost, maintainability):
  - Extract `metric`, `rule` (hard/soft ceiling/floor), and `verify_command` fields.
  - Skip categories with `none declared` or missing `verify_command`.

**Execution:**
- For each budget with `verify_command`:
  - Run command (timeout: 180s for performance/load tests, 60s for others).
  - Parse output for measured value.
  - Compare against declared metric threshold.
- Per-budget result:
  - Measured value within threshold → **PASS**
  - Measured value exceeds threshold → **FAIL** with measured vs expected

**Verdict aggregation:**
- All budgets PASS or SKIP → Overall **PASS**
- Any budget FAIL:
  - `hard ceiling/floor` budget → **FAIL** (re-dispatch last relevant task, max 2 retries)
  - `soft ceiling/floor` budget → **WARN** (advisory)
- No `verify_command` configured → **SKIP** (log: `"No Quality Budget verify commands configured"`)

**Report:** Include budget verification results in final completion report.

| Budget | Metric | Target | Measured | Rule | Verdict |
|--------|--------|--------|----------|------|---------|
| (from spec) | (from spec) | (from spec) | (from execution) | hard/soft | PASS / FAIL / WARN / SKIP |

## 12. Final Code Review

After all tasks complete + Quality Budget gate, dispatch `ezpowers:code-reviewer` plugin agent via `subagent_type`:

- Provide plan path, diff range, changed-files list, Quality Budget results
  (if any), and artifact paths. Do not paste the full diff into the prompt;
  the reviewer reads the diff/files as needed.
- Implementation summary
- Expect `## Verdict: PASS`, `## Verdict: PASS_WITH_ISSUES`, or `## Verdict: FAIL` output
- **Verdict parsing:** Extract full value after `## Verdict: ` to end of line. Match exactly against `PASS`, `PASS_WITH_ISSUES`, `FAIL`. Unknown value → treat as FAIL.
- PASS → complete.
- PASS_WITH_ISSUES → extract Important findings, auto-fix (1 round), then fresh code-reviewer dispatch. If re-review returns PASS or PASS_WITH_ISSUES (same or fewer issues) → accept. If FAIL → enter FAIL loop. Max 3 PASS_WITH_ISSUES rounds total.
- FAIL → fix + fresh re-dispatch. Warn@5, stop@10. Oscillation check from iteration 3.
- If `## Verdict:` pattern not found in subagent response, treat as FAIL and escalate: "Code reviewer did not return a verdict in the standard format."

### 12a. Code Duplication Gate

**Purpose:** Detect AI-generated code duplication that inflates maintenance cost (GitClear: 4x duplication increase with AI coding).

**Trigger:** After Final Code Review, before Completion.

**Execution:**
1. Check `config.quality.duplication_command` in `.harness/config.json`
   - If configured: run command against changed files (timeout: 60s)
   - If not configured: run heuristic check (see below)

2. **Heuristic duplication check** (when no dedicated tool):
   - Extract all function/method bodies from changed files (>5 lines)
   - Compare each pair for structural similarity (normalize whitespace, variable names)
   - Flag pairs with >80% structural similarity
   - Threshold: 3+ duplicated blocks → **WARN**

3. **Tool-based check** (when `duplication_command` configured):
   - Common tools: `jscpd --min-lines=5 --threshold=3 {changed_files}`, `pylint --disable=all --enable=duplicate-code {files}`
   - Parse output for duplication percentage or block count
   - Duplication >5% of changed code → **WARN** (`"Code duplication detected: {pct}%. Consider extracting shared function/module."`)
   - Duplication >15% → **FAIL** (re-dispatch with: "Extract duplicated logic into shared function. Duplicated blocks: {list}")

4. **Verdict:** WARN does not block. FAIL triggers 1 fix round (max 1 retry, then downgrade to WARN).

### 12b. Mutation Testing Gate (Optional)

**Purpose:** Verify that Verify commands and tests actually detect code defects, not just exercise code paths. Prevents "tests that test nothing" pattern common in AI-generated code.

**Trigger:** Only when `config.quality.mutation_command` is configured. Advisory gate (WARN only, never FAIL).

**Execution:**
1. Run `config.quality.mutation_command` against changed source files (timeout: 300s)
   - Common tools:
     | Stack | Command |
     |-------|---------|
     | Python | `mutmut run --paths-to-mutate={changed_files} --runner="pytest {test_files}"` |
     | JavaScript | `npx stryker run --mutate='{changed_files}'` |
     | Java | `mvn pitest:mutationCoverage -DtargetClasses={changed_classes}` |

2. Parse mutation score (killed mutants / total mutants x 100)

3. **Verdict:**
   - Mutation score >= 70% → **PASS** (tests are meaningful)
   - Mutation score 40-69% → **WARN** (`"Mutation score {score}%: tests may not catch real bugs. Consider strengthening assertions."`)
   - Mutation score < 40% → **WARN** (strong) (`"Mutation score {score}%: tests are weak — {survived_count} mutations survived. Review test quality."`)
   - Tool not configured → **SKIP**

4. **Report:** Include mutation score in final completion report alongside other metrics.

**Note:** This gate is intentionally advisory-only. Mutation testing is computationally expensive and may produce false positives (equivalent mutants). The goal is awareness, not blocking.

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
3. **Path 1/3 final lightpath gate (fail-closed):**
   Run:

   ```powershell
   scripts/lightpath-gate.ps1 -Scope final -ProjectRoot <project-root> -Phase <phase> -DiffRange <first-task-start-hash>..HEAD
   ```

   - `pass` -> continue.
   - `review_pending` -> dispatch `ezpowers:wiring-reviewer` with plan path,
     diff range, `wiring-gate.json`, and runtime artifacts. Record the verdict
     with `scripts/lightpath-gate.ps1 -Scope final -ReviewerVerdict <verdict>`
     and rerun/finalize the gate.
   - `test_gap`/`code_gap`/`spec_gap`/`fail` -> do not complete. Re-dispatch
     the responsible implementer or return to `/plan` according to the verdict.
   - Missing or malformed `lightpath-gate.json`/`wiring-gate.json` is
     `TEST_GAP`.
4. **Wiring Gate Test detail (fail-closed):**
   Path 1/3 run these rules through `lightpath-gate.ps1`; Path 2 receives the
   same verdict from `/executeharness`. Apply Wiring Config Validation
   (Section 3.7). If exempt/skip, skip wiring gate.
   - Plan `## Full-Feature Wiring Gate` with `Required: yes`:
     - `config.wiring.wiring_gate_command` non-empty → 실행 (timeout: 120s).
     - `config.wiring.wiring_gate_command` empty → plan의 Wiring Gate Verify 커맨드 사용.
     - 양쪽 모두 empty → FAIL: `"Required wiring gate has no executable command."`
   - `wiring.enabled: true` + plan에 2개 이상 연결된 task 존재 + `## Full-Feature Wiring Gate` 없음 → FAIL: `"Connected tasks exist but plan has no Full-Feature Wiring Gate. Return to /plan."`
   Exit 0 = PASS. Non-zero = FAIL.
   FAIL → 테스트 출력에서 실패 뷰/파이프라인 식별, Coverage Matrix로 Task 역추적, 해당 Task implementer 재디스패치. Max 3 retries → user 에스컬레이션.
   `Required: yes` → skip 불가. 테스트 파일 미존재 → 테스트 작성 Task를 자동 추가.
5. **Smoke/runtime gate:** Run the configured runtime probe. If `config.smoke.required: true`, missing `config.smoke.command` is FAIL. Empty smoke may skip only for `artifact_kind: docs|library` with `required: false`. Any failure enters the fix loop (max 3).

   **GUI smoke (if `config.smoke.gui_strategy` is not `skip` and not absent):**
   Execute the gui_strategy probe after smoke command:
   - `process_probe`: start app → survive N seconds → no fatal stderr → window handle exists → kill. PASS/FAIL by exit code.
   - `screenshot_vision`: process_probe + capture screenshot + deterministic non-blank check. PASS/FAIL.
   - `headless`: run `config.smoke.command` as headless test runner (Playwright, Avalonia.Headless, FlaUI). Exit 0 = PASS.
   - Vision is not a v1 hard gate; deterministic process/window/screenshot/UIA evidence is required.
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
   | 18 | Expected UI text/name missing |
   | 20 | Timeout |
   | 30 | Unsupported platform |

6. Dispatch `ezpowers:workflow-runner` to invoke `/sync-docs` in
   `auto-from-choiceexecutor` mode:

   ```
   Agent tool:
     subagent_type: "ezpowers:workflow-runner"
     description: "Sync reference docs after implementation"
     prompt: |
       **Target command:** /sync-docs
       **Invocation mode:** auto-from-choiceexecutor
       **Working directory:** <absolute project root>
       **Plan artifact:** <absolute path to plan file>
       **Diff range:** <first-task-start-hash>..HEAD
       **Completed tasks:** <completed/failed/SKIPPED task list>
       **Changed files:** <newline-separated changed files>
   ```

   Status handling:
   - `DONE`: docs were updated, verified, and committed.
   - `NO_CHANGES`: docs already match the codebase.
   - `NEEDS_USER`: report the required decision and pause build completion until it is resolved.
   - `FAIL`: report the sync failure and route to `/sync-docs` for manual recovery.

   After workflow-runner returns, record the result in `phases/index.json`:
   ```json
   {
     "docs_sync": {
       "status": "DONE | NO_CHANGES | NEEDS_USER | FAIL",
       "timestamp": "<ISO 8601>",
       "changed_docs": ["docs/reference/..."],
       "commit": "<hash or null>"
     }
   }
   ```

7. **Conditional eval regression check (advisory):**
   If changed-files include any path under `commands/`, `agents/`, or
   `skills/`, run `/eval` to detect cumulative regression across all tasks.
   Record result in `phases/index.json` under `eval_check`. This gate is
   advisory — WARN on regression, never FAIL or block completion.

8. Next recommendation: `/review`

Update `phases/index.json`:
- build: `status: "complete"`, `completed_at: "<ISO 8601>"`
