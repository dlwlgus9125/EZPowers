# Setup Contract

This contract defines installation of the self-contained v5 project kit.
`setup` configures deterministic project checks; it does not configure an
external executor or choose how a host performs implementation.

## Inspect First

Read project instructions, manifests, source roots, package scripts, CI files,
tests, existing specs and plans, and any `.ezpowers/config.json`. Infer checks
only from executable repository evidence. Ask one question at a time for a
required command or completion condition that cannot be established from the
repository.

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
preserved unless the user requests refresh or repair. Legacy `.harness/` and
`phases/` files are migration inputs only; v5 does not create or use them.

## Install Or Refresh

For a new project:

```text
python <plugin-root>/scripts/ezpowers.py install --project-root <project>
```

For an installed project upgraded from the current plugin distribution:

```text
python <plugin-root>/scripts/ezpowers.py install --project-root <project> --refresh
```

For a same-version repair from the installed kit:

```text
python .ezpowers/ezpowers.py install --project-root <project> --refresh
```

Add `--enable-hooks claude`, `codex`, or `both` only after the user explicitly
requests project completion hooks. The default is `none`. Installation never
installs a plugin, changes a global marketplace, or configures the global HUD.

## Installed Surface

The manifest and ledger must make these files locally available:

```text
.ezpowers/
  ezpowers.py
  config.json
  state.json
  ledger.json
  kit/manifest.json
  kit/skills/<eight-project-skills>/...
  contracts/...
  tools/frontend-visual-readiness.py
.claude/skills/<eight-project-skills>/...
.agents/skills/<eight-project-skills>/...
```

The eight project skills are `setup`, `deep-interview`,
`design-architecture`, `spec`, `prepare-execute`, `execute`,
`frontend-design`, and `improve-codebase-architecture`. `hud` remains
plugin-only and global.

Each manifest source and installed target is SHA-256 verified. Canonical skill
files and both host copies are byte-identical. The ledger records the kit
version, installation source, timestamp, each managed file hash, and migration
warnings. Missing sources, unsafe paths, hash drift, or host-copy drift fail
installation.

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

## Legacy Migration

When no v5 config exists, setup may translate safe legacy command strings into
argv checks. Preserve the legacy files. Ignore and report fields for external
`harness.root`, executor/model routing, context budgets, retry/verifier policy,
reviewers, phase state, and HUD. A legacy command requiring pipelines,
redirection, or other shell parsing is reported and not migrated.

## Optional Hook Adapters

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

## Verification And Report

Run the installed runtime:

```text
python .ezpowers/ezpowers.py status --json
python .ezpowers/ezpowers.py validate --spec <spec-path>
python .ezpowers/ezpowers.py validate --plan <plan-path>
```

Run only the validation commands whose artifacts already exist. Report managed
and preserved files, configured checks and required checks, ledger path,
migration warnings, hook choice and trust follow-up, conflicts, and unresolved
project completion criteria. The next step is `deep-interview` only when a
material decision remains ambiguous; otherwise use `design-architecture` or
`spec`.
