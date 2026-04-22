# /build — 작업 실행

plan 문서의 task들을 실행한다. Fresh 서브에이전트 per task + 컨트롤러 AC 검증 + 조건부 보안 리뷰 + 최종 코드 리뷰.

## 1. 사전 확인

다음을 먼저 확인한다:
1. `.harness/config.json` 존재 여부
2. plan 문서 존재 여부 (우선순위: 인자 > `phases/index.json`의 plan.artifact > config의 `defaults.plan_location`에서 최신 파일)
3. plan이 참조하는 spec 문서 존재 여부

없으면 해당 단계를 먼저 실행하라고 안내:
- config 없음 -> `/setup`
- plan 없음 -> `/plan`
- spec 없음 -> `/brainstorm`

`phases/index.json`이 있으면 build phase를 `in_progress`로 업데이트:
```json
{ "current_phase": "build", "phases": { "...": "...", "build": { "status": "in_progress" } } }
```

## 2. 실행 경로 선택

사용자에게 실행 방식을 묻는다:

> **Plan: `<plan-path>` — {task-count}개 task**
>
> **1. 서브에이전트 드리븐 (추천)** — task마다 fresh 에이전트 배치, 빠른 반복
>
> **2. /executeharness (하네스 실행)** — EasyPowersHarness의 Python executor로 step 단위 실행 (`harness.root` 설정 필요)
>
> **3. 인라인 실행** — 현재 세션에서 순차 실행
>
> **어떤 방식으로 하시겠습니까?**

경로 2 선택 시 `commands/executeharness.md`의 절차를 따른다.

## 3. Task Graph Analysis

실행 전 task들의 의존 관계를 분석하여 실행 전략 결정.

### Step 1: Parse Dependencies

각 task에서 식별:
- **명시적 의존:** `Depends on: Task N` 마커
- **암시적 의존:** 같은 파일 수정 (`Modify:` 항목 매칭)
  - 암시적 의존 감지: 각 task의 `Modify:` 경로를 정규화(trailing slash 제거, 대소문자 통일)한 뒤 정확 문자열 비교. 부분 경로 매칭 없음.

### Step 2: Build Directed Graph

방향 그래프 구성: Task A -> Task B = "B가 A에 의존"

### Step 3: Classify Task Groups

| 분류 | 조건 | 실행 전략 |
|------|------|-----------|
| **독립 클러스터** | 그룹 내 의존 없음 | 순서 무관 순차 배치 |
| **선형 체인** | A->B->C 엄격 순서 | Pipeline (순차 실행) |
| **혼합** | 독립 + 체인 | 독립은 순서 무관, 체인은 순차 |

### Step 4: Execute by Classification

> **Note:** Claude Code의 Agent tool은 순차 실행만 지원한다. "독립"은 의존성 없는 task를 임의 순서로 실행할 수 있다는 의미이지, 동시에 배치한다는 뜻이 아니다.

- **독립 클러스터 (2+ 독립 task):** 순차 배치하되 순서 무관. 완료 후 per-task AC 검증 + 보안 리뷰.
- **Pipeline:** 엄격한 순차 동작.
- **단일 독립 task:** 순차 배치.

### Edge Cases

- 의존 마커 없고 서로 다른 파일 수정 -> 독립으로 취급
- **모든 task가 같은 파일 수정 -> 강제 순차**
- **순환 의존 감지:** 위상 정렬(topological sort) 수행. 모든 task를 방문하지 못하면 사이클 존재. 사이클에 포함된 task 목록을 사용자에게 경고하고 순차 fallback.
- **분석 불확실 -> 순차 fallback (안전)**

### Failure Handling

- **실패 전파:** task 실패 시, 해당 task에 의존하는 모든 하류 task를 `SKIPPED` 상태로 표기하고 실행하지 않음. 하류 task의 하류도 재귀적으로 SKIPPED.
- 한 task 3회 실패 -> 해당 task만 사용자 에스컬레이션
- 독립 task 실패가 다른 독립 task 차단 안 함
- **부분 실패 보고:** 실행 완료 시 PASS/FAIL/SKIPPED 상태를 task별로 요약하여 사용자에게 제시

## 4. Per-Task Execution Loop (서브에이전트 드리븐)

