# Harness Execution Contract

This reference is the runtime source-of-truth for `/choice-execute` Path 2
(strict EasyPowersHarness execution) and Path 3 (inline execution). It holds
both the controller procedure and the supporting detail for each path.

## Source Contracts

- `docs/reference/verification-contract.md`
- `docs/reference/dispatch-protocol.md`
- `docs/reference/model-routing-contract.md`
- `docs/reference/domain-language.md`

## Path 2 — Strict (EasyPowersHarness) Execution

### Purpose

Run the strict execution path for a plan phase when step logs, external harness
state, runtime smoke, recovery, or full-feature wiring evidence are required.
Delegate to the installed EasyPowersHarness; do not copy its executor into this
repo. Light, independent work stays in `/choice-execute` Path 1 or Path 3.

### Inputs

Read before running:

- `docs/reference/verification-contract.md`
- `docs/reference/dispatch-protocol.md`
- `docs/reference/domain-language.md`
- `.harness/config.json`, `AGENTS.md`, `phases/index.json`
- Plan artifact, `phases/{phase}/index.json`, `wiring-gate.json`, run logs
- Current git hash and recent diff

### Controller Sequence

Run the strict path in this order: **doctor -> convert -> run -> gate ->
certify.**

1. Run `scripts/harness-doctor.ps1 -ProjectRoot <project-root> -Phase <phase>`
   before conversion or execution. Stop on FAIL. (Preflight below.)
2. Use `scripts/harness-phase.ps1` for `--status` and `--reset-step`; skip
   conversion when a usable phase already exists. (Mode Routing below.)
3. Use `scripts/harness-convert.ps1` for plan-to-phase conversion only when no
   usable phase exists. Preserve task categories and wiring handoffs in step
   files. The skeleton step (`step0`) must pass runtime smoke before feature
   steps begin. (Plan To Phase Conversion below.)
4. Use `scripts/harness-run.ps1 -ProjectRoot <project-root> -Phase <phase>` for
   step execution so timeout, progress, and attempt logs are controlled. If
   `/choice-execute` supplies an execution model override, add
   `-ExplicitModel <model>` to the same command. (Step Execution below.)
5. Use `scripts/harness-gate.ps1 -ProjectRoot <project-root> -Phase <phase>`
   for Full-Feature Wiring Gate evidence. If it records `review_pending`, stop
   with `PENDING_REVIEW` and return the artifact paths; the parent
   `/choice-execute` owns reviewer dispatch, verdict recording, and the final
   gate rerun. (Wiring Gate Execution below.)
6. Use `scripts/harness-certify.ps1 -ProjectRoot <project-root> -Phase <phase>`
   before reporting strict-path completion. (Completion Certificate below.)

Protect EZPowers `phases/index.json` from harness schema conflicts as defined
in EZPowers Phase Protection below. Before any reset or redispatch, identify
the failing Verify, runtime, or wiring signal — a completed step table is not
completion. Final success requires completed steps, wiring gate PASS, runtime
evidence when required, and restored EZPowers phase state. Final code review
remains owned by the parent `/choice-execute`.

### Stop Conditions

- `harness.root` is empty, invalid, or missing `{harness.root}/scripts/execute.py`.
- `harness-doctor.ps1` reports FAIL.
- Prior `phases/index.ezpowers.json` backup needs user choice.
- Conversion cannot produce valid step files, phase index, or wiring gate.
- Step execution times out, makes no progress, or returns failed/blocked status.
- Wiring gate returns `fail`, `test_gap`, `code_gap`, or `spec_gap`.
- Wiring gate returns `review_pending`; report `PENDING_REVIEW` for parent
  `/choice-execute` finalization.

### Outputs

- Phase name, start hash, and execution mode.
- Per-step status table and run log path.
- Runtime smoke and wiring gate evidence, including `gate_status`.
- Recovery instruction when stopped.
- Restored `phases/index.json` build state.
- Diff range for parent `/choice-execute` final review.

### Preflight

Run:

```powershell
scripts/harness-doctor.ps1 -ProjectRoot <project-root> -Phase <phase>
```

Stop on FAIL. Report WARN before continuing.

