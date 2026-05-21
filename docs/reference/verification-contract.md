# Verification Contract

This document is the canonical contract for EZPowers acceptance criteria,
Verify commands, runtime probes, integration evidence, and wiring gates.
Commands and agents may add local procedure details, but must not weaken this
contract.

## Acceptance Criteria Interface

Every behavior-bearing requirement must expose an acceptance criterion with:

- `Given`: observable precondition or state before the action.
- `When`: user or system action, not an implementation call.
- `Then`: concrete observable result.
- `Verify`: automated command where exit 0 means pass.
- `Verify-type`: one of `pure`, `cli`, `lib`, `api`, `e2e`, or `data`.

For `pure` criteria, `Input`, `Transform`, and `Output` may replace
Given/When/Then when the behavior has no side effects.

Given/When/Then text must describe observable behavior and must not depend on
function names, class names, internal variables, or private file structure.

## Verify-Type Evidence

| Verify-type | Required evidence |
| --- | --- |
| `pure` | Deterministic transform assertion with no external side effects. |
| `cli` | CLI invocation or script command that checks stdout, stderr, exit code, generated file, or other observable CLI result. |
| `lib` | Consumer-level script or test that imports the public entry point and asserts behavior. |
| `api` | HTTP, RPC, or similar request against the configured server plus a response/status assertion. |
| `e2e` | User-facing or entry-path probe that observes the Then clause, not only process survival. |
| `data` | Query, migration check, schema check, or file/data assertion against the persisted result. |

## UI Adapter Evidence

UI-facing criteria must use the configured `ui_verification` adapter from
`.harness/config.json` or an approved equivalent from
`docs/reference/ui-verification-adapter-contract.md`. The adapter must assert
the same user-observable Then clause: visible state, route, interaction,
accessibility, screenshot, terminal screen, or native window behavior as
appropriate.

If Playwright cannot run in the project, `/design_architecture` chooses another
capability-equivalent adapter. `/prepare_execute` must add an adapter-install
or adapter-build task before feature work when no runnable adapter exists.

Broad suite commands are allowed only when they include a feature-specific
assertion or filter. A command such as `pytest`, `npm test`, or `cargo test`
without a feature-specific oracle is weak evidence and should be reported as a
warning by planning or audit.

### SAST Evidence Layer

SAST (Static Application Security Testing) runs as a **mandatory per-task gate** for executable artifacts, independent of Verify-type evidence.

| Aspect | Requirement |
|--------|------------|
| Scope | Changed files only (not full codebase scan) |
| Timing | After implementer completes, before AC Verification |
| Severity handling | Critical/High = FAIL (block), Medium/Low = WARN (advisory) |
| Config | `config.security.sast_command` — project-specific SAST tool |
| Fallback | If no SAST command configured for executable artifact: WARN (not FAIL) |
| Evidence | SAST tool output (JSON preferred) recorded in task status |

**Relationship to Security Reviewer:** SAST gate catches pattern-based vulnerabilities (SQL injection, command injection, XSS, path traversal) that LLM review may miss. Security Reviewer catches logic-level security issues (broken auth, privilege escalation, insecure design) that SAST tools miss. Both layers complement each other.

## Automatable Criteria

Acceptance criteria default to `Automatable: true`. If a spec marks a criterion
as `Automatable: false`, the plan must replace it with an automated probe before
implementation.

`Automatable: false` with `Verify-type: e2e` or `api` is not executable until a
probe exists. The executor must treat a missing, empty, placeholder-only,
`echo`, `true`, or `:` Verify command as a failure.

## Planning Translation

Plans must copy relevant spec acceptance criteria into task completion criteria
without changing the behavior claim. If the Verify command changes between spec
and plan, the plan must preserve the same oracle strength and the audit should
report the drift. Predicted execution difficulty is not a reason to weaken
oracle strength. If a Verify command appears impractical, create infrastructure
or escalate — do not substitute a weaker oracle.

Behavior-bearing tasks must include a TDD Slice Contract with:

- public interface
- behavior under test
- test oracle
- setup or fixtures
- minimal implementation boundary
- non-goals
- missing-info handling

