---
name: writing-skills
description: Use when creating new skills, editing existing skills, or verifying skills work before deployment
---

# Writing Skills

## Overview

**스킬 작성은 프로세스 문서에 적용하는 TDD다.**

**Core principle:** 스킬 없이 에이전트가 실패하는 것을 관찰하지 않았으면, 스킬이 올바른 것을 가르치는지 모른다.

**Official guidance:** Anthropic 공식 가이드는 [anthropic-best-practices.md](anthropic-best-practices.md) 참조.

## What is a Skill?

**Skill:** 검증된 기법, 패턴, 도구에 대한 참조 가이드.

- **Skills are:** 재사용 가능한 기법, 패턴, 도구, 참조
- **Skills are NOT:** 한 번 문제를 해결한 과정의 서사

## TDD Mapping for Skills

| TDD Concept | Skill Creation |
|-------------|----------------|
| **Test case** | 서브에이전트 pressure scenario |
| **Production code** | 스킬 문서 (SKILL.md) |
| **Test fails (RED)** | 에이전트가 스킬 없이 규칙 위반 (baseline) |
| **Test passes (GREEN)** | 스킬 있으면 에이전트 준수 |
| **Refactor** | 허점 봉쇄하면서 compliance 유지 |
| **Write test first** | 스킬 작성 전에 baseline scenario 실행 |
| **Watch it fail** | 에이전트 핑계를 원문 그대로 기록 |
| **Minimal code** | 구체적 위반에 대응하는 최소 스킬 작성 |
| **Watch it pass** | 에이전트가 이제 준수하는지 확인 |
| **Refactor cycle** | 새 핑계 -> 대응 -> 재확인 |

## Skill Types

| Type | 설명 | 예시 |
|------|------|------|
| **Technique** | 단계가 있는 구체적 방법 | systematic-debugging |
| **Pattern** | 문제에 대한 사고 방식 | flatten-with-flags |
| **Reference** | API 문서, 문법, 도구 참조 | office docs |

## Directory Structure

```
skills/
  skill-name/
    SKILL.md              # 메인 참조 (필수)
    supporting-file.*     # 필요할 때만
```

### File Organization Patterns

**Self-contained** — 모든 내용이 SKILL.md에 인라인:
```
defense-in-depth/
  SKILL.md    # Everything inline
```
When: 내용이 짧고 별도 참조 불필요

**With reusable tool** — 재사용 가능한 스크립트/유틸리티:
```
condition-based-waiting/
  SKILL.md    # Overview + patterns
  example.ts  # Working helpers to adapt
```
When: 도구가 재사용 가능한 코드

**With heavy reference** — 100+ 라인 참조 자료:
```
pptx/
  SKILL.md       # Overview + workflows
  pptxgenjs.md   # 600 lines API reference
  scripts/       # Executable tools
```
When: 참조가 인라인하기에 너무 큼

## SKILL.md Structure

### Frontmatter (YAML)

- `name`: 문자, 숫자, 하이픈만 (특수문자 금지)
- `description`: 3인칭, "Use when..." 시작, 트리거 조건만 기술
  - **절대 스킬의 워크플로우/프로세스를 요약하지 않는다** (CSO 참조)

```markdown
---
name: skill-name
description: Use when [specific triggering conditions]
---

# Skill Name

## Overview
핵심 원칙 1-2 문장.

## When to Use
증상/상황 목록. 사용하지 않을 때 포함.

## Core Pattern
Before/after 비교 또는 핵심 플로우.

## Quick Reference
빠른 스캔용 표 또는 목록.

## Common Mistakes
자주 틀리는 것 + 해결.
```

## Claude Search Optimization (CSO)

### Layer 1: Description Field Rules

- 1-2 sentences, <120 words
- "Use when..." 시작
- 트리거 조건과 검색 가능 키워드만
- 워크플로우 단계, 출력, 프로세스 동사 나열 제외
- 선택적으로 "Not for..." 안티트리거 추가
- **CSO self-test:** description만 읽고 스킬 워크플로우를 시도할 수 있으면 -> 다시 쓴다

```yaml
# BAD: 워크플로우 요약 — Claude가 본문 대신 이것만 따를 수 있음
description: Use when executing plans - dispatches subagent per task with code review

# GOOD: 트리거 조건만
description: Use when executing implementation plans with independent tasks
```