If `.harness/config.json` enables `executor.model_routing`, doctor validates
the default profile. Warning-only model routing results exit with code 2 and
must be shown to the user; fail results stop execution.

Verify:

- `.harness/config.json` exists.
- `harness.root` is configured.
- `{harness.root}/scripts/execute.py` exists.
- Plan document exists.
- Prior `phases/index.ezpowers.json` backup is resolved.

Capture the start hash with `git rev-parse HEAD`. If no commit exists, use the
empty tree hash `4b825dc642cb6eb9a060e54bf899d8b2306e7304`.

### Mode Routing

Avoid conversion work when a usable phase already exists.

- `--status`: call `scripts/harness-phase.ps1 -ProjectRoot <project-root> -Phase <phase> -Status` and stop.
- `--reset-step N`: identify the failing signal, then call `scripts/harness-phase.ps1 -ProjectRoot <project-root> -Phase <phase> -ResetStep N` and stop.
- Existing phase with pending steps: skip conversion and execute.
- New phase: convert the plan.

### Plan To Phase Conversion

Prefer:

```powershell
scripts/harness-convert.ps1 -ProjectRoot <project-root> -PlanPath <plan-path>
```

If the helper fails, report the failure and use the manual mapping only when it
is safe.

Feature name comes from the plan filename with the date prefix removed.

Create:

- `phases/{feature-name}/phase-context.md`
- `phases/{feature-name}/step0.md`, `step1.md`, ...
- `phases/{feature-name}/index.json`
- `phases/{feature-name}/wiring-gate.json`
- `phases/{feature-name}/anchors/*.hashline.json`

### Step Mapping

Harness steps are zero-indexed:

- Task 1 -> `step0.md`
- Task 2 -> `step1.md`
- `--reset-step 2` resets Task 3.

Step files include:

- Files to Read.
- Full task text.
- Task category (`skeleton`/`feature`/`wiring`/`integration-test`).
- Model profile (`balanced` by default, or `**Model profile:** <profile>`).
- Wiring handoff (if present in the plan task).
- Acceptance Criteria.
- Verification.
- tools.

Do not create an empty Forbidden section.

### Harness Phase Index

`phases/{feature-name}/index.json` uses:

```json
{
  "project": "project-name",
  "phase": "feature-name",
  "created_at": "2026-05-13T00:00:00Z",
  "steps": [
    {
      "step": 0,
      "name": "task name",
      "status": "pending",
      "step_md": "step0.md"
    }
  ]
}
```

Step statuses map to EZPowers as:

- `completed`: PASS.
- `error`: FAIL.
- `blocked`: BLOCKED.
- `rejected`: verifier FAIL.
- `pending`: not executed.

### Wiring Gate File

Create from the plan's Full-Feature Wiring Gate:

```json
{
  "phase": "feature-name",
  "required": true,
  "verify_type": "e2e",
  "commands": ["command"],
  "covered_tasks": ["T1", "T2"],
  "covered_edges": ["T1->T2"],
  "expected_observation": "observable result",
  "status": "pending",
  "evidence_status": "",
  "runtime_artifacts": [],
  "reviewer_verdict": "",
  "attempts": []
}
```

Allowed statuses:

- `pending`
- `review_pending`
- `pass`
- `fail`
- `spec_gap`
- `test_gap`
- `code_gap`

When a plan is exempt, create `required: false`, `status: "pass"`, and a
reason. Required gates with no command are `spec_gap`.

For client-server wiring, final runtime artifacts must include
`client_server_evidence.api_observation` inside `runtime-probe.json` or
`smoke-output.json`, or the backward-compatible
`desktop_evidence.api_observation` for desktop clients. This evidence proves
the client consumed server/API data; reviewer `PASS` does not replace it.

For desktop artifacts, final runtime artifacts must also include
`desktop_evidence` with a window signal, screenshot path, pixel variance, and
UI text, automation name, or API observation.

### EZPowers Phase Protection

The harness phase index and EZPowers phase index have different schemas.

Before harness execution:

1. Copy `phases/index.json` to `phases/index.ezpowers.json`.
2. Let the harness use `phases/index.json`.

After completion or abort:

1. Restore `phases/index.json` from `phases/index.ezpowers.json`.
2. Update EZPowers build status.
3. Delete `phases/index.ezpowers.json`.

