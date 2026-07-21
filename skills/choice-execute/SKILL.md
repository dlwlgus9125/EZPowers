---
name: choice-execute
description: Select and run execution path for plan tasks
disable-model-invocation: true
argument-hint: "[plan-path] | Path 2"
allowed-tools: [Bash, Read, Write, Edit, Agent, AskUserQuestion]
---

# /choice-execute — Execution Path Selection

Source contracts: `docs/reference/domain-language.md`, `docs/reference/verification-contract.md`, `docs/reference/ui-verification-adapter-contract.md`, `docs/reference/dispatch-protocol.md`, `docs/reference/reviewer-placement-contract.md`, `docs/reference/model-routing-contract.md`, `docs/reference/strict-execution-adapter.md`.
Execute tasks from the plan document. Choose an execution mode (subagent / harness / inline), then run tasks + AC verification + conditional security review + final code review.

Gate scripts are required runtime dependencies. If `scripts/lightpath-gate.ps1`,
`scripts/harness-certify.ps1`, `scripts/harness-resume-proof.ps1`, or
`scripts/verify-step.py` is missing, run `/reset-setup` to reinstall the
manifest helpers. If the helper is still missing, stop as `TEST_GAP`; never
replace a missing gate script with inline verification.

## 1. Pre-flight Checks

Verify the following first:
1. `.harness/config.json` exists
2. Plan document exists (priority: argument > `phases/index.json` plan.artifact > latest file at config `defaults.plan_location`)
3. Spec document referenced by the plan exists
4. `phases/index.json` audit gate:
   - `audit.status` is `"FAIL"` → report `"internal pipeline audit has unresolved findings. Fix them and rerun the internal audit."` and stop
   - `audit` field is missing → report `"Run the internal pipeline audit first."` and stop
   - `audit.status` is `"PASS"` or `"WARN"` → proceed

If missing, direct the user to the required step:
- No config -> `/setup`
- No plan -> `/prepare-execute`
- No spec -> `/spec`
- No audit or audit FAIL -> `internal pipeline audit`

If `phases/index.json` exists, update the build phase to `in_progress`:
```json
{ "current_phase": "build", "phases": { "...": "...", "build": { "status": "in_progress" } } }
```

### Previous Session Re-entry Detection

If the build phase in `phases/index.json` is already `in_progress` and the plan has tasks checked with `- [x]`, treat it as a possible resumed session. Checkboxes are progress hints, not PASS evidence.

Before offering to skip any checked task, run resume proof for the checked prefix:

```powershell
scripts/harness-resume-proof.ps1 -ProjectRoot <project-root> -Phase <phase> -PlanPath <plan-path> -CompletedTaskCount <N> -ResumeHash <resume-hash>
```

Read `phases/<phase>/resume-proof.json` directly. Only tasks accepted by this proof may be skipped. Missing, stale, nonpassing, timed-out, or too-short e2e task-gate evidence is a `TEST_GAP`/`FAIL` and routes to re-run, not resume.

Present options to the user:

> **Previous session: Tasks 1-{N} are checked. Resume proof determines which are verified.**
>
> **1. Resume verified prefix** - skip only tasks accepted by `resume-proof.json`, continue from the first unverified task
>
> **2. Re-run that task** - reset the first unverified or incomplete task checkbox, re-implement from scratch (existing commits kept; implementer reworks on current state)
>
> **3. Full re-run** - reset all checkboxes (`- [x]` -> `- [ ]`), update `first-task-start-hash`, re-run everything
>
> **4. Abort** - keep current state

Option behavior:
- **Resume verified prefix:** Apply Resume Protocol (Section 13). Skip only the task prefix that passed `scripts/harness-resume-proof.ps1`; a checkbox alone never means PASS.
- **Re-run that task:** Reset the first unverified or incomplete task's `- [x]` to `- [ ]`. No git revert - implementer re-implements on existing code without conflicts.
- **Full re-run:** Reset all checkboxes to `- [ ]`. Remove `**Resume hash:**` marker. Record new `first-task-start-hash`.
- **Abort:** No action.