**왜 중요:** description이 워크플로우를 요약하면 Claude가 본문 대신 description을 따르는 단축 경로를 만든다.

### Keyword Coverage

Claude가 검색할 단어를 사용:
- 에러 메시지: "Hook timed out", "ENOTEMPTY", "race condition"
- 증상: "flaky", "hanging", "zombie", "pollution"
- 동의어: "timeout/hang/freeze", "cleanup/teardown/afterEach"
- 도구: 실제 커맨드, 라이브러리, 파일 타입

### Naming

- 능동태, 동사 우선: `creating-skills` (not `skill-creation`)
- 제네릭 이름 금지: `condition-based-waiting` (not `async-test-helpers`)
- Gerund (-ing)가 프로세스에 잘 맞음

### Cross-Referencing Rules

```markdown
# GOOD: 요구 마커 + 스킬 이름만
**REQUIRED SUB-SKILL:** Use test-driven-development
**REQUIRED BACKGROUND:** You MUST understand systematic-debugging

# BAD: 경로로 참조 — 불명확
See skills/testing/test-driven-development

# BAD: @ 링크 — 즉시 로드되어 컨텍스트 낭비
@skills/testing/test-driven-development/SKILL.md
```

**@ 링크 금지 이유:** `@` 문법은 파일을 즉시 로드하여 필요 전에 컨텍스트 예산을 소비.

### Token Efficiency

| Skill type | Target |
|-----------|--------|
| 자주 로드되는 스킬 | <200 words |
| 기타 | <500 words |

기법: 상세는 `--help`로 위임, 교차 참조로 중복 제거, 예제는 하나만 훌륭하게.

## Flowchart Usage

**사용할 때:**
- 명확하지 않은 결정 포인트
- 너무 일찍 멈출 수 있는 프로세스 루프
- "A vs B 언제 사용" 결정

**사용하지 않을 때:**
- 참조 자료 -> 표/목록
- 코드 예시 -> 마크다운 블록
- 선형 지시 -> 번호 목록

## Code Examples

**하나의 훌륭한 예시 > 여러 평범한 예시**

언어 선택 가이드:
- 테스트 기법 -> TypeScript/JavaScript
- 시스템 디버깅 -> Shell/Python
- 데이터 처리 -> Python

좋은 예시: 완전하고 실행 가능, WHY를 설명하는 주석, 실제 시나리오에서 추출.
나쁜 예시: 5+ 언어 구현, 빈칸 채우기 템플릿, 인위적 예시.

## RED-GREEN-REFACTOR for Skills

### RED: 스킬 없이 테스트

서브에이전트로 pressure scenario를 스킬 없이 실행:
- 어떤 선택을 했는가?
- 어떤 핑계를 댔는가? (원문 그대로 기록)
- 어떤 압박이 위반을 유발했는가?

### GREEN: 최소 스킬 작성

RED에서 발견한 구체적 위반에 대응하는 최소 문서 작성. 재실행 -> 에이전트가 준수해야 함.

### REFACTOR: 허점 봉쇄

새 핑계 발견 -> 명시적 반박 추가. 재테스트. 견고해질 때까지 반복.

**Testing methodology:** [testing-skills-with-subagents.md](testing-skills-with-subagents.md) 참조.

## Testing All Skill Types

### Discipline-Enforcing Skills (규칙/요구사항)

**Test with:**
- 학술 질문: 규칙을 이해하는가?
- 압력 시나리오: 스트레스 하에 준수하는가?
- 복합 압력: 시간 + 매몰 비용 + 피로 결합

**Success:** 최대 압력 하에 규칙 준수

### Technique Skills (방법론)

**Test with:**
- 적용 시나리오: 기법을 올바르게 적용?
- 변형 시나리오: 엣지 케이스 처리?
- 정보 부족 테스트: 지시에 갭이 있는가?

**Success:** 새 시나리오에 기법 성공 적용

### Pattern Skills (사고 모델)

**Test with:**
- 인식 시나리오: 패턴 적용 시점 인식?
- 적용 시나리오: 멘탈 모델 사용 가능?
- 반례: 적용하지 않을 때를 아는가?

