# Harness Execution Contract

This reference contains the strict-path details that do not belong in the
`/executeharness` controller prompt.

## Source Contracts

- `docs/reference/mattpocock-harness-adapter.md`
- `docs/reference/verification-contract.md`
- `docs/reference/dispatch-protocol.md`
- `docs/reference/model-routing-contract.md`
- `docs/reference/domain-language.md`

## Preflight

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

## Mode Routing

Avoid conversion work when a usable phase already exists.

- `--status`: call `scripts/harness-phase.ps1 -ProjectRoot <project-root> -Phase <phase> -Status` and stop.
- `--reset-step N`: identify the failing signal, then call `scripts/harness-phase.ps1 -ProjectRoot <project-root> -Phase <phase> -ResetStep N` and stop.
- Existing phase with pending steps: skip conversion and execute.
- New phase: convert the plan.

## Plan To Phase Conversion

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

## Step Mapping

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

## Harness Phase Index

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

## Wiring Gate File

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

## EZPowers Phase Protection

The harness phase index and EZPowers phase index have different schemas.

Before harness execution:

1. Copy `phases/index.json` to `phases/index.ezpowers.json`.
2. Let the harness use `phases/index.json`.

After completion or abort:

1. Restore `phases/index.json` from `phases/index.ezpowers.json`.
2. Update EZPowers build status.
3. Delete `phases/index.ezpowers.json`.

If a backup exists before the run, ask whether to restore it or discard it.

## Step Execution

Prefer:

```powershell
scripts/harness-run.ps1 -ProjectRoot <project-root> -Phase <phase> -TimeoutSeconds 600
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

## Wiring Gate Execution

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
- Parent `/choiceexecutor` dispatches `ezpowers:wiring-reviewer` through the
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

## Completion Certificate

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

## Recovery

Do not reset a step without a concrete pass/fail signal.

Report:

```markdown
Step N failed: summary

Recovery:
1. Fix the root cause.
2. /executeharness phase --reset-step N
3. /executeharness phase
```

Use zero-indexed step numbers in reset commands.

## Completion

Completion requires:

- Every step completed.
- Every completed step has fresh task gate proof.
- Wiring gate PASS.
- Runtime smoke evidence when required.
- Completion certificate PASS.
- EZPowers `phases/index.json` restored.
- Parent `/choiceexecutor` completion requires Final code review PASS.

After success:

- Print per-step summary.
- Print wiring and runtime evidence.
- Print the diff range `<harness-start-hash>..HEAD`.
- Continue to `/choiceexecutor` Path 2 finalization with plan path, diff range,
  `wiring-gate.json`, runtime artifacts, and run log path.
- Continue to `/choiceexecutor` Final Code Review only after Path 2
  finalization produces wiring gate PASS.
