# Verification Contract

This is the canonical completion contract for the v5 project-local runtime.
Host instructions, reports, tests, and hooks may explain it but must not weaken
or independently reinterpret it.

## Authority Boundary

Claude Code or Codex implements and reviews the plan with native capabilities.
EZPowers decides only whether the declared project checks produced fresh,
untampered evidence for the current workspace.

When an explicitly approved `harness-chain` run matches the plan, EZPowers
also decides whether frozen acceptance inputs are unchanged, approved attempt
limits remain, and required host-native independent review receipts bind the
exact evidence. It still does not implement or review code.

The runtime is `.ezpowers/ezpowers.py`. No external execution service or second
orchestration state machine participates in the completion path.
Python 3.10 or newer is required; the runtime otherwise uses only the standard
library.

The project root must be the Git worktree root. `setup` checks this before
installation; verification does not fall back to an unversioned filesystem
snapshot because that would change freshness semantics across projects.

## Validation

```text
python .ezpowers/ezpowers.py validate --spec <spec-path> --json
python .ezpowers/ezpowers.py validate --plan <plan-path> --json
python .ezpowers/ezpowers.py validate --plan <plan-path> --activate --json
python .ezpowers/ezpowers.py trace --plan <plan-path> --json
```

Spec validation checks the one managed JSON block and its observable criteria.
Plan validation additionally checks the referenced spec, exact criterion
coverage, check references, command shape, contained paths, placeholder bans,
and integration evidence kind. Plan v2 also requires every `depends_on`
array, rejects duplicate, unknown, self, and cyclic dependencies, and returns
stable topological task waves plus the derived assurance-graph hash. Plan v1
remains valid and serial; graph-only fields in v1 fail instead of being
ignored.

Spec validation and ordinary plan validation are read-only. `--activate` is
valid only with `--plan` and explicitly selects a valid plan as the resume
target. Switching plans invalidates all evidence and certificate pointers but
does not delete their immutable files; activating the already-active plan does
not rewrite state. `verify` also activates the plan it actually runs.

Project-profile validation is fail-closed. Config v1/v2 implies `software` and
accepts only plan v1/v2. Config v3 requires an explicit `software` or
`planning` profile; planning accepts only plan v3, while explicit software
continues to accept only v1/v2. Planning validation additionally checks safe
byte inputs, logical deliverables, exact input/criterion mappings, disjoint
paths, and direct or inspected review sources.

Validation is fail-closed. Missing files, duplicate markers or IDs, malformed
JSON, unknown references, path traversal, invalid timeouts, check collisions,
unmapped criteria, no-op commands, shell control syntax, PowerShell encoded or
opaque command forms, and `cmd /K` are errors. Managed `spec` and `cwd` values
are project-relative; absolute paths are invalid even though an absolute plan
path may be supplied as a CLI argument. A valid document is not proof that the
implementation passes.

## Exact Command Execution

The runtime reads checks from the current plan and `.ezpowers/config.json` on
every run. It passes `argv` directly to `subprocess` with `shell` disabled and
runs it in the declared project-relative `cwd`.

A ready managed documentation graph contributes the exact required
`ezpowers.docs` static check. When that graph contains DESIGN.md entries, it
also contributes `ezpowers.design`, which validates the broad frontend mapping,
nearest implementation ownership, retained local profiles, and any already
installed pinned official CLI cross-check. Both run as real required checks
and participate in evidence and freshness; neither is a prose verdict.

For every check it records:

- exact argv, cwd, kind, and timeout;
- exit code, timeout flag, spawn error, duration, and PASS/FAIL;
- separate stdout and stderr log paths;
- SHA-256 for each log.

Exit zero, no timeout, and no spawn error are all required for a check PASS.
The runtime kills the process tree on timeout. It never infers PASS from log
text or an implementer report.

### Versioned safe concurrency

