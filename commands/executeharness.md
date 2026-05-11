---
description: Delegate plan execution to EasyPowersHarness executor
argument-hint: "[phase] [--status|--reset-step N|--push]"
allowed-tools: [Bash, Read, Write, Agent]
---

# /executeharness — EasyPowersHarness Execution Delegation

Execute plan tasks step-by-step through the EasyPowersHarness Python executor (`scripts/execute.py`).
This command is a thin wrapper; the actual step execution is handled by the harness's Python executor.

<HARD-GATE>
Do not copy execute.py into EZPowers. Reference the harness install path and delegate.
</HARD-GATE>

## 1. Pre-flight Checks

Verify the following first:
1. Harness path from `.harness/config.json` `harness.root` field
2. `{harness.root}/scripts/execute.py` exists
3. Plan document exists
4. `phases/index.ezpowers.json` remnant — previous harness run terminated abnormally without restoration

If `phases/index.ezpowers.json` exists:
> "A previous harness run appears to have terminated abnormally. Restore the EZPowers index from `phases/index.ezpowers.json`?"
>
> 1. Restore then proceed — restore `phases/index.ezpowers.json` → `phases/index.json`, then delete the backup
> 2. Discard backup then proceed — delete `phases/index.ezpowers.json`, use current `phases/index.json` as-is
>
> Either option handles the previous backup immediately, so it will not conflict with Section 7 (Restoration) for the current session's backup.

If `harness.root` is empty or unset:
> "`harness.root` is not configured. Set it in /setup, or use `/choiceexecutor` Path 1 (subagent) or Path 3 (inline)."

If `execute.py` not found:
> "EasyPowersHarness not found at `{harness.root}`. Check the path."

## 2. Git Hash Capture

Record the current commit hash before conversion:

```bash
git rev-parse HEAD
```

Store as `<harness-start-hash>`. Used as the diff range for Final Code Review after execution.
No commits yet: use empty tree hash `4b825dc642cb6eb9a060e54bf899d8b2306e7304`.

## 3. Plan → Phase Conversion

Convert plan tasks into harness step files.

### 3-1. Phase Directory Creation

```bash
mkdir -p phases/{feature-name}
```

`{feature-name}`: kebab-case name from the plan filename with date prefix removed.
Example: `2026-04-22-user-auth.md` → `user-auth`

### 3-2. phase-context.md Generation

`phases/{feature-name}/phase-context.md`:

```markdown
# {Feature Name}

## Goal
{Goal from plan header verbatim}

## Architecture
{Architecture from plan header verbatim}

## Tech Stack
{Tech Stack from plan header}

## Spec
{Spec file path}

## Constraints
{Boundaries section from AGENTS.md — copy if present, omit if not}
```

### 3-3. Task → Step Field Mapping

Convert each plan Task N to `phases/{feature-name}/step{N-1}.md` (harness executor is 0-indexed).

**Numbering rule:** `Task N → step{N-1}.md` (e.g., Task 1 → step0.md, Task 2 → step1.md, Task 3 → step2.md)
`--reset-step` argument is also 0-indexed, so to reset Task 3, use `--reset-step 2`.

| EZPowers Plan Task Field | Harness Step Section | Conversion Rule |
|--------------------------|---------------------|-----------------|
| Task title (`### Task N: [Name]`) | `# Step {N-1} (Task N): [Name]` | Number conversion + Task number notation |
| `**Files:**` (Create/Modify/Test) | `## Files to Read` | List Modify/Test files |
| Full task text | `## Task` | Copy verbatim including Impact scope, Depends on |
| `**Completion criteria (from spec):**` | `## Acceptance Criteria` | Copy Given/When/Then/Verify verbatim |
| `**Verification method:**` | `## Verification` | Copy Verify commands |
| Test file path + related doc paths | `## tools` | List file paths in prompt format |
| N/A | `## Forbidden` | Omit (do not create section if empty) |

Step file result structure:

```markdown
# Step {N-1} (Task N): {task name}

## Files to Read
- `{Modify file path}`
- `{Test file path}`

## Task
{Full task text verbatim}

## Acceptance Criteria
{Completion criteria verbatim — Given/When/Then/Verify format as-is}

## Verification
{Verification method verbatim}

## tools
- `{Test file path}`
- `{Related spec/plan path}`
```

### 3-4. phases/{feature-name}/index.json Generation

index.json following the harness executor schema:

```json
{
  "project": "{config.project}",
  "phase": "{feature-name}",
  "created_at": "{ISO 8601}",
  "steps": [
    {
      "step": 0,
      "name": "{task 1 name}",
      "status": "pending",
      "step_md": "step0.md"
    },
    {
      "step": 1,
      "name": "{task 2 name}",
      "status": "pending",
      "step_md": "step1.md"
    }
  ]
}
```

### 3-5. wiring-gate.json Generation

Create `phases/{feature-name}/wiring-gate.json` from the plan's
`## Full-Feature Wiring Gate`.

If the plan requires a wiring gate but the section is missing, stop before
conversion and return to `/plan`.

If the plan is exempt, still create the file with `required: false`,
`status: "pass"`, and `reason: "single-task library-only or no executable
artifact"`.

Required schema:

```json
{
  "phase": "{feature-name}",
  "required": true,
  "verify_type": "e2e",
  "commands": ["{Full-Feature Wiring Gate Verify command}"],
  "covered_tasks": ["T1", "T2"],
  "covered_edges": ["T1->T2"],
  "expected_observation": "{Expected observation text}",
  "status": "pending",
  "attempts": []
}
```