## 2. Execution Path Selection

Ask the user for the execution mode:

> **Plan: `<plan-path>` — {task-count} tasks**
>
> **1. Subagent-driven (recommended)** — fresh agent per task, fast iteration
>
> **2. Harness execution (Strict Path)** — step-by-step execution via EasyPowersHarness Python executor (`harness.root` required)
>
> **3. Inline execution** — sequential execution in the current session
>
> **Which mode?**

**Recommendation guide:**
- 1-3 tasks, independent → **inline** (fast and lightweight)
- 4+ tasks → **subagent-driven** (context isolation)
- `harness.root` configured + external harness logs or step-level recovery needed → **harness**
- All paths are fail-closed for Verify, runtime smoke, and Full-Feature Wiring Gate. Harness is the external executor/recovery path, not the only strict verification path.

After selecting the path, show the configured default model from
`.harness/config.json` `executor` and ask once whether to use it or override it
for this run. Apply the selected model to subagent dispatch or Path 2
execution by passing `-ExplicitModel <model>` to `scripts/harness-run.ps1`,
which sets `EZPOWERS_MODEL` for the harness executor. Keep reviewer model
routing separate unless the user explicitly overrides reviewer settings.

Path 2 follows `docs/reference/strict-execution-adapter.md`.

## 3. Task Graph Analysis

Analyze task dependencies before execution. Per task, identify: **explicit**
dependency (`Depends on: Task N`), **file overlap** dependency
(`**File overlap with:** Task N`, pre-computed by /prepare-execute — trust
over implicit when present), and **implicit** dependency (same `Modify:` file;
normalize paths — strip trailing slash, unify case — then exact string
comparison, no partial matching). Build the directed graph
(Task A -> Task B = "B depends on A") and classify:

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

All classifications dispatch sequentially ("independent" means order-agnostic,
not concurrent). Per-task AC verification + conditional security review run
after each task regardless of classification.

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
        -> TEST_GAP/CODE_GAP/SPEC_GAP -> re-dispatch or return to /prepare-execute
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

Before every dispatch (initial and re-dispatch), record the current task's
Verify Command Baseline and run the Verify Fidelity Check between prompt
construction and dispatch. Canonical procedure:
`docs/reference/verification-contract.md` § Verify Command Baseline & Fidelity
Check. Any prompt/plan Verify mismatch → **HALT.** Log:
`Verify Fidelity FAIL: plan=\`<plan>\`, prompt=\`<prompt>\`. Correct prompt.`
Re-check, then dispatch only when all entries match. This is a hard gate, not
advisory.

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
2. Execute each Verify command and check exit codes (exit 0 = PASS). Use the
   Verify-type timeouts from `docs/reference/verification-contract.md`
   § Execution Verification (`pure`/`cli`/`api` 30s, `data` 60s, `e2e` 120s);
   pass the same value in milliseconds as the Bash tool `timeout` parameter.
3. **Server management (e2e/api):** if `config.server.start_command` is set,
   start the server in the background, poll `config.server.health_check_url`
   (max `config.server.health_check_timeout` seconds, default 15s; 5s fixed
   wait when no URL is set), run Verify, then stop via
   `config.server.stop_command` (or kill the started process). If
   `start_command` is empty, skip server management.
4. No Verify commands: fall back to the plan's verification method.
5. ALL PASS -> conditional security review. ANY FAIL -> re-dispatch with
   failure details. **Re-dispatch loop:** max 3. Then escalate to user.

**Runtime probe (executable artifacts only):** after all Verify commands PASS,
if the task has a `Runtime verification:` line in the plan, run it (timeout:
30000ms); exit 0 = PASS, non-zero -> re-dispatch with error output + exit
code; no line -> skip. Runtime probe is separate from AC verification: AC
verifies spec behavior, the probe verifies the artifact starts and survives.
Both must pass. GUI executable tasks use the multi-layer probe (process
survival, fatal output check, window existence, screenshot non-blank check,
optional UI Automation oracle) defined in
`docs/reference/verification-contract.md` § Runtime Probe; any layer FAIL ->
re-dispatch implementer with the specific layer and exit code.
Desktop/server/CLI artifacts may not skip runtime smoke. Only
`artifact_kind: docs|library` with `config.smoke.required: false` may skip.

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

