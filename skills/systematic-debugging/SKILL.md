---
name: systematic-debugging
description: Use when encountering any bug, test failure, or unexpected behavior, before proposing fixes
---

# Systematic Debugging

## Overview

Random fixes waste time and create new bugs. Quick patches mask underlying issues.

**Core principle:** ALWAYS find root cause before attempting fixes. Symptom fixes are failure.

**Violating the letter of this process is violating the spirit of debugging.**

## The Iron Law

```
NO FIXES WITHOUT ROOT CAUSE INVESTIGATION FIRST
```

Phase 1을 완료하지 않았으면 fix를 제안할 수 없다.

## When to Use

ANY technical issue:
- Test failures, bugs, unexpected behavior
- Performance problems, build failures
- Integration issues

**ESPECIALLY when:**
- 시간 압박 (급하면 추측이 유혹적)
- "빠른 fix 하나면 될 것 같은데"
- 이미 여러 fix를 시도한 상태
- 이슈를 완전히 이해하지 못함

**Don't skip when:**
- 이슈가 단순해 보일 때 (단순한 버그도 근본 원인이 있다)
- 급할 때 (체계적 디버깅이 추측보다 빠르다)

## The Four Phases

각 phase를 완료해야 다음으로 진행한다.

**Phase 완료 선언:** 각 phase 완료 시 다음 형식으로 명시적 선언 후 다음 phase에 진입한다:

```
✓ Phase N complete: [1줄 요약 — 발견한 것/확인한 것]
→ Entering Phase N+1
```

이 선언 없이 다음 phase의 활동을 시작하면 위반이다.

### Phase 1: Root Cause Investigation

**어떤 fix도 시도하기 전에:**

#### Step 0: Build a Feedback Loop

**이것이 핵심 스킬이다.** 나머지는 기계적이다. 빠르고, 결정적이고, 에이전트가 실행할 수 있는 pass/fail 신호가 있으면 원인을 찾을 수 있다. 없으면 코드를 아무리 봐도 해결되지 않는다.

**여기에 불균형한 노력을 투자한다. 공격적으로. 창의적으로. 포기를 거부한다.**

피드백 루프 구축 방법 (이 순서로 시도):

1. **Failing test** — 버그에 도달하는 seam에서 (unit/integration/e2e)
2. **Curl / HTTP script** — 개발 서버에 대해 실행
3. **CLI invocation** — fixture 입력으로 실행, known-good 스냅샷과 diff
4. **Headless browser script** — Playwright/Puppeteer로 UI 구동, DOM/console/network assert
5. **Replay captured trace** — 실제 네트워크 요청/페이로드/이벤트 로그를 디스크에 저장, 코드 경로에 격리 재생
6. **Throwaway harness** — 시스템의 최소 서브셋 (하나의 서비스, mocked deps)으로 버그 코드 경로를 단일 함수 호출로 실행
7. **Property / fuzz loop** — "가끔 잘못된 출력" → 1000개 랜덤 입력으로 실패 모드 탐색
8. **Bisection harness** — 두 알려진 상태 사이에서 나타난 버그 → `git bisect run` 자동화
9. **Differential loop** — 같은 입력을 old vs new (또는 두 설정)로 실행, 출력 diff
10. **HITL script** — 최후 수단. 사람이 클릭해야 하면, 구조화된 스크립트로 가이드하여 캡처된 출력을 피드백으로 받는다

**루프를 제품처럼 개선한다:**
- 더 빠르게? (설정 캐시, 불필요한 초기화 건너뛰기, 테스트 범위 축소)
- 신호를 더 선명하게? ("크래시 안 함"이 아닌 구체적 증상에 assert)
- 더 결정적으로? (시간 고정, RNG 시드, 파일시스템 격리, 네트워크 동결)

30초짜리 flaky 루프는 없는 것과 비슷. 2초짜리 결정적 루프가 디버깅 슈퍼파워.

**비결정적 버그:** 깨끗한 재현이 아닌 **높은 재현율**이 목표. 트리거를 100× 루프, 병렬화, 스트레스 추가, 타이밍 윈도우 축소, sleep 주입. 50% flake는 디버깅 가능; 1%는 불가 — 비율을 높여라.

**루프 구축 불가 시:** 명시적으로 중단하고 선언한다. 시도한 것을 나열한다. 사용자에게 요청: (a) 재현되는 환경 접근, (b) 캡처된 아티팩트 (HAR 파일, 로그 덤프, 코어 덤프, 스크린 레코딩), (c) 임시 프로덕션 계측 허가. 루프 없이 가설을 세우지 **않는다**.

