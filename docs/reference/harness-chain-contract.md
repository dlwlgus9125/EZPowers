# Harness Chain Contract

This contract defines the explicit, project-local EZPowers harness chain.
Claude Code and Codex own implementation and native orchestration. EZPowers
owns frozen acceptance inputs, exact command execution, review receipt
binding, hard limits, evidence freshness, certification, and resume state.

The chain is opt-in. Installing EZPowers does not configure it, and ordinary
`execute`, `verify`, and `certify` retain their normal behavior when no
matching chain run is active.

## Configuration

The canonical project configuration is `.ezpowers/chain.json`. It records:

- enabled hosts;
- `auto` or `always` selection for `deep-interview`,
  `frontend-design`, and `design-architecture`;
- project-specific additional adversarial-QA triggers;
- hard limits for total continuations, QA cycles, validation failures, review
  failures, and identical repeated failures.

Configuration uses a hash-bound preview/apply pair. Apply writes only
project-local configuration and hooks. It requires one explicit user approval
for the exact preview. Unknown Stop hooks conflict because a configured chain
must have one continuation authority.

Preview checks the selected host executables before it can become `READY`.
Claude requires Claude Code 2.1.217 or newer and Codex requires Codex CLI
0.145.0 or newer. Missing, unreadable, or outdated selected hosts are reported
without writing configuration or hooks.

Both host adapters install `SessionStart`, `Stop`, `PreToolUse`,
`SubagentStart`, and `SubagentStop` handlers. A host is ready only after the
installed hook identity and a real SessionStart session ID are recorded.
Host trust, sandbox, login, secret, billing, and permission prompts remain host
responsibilities; EZPowers does not bypass them.

A host's hooks count as installed only when every chain event has a
runtime-owned entry whose matcher equals the installed kit's definition. After
`setup --refresh` to a kit that changes those definitions, status reports the
host's hooks as missing or changed, no handshake is recorded, and a
nonterminal run on that host becomes `NEEDS_REAPPROVAL`. Finish or abandon an
in-flight run before refreshing; afterwards apply the chain configuration
again, restart the host session, and approve the feature again.

Claude Code does not report its permission mode on SessionStart. The runtime
takes it from the first hook event of that session that reports one, and until
then status says the session has not reported a mode. A mode that has not been
observed is not treated as a changed one. Claude Code is unattended-capable in
`auto`, `dontAsk`, or `bypassPermissions`; Codex readiness still requires
`dontAsk` or `bypassPermissions`. In `auto` the host's classifier can deny an
action or return to prompting after repeated blocks. That boundary stays
host-owned; disclose it before feature approval.

Readiness covers the runtime-owned project hook definitions only. Codex merges
hooks from every active config layer and requires trust again when a
non-managed hook hash changes; user, managed, or plugin hooks may still run.
Claude Code overrides a Stop hook after eight continuations in a row with no
tool call between them, and chain hooks do not run in a `--bare` session.
Resolve those host-level policies before leaving a run unattended. An EZPowers
hard limit is a maximum, not a promise that a host or external service will
remain available until it. No part of the Codex chain has been verified on a
live host.

## Feature approval

A feature bundle lives under `.ezpowers/staging/` and declares one request,
host, optional-stage decisions with reasons, risk classes, one managed spec,
one managed plan, and one or more acceptance-oracle files. When the spec has
`design_context.required: true`, the same bundle also declares exactly one
`frontend-design` file and every listed `design-system` file. Their targets
must exactly match the spec and the managed frontend mapping.
When `design_architecture` is selected, the bundle also declares one or more
safe Markdown files with role `architecture`; when it is not selected, that
role is absent. The files are already-settled architecture inputs, not a
license to invent boundaries during implementation.

The project config fixes the profile for the whole run. Software uses bundle
schema v1 and plan v1/v2. Planning uses bundle schema v2 with
`project_profile: planning` and plan v3. Planning inputs stay at their real
project paths and may be arbitrary binary or text files; staged `files` remain
UTF-8 acceptance adapters and managed documents. Planning outputs are logical
multi-file deliverables declared by the plan, not staged acceptance files.

Every criterion must be covered exactly once by an oracle. Every oracle names
its observable boundary, positive case, negative case, exact mapped checks,
artifact paths, and expected current baseline. Source-presence, string,
test-name, or prose-only boundaries are invalid.