```
git hash 기록 (git rev-parse HEAD)
  -> Task 복잡도 평가
  -> 서브에이전트 배치 (agents/implementer-prompt.md)
  -> Implementer 상태 핸들링
  -> 컨트롤러: AC 검증 (Verify 커맨드 실행)
    -> ALL PASS -> 조건부 보안 리뷰
    -> FAIL -> 실패 상세와 함께 재배치 (최대 3회)
    -> 3회 실패 -> 사용자 에스컬레이션
  -> changed-files 계산 -> 다음 task
```

### Git Hash Recording

- **각 task 시작 전:** `git rev-parse HEAD` -> `<task-start-hash>` 저장
- **첫 task:** `<first-task-start-hash>`도 저장 (최종 리뷰용)
- **커밋 없는 상태:** `git rev-parse HEAD` 실패 시 빈 트리 해시 `4b825dc642cb6eb9a060e54bf899d8b2306e7304`를 사용. 이 해시는 git의 빈 트리를 나타내며 `git diff <empty-tree>..HEAD`로 전체 변경을 볼 수 있다.
- **각 task 완료 후:** changed-files = `git diff --name-only <task-start-hash>..HEAD` + `git ls-files --others --exclude-standard` (합집합, 중복 제거)

### Task Complexity Assessment

배치 전 3차원으로 복잡도 평가:

| Dimension | Low | Medium | High |
|-----------|-----|--------|------|
| **Scope** | 1-2 files, <50 lines | 3-5 files, 50-200 lines | 6+ files, 200+ lines |
| **Coupling** | 독립 파일 | 2-3 상호 의존 | 밀결합 모듈 |
| **Context breadth** | <5 files 읽기 | 5-10 files | 10+ files |

- **Simple** (전부 low): 그대로 배치
- **Medium** (2개 medium): 추가 컨텍스트와 함께 배치 — 아키텍처 노트, 인터페이스 계약, 의존성 설명 포함
- **Complex** (하나라도 high): 분할 추천

### Implementer Status Handling

- **DONE:** AC 검증 진행
- **DONE_WITH_CONCERNS:** 정확성 영향 시 먼저 처리, cosmetic이면 AC 검증 진행
- **BLOCKED:** 컨트롤러가 해결 (추가 컨텍스트, task 분할, 사용자 에스컬레이션). **절대 skip 금지**
- **NEEDS_CONTEXT:** 요청된 컨텍스트 포함하여 재배치

## 5. Acceptance Criteria Verification (컨트롤러)

**단위 테스트 통과는 완료 조건이 아니다.** 완료 판정은 반드시 plan의 Verify 커맨드를 실행하여 exit 0을 확인해야 한다.

**Primary verification — Verify 커맨드 실행:**

1. Task의 completion criteria에서 Verify 커맨드 추출
2. 각 Verify 커맨드 실행, exit code 확인 (exit 0 = PASS)
3. **Verify-type별 타임아웃:**
   - `pure` / `cli`: 30초
   - `e2e`: 120초
   - `api`: 30초
   - `data`: 60초

   **Bash tool timeout 매핑:**
   | Verify-type | 타임아웃 | Bash tool timeout 파라미터 |
   |-------------|----------|---------------------------|
   | `pure` / `cli` | 30초 | `timeout: 30000` |
   | `api` | 30초 | `timeout: 30000` |
   | `data` | 60초 | `timeout: 60000` |
   | `e2e` | 120초 | `timeout: 120000` |

4. **Server management (e2e/api):**
   - `config.server.start_command`가 비어있으면 서버 관리 건너뜀
   - 서버 시작: `config.server.start_command` 실행 (background)
   - Health check: `config.server.health_check_url`에 GET 요청 polling (최대 `config.server.health_check_timeout`초, 기본 15초)
   - Health check URL 미설정 시 5초 대기로 fallback
   - Verify 실행
   - 서버 종료: `config.server.stop_command` 실행 (미설정 시 시작한 프로세스 kill)
5. Verify 없는 기준: plan의 verification method로 fallback
6. ALL PASS -> 조건부 보안 리뷰
7. ANY FAIL -> 실패 상세와 함께 재배치

**Re-dispatch loop:** 최대 3회. 이후 사용자 에스컬레이션.

