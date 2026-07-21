# Setup Contract

This reference contains the setup details that do not belong in the `/setup`
controller prompt. `/setup` owns orchestration; this document owns generated
artifact shape.

## Source Contracts

- `docs/reference/mattpocock-harness-adapter.md`
- `docs/reference/domain-language.md`
- `docs/reference/reviewer-placement-contract.md`
- `docs/reference/verification-contract.md`
- `docs/reference/app-delivery-contract.md`
- `docs/reference/harness-kit-contract.md`
- `docs/reference/ui-verification-adapter-contract.md`

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
- Preferred `/choice-execute` mode.
- Executor agent, context window, and budget ratio.
- Canonical product doc path, if any.
- Existing architecture docs, if any.
- ADR usage.
- UI presence.
- UI verification capability, adapter, fallback adapter, and oracle when UI is
  present.
- Frontend design readiness artifact, token source, component inventory, and
  visual QA strategy when UI is present.
- App delivery profile: surface kind, frontend, backend, packaging,
  deployment, and QA strategy.
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
- `docs/release` when packaging or deployment is in scope.

## Required Files

Create or update (in the target project, not in the EZPowers plugin repo):

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
- `docs/reference/project-structure.md`
- `docs/reference/testing-methodology.md`
- `docs/product/ROADMAP.md`
- `docs/specs/.gitkeep`
- `docs/plans/.gitkeep`

Conditional:

- `docs/decisions/README.md`
- `docs/ux/README.md`
- `docs/ux/frontend-design.md`
- `docs/release/README.md`
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
- Release And Deployment when packaging or deployment is in scope.
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

`architecture.lifecycle_stage` defaults to `"undecided"`, not MVP. `/setup`
may infer the lifecycle from repo evidence or explicit user input, but it must
not silently shrink scope to MVP. If the value remains `"undecided"`, route to
`/design-architecture` to confirm it before architecture completion.

## Config Schema

`.harness/config.json` must preserve these top-level blocks:

