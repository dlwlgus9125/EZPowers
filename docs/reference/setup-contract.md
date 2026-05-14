# Setup Contract

This reference contains the setup details that do not belong in the `/setup`
controller prompt. `/setup` owns orchestration; this document owns generated
artifact shape.

## Source Contracts

- `docs/reference/mattpocock-harness-adapter.md`
- `docs/reference/domain-language.md`
- `docs/reference/verification-contract.md`

EZPowers automation owns project state. Matt Pocock influence is limited to
short prompts, explicit stop conditions, and fast evidence loops.

## Project Detection

Read the target repo before asking the user:

- Manifests: `package.json`, `Cargo.toml`, `pyproject.toml`, `go.mod`, or peers.
- Source roots: `src/`, `lib/`, `app/`, or framework-specific equivalents.
- Existing `.harness/config.json`, `phases/index.json`, `AGENTS.md`, `CLAUDE.md`.
- Existing `CONTEXT.md` at the project root.
- Existing docs under `docs/`.
- Domain vocabulary: scan for model/entity names, business terms in source files.

Classification:

- Existing `.harness/config.json`: ask whether to overwrite.
- Manifest or source root exists: existing project.
- Neither exists: new project.

Immediately create or update `phases/index.json` with setup `in_progress`
before creating the remaining files.

## Required User Inputs

Infer first, then ask one question at a time for unknowns:

- Project name and one-line description.
- Tech stack.
- Test, build, lint, and smoke commands.
- Smoke artifact kind and GUI strategy.
- Preferred `/choiceexecutor` mode.
- Executor agent, context window, and budget ratio.
- Canonical product doc path, if any.
- Existing architecture docs, if any.
- ADR usage.
- UI presence.
- Architecture profile: lifecycle stage, quality priorities, performance
  budgets, operational constraints, compatibility policy, ADR requirement.
- Domain vocabulary confirmation (after detection results are shown).

Default executor values:

```json
{
  "agent": "claude-sonnet-4-6",
  "context_window": 200000,
  "budget_ratio": 0.40
}
```

## Directories

Create these directories before writing files:

- `.harness`
- `phases`
- `docs/product`
- `docs/reference`
- `docs/specs`
- `docs/plans`

Conditional:

- `docs/decisions` when ADRs are enabled.
- `docs/ux` when the project has UI.

## Required Files

Create or update:

- `.harness/config.json`
- `AGENTS.md`
- `phases/index.json`
- `docs/INDEX.md`
- `docs/product/PRD.md`
- `docs/reference/architecture.md`
- `docs/reference/protocol.md`
- `docs/reference/schema.md`
- `docs/reference/config.md`
- `docs/reference/conventions.md`
- `docs/specs/.gitkeep`
- `docs/plans/.gitkeep`

Conditional:

- `docs/decisions/README.md`
- `docs/ux/README.md`
- `CLAUDE.md` only if missing.
- `CONTEXT.md` when the project has domain-specific terms beyond pure
  infrastructure.

## CONTEXT.md Shape

Generated as a draft slot at the project root. If `CONTEXT.md` already exists,
preserve it and offer to merge new terms.

No frontmatter — `CONTEXT.md` is a project artifact like `CLAUDE.md`, not a
`docs/` reference slot. It is not listed in `docs/INDEX.md`.

Sections:

