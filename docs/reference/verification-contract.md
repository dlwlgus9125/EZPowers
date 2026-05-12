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

Broad suite commands are allowed only when they include a feature-specific
assertion or filter. A command such as `pytest`, `npm test`, or `cargo test`
without a feature-specific oracle is weak evidence and should be reported as a
warning by planning or audit.

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
report the drift.

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

Vision checks may be used as advisory evidence, but the v1 hard gate is
deterministic process/window/screenshot/UI Automation evidence.

Runtime probe success never replaces a Verify command whose Then clause
describes feature behavior.

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

## Arbiter Verdicts

Independent arbiters and wiring reviewers classify gaps as:

- `PASS`: evidence observes the entry path and no connection gap remains.
- `TEST_GAP`: implementation may be wired, but evidence does not prove the Then clause.
- `CODE_GAP`: registration, route, import, binding, subscription, or call site is missing.
- `SPEC_GAP`: the plan lacks an automatable oracle or enough path detail to judge wiring.

## View Wiring Verification

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
