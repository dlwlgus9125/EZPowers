---
description: Initialize project harness with config and steering docs
allowed-tools: [Bash, Read, Write, Glob, AskUserQuestion]
---

# /setup — Project Harness Initialization

Set up the EZPowers harness for a project. Interactive process to create config files and steering document scaffolding. No code is written.

## Phase 1: Project State Detection

Read the current working directory to determine if this is an existing or new project.

Check items:
1. Directory listing
2. Manifest file presence (package.json / Cargo.toml / pyproject.toml / go.mod etc.)
3. Source directory presence (src/ / lib/ / app/)
4. `.harness/config.json` presence
5. `AGENTS.md` presence
6. `CLAUDE.md` presence

Detection rules:
- `.harness/config.json` already exists → ask the user whether to overwrite
- Manifest or source directory exists → existing project
- Neither exists → new project

If `phases/index.json` does not exist yet, create immediately with setup phase set to `in_progress`:
```json
{ "current_phase": "setup", "phases": { "setup": { "status": "in_progress" } } }
```

## Phase 2A: Existing Project Analysis

For existing projects, analyze the current state.

Read:
- Manifest files
- Top-level directory structure
- Existing test/build/lint scripts
- `docs/` contents
- `AGENTS.md` if present

Present summary to the user:
```
Project: {name}
Stack: {inferred}
Test command: {inferred}
Build command: {inferred}
Lint command: {inferred}
Smoke command: {inferred or empty string}
Test strategy: {unit/integration/e2e etc.}
```

For unknown values, ask the user directly — do not guess.

## Phase 2B: New Project Setup

For new projects, create base settings through conversation.

Order:
1. Project name and one-line description
2. Tech stack
3. Test strategy
4. build/lint/test commands
5. smoke.command — warn if same as `build.command`. Per-stack guide: CLI (`./dist/cli --version`), server (start → health check → stop), desktop (start → survive N seconds → stop), library (`node -e "require('./dist')"` or ESM import)
6. Preferred execution mode for `/choiceexecutor` (subagent vs harness vs inline)

Suggest presets when possible:
- Next.js + TypeScript
- Python + FastAPI
- Rust + CLI
- Library
- MCP server

## Phase 2.5: Executor Info

Collect executor info so `/plan` can compute step size budgets.

Required values:
- `executor.agent` — model for subagents
- `executor.context_window` — context window size
- `executor.budget_ratio` — allowed ratio per step

Recommended defaults:
```json
{
  "agent": "claude-sonnet-4-6",
  "context_window": 200000,
  "budget_ratio": 0.40
}
```

## Phase 2.7: Document Governance

Confirm with the user:

- "Does this project have a canonical product document?" (if yes, get the path)
- "Do existing architecture docs exist?" (if yes, link to `docs/reference/`)
- "Use ADR (Architecture Decision Records)?"
- "Does this project have a UI?" (if yes, create `docs/ux/` slot; otherwise skip)

## Phase 3: File Creation

Create the following files.

### Directory Creation (before files)

Create required directories before writing files:

```bash
mkdir -p .harness
mkdir -p phases
mkdir -p docs/product
mkdir -p docs/reference
mkdir -p docs/specs
mkdir -p docs/plans
```

If using ADR: `mkdir -p docs/decisions`
If UI project: `mkdir -p docs/ux`

### Required Files

**`.harness/config.json`** — project settings (full schema below)

**`AGENTS.md`** — agent context document:
```markdown
# {Project Name}
> {One-line description}

## Steering
- spec location: docs/specs/
- plan location: docs/plans/

## Stack
{Tech stack summary}

## Conventions
{Project-specific rules — naming, structure, error handling patterns etc.}

## Boundaries
{No-change zones, external contracts, caveats}

## Review Settings
review-skip: {File patterns to skip in review — leave empty if none}
```

**`phases/index.json`** — phase state tracking:
```json
{
  "current_phase": "setup",
  "phases": {
    "setup": { "status": "complete", "completed_at": "2025-01-15T10:30:00Z" },
    "brainstorm": { "status": "pending", "artifact": null },
    "plan": { "status": "pending", "artifact": null },
    "build": { "status": "pending", "artifact": null }
  }
}
```

`status` values: `pending` | `in_progress` | `complete` | `failed`
`artifact`: path to the phase's output (spec, plan, etc.). Required when `complete`.
`completed_at`: ISO 8601 timestamp. Required when `complete`.

**On backward transition:** Set the target phase to `in_progress` and reset subsequent phases to `pending`. Preserve artifacts (for referencing prior outputs).

**`docs/INDEX.md`** — document navigation map (required):
```markdown
# {Project Name}
> One-line project description

## Product Contract
- [PRD](product/PRD.md): [canonical] product requirements definition

## System Reference
- [Architecture](reference/architecture.md): [canonical] system architecture
- [Protocol](reference/protocol.md): [canonical] protocol contract
- [Schema](reference/schema.md): [canonical] DB schema
- [Config](reference/config.md): [canonical] config contract

## Decisions
- [ADR Index](decisions/README.md): architecture decision records

## UX Spec (UI projects only)
- [UX Index](ux/README.md): UI spec index
```

