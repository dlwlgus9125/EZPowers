---
doc_type: reference
authority: canonical
status: active
---

# Architecture

EZPowers is a thin, dual-host project workflow plus a deterministic,
project-local verification runtime. It does not replace Claude Code or Codex as
the execution host.

## Product Boundary

The host owns code editing, shell execution, subagents, worktrees, sandbox and
approval policy, review, and retry decisions. EZPowers owns only the parts that
must remain stable across hosts and sessions:

- settled project intent and architecture decisions;
- one managed JSON contract in each feature spec and plan;
- project-specific checks represented as exact argument arrays;
- check output, hashes, workspace freshness, certification, and resume state;
- thin, optional host hook adapters over the same completion verdict.

There is no second executor, numbered execution path, parallel task-state
machine, or host-independent orchestration policy in the v5 architecture.

## Distribution And Installation

The plugin repository contains the nine retained skills and the Claude and
Codex manifests. `setup` installs the project kit into the target repository:

```text
plugin distribution
  -> .ezpowers/                  canonical runtime, config, state, ledger, kit
  -> .claude/skills/             Claude project skill copies
  -> .agents/skills/             Codex project skill copies
  -> .claude/settings.json       optional Claude Stop adapter
  -> .codex/hooks.json           optional Codex Stop adapter
```

The installed `.ezpowers/ezpowers.py` is standard-library only and is the
runtime entry point after installation. The kit is self-contained: installing
or repairing a project must not require this checkout, another repository, or
a hidden user-local script. The target project root is also the Git worktree
root because Git state is part of every completion fingerprint.

`hud` is intentionally excluded from the project kit. It is a plugin-only,
global Codex opt-in described in `docs/reference/codex-hud.md`.

## Workflow And Data Flow

```text
setup
  -> deep-interview (only while material decisions are ambiguous)
  -> design-architecture
  -> spec
  -> prepare-execute
  -> execute with host-native facilities
  -> .ezpowers verify --all
  -> .ezpowers certify
```

`spec` records host-independent observable criteria. `prepare-execute` maps
each criterion to exact project checks. `execute` does not create a second
task-state machine; it implements the plan and asks the local runtime for the
completion verdict.

The runtime executes checks without an implicit shell, stores logs and hashes
under `.ezpowers/evidence/`, and binds a PASS to the current spec, plan,
config, installed-kit identity, Git HEAD, tracked diff, and untracked-file
digest. A bounded project-local lock serializes state writers.
`.ezpowers/state.json` holds only revalidated resume pointers; it never turns a
stale result into PASS. Plan validation is read-only until execution explicitly
activates a resume target. Task-scope pointers are independently revalidated
for resume guidance but cannot promote the all-scope completion verdict.

## Source Of Truth

- Architecture and testing decisions: project architecture artifacts.
- Observable feature claims: the spec managed JSON block.
- Task coverage and exact commands: the plan managed JSON block plus named
  checks in `.ezpowers/config.json`.
- Completion: fresh all-scope evidence and its certificate.
- Host discovery and adapter differences:
  `docs/reference/codex-plugin-discovery.md`.
- Evidence and freshness rules: `docs/reference/verification-contract.md`.

Human-readable Markdown may explain these contracts but must not duplicate or
override the managed JSON values.
