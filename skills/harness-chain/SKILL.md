---
name: harness-chain
description: Use only when the user explicitly asks to configure or run the project-local EZPowers harness chain for unattended, evidence-gated feature work. Not for ordinary execute runs, generic planning, or silently adding orchestration to a project.
disable-model-invocation: true
---

# Harness Chain

Configure one repository-specific chain through questions, or run one feature
through its already-configured chain. Claude Code or Codex remains the
implementer and orchestrator. The project-local runtime freezes the approved
acceptance contract, executes exact checks, records independent-review
receipts, enforces retry limits, and issues the completion verdict.

Read `AGENTS.md`, current Git state, `.ezpowers/config.json`, and
`.ezpowers/contracts/harness-chain-contract.md` first. Read
`.ezpowers/contracts/engineering-practices-contract.md` before diagnosing a
product failure or changing a product-code boundary. Preserve user changes.
Never install a plugin, change global host configuration, select reviewer
models, invent an external executor, or add a second task/phase state machine.

## Choose one mode

- If no `.ezpowers/chain.json` exists, or the user asks to configure/change the
  chain, use **Configure**.
- If the project chain is ready and the user gives a feature request, use
  **Feature run**.
- If neither intent is clear, ask which mode they want. Do not configure or
  start a run implicitly.

## Configure

Ask a short project-level interview that settles:

1. enabled hosts: Claude Code, Codex, or both;
2. whether `deep-interview`, `frontend-design`, and `design-architecture` are
   `auto` or `always`;
3. additional phrases or project conditions that require adversarial QA;
4. hard limits for total continuations, QA cycles, validation failures, review
   failures, and identical repeated failures;
5. whether the selected hosts are already in a non-interactive permission mode
   suitable for the intended unattended run.

Recommend the defaults unless repository evidence supports stricter values:

```json
{
  "total_iterations": 10,
  "qa_cycles": 5,
  "validation_retries": 3,
  "review_retries": 3,
  "identical_error_repeats": 3
}
```

Write only a staging bundle under `.ezpowers/staging/<id>/bundle.json`:

```json
{
  "schema_version": 1,
  "optional_stages": {
    "deep_interview": "auto",
    "frontend_design": "auto",
    "design_architecture": "auto"
  },
  "additional_qa_triggers": [],
  "limits": {
    "total_iterations": 10,
    "qa_cycles": 5,
    "validation_retries": 3,
    "review_retries": 3,
    "identical_error_repeats": 3
  },
  "hosts": ["claude", "codex"]
}
```

Run:

```text
python .ezpowers/ezpowers.py chain config preview --bundle <bundle> --json
```

Show the user the exact preview hash, hosts, minimum-version prerequisite
results, limits, hook targets, and any conflict. Claude requires 2.1.217 or
newer and Codex requires 0.145.0 or newer. Ask once whether to apply a `READY`
hash. Only after approval run:

```text
python .ezpowers/ezpowers.py chain config apply --bundle <bundle> --preview-sha256 <sha256> --json
python .ezpowers/ezpowers.py chain config status --json
```

Configuration writes project-local files and host hooks, so this one apply
approval is mandatory. It is not approval for global configuration. A new or
changed hook must complete a real `SessionStart` handshake; do not claim
unattended readiness while status is `PENDING_HOST_TRUST`. Apply resets every
prior handshake, and the hook fires only on session startup, resume, clear,
or compact: after apply, ask the human to restart the host session or run
`/clear`, then confirm `chain config status` reports `READY`.

## Feature run

### 1. Settle and stage the acceptance contract

Classify each optional stage with a concrete reason. An `always` project stage
must be selected and actually run before staging; the runtime validates only
the recorded selection and reason, so the approval summary is where a false
stage claim gets caught. For an `auto` stage, run it only when its own trigger
applies:

- use `deep-interview` for stated ambiguity or a plausible consequential blind
  spot;
- use `frontend-design` when UI/UX decisions are unsettled;
- use `design-architecture` when technical boundaries are unsettled.