Config schema v2 or v3 requires `verification.max_parallel_checks` from 1
through 32. Check concurrency is opt-in on each plan/config schema-v2/v3
check. A safe check holds its declared `resource_locks` plus an implicit lock
derived from the check ID. Checks in the same ready task wave may overlap only
when every check is safe, their locks are disjoint, and the worker cap is not
exceeded. An
unmarked or `safe: false` check is a global barrier. Plan or config v1 forces a
worker cap of one regardless of other input.

Task dependencies order ready waves, not outcomes. A failed task never skips a
dependent task's declared checks: all selected checks run so the evidence is
complete. All-scope required project checks start only after every task wave
finishes. Task scope runs exactly the selected task and neither auto-runs nor
blocks on its declared dependencies. Results and log arrays retain plan and
check declaration order even when process execution overlaps. Timeout,
interrupt, and scheduler-error cleanup terminates active process trees before
the runtime exits.

## Verification Scopes

Task-scope feedback:

```text
python .ezpowers/ezpowers.py verify --plan <plan-path> --task <task-id> --json
```

This runs that task's checks and may be used during implementation. It cannot
be certified and is not completion evidence.

All-scope completion candidate:

```text
python .ezpowers/ezpowers.py verify --plan <plan-path> --all --json
```

This runs every task check plus every check named by
`.ezpowers/config.json` `required_checks`. Any failure, timeout, spawn error,
unknown check, invalid plan, or required-check failure makes the result FAIL.
Certification considers only the latest all-scope result.

Checks must not mutate the tracked or untracked workspace used for the
fingerprint. Generated build or test output should be reproducibly cleaned,
ignored by Git, or placed in already ignored paths. A workspace, plan, or
config change during verification fails the run.

For the planning profile, every declared input and deliverable output must be
an existing regular non-symlink file before any check starts. The runtime
captures their bytes before and after the run and rejects a missing file,
changed path inventory, or any input/output byte mutation even when Git ignores
the path. Planning checks are therefore read-only validators; they do not
generate or normalize the deliverable during `verify`. The same exact-command
rules apply to Markdown, XLSX, and every other format without a built-in parser.

## Evidence Record

Each run creates an immutable candidate directory under:

```text
.ezpowers/evidence/<run-id>/
```

`result.json` includes schema version, run ID, scope, canonical plan and spec
paths and SHA-256 values, config SHA-256, installed-kit identity, start and
finish times, task and required-check results, failure reasons, and before/after
workspace and installation snapshots. The installed identity binds the local
manifest, ledger, runtime, and every managed target. Its adjacent
`result.json.sha256` binds the record bytes.

Plan-v2 results use evidence schema v2. They additionally record the complete
assurance-graph-v1 snapshot and SHA-256, unique node ID and start/finish time
for every check occurrence, the bounded execution waves, and the effective
worker cap. Repeated references to one named check remain distinct
occurrences with distinct logs while the implicit same-check lock prevents
overlap. Plan-v1 evidence remains schema v1 and retains the existing serial
shape.

Planning plan-v3 results use evidence schema v3 and assurance-graph schema v2.
The graph adds typed input and logical-deliverable nodes plus their criterion,
producer, inspection, input, and artifact-review relations. The result records
`project_profile: planning`, the complete before/after input and output path/
SHA-256 inventory, and one aggregate artifact-inventory hash. These fields are
part of the evidence bytes and do not replace real check results or logs.

For a matching chain run, the result additionally binds the chain run ID,
approval path and SHA-256, and chain configuration SHA-256. That binding is
part of the immutable result bytes; ordinary non-chain evidence has no
synthetic chain field.

The workspace fingerprint covers:

- Git HEAD;
- the binary tracked diff hash;
- a deterministic digest and count of untracked files.

Runtime-owned state and evidence paths are excluded so recording a run
does not invalidate itself. Documentation staging and backup trees plus the
local wiki are also excluded because they are non-authoritative worktree-local
state. Applied documentation, `.ezpowers/docs.json`, and config remain in the
fingerprint. Git inspection errors fail closed. The before and after workspace
and installation snapshots must match.

