---
name: harness-chain
description: Use only when the user explicitly asks to configure or run the project-local EZPowers harness chain for unattended, evidence-gated software or planning-deliverable work. Not for ordinary execute runs, generic planning, or silently adding orchestration to a project.
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
Read the configured `project_profile` before staging a feature; it determines
the plan/bundle schema and mandatory independent-review gate.
Never install a plugin, change global host configuration, select reviewer
models, invent an external executor, or add a second task/phase state machine.

## Rules that hold for the whole run

- The runtime verdict is the only completion authority. Stop only at a
  terminal verdict.
- Frozen files stay frozen. Never weaken, skip, or replace a check, and never
  write or relay a review receipt yourself.
- One continuation authority per feature. On Claude Code that is the project
  Stop hook; never set the native `/goal` for a chain feature.
- Spawn one reviewer per challenge and let the host deliver its result. Do not
  poll it, start a second one, or answer for it.
- A limit that is reached is terminal. Do not attempt another pass.

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

Claude Code is unattended-capable in `auto`, `dontAsk`, or `bypassPermissions`.
A `claude -p` run needs `--permission-mode` set explicitly, and chain hooks do
not run in a `--bare` session. In `auto` the host can still deny an action or
return to prompting after repeated classifier blocks; disclose that before
feature approval.

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
compact, or fork: after apply, ask the human to restart the host session or run
`/clear`, then confirm `chain config status` reports `READY`. Claude Code
reports its permission mode on tool and Stop events rather than on
SessionStart, so status can say the session has not reported a mode until the
first tool call after the restart.

After `setup --refresh`, run `chain config status`. If it reports chain hooks as
missing or changed, a newer runtime writes different hook matchers: preview and
apply the same configuration again with the user's approval, then have the
user restart the session.

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
- use `design-architecture` when the feature creates or changes a durable
  boundary, or when its technical boundaries are unsettled.

Create settled spec and plan data using their installed contracts. Create at
least one acceptance-oracle file. Each criterion must map exactly once to an
oracle that names:

- an observable runtime boundary for software, or project-check/artifact-
  inspection boundary for planning deliverables;
- a positive and negative case;
- the exact plan checks that exercise it;
- whether the current implementation is expected to `fail` or `pass`.

Do not use source presence, test names, model assertions, self-mocks, or
prose-only checks as acceptance proof.

New staged software plans use schema v2; planning-profile plans use schema v3
with byte inputs, logical deliverables, and direct/inspected review sources.
Both use explicit `depends_on`. Concurrency remains
per-check opt-in: the baseline and later verification may overlap a check only
when its independence and resource locks are already justified. The preview
shows the derived assurance-graph hash, and the approval freezes it; this graph
does not assign host implementation work.

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

The example above is the software bundle schema v1. A planning run uses bundle
schema v2 and adds `"project_profile": "planning"`. Its binary or text
`plan.inputs` remain in the project and are hashed directly; do not copy them
into the staged UTF-8 `files` array. Planning outputs are explicit
`plan.deliverables` paths and remain mutable until verification. The preview
must show the frozen input inventory and logical deliverable contract.

Feature `limit_overrides` may lower, never raise, project limits.
The architecture role contains one or more safe Markdown artifacts exactly
when `design_architecture` is selected. Those files are applied with the
feature bundle and frozen by full-file hash, for example:

```json
{"role": "architecture", "source": "ARCHITECTURE.md", "target": "ARCHITECTURE.md"}
```

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
Begin the gate immediately before the spawn so no other subagent binds first.
Start the reviewer in the foreground when the host lets you choose. If it runs
in the background, end your turn and wait: on Claude Code the Stop hook neither
blocks nor counts while a background subagent is running, and the host resumes
the session when it reports. Do not begin another gate, rerun verification, or
start a second reviewer while one is bound. A report that arrives while a
verification is running is kept and judged when that verification ends, so do
not abandon its reviewer; a new all-scope verification still makes the review
moot, because its receipt is for the earlier evidence. If a receipt is rejected, the same
`chain gate begin` command reports it as `previous_receipt` with the reason
and a `next_step`, and inside a run the Stop reason says the same. When it
then shows no `bound_agent_id`, the first reviewer could not be continued:
spawn one new reviewer for that challenge.
An oracle audit allows that once. If the replacement's report is rejected too,
the preview is closed like a failed audit; tell the person and revise the
staged contract. Inside a run each rejection counts toward the review limit.
If a bound reviewer cannot report at all, because it was interrupted or its
session ended, run:

```text
python .ezpowers/ezpowers.py chain gate abandon --json
```