**Arbiter verdicts** follow `docs/reference/verification-contract.md`
§ Arbiter Verdicts: **PASS** → proceed to conditional security review;
**TEST_GAP** → re-dispatch implementer: "Verification does not prove the Then
clause. Write a probe that directly observes [specific Then clause].";
**CODE_GAP** → re-dispatch implementer with the verification evidence showing
the implementation fails; **SPEC_GAP** → return to /prepare-execute
automatically (Section 13).

**Arbiter dispatch limit:** max 2 rounds per task. If arbiter returns TEST_GAP or CODE_GAP twice, escalate to user.

### View Wiring Test (Per-Task, fail-closed)
**Config validation:** Apply Wiring Config Validation (Section 3.7).

**Detection:** with `wiring.enabled: true`, check whether the task's
changed-files include extensions matching `config.wiring.view_extensions`.
**Execution:** extract Verify commands from the task's `**View wiring
verification**` section; a changed view file with no such section is FAIL
(plan omitted wiring verification). Run the command (timeout: 120s); exit 0 =
PASS. On FAIL, classify the defect with the W1-W5 taxonomy from
`docs/reference/verification-contract.md` § View Wiring Verification and
re-dispatch implementer: "View Wiring Test failed. Defect type: [W1-W5].
[output excerpt]. Fix the wiring defect." Max 3 retries → user escalation.
`wiring.enabled: true` with non-empty `view_extensions` and changed view files
→ no skip. **Inline execution (Path 3):** same detection/execution;
fix-in-place instead of re-dispatch.

### Incremental Runnability (executable artifacts, post-skeleton)

**Trigger:** `config.smoke.artifact_kind` is `cli`/`server`/`desktop` AND at
least one `{skeleton}` task has completed and passed runtime smoke. Every
subsequent task must pass `config.smoke.command` before proceeding (same
timeout as the Section 14 smoke gate; if `config.smoke.gui_strategy` is
configured, run the same GUI probe as Section 14). Exit 0 = PASS. Failure →
re-dispatch implementer: "Runtime smoke failed after your changes. The app no
longer starts. Fix the regression before proceeding." Max 2 retries →
escalate to user. Canonical semantics:
`docs/reference/verification-contract.md` § Incremental Runnability.

### Incremental Wiring Probe (executable artifacts, post-skeleton)

**Trigger:** Task has a `**Wiring probe:**` section in the plan AND at least
one `{skeleton}` task has completed. Extract the Wiring Probe Verify command
from the plan file (not from implementer reports or cached context) and run it
(timeout: 120s); exit 0 = PASS. On FAIL, classify the failure
(`IMPORT_UNREACHABLE` / `REGISTRATION_MISSING` / `RUNTIME_UNREACHABLE`) and
re-dispatch implementer: "Wiring Probe failed: [type]. Module [path] is not
reachable from entry point [path]. Add the missing import/registration." Max 2
retries → escalate to user. Missing-probe and refactoring-rename detection
follow `docs/reference/verification-contract.md` § Incremental Wiring Probe:
log WARNING `"Task N creates [path] but has no Wiring Probe. Plan defect."`
and surface it in the completion report. **Inline execution (Path 3):** same
detection/execution; fix-in-place instead of re-dispatch.

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

**Tiered escalation:** per-review-type max/warn/stop limits follow the review
loop table in `docs/reference/dispatch-protocol.md` § Retry And Oscillation.
If the Verdict header is missing 2 consecutive times for any review type,
immediately escalate to user.

**PASS_WITH_ISSUES handling:** conditional PASS per the dispatch protocol —
exactly 1 additional fix-and-review round for Important issues; second review
PASS or PASS_WITH_ISSUES → accept; FAIL → enter the FAIL loop at iteration
count 2. Max 3 PASS_WITH_ISSUES rounds total prevents endless
Important-issue churn.

**Exemption check:** Before entering the review loop:
- `AGENTS.md` has `review-skip:` pattern?
- User explicitly requested review skip?
- Auto-excluded: lock files, generated, binary, git metadata, <20-line configs
- If true, skip the review loop.

**Large output handling:** 500+ line diff or 10+ files -> split review by task boundary or directory. No splitting within a single file. All chunks must PASS.

## 8. Controller Context Hygiene

**Subagent prompt sizing:** include the task text and completion criteria
verbatim in the prompt (see implementer-prompt.md template); extra context
(architecture notes, dependency descriptions) ~2K tokens max. Do not paste the
full plan/spec — provide paths only. Do not pre-read source files into the
prompt — the subagent reads with fresh context.

**Between-task cleanup:** preserve only task status (pass/fail), changed
files, unresolved issues, and lightpath evidence as paths + verdicts
(`lightpath-gate.json`, `wiring-gate.json`, runtime artifact names, short
failure tails). Do not preserve subagent full output, review details, or
intermediate reasoning. The controller owns the final completion decision but
delegates mechanical checks to gate scripts and qualitative checks to
reviewer/arbiter subagents, parsing only status lines and verdict enums.

**Context pressure relief:** before Task 5, compact on pressure detection;
after Task 5, compact proactively. "Compact" = stop referencing prior
subagent output/review details and proceed using only work notes (remaining
task numbers/titles, cumulative changed files, unresolved issue summary,
per-task PASS/FAIL). Past Task 10, suggest `/compact` or a fresh session.

### Context Anchoring in Subagent Prompts

Include in implementer prompts for tasks modifying existing files:

> Before writing any code:
> 1. Read the module's AGENTS.md (if it exists)
> 2. Run `git log --oneline -10 [module-directory]`
> 3. Read related files until you can describe: (a) error handling pattern, (b) naming/structure pattern, (c) recent change direction
> 4. Output a 3-line pattern summary before proceeding

### Model Selection

- Read `executor.agent`, `executor.backend`, and
  `executor.model_routing.default_profile` from `.harness/config.json`.
- Ask once: use the configured default for this run, or override the execution
  model. Record the answer in the run notes.
- **Implementer:** selected execution model, or router-selected coding model.
- **Path 2:** pass the selected execution model as
  `scripts/harness-run.ps1 -ExplicitModel <model>` so the executor receives
  `EZPOWERS_MODEL`.
- **Security reviewer:** reviewer routing from `docs/reference/model-routing-contract.md`.
- **Final code reviewer:** reviewer routing from `docs/reference/model-routing-contract.md`.

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
3. **Context Injection Check:** If the prompt contains `EZP_CONTEXT` sentinels, run `python scripts/context-injector.py verify --file <prompt-file> --json`; duplicate or missing markers block dispatch.

## 9. Degradation Detection and Response

| Signal (controller-tracked) | Response |
|-----------------------------|----------|
| NEEDS_CONTEXT 2+ times on the same task (per-task counter) | Re-assess complexity, consider splitting |
| Same issue category recurs across tasks (classify by `[severity]` keyword) | Session-level: 3+ tasks degraded → reconsider plan decomposition |
| Implementer self-reports reading 8+ files (match "Files read:"/"read N files") | Compact controller context |
| 3+ re-dispatch cycles (per-task dispatch counter) | Re-assess complexity + splitting |
| Task completion counter ≥ 5 | Proactive compact (Section 8) |

If degradation persists after compaction + splitting → save state + suggest a
fresh session.

## 10. Harness Execution (Path 2, Strict Path)

When the user selects Path 2, load `docs/reference/strict-execution-adapter.md` and follow that
command as the source of truth for all harness conversion, execution, recovery,
and restoration behavior. Do not duplicate the harness procedure here.

After `/choice-execute Path 2` reports all steps complete, require its full-feature
wiring gate verdict before continuing:

- Read `phases/<phase>/wiring-gate.json` directly. Do not rely only on the
  `/choice-execute Path 2` status line or process exit code.
- `PASS` or `pass` -> continue at Section 12 (Final Code Review) using the diff range
  returned by `/choice-execute Path 2` (`<harness-start-hash>..HEAD`)
- `review_pending` -> dispatch `ezpowers:wiring-reviewer` with plan path,
  diff range, `wiring-gate.json`, runtime artifacts, and run log path. Write
  the verdict to `wiring-gate.json.reviewer_verdict`, rerun
  `scripts/harness-gate.ps1 -ProjectRoot <project-root> -Phase <phase>`, then
  reread `wiring-gate.json`. Continue only if status becomes `pass`.
- `TEST_GAP` -> stop and return to `/prepare-execute` or reset the probe-writing step
- `CODE_GAP` -> reset the related harness step and rerun `/choice-execute Path 2`
- `SPEC_GAP` -> return to `/prepare-execute`
- `fail`, `pending`, or any unknown status -> do not complete; report the gate
  status and recovery route
- Missing or malformed wiring verdict -> treat as `TEST_GAP`

Path 2 completion requires `all steps completed + wiring gate PASS + Final Code
Review PASS`. Step completion alone is not enough.

## 11. Inline Execution (Path 3)

When the user selects Path 3, load
`docs/reference/inline-execution-adapter.md` and follow it as the source of
truth for the inline context pre-check, per-task fix-in-place loop, and gate
equivalence rules. Do not duplicate the inline procedure here.

Inline runs all work in the controller's context. Verification gates are
identical to the subagent path (Sections 4a/4b, 5, and 6), with re-dispatch
replaced by fix-in-place -> re-verify at the same retry limits. After all
tasks complete, continue at Section 11a (Quality Budget) and Section 12
(Final Code Review).

## 11a. Quality Budget Verification Gate

**Trigger:** After all tasks complete, before Final Code Review. Only for
budgets where `verify_command` is specified in the spec's Quality Budgets
section. Canonical procedure: `docs/reference/verification-contract.md`
§ Quality Budget Gate.

- All budgets PASS or SKIP → overall **PASS**.
- `hard ceiling/floor` FAIL → **FAIL**: re-dispatch the last relevant task
  (max 2 retries). `soft ceiling/floor` FAIL → **WARN** (advisory).
- No `verify_command` configured → **SKIP** (log: `"No Quality Budget verify
  commands configured"`).

