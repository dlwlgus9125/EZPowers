# Setup Contract

This contract defines installation of the self-contained v5.6 project kit.
`setup` configures deterministic project checks and may stage the
repository-aware documentation workflow defined by
`documentation-contract.md`; it does not configure an external executor or
choose how a host performs implementation.

## Inspect First

Read project instructions, existing Markdown, manifests, source roots, package
scripts, CI files, tests, existing specs and plans, root or app-local
`DESIGN.md` files, and any
`.ezpowers/config.json` or `.ezpowers/docs.json`. Infer checks and documentation
claims only from repository evidence. Ask one question at a time for a required
command, authority choice, or completion condition that cannot be established
from the repository.

The target path must be the top level of an existing Git worktree. Installation
checks this before writing files and fails if Git is unavailable, the path is
not a worktree, or a worktree subdirectory was supplied. This is required
because completion freshness binds Git HEAD, tracked changes, and untracked
content.

The runtime requires Python 3.10 or newer and only the Python standard library.
Run `python --version` before invoking it and fail with that explicit
prerequisite when the selected interpreter is older or unavailable. Python 3.9
cannot parse the runtime, so this preflight cannot be deferred to the script.

An existing `.ezpowers/config.json` is an installed project and must be
preserved unless the user requests refresh or repair. Pre-v5 `.harness/` and
`phases/` content is retired. v5 neither reads nor translates it and leaves
those files untouched.

## Install Or Refresh

For a new project:

```text
python <plugin-root>/scripts/ezpowers.py install --project-root <project>
```

For an installed project upgraded from the current plugin distribution:

```text
python <plugin-root>/scripts/ezpowers.py install --project-root <project> --refresh
```

An older v5 installation does not update implicitly. The explicit refresh
changes the installed kit identity and makes prior completion evidence stale.
If any managed target differs from its ledger hash, refresh reports every
conflict and writes none of the replacement set.

For a same-version repair from the installed kit:

```text
python .ezpowers/ezpowers.py install --project-root <project> --refresh
```

Add `--enable-hooks claude`, `codex`, or `both` only after the user explicitly
requests project completion hooks. Add `--enable-wiki-hooks claude`, `codex`,
or `both` only after separate explicit approval for the allowlisted SessionEnd
capture described by `wiki-contract.md`. Both defaults are `none`. Configuring
Claude-specific hooks requires Claude Code 2.1.217 or newer; configuring
Codex-specific hooks requires Codex CLI 0.145.0 or newer. All selected hosts
are checked before any install write.
Installation never installs a plugin, changes a global marketplace, or
configures the global HUD.
It installs the explicit `harness-chain` skill and contract but does not create
`.ezpowers/chain.json`, feature approvals, or chain hooks. Those require the
separate questions and hash-bound approval in `harness-chain-contract.md`.

## Installed Surface

The manifest and ledger must make these files locally available:

```text
.ezpowers/
  ezpowers.py
  config.json
  state.json
  ledger.json
  kit/manifest.json
  kit/skills/<thirteen-project-skills>/...
  contracts/...
  tools/frontend-visual-readiness.py
  tools/architecture-review-report.py
  tools/design-md.py
.claude/skills/<thirteen-project-skills>/...
.agents/skills/<thirteen-project-skills>/...
```

The thirteen project skills are `setup`, `deep-interview`,
`explain-with-evidence`, `diagnose`, `codebase-design`,
`improve-codebase-architecture`, `design-architecture`, `spec`,
`prepare-execute`, `execute`, `frontend-design`, `wiki`, and `harness-chain`.
`hud` remains plugin-only and global. Engineering practices, documentation,
wiki, harness-chain, frontend-design, and pinned DESIGN.md profile contracts
are installed with the existing workflow contracts. The explanation skill's
Apache-2.0 license and adaptation notice
are installed beside its `SKILL.md` without being loaded as prompt context.

Each manifest source and installed target is SHA-256 verified. Canonical skill
files and both host copies are byte-identical. The ledger records the kit
version, installation source, timestamp, and each managed file hash. Missing
sources, unsafe paths, hash drift, or host-copy drift fail installation.