Plans that modify executable entry points must include runtime verification in
addition to acceptance criteria verification.

## Execution Verification

The executor must run Verify commands and check exit codes. Passing unit tests
alone is not completion.

The executor must extract Verify commands from the plan file at execution time,
not from cached context, implementer reports, or dispatch prompts. On every
verification pass the plan file is the single source of truth. If the
executor's context contains a different command, the plan file wins.

Recommended command timeouts:

| Verify-type | Timeout |
| --- | --- |
| `pure` | 30 seconds |
| `cli` | 30 seconds |
| `lib` | 30 seconds |
| `api` | 30 seconds after server readiness |
| `data` | 60 seconds |
| `e2e` | 120 seconds |

For `api` and `e2e` criteria that need a server, use configured start, health
check, and stop commands when available. If no server command exists, the audit
should warn before execution.

## Runtime Probe

Runtime probes prove executable artifacts start and survive long enough for
basic readiness. They are separate from feature verification.

A runtime probe passes only when:

- the process starts
- the process survives the configured interval
- fatal stdout or stderr patterns are absent
- GUI artifacts also satisfy configured window, screenshot, non-blank pixel
  variance, and optional UI Automation text/name checks

Executable artifacts (`cli`, `server`, `desktop`) require runtime smoke. A
missing required smoke command is failure, not skip. Only `docs` and `library`
artifacts may skip runtime smoke with `smoke.required: false`.
Executable artifacts (cli, server, desktop) require runtime smoke.

For executable artifacts, the smoke command must launch or probe the same
artifact a human would use. A build, typecheck, lint, or isolated test command
is not runtime smoke and must not be reused as `smoke.command`.

Vision checks may be used as advisory evidence, but the v1 hard gate is
deterministic process/window/screenshot/UI Automation evidence.

Runtime probe success never replaces a Verify command whose Then clause
describes feature behavior.

## App Delivery Verification

Use this section with `docs/reference/app-delivery-contract.md`.

- Frontend/UI verification must observe rendered output through a browser,
  mobile shell, desktop window, or framework-supported headless renderer when
  the requirement concerns a user-facing surface.
- Responsive UI verification must cover at least one mobile and one desktop
  viewport unless the App Experience And Delivery Baseline declares a
  single-viewport product.
- Visual verification may be screenshot diff, DOM/layout assertions, or a
  deterministic canvas/pixel check. It must include a feature-specific oracle.
- API verification must assert status, payload shape, and error shape when the
  feature exposes an API boundary.
- Package verification must assert that the declared artifact exists and can be
  launched or served through the same entry point a user or deploy target uses.
- Deployment verification defaults to preview deployment and must assert a
  readiness signal such as a URL, health endpoint, deployment status, or build
  log success. Production deployment requires explicit user intent.

## Light Path Gate

Subagent-driven and inline execution use the same verification semantics as the
harness path. The parent/controller owns the completion decision, but it must
delegate evidence-heavy work to gate scripts and reviewer/arbiter agents.

`scripts/lightpath-gate.ps1` is the controller interface:

- `-Scope prepare` converts the plan into harness-compatible step and wiring
  artifacts.
- `-Scope task` runs `scripts/verify-step.py` for the task step and records
  runtime smoke evidence when required. It must also write
  `phases/<phase>/task-gates/task-N.json`.
- `-Scope final` runs the Full-Feature Wiring Gate, then runs
  `scripts/harness-certify.ps1` before any `pass` completion. Reviewer
  verdicts map to `pass`, `test_gap`, `code_gap`, or `spec_gap`.

`scripts/harness-certify.ps1` is the completion source of truth. It writes
`phases/<phase>/completion-certificate.json` and fails closed unless every
completed step has a fresh passing task gate proof, the final wiring gate is
`pass` when required, and required runtime evidence is present.

The controller may keep only verdict enums, artifact paths, changed-file lists,
diff ranges, and short failure tails in context. It must not treat an
implementer subagent's `DONE` report as completion. Completion requires the
task gate proof and completion certificate to pass and the final wiring gate to
reach `pass`; `review_pending` requires an independent wiring reviewer verdict
before completion.

