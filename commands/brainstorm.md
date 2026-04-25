# /brainstorm — 설계 문서 생성

아이디어를 대화를 통해 설계 문서(spec)로 만든다. 구현 코드는 작성하지 않는다.

<HARD-GATE>
설계 문서를 사용자가 승인하기 전까지 어떤 구현 행위도 하지 않는다. 프로젝트가 아무리 단순해 보여도 설계 -> 승인 -> plan 순서를 지킨다.
</HARD-GATE>

## Anti-Pattern: "이건 너무 단순해서 설계가 필요 없다"

모든 프로젝트가 이 프로세스를 거친다. 간단한 유틸, 설정 변경 포함. "단순한" 프로젝트에서 검토하지 않은 가정이 가장 많은 재작업을 일으킨다. 설계는 짧을 수 있지만 반드시 존재해야 하고 사용자 승인을 받아야 한다.

## Process Flow

```
프로젝트 컨텍스트 파악
  -> 한 번에 하나씩 질문 (scope, constraints, success criteria)
  -> 접근법 2-3개 제안 + 추천
  -> 설계 섹션별 제시 -> 사용자 승인
  -> 요구사항 추출 (R1, R2, ...)
  -> 사용자 요구사항 확인
  -> Spec 문서 작성 + 커밋
  -> Spec review loop (서브에이전트)
  -> 사용자 Spec 리뷰
  -> 다음 단계: /plan
```

## 1. 프로젝트 컨텍스트 파악

먼저 현재 프로젝트 상태를 읽는다:
- `AGENTS.md` (steering 정보)
- `.harness/config.json` (프로젝트 설정)
- 디렉터리 구조, 최근 git 변경
- `docs/` 아래 기존 문서

`.harness/config.json`이 없으면 `/setup`을 먼저 실행하라고 안내하고 종료.

`phases/index.json`이 있으면 brainstorm phase를 `in_progress`로 업데이트:
```json
{ "current_phase": "brainstorm", "phases": { ..., "brainstorm": { "status": "in_progress" } } }
```

## 2. 대화형 설계

**질문 규칙:**
- **한 번에 하나의 질문만** — 사용자를 압도하지 않는다
- **도메인 정의 질문을 구현 질문보다 먼저** — "어떤 문제를 풀려는 건가요?"가 "어떤 기술 스택을 쓸까요?"보다 선행
- 가능하면 선택지 형태로 제시
- 목적, 제약, 성공 기준에 집중
- 이미 알고 있는 것은 다시 묻지 않는다

**범위 확인:**
- 요청이 여러 독립 서브시스템을 포함하면 즉시 분해를 제안
- 분해가 필요하면 첫 번째 서브프로젝트부터 진행
- 각 서브프로젝트는 자체 spec -> plan -> build 사이클

**접근법 제안:**
- 2-3개 접근법을 트레이드오프와 함께 제시
- 추천 옵션을 먼저, 이유와 함께

**설계 제시:**
- 섹션별로 나누어 제시 (아키텍처, 컴포넌트, 데이터 플로우, 에러 처리, 테스트)
- 각 섹션 후 "여기까지 맞나요?" 확인
- 복잡도에 비례해 설명량 조절

**격리와 명확성을 위한 설계:**
- 각 단위가 명확한 목적, 잘 정의된 인터페이스, 독립적으로 테스트 가능
- 내부를 모르고도 역할을 이해할 수 있는가? 내부를 바꿔도 소비자가 안 깨지는가?

**기존 코드베이스 작업:**
- 기존 구조를 먼저 탐색하고 기존 패턴을 따른다
- 현재 작업에 영향을 미치는 문제만 개선 포함, 무관한 리팩토링 금지

## 3. 가정 선언

설계 제안 전 가정을 명시적으로 선언한다:

```
ASSUMPTIONS:
1. [scope/기술/제약/의도에 대한 가정]
2. [기존 코드 동작이나 시스템 경계에 대한 가정]
-> 틀린 게 있으면 지금 알려주세요.
```

가정이 틀렸으면 영향받는 설계를 수정한다.

## 4. 요구사항 추출

사용자가 설계를 승인하면 대화에서 모든 요구사항을 추출한다:

```
## Extracted Requirements

- R1: [구체적 요구사항]
- R2: [구체적 요구사항]
...

빠진 것이나 수정할 것이 있나요?
```

규칙:
- 각 요구사항에 고유 ID (R1, R2, ...)
- 요약이 아닌 구체적이고 실행 가능한 문장
- 사용자가 명시적으로 승인할 때까지 반복
- 요구사항이 10개를 넘으면 서브프로젝트 분해 제안

**Hard gate failure:** 사용자가 누락 요구사항을 3회 연속 지적하면 → "논의되지 않은 요구사항이 많은 것 같습니다. 질문 단계로 돌아가 더 탐색할까요?"