Every install or refresh also validates the complete config schema before
writing managed files. Installation and other state-writing operations use a
bounded project-local `.ezpowers/runtime.lock`; concurrent writers fail with a
clear busy result rather than interleaving state. The lock file is runtime
state and is excluded internally from workspace fingerprints. The installer
does not edit the target project's `.gitignore`; a project may add the exact
`.ezpowers/runtime.lock` path to its ignore file if it wants Git to hide it.

## Managed File Ownership

Installation may create a missing managed file or replace a file whose bytes
still match its previous ledger hash. A user-modified managed file is a
conflict: preserve it, report the path, and exit non-zero. Do not synthesize a
missing skill, contract, runtime, or tool from prompt text.

Unknown fields in user-owned configuration are preserved. Refresh is repair,
not authority to overwrite a customized managed file.

## Config Schema

`.ezpowers/config.json` schema version 1 is intentionally small:

```json
{
  "schema_version": 1,
  "project_name": "example",
  "checks": {
    "unit": {
      "argv": ["python", "-m", "unittest"],
      "cwd": ".",
      "timeout_seconds": 120,
      "kind": "test"
    }
  },
  "required_checks": ["unit"]
}
```

Check IDs are 1-64 characters, start with a letter, and contain only letters,
digits, `.`, `_`, or `-`. `argv` is a non-empty string array executed without
an implicit shell. `cwd` is an existing project-relative directory with no
traversal. `timeout_seconds` is an integer from 1 through 86400. `kind` is one
of `build`, `custom`, `e2e`, `integration`, `lint`, `security`, `smoke`,
`static`, `test`, `typecheck`, or `visual`. Placeholder/no-op commands,
explicit shell pipelines, redirections, control operators, PowerShell encoded
or opaque command forms, and `cmd /K` are invalid. A literal operator-looking
argument passed to an ordinary direct executable is not treated as a shell
pipeline.

Every `required_checks` entry must name a check in `checks`. Required checks
run in addition to every plan task check during `verify --all`.

## State Initialization

`.ezpowers/state.json` starts with schema version 1, no active plan, no all- or
task-scope evidence pointers, and no certificate pointer. State is a resume
index, not completion evidence; every pointer is revalidated against the
evidence files, exact scope/inventory, installed kit, and current workspace.
Malformed pointer containers fail closed. Plan validation is read-only unless
the caller supplies `--activate`; that explicit transition changes the resume
target and invalidates pointers only when the selected plan changes.
The same file initializes empty chain host handshakes, gate receipts, and run
state. Those inert fields do not activate a chain or change ordinary
verification.

## Explicit Harness Chain

The installed chain skill is dormant until the user invokes it. Its
configuration preview/apply writes `.ezpowers/chain.json` and merges
SessionStart, Stop, PreToolUse, SubagentStart, and SubagentStop handlers for
the explicitly selected hosts. Preview requires Claude Code 2.1.217 or newer
for Claude and Codex CLI 0.145.0 or newer for Codex, reports each prerequisite,
and cannot become `READY` when one is missing or outdated. This is a separate
approval from installation and from the ordinary optional completion hook
below.

An existing non-EZPowers Stop hook conflicts with chain configuration because
the chain requires one continuation authority. Configuring a chain replaces
the runtime-owned ordinary completion Stop entry for that host, preserves
unrelated non-Stop hooks, and then requires a fresh SessionStart handshake.
The complete approval, host asymmetry, and evidence rules are in
`harness-chain-contract.md`.

## Pre-v5 Clean Break

When no v5 config exists, installation creates the small default v5 config
from repository identity only. Retired pre-v5 files remain user-owned and
untouched; they are not configuration inputs, warning sources, or command
sources. A user who wants an old check retained must confirm it as a new
exact-argv v5 check.

## Documentation Bootstrap

Documentation bootstrap is a separate setup lane governed by
`documentation-contract.md`. The setup skill may interpret `--refresh-docs`,
but that flag is not passed to the runtime installer. It analyzes the
repository, stages a bundle under `.ezpowers/staging/`, previews its exact
effect, and applies it only with the matching preview hash.