### Incremental Runnability

For executable artifacts, `config.smoke.command` runs after every task
following a completed skeleton task. This is separate from per-task
`Runtime verification:` which tests task-specific behavior. Incremental
smoke verifies the app still starts — it does not replace feature-specific
verification.

### Incremental Wiring Probe

Incremental Runnability proves the app starts. The Wiring Probe proves
the task's module is reachable from the app's entry point — closing the
gap between "app runs" and "feature is connected."

Every task that creates or modifies a module in an executable artifact must
include a `**Wiring probe:**` section in the plan with:

- Entry point file path (the WM-EP that should reach this module)
- Module file path (the file this task creates or modifies)
- Probe type: one of `import-chain`, `runtime-load`, or `e2e-touch`
- Verify command where exit 0 = module is reachable

Probe types:

| Probe type | What it proves | Example |
| --- | --- | --- |
| `import-chain` | Static import path exists from entry point to module. | `node -e "require('./src/main/index')"` or dependency-cruiser rule |
| `runtime-load` | App starts and module initializes (log output, DI resolution, handler registration). | `pnpm dev & sleep 3 && curl localhost:3000/health \| grep metrics && kill %1` |
| `e2e-touch` | User-facing action reaches the module (API call, UI interaction, CLI subcommand). | `playwright test --grep "metrics panel"` |

Probe evidence:

- `import-chain`: entry point → intermediate imports → target module chain
  traced statically. Verify exits non-zero if any link is missing.
- `runtime-load`: process starts, target module's initialization log or
  registration signal is observed, process exits cleanly.
- `e2e-touch`: user-facing action triggers observable behavior in the target
  module (response content, UI element, file output).

Tasks exempt from Wiring Probe:

- `docs` or `library` artifact kinds
- Tasks that only modify existing files without adding new modules
- Tasks where `config.wiring.enabled: false` with valid `exempt_reason`

A task creating a new module with no `**Wiring probe:**` section is a plan
defect. The executor logs a WARNING; the plan reviewer should have required it.

## Integration And Wiring

A plan needs a Full-Feature Wiring Gate when work crosses connected tasks,
multiple layers, executable entry points, or any route, registration, binding,
subscription, integration, milestone, or end-to-end path.

The gate must define:

- required status
- Verify-type (`e2e`, `api`, or `cli`)
- covered tasks or pipeline IDs
- expected observable result
- non-trivial automated Verify command

The wiring Verify command must drive the user-facing path or the same entry path
described by the gate. Single-component unit tests do not prove connected
features.

Passing a wiring command only proves the dynamic probe ran. Full-feature wiring
is complete only after runtime evidence is present and an independent wiring
review verdict is `PASS`; until then the gate remains `review_pending`.

## Arbiter Verdicts

Independent arbiters and wiring reviewers classify gaps as:

- `PASS`: evidence observes the entry path and no connection gap remains.
- `TEST_GAP`: implementation may be wired, but evidence does not prove the Then clause.
- `CODE_GAP`: registration, route, import, binding, subscription, or call site is missing.
- `SPEC_GAP`: the plan lacks an automatable oracle or enough path detail to judge wiring.

## Wiring Config Validation (fail-closed)

This is the canonical definition of wiring config validation. All commands
and reference docs should reference this section instead of restating.

### Cross-Reference Policy

When a rule from this contract appears in another document:
- **Subagent-consumed documents** (commands/, agents/): inline restatement allowed (isolation principle; SOCpilot: inline compliance 0.87 vs cross-ref 0.36). Must annotate canonical source.
- **Reference documents** (docs/reference/): cross-reference only, no restatement.
- Inline restatements must include a `Canonical definition:` annotation pointing here.

- `wiring` block missing → FAIL: `"config.json has no wiring block. Run /setup to regenerate."`
- `wiring.enabled: false` + `wiring.exempt_reason` empty → FAIL: `"wiring disabled without exempt_reason."`
- `wiring.enabled: false` + `wiring.exempt_reason` non-empty + `artifact_kind` not `docs` or `library` → FAIL: `"wiring exemption not allowed for artifact_kind: {kind}"`
- `wiring.enabled: false` + `wiring.exempt_reason` non-empty + `artifact_kind` is `docs` or `library` → skip/exempt
- `wiring.enabled: true` + `wiring.view_extensions` empty → skip only View Wiring Test. Full-Feature Wiring Gate still runs when required.