Rules:
- `status` is one of `pending`, `pass`, `fail`, `spec_gap`, `test_gap`, `code_gap`.
- A required gate with no executable command is `spec_gap`, not complete work.
- Keep one attempt record per gate run: command, exit code, stdout/stderr tail, timestamp.

### 3-6. Top-level phases/index.json Protection

EZPowers' `phases/index.json` and the harness executor's top-level index may have schema conflicts.

**Protection procedure:**
1. Copy existing `phases/index.json` to `phases/index.ezpowers.json` (backup)
2. Run harness (harness uses `phases/index.json` freely)
3. After execution, restore `phases/index.json` from `phases/index.ezpowers.json`
4. Update the restored EZPowers index's build phase based on results

### 3-7. Commit Converted Files

```
chore: convert plan to harness phase — {feature-name}
```

## 4. Step-by-Step Execution

Due to Bash tool timeout limits (max 600s), run steps individually in a loop rather than the entire phase at once.

### Execution Loop

```
for each pending step:
  1. python "{harness_root}/scripts/execute.py" {feature-name}
     (executor runs the first pending step and exits)
     Bash timeout: 600000
  2. Read phases/{feature-name}/index.json to check step status
  3. Map status + report
  4. error/blocked → escalate to user, break loop
  5. completed → next step
```

The final harness call must run in strict runtime-gate mode. Executable
artifacts require `smoke.required: true` and a non-empty `smoke.command`;
desktop artifacts also require `gui_strategy != "skip"`. Missing required
runtime smoke is failure, not skip. Only docs/library artifacts with
`smoke.required: false` may skip.

### Status Mapping

| Harness Status | EZPowers Equivalent | Meaning |
|----------------|-------------------|---------|
| `completed` | PASS | Step succeeded |
| `error` | FAIL | Step failed |
| `blocked` | BLOCKED | User intervention needed |
| `rejected` | FAIL (verifier) | Verifier rejected |
| `pending` | Not executed | Not yet run |

### Argument Support

When the user invokes `/executeharness` directly:

- `/executeharness {phase}` — execute pending steps sequentially
- `/executeharness {phase} --status` — print step status table (foreground, Bash timeout: 30000)
- `/executeharness {phase} --reset-step N` — reset step N to pending (foreground, Bash timeout: 30000)
- `/executeharness {phase} --push` — auto-push after completion

## 5. Full-Feature Wiring Gate

After every step is `completed`, run `phases/{feature-name}/wiring-gate.json`
before reporting harness success.

### Gate Execution

1. Read `wiring-gate.json`.
2. If `required` is false, keep `status: "pass"` and continue.
3. If `required` is true and `commands` is empty, set `status: "spec_gap"` and stop.
4. Execute every command from `commands` in the project root.
5. Record each attempt with command, exit code, stdout/stderr tail, and timestamp.
6. Any non-zero exit sets `status: "fail"` and stops completion.
7. Read `runtime-probe.json` / `smoke-output.json`; missing required runtime artifacts set `status: "test_gap"` and stop completion.
8. Dispatch `ezpowers:wiring-reviewer` for an independent verdict.

> **Dispatch protocol:** Read `docs/reference/dispatch-protocol.md` and follow the backend-appropriate dispatch path.

Wiring reviewer dispatch:

```
Agent tool:
  subagent_type: "ezpowers:wiring-reviewer"
  description: "Full-feature wiring review"
  prompt: |
    **Plan file:** <absolute plan path>
    **Diff range:** <harness-start-hash>..HEAD
    **Harness phase directory:** <absolute phases/{feature-name}>
    **Wiring gate:** <absolute phases/{feature-name}/wiring-gate.json>
    **Step status table:** <summarized phases/{feature-name}/index.json>
    **Wiring Verify output:** <command outputs and exit codes>
    **Smoke output:** <smoke-output.json content or skipped>
```

### Gate Verdict Handling

| Verdict | Action |
|---------|--------|
| `PASS` | Set `wiring-gate.json.status` to `pass`; continue to Final Code Review |
| `TEST_GAP` | Set `status` to `test_gap`; return to `/plan` or reset the probe-writing step |
| `CODE_GAP` | Set `status` to `code_gap`; reset the related step and rerun harness |
| `SPEC_GAP` | Set `status` to `spec_gap`; return to `/plan` |
| Missing or malformed verdict | Treat as `test_gap` and stop |

`all steps completed` is not a completion condition by itself. Completion
requires `all steps completed + wiring gate PASS + Final Code Review PASS`.

## 6. Failure Recovery

On step failure, guide the user to recovery:

```
Step {N} failed: {error summary}

Recovery:
1. Fix the root cause
2. /executeharness {phase} --reset-step {N}
3. /executeharness {phase}
```

## 7. phases/index.json Restoration

After all steps complete or on abort:

1. Restore EZPowers format `phases/index.json` from `phases/index.ezpowers.json`
2. Update build phase status:
   - All complete + wiring gate PASS → `complete` (after Final Code Review)
   - Partial failure → keep `in_progress`
3. Delete `phases/index.ezpowers.json`

## 8. Result Report + Final Code Review Connection

When all steps complete and the wiring gate verdict is `PASS`:

1. Print per-step PASS/FAIL/BLOCKED summary
2. Print wiring gate PASS evidence
3. Review full changes via `git diff <harness-start-hash>..HEAD`
4. Proceed to `/choiceexecutor` Final Code Review (Section 12):
   - Provide plan path
   - Diff range: `<harness-start-hash>..HEAD`
   - Note that this was the harness execution path

If the wiring gate is `fail`, `test_gap`, `code_gap`, or `spec_gap`, do not
proceed to Final Code Review and do not mark build complete.