Include the per-budget table (target vs measured vs verdict) in the final
completion report.

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

**Trigger:** After Final Code Review, before Completion. Run
`config.quality.duplication_command` against changed files when configured;
otherwise run the heuristic pair-similarity check. Canonical procedure and
thresholds: `docs/reference/verification-contract.md` § Code Duplication Gate.
**Verdict:** WARN does not block. FAIL triggers 1 fix round (max 1 retry,
then downgrade to WARN).

### 12b. Mutation Testing Gate (Optional)

**Trigger:** Only when `config.quality.mutation_command` is configured.
Advisory gate (WARN only, never FAIL). Run the command against changed source
files (timeout: 300s), parse the mutation score, and report per the
thresholds in `docs/reference/verification-contract.md` § Mutation Testing
Gate. Include the score in the final completion report.

## 13. Backward Transition: Return to /prepare-execute

If plan decomposition proves inadequate during execution — tasks too tightly coupled, missing dependencies, misaligned boundaries — do not force a broken plan.

**Triggers:** 2+ tasks modify the same file in conflicting ways; task
prerequisites missing from the plan; task ordering assumptions wrong given the
actual codebase; 2+ consecutive tasks BLOCKED for structural reasons.

**Actions:** Log and report "Returning to /prepare-execute: [specific
reason]". Save progress: check completed tasks' checkboxes (`- [x]`) in the
plan, leave incomplete tasks unchecked as re-plan targets, record
`**Resume hash:** <first-task-start-hash>` in the plan header, and commit
(`wip: build progress saved before /prepare-execute return — Tasks 1-N
complete`). Update `phases/index.json` (build `pending`, plan `in_progress`),
return to `/prepare-execute`, then resume `/choice-execute` with the updated
plan.