If a backup exists before the run, ask whether to restore it or discard it.

### Step Execution

Prefer:

```powershell
scripts/harness-run.ps1 -ProjectRoot <project-root> -Phase <phase> -TimeoutSeconds 600
```

When `/choice-execute` selected a one-run execution model override, use:

```powershell
scripts/harness-run.ps1 -ProjectRoot <project-root> -Phase <phase> -TimeoutSeconds 600 -ExplicitModel <model>
```

The controlled runner executes pending steps, captures stdout/stderr tails,
writes `phases/{feature-name}/harness-run.json`, stops on timeout, and refuses
to continue when status makes no progress.

Before each external harness executor invocation, `harness-run.ps1` resolves the
step `model_profile` through `scripts/model-router.py` using backend
`harness-env`. It records the result in `harness-run.json` and passes it to the
executor through `EZPOWERS_MODEL*` environment variables.

After a step reports `completed`, `scripts/verify-step.py` is a hard gate. A
failed or missing verifier sets the step status to `rejected` and stops the run.
Every completed step must write `phases/{feature-name}/task-gates/task-N.json`
with the Verify command list, Verify result, step hash, and runtime smoke
result when applicable.

The final harness call must enforce runtime smoke for executable artifacts.
Missing required smoke evidence is a failure, not a skip.

After a `{skeleton}` step passes runtime smoke, every subsequent step must also
pass `config.smoke.command` before advancing. Failure sets step status to
`error` and triggers the recovery route.

### Wiring Gate Execution

Prefer:

```powershell
scripts/harness-gate.ps1 -ProjectRoot <project-root> -Phase <phase>
```

Gate rules:

- `required: false` keeps `status: "pass"`.
- Required gate with empty commands becomes `spec_gap`.
- Required gate with no-op commands (`echo`, `true`, `:`, `exit 0`, or simple
  output-only commands) becomes `spec_gap`.
- Any non-zero command exit becomes `fail`.
- Missing required runtime artifacts become `test_gap`.
- Attempts record command, exit code, stdout/stderr tail, and timestamp.
- Passing command evidence without an independent reviewer verdict becomes
  `review_pending`, not `pass`.
- `scripts/harness-gate.ps1` exits `5` for `review_pending`; it is not a
  successful completion.
- Parent `/choice-execute` dispatches `ezpowers:wiring-reviewer` through the
  dispatch protocol, then writes the verdict back to `wiring-gate.json` and
  reruns or finalizes the gate.

Reviewer verdict handling:

- `PASS`: set status `pass`.
- `TEST_GAP`: set status `test_gap`.
- `CODE_GAP`: set status `code_gap`.
- `SPEC_GAP`: set status `spec_gap`.
- Missing or malformed verdict: treat as `test_gap`.

Exit code contract:

- `pass`: 0.
- `fail`: 1.
- `spec_gap`: 2.
- `test_gap`: 3.
- `code_gap`: 4.
- `review_pending`: 5.

### Completion Certificate

Before strict-path or light-path completion, run:

```powershell
scripts/harness-certify.ps1 -ProjectRoot <project-root> -Phase <phase>
```

The certificate gate writes
`phases/{feature-name}/completion-certificate.json` and fails closed when:

- Any step is not `completed`.
- A completed step lacks matching `task-gates/task-N.json` proof.
- Task proof is stale against the current step file hash.
- Verify command evidence is missing, timed out, or non-zero.
- An `e2e` proof used less than a 120 second Verify timeout.
- Required wiring or runtime smoke evidence is not `pass`.

### Resume Proof

Before `/choice-execute` skips checked tasks in a mid-build resume, run:

```powershell
scripts/harness-resume-proof.ps1 -ProjectRoot <project-root> -Phase <phase> -PlanPath <plan-path> -CompletedTaskCount <N> -ResumeHash <resume-hash>
```

The resume proof writes `phases/{feature-name}/resume-proof.json` and validates
only the checked task prefix. It fails closed when any skipped task lacks fresh
passing `task-gates/task-N.json` proof, when the recorded step hash is stale,
when Verify evidence is missing, non-zero, timed out, or too short for e2e, or
when required runtime evidence is absent.