## View Wiring Verification

The rules in this English subsection are canonical. If later legacy text in
this section conflicts or is unreadable, ignore it and follow this subsection.

Apply view wiring verification to tasks that create or modify files matching
`config.wiring.view_extensions`. Logic-only tasks with no view file are exempt.

Verification layers:

1. Model/ViewModel test: existing task acceptance criteria.
2. View Wiring Test: instantiate the view, attach the real model or view model,
   and assert binding/handler/dependency/template behavior.
3. Integration Probe: exercise the connected feature path through the
   Full-Feature Wiring Gate.
4. Runtime Smoke: prove the executable starts and survives according to
   `config.smoke`.

Layer 1 alone does not prove view wiring. A task that changes a view file must
run either its task-level `View wiring verification` command or
`config.wiring.view_test_command`; exit 0 is PASS.

Classify view wiring failures with this taxonomy:

| ID | Defect | Observable symptom |
| --- | --- | --- |
| W1 | Binding resolution | Expected rendered value is missing or null. |
| W2 | Handler connection | User interaction does not change model state. |
| W3 | Dependency resolution | Real DI/startup fails, nulls, or crashes. |
| W4 | Activation state | Enabled/disabled state is hardcoded or stale. |
| W5 | Template resolution | Model resolves to the wrong or no view/template. |

Full-Feature Wiring Gate failures must identify the failed view or pipeline,
classify W1-W5 when applicable, map the failure back to the responsible task,
and retry at most 3 times before user escalation.

## Assertion Dimensions

Step verification uses four primary assertion dimensions via
`scripts/verify-step.py`, plus an optional static dimension.
Each dimension produces independent pass/fail results with per-check detail.

| Dimension | What it checks |
| --- | --- |
| `structural` | File existence, JSON/YAML parse validity, markdown section presence. |
| `content` | Regex patterns, count thresholds, banned expression scan. |
| `relational` | Cross-file reference integrity (R-ids in spec match plan, file refs exist). |
| `command` | Shell command execution with exit 0 semantics (backwards-compatible). |
| `static` | Optional `Static-verify:` or `Ast-grep:` command execution. |

Verify-type determines which dimensions apply:

| Verify-type | structural | content | relational | command |
| --- | --- | --- | --- | --- |
| `pure` | yes | yes | - | yes |
| `cli` | yes | yes | - | yes |
| `lib` | yes | yes | yes | yes |
| `api` | yes | yes | yes | yes |
| `data` | yes | yes | yes | yes |
| `e2e` | yes | yes | yes | yes |

A step passes only when all enabled dimensions pass. The `command` dimension
preserves backwards compatibility with existing shell Verify commands.

If `phases/<phase>/anchors/<step>.hashline.json` exists, structural
verification also checks that the generated step file has not drifted from its
conversion-time anchor. If `.harness/config.json` sets
`verification.static_required: true`, a step without static verification fails.

### Legacy Notes

View를 포함하는 작업의 모델 레벨 테스트만으로는 5가지 와이어링 결함을 잡지
못한다. 검증 계층 모델:

```
Layer 1: Model/ViewModel Unit Test  (기존 — Task AC)
Layer 2: View Wiring Test           (이 섹션)
Layer 3: Integration Probe          (Full-Feature Wiring Gate)
Layer 4: Runtime Smoke              (config.smoke)
```

Layer 1만으로는 와이어링을 검증할 수 없다. Layer 2-3이 반드시 필요하다.

### 적용 조건

`config.wiring.view_extensions`에 해당하는 파일을 Create 또는 Modify하는 Task에
의무 적용. 모델/로직 전용 Task는 면제.

### Wiring Defect Taxonomy (W1-W5)

