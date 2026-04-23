# /executeharness — EasyPowersHarness 실행 위임

EasyPowersHarness의 Python executor(`scripts/execute.py`)를 통해 plan의 task를 step 단위로 실행한다.
이 커맨드는 thin wrapper이며, 실제 step 실행은 하네스의 Python executor가 담당한다.

<HARD-GATE>
execute.py를 EZPowers에 복사하지 않는다. 하네스 설치 경로를 참조하여 위임한다.
</HARD-GATE>

## 1. 사전 확인

다음을 먼저 확인한다:
1. `.harness/config.json`의 `harness.root` 필드에서 하네스 경로 확인
2. `{harness.root}/scripts/execute.py` 존재 여부
3. plan 문서 존재 여부
4. `phases/index.ezpowers.json` 잔존 여부 — 이전 하네스 실행이 비정상 종료되어 복원이 안 된 상태

`phases/index.ezpowers.json`이 존재하면:
> "이전 하네스 실행이 비정상 종료된 것으로 보입니다. `phases/index.ezpowers.json`에서 EZPowers index를 복원할까요?"
>
> 1. 복원 후 진행 — `phases/index.ezpowers.json` → `phases/index.json` 복원 후 백업 파일 삭제
> 2. 백업 폐기 후 진행 — `phases/index.ezpowers.json` 삭제, 현재 `phases/index.json`을 그대로 사용
>
> 어느 쪽이든 이전 백업 파일은 즉시 처리되므로, 이후 섹션 6(복원)에서 현재 세션의 백업과 충돌하지 않는다.

`harness.root`가 비어있거나 미설정:
> "`harness.root`가 설정되지 않았습니다. /setup에서 설정하거나, `/choiceexecutor`의 경로 1(서브에이전트) 또는 경로 3(인라인)을 사용하세요."

`execute.py` 미존재:
> "EasyPowersHarness가 `{harness.root}`에서 발견되지 않습니다. 경로를 확인하세요."

## 2. Git Hash 캡처

변환 시작 전 현재 커밋 해시를 기록한다:

```bash
git rev-parse HEAD
```

이 해시를 `<harness-start-hash>`로 저장. 실행 완료 후 Final Code Review의 diff 범위로 사용.
커밋 없는 상태: 빈 트리 해시 `4b825dc642cb6eb9a060e54bf899d8b2306e7304` 사용.

## 3. Plan → Phase 변환

plan 문서의 task를 하네스 step 파일로 변환한다.

### 3-1. Phase 디렉터리 생성

```bash
mkdir -p phases/{feature-name}
```

`{feature-name}`: plan 파일명에서 날짜 접두사를 제거한 kebab-case 이름.
예: `2026-04-22-user-auth.md` → `user-auth`

### 3-2. phase-context.md 생성

`phases/{feature-name}/phase-context.md`:

```markdown
# {Feature Name}

## Goal
{plan 헤더의 Goal 원문}

## Architecture
{plan 헤더의 Architecture 원문}

## Tech Stack
{plan 헤더의 Tech Stack}

## Spec
{spec 파일 경로}

## Constraints
{AGENTS.md의 Boundaries 섹션 — 있으면 복사, 없으면 생략}
```

### 3-3. Task → Step 필드 매핑

각 plan Task N을 `phases/{feature-name}/step{N-1}.md`로 변환한다 (하네스 executor가 0-indexed).

**번호 변환 규칙:** `Task N → step{N-1}.md` (예: Task 1 → step0.md, Task 2 → step1.md, Task 3 → step2.md)
`--reset-step` 인자도 0-indexed이므로, Task 3을 리셋하려면 `--reset-step 2`를 사용한다.

| EZPowers Plan Task 필드 | 하네스 Step 섹션 | 변환 규칙 |
|--------------------------|------------------|-----------|
| Task 제목 (`### Task N: [이름]`) | `# Step {N-1} (Task N): [이름]` | 번호 변환 + Task 번호 병기 |
| `**Files:**` (Create/Modify/Test) | `## 읽어야 할 파일` | Modify/Test 파일을 목록으로 |
| task 전체 텍스트 | `## 작업` | Impact scope, Depends on 포함하여 원문 복사 |
| `**Completion criteria (from spec):**` | `## Acceptance Criteria` | Given/When/Then/Verify 원문 복사 |
| `**Verification method:**` | `## Verification` | Verify 커맨드 복사 |
| Test 파일 경로 + 관련 문서 경로 | `## tools` | 파일 경로를 prompt 형식으로 나열 |
| 해당 없음 | `## 금지사항` | 생략 (없으면 섹션 자체 미생성) |

