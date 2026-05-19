---
description: Cross-stage completeness gate — verify document traceability, spec depth, and execution readiness
allowed-tools: [Bash, Read, Write]
---

# /pipeline-audit — Cross-Stage Completeness Gate

Source contract: `docs/reference/app-delivery-contract.md` defines mandatory D9 App Delivery Readiness; include D9 whenever its trigger applies.

Verify that spec and plan documents are complete, traceable, and executable before proceeding to the next pipeline stage. This command checks the **seams between documents** — gaps that individual reviewers (spec-reviewer, plan-reviewer) cannot detect because they only inspect one document at a time.

<HARD-GATE>
Pipeline-audit is a mandatory gate. /plan and /choiceexecutor will not proceed without a passing audit.
</HARD-GATE>

## Pipeline Position

```
/brainstorm → /pipeline-audit → /plan → /pipeline-audit → /choiceexecutor
                D2 + D6L1 + D7 + D9    D1-D9 full audit
```

## 1. Detect Pipeline State

Read project state to determine which dimensions to run:

1. Read `phases/index.json` for phase statuses and artifact paths
2. Read `.harness/config.json` for project configuration
3. Collect spec documents:
   - **Plan exists:** parse plan header `**Spec:**` field and Coverage Matrix to reverse-lookup all referenced specs
   - **No plan (spec-only):** collect all `YYYY-MM-DD-*-design.md` files from config `defaults.spec_location` (default: `docs/specs/`)
4. Classify state:

| State | Condition | Dimensions |
|-------|-----------|-----------|
| **spec-only** | Spec(s) exist, no plan | D2 + D6 Layer 1 + D7 + D9 when triggered |
| **spec+plan** | Both exist | D1-D9 all, with D9 skipped only when not triggered |
| **mid-build** | Build phase `in_progress` | D1-D9, completed tasks → INFO severity |
| **no-documents** | Neither spec nor plan | Error: "No spec or plan found. Run /brainstorm first." → stop |

For `mid-build`, include D7, D8, and D9 in addition to the listed dimensions.
D9 is triggered when `config.app_delivery.surface_kind` is not `docs` or
`library`, or when the spec/plan declares an App Experience And Delivery
Baseline.

5. Report state to user:

> **Pipeline Audit**
> - State: [spec-only | spec+plan | mid-build]
> - Spec(s): [paths]
> - Plan: [path or N/A]
> - Dimensions: [list]

## 2. Run Audit Dimensions

### D1: Traceability Chain (spec+plan required)

Purpose: Every spec AC bullet must have a corresponding plan completion criteria entry.

**Checks:**
1. Parse each spec's `## Extracted Requirements` to list R1..Rn
2. Parse each R's Acceptance criteria bullets (each `- [ ] Given:...` or `- [ ] Input:...` block)
3. Parse plan's `## Coverage Matrix` to get R → T mappings
4. For each mapped T, parse `**Completion criteria (from spec):**` entries
5. For each spec AC bullet, find a matching plan completion criteria entry
   - Match by: R-tag (e.g., `(R2)`) AND Given/When/Then text similarity (substring match of When + Then clauses)
6. Verdicts:
   - **FAIL**: AC bullet has no matching completion criteria
     → `"R2 AC-3 (Given: [condition] / When: [action] / Then: [result]) — no completion criteria in T1 or T4"`
   - **WARN**: Verify command text differs between spec and plan
     → `"R1 AC-2: Verify command text drift — spec: 'curl ...' vs plan: 'wget ...'"`

### D2: Verify Executability (spec required)

Purpose: Pre-check that Verify commands can run in the project environment.

**Checks:**
1. Extract all Verify commands from spec AC bullets
2. **Tool availability:** extract first command token (e.g., `curl`, `pytest`, `playwright`). Run `command -v <token>` to check existence.
   → **WARN** if not found: `"R1 AC-1: Verify uses 'playwright' — not found in PATH"`
3. **Port/URL plausibility** (Verify-type api or e2e): if Verify references `localhost:NNNN`, cross-check against `config.server.health_check_url` port.
   → **WARN** on port mismatch: `"R2 AC-1: Verify uses port 3000, config.server uses port 8080"`
4. **Path references:** if Verify references file paths (test files, scripts), check they exist on disk OR appear in the plan's Create list.
   → **FAIL** if neither: `"R3 AC-2: Verify references tests/login.spec.ts — file does not exist and not in any task's Create list"`
