---
description: Decompose spec into task plans with agent assignments
allowed-tools: [Bash, Read, Write, Agent, AskUserQuestion]
---

# /plan — 작업순서 플래닝

brainstorm에서 만든 설계 문서(spec)를 입력으로 받아 상세 task 문서로 분해하고 에이전트 배치를 결정한다. 코드는 작성하지 않는다.

> **For agentic workers:** /choiceexecutor에서 서브에이전트 드리븐, 하네스, 또는 인라인 실행으로 이 plan의 task를 실행한다. Steps는 체크박스 구문으로 추적.

## 1. 사전 확인

다음을 먼저 확인한다:
1. `.harness/config.json` 존재 여부
2. `AGENTS.md` 존재 여부
3. spec 문서 존재 여부 (우선순위: 인자 > `phases/index.json`의 brainstorm.artifact > config의 `defaults.spec_location` 디렉터리에서 파일명의 `YYYY-MM-DD` 접두사를 기준으로 가장 최근 날짜의 파일 선택. 동일 날짜면 파일명 내림차순)
4. 최근 git 변경사항

없으면 해당 단계를 먼저 실행하라고 안내하고 종료:
- config 없음 -> `/setup`
- spec 없음 -> `/brainstorm`

`phases/index.json`이 있으면 plan phase를 `in_progress`로 업데이트:
```json
{ "current_phase": "plan", "phases": { ..., "plan": { "status": "in_progress" } } }
```

## 2. Spec 읽기 + 가정 선언

spec을 읽은 후 가정을 선언한다:

```
ASSUMPTIONS ABOUT THIS SPEC:
1. [모호한 요구사항 해석에 대한 가정]
2. [spec에 명시되지 않은 기술 접근에 대한 가정]
3. [모듈 경계나 기존 코드 동작에 대한 가정]
-> 틀린 게 있으면 지금 알려주세요.
```

명확하지 않은 부분이 있으면 사용자와 짧게 합의한다. 한 번에 하나의 질문만.

## Scope Check

spec이 여러 독립 서브시스템을 다루면 별도 plan으로 분할 제안. 각 plan은 독립적으로 작동하는 테스트 가능한 소프트웨어를 산출해야 한다.

## 3. 파일 구조 매핑

태스크를 정의하기 전에 생성/수정할 파일을 먼저 매핑한다:
- 각 파일의 책임을 명확히 — 하나의 파일, 하나의 명확한 책임
- 단위가 명확한 경계와 인터페이스를 갖도록
- 함께 변경되는 파일은 함께 배치
- 기존 코드베이스라면 기존 패턴을 따름
- 작고 집중된 파일 선호 — 파일이 커지면 역할이 과다한 신호

## 4. Coverage Matrix (필수)

모든 plan은 이 매트릭스를 포함해야 한다:

```markdown
## Coverage Matrix

| Requirement | Related Tasks |
|-------------|---------------|
| R1: [제목] | T1, T3 |
| R2: [제목] | T2 |
```

규칙:
- spec의 모든 R이 매트릭스에 있어야 함
- 모든 R이 최소 하나의 T에 매핑되어야 함
- R에 대응 T가 없으면 task를 추가하거나 이유를 명시 (사용자 승인 필요)
- T가 R에 매핑되지 않으면 경고 (불필요한 작업 가능성)

**Hard gate:** plan reviewer가 검증. 누락된 매트릭스 또는 매핑 안 된 R = FAIL.

## Structural Invariants (권장)

Coverage Matrix 다음에, 프로젝트에 아키텍처 규칙(`.claude/rules/`, AGENTS.md 제약, CLAUDE.md 규칙)이 있으면 추출하여 포함:

```markdown
## Structural Invariants

| ID | Rule | Source | Verification |
|----|------|--------|-------------|
| SI-1 | DB layer must not import from API layer | .claude/rules/db.md | `grep -r "from.*api/" src/db/` returns no matches |
| SI-2 | Shared module has no runtime dependencies | CLAUDE.md | `jq '.dependencies' shared/package.json` is empty |
```

규칙:
- 각 invariant은 검증 가능한 커맨드로 표현
- Source에 규칙 파일/문서 참조
- 프로젝트 규칙 없으면 이 섹션 생략 — 규칙을 만들어내지 않는다
- code-reviewer가 구현 완료 후 검증

## 5. Task 분해 원칙

각 task는 독립적인 에이전트 세션에서 실행된다고 가정하고 작성한다.