### Resume Protocol (after returning from /prepare-execute)

1. Check for `**Resume hash:**` marker in plan document
2. If present: restore previous `first-task-start-hash` (preserves final review diff range)
3. Count the contiguous checked task prefix and run `scripts/harness-resume-proof.ps1` for that prefix.
4. Skip only tasks that are listed in `resume-proof.json` with status `pass`; checkboxes are progress hints, not PASS evidence.
5. Execute the first unchecked or unverified task and all following tasks, including newly added tasks.
6. If a checked task lacks fresh passing task-gate proof, reset that task to `- [ ]` and re-run from there. Do not skip it from checkbox state.
7. **Caution:** If the revised plan modifies files from already-completed tasks, those tasks must be manually reset to `- [ ]` - /prepare-execute notifies the user

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
     the responsible implementer or return to `/prepare-execute` according to the verdict.
   - Missing or malformed `lightpath-gate.json`/`wiring-gate.json` is
     `TEST_GAP`.
   - `scripts/harness-certify.ps1` must produce a PASS completion certificate before completion.
4. **Wiring Gate Test detail (fail-closed):**
   Path 1/3 run these rules through `lightpath-gate.ps1`; Path 2 receives the
   same verdict from `/choice-execute Path 2`. Apply Wiring Config Validation
   (Section 3.7). If exempt/skip, skip wiring gate.
   - Plan `## Full-Feature Wiring Gate` with `Required: yes`: run
     `config.wiring.wiring_gate_command` when non-empty (timeout: 120s); when
     empty, use the plan's Wiring Gate Verify command; both empty → FAIL:
     `"Required wiring gate has no executable command."`
   - `wiring.enabled: true` + plan has 2+ connected tasks + no
     `## Full-Feature Wiring Gate` → FAIL: `"Connected tasks exist but plan
     has no Full-Feature Wiring Gate. Return to /prepare-execute."`
   Exit 0 = PASS. Non-zero = FAIL. On FAIL, identify the failed view/pipeline
   from test output, trace back to the responsible task via the Coverage
   Matrix, and re-dispatch that task's implementer. Max 3 retries → user
   escalation. `Required: yes` → no skip. Missing test file → auto-add a
   test-writing task.