## 5. Spec 문서 작성

요구사항이 확인되면 spec 문서를 작성한다.

**저장 위치:** `AGENTS.md`의 `spec location:` 값. 없으면 `docs/specs/` 기본값.
**파일명:** `YYYY-MM-DD-<topic>-design.md`

### Extracted Requirements 섹션 (필수)

Spec 파일 상단에 섹션 4에서 추출한 요구사항 목록을 반드시 포함한다:

```markdown
## Extracted Requirements

- R1: [요구사항 제목]
- R2: [요구사항 제목]
...
```

이 섹션은 spec reviewer가 요구사항 커버리지를 검증하는 기준이 되며, `/plan`의 Coverage Matrix가 이 목록을 참조한다. 누락 시 spec review FAIL.

### 요구사항별 구조

각 요구사항은 이 구조를 따른다:

```markdown
### R[N]: [제목]

**Input:** [트리거 또는 입력]
**Behavior:** [단계별 동작 설명]
**Output:** [관찰 가능한 결과]
**Impact scope:**
- [모듈/컴포넌트]: [영향]
**Acceptance criteria:**
- [ ] Given: [사전 조건 — 행동 전 관찰 가능 상태]
      When: [사용자 또는 시스템이 수행하는 행동]
      Then: [관찰 가능한 결과]
      Verify: `[exit 0 = 통과인 셸 커맨드]`
      Verify-type: [api | e2e | cli | lib | data | pure]
**Edge cases:**
- [조건]: [기대 동작]
```

**Hard gate:** 각 R에 Input, Behavior, Output, Impact scope, Acceptance criteria, Edge cases 6개 필수. 하나라도 빠지면 FAIL.

### 구현 용어 금지 (Implementation term ban)

Given/When/Then 텍스트에 구현 용어(함수명, 클래스명, 내부 변수명 등) 금지. 사용자 행동과 관찰 가능한 결과만 기술.

예: ~~"When `handleClick()` is called"~~ -> "When the user clicks the submit button"

### Pure-type exception

Verify-type이 `pure`인 경우 Given/When/Then 대신 Input/Transform/Output 형식 허용:

```markdown
- Input: [입력값]
  Transform: [순수 변환 설명]
  Output: [기대 출력]
  Verify: [검증 커맨드]
  Verify-type: pure
```

### Verify-type 가이드

| Verify-type | When to use | Example Verify |
|-------------|-------------|----------------|
| `api` | REST/GraphQL endpoint behavior | `curl -s localhost:3000/api/users \| jq '.status'` returns `200` |
| `e2e` | User-facing UI flow | `playwright test tests/login.spec.ts` passes |
| `cli` | CLI command behavior | `mycli --version` prints `1.2.0` |
| `lib` | 인라인 스크립트로 소비자 코드 실행 | `node -e "const {parse} = require('./lib'); assert(parse('k=v').k === 'v')"` |
| `data` | Data migration, schema, ETL | Query `SELECT count(*) FROM users` returns expected count |
| `pure` | Pure function, no side effects | `assertEquals(add(1, 2), 3)` |

### Re-export awareness

영향받는 모듈의 심볼이 다른 모듈에서 re-export되면 (barrel files, `__init__.py` 등) re-exporting 모듈도 Impact scope에 포함.

### Deletion requirements 변형

삭제 요구사항 (예: "R5: feature X 제거"):
- Input/Output 대신 "Before state" / "After state" 사용
- AC: 기능이 완전히 제거되었음을 증명하는 조건

### 금지 표현

다음 표현은 spec 문서에서 **금지**. 존재하면 자동 FAIL:

| 금지 (Korean) | 금지 (English) | 이유 | 대안 |
|---------------|----------------|------|------|
| 적절히/적절하게 처리한다 | handle appropriately | 구현자가 추측해야 함 | 정확한 동작 기술 |
| 필요한 경우/필요 시 | if necessary/if needed | 조건 미정의 | 정확한 조건 기술 |
| 등등/기타/등 | etc./and so on | 범위 무한 | 전체 목록 또는 "이 목록이 전부" |
| 올바르게/정상적으로 | properly/correctly | 정의 없음 | AC로 정의 |
| 효율적으로/최적화하여 | efficiently/optimized | 측정 불가 | 구체적 메트릭 또는 삭제 |
| 가능하면/가급적 | if possible/preferably | 필수 여부 불명 | MUST 또는 MAY 명시 |
| 상황에 맞게/상황에 따라 | as appropriate/depending on | 결정 보류 | 상황과 대응을 열거 |