| ID | 결함 유형 | 모델 테스트가 못 잡는 이유 | 실앱 증상 |
|---|---|---|---|
| W1 | Binding resolution | 뷰를 인스턴스화하지 않음 | 데이터 안 나옴 (조용한 실패) |
| W2 | Handler connection | 뷰 상호작용 코드 미실행 | 버튼/이벤트 무반응 |
| W3 | Dependency resolution | Mock 사용, 실제 DI 미검증 | 앱 시작 시 크래시 또는 null |
| W4 | Activation state | 모델 속성과 무관하게 하드코딩 | 요소 비활성/숨김 |
| W5 | Template resolution | 모델만 테스트 | 모델은 있으나 뷰 렌더 안 됨 |

### Per-Task View Wiring Test (Layer 2)

View를 생성하거나 수정하는 모든 Task에 의무 적용.
모델만 생성하는 Task (View 없음)는 면제.

Task의 AC 검증 통과 후, View Wiring Verify 커맨드를 실행한다.
커맨드 소스: task의 `**View wiring verification**` 섹션 Verify 또는
`config.wiring.view_test_command`. Exit 0 = PASS.

5대 검증 항목:

- **W1 Binding resolution**: 뷰 인스턴스화 후 핵심 데이터 바인딩 속성이
  non-null 값으로 렌더됨
- **W2 Handler connection**: 사용자 상호작용 핸들러를 프로그래밍으로 트리거 →
  모델 상태 변경 확인
- **W3 Dependency resolution**: 런타임 DI에서 모델/서비스 해석 → 뷰 컨텍스트
  설정 → 크래시 없음
- **W4 Activation state**: 사용자 상호작용 요소의 활성화 상태가 모델에 바인딩,
  하드코딩 아님
- **W5 Template resolution**: 모델→뷰 템플릿 매핑이 기대하는 뷰 타입으로 해석

### Integration Probe (Layer 3)

2개 이상의 Task가 완료된 빌드, executable artifact가 있는 빌드, 또는
Full-Feature Wiring Gate가 plan에 정의된 빌드에서 적용.

Full-Feature Wiring Gate의 Verify 커맨드로 전체 파이프라인 와이어링을 검증한다.
`config.wiring.wiring_gate_command`가 설정되어 있으면 이를 우선 사용.
기존 Wiring Gate 계약과 동일한 규칙 적용.

Wiring Gate FAIL 시:
1. 어떤 View/Pipeline에서 실패했는지 식별
2. 어떤 유형의 결함인지 (W1-W5) 분류
3. 해당 Task 역추적 → 재구현 디스패치
4. Max 3 retries → user 에스컬레이션
5. Wiring Gate 건너뛰기 불가 (Required: yes인 경우)

## Per-Task Quality Gates

These gates run after each implementer completion, before AC Verification.
`/choice_execute` references these sections by name; this file is the canonical
procedure.

### Test Baseline Protection

**Purpose:** Prevent AI from silently deleting, weakening, or disabling existing tests (SWE-bench PASS_TO_PASS invariant).

**Phase 1 — Baseline Snapshot (before implementer dispatch):**
1. Record test file inventory:
   - `git ls-files -- '**/*test*' '**/*spec*' '**/__tests__/**' '**/*.test.*' '**/*.spec.*'`
   - Store as `test_baseline_files` list
2. If `config.test.command` exists:
   - Run test suite: `config.test.command` (timeout: 120s)
   - Record pass count, fail count, skip count as `test_baseline_counts`
   - Store individual test names if test runner supports `--list` or JSON output

**Phase 2 — Protection Check (after implementer completes, before AC Verification):**

1. **Deletion detection:**
   - `git diff --name-status <task-start-hash>..HEAD -- '**/*test*' '**/*spec*' '**/__tests__/**'`
   - If any test file has status `D` (deleted): **FAIL** (`"Test file deleted: {path}. AI must not delete existing tests."`)
   - Re-dispatch implementer: "Restore deleted test file {path}. Fix the implementation to pass the existing test, do not delete the test."

2. **Weakening detection:**
   - For modified test files: `git diff <task-start-hash>..HEAD -- {modified_test_files}`
   - Count assertion removals: lines matching `assert|expect|should|toBe|toEqual|assertEqual|raises|throws` removed vs added
   - If net assertion count decreased by >20%: **WARN** (`"Test assertions reduced by {pct}% in {file}."`)
   - If assertions reduced to 0 in any test function: **FAIL** (`"All assertions removed from test function in {file}"`)