5. **Smoke/runtime gate:** Run the configured runtime probe. If `config.smoke.required: true`, missing `config.smoke.command` is FAIL. Empty smoke may skip only for `artifact_kind: docs|library` with `required: false`. Any failure enters the fix loop (max 3).

   **GUI smoke (if `config.smoke.gui_strategy` is not `skip` and not absent):**
   Execute the gui_strategy probe after the smoke command — `process_probe`
   (start → survive → no fatal stderr → window handle → kill),
   `screenshot_vision` (process_probe + screenshot + deterministic non-blank
   check), or `headless` (run `config.smoke.command` as a headless test
   runner; exit 0 = PASS). Vision is not a v1 hard gate; deterministic
   process/window/screenshot/UIA evidence is required. GUI smoke FAIL → same
   fix loop (max 3), no user confirmation. Failures map to the exit code
   convention in `docs/reference/verification-contract.md` § Runtime Probe
   (e.g. 13 = No main window, 18 = Expected UI text/name missing).

6. Dispatch `ezpowers:workflow-runner` to invoke `/sync-docs` in
   `auto-from-choice_execute` mode:

   ```
   Agent tool:
     subagent_type: "ezpowers:workflow-runner"
     description: "Sync reference docs after implementation"
     prompt: |
       **Target command:** /sync-docs
       **Invocation mode:** auto-from-choice_execute
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
