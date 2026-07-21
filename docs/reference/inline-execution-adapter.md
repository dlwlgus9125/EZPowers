---
doc_type: reference
authority: supporting
---

# Inline Execution Adapter - Path 3 Procedure

## Purpose

Internal adapter used by `/choice_execute` Path 3. Execute plan tasks
sequentially in the controller's own session when the task count is small and
context headroom allows. All verification gates match the subagent path;
re-dispatch loops become fix-in-place loops with the same retry limits.

## Read

- `docs/reference/verification-contract.md`
- `docs/reference/dispatch-protocol.md`
- Plan artifact, `.harness/config.json`, `phases/index.json`

## Context Pre-check

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

## Git Hash Recording And Gate Preparation

Apply the Git Hash Recording Protocol (`/choice_execute` Section 3.6), then
prepare the same lightpath gate artifacts used by the subagent path:

```powershell
scripts/lightpath-gate.ps1 -Scope prepare -ProjectRoot <project-root> -PlanPath <plan-path> -Phase <phase>
```

## Per-Task Execution Loop

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

## Gate Equivalence Rules

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
  `/choice_execute` Section 6 (27 keywords). On trigger, dispatch the
  `ezpowers:security-reviewer` plugin agent via `subagent_type`.
- Failure handling is fix-in-place -> re-verify: analyze the failure output,
  fix by root cause, re-run Verify. Max 3 attempts, then escalate to user.
- After all tasks complete, proceed to `/choice_execute` Section 11a (Quality
  Budget) and Section 12 (Final Code Review), same as the subagent path.