Preview validates the staged spec and plan against the actual project config.
For UI work it also validates the frontend managed mapping and each staged
DESIGN.md against its retained profile. It then runs the oracle checks against
an isolated current-workspace overlay and
requires the declared baseline result. The baseline always executes its checks
and never carries a recorded PASS. An oracle check that declares `reuse` must
select every one of its oracle's `artifact_paths`; otherwise preview fails.
Preview identity binds:

- request, host, stages, risks, and effective limits;
- staged file bytes and current target hashes;
- current chain and project-check hashes;
- exact required check argv;
- baseline result and installed-kit identity.
- for planning, the frozen input path/byte inventory and logical deliverable
  contract, including direct or inspected review sources.

Preview is `REVIEW_REQUIRED` until a bound independent `oracle-audit` receipt
passes for that exact hash. Any input change creates a new hash.
A bound audit `FAIL` makes that exact preview ineligible for another audit. So
do two rejected hand-backs on one audit challenge, and so does abandoning or
replacing an audit challenge that had a reviewer bound.
The staged acceptance contract must change and produce a new preview hash;
cycling independent reviewers over unchanged evidence is not a retry path.
An oracle audit cannot begin while a run is `PENDING_LOOP` or `RUNNING`: one
feature is audited, approved, and run at a time.

Apply requires one explicit approval for a `READY` preview. Replaced files
require approved `--force` and are backed up. Apply writes the staged files and
immutable `.ezpowers/approvals/<run-id>.json`, clears old completion pointers,
and enters `PENDING_LOOP`. New software approvals use schema v2. Planning
approvals use schema v3 and also bind the project profile, byte-hashed inputs,
and logical deliverable contract. Both bind the assurance graph derived by the
same normalizer used for ordinary plans.

## One host-native loop

Activation binds exactly one authority:

| Host | Continuation authority | Stop adapter |
| --- | --- | --- |
| Codex | one native Codex goal using the exact returned objective | observer and terminal brake |
| Claude Code | the project Stop hook | sole continuation loop |

The objective hash, approved host, trusted hook handshake, and authority name
must match. EZPowers does not route models, translate plans into phases, own
implementation tasks, or call an external executor.

“Exactly one” means one EZPowers continuation authority for the feature; it
does not disable organization-managed or user-owned host hooks. Claude Code's
native `/goal` is a session-scoped Stop hook judged by a model from the
transcript; never combine it with the chain Stop hook for one feature.

A Claude Stop that arrives while the run is `RUNNING` and a background
subagent is still running neither blocks nor counts: the host resumes the
session when that subagent reports. Background shells and monitors never defer
a Stop. A reviewer that never reports therefore leaves the run waiting; the
runtime does not time it out.

After feature approval, normal product edits and retries inside the approved
limits need no additional human approval. Host-owned permission boundaries
still apply.

## Frozen contract and reapproval

The feature approval freezes by path and SHA-256:

- project chain configuration;
- project verification configuration and exact required argv, including every
  check's `reuse` declaration;
- managed spec and plan;
- the deterministic assurance-graph SHA-256, including task dependencies,
  check occurrences, concurrency contracts, and required-check phase;
- every architecture artifact when `design_architecture` was selected;
- the broad frontend-design artifact and every applicable DESIGN.md for UI
  work;
- every acceptance-oracle file;
- approval identity.
- for planning, every declared input path and SHA-256.

PreToolUse is an early guard. It denies a file tool whose target is a frozen
file, and a shell command that names one together with a direct mutation, an
in-place edit, inline interpreter code, a redirection into it, or a copy onto
it. It allows the runtime's own commands, a script or test run that names a
frozen file, and a copy of one to another place, and it ignores text that only
mentions one. On Claude Code it inspects `Bash`,
`PowerShell`, `Write`, `Edit`, and `NotebookEdit`. Indirect writes pass it; the
authoritative check is a fresh hash comparison before verification, review,
and certification.
Missing or changed frozen material immediately sets `NEEDS_REAPPROVAL`.
Evidence cannot thaw it. A new preview, oracle audit, and human approval are
required. On explicit kit refresh, a nonterminal legacy approval that predates
the graph binding also becomes `NEEDS_REAPPROVAL`; the runtime never invents a
hash for an approval the user did not inspect.