Ordinary `install --refresh` updates or repairs only manifest-owned kit files.
It never creates, adopts, or replaces repository documentation. A ready graph
must include canonical `AGENTS.md`, exact `CLAUDE.md` import shim, and
`docs/INDEX.md`; it records ownership and hashes in `.ezpowers/docs.json` and
adds `ezpowers.docs` to required checks. Existing unmanaged documents are
preserved unless the bundle marks explicit adoption and the user authorizes a
force-backed apply.

Analysis also discovers an existing canonical architecture, C4, arc42, or
organization-standard document and registers it without relocation or
duplication. When none exists but repository evidence shows multiple
meaningful runtime/module/deployment boundaries or consequential API/data
ownership, setup leaves the graph incomplete and hands authorship to
`design-architecture`; it does not synthesize plausible boundaries. The
default new primary path is root `ARCHITECTURE.md`.

Analysis detects existing root and frontend-local `DESIGN.md` files and reports
candidate frontend roots. It does not auto-adopt, relocate, normalize, or
migrate them. A newly managed DESIGN.md uses validator `design-md` and an
explicit retained profile. When a ready graph contains such entries, exactly
one broader `frontend-design` role supplies their mappings and setup also
registers `ezpowers.design`. Old-profile migration follows the ordinary
preview, explicit approval, and backup rules; installer refresh alone never
changes repository design documents.

## Ordinary Optional Hook Adapters

With explicit opt-in, merge one owned Stop command into
`.claude/settings.json` and/or `.codex/hooks.json`. Resolve and safely quote
the current Python executable and the installed runtime as absolute paths so a
host session started below the project root still reaches the same runtime:

```text
<absolute-python> <absolute-project>/.ezpowers/ezpowers.py hook --host claude
<absolute-python> <absolute-project>/.ezpowers/ezpowers.py hook --host codex
```

The host configuration shapes are intentionally different. Claude stores the
absolute Python executable in `command` and the remaining tokens in `args`, so
no shell quoting is needed. Codex stores a POSIX-safe `command` plus a Windows
`commandWindows` string because its hook schema does not expose a separate
argument array. Both invoke the same installed runtime and emit the same Stop
payload: `{}` when stopping is allowed, or
`{"decision":"block","reason":"..."}` when it is not.

Preserve unrelated settings and hooks. A conflicting non-object hook structure
is an installation conflict. Codex project hooks require a trusted project and
review of a new or changed command hook through `/hooks`; report that required
host step rather than claiming the hook is active immediately.

With separate explicit wiki approval, merge one owned SessionEnd command into
the same host file:

```text
<absolute-python> <absolute-project>/.ezpowers/ezpowers.py wiki capture --host claude
<absolute-python> <absolute-project>/.ezpowers/ezpowers.py wiki capture --host codex
```

Completion and wiki hooks are identified and updated independently, so
enabling both cannot replace one with the other. Wiki handlers use a five
second timeout, return `{}`, and never influence the completion verdict. Their
strict capture and privacy contract is `wiki-contract.md`.

These installer flags do not activate `harness-chain`. The ordinary Stop
adapter only maps current certification status. Chain hooks are installed
later through their own preview/apply flow and follow the asymmetric contract
instead of pretending Claude and Codex have identical continuation behavior.

## Verification And Report

Run the installed runtime:

```text
python .ezpowers/ezpowers.py status --json
python .ezpowers/ezpowers.py docs status --json
python .ezpowers/ezpowers.py validate --spec <spec-path>
python .ezpowers/ezpowers.py validate --plan <plan-path>
```

Run only the validation commands whose artifacts already exist. Report managed
and preserved files, configured checks and required checks, ledger path, host
prerequisite results, hook choice and trust follow-up, conflicts, and unresolved
project completion criteria. Report documentation status and backup paths, and
report completion-hook and wiki-hook choices separately. The next step is
`deep-interview` only when a material decision remains ambiguous; otherwise
use `design-architecture` or `spec`.