**Manual verification items:** 자동화 불가 시 사용자에게 배치 전달. 체인 차단 안 함.

## 6. Conditional Security Review

AC 검증 PASS 후 보안 리뷰 필요 여부 확인.

**트리거:** 다음 중 ANY가 true:
- Task 설명/요구사항에 보안 키워드 포함
- 변경 파일 내용에 보안 키워드 포함
- Task가 인증, 인가, 데이터 검증 로직 수정

**27개 Security Keywords:**
auth, login, password, token, secret, encrypt, decrypt, hash, session, cookie, permission, role, sanitize, escape, injection, CORS, CSRF, API key, credential, certificate, OAuth, JWT, bearer, privilege, access control, rate limit, brute force

**트리거됨:** `agents/security-reviewer-prompt.md` 기반 서브에이전트 배치
**트리거 안 됨:** 스킵. 로그: "Security review skipped — no security surface in Task N."

**False positive policy:** 의심되면 리뷰. 안전 > 효율.

**Security-spec conflict:** 보안 리뷰어가 spec과 충돌하는 이슈를 플래그하면 보안이 spec보다 우선. 로그: "Spec deviation: [description]. Security concern overrode spec requirement."

## 7. Review Loop Protocol

**Independent re-review:** 재디스패치 시 동일 프롬프트. 이전 결과 전달 금지.

**Controller issue log:** 비공개. iteration마다 이슈+fix 기록. 리뷰어와 공유 안 함.

**Oscillation detection (iteration 3부터):** 이슈를 `{file}:{issue_type}` 키로 로깅. 현재 키가 2+ 이전 iteration에도 존재 -> 사용자 에스컬레이션.

**Tiered escalation (통합 참조표):**

| Review type | Source | Max iterations | Warn at | Stop at |
|-------------|--------|----------------|---------|---------|
| Spec review | brainstorm.md | 5 | 3 | 5 |
| Plan review | plan.md | 5 | 3 | 5 |
| Implementer AC | build.md | 3 | — | 3 |
| Security review | build.md | 5 | 3 | 5 |
| Final code review | build.md | 10 | 5 | 10 |

모든 review type에서 Verdict 헤더 누락이 2회 연속 시 즉시 사용자 에스컬레이션.

**Exemption check:** 리뷰 루프 진입 전:
- `AGENTS.md`의 `review-skip:` 패턴?
- 사용자가 명시적으로 리뷰 스킵?
- Auto-excluded: lock files, generated, binary, git metadata, <20-line configs
- True이면 리뷰 루프 스킵.

**Large output handling:** 500-line diff 또는 10-file 초과 -> task 경계 또는 디렉터리로 분할 리뷰. 단일 파일 내 분할 금지. 모든 chunk PASS 필요.

## 8. Controller Context Hygiene

**서브에이전트 프롬프트 사이징:**
- Task 설명 + completion criteria는 원문 그대로 포함. 추가 컨텍스트(아키텍처 노트, 의존성 설명)는 ~2K tokens 이내
- **해당 task 텍스트와 completion criteria는 프롬프트에 직접 포함** (implementer-prompt.md 템플릿 참조)
- **전체 plan/spec 파일은 붙여넣지 않는다** — 경로만 제공, 서브에이전트가 필요 시 직접 읽음
- 소스 파일 내용을 미리 읽어서 프롬프트에 넣지 않는다 — 서브에이전트가 fresh context로 직접 읽음

**Between-task cleanup:**
- 각 task 완료 후 보존: task 상태(pass/fail), 변경 파일, 미해결 이슈만
- 서브에이전트 전체 출력, 리뷰 상세, 중간 추론 보존 안 함

**Context pressure relief:**
- Task 5 전: 압박 감지 시 컴팩트
- Task 5 후: 무조건 프로액티브 컴팩트
- **컴팩션 방법:** 컨트롤러는 자체 컨텍스트 윈도우를 직접 축소할 수 없다. "컴팩트"란 다음을 의미한다:
  1. 이후 출력에서 이전 서브에이전트 출력/리뷰 상세/중간 추론을 다시 언급하지 않는다
  2. 대신 아래 "작업 메모"만 참조하여 진행한다:
     - 남은 task 번호와 제목 목록
     - 지금까지 변경된 파일 목록 (누적)
     - 미해결 이슈 요약 (있으면)
     - 각 완료 task의 PASS/FAIL 상태
  3. Task 10 이후에도 세션이 계속되면 사용자에게 `/compact` 사용 또는 fresh 세션 시작을 제안한다