---

1. **에러 메시지를 꼼꼼히 읽는다**
   - 스택 트레이스 전체를 읽는다
   - 라인 번호, 파일 경로, 에러 코드를 기록
   - 에러를 건너뛰지 않는다 — 정확한 해답이 들어있을 수 있다

2. **일관되게 재현한다**
   - 정확한 재현 스텝은?
   - 매번 발생하는가?
   - 재현 불가 -> 데이터를 더 모은다, 추측하지 않는다

3. **최근 변경을 확인한다**
   - `git diff`, 최근 커밋
   - 새 의존성, 설정 변경, 환경 차이

4. **멀티 컴포넌트 시스템에서 증거 수집**
   - 각 컴포넌트 경계에서 데이터 입출력을 로깅
   - 한 번 실행하여 어디서 깨지는지 증거 확보
   - 그 다음 해당 컴포넌트를 조사

5. **데이터 플로우 추적**
   - 잘못된 값이 어디서 시작되는가?
   - 콜 스택을 거슬러 올라가 소스를 찾는다
   - 증상이 아닌 소스에서 fix
   - 역추적 기법 상세: [root-cause-tracing.md](root-cause-tracing.md) 참조

#### Confusion Management

조사 중 모순된 정보가 나오면 명시적으로 표면화:

```
CONFUSION: [모순 설명]
- Evidence A: [소스A의 주장] (출처: [파일/로그])
- Evidence B: [소스B의 주장] (출처: [파일/로그])

Options:
  A) [소스A]를 신뢰 — [이유]
  B) [소스B]를 신뢰 — [이유]
  C) 추가 증거 필요 — [확인할 것]
```

사용할 때:
- 에러 메시지가 실제 동작과 모순 (예: "file not found" 인데 파일 존재)
- Spec과 코드가 불일치
- 두 로그가 같은 변수에 다른 상태 표시
- 스택 트레이스가 정상으로 보이는 라인을 가리킴
- 로컬 통과, CI 실패

규칙:
- 한쪽을 조용히 선택하지 않는다 — 충돌을 표면화
- 추가 증거로 해결할 수 있으면 먼저 시도 (Option C)
- 조사 옵션을 소진한 후에만 사용자에게 질문

### Phase 2: Pattern Analysis

**fix 전에 패턴을 찾는다:**

1. **같은 코드베이스에서 작동하는 유사 코드를 찾는다**
   - 깨진 것과 비슷하지만 작동하는 코드는?

2. **참조 구현이 있으면 완전히 읽는다**
   - 훑어보기 금지 — 모든 라인을 읽는다
   - 패턴을 완전히 이해한 후 적용

3. **작동하는 것과 깨진 것의 차이를 모두 나열**
   - 아무리 작은 차이도 나열
   - "이건 상관없을 거야" 가정 금지

4. **의존성, 설정, 환경 가정을 파악**
   - 다른 컴포넌트가 필요한가?
   - 어떤 설정, 환경을 가정하는가?

### Phase 3: Hypothesis and Testing

**과학적 방법:**

1. **단일 가설 수립**
   - "X가 근본 원인이라고 생각한다, 왜냐하면 Y"
   - 적어두고 구체적으로

2. **최소 변경으로 테스트**
   - 가능한 가장 작은 변경으로 가설 테스트
   - 한 번에 하나의 변수만
   - 여러 fix를 동시에 쌓지 않는다

3. **검증**
   - 성공 -> Phase 4
   - 실패 -> 새 가설 수립 (더 많은 fix 쌓지 않는다)

4. **모를 때**
   - "X를 모르겠다"고 인정
   - 아는 척하지 않는다
   - 도움을 요청하거나 더 조사

### Phase 4: Implementation

**증상이 아닌 근본 원인을 고친다:**

1. **실패하는 테스트 케이스 작성** (fix 전에)
   - 가장 단순한 재현
   - 자동화 테스트 가능하면 자동화
   - fix 전에 반드시 존재해야 함

2. **단일 fix 구현**
   - 식별된 근본 원인만
   - 한 번에 하나의 변경
   - "하는 김에" 개선 금지, 번들 리팩토링 금지

3. **fix 검증**
   - 테스트 통과하는가?
   - 다른 테스트 깨지지 않는가?
   - 이슈가 실제로 해결되었는가?

4. **3회 이상 fix 실패 시 — STOP**
   - 시도한 fix 수를 세어본다
   - **3회 이상: 아키텍처를 의심한다**
   - Fix #4를 아키텍처 논의 없이 시도하지 않는다