### Document Slots (empty files + frontmatter)

- `docs/product/PRD.md`
- `docs/reference/architecture.md`
- `docs/reference/protocol.md`
- `docs/reference/schema.md`
- `docs/reference/config.md`
- `docs/decisions/README.md` (if using ADR)
- `docs/ux/README.md` (UI projects only)
- `docs/specs/.gitkeep` (spec document directory)
- `docs/plans/.gitkeep` (plan document directory)

### Frontmatter Spec

All doc slots include 3-field YAML frontmatter:

```yaml
---
doc_type: reference
authority: canonical
status: draft
---

This document is the SSOT (Single Source of Truth) for {topic}.
Content is authored by humans.
```

`authority` values: `canonical` (SSOT) / `supporting` (supplementary) / `derived` (auto-generated)

Mark each document's authority in INDEX.md as `[canonical]`, `[supporting]`, or `[derived]`.

### Other Files

- `CLAUDE.md` — if missing, generate a minimal guide

## config.json Schema

```json
{
  "project": "my-project",
  "stack": ["next.js", "typescript", "react"],
  "test": {
    "command": "npm test",
    "strategy": "unit + e2e"
  },
  "build": {
    "command": "npm run build"
  },
  "lint": {
    "command": "npm run lint"
  },
  "smoke": {
    "command": "",
    "description": ""
  },
  "server": {
    "start_command": "",
    "stop_command": "",
    "health_check_url": "",
    "health_check_timeout": 15
  },
  "executor": {
    "agent": "claude-sonnet-4-6",
    "context_window": 200000,
    "budget_ratio": 0.40,
    "backend": "claude-code",
    "reviewer_backend": "claude-code"
  },
  "harness": {
    "root": ""
  },
  "defaults": {
    "spec_location": "docs/specs/",
    "plan_location": "docs/plans/",
    "max_retries": 3,
    "timeout": 1800,
    "auto_push": false,
    "prompt_logging": false,
    "verifier": "off",
    "verifier_max_rounds": 1
  }
}
```

Field descriptions:
- `project`: Project name
- `stack`: Tech stack list (array)
- `test.command`: Test execution command
- `test.strategy`: Test strategy description (unit, integration, e2e, etc.)
- `build.command`: Build command
- `lint.command`: Lint command
- `smoke.command`: Smoke command to verify the actual entrypoint
- `smoke.description`: What the smoke test verifies
- `server.start_command`: Server start command before Verify-type `api`/`e2e` execution (empty string = skip server management)
- `server.stop_command`: Server stop command after Verify completion
- `server.health_check_url`: URL to confirm server readiness (e.g., `http://localhost:3000/health`)
- `server.health_check_timeout`: Max health check wait time (seconds, default 15)
- `executor.agent`: Model for `/choiceexecutor` subagents
- `executor.context_window`: Context window size
- `executor.budget_ratio`: Allowed ratio per step
- `executor.backend`: `/executeharness` execution backend (`claude-code` | `codex-cli` | `openai-api`, default `claude-code`)
- `executor.reviewer_backend`: Verifier subagent backend (default `claude-code`)
- `harness.root`: EasyPowersHarness install path (empty string = `/executeharness` path disabled)
- `defaults.spec_location`: Spec document save directory
- `defaults.plan_location`: Plan document save directory
- `defaults.max_retries`: Step retry count
- `defaults.timeout`: Step timeout (seconds)
- `defaults.auto_push`: Auto-push after completion
- `defaults.prompt_logging`: Save prompt logs
- `defaults.verifier`: `off` or `sub-agent`
- `defaults.verifier_max_rounds`: Verifier max rounds

## Phase 3.5: Eval/Trace Infrastructure (optional flags)

### `--with-evals` Flag

If invoked with `/setup --with-evals`, create the eval directory tree:

```bash
mkdir -p evals/optimization evals/holdout evals/golden evals/honeypot
mkdir -p evals/results/baselines evals/results/runs
mkdir -p evals/rubrics
```

Generated files:
- `evals/INDEX.md` (eval index template)
- `evals/schema.json` (copied from plugin)
- `evals/rubrics/spec_quality.md` (template)

Add to `.claudeignore`: `evals/holdout/**`
Add to `.gitignore`: `evals/holdout/**`, `evals/results/runs/**`

### `--enable-traces` Flag

If invoked with `/setup --enable-traces`, enable trace collection hooks:

1. Check if `hooks/hooks.json` exists (if not, copy from plugin)
2. Create `${CLAUDE_PLUGIN_DATA:-$HOME/.ezpowers-traces}/traces/` directory
3. Add to `.gitignore`: `*.ezpowers-traces/`

The two flags are independent. A user may want evals without trace collection.

## Phase 4: Completion

After creation:
1. List of created files
2. Items the user needs to fill in (especially AGENTS.md Conventions and Boundaries)
3. Next command: `/brainstorm`