`.ezpowers/state.json` stores the active plan and pointers to the latest task,
all-scope, and certificate artifacts. The pointer repeats the evidence hash;
state never substitutes for the artifact it points to. A bounded
`.ezpowers/runtime.lock` serializes installation, verification, certification,
and other state-writing commands; the lock itself is excluded from the
workspace fingerprint.

## Freshness And Tamper Detection

An all-scope result is fresh only when all of these hold:

- the pointer is the canonical `.ezpowers/evidence/<run-id>/result.json`, and
  the record's own path and run ID agree with that directory;
- `result.json`, its sidecar, and the state pointer hashes agree;
- schema, scope, and status are valid and PASS, and `reasons` is empty;
- for plan v2, the graph snapshot hashes to the recorded value, equals the
  graph derived from the current plan/config, every occurrence ID is exact,
  and execution waves obey task waves, phase order, locks, barriers, and the
  worker cap;
- for planning plan v3, the current profile and graph-v2 hash agree, every
  declared input/output byte hash equals the evidence inventory, and recorded
  artifact before/after inventories are identical;
- plan and spec paths and current SHA-256 values agree;
- current config SHA-256 agrees;
- the current installed manifest, ledger, runtime, and managed files agree with
  the recorded installed-kit identity;
- current Git HEAD, tracked diff, and untracked digest agree;
- when a chain run matches the plan, its run, approval, and chain hashes agree
  and all frozen acceptance files remain unchanged;
- recorded before/after workspace and installation snapshots agree;
- the result contains exactly every task and required check declared by the
  current plan and config;
- every recorded check has exit code zero, `timed_out: false`, an empty
  `spawn_error`, and PASS;
- every stdout and stderr file exists inside the evidence tree and matches its
  recorded SHA-256, uses its canonical same-run path, and is not reused by a
  second stream.

Missing logs or sidecars, edited evidence, changed plan/config/workspace,
non-all scope, or a failed check makes the result stale. Rerun all checks; do
not repair evidence by hand.

Task pointers are checked by the same path, hash, binding, inventory, result,
and log rules, except that the expected scope is exactly `task:<task-id>`, the
inventory is exactly that one current task, and `project_checks` must be empty.
The current plan's task entries are reported as `MISSING`, `FRESH_PASS`, or
`STALE`. State keys for tasks no longer in the plan are reported separately as
`ORPHAN`; malformed pointers are never collapsed into `MISSING`. Status
computes the current workspace and installed-kit binding once and applies it
to every pointer.

## Certification And Resume

```text
python .ezpowers/ezpowers.py certify --plan <plan-path> --json
python .ezpowers/ezpowers.py status --json
```

`certify` revalidates freshness, then writes `certificate.json` next to the
evidence and stores its pointer. The certificate binds the plan, config, spec,
installed-kit identity, workspace, canonical evidence path, and evidence
SHA-256. A plan-v2 certificate uses schema v2 and also binds the assurance
graph SHA-256. A planning certificate uses schema v3 and additionally binds
the planning profile and full artifact inventory. The selected plan must already be active through explicit activation
or verification; certification never changes the resume target or clears a
different plan's pointers. Its state pointer must resolve to the canonical `certificate.json`
next to that exact evidence result and match the certificate hash. It never
executes missing checks or upgrades a stale result.

For a matching RUNNING chain, certification additionally requires the
profile's bound primary-review PASS receipt for the exact evidence hash:
`code-review` for software or per-deliverable `artifact-review` for planning.
It also requires a bound `adversarial-qa` PASS receipt when the approved risks
or triggers require it.
Those receipt pointers and the chain binding are written into the certificate.
Success changes chain state to `CERTIFIED`. Missing review cannot be replaced
by implementer prose; a terminal chain cannot be certified by another attempt.

`status` reconstructs the verdict from the active plan and stored artifacts:

- `UNCONFIGURED`: no active plan;
- `STALE`: no fresh all-scope result or a freshness check failed;
- `READY`: fresh all-scope evidence exists but certification is absent;
- `CERTIFIED`: fresh evidence and its certificate agree.