Software product source is not frozen and is expected to change during
implementation. Planning deliverable output paths are likewise mutable until
verification; their exact bytes become evidence only after real checks pass.

## Independent gates

`oracle-audit`, `code-review`, `artifact-review`, `adversarial-qa`, and `blocker-review` use
challenge IDs. `SubagentStart` binds one real host-native subagent ID, host
session, agent type, kind, and subject. Only that bound agent's final report
can create a receipt: on Claude Code the message of its SubagentHandback call
when that carries a gate marker, otherwise its SubagentStop message. The two
are never combined.

The terminal marker contains schema version, challenge ID, `PASS`, `FAIL`, or
allowed `BLOCKED` verdict, blocking findings, and non-empty observations. The
marker is a single fenced `json` code block between the gate start and end
comment lines with exactly those five keys, and the injected rubric carries a
matching template. PASS cannot contain blocking findings; FAIL or BLOCKED
requires at least one. Main-agent prose, an unbound agent,
malformed JSON, reused challenges, manually edited files, or receipts whose
hash sidecar/pointer differs are not valid review evidence.

Software uses `code-review` as its mandatory primary gate. Planning replaces
that gate with `artifact-review`. Its terminal marker uses schema v2 and
contains exactly `schema_version`, `challenge_id`, and ordered `deliverables`.
Every deliverable entry contains exactly its ID, `PASS` or `FAIL`, findings,
non-empty observations, and all required `reviewed_sources`. Direct sources
bind declared output path/bytes; inspected sources bind the exact PASS check
occurrence and stdout/stderr log hashes. The runtime derives the single gate
verdict only after every declared deliverable has a valid result.

Code review, artifact review, and adversarial QA bind the exact latest fresh
all-scope evidence SHA-256. New verification invalidates their usefulness. Adversarial QA is
mandatory for approved user-facing, integration, or regression risks and for
configured project triggers. `BLOCKED` is accepted only from a
`blocker-review`.

A valid code-review, artifact-review, or adversarial-QA `FAIL` clears product-gate pointers,
invalidates the latest chain PASS, and stores the reviewed workspace
fingerprint. Another product review is unavailable until repository content
changes and a new all-scope verification passes. A structured-receipt format
error is different: the same bound reviewer must correct the same challenge
without editing the repository. A finished run left in state does not end a
pending oracle audit, so that rule holds for every feature after the first.

Claude Code does not continue a subagent that already handed its report back,
so there a rejected hand-back releases the binding for a new reviewer on the
same challenge instead. That replacement is bounded. Inside a run every
rejection counts as a review failure and the approved review limit ends the
run. Before a run nothing counts: an oracle audit allows one replacement, and
a second rejected hand-back closes that preview exactly as a bound audit
`FAIL` does.

### Challenge lifecycle

One challenge is pending at a time, and it has an owner. A product gate
(`code-review`, `artifact-review`, `adversarial-qa`, `blocker-review`) belongs
to the run that was `RUNNING` when it began. An oracle audit belongs to its
preview hash. A rejected audit receipt never counts against a run.

A challenge ends when its bound reviewer's receipt is accepted, when its owner
ends, when `chain gate begin` names a new subject of the same kind, when it is
abandoned, or through the bounds on rejected reports above. The gate of a run
that has ended is dropped by the next `chain gate begin` and binds no later
subagent.

Ending a challenge without a receipt is fail-closed once a reviewer is
involved. An oracle audit that ever had a reviewer bound closes its preview. A
product gate with a reviewer bound counts one review failure in its running
run, at most once for each reviewer. A challenge that never had a reviewer,
and the gate of a run that has ended, leave nothing. A hand-back with a gate
marker that is already stored on the challenge is judged first, so a `FAIL`
that arrived cannot be abandoned away.

`chain gate abandon` is for a bound reviewer that cannot report. Before
approval it closes the preview. Inside a run it counts one review failure and
releases the same challenge for one new reviewer, or ends the run at the
review limit. A later report from an abandoned reviewer is ignored.

A rejection is recorded on the challenge as one short ASCII line written by
the runtime. `chain gate begin` for the pending challenge repeats it as
`previous_receipt` with a `next_step`, and inside a run the next action
repeats it when that challenge is the one the run is waiting for. While a
reviewer is bound, both tell the main agent to wait before they mention
abandoning.