3. **PASS_TO_PASS verification:**
   - If `config.test.command` exists and baseline was recorded:
     - Re-run `config.test.command` (timeout: 120s)
     - Compare: pass_count must be >= `test_baseline_counts.pass_count`
     - If pass_count decreased: **FAIL** (`"PASS_TO_PASS violation: {n} previously passing tests now fail"`)
     - Re-dispatch implementer: "Fix implementation so these previously-passing tests pass again: {list}"
   - Max 3 re-dispatch attempts, then escalate to user

4. **Skip/disable detection:**
   - Check diff for newly added skip markers: `@pytest.mark.skip`, `@Ignore`, `xit(`, `xdescribe(`, `test.skip(`, `.skip()`, `#[ignore]`
   - If found: **WARN** (`"New test skip marker added in {file}:{line}."`)

Inline execution (Path 3): Same detection/execution. Re-dispatch is replaced by fix-in-place -> re-check loops (max 3).

### Lint & Typecheck Gate

**Purpose:** Catch hallucinated API calls, undefined references, and code quality issues per-task (Aider lint-test-fix pattern).

**Trigger:** Every task (unconditional).

**Execution:**
1. Collect changed files: `git diff --name-only <task-start-hash>..HEAD` + `git ls-files --others --exclude-standard`
2. Filter to source files (exclude config, docs, assets)

3. **Typecheck gate** (if `config.build.typecheck_command` configured):
   - Run: `config.build.typecheck_command` (timeout: 60s)
   - Exit 0 -> PASS
   - Non-zero -> extract errors in changed files only (ignore pre-existing errors)
   - If new type errors in changed files: **FAIL** -- re-dispatch implementer with error output
   - Max 2 retries, then escalate

4. **Lint gate** (if `config.lint.command` configured):
   - Run: `config.lint.command -- {changed_source_files}` (timeout: 60s)
   - Or if lint command doesn't accept file args: run full lint, filter output to changed files
   - Exit 0 -> PASS
   - Non-zero -> extract lint errors in changed files
   - **Error-level findings** -> **FAIL** -- re-dispatch with lint output
   - **Warning-level findings** -> **WARN** -- include in task status, do not block
   - Max 2 retries, then escalate

5. **Hallucination signal detection:**
   - Type errors containing "is not defined", "cannot find module", "has no attribute", "undefined reference" in changed files -> likely hallucinated API/import
   - Add to re-dispatch prompt: "The following references do not exist -- verify the API/module exists before using it: {error_list}"

Inline execution (Path 3): Same detection/execution. Re-dispatch is replaced by fix-in-place -> re-check loops (max 2).

### Dependency Audit Gate

**Trigger:** Task diff includes changes to dependency manifests (`package.json`, `requirements.txt`, `Pipfile`, `Cargo.toml`, `go.mod`, `pom.xml`, `build.gradle`, `Gemfile`, `*.csproj`).

**Execution:**
1. Check `config.security.dependency_audit_command` in `.harness/config.json`
   - If missing: use auto-detection based on manifest type:
     | Manifest | Auto command |
     |----------|-------------|
     | package.json | `npm audit --json` |
     | requirements.txt / Pipfile | `pip-audit --format=json` |
     | Cargo.toml | `cargo audit --json` |
     | go.mod | `govulncheck ./...` |
   - If auto-detection fails: **WARN** (`"No dependency audit tool detected"`)
2. Detect newly added dependencies:
   - `git diff <task-start-hash>..HEAD -- {manifest_files}`
   - Extract added package names
3. For each newly added package:
   - **Registry existence check**: verify package exists in the canonical registry
   - If package does NOT exist in registry: **FAIL** (`"Hallucinated dependency: {package_name} not found in {registry}"`)
4. Run dependency audit command
   - Critical/High CVE → **FAIL** (max 2 retries: use alternative package or pin safe version)
   - Medium/Low CVE → **WARN** (include in final report)
5. Record audit results in task status
