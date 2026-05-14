# Harness Execution Contract

This reference contains the strict-path details that do not belong in the
`/executeharness` controller prompt.

## Source Contracts

- `docs/reference/mattpocock-harness-adapter.md`
- `docs/reference/verification-contract.md`
- `docs/reference/dispatch-protocol.md`
- `docs/reference/domain-language.md`

## Preflight

Run:

```powershell
scripts/harness-doctor.ps1 -ProjectRoot <project-root> -Phase <phase>
```

Stop on FAIL. Report WARN before continuing.

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

## Step Mapping

Harness steps are zero-indexed:

- Task 1 -> `step0.md`
- Task 2 -> `step1.md`
- `--reset-step 2` resets Task 3.

Step files include:

- Files to Read.
- Full task text.
- Task category (`skeleton`/`feature`/`wiring`/`integration-test`).
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
  "attempts": []
}
```

Allowed statuses:

- `pending`
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
- Any non-zero command exit becomes `fail`.
- Missing required runtime artifacts become `test_gap`.
- Attempts record command, exit code, stdout/stderr tail, and timestamp.
- `ezpowers:wiring-reviewer` gives the independent verdict through the dispatch
  protocol.

Reviewer verdict handling:

- `PASS`: set status `pass`.
- `TEST_GAP`: set status `test_gap`.
- `CODE_GAP`: set status `code_gap`.
- `SPEC_GAP`: set status `spec_gap`.
- Missing or malformed verdict: treat as `test_gap`.

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
- Wiring gate PASS.
- Runtime smoke evidence when required.
- EZPowers `phases/index.json` restored.
- Final code review PASS.

After success:

- Print per-step summary.
- Print wiring and runtime evidence.
- Review `git diff <harness-start-hash>..HEAD`.
- Continue to `/choiceexecutor` Final Code Review with plan path and diff range.
