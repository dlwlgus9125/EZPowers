---
description: Cross-stage completeness gate — verify document traceability, spec depth, and execution readiness
disable-model-invocation: true
allowed-tools: [Bash, Read, Write]
---

# /pipeline-audit — Cross-Stage Completeness Gate

Verify that spec and plan documents are complete, traceable, and executable before proceeding to the next pipeline stage. This command checks the **seams between documents** — gaps that individual reviewers (spec-reviewer, plan-reviewer) cannot detect because they only inspect one document at a time.

<HARD-GATE>
Pipeline-audit is a mandatory gate. /plan and /choiceexecutor will not proceed without a passing audit.
</HARD-GATE>

## Pipeline Position

```
/brainstorm → /pipeline-audit → /plan → /pipeline-audit → /choiceexecutor
                D2 + D6L1 + D7         D1-D7 full audit
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
| **spec-only** | Spec(s) exist, no plan | D2 + D6 Layer 1 + D7 |
| **spec+plan** | Both exist | D1-D7 all |
| **mid-build** | Build phase `in_progress` | D1-D6, completed tasks → INFO severity |
| **no-documents** | Neither spec nor plan | Error: "No spec or plan found. Run /brainstorm first." → stop |

For `mid-build`, include D7 in addition to the listed dimensions.

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
5. **No pipelines detected:** if plan has no Integration Pipeline Matrix and no tasks with integration/milestone keywords:
   → **SKIP**

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
   - **WARN**: Verify is a full test suite invocation without specific filter: `dotnet test`, `npm test`, `pytest`, `cargo test`, `go test ./...`
   - **PASS**: Verify targets a specific test or feature: `dotnet test --filter SystemMonitor`, `pytest tests/test_monitor.py`
   - This is WARN (not FAIL) because a broad test suite may still catch issues, but a targeted test is stronger evidence.

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
   - **FAIL** when an ASR has no plan task or invariant.

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

### D5: Integration Readiness — PASS | WARN | FAIL | SKIP
- [milestone/pipeline findings or "No pipelines detected"]

### D6: Step Specification Sufficiency — PASS | WARN | FAIL
#### Layer 1 — Spec Depth
- [per-R signal findings grouped by spec file]
#### Layer 2 — Plan Task (post-plan only)
- [per-task sub-gate findings]

### D7: Architecture Readiness ??PASS | WARN | FAIL
- [architecture section, ASR, lifecycle, budget, ADR, and carry-forward findings]

---

## Overall: PASS | WARN | FAIL
- FAIL: N dimensions
- WARN: N dimensions
- PASS: N dimensions
- SKIP: N dimensions

## Routing Recommendations

### Return to /brainstorm (spec-level gaps)
- [specific R/AC references with reason]

### Return to /plan (plan-level gaps)
- [specific T/AC references with reason]

### Proceed to [/plan | /choiceexecutor]
- [conditions met, or all gaps are WARN-level only]
```

**Verdict aggregation rules:**
- Any dimension FAIL → Overall **FAIL** (block next stage)
- No FAIL + any WARN → Overall **WARN** (proceed with caution)
- All PASS/SKIP → Overall **PASS**

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