```json
{
  "project": "my-project",
  "stack": ["example"],
  "test": { "command": "", "strategy": "" },
  "build": { "command": "", "typecheck_command": "" },
  "lint": { "command": "" },
  "security": { "sast_command": "", "dependency_audit_command": "" },
  "quality": { "duplication_command": "", "mutation_command": "" },
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
  "app_delivery": {
    "surface_kind": "web",
    "frontend": {
      "present": true,
      "framework": "",
      "routes": "",
      "design_system": "",
      "view_extensions": [],
      "viewport_matrix": ["mobile", "desktop"],
      "accessibility_baseline": "keyboard navigation and semantic labels",
      "design_readiness_required": true,
      "design_artifact": "docs/ux/frontend-design.md",
      "token_source": "",
      "component_inventory": "",
      "visual_qa": "",
      "mock_prototype_artifacts": "",
      "visual_baseline": ""
    },
    "backend": {
      "present": false,
      "api_style": "",
      "auth_session": "",
      "persistence": "",
      "background_jobs": "",
      "external_services": []
    },
    "packaging": {
      "artifact": "static_site",
      "build_output": "",
      "installer_or_image": ""
    },
    "deployment": {
      "target": "local",
      "provider": "",
      "preview_default": true,
      "required_env": [],
      "rollback": "revert commit or redeploy previous artifact"
    },
    "qa": {
      "browser_or_e2e": "",
      "visual_regression": "",
      "release_checklist": []
    }
  },
  "ui_verification": {
    "required": true,
    "capability": "browser-e2e",
    "adapter": "",
    "command": "",
    "oracle": "",
    "fallback_adapter": "",
    "evidence": []
  },
  "server": {
    "start_command": "",
    "stop_command": "",
    "health_check_url": "",
    "health_check_timeout": 15
  },
  "architecture": {
    "lifecycle_stage": "undecided",
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
    "codex_reviewer_model": "",
    "model_routing": {
      "enabled": false,
      "default_profile": "balanced",
      "fail_on_unresolved": false,
      "availability_cache": ".harness/model-availability.json",
      "profiles": {}
    }
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

## App Delivery Profile

Follow `docs/reference/app-delivery-contract.md` when populating
`app_delivery`. Infer values from manifests, source roots, framework files,
routes, CI/deploy files, package scripts, and existing docs before asking.
Present inferred frontend view extensions, deployment target, and packaging
artifact to the user for confirmation when they affect verification.

## Frontend Design Readiness

Follow `docs/reference/frontend-design-contract.md` when UI is present. Setup
creates the `docs/ux/frontend-design.md` slot and records readiness fields in
config, but it must not synthesize the design brief. `/design-architecture`
owns invoking `frontend-design` and filling the artifact after repo evidence
and user direction are known.

## Smoke Rules

Executable artifacts (`cli`, `server`, `desktop`) require `smoke.required:
true` and a non-empty `smoke.command`.

Only `docs` and `library` may set `smoke.required: false`.

`smoke.command` must launch or probe the real artifact entry point. It must not
be the same command as build, typecheck, lint, or test verification.

GUI strategy defaults:

- Avalonia, WPF, WinForms, Qt, GTK: `process_probe`.
- Electron, Tauri: `headless`.
- Console/server: `skip`, but still require a non-empty smoke command.
- Docs/library: `skip` only when runtime smoke is explicitly not required.

Desktop smoke output must write `desktop_evidence` to `runtime-probe.json` or
`smoke-output.json`: window found or a nonzero window handle, screenshot path,
pixel variance, and UI text, automation name, or API observation. Desktop
features that use a configured server or API must include API observation.

Client surfaces (`web`, `mobile`, `desktop`, or GUI) that use a configured
server/API must write `client_server_evidence.api_observation` to
`runtime-probe.json` or `smoke-output.json`. For desktop clients,
`desktop_evidence.api_observation` is accepted for backward compatibility.

Fail setup/doctor validation if the smoke command is the same as the build or
test command.

## Wiring Rules

Projects with UI presence require `wiring.enabled: true` and a non-empty
`wiring.view_extensions` array. Auto-detect view extensions from the tech
stack. `wiring.view_test_command` and `wiring.wiring_gate_command` may be
empty at setup time — per-task and per-plan commands serve as fallbacks.

Validation rules for wiring config are defined in
`docs/reference/verification-contract.md` § Wiring Config Validation.
Auto-fill `wiring.exempt_reason` for docs/library artifacts
(e.g., `"pure library, no UI components"`).

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

## Local Harness Kit

Install the versioned local kit from `harness-kit/v2.0.0/manifest.json` into
`.harness/ezpowers/`. Setup must copy bundled files only, compute SHA-256 before
and after install, and write `.harness/ezpowers/ledger.json`. The same manifest
must also install the approved deterministic helper scripts into the target
project `scripts/` directory so `/choice-execute` can run mechanical gates.

Do not synthesize `SKILL.md` or contract bodies during setup. Missing bundled
files are setup failures, not prompts to improvise replacements.

## UI Verification

Populate `ui_verification` from
`docs/reference/ui-verification-adapter-contract.md`. UI projects require a
selected capability and an adapter plan. If no adapter can run yet, setup may
leave `command` empty only when `/prepare-execute` will add a prerequisite
adapter-install task before feature work.

## Phase Index

Final setup state:

```json
{
  "current_phase": "setup",
  "phases": {
    "setup": { "status": "complete", "completed_at": "2026-05-13T00:00:00Z" },
    "architecture": { "status": "pending", "artifact": null },
    "spec": { "status": "pending", "artifact": null },
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

`/setup --enable-traces` creates or reuses project-local `hooks/hooks.json`
from `docs/reference/trace-hooks-template.json`, creates the plugin data trace
directory, and ignores `*.ezpowers-traces/`. Codex plugin bundles must not ship
an active root `hooks/hooks.json`; Codex activates plugin hook files during
tool use.

The two flags are independent.

## Completion Report

Report:

- Created or updated files.
- Config values inferred from repo evidence.
- Config values supplied by the user.
- App delivery profile values and unresolved deployment or packaging inputs.
- Frontend design readiness artifact path, token source, component inventory,
  visual QA strategy, and unresolved design inputs.
- Local kit version and hash ledger path.
- UI verification capability, selected adapter, fallback adapter, and unresolved
  adapter setup task if any.
- Remaining human-authored docs.
- Smoke command and GUI strategy.
- Next command: `/design-architecture`.