5. **아키텍처 문제 징후:**
   - 각 fix가 다른 곳에서 새 공유 상태/결합 문제를 드러낸다
   - fix에 "대규모 리팩토링"이 필요
   - 각 fix가 다른 곳에서 새 증상을 만든다
   - STOP하고 근본을 의문시한다: 패턴 자체가 건전한가? 관성으로 계속하고 있는가?
   - **사용자와 논의한 후 진행**

## Red Flags — STOP

이런 생각이 들면 Phase 1로 돌아간다:
- "일단 X를 바꿔보고 되나 보자"
- "빠르게 fix하고 나중에 조사하자"
- "여러 개를 한꺼번에 바꾸고 테스트하자"
- "테스트 건너뛰고 수동 검증하자"
- "아마 X일 거야, 고치자"
- "완전히 이해 못 했지만 이게 될 수 있을 것 같다"
- "패턴은 X라고 하지만 다르게 적용하겠다"
- "주요 문제들: [조사 없이 fix 나열]"
- 데이터 플로우 추적 전에 솔루션 제안
- **"하나만 더 시도해보자" (이미 2회 이상 시도했을 때)**
- **각 fix가 다른 곳에서 새 문제를 드러낸다**

**ALL of these mean: STOP. Return to Phase 1.**

**3+ fix 실패: 아키텍처를 의심한다 (Phase 4.5 참조)**

## Your Human Partner's Signals

이런 리다이렉션을 주시한다:
- "그거 안 되는 거 아냐?" — 검증 없이 가정했다
- "그게 보여줄까?" — 증거 수집을 추가했어야 한다
- "추측 그만" — 이해 없이 fix 제안 중
- "제대로 생각해봐" — 증상이 아닌 근본을 질문한다
- "우리 막힌 거야?" (좌절) — 접근법이 작동하지 않는다

**이런 신호가 오면: STOP. Phase 1으로.**

## Common Rationalizations

| 핑계 | 현실 |
|------|------|
| "단순한 이슈라 프로세스 불필요" | 단순한 이슈에도 근본 원인은 있다. 프로세스는 단순 버그에 빠르다. |
| "급해서 시간 없음" | 체계적 디버깅이 추측보다 빠르다. |
| "일단 하나 해보고 조사하자" | 첫 fix가 패턴을 정한다. 처음부터 제대로. |
| "테스트는 fix 확인 후에" | 테스트 없는 fix는 지속되지 않는다. |
| "여러 fix를 한 번에 하면 시간 절약" | 뭐가 효과 있었는지 분리 불가. 새 버그 유발. |
| "참조가 너무 길어, 패턴을 적당히 적용" | 부분적 이해가 버그를 보장. 완전히 읽는다. |
| "문제가 보인다, 고치자" | 증상 보기 ≠ 근본 원인 이해. |
| "하나만 더" (2+ 실패 후) | 3+ 실패 = 아키텍처 문제. 패턴을 의심, 다시 고치지 않는다. |

## Quick Reference

| Phase | Key Activities | Success Criteria |
|-------|---------------|------------------|
| **1. Root Cause** | 에러 읽기, 재현, 변경 확인, 증거 수집 | WHAT과 WHY를 이해 |
| **2. Pattern** | 작동 예시 찾기, 비교 | 차이 식별 |
| **3. Hypothesis** | 이론 수립, 최소 테스트 | 확인 또는 새 가설 |
| **4. Implementation** | 테스트 작성, fix, 검증 | 버그 해결, 테스트 통과 |

## When Process Reveals "No Root Cause"

체계적 조사가 이슈가 환경, 타이밍, 외부 원인임을 밝히면:

1. 프로세스를 완료한 것이다
2. 조사 내용을 문서화
3. 적절한 처리 구현 (재시도, 타임아웃, 에러 메시지)
4. 미래 조사를 위한 모니터링/로깅 추가

**But:** 95%의 "근본 원인 없음"은 불완전한 조사.

## Supporting Techniques

이 디렉터리에서 사용 가능:

- **`root-cause-tracing.md`** — 호출 스택 역추적으로 원래 트리거 찾기
- **`defense-in-depth.md`** — 근본 원인 발견 후 다층 검증 추가

## Real-World Impact

디버깅 세션 경험치:
- 체계적 접근: 15-30분에 fix
- 추측 접근: 2-3시간 삽질
- 첫 시도 fix 성공률: 95% vs 40%
- 새 버그 도입: 거의 0 vs 흔함