Step 파일 결과 구조:

```markdown
# Step {N-1} (Task N): {task name}

## 읽어야 할 파일
- `{Modify 파일 경로}`
- `{Test 파일 경로}`

## 작업
{task 전체 텍스트 원문}

## Acceptance Criteria
{Completion criteria 원문 — Given/When/Then/Verify 형식 그대로}

## Verification
{Verification method 원문}

## tools
- `{Test 파일 경로}`
- `{관련 spec/plan 경로}`
```

### 3-4. phases/{feature-name}/index.json 생성

하네스 executor 스키마를 따르는 index.json:

```json
{
  "project": "{config.project}",
  "phase": "{feature-name}",
  "created_at": "{ISO 8601}",
  "steps": [
    {
      "step": 0,
      "name": "{task 1 name}",
      "status": "pending",
      "step_md": "step0.md"
    },
    {
      "step": 1,
      "name": "{task 2 name}",
      "status": "pending",
      "step_md": "step1.md"
    }
  ]
}
```

### 3-5. 최상위 phases/index.json 보호

EZPowers의 `phases/index.json`과 하네스 executor의 최상위 index가 스키마 충돌을 일으킬 수 있다.

**보호 절차:**
1. 기존 `phases/index.json`을 `phases/index.ezpowers.json`으로 복사 (백업)
2. 하네스 실행 (하네스가 `phases/index.json`을 자유롭게 사용)
3. 실행 완료 후 `phases/index.ezpowers.json`에서 `phases/index.json` 복원
4. 복원된 EZPowers index의 build phase를 결과에 따라 업데이트

### 3-6. 변환 파일 커밋

```
chore: convert plan to harness phase — {feature-name}
```

## 4. Step-by-Step 실행

Bash tool 타임아웃(최대 600초) 제한 때문에 전체 phase를 한 번에 실행하지 않고, step 단위로 루프한다.

### 실행 루프

```
for each pending step:
  1. python "{harness_root}/scripts/execute.py" {feature-name}
     (executor는 첫 번째 pending step을 실행하고 종료)
     Bash timeout: 600000
  2. phases/{feature-name}/index.json 읽어서 방금 실행한 step 상태 확인
  3. 상태 매핑 + 보고
  4. error/blocked → 사용자 에스컬레이션, 루프 중단
  5. completed → 다음 step으로
```

### 상태 매핑

| 하네스 상태 | EZPowers 대응 | 의미 |
|-------------|---------------|------|
| `completed` | PASS | step 성공 |
| `error` | FAIL | step 실패 |
| `blocked` | BLOCKED | 사용자 개입 필요 |
| `rejected` | FAIL (verifier) | verifier가 거부 |
| `pending` | 미실행 | 아직 실행 안 됨 |

### 인자 지원

사용자가 `/executeharness`를 직접 호출할 때:

- `/executeharness {phase}` — pending step 순차 실행
- `/executeharness {phase} --status` — step 상태 표 출력 (foreground, Bash timeout: 30000)
- `/executeharness {phase} --reset-step N` — step N을 pending으로 리셋 (foreground, Bash timeout: 30000)
- `/executeharness {phase} --push` — 완료 후 자동 push

## 5. 실패 복구

step 실패 시 사용자에게 복구 경로 안내:

```
Step {N} 실패: {error 요약}

복구 방법:
1. 원인 수정
2. /executeharness {phase} --reset-step {N}
3. /executeharness {phase}
```

## 6. phases/index.json 복원

모든 step 완료 또는 중단 후:

1. `phases/index.ezpowers.json`에서 EZPowers 형식 `phases/index.json` 복원
2. build phase 상태 업데이트:
   - 전체 완료 → `complete` (Final Code Review 후)
   - 부분 실패 → `in_progress` 유지
3. `phases/index.ezpowers.json` 삭제

## 7. 결과 보고 + Final Code Review 연결

모든 step 완료 시:

1. step별 PASS/FAIL/BLOCKED 요약 출력
2. `git diff <harness-start-hash>..HEAD`로 전체 변경 확인
3. `/choiceexecutor`의 Final Code Review(섹션 12) 진행:
   - Plan 경로 제공
   - Diff range: `<harness-start-hash>..HEAD`
   - 하네스 실행 경로였음을 명시