5. **Server dependency** (Verify-type api or e2e): check `config.server.start_command` is non-empty.
   → **WARN** if empty: `"R2 AC-1: Verify-type api but config.server.start_command is empty"`

6. **Tool version validation:** after `command -v` confirms a tool exists, run
   `<tool> --version` and compare against version constraints in project
   manifests (`package.json` engines, `.python-version`, `.nvmrc`,
   `pyproject.toml` requires-python). → **WARN** on version mismatch.
7. **Environment variable dependency:** scan Verify commands and spec text for
   `$VAR` or `${VAR}` patterns. For each found variable, check whether it is
   set in the current environment.
   → **FAIL** if unset and referenced in a Verify command (blocks execution):
   `"R1 AC-2: Verify references $DATABASE_URL — not set in environment"`
   → **WARN** if unset and referenced only in spec text (not in Verify).
8. **Service port availability** (Verify-type api or e2e): if Verify
   references `localhost:NNNN` beyond the config port check (#3), verify the
   port is not already occupied by another process. → **INFO**: advisory only,
   service may start at execution time.
9. **Dependency resolution** (spec+plan required):
   - Scan Verify commands and spec/plan text for import/require/use statements referencing external packages
   - Cross-reference with project manifest files (`package.json`, `requirements.txt`, `Pipfile`, `Cargo.toml`, `go.mod`, etc.)
   - For packages referenced in Verify commands but NOT in manifest:
     → **WARN**: `"Verify command references '{package}' but it is not declared in {manifest}. Add to dependencies or verify it's a built-in."`
   - For packages in manifest that are newly added (not in current lockfile):
     → **INFO**: `"New dependency '{package}' will be installed. Verify it exists in the registry."`
   - If no manifest file found and Verify commands reference external tools:
     → **WARN**: `"No package manifest found. External tool dependencies may not be available at execution time."`
10. **Executable runtime smoke**: if the plan or config identifies an executable
   artifact (`cli`, `server`, or `desktop`), `config.smoke.required` must be
   true and `config.smoke.command` must be non-empty.
   -> **FAIL** if missing: `"Executable artifact has no required runtime smoke command"`
11. **Desktop GUI smoke**: if `config.smoke.artifact_kind == "desktop"`,
   `config.smoke.gui_strategy` must not be `skip`, and the probe must produce
   a screenshot artifact.
   -> **FAIL** if weak: `"Desktop artifact cannot skip GUI runtime probe"`
12. **Quality Budget verify_command**: extract `verify_command` fields from
   spec's Architecture Baseline → Quality Budgets section. For each non-empty
   command, run `command -v <first-token>` to check tool availability. Scan
   for `$VAR`/`${VAR}` references and verify env vars are set. Scan for file
   path arguments and verify they exist or appear in a plan Create list.
   → **WARN** if tool not found: `"Quality Budget '{category}' verify_command uses '{tool}' — not found in PATH. Budget measurement will fail at execution."`
   → **WARN** if env var unset: `"Quality Budget '{category}' verify_command references ${VAR} — not set in environment."`
   → No `verify_command` fields → skip.

### D3: Semantic Granularity (spec+plan required)

Purpose: Catch silent AC drops — task "covers" an R but skips some of its AC bullets.

**Checks:**
1. For each R in the Coverage Matrix, count AC bullets in the spec
2. For each mapped T, count completion criteria entries tagged with that R (by `(RN)` prefix)
3. If spec AC count > plan criteria count for that R:
   → **FAIL**: `"R1 has 5 ACs in spec but T1 only addresses 3. Missing: AC-2 (When: bulk import / Then: progress bar), AC-4 (When: cancel / Then: rollback)"`
4. If counts match but Then clause text differs substantively:
   → **WARN** with the diff

### D4: File Mutation Consistency (plan required)

Purpose: Detect file-level conflicts and ordering issues within the plan.

**Checks:**
1. Parse every task's `**Files:**` section to build a mutation map: `{path → [{task, action: Create|Modify|Test}]}`
2. **Create-after-Modify conflict:** file is `Modify` in an earlier task and `Create` in a later task, with no dependency between them.
   → **FAIL**: `"src/foo.ts is Modify in T1 but Create in T3 — Create should precede Modify"`
3. **Create-Create conflict:** same file appears as `Create` in two different tasks.
   → **FAIL**: `"src/foo.ts is Create in both T1 and T3"`
4. **Modify without existence:** file is `Modify` in a task but does not exist on disk AND is not `Create` in any preceding task (considering dependencies).
   → **FAIL**: `"T2 modifies src/bar.ts but this file does not exist and no preceding task creates it"`
5. **Shared file without dependency marker:** two tasks modify the same file but neither has `**File overlap with:**` or `**Depends on:**` markers connecting them.
   → **WARN**: `"T2 and T5 both modify src/config.ts but have no dependency relationship"`
6. **Dependency manifest consistency:** if a task creates or modifies source files that contain import/require/use statements for packages not already in the project manifest, but no task in the plan modifies the manifest file (`package.json`, `requirements.txt`, etc.):
   → **WARN**: `"T{n} imports '{package}' but no task modifies {manifest_file}. Dependency may not be installed."`

### D5: Integration Readiness (plan required)

Purpose: Verify that integration milestone tasks actually test the full pipeline.

**Checks:**
1. Find integration/milestone tasks: tasks listed in `## Integration Pipeline Matrix`, or tasks whose title contains "integration", "milestone", or "wiring"
2. **Unit test as milestone Verify:** milestone's Verify command matches a single-file test pattern (e.g., `pytest tests/test_one.py::test_specific`).
   → **WARN**: `"T8 milestone Verify runs a unit test, not an integration test"`
3. **Partial pipeline coverage:** milestone's Then clause mentions only the last component of the pipeline (e.g., "Renderer output" but pipeline is PTY→Parser→Buffer→Renderer).
   → **WARN**: `"T8 Then clause mentions only Renderer output but pipeline is PTY→Parser→Buffer→Renderer"`
4. **Pipeline without milestone:** Integration Pipeline Matrix lists pipeline P but no corresponding milestone task exists.
   → **FAIL**: `"Pipeline P1 (PTY→Parser→Buffer→Renderer) has no milestone task"`
5. **Full-feature wiring gate missing:** if a pipeline, milestone, or wiring task exists, the plan must contain `## Full-Feature Wiring Gate`.
   → **FAIL**: `"Pipeline P1 has no Full-Feature Wiring Gate"`
6. **Weak wiring gate Verify:** gate Verify is empty, placeholder-only, `echo`, `true`, `:`, or a unit-only command for one component.
   → **FAIL**: `"Full-Feature Wiring Gate does not exercise the full feature"`
7. **Missing runtime evidence for executable gates:** executable or desktop
   wiring gates must mention `runtime-probe.json`, `smoke-output.json`, or an
   equivalent runtime probe artifact; desktop gates must include screenshot
   evidence.
   -> **FAIL**: `"Full-Feature Wiring Gate lacks runtime artifact evidence"`
8. **Data flow path coverage:** for each WM-DF entry in the spec, check whether
   at least one task's Verify command, a milestone task, or the Full-Feature
   Wiring Gate exercises that data flow path (entry → transformations → exit).
   → **FAIL** for executable artifacts (`cli`/`server`/`desktop`) if a WM-DF
   has no corresponding verification:
   `"WM-DF1 (CLI args → CommandHandler → stdout) has no task or gate Verify exercising this path"`
   → **WARN** for `library` artifacts.
9. **Wiring Probe coverage:** for executable artifacts, every task that creates
   a new module must have a `**Wiring probe:**` section with a non-trivial
   Verify command and a probe type matching the corresponding WM-REG entry's
   recommended strategy.
   → **FAIL** if task creates a new module but has no Wiring Probe:
   `"Task N creates [module] but has no Wiring Probe. Add **Wiring probe:** with entry point, module path, probe type, and Verify command."`
   → **WARN** if probe type does not match WM-REG recommended strategy:
   `"Task N Wiring Probe uses import-chain but WM-REG1 recommends runtime-load"`
10. **No pipelines detected:** if plan has no Integration Pipeline Matrix and no tasks with integration/milestone/wiring keywords:
   - If `config.wiring.enabled: true` and plan has 2+ tasks with file dependencies (`Depends on` or shared `Modify` files) → **WARN**: `"No Integration Pipeline Matrix but task dependencies exist. Consider adding integration verification."`
   - If `config.wiring.enabled: false` with valid `exempt_reason`, or plan has truly independent single-file tasks → **PASS**
   - If `config.wiring` block missing → **FAIL**: `"config.json has no wiring block. Run /setup to regenerate."`
11. **ICM completeness (plan required):** for each pair of tasks where one has
   `Depends on` or `File overlap with` the other, check whether at least one
   Integration Contract Matrix row names both tasks as Producer and Consumer
   (or vice versa). Skip pairs where both tasks only share test files.
   → **WARN** if dependent tasks have no ICM row:
   `"T{a} depends on T{b} but no Integration Contract Matrix row links them. Implicit runtime contract may be unverified at execution."`

### D6: Step Specification Sufficiency (spec or plan required)

Purpose: Detect tasks/steps that lack verifiable specification — the "구현한다" problem. A task that can't be meaningfully verified should not proceed to execution.

> **Background (EZTerminal Phase 1a):** step2/step3 had "implement system monitor" without concrete AC. System marked them complete based on "build passes, tests pass" but actual functionality was broken — panel created with "추후 지원" placeholder.

#### Layer 1 — Spec Depth Check (runs at post-brainstorm audit)

Each R section's content must be sufficient to produce meaningful verification at execution time.

**3 Measurable Signals:**

1. **Behavior field specificity**
   - **FAIL**: Behavior is 1 sentence or less AND contains only a broad verb (구현한다/표시한다/처리한다/생성한다/관리한다 / implement/display/handle/create/manage) with no step-by-step detail
   - **PASS**: Step-by-step description OR specific data/behavior mentioned
   - Example FAIL: `"시스템 정보를 표시한다"` — single sentence, broad verb, no detail
   - Example PASS: `"1) CPU 사용률을 1초 간격으로 폴링한다 2) 메모리 사용량을 MB 단위로 표시한다"` — multi-step, specific data

2. **AC Then clause observability**
   - **FAIL**: Then clause matches vague patterns: "정상 동작한다", "올바르게 표시된다", "기능이 작동한다", "works properly", "displays correctly", "functions as expected"
   - **PASS**: Then clause describes a concrete observable result
   - Example FAIL: `"Then: 시스템 모니터가 정상 동작한다"`
   - Example PASS: `"Then: CPU 사용률이 0-100% 범위의 숫자로 표시되고 1초마다 갱신된다"`

3. **Verify command feature-specificity**
   - **FAIL**: Verify is a full test suite invocation without specific filter (`dotnet test`, `npm test`, `pytest`, `cargo test`, `go test ./...`) AND the R has specific behavioral claims (concrete Given/When/Then with observable values, not structural requirements like "project builds").
   - **WARN**: Verify is a broad suite but the R is a general structural requirement (e.g., "project compiles", "no lint errors").
   - **PASS**: Verify targets a specific test or feature: `dotnet test --filter SystemMonitor`, `pytest tests/test_monitor.py`

#### Layer 2 — Plan Task Check (runs at post-plan audit)

Each task's completion criteria must be specific enough for meaningful verification.

**Sub-gates:**

1. **AC Presence Gate**: task has a `**Completion criteria (from spec):**` section with at least one Given/When/Then entry.
   → **FAIL** if empty or absent: `"T3 has no completion criteria"`

2. **AC Specificity Gate**: each Given/When/Then is concrete.
   → **WARN**: Then contains vague patterns ("works properly", "정상적으로", "as expected")
   → **WARN**: When is a category, not an action ("feature is used" vs "user clicks submit button")
   → **WARN**: Given is universal ("any state", "system is running") — with no specific precondition

3. **Verify Completeness Gate**: every AC has a non-trivial Verify command.
   → **FAIL**: Verify is trivial (`echo`+`exit 0`, `true`, `:`, or missing entirely)
   → **FAIL**: Verify is generic fallback only ("Run tests and verify", "Check manually")

4. **E2E Automatable Gate**: AC with Verify-type `e2e` or `api` has `Automatable: true` (or explicit automated probe replacement in task steps).
   → **FAIL**: `"T5 AC-1: Verify-type e2e with Automatable: false and no probe replacement in task steps"`

5. **Milestone Verification Gate**: integration milestone tasks verify actual functionality, not just process survival.
   → **WARN**: Verify pattern is survival-only (`timeout N <cmd>`, "process survived N seconds") without functional output assertion

### D7: Architecture Readiness (spec required)

Purpose: Catch architecture gaps before `/plan` turns them into implementation
tasks.

**Checks:**
1. Required sections: spec contains Architecture Baseline, ASR Ledger, Option
   Matrix, Lifecycle And Operations, Quality Budgets, and Decision Log.
   - **FAIL** when any section is missing.
2. R-to-ASR linkage: every R has an `ASR:` field and every referenced ASR
   exists in the ASR Ledger.
   - **FAIL** when an R lacks ASR linkage or references an unknown ASR.
3. Option tradeoffs: Option Matrix has at least two options and exactly one
   selected option.
   - **FAIL** when the selected architecture cannot be identified.
4. Lifecycle coverage: startup/shutdown, deployment/runtime,
   migration/compatibility, observability, recovery, and ownership are present.
   - **WARN** when a field is `none declared`.
   - **FAIL** when a field is missing.
5. Quality budgets: performance, reliability, security, cost, and
   maintainability each have a metric, rule, or `none declared` plus risk.
   - **WARN** for `none declared` plus risk.
   - **FAIL** for empty values.
6. ADR traceability: `ADR required: yes` must reference ADR files under
   `docs/decisions/`; each referenced file must exist.
   - **FAIL** when required ADRs are absent.
7. Post-plan carry-forward: when a plan exists, ASR IDs from spec must appear
   in Coverage Matrix rows, task `**ASR:**` fields, or Structural Invariants.
   - If `phases/index.json` records `plan.review.plan` as `"PASS"`, inherit
     PASS for this check (plan-reviewer check 1A already validated).
   - Otherwise, execute the check directly.
   - **FAIL** when an ASR has no plan task or invariant.
8. Wiring Map (executable artifacts only): if `config.smoke.artifact_kind` is
   `cli`, `server`, or `desktop`, spec must contain a Wiring Map table with at
   least one WM-EP entry, one WM-REG or WM-DF entry, and one WM-C entry.
   - **FAIL** when Wiring Map is missing or incomplete for executable artifacts.
9. Initialization Order (executable artifacts with 2+ modules): if the spec
   references database connections, service registrations, queue subscriptions,
   startup hooks, config loaders, plugin systems, cache warmups, or auth
   bootstraps, an Initialization Order section should exist in the
   Architecture Baseline listing module → prerequisite → readiness signal.
   - **FAIL** when absent for executable artifacts (`cli`/`server`/`desktop`)
     with runtime dependencies.
   - **WARN** when absent for `library` artifacts with startup dependencies.

### D8: Sensor Completeness (plan required)

Purpose: Verify that expected verification layers are configured and plan-aligned. Meta-verification — checks the verification pipeline itself.

1-3. **Wiring config validation:** Apply `docs/reference/verification-contract.md` § Wiring Config Validation (fail-closed). Covers: wiring block presence, exemption validity, view extension coverage.
4. **Expected sensor count:** Report expected verification layers:
   - L1 (AC verification): always expected. Count = task count.
   - L2 (View Wiring Test): expected if `wiring.enabled: true`, `wiring.view_extensions` is non-empty, and any task creates/modifies view files. Count = view-touching task count.
   - L3 (Wiring Gate): expected if plan has `## Full-Feature Wiring Gate` with `Required: yes`. Count = 1.
   - L4 (Runtime Smoke): expected if `config.smoke.required: true`. Count = 1.
   → Report: `"Expected sensors: L1=N, L2=M, L3=P, L4=Q"`
5. **L2 sensor-plan alignment:** For each expected L2 sensor, the corresponding task must have a `**View wiring verification**` section.
   → **FAIL**: `"T3 modifies view files but has no View wiring verification section. Expected L2 sensor missing."`
6. **L3 sensor-plan alignment:** If L3 expected, `## Full-Feature Wiring Gate` must have a non-trivial Verify command (not echo/true/:/placeholder).
   → **FAIL**: `"Expected L3 sensor (wiring gate) has no executable command."`

### D9: App Delivery Readiness (triggered by app surface)

Purpose: Verify that frontend, backend, packaging, deployment, and release
surfaces are represented in the spec/plan when the project is an app or when an
App Experience And Delivery Baseline is declared.

Source of truth: `docs/reference/app-delivery-contract.md` section
`## D9: App Delivery Readiness`.

**Trigger:**
- Run D9 when `config.app_delivery.surface_kind` is not `docs` or `library`.
- Run D9 when any spec or plan contains `App Experience And Delivery Baseline`.
- Otherwise report D9 as `SKIP` with reason `non-app surface`.

**Spec-only checks:**
1. UI feature lacks App Experience And Delivery Baseline, UX flow map,
   frontend contract, or browser/e2e/visual Verify command → **FAIL**.
2. API/server feature lacks backend contract, auth/session decision when
   applicable, error shape, or API Verify command → **FAIL**.
3. Packaging or deployment is `none declared` for an executable app → **WARN**.
4. Deployment is in scope but required env vars, preview/staging target,
   readiness signal, or rollback rule is missing → **FAIL**.

**Spec+plan checks:**
1. Spec has App Experience And Delivery Baseline but the plan lacks an
   Experience/Delivery Matrix → **FAIL**.
2. Any Experience/Delivery Matrix row has no mapped task or no non-trivial
   Verify command → **FAIL**.
3. UI tasks lack viewport/e2e or visual verification → **FAIL**.
4. Package/deploy tasks lack build artifact, readiness, or rollback
   verification → **FAIL**.
5. Visual or accessibility verification is advisory-only → **WARN** and record
   the accepted risk.

## 3. Output Report

```
## Pipeline Audit Report

**Spec(s):** [paths, comma-separated]
**Plan:** [path or N/A]
**Audit point:** post-brainstorm | post-plan
**Date:** [ISO 8601]

### D1: Traceability Chain — PASS | WARN | FAIL
- [R/AC/T-level findings]

### D2: Verify Executability — PASS | WARN | FAIL
- [tool/port/path findings per Verify command]

### D3: Semantic Granularity — PASS | WARN | FAIL
- [AC count mismatches per R]

### D4: File Mutation Consistency — PASS | WARN | FAIL
- [file conflict findings per path]

### D5: Integration Readiness — PASS | WARN | FAIL
- [milestone/pipeline findings]

### D6: Step Specification Sufficiency — PASS | WARN | FAIL
#### Layer 1 — Spec Depth
- [per-R signal findings grouped by spec file]
#### Layer 2 — Plan Task (post-plan only)
- [per-task sub-gate findings]

### D7: Architecture Readiness — PASS | WARN | FAIL
- [architecture section, ASR, lifecycle, budget, ADR, and carry-forward findings]

### D8: Sensor Completeness — PASS | WARN | FAIL
- [wiring config, sensor count, sensor-plan alignment findings]

### D9: App Delivery Readiness — PASS | WARN | FAIL | SKIP
- [frontend, backend, packaging, deployment, and release findings]

---

## Overall: PASS | WARN | FAIL
- FAIL: N dimensions
- WARN: N dimensions
- PASS: N dimensions
- SKIP: N dimensions

## Routing Recommendations

### Return to /setup (config gaps)
- [D8: missing wiring block, invalid exemption]
- [D9: missing or wrong app_delivery surface profile]

### Return to /brainstorm (spec-level gaps)
- [specific R/AC references with reason]
- [D9: missing App Experience And Delivery Baseline or surface decisions]

### Return to /plan (plan-level gaps)
- [specific T/AC references with reason, D8 missing View wiring sections]
- [D9: missing Experience/Delivery Matrix rows or delivery Verify commands]

### Proceed to [/plan | /choiceexecutor]
- [conditions met, or all gaps are WARN-level only]
```

**Verdict aggregation rules:**
- Any dimension FAIL → Overall **FAIL** (block next stage)
- No FAIL + any WARN → Overall **WARN** (proceed with caution)
- All PASS → Overall **PASS**
- SKIP dimensions do not count as PASS; they must include a reason.

## 4. Write Verdict

After generating the report, record the verdict in `phases/index.json`:

```json
{
  "audit": {
    "status": "PASS | WARN | FAIL",
    "timestamp": "<ISO 8601>",
    "audit_point": "post-brainstorm | post-plan",
    "spec_artifacts": ["docs/specs/..."],
    "plan_artifact": "docs/plans/..." ,
    "fail_count": 0,
    "warn_count": 0,
    "summary": "D3: 2 FAIL, D6: 1 FAIL"
  }
}
```

This field is read by `/plan` and `/choiceexecutor` pre-flight checks. FAIL or missing field = next stage blocked.

## 5. Route Recommendations

Each finding maps to a specific routing action:

| Finding Category | Route To | Action |
|-----------------|----------|--------|
| D6 L1: Behavior too vague | /brainstorm | Refine R with step-by-step behavior |
| D6 L1: Then not observable | /brainstorm | Rewrite Then with concrete result |
| D6 L1: Verify not specific | /brainstorm | Add feature-specific test filter |
| D2: Tool not in PATH | User decision | Install tool or rewrite Verify |
| D2: Port mismatch | /brainstorm or config | Align Verify port with server config |
| D2: File path missing | /brainstorm or /plan | Create test file or fix path |
| D1: AC not in plan | /plan | Add completion criteria to task |
| D3: AC count mismatch | /plan | Add missing AC bullets to task |
| D4: File ordering conflict | /plan | Add Depends on or reorder tasks |
| D5: Missing milestone | /plan | Add integration milestone task |
| D6 L2: No completion criteria | /plan | Add Given/When/Then from spec |
| D6 L2: Trivial Verify | /plan or /brainstorm | Write real verification command |
| D6 L2: E2E not automatable | /plan | Add automated probe replacement |
| D7: Missing architecture section | /brainstorm | Add architecture baseline sections |
| D7: R has no ASR linkage | /brainstorm | Add `ASR:` field to R section |
| D7: ASR not carried to plan | /plan | Map ASR to task or Structural Invariant |
| D7: ADR missing | /brainstorm | Create ADR and link it from Decision Log |
| D9: Missing app_delivery profile | /setup | Regenerate or update app_delivery config |
| D9: Missing App Experience And Delivery Baseline | /brainstorm | Add frontend/backend/package/deploy baseline |
| D9: Missing Experience/Delivery Matrix | /plan | Add matrix rows with mapped tasks and Verify commands |
| D2: Undeclared dependency | /brainstorm or /plan | Add dependency to manifest or verify built-in |
| D4: Missing manifest update | /plan | Add manifest modification step to task |

Present routing grouped by target command:

```
### Return to /brainstorm
- spec2 R1: Behavior is "시스템 모니터를 구현한다" (1 sentence + broad verb)
  → Add step-by-step behavior (polling interval, data sources, display format)
- spec2 R1 AC-1: Then is "정상 동작한다" (not observable)
  → Rewrite: "CPU 사용률이 0-100% 숫자로 1초마다 갱신된다"

### Return to /plan
- T3: No completion criteria
  → Copy Given/When/Then from spec2 R1 AC-1 through AC-3
- T5 AC-1: Verify-type e2e with Automatable: false
  → Add automated probe (headless test or process+screenshot)
```

## Bilingual Support

- Parse both `## Extracted Requirements` and `## 추출된 요구사항`
- Match both `Given:`/`When:`/`Then:` and `주어진:`/`할 때:`/`그러면:`
- D6 L1 broad verb detection covers both Korean (구현한다/표시한다/처리한다/생성한다/관리한다) and English (implement/display/handle/create/manage)
- D6 L1 vague Then detection covers both Korean (정상 동작한다/올바르게 표시된다/기능이 작동한다) and English (works properly/displays correctly/functions as expected)
- Output report in the predominant language of the spec (detected by script majority in Extracted Requirements section)

## Common Rationalizations

| Excuse | Reality |
|--------|---------|
| "Plan reviewer already checked" | Plan reviewer checks R→T mapping exists. Pipeline-audit checks AC→step granularity. |
| "Verify will work at runtime" | EZTerminal: 40% of runtime failures were missing tools or wrong ports. Pre-check costs seconds, debugging costs hours. |
| "Coverage Matrix covers everything" | Matrix is R-level. Gaps are AC-level. R1 "covered" by T1 but 2 of 5 ACs silently dropped. |
| "Files will sort themselves out" | Create/Modify ordering bugs are silent until execution — then they cascade. |
| "Build passes so it works" | EZTerminal Phase 1a: 106 unit tests PASS, 12 verify scripts PASS, app completely broken. |
| "Simple enough, no detailed spec needed" | EZTerminal: "simple" step2/step3 became empty placeholder panels marked as complete. |
| "Process survived = functional" | Process not crashing ≠ process doing its job. Survival without functional assertion is meaningless. |
| "Spec reviewer already caught vague terms" | Spec reviewer catches banned expressions. D6 L1 catches borderline cases that pass structural gates but lack semantic depth. |