Create settled spec and plan data using their installed contracts. Create at
least one acceptance-oracle file. Each criterion must map exactly once to an
oracle that names:

- an observable runtime boundary;
- a positive and negative case;
- the exact plan checks that exercise it;
- whether the current implementation is expected to `fail` or `pass`.

Do not use source presence, test names, model assertions, self-mocks, or
prose-only checks as acceptance proof.

Place the spec, plan, oracle files, and `bundle.json` under one
`.ezpowers/staging/<run-id>/` directory. The bundle shape is:

```json
{
  "schema_version": 1,
  "run_id": "feature-id",
  "request": "settled user request",
  "host": "codex",
  "stage_selection": {
    "deep_interview": {"selected": false, "reason": "request is settled"},
    "frontend_design": {"selected": false, "reason": "no UI change"},
    "design_architecture": {"selected": false, "reason": "no boundary change"}
  },
  "risk_classes": ["regression_risk"],
  "files": [
    {"role": "spec", "source": "spec.md", "target": "docs/specs/feature-id.md"},
    {"role": "plan", "source": "plan.md", "target": "docs/plans/feature-id.md"},
    {"role": "frontend-design", "source": "frontend-design.md", "target": "docs/ux/frontend-design.md"},
    {"role": "design-system", "source": "DESIGN.md", "target": "DESIGN.md"},
    {"role": "oracle", "source": "test_feature.py", "target": "tests/test_feature.py"}
  ],
  "oracles": [
    {
      "id": "feature-oracle",
      "criteria": ["AC-1"],
      "checks": ["feature-check"],
      "boundary": "public API",
      "artifact_paths": ["tests/test_feature.py"],
      "baseline": "fail",
      "positive_case": "describe the accepted behavior",
      "negative_case": "describe what must be rejected"
    }
  ]
}
```

Feature `limit_overrides` may lower, never raise, project limits.
The two design roles are present only when
`spec.design_context.required` is true. In that case there is exactly one
frontend-design file and at least one design-system file, and their targets
must exactly equal the spec paths and managed mapping. A non-UI spec includes
neither role.

### 2. Prove the oracle before approval

Run the preview. It executes the staged oracle against an isolated copy of the
current repository and requires the declared baseline:

```text
python .ezpowers/ezpowers.py chain run preview --bundle <bundle> --json
```

For `REVIEW_REQUIRED`, begin the exact challenge:

```text
python .ezpowers/ezpowers.py chain gate begin --kind oracle-audit --subject-sha256 <preview-sha256> --json
```

Spawn one host-native, read-only independent reviewer. The SubagentStart hook
binds that agent to the challenge and injects the rubric. Binding is silent:
an agent from another session, or a second subagent after one is bound, is
ignored without an error and its receipt never registers. To confirm the
binding, rerun the same `chain gate begin` command and check the reported
`bound_agent_id`. Do not write the review receipt yourself, relay a
main-agent verdict, or accept unbound output.
After its SubagentStop receipt, rerun the same preview. Any staged or target
change produces a different hash and requires a new audit.
A bound audit `FAIL` consumes that exact preview hash: revise the staged
acceptance contract before starting another audit. Do not cycle reviewers
against unchanged oracle evidence until one returns `PASS`.

### 3. Obtain one feature approval

When preview is `READY`, show the user:

- the settled request and selected/skipped stages;
- spec, plan, oracle, and applicable frontend/DESIGN.md targets and
  create/replace actions;
- baseline result, risks, QA requirement, and hard limits;
- preview hash and any forced replacement/backup requirement;
- that approval starts an unattended loop until `CERTIFIED`,
  `NEEDS_REAPPROVAL`, `BLOCKED`, or `FAILED`.

Ask once whether to apply this exact preview. After approval:

```text
python .ezpowers/ezpowers.py chain run apply --bundle <bundle> --preview-sha256 <sha256> --json
```

Use `--force` only when the approved preview names replacements; the runtime
backs them up. Do not ask the user to approve normal implementation edits,
verification retries, review retries, or QA cycles again.

### 4. Activate exactly one continuation authority

Use the exact `goal_objective` and hash returned by apply.