**반드시 지킬 것:**
- 한 task는 하나의 명확한 목표
- task 문서만 읽고도 작업을 시작할 수 있어야 함
- "이전 대화에서" 같은 외부 문맥 참조 금지
- 관련 문서와 파일 경로를 명시
- AC는 관찰 가능한 결과 기준

### Token Budget

- **경험칙:** 100 lines ≈ 500-1000 tokens
- **목표:** task당 컨텍스트 비용을 모델 context window의 ~25% 이내
- **분할 트리거:**
  - 5+ 파일을 건드리는 task
  - 10+ 파일을 읽어야 하는 task
  - 인프라 변경 + 비즈니스 로직 혼합
  - 새 파일 생성 + 기존 밀결합 파일 수정 혼합

### Task 크기

- 각 step은 2-5분 단위 (테스트 작성, 실행, 구현, 검증, 커밋)
- 인프라 변경과 비즈니스 로직 변경을 섞지 않음

### Task 구조

````markdown
### Task N: [이름] [R1, R3]

**Files:**
- Create: `exact/path/to/file.py`
- Modify: `exact/path/to/existing.py:123-145`
- Test: `tests/exact/path/to/test.py`

**Impact scope:**
- (a) Reference breakage: [`path/to/consumer.py`] — imports `changed_function`; [`path/to/indirect.py`] — imports via re-export in `path/to/barrel.py`; [`path/to/caller.py`] — calls `modified_function` (signature change: added `timeout` param)
- (b) Call site info (reference only — no verdict impact): [`path/to/other.py:30`] — calls `modified_function` (behavioral dependency only)
- (c) Code preservation: [`path/to/existing.py:50-65`] — input validation logic, must be preserved

**Depends on:** Task N (있으면)
**File overlap with:** Task N (같은 파일 수정 시)

**Completion criteria (from spec):**
- [ ] (R1) Given: [조건] / When: [행동] / Then: [결과] / Verify: `[커맨드]`

**Verification method:** spec의 Verify 커맨드 실행 (exit 0 = PASS)

- [ ] **Step 1: Write the failing test**

```python
def test_specific_behavior():
    # Given: [precondition from completion criteria]
    result = function(input)
    # Then: [expected outcome]
    assert result == expected
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/path/test.py::test_name -v`
Expected: FAIL

- [ ] **Step 3: Write minimal implementation**

- [ ] **Step 4: Run test to verify it passes**

- [ ] **Step 5: Run Verify command**

```bash
[Verify command from completion criteria]
```
Expected: exit 0

- [ ] **Step 6: Commit**
````

### Impact scope 규칙

- Modify 파일이 있는 task만 필수. Create-only task는 면제.
- **(a) Reference breakage:** 변경 후 수정 없이는 깨지는 파일 목록.
  - 직접 import + re-export chain 1단계
  - 시그니처 변경 (파라미터 추가/제거/타입 변경, 반환 타입, 예외, 이름 변경)
  - Re-export 패턴: JS/TS `export { X } from`/`export * from`, Python `__init__.py`, CommonJS `module.exports = require(...)`
  - 불확실하면 (a)로 분류 (안전 > 효율)
- **(b) Call site info:** 동작에만 의존, 수정 불필요. "reference only" 마커. 누락이 FAIL 유발 안 함.
- **(c) Code preservation:** 수정 범위 내 방어 코드 (validation, error handling, auth). 없으면 "No defensive code patterns found" 명시.

### Completion criteria 규칙

- spec AC를 **원문 그대로 복사** — 의역 금지
- task가 여러 R에 걸치면 해당 부분만 복사
- 모든 task에 verification method 필수

### Task 의존성

- `**Depends on:** Task N` — 선행 task 필수
- `**File overlap with:** Task N` — 같은 파일 수정
- 모든 task 독립이면 Coverage Matrix 뒤에 "All tasks are independent" 표기

## 6. 에이전트 배치

```markdown
## Agent Assignment

| Task | Agent | Mode | Reason |
|------|-------|------|--------|
| T1 | subagent | isolated | 독립 모듈 생성 |
| T2 | subagent | isolated | 독립 테스트 |
| T3 | inline | sequential | T1 결과에 의존 |
```

Mode: `isolated` / `sequential` / `parallel`

## 7. Plan Review Loop

Plan 작성 완료 후:

1. `ezpowers:plan-reviewer` 플러그인 에이전트를 `subagent_type`으로 지정하여 디스패치. 동적 정보만 prompt로 전달:

   ```
   Agent tool:
     subagent_type: "ezpowers:plan-reviewer"
     description: "Review plan document"
     prompt: |
       **Plan to review:** <plan 파일의 절대 경로>
       **Spec for reference:** <spec 파일의 절대 경로>
   ```