### Context Anchoring in Subagent Prompts

기존 파일 수정 task의 implementer 프롬프트에 포함:

> Before writing any code:
> 1. Read the module's AGENTS.md (if it exists)
> 2. Run `git log --oneline -10 [module-directory]`
> 3. Read related files until you can describe: (a) error handling pattern, (b) naming/structure pattern, (c) recent change direction
> 4. Output a 3-line pattern summary before proceeding

### Model Selection

- **Implementer:** 최고 코딩 모델
- **Security reviewer:** 분석 능력 필요한 모델
- **Final code reviewer:** 판단력 필요한 모델

### Parallel Reviewer Limit

3개 초과 `.md` 리뷰어 -> 순차 실행

### Subagent Dispatch — Placeholder 치환 목록

각 서브에이전트 디스패치 시 템플릿 placeholder를 반드시 치환:

**Implementer (`agents/implementer-prompt.md`):**
| Placeholder | 치환값 |
|-------------|--------|
| `[task name]` / `Task N` | 실제 task 번호와 이름 |
| `[FULL TEXT of task from plan]` | plan에서 해당 task 전문 복사 |
| `[Scene-setting...]` | 아키텍처 컨텍스트, 의존성, 선행 task 결과 |
| `[PASTE COMPLETION CRITERIA FROM PLAN]` | plan의 completion criteria 원문 |
| `[PASTE FROM PLAN]` | plan의 verification method 원문 |
| `[directory]` | 작업 디렉터리 절대 경로 |
| `[module-directory]` | 수정 대상 모듈 디렉터리 경로 |

**Security Reviewer (`agents/security-reviewer-prompt.md`):**
| Placeholder | 치환값 |
|-------------|--------|
| `[LIST OF CHANGED FILES WITH PATHS]` | `git diff --name-only <task-start-hash>..HEAD` 결과 |

**Code Reviewer (`agents/code-reviewer.md`):**
| Placeholder | 치환값 |
|-------------|--------|
| `[PLAN_FILE_PATH]` | plan 파일 절대 경로 |
| `[DIFF_RANGE]` | `<first-task-start-hash>..HEAD` |

**Post-substitution validation:** 디스패치 전 완성된 프롬프트에서 `[` + 대문자/소문자 + `]` 패턴 (예: `[SPEC_FILE_PATH]`, `[directory]`)을 검색. 미치환 placeholder가 남아있으면 디스패치하지 않고 누락된 placeholder를 로그하여 수정.

## 9. Degradation Detection and Response

**5개 감지 시그널:**
- Implementer가 같은 task에 NEEDS_CONTEXT 2회+
- 같은 이슈 카테고리가 여러 task에서 반복
- Implementer가 8+ 파일 읽기 self-report
- 3+ re-dispatch 사이클
- Task 5 이후 컴팩션 체크포인트 통과

**시그널 추출 규칙:**
- "NEEDS_CONTEXT 2회+" → 컨트롤러가 task별 NEEDS_CONTEXT 카운터 유지
- "같은 이슈 카테고리 반복" → 리뷰어 Issues의 `[severity]` 키워드를 카테고리로 분류, task 간 중복 체크
- "8+ 파일 읽기" → implementer report에서 "Files read:" 또는 "read N files" 패턴 매칭, 또는 self-report의 숫자 추출
- "3+ re-dispatch" → 컨트롤러가 task별 dispatch 카운터 유지
- "Task 5 이후 컴팩션" → task 완료 카운터 ≥ 5 시 트리거

**Response protocol:**
1. **Immediate:** 컨트롤러 컨텍스트 컴팩트
2. **Per-task:** 2회 배치 후 실패 시 복잡도 재평가 + 분할 고려
3. **Session-level:** 3+ task에서 degradation -> plan 분해 재검토
4. **Escalation:** 컴팩션+분할 후에도 지속 -> 상태 저장 + fresh 세션 제안

