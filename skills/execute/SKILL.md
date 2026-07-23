---
name: execute
description: Use when a validated EZPowers plan should be implemented with host-native editing and orchestration, then verified and certified by the project-local runtime.
disable-model-invocation: true
---

# Execute

Implement a validated plan using the active host's native capabilities. There
are no numbered execution paths and no external harness executor.
EZPowers owns the completion verdict; Claude Code or Codex owns code editing,
subagents, worktrees, sandboxing, retries, and code review.

## Preflight

Read repository instructions, the selected spec and plan, architecture and
frontend-design artifacts, current Git state, `.ezpowers/config.json`, and
`.ezpowers/contracts/verification-contract.md`.
When `.ezpowers/docs.json` exists, read the registered documentation graph and
run `docs status --json`; use wiki candidates only after confirming them
against repository evidence.

Run:

```text
python .ezpowers/ezpowers.py validate --plan <plan-path> --activate
python .ezpowers/ezpowers.py status --json
```

Stop if the kit is missing, the plan is invalid, or a managed-file conflict is
reported. `--activate` explicitly makes this plan the resume target and clears
old pointers only when switching plans; plain validation elsewhere remains
read-only. Preserve unrelated and user-owned changes.

## Implement

Work through the plan's dependency order. Use the host's native execution and
review features when they improve safety, but do not pretend a capability from
one host exists in the other. Do not translate the plan into a second phase or
step state machine. Do not select models or impose a generic retry policy.

After each coherent slice, run the task's real checks. Treat the check result as
feedback, not completion evidence; only a full `verify --all` run can become
the certification candidate.

## Verify and certify

When implementation and review are complete, run:

```text
python .ezpowers/ezpowers.py verify --plan <plan-path> --all --json
python .ezpowers/ezpowers.py certify --plan <plan-path> --json
python .ezpowers/ezpowers.py status --json
```

Never edit evidence, synthesize a PASS result, omit a required check, or weaken
a command to make certification pass. A failure, timeout, stale workspace,
changed plan/config, documentation drift, missing log, or hash mismatch is
blocking. Fix the product or revise the approved spec/plan, then rerun the
complete verification set.

## Resume and report

On a later session, start from `status --json`, Git state, the plan, and stored
evidence rather than conversation memory. Task entries marked `FRESH_PASS` may
guide where implementation resumes, but they never substitute for all-scope
completion. Reuse any PASS only when the runtime says it is fresh.

Report changed paths, host-native execution/review choices actually used,
every command and exit result, evidence path and hashes, certification status,
and remaining limitations. Do not claim completion unless certification is a
fresh PASS.