2. reviewer 결과는 `## Verdict: PASS` 또는 `## Verdict: FAIL` 헤더만 판정 기준으로 파싱. 다른 위치의 `PASS`/`FAIL` 문자열은 무시. **Verdict 헤더가 없거나 형식이 다르면:** `FAIL`로 간주하되, 2회 연속 Verdict 헤더 누락 시 사용자에게 에스컬레이션 ("Reviewer가 표준 형식으로 판정을 반환하지 않습니다.")
3. Issues Found -> fix -> fresh 서브에이전트 재디스패치 (동일 프롬프트, 이전 결과 전달 금지)
4. 비공개 이슈 로그 유지 — oscillation 감지용. 각 이슈를 `{task}:{check_number}` 키로 기록 (예: `T2:coverage_matrix`, `T3:impact_scope`).
5. **Oscillation check (iteration 3부터):** 현재 이슈의 `{task}:{check_number}` 키가 2+ 이전 iteration에도 존재 -> 즉시 사용자 에스컬레이션
6. **Tiered escalation:** 3회 -> 경고. 5회 -> 중단.

## Backward Transition: /brainstorm으로 복귀

plan 작성 중 spec이 불충분하면 — 누락 요구사항, 모순된 제약, 불분명한 범위 — 깨진 spec에 대해 plan을 계속 쓰지 않는다.

**트리거:**
- task 분해 시 요구사항이 모호
- 두 spec 요구사항이 모순
- 중대한 기술 제약이 spec에서 탐색되지 않음

**액션:**
1. 이유 로그: "Returning to /brainstorm: [구체적 이유]"
2. 사용자에게 보고: 무엇이 불충분하고 왜 plan 진행 불가
3. `/brainstorm`으로 복귀하여 spec 갭 해결
4. spec 업데이트 후 `/plan` 재개

## 8. 산출물

**저장 위치:** `AGENTS.md`의 `plan location:` 값. 없으면 `docs/plans/` 기본값.
**파일명:** `YYYY-MM-DD-<feature-name>.md`

Plan 헤더:
```markdown
# [Feature Name] Implementation Plan

**Goal:** [한 문장]
**Architecture:** [2-3 문장]
**Tech Stack:** [핵심 기술]
**Spec:** [spec 파일 경로]

---
```

### INDEX.md 업데이트

Plan 커밋 시 `docs/INDEX.md`에 plan 항목을 추가:

```markdown
## Plans
- [YYYY-MM-DD-<feature-name>](plans/YYYY-MM-DD-<feature-name>.md): [derived] 구현 플랜
```

기존 Plans 섹션이 있으면 항목 추가, 없으면 섹션 생성.

## 9. 완료 안내

plan 작성이 끝나면:
1. task 개수, 의존 관계 요약
2. 리스크 있는 task
3. 다음 명령: `/choiceexecutor`

`phases/index.json` 업데이트:
- plan: `status: "complete"`, `artifact: "<plan 파일 경로>"`, `completed_at: "<ISO 8601>"`
- build: `status: "pending"` (변경 없음 확인)

## Remember

- 정확한 파일 경로 항상
- plan에 완전한 코드 ("validation 추가" 금지)
- 기대 출력이 있는 정확한 커맨드
- DRY, YAGNI, TDD, 빈번한 커밋

## Common Rationalizations

| 핑계 | 현실 |
|------|------|
| "spec이 명확해서 plan 불필요" | Spec은 WHAT, Plan은 HOW + 순서 + 파일. 둘 다 필요. |
| "task 순서는 구현 중에" | 잘못된 순서 = 차단, 컨텍스트 스위치, 충돌. 지금 계획. |
| "task가 너무 많아 그룹핑" | 그룹핑은 복잡성을 숨긴다. 5분 넘으면 분할. |
| "impact scope 분석이 오래 걸린다" | 구현 중 깨진 호출자 찾기가 더 오래. 5분 분석이 수시간 디버깅 절약. |
| "테스트는 당연해서 plan에 불필요" | 누구에게 당연? 구현자에게 정확한 테스트 코드와 커맨드 필요. |
| "파일 구조는 자연스럽게" | 자연 발생 = 일관성 없는 경계. 경계를 미리 결정. |
| "coverage matrix는 관료주의" | 매핑 안 된 요구사항 = 잊힌 요구사항. 매트릭스가 안전망. |
| "이 task는 너무 작아서 step 불필요" | 작은 task도 step 누락 시 잘못 구현. 명시한다. |