## 10. /executeharness Execution (경로 B)

사용자가 경로 2를 선택하면 `/executeharness` 커맨드로 위임한다.

1. `harness.root` 확인 → 미설정 시 사용자에게 안내
2. Git hash 캡처 (`git rev-parse HEAD` → `<harness-start-hash>`)
3. Plan → Phase 변환 (task를 stepN.md로, plan 헤더를 phase-context.md로)
4. `phases/{feature-name}/index.json` 생성 (하네스 스키마)
5. `phases/index.json` 보호 (EZPowers 형식 백업)
6. 변환 파일 커밋
7. Step-by-step 실행 (`execute.py` 호출 루프)
8. `phases/index.json` 복원 (EZPowers 형식)
9. 완료 시 → 섹션 12(Final Code Review)로 진행, diff range: `<harness-start-hash>..HEAD`

상세 절차는 `commands/executeharness.md` 참조.

## 11. Inline Execution (경로 C)

현재 세션에서 task를 순차적으로 실행한다.

각 task마다:
1. task 내용 읽기
2. TDD 순서로 구현 (테스트 -> 실패 확인 -> 구현 -> 통과 확인)
3. Verify 커맨드 실행
4. 커밋
5. 다음 task

## 12. Final Code Review

모든 task 완료 후 `agents/code-reviewer.md` 기반 서브에이전트 배치:

- Plan 경로 제공
- 전체 diff: `git diff <first-task-start-hash>..HEAD`
- 구현 요약
- `## Verdict: PASS` 또는 `## Verdict: FAIL` 출력 필요
- FAIL -> fix + fresh 재디스패치. warn@5, stop@10. Oscillation check from iteration 3.
- `## Verdict:` 패턴이 서브에이전트 반환에서 발견되지 않으면 FAIL로 처리하고 사용자에게 에스컬레이션: "Code reviewer가 표준 형식으로 판정을 반환하지 않았습니다."

## 13. Backward Transition: /plan으로 복귀

실행 중 plan 분해가 부적절하면 — task가 너무 밀결합, 의존성 누락, 경계 불일치 — 깨진 plan을 강행하지 않는다.

**트리거:**
- 2+ task가 같은 파일을 충돌하는 방식으로 수정
- task의 prerequisites가 plan에 누락
- task 순서 가정이 실제 코드베이스에서 오류
- 연속 2+ task가 구조적 이유로 BLOCKED

**액션:**
1. 이유 로그: "Returning to /plan: [구체적 이유]"
2. 사용자에게 보고
3. 현재 진행 저장:
   - 완료 task: plan 문서의 해당 task 체크박스(`- [x]`)를 체크하고 커밋
   - 미완 task: 체크박스 미체크 상태 유지, 재계획 대상으로 표시
   - `first-task-start-hash`를 plan 문서 헤더에 기록: `**Resume hash:** <first-task-start-hash>`
   - 커밋 메시지: `wip: build progress saved before /plan return — Tasks 1-N complete`
4. `phases/index.json` 업데이트: build를 `pending`으로, plan을 `in_progress`로 리셋
5. `/plan`으로 복귀하여 plan 수정
6. 업데이트된 plan으로 /build 재개

### Resume Protocol (plan 복귀 후 /build 재개 시)

1. Plan 문서에서 `**Resume hash:**` 마커 확인
2. 마커 있으면: 이전 `first-task-start-hash` 복원 (최종 리뷰 diff 범위 유지)
3. `- [x]`로 체크된 task는 PASS로 간주하고 스킵
4. `- [ ]`인 task만 실행 (새로 추가된 task 포함)
5. 스킵된 task의 artifact(커밋)는 이미 존재하므로 의존성 충족으로 간주
6. **주의:** plan이 기존 완료 task의 파일을 재수정하도록 변경했으면, 해당 task를 수동으로 `- [ ]`로 리셋해야 함 — /plan에서 사용자에게 안내

## 14. 완료

모든 task + final review 완료 후:
1. 전체 diff 요약 (`git diff <first-task-start-hash>..HEAD`)
2. 완료/실패/SKIPPED task 목록
3. 다음 추천: `/review`
`phases/index.json` 업데이트:
- build: `status: "complete"`, `completed_at: "<ISO 8601>"`