**예외:** 코드 블록(```)이나 인용문(> ) 안의 표현은 면제.

**Hard gate failure loop:** 금지 표현 발견 -> 구체적 언어로 자동 교체 -> 재확인. 3회 실패 후 사용자에게 해당 문장의 구체적 동작 요청.

### Verify 스크립트 생성

spec 커밋 시 `<spec-basename>.verify.sh`도 함께 생성:
1. spec의 모든 Verify 커맨드 추출
2. Verify가 0개면: 생성 건너뛰고 경고
3. 서버 의존 커맨드(api, e2e): 서버 start/stop 래핑
4. 외부 서비스 의존 커맨드: `|| echo "SKIP: ..."` 처리
5. spec과 같은 커밋에 포함

### INDEX.md 업데이트

Spec 커밋 시 `docs/INDEX.md`에 spec 항목을 추가:

```markdown
## Specs
- [YYYY-MM-DD-<topic>-design](specs/YYYY-MM-DD-<topic>-design.md): [authority] 설계 문서
```

기존 Specs 섹션이 있으면 항목 추가, 없으면 섹션 생성.

## 6. Spec Review Loop

Spec 작성 후:

1. `ezpowers:spec-reviewer` 플러그인 에이전트를 `subagent_type`으로 지정하여 디스패치. 동적 정보만 prompt로 전달:

   ```
   Agent tool:
     subagent_type: "ezpowers:spec-reviewer"
     description: "Review spec document"
     prompt: |
       **Spec to review:** <spec 파일의 절대 경로>
   ```

2. reviewer 결과는 `## Verdict: PASS` 또는 `## Verdict: FAIL` 헤더만 판정 기준으로 파싱. 다른 위치의 `PASS`/`FAIL` 문자열은 무시. **Verdict 헤더가 없거나 형식이 다르면:** `FAIL`로 간주하되, 2회 연속 Verdict 헤더 누락 시 사용자에게 에스컬레이션 ("Reviewer가 표준 형식으로 판정을 반환하지 않습니다.")
3. Issues Found -> 이슈 fix -> fresh 서브에이전트 재디스패치 (동일 프롬프트, 이전 리뷰 결과 전달 금지)
4. 비공개 이슈 로그 유지 (리뷰어와 공유하지 않음) — oscillation 감지용. 각 이슈를 `{section}:{check_number}` 키로 기록 (예: `R2:structural_completeness`, `R3:banned_expression`). 이것이 oscillation 매칭의 "category".
5. **Oscillation check (iteration 3부터):** 현재 이슈의 `{section}:{check_number}` 키가 2+ 이전 iteration에도 존재 -> 즉시 사용자 에스컬레이션
6. **Tiered escalation:** 3회 승인 없음 -> 사용자 경고. 5회 -> 중단.

## 7. 사용자 Spec 리뷰

Spec review loop 통과 후:

> "Spec을 `<path>`에 작성하고 커밋했습니다. 리뷰 후 변경 사항이 있으면 알려주세요."

사용자 승인 후 다음 단계: **`/plan`**

`phases/index.json` 업데이트:
- brainstorm: `status: "complete"`, `artifact: "<spec 파일 경로>"`, `completed_at: "<ISO 8601>"`
- plan: `status: "pending"` (변경 없음 확인)

## Common Rationalizations

| 핑계 | 현실 |
|------|------|
| "너무 단순해서 설계 불필요" | Anti-Pattern 섹션 참고. 설계는 짧을 수 있지만 존재해야 한다. |
| "뭘 만들어야 하는지 이미 안다" | 당신이 아는 것이고 사용자는 다를 수 있다. 명시적으로 확인한다. |
| "설계가 느리게 만든다" | 잘못 이해한 요구사항의 재작업은 10분 설계 대화보다 5-10배 느리다. |
| "질문 하나만 하고 시작" | 질문 하나 ≠ 이해. 사용자 답을 예측할 수 있을 때까지 묻는다. |
| "사용자가 급해하니 코드로" | 잘못된 코드 전달이 올바른 질문보다 느리다. |
| "컨텍스트에서 요구사항이 명백" | 누구에게 명백? 명시적으로 진술하고 확인받는다. |
| "엣지 케이스는 구현 중에" | 구현 중 발견되면 재설계. 지금 발견한다. |
| "spec이 상세해서 설계 불필요" | Spec은 WHAT, 설계는 HOW. 둘 다 필요. |

## Key Principles

- **한 번에 하나의 질문** — 여러 질문으로 압도하지 않는다
- **선택지 선호** — 가능하면 객관식, 열린 질문도 OK
- **YAGNI** — 불필요한 기능을 모든 설계에서 제거
- **대안 탐색** — 항상 2-3개 접근법 제안 후 결정
- **점진적 검증** — 설계 제시 후 승인받고 다음으로
- **유연하게** — 맞지 않으면 돌아가서 명확히