- **Language** — bold term, one-line definition, _Avoid:_ aliases.
- **Relationships** — how terms relate (e.g. "An Order contains one or more
  Line Items").
- **Flagged Ambiguities** — unresolved terms with resolution status.

Only include terms meaningful to domain experts. Do not couple to
implementation details. Create lazily — only when the first term is resolved.

## Document Slot Frontmatter

Every generated reference slot uses this frontmatter and a one-line SSOT note:

```yaml
---
doc_type: reference
authority: canonical
status: draft
---
```

`authority` values are `canonical`, `supporting`, or `derived`. Reflect the
authority marker in `docs/INDEX.md`.

## AGENTS.md Shape

`AGENTS.md` must include:

- Project name and one-line description.
- Steering paths for specs and plans.
- Stack summary.
- Project conventions.
- No-change boundaries and external contracts.
- Review skip patterns, empty when none.

## docs/INDEX.md Shape

The index must include sections for:

- Product Contract.
- System Reference.
- Decisions when ADRs are enabled.
- UX Spec when the project has UI.
- Specs.
- Plans.

Links must be relative to `docs/`.

## Architecture Reference Slot

`docs/reference/architecture.md` includes:

- System Context.
- Module Boundaries.
- Data Flow.
- Lifecycle And Operations.
- Quality Budgets.
- Architecture Debt.
- Decision Log.

Use collected architecture profile values. Do not leave blanks for values that
can be inferred or asked.

## Config Schema

`.harness/config.json` must preserve these top-level blocks:

```json
{
  "project": "my-project",
  "stack": ["example"],
  "test": { "command": "", "strategy": "" },
  "build": { "command": "" },
  "lint": { "command": "" },
  "smoke": {
    "required": true,
    "artifact_kind": "cli",
    "command": "",
    "description": "",
    "gui_strategy": "skip",
    "startup_timeout_seconds": 15,
    "survival_seconds": 8,
    "stderr_fail_regex": "Unhandled exception|Fatal|Traceback|panic|XamlLoadException|segmentation fault",
    "window_title_regex": "",
    "expected_automation_name_regex": "",
    "expected_text_regex": "",
    "screenshot_path": ".harness/artifacts/gui-smoke.png",
    "min_pixel_variance": 12.0
  },
  "server": {
    "start_command": "",
    "stop_command": "",
    "health_check_url": "",
    "health_check_timeout": 15
  },
  "architecture": {
    "lifecycle_stage": "mvp",
    "quality_priorities": ["maintainability", "reliability", "performance"],
    "performance_budgets": "none declared",
    "operational_constraints": "local development only",
    "compatibility_policy": "breaking changes allowed before production",
    "adr_required": false
  },
  "executor": {
    "agent": "claude-sonnet-4-6",
    "context_window": 200000,
    "budget_ratio": 0.40,
    "backend": "claude-code",
    "reviewer_backend": "claude-code",
    "reviewer_model": "",
    "codex_reviewer_model": ""
  },
  "harness": { "root": "" },
  "defaults": {
    "spec_location": "docs/specs/",
    "plan_location": "docs/plans/",
    "max_retries": 3,
    "timeout": 1800,
    "auto_push": false,
    "prompt_logging": false,
    "verifier": "off",
    "verifier_max_rounds": 1
  },
  "wiring": {
    "enabled": true,
    "exempt_reason": "",
    "view_extensions": [],
    "view_test_command": "",
    "wiring_gate_command": ""
  }
}
```

## Smoke Rules

Executable artifacts (`cli`, `server`, `desktop`) require `smoke.required:
true` and a non-empty `smoke.command`.

Only `docs` and `library` may set `smoke.required: false`.

GUI strategy defaults:

- Avalonia, WPF, WinForms, Qt, GTK: `process_probe`.
- Electron, Tauri: `headless`.
- Console/server: `skip`, but still require a non-empty smoke command.
- Docs/library: `skip` only when runtime smoke is explicitly not required.

Warn if the smoke command is the same as the build command.

## Wiring Rules

Projects with UI presence require `wiring.enabled: true` and a non-empty
`wiring.view_extensions` array. Auto-detect view extensions from the tech
stack. `wiring.view_test_command` and `wiring.wiring_gate_command` may be
empty at setup time — per-task and per-plan commands serve as fallbacks.

Only `docs` and `library` artifacts may set `wiring.enabled: false`. Setting
`enabled: false` requires a non-empty `wiring.exempt_reason`; auto-fill for
docs/library (e.g., `"pure library, no UI components"`).

A missing `wiring` block is a configuration error. All downstream gates
(plan-reviewer, choiceexecutor, wiring-reviewer, pipeline-audit) treat a
missing block as FAIL, not skip.

Stack auto-detection defaults:

| Stack | view_extensions |
|-------|----------------|
| React, Next.js | `[".tsx", ".jsx"]` |
| Vue, Nuxt | `[".vue"]` |
| Angular | `[".component.ts", ".component.html"]` |
| Svelte, SvelteKit | `[".svelte"]` |
| WPF, Avalonia | `[".xaml"]` |
| WinForms | `[".cs"]` (form classes) |
| Qt | `[".qml", ".ui"]` |
| GTK | `[".glade", ".ui"]` |
| Electron, Tauri | `[".tsx", ".jsx", ".html"]` |
| Flutter | `[".dart"]` |
| SwiftUI | `[".swift"]` |

After auto-detection, present the inferred `view_extensions` to the user for
confirmation. If the user declares no UI presence, require an `exempt_reason`.

## Phase Index

Final setup state:

```json
{
  "current_phase": "setup",
  "phases": {
    "setup": { "status": "complete", "completed_at": "2026-05-13T00:00:00Z" },
    "brainstorm": { "status": "pending", "artifact": null },
    "plan": { "status": "pending", "artifact": null },
    "build": { "status": "pending", "artifact": null }
  }
}
```

Status values are `pending`, `in_progress`, `complete`, and `failed`.
Completed phases require `completed_at`. Phases that produce artifacts require
`artifact`.

On backward transition, set the target phase to `in_progress`, reset later
phases to `pending`, and preserve existing artifacts for reference.

## Optional Flags

`/setup --with-evals` creates:

- `evals/optimization`
- `evals/holdout`
- `evals/golden`
- `evals/honeypot`
- `evals/results/baselines`
- `evals/results/runs`
- `evals/rubrics`
- `evals/INDEX.md`
- `evals/schema.json`
- `evals/rubrics/spec_quality.md`

It also ignores `evals/holdout/**` and `evals/results/runs/**`.

`/setup --enable-traces` creates or reuses `hooks/hooks.json`, creates the
plugin data trace directory, and ignores `*.ezpowers-traces/`.

The two flags are independent.

## Completion Report

Report:

- Created or updated files.
- Config values inferred from repo evidence.
- Config values supplied by the user.
- Remaining human-authored docs.
- Smoke command and GUI strategy.
- Next command: `/brainstorm`.