Chain hooks decode host input as UTF-8 and answer with ASCII-only JSON, so a
console whose locale encoding is not UTF-8 cannot corrupt a report.

Artifact-review failure additionally stores the exact byte inventory of every
failed logical deliverable. Another all-scope verification is rejected until
each failed group changes bytes; a change to unrelated repository content or
only a subset of failed groups is not product rework.

Independent review does not replace deterministic checks. Deterministic checks
do not replace independent review.

## Failure and continuation limits

The approval stores effective limits. Feature overrides can lower but never
raise project limits.

- every failed verification increments `validation_failures`;
- every failed or invalid post-verification review increments
  `review_failures`;
- completed failed adversarial QA increments `qa_cycles`;
- each host continuation event increments `iterations`;
- consecutive failures with the same canonical signature increment
  `identical_error_repeats`.

When a counter reaches its limit, the run becomes `FAILED` immediately. The
runtime rejects an extra verification, review, or continuation attempt. A
PASS clears only the consecutive identical-failure counter; it does not erase
historical attempts.

## Verification, evidence, and certification

For a matching RUNNING chain, `verify` first checks the frozen approval.
Evidence includes the run ID, approval path and hash, chain hash, and graph
hash. Staged plan validation, isolated baseline checks, ordinary verification,
and certification use the shared plan/config normalizer. A plan-v2 baseline
may overlap only the explicitly safe oracle checks under the same resource-lock
and worker-cap rules; version-1 baselines remain serial. Planning v3 uses the
same scheduler and binds its artifact inventory. Any all-scope verification
invalidates the older profile-primary-review and QA pointers. On FAIL,
the product must be reworked and all-scope verification run again; changing the
oracle or check is reapproval, not rework.

Content-bound check reuse applies to chain verification with one additional
condition: a recorded PASS is carried only from a result bound to the same
approved run. Feature apply clears earlier reuse candidates, so the first
verification after approval executes every check and nothing verified before
approval can satisfy the frozen contract. Later rework verifications carry a
declared check whose selected content is unchanged. Gate, rework, and limit
rules do not change: a carried result is part of the fresh all-scope evidence
that every review binds, and a carried check that would have passed again
proves nothing new about the rework.

The failed workspace fingerprint is durable state. Another all-scope
verification against identical repository content is rejected and counts as
a validation failure; task-scoped diagnostic checks cannot clear this
requirement. For planning artifact-review failure, every failed logical group
must change bytes even when Git ignores it. A qualifying content change permits
verification but does not itself prove the fix—the exact checks must still pass.

Certification requires:

- fresh all-scope PASS evidence bound to the active approval;
- a fresh independent code-review PASS receipt for software, or a complete
  per-deliverable artifact-review PASS receipt for planning;
- a fresh adversarial-QA PASS receipt when required;
- unchanged frozen contract, current workspace, installation, logs, sidecars,
  pointers, and exact check inventory.

The certificate binds the approval, evidence, and required receipt hashes.
Successful certification sets chain status `CERTIFIED`.
Status revalidates those receipt files, sidecars, pointers, reviewer bindings,
and workspaces; deleting or changing a receipt invalidates certification even
though `.ezpowers/evidence/` is excluded from the product workspace hash.

## Terminal and resume states

- `PENDING_LOOP`: approved but not bound to its host authority;
- `RUNNING`: unattended implementation/rework/review may continue;
- `NEEDS_REAPPROVAL`: frozen inputs changed;
- `BLOCKED`: an independent blocker review confirmed an external impasse;
- `FAILED`: an approved hard limit or invalid chain invariant was reached;
- `CERTIFIED`: fresh verification, required independent gates, and
  certificate agree.

Claude Stop blocks while RUNNING and returns the next evidence-backed action,
except while a background subagent is still running. A deferred Stop is not a
continuation event and does not increment `iterations`.
Codex Stop does not continue work because the native goal is authoritative.
Both permit the host to stop at terminal state. A chain hook that cannot read
runtime state degrades to a fail-safe no-op response with exit 0 instead of
blocking: a corrupt loop dies rather than wedging the session, and the
authoritative contract checks still gate verification, review, and
certification. Resume uses repository state
and hashed artifacts, never conversation memory.

Terminal states do not grant authority to weaken checks, repair evidence,
silently expand scope, change global configuration, or request approval merely
to avoid product rework.
