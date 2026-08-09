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

Readiness covers the runtime-owned project hook definitions only. Codex merges
hooks from every active config layer and requires trust again when a
non-managed hook hash changes; user, managed, or plugin hooks may still run.
Claude may also enforce its own loop-safety cutoff. Resolve those host-level
policies before leaving a run unattended. An EZPowers hard limit is a maximum,
not a promise that a host or external service will remain available until it.

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

Every criterion must be covered exactly once by an oracle. Every oracle names
its observable boundary, positive case, negative case, exact mapped checks,
artifact paths, and expected current baseline. Source-presence, string,
test-name, or prose-only boundaries are invalid.

Preview validates the staged spec and plan against the actual project config.
For UI work it also validates the frontend managed mapping and each staged
DESIGN.md against its retained profile. It then runs the oracle checks against
an isolated current-workspace overlay and
requires the declared baseline result. Preview identity binds:

- request, host, stages, risks, and effective limits;
- staged file bytes and current target hashes;
- current chain and project-check hashes;
- exact required check argv;
- baseline result and installed-kit identity.

Preview is `REVIEW_REQUIRED` until a bound independent `oracle-audit` receipt
passes for that exact hash. Any input change creates a new hash.
A bound audit `FAIL` makes that exact preview ineligible for another audit.
The staged acceptance contract must change and produce a new preview hash;
cycling independent reviewers over unchanged evidence is not a retry path.

Apply requires one explicit approval for a `READY` preview. Replaced files
require approved `--force` and are backed up. Apply writes the staged files and
immutable `.ezpowers/approvals/<run-id>.json`, clears old completion pointers,
and enters `PENDING_LOOP`.

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
does not disable organization-managed or user-owned host hooks.

After feature approval, normal product edits and retries inside the approved
limits need no additional human approval. Host-owned permission boundaries
still apply.

## Frozen contract and reapproval

The feature approval freezes by path and SHA-256:

- project chain configuration;
- project verification configuration and exact required argv;
- managed spec and plan;
- every architecture artifact when `design_architecture` was selected;
- the broad frontend-design artifact and every applicable DESIGN.md for UI
  work;
- every acceptance-oracle file;
- approval identity.

PreToolUse denies obvious writes to these paths, but the authoritative check
is a fresh hash comparison before verification, review, and certification.
Missing or changed frozen material immediately sets `NEEDS_REAPPROVAL`.
Evidence cannot thaw it. A new preview, oracle audit, and human approval are
required.

Product source is not frozen and is expected to change during implementation.

## Independent gates

`oracle-audit`, `code-review`, `adversarial-qa`, and `blocker-review` use
challenge IDs. `SubagentStart` binds one real host-native subagent ID, host
session, agent type, kind, and subject. Only that bound agent's SubagentStop
message can create a receipt.

The terminal marker contains schema version, challenge ID, `PASS`, `FAIL`, or
allowed `BLOCKED` verdict, blocking findings, and non-empty observations. The
marker is a single fenced `json` code block between the gate start and end
comment lines with exactly those five keys, and the injected rubric carries a
matching template. PASS cannot contain blocking findings; FAIL or BLOCKED
requires at least one. Main-agent prose, an unbound agent,
malformed JSON, reused challenges, manually edited files, or receipts whose
hash sidecar/pointer differs are not valid review evidence.

Code review and adversarial QA bind the exact latest fresh all-scope evidence
SHA-256. New verification invalidates their usefulness. Adversarial QA is
mandatory for approved user-facing, integration, or regression risks and for
configured project triggers. `BLOCKED` is accepted only from a
`blocker-review`.

A valid code-review or adversarial-QA `FAIL` clears product-gate pointers,
invalidates the latest chain PASS, and stores the reviewed workspace
fingerprint. Another product review is unavailable until repository content
changes and a new all-scope verification passes. A structured-receipt format
error is different: the same bound reviewer must correct the same challenge
without editing the repository.

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
Evidence includes the run ID, approval path and hash, and chain hash. Any
all-scope verification invalidates older code-review and QA pointers. On FAIL,
the product must be reworked and real checks rerun; changing the oracle or
check is reapproval, not rework.

The failed workspace fingerprint is durable state. Another all-scope
verification against identical repository content is rejected and counts as
a validation failure; task-scoped diagnostic checks cannot clear this
requirement. A content change permits verification but does not itself prove
the fix—the exact checks must still pass.

Certification requires:

- fresh all-scope PASS evidence bound to the active approval;
- a fresh independent code-review PASS receipt for that evidence;
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

Claude Stop blocks while RUNNING and returns the next evidence-backed action.
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