For an active valid plan, status adds the compatible
`assurance_graph_sha256` and `primary_blocker` summary. The dedicated `trace`
command returns the sorted typed graph, task waves, node states, and all
candidate blocking paths. It omits argv, logs, prompts, and request text.
Every path is labelled `causality: not-proven`: dependency structure narrows
where to investigate but does not establish the cause of a failure.

Its `task_evidence` object reports every current task, while
`orphan_task_evidence` exposes stale state keys that no longer occur in the
plan. These fields are resume diagnostics only: missing, stale, or orphan task
evidence never changes the all-scope status, certification result, hook
verdict, or status exit code.

On resume, read status, Git state, the current spec and plan, and the referenced
evidence. A task `FRESH_PASS` can identify a trustworthy completed slice;
Markdown checkboxes and conversation memory are hints only. Completion still
requires `CERTIFIED` for the current workspace.

## Host Hook Adapters

### Ordinary completion adapters

Project hooks are optional and disabled by default. They read status; they do
not execute checks. With no active plan they are neutral. With an active plan,
only a fresh certified result permits stopping.

Optional wiki SessionEnd hooks are a separate feature. They never read or
change the completion verdict and are governed by `wiki-contract.md`.

Both adapters derive the same allow/block verdict and block reason from the
core status. They emit only the fields documented by the hosts' official Stop
schemas. The standard Stop payload is identical on both hosts:

| Core verdict | Claude and Codex Stop output |
| --- | --- |
| allow | `{}` |
| block | `{"decision":"block","reason":"<core reason>"}` |

The configuration wire formats differ: Claude uses a no-shell `command` plus
`args`, while Codex uses POSIX `command` and Windows `commandWindows` strings.
That storage difference must not change PASS/FAIL semantics. Codex project
hooks also require project trust and review of new or changed command hooks.

### Explicit harness-chain adapters

Chain configuration is a separate, hash-approved operation governed by
`harness-chain-contract.md`. It installs five project events and removes the
runtime-owned ordinary Stop entry for that host.

The shared deterministic verdict does not imply identical continuation:

- Claude Stop blocks a nonterminal RUNNING stop and reports the next
  evidence-backed action. It is that run's sole continuation authority.
- Codex continuation belongs to one native goal. Codex Stop does not continue
  a nonterminal run; at a terminal state it emits a hook-run terminal brake.
- both hosts use SessionStart to bind installed hook identity and the current
  session, PreToolUse as a frozen-path early guard, and SubagentStart/Stop to
  bind and record independent review challenges.

Runtime hash checks, evidence freshness, receipt sidecars, and hard counters
remain authoritative. A hook response alone cannot certify completion.

## Integration And Frontend Evidence

A spec criterion marked `integration: true` must map to at least one
`integration`, `e2e`, or `smoke` check. The command must cross the real boundary
named by the claim; a unit test or process-survival probe is not an equivalent
oracle unless the claim is limited to that behavior.

For frontend work, use the chosen project-local browser, accessibility,
terminal, native-window, component, or visual check. The optional detector is:

```text
python .ezpowers/tools/frontend-visual-readiness.py --mode detect
python .ezpowers/tools/frontend-visual-readiness.py --mode check
```

The detector never installs tools or creates screenshots. `check` is blocking
only for lanes the architecture or plan has declared required. Visual or
accessibility claims still require a feature-specific deterministic oracle.

## Non-Substitution Rules

- Passing repository tests does not replace plan validation or required
  project checks.
- Task-scope evidence does not replace all-scope evidence.
- Fresh evidence without certification is not completed work.
- Host review, reviewer text, or an agent's DONE report does not replace
  machine evidence.
- In a chain, main-agent review prose or an unbound reviewer does not replace a
  challenge-bound independent receipt, and a receipt does not replace checks.
- Runtime smoke does not replace a feature-specific criterion.
- A weaker command must not replace an approved oracle merely to obtain PASS.