Resume proof is not a final completion certificate. It must allow later pending
steps and must not require final wiring gate PASS. `- [x]` checkboxes and
`**Resume hash:**` preserve controller continuity only; they are not PASS
evidence.

### Recovery

Do not reset a step without a concrete pass/fail signal.

Report:

```markdown
Step N failed: summary

Recovery:
1. Fix the root cause.
2. /choice-execute Path 2 phase --reset-step N
3. /choice-execute Path 2 phase
```

Use zero-indexed step numbers in reset commands.

### Completion

Completion requires:

- Every step completed.
- Every completed step has fresh task gate proof.
- Wiring gate PASS.
- Runtime smoke evidence when required.
- Completion certificate PASS.
- EZPowers `phases/index.json` restored.
- Parent `/choice-execute` completion requires Final code review PASS.

After success:

- Print per-step summary.
- Print wiring and runtime evidence.
- Print the diff range `<harness-start-hash>..HEAD`.
- Continue to `/choice-execute` Path 2 finalization with plan path, diff range,
  `wiring-gate.json`, runtime artifacts, and run log path.
- Continue to `/choice-execute` Final Code Review only after Path 2
  finalization produces wiring gate PASS.

## Path 3 — Inline Execution

### Purpose

Execute plan tasks sequentially in the controller's own session when the task
count is small and context headroom allows. All verification gates match the
subagent path; re-dispatch loops become fix-in-place loops with the same retry
limits.

### Inputs

Read before running:

- `docs/reference/verification-contract.md`
- `docs/reference/dispatch-protocol.md`
- Plan artifact, `.harness/config.json`, `phases/index.json`

### Context Pre-check

On inline selection, estimate context consumption (roughly 3-5K tokens per
task for file reads, implementation, tests, and Verify, plus context already
consumed in the session). If the estimate exceeds 40% of the context window,
ask the user:

> "Inline execution is estimated to consume over 40% of the context window.
> Run `/compact` first?"
>
> 1. `/compact` then proceed
> 2. Proceed as-is
> 3. Switch to subagent-driven

### Git Hash Recording And Gate Preparation

Apply the Git Hash Recording Protocol (`/choice-execute` Section 3.6), then
prepare the same lightpath gate artifacts used by the subagent path:

```powershell
scripts/lightpath-gate.ps1 -Scope prepare -ProjectRoot <project-root> -PlanPath <plan-path> -Phase <phase>
```

### Per-Task Execution Loop

```
Record git hash (git rev-parse HEAD)
  -> Read task content
  -> Implement in TDD order (test -> confirm failure -> implement -> confirm pass)
  -> Test Baseline Protection (fix-in-place, max 3)
  -> Lint & Typecheck Gate (fix-in-place, max 2)
  -> Lightpath task gate (scripts/lightpath-gate.ps1 -Scope task -TaskNumber N)
    -> PASS -> conditional security review
    -> FAIL -> analyze failure -> fix code -> re-verify (max 3)
    -> 3 failures -> escalate to user
  -> Commit
  -> Compute changed-files
  -> Next task
```

### Gate Equivalence Rules

- Test Baseline Protection and Lint & Typecheck follow the canonical
  procedures in `docs/reference/verification-contract.md` § Per-Task Quality
  Gates. Detection logic, thresholds, and FAIL/WARN outcomes are identical to
  the subagent path; re-dispatch is replaced by fix-in-place -> re-check loops
  with the same max retry counts (test protection: max 3, lint/typecheck:
  max 2).
- AC verification runs `scripts/lightpath-gate.ps1 -Scope task`. Re-read the
  plan file through the converted step artifact; do not use commands from
  earlier session context. If the gate fails, fix the code or the plan gap;
  do not weaken or replace the Verify command.
- Conditional security review uses the same trigger conditions as
  `/choice-execute` Section 6 (27 keywords). On trigger, dispatch the
  `ezpowers:security-reviewer` plugin agent via `subagent_type`.
- Failure handling is fix-in-place -> re-verify: analyze the failure output,
  fix by root cause, re-run Verify. Max 3 attempts, then escalate to user.
- After all tasks complete, proceed to `/choice-execute` Section 11a (Quality
  Budget) and Section 12 (Final Code Review), same as the subagent path.