- Codex: create one native Codex goal with that exact objective, then activate
  with `--host codex --authority native-goal`.
- Claude Code: activate with `--host claude --authority stop-hook`; the
  project Stop hook is the sole continuation authority.

```text
python .ezpowers/ezpowers.py chain activate --host <host> --authority <authority> --objective-sha256 <sha256> --json
```

Codex Stop is an observer and terminal brake; it must not create a second
loop. Claude Stop may continue a nonterminal run. Never emulate either host's
missing capability.

### 5. Implement until the runtime verdict

Edit product code with host-native tools. The approved spec, plan, oracle,
applicable frontend/DESIGN.md files, project checks, chain config, and approval
are frozen. If any changes, stop normal work at `NEEDS_REAPPROVAL`; do not
repair hashes or silently thaw it.

Run real verification:

```text
python .ezpowers/ezpowers.py verify --plan <plan> --all --json
```

On FAIL, apply the `diagnose` evidence ladder to the recorded logs, add a
regression test before the fix when applicable, and fix the product. Put a new
regression test in a new non-frozen file: editing an approved oracle, spec, or
plan file (even to add a test) changes a frozen hash and ends the run at
`NEEDS_REAPPROVAL`. This does
not create another retry authority or expand the approved acceptance contract.
Reproduction and root cause are intermediate chain work; continue through the
source-cause patch and rerun the original failing scenario before full
verification.
Never weaken, skip, rename, or replace the oracle/check to obtain PASS. A
failure that reaches any approved limit becomes terminal immediately; do not
perform an extra attempt. The runtime records the failed workspace and rejects
another all-scope verification until a real workspace content change is
observed. Task-scoped checks may still be used for diagnosis, but cannot clear
the rework requirement, and a failing task-scoped run still spends the same
validation and identical-failure budget as an all-scope failure; read the
recorded logs before replaying a failing check.

After a fresh PASS, run an independent code review bound to that evidence:

```text
python .ezpowers/ezpowers.py chain gate begin --kind code-review --subject-sha256 <evidence-sha256> --json
```

If the approved risks require QA, likewise run:

```text
python .ezpowers/ezpowers.py chain gate begin --kind adversarial-qa --subject-sha256 <evidence-sha256> --json
```

Spawn a host-native independent subagent for each challenge. A FAIL means fix
the product and rerun full verification. The runtime clears prior product-gate
receipts, rejects the unchanged workspace, and will not review the old PASS
evidence again. Use `blocker-review` only for a concrete external blocker
after safe in-scope alternatives are exhausted.

Finally run:

```text
python .ezpowers/ezpowers.py certify --plan <plan> --json
python .ezpowers/ezpowers.py chain run status --json
```

Stop only at a runtime terminal verdict. `CERTIFIED` is success. Report the
approval, evidence, review receipt, QA receipt when required, certificate
hashes, command exits, changes, and remaining limitations.

## Emergency stop

A stuck loop must be escapable without the loop's cooperation. Out-of-band
options, in order of preference:

- delete or rename `.ezpowers/chain.json` or the active approval file: the
  next Stop contract check marks the run `NEEDS_REAPPROVAL`, a terminal
  state, and the hook permits stopping;
- remove the EZPowers chain hook entries from `.claude/settings.json`.

If runtime state is unreadable, the chain hook itself degrades to a fail-safe
no-op (exit 0, empty response) instead of blocking, so a corrupt loop dies
rather than wedging the session. After any emergency stop, repair state with a
new preview/audit/approval; never hand-edit hashes to resurrect the old run.

## Approval and absence rules

The chain deliberately has two human boundaries: configuration apply and one
feature apply. It must not manufacture extra approvals inside the approved
run. Host sandbox, trust, secret, billing, login, or external-system prompts
remain host-owned and cannot be bypassed by EZPowers. If those can interrupt
the requested unattended period, disclose that before feature approval.

When the user is absent, continue through recoverable product failures within
the approved limits. Stop without asking only on a terminal verdict. A changed
contract requires a new preview/audit/approval; a genuine external blocker
requires a bound blocker review.
