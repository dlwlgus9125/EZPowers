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
frontend-design artifacts, every `DESIGN.md` named by the spec's
`design_context`, current Git state, `.ezpowers/config.json`, and
`.ezpowers/contracts/verification-contract.md`.
When the config selects the planning profile, also read the plan's declared
inputs, logical deliverables, and direct/inspected review sources. Treat input
bytes as immutable acceptance material and output paths as the product to
create or revise.
Read `.ezpowers/contracts/engineering-practices-contract.md` before diagnosing
a nontrivial failure or implementing a planned product-code boundary change.
When `.ezpowers/docs.json` exists, read the registered documentation graph and
run `docs status --json`; use wiki candidates only after confirming them
against repository evidence.

Run:

```text
python .ezpowers/ezpowers.py validate --plan <plan-path> --activate
python .ezpowers/ezpowers.py status --json
python .ezpowers/ezpowers.py trace --plan <plan-path> --json
```

Stop if the kit is missing, the plan is invalid, or a managed-file conflict is
reported. `--activate` explicitly makes this plan the resume target and clears
old pointers only when switching plans; plain validation elsewhere remains
read-only. Preserve unrelated and user-owned changes.

## Implement

Work through the plan's dependency order. The runtime graph orders only check
readiness and never assigns implementation tasks. Use the host's native execution and
review features when they improve safety, but do not pretend a capability from
one host exists in the other. Do not translate the plan into a second phase or
step state machine. Do not select models or impose a generic retry policy.
Before changing UI, resolve the nearest mapped `DESIGN.md`. Treat it as
authoritative for tokens and reusable-component styling, and implement any
recorded code alignment rather than weakening the design contract.
Treat the spec's architecture impact and referenced artifacts as settled
constraints. If implementation requires a new or different structural
boundary, stop that path and return through `design-architecture`, `spec`, and
plan validation; do not hide the divergence with a final documentation edit.

After each coherent slice, run the task's real checks. Treat the check result as
feedback, not completion evidence; only an all-scope `verify --all` result can
become the certification candidate. Plan-v2 verification may overlap only checks
whose own contract is explicitly safe and lock-compatible; do not add a safety
declaration merely to accelerate the current run.
When a check declares `reuse`, the runtime carries its recorded PASS while the
declared content, the check contract, and the installed kit are unchanged, so
running `verify --all` again after small rework executes only what the change
can affect plus every undeclared check. Never add, narrow, or remove a `reuse`
declaration during execute, and never hand-pick a subset of checks as
completion evidence. Add `--no-reuse` when a full fresh run is wanted, for
example before a release.
Planning validators are likewise read-only during verification: produce the
deliverable before `verify`, and never let a check rewrite, normalize, or
repair declared input/output bytes. Git-ignored deliverables are still bound
by their own SHA-256 inventory.

Before the certification candidate, run the change: exercise the changed
behavior on the real running system with the host's own means. On Claude Code
use a project `verify` or `run-<name>` recipe skill when one exists, otherwise
the bundled `/verify` or `/run` skill; on Codex perform an equivalent real run
as the project instructions describe. Treat what you observe as feedback. It is
never completion evidence and never replaces `verify --all` or `certify`. Do
it before `verify --all`, because a recipe file the host records is a workspace
change. Documentation-only and test-only changes are exempt.

## Verify and certify

Review means the host's own review feature when it has one: Claude Code's
bundled `/code-review` skill, or Codex's built-in `codex review`. Use one
reviewer tuned through project instructions rather than stacked reviewers, and
let a later round build on earlier findings. EZPowers supplies no reviewer.

When implementation and review are complete, run:

```text
python .ezpowers/ezpowers.py verify --plan <plan-path> --all --json
python .ezpowers/ezpowers.py certify --plan <plan-path> --json
python .ezpowers/ezpowers.py status --json
python .ezpowers/ezpowers.py trace --plan <plan-path> --json
```

Never edit evidence, synthesize a PASS result, omit a required check, or weaken
a command to make certification pass. A failure, timeout, stale workspace,
changed plan/config, documentation drift, missing log, or hash mismatch is
blocking. Apply the `diagnose` evidence ladder before fixing a nontrivial
failure. Because this explicit skill already has implementation authority, a
regression test may be added before the fix when the approved plan permits it;
the diagnosis itself never expands scope. Root cause is not a handoff point:
continue through the source-cause patch, the original failure reproduction,
affected checks, and cleanup. Fix the product or revise the approved spec/plan,
then run `verify --all` again.

An intermittent failure is a defect, not noise. Never rerun a check until it
passes, add a sleep or retry, skip it, or loosen its assertion; apply the
`diagnose` ladder, whose red signal for a flaky failure is a recorded failure
rate.

## Resume and report

On a later session, start from `status --json`, Git state, the plan, and stored
evidence rather than conversation memory. Task entries marked `FRESH_PASS` may
guide where implementation resumes, but they never substitute for all-scope
completion. Reuse any PASS only when the runtime says it is fresh.

Report changed paths, host-native execution/review choices actually used,
every command and exit result, which declared checks executed and which were
carried, evidence path and hashes, certification status,
and remaining limitations. Do not claim completion unless certification is a
fresh PASS.