Wait for a reviewer that is still running; abandoning is not a way around a
review. It closes an audit's preview, and inside a run it counts one review
failure and frees the challenge for one new reviewer.
After the bound reviewer's receipt registers, rerun the same preview. Any staged or target
change produces a different hash and requires a new audit.
A bound audit `FAIL` consumes that exact preview hash: revise the staged
acceptance contract before starting another audit. Do not cycle reviewers
against unchanged oracle evidence until one returns `PASS`. A new preview hash
replaces a pending audit and closes the earlier preview when a reviewer was
already bound to it. Do not begin an oracle audit while a run is
`PENDING_LOOP` or `RUNNING`.

### 3. Obtain one feature approval

When preview is `READY`, show the user:

- the settled request and selected/skipped stages;
- spec, plan, oracle, applicable architecture, and frontend/DESIGN.md targets and
  create/replace actions;
- baseline result, risks, QA requirement, and hard limits;
- preview hash and any forced replacement/backup requirement;
- assurance-graph hash and topological task waves;
- every check `reuse` declaration that the approval freezes;
- selected project profile and, for planning, frozen inputs, deliverable
  groups, and direct/inspected review sources;
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
Claude Code overrides a Stop hook after eight continuations in a row with no
tool call between them. That is a host safety cutoff, not a runtime verdict.

### 5. Implement until the runtime verdict

Edit the declared product with host-native tools. The approved spec, plan, oracle,
applicable architecture and frontend/DESIGN.md files, project checks, chain
config, assurance graph, approval, and planning inputs are frozen. Planning
deliverable outputs are the mutable product. If frozen material changes, stop normal work at
`NEEDS_REAPPROVAL`; do not
repair hashes or silently thaw it.

Run real verification:

```text
python .ezpowers/ezpowers.py verify --plan <plan> --all --json
```

A check that declares `reuse` is carried only from a PASS executed in this same
run, so the first verification after approval executes everything and later
rework verifications execute what the rework can affect plus every undeclared
check. A reuse-declared oracle check must select its own oracle files or the
preview rejects the bundle. Never add or narrow a declaration to shorten the
loop; it is frozen with the approval.

On FAIL, apply the `diagnose` evidence ladder to the recorded logs, add a
regression test before the fix when applicable, and fix the product. Put a new
regression test in a new non-frozen file: editing an approved oracle, spec, or
plan file (even to add a test) changes a frozen hash and ends the run at
`NEEDS_REAPPROVAL`. This does
not create another retry authority or expand the approved acceptance contract.
Reproduction and root cause are intermediate chain work; continue through the
source-cause patch and rerun the original failing scenario before all-scope
verification.
Never weaken, skip, rename, or replace the oracle/check to obtain PASS. A
failure that reaches any approved limit becomes terminal immediately; do not
perform an extra attempt. The runtime records the failed workspace and rejects
another all-scope verification until a real workspace content change is
observed. Task-scoped checks may still be used for diagnosis, but cannot clear
the rework requirement, and a failing task-scoped run still spends the same
validation and identical-failure budget as an all-scope failure; read the
recorded logs before replaying a failing check.

After a fresh PASS, run the profile's independent review bound to that
evidence. Software uses:

```text
python .ezpowers/ezpowers.py chain gate begin --kind code-review --subject-sha256 <evidence-sha256> --json
```

Planning uses:

```text
python .ezpowers/ezpowers.py chain gate begin --kind artifact-review --subject-sha256 <evidence-sha256> --json
```

The injected planning rubric lists every deliverable and its allowed direct
artifact or inspection-log source IDs. The bound reviewer must return one
schema-v2 result per deliverable. A failed artifact review requires an actual
byte change in every failed logical group plus a new all-scope PASS; changing
only an unrelated source or one of several failed groups is insufficient.

If the approved risks require QA, likewise run:

```text
python .ezpowers/ezpowers.py chain gate begin --kind adversarial-qa --subject-sha256 <evidence-sha256> --json
```

Spawn a host-native independent subagent for each challenge. A FAIL means fix
the product and run all-scope verification again. The runtime clears prior product-gate
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

After an explicit kit refresh, a nonterminal approval that predates a binding
the refreshed runtime requires is intentionally terminal at `NEEDS_REAPPROVAL`.
Start a new preview, oracle audit, and approval; never synthesize the missing
binding.

## Emergency stop

A stuck loop must be escapable without the loop's cooperation. Out-of-band
options, in order of preference:

- delete or rename `.ezpowers/chain.json` or the active approval file: the
  next Stop contract check marks the run `NEEDS_REAPPROVAL`, a terminal
  state, and the hook permits stopping;
- remove the EZPowers chain hook entries from `.claude/settings.json` or
  `.codex/hooks.json`; on Codex also clear the native goal with the host's own
  control.

If runtime state is unreadable, the chain hook itself degrades to a fail-safe
no-op (exit 0, empty response) instead of blocking, so a corrupt loop dies
rather than wedging the session. After any emergency stop, repair state with a
new preview/audit/approval; never hand-edit hashes to resurrect the old run.
A review gate the stopped run left pending is dropped by the next
`chain gate begin`.

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