**Success:** 올바른 적용 시점/방법 식별

### Reference Skills (문서/API)

**Test with:**
- 검색 시나리오: 올바른 정보를 찾는가?
- 적용 시나리오: 찾은 것을 올바르게 사용?
- 갭 테스트: 일반 사용 사례 커버?

**Success:** 참조 정보를 올바르게 찾고 적용

## Bulletproofing Against Rationalization

### Close Every Loophole Explicitly

규칙만 말하지 말고 구체적 우회를 금지:

```markdown
코드를 테스트 전에 작성했으면? 삭제한다. 처음부터.

**예외 없음:**
- "참고용"으로 남기지 않는다
- 테스트 작성하면서 "수정"하지 않는다
- 삭제는 삭제다
```

### "Spirit vs Letter" 대응

```markdown
**Violating the letter of the rules is violating the spirit of the rules.**
```

"정신을 따르고 있다" 류의 전체 핑계 클래스를 차단.

### Rationalization Table 구축

baseline 테스트에서 캡처한 모든 핑계를 테이블에:

```markdown
| 핑계 | 현실 |
|------|------|
| "너무 단순해서 테스트 불필요" | 단순한 코드도 깨진다. 테스트 30초. |
| "나중에 테스트" | 나중에 통과하는 테스트는 아무것도 증명 안 함. |
```

### Red Flags 목록 구축

```markdown
## Red Flags — STOP
- 테스트 전에 코드 작성
- "이미 수동 테스트했음"
- "정신을 따르는 거지 규칙을 따르는 게 아니다"
- "이건 다른데..."
-> 전부: 삭제하고 처음부터.
```

## Anti-Patterns

### Narrative Example
"2025-10-03 세션에서 빈 projectDir가..." — 너무 구체적, 재사용 불가

### Multi-Language Dilution
example-js.js, example-py.py — 평범한 품질, 유지보수 부담

### Code in Flowcharts
`step1 [label="import fs"]` — 복사 불가, 읽기 어려움

### Generic Labels
helper1, step3, pattern4 — 의미 있는 이름이어야 함

## Common Rationalizations

| 핑계 | 현실 |
|------|------|
| "스킬이 명백히 명확" | 당신에게 명확 ≠ 에이전트에게 명확. 테스트. |
| "참조일 뿐" | 참조도 갭이 있다. 검색 테스트. |
| "테스트는 과잉" | 미테스트 스킬에는 항상 이슈. 15분이 수시간 절약. |
| "문제 생기면 테스트" | 문제 = 에이전트가 못 씀. 배포 전 테스트. |
| "지루한 테스트" | 프로덕션에서 나쁜 스킬 디버깅이 더 지루. |
| "확신이 있다" | 과신이 이슈를 보장. 어쨌든 테스트. |
| "학술 리뷰면 충분" | 읽기 ≠ 사용. 적용 시나리오 테스트. |
| "테스트할 시간 없다" | 미테스트 배포가 나중에 더 많은 시간 낭비. |

## STOP: Before Moving to Next Skill

스킬 작성 후 반드시 배포 프로세스를 완료한다.

**하지 않을 것:**
- 테스트 없이 여러 스킬 배치 생성
- 현재 스킬 검증 전 다음 스킬로 이동
- "배칭이 효율적"이라고 테스트 건너뛰기

## Checklist

**RED Phase:**
- [ ] Pressure scenario 생성 (discipline 스킬: 3+ 복합 압력)
- [ ] 스킬 없이 실행 — baseline 문서화
- [ ] 핑계/실패 패턴 식별

**GREEN Phase:**
- [ ] Frontmatter: name + description (max 1024 chars)
- [ ] Description: "Use when..." 시작, 트리거만, 워크플로우 요약 없음
- [ ] 구체적 baseline 실패에 대응하는 최소 스킬
- [ ] 스킬과 함께 재실행 — 에이전트 준수 확인

**REFACTOR Phase:**
- [ ] 새 핑계 식별
- [ ] 명시적 대응 추가
- [ ] 핑계 테이블 + Red Flags 업데이트
- [ ] 재테스트 — 견고해질 때까지

**Quality:**
- [ ] 키워드 커버리지 (에러, 증상, 도구)
- [ ] 커밋
