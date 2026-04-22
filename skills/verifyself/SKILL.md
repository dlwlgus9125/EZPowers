---
name: verifyself
description: Use when the user wants to verify the agent's own proposal or judgment
---

# Verifyself

## Overview

CoVe(Chain-of-Verification) 패턴으로 에이전트 자신의 제안/판단을 검증한다. 주관적 자기평가 대신 구체적 검증 질문을 생성하고 독립적으로 답변한 뒤 원래 제안과 비교한다.

**Core principle:** "이 사실이 맞는가?"는 답할 수 있다. "충분히 깊이 생각했는가?"는 답할 수 없다. 후자를 전자로 변환한다.

## When to Use

- `/verifyself` 호출 시
- `/verifyself [target]` — 특정 대상 지정 시

## Step 1: 검증 대상 확인

**인자 있음:** 인자를 대상으로 사용 (파일 경로면 읽기, 텍스트면 직접 사용)
**인자 없음:** 현재 대화에서 가장 최근 제안/판단을 대상으로 사용. "제안/판단"이란: 코드 블록으로 제시된 구현, 설계/아키텍처 제안, 의사결정 추천, 분석 결론 중 가장 최근 것. 단순 질문이나 정보 요청은 제외.

대상을 사용자에게 보여준다:
```
Verification target:
---
[대상 내용]
---
```

## Step 2: 대상 유형 분류

| Type | Indicators |
|------|-----------|
| **code** | 구현, 리팩토링, 버그 fix, 코드 설계 |
| **document** | spec, plan, 설계 문서, 아키텍처 |
| **judgment** | 추천, 결정, 분석, 의견 |

애매하면 "judgment"로 기본 분류.

## Step 3: 6차원 검증 질문 생성

각 차원에서 1-2개 검증 질문을 생성한다.

### 1. Exploration Depth — 검증된 사실인가, 확인하지 않은 가정인가?
- code: "이 함수가 실제로 [가정]한 대로 동작하는가?"
- document: "참조한 문서가 실제로 [주장]을 명시하는가?"
- judgment: "이 주장의 전제 [X]가 사실인가?"

### 2. Impact Scope — 영향받는 모든 것을 고려했는가?
- code: "변경된 컴포넌트를 의존하는 다른 파일/모듈은?"
- document: "이 문서를 참조하는 다른 문서는?"
- judgment: "이 판단이 영향을 미치는 다른 영역은?"

### 3. Alternative Consideration — 첫 번째 아이디어를 바로 채택하지 않았는가?
- code: "다른 접근법으로 해결할 수 있는가?"
- document: "다른 구조가 가능한가?"
- judgment: "이 입장에 대한 가장 강력한 반론은?"

### 4. Temporal Perspective — 시간이 지나도 괜찮은가?
- code: "하드코딩/강결합/가정이 미래에 바뀌어야 하지 않을까?"
- document: "요구사항이 확장되면 이 구조가 수용하는가?"
- judgment: "인정하지 않은 미래 제약을 만들지 않는가?"

### 5. Context Alignment — 프로젝트에 맞는가, 진공 속 설계가 아닌가?
- code: "같은 모듈의 인접 파일이 동일 패턴을 따르는가?"
- document: "프로젝트의 기존 문서 규약을 따르는가?"
- judgment: "프로젝트의 확립된 방향과 일관되는가?"

### 6. Evidence Sufficiency — 핵심 주장이 검증 가능한 사실에 기반하는가?
- code: "핵심 주장 [X]를 코드베이스에서 검증할 수 있는가?"
- document: "참조한 문서가 실제로 존재하고 주장된 내용을 포함하는가?"
- judgment: "주장 [X]의 출처/근거가 검증 가능한가?"

해당 없는 차원: "N/A — [이유]"로 표기하고 다음으로.

## Step 4: 각 질문에 독립 답변

각 검증 질문에 대해:
1. **원래 제안의 결론을 참조하지 않는다** — 질문과 증거만으로 판단
2. code 질문: 파일 읽기, grep으로 증거 수집
3. document 질문: 참조 문서를 직접 열어 확인
4. judgment 질문: 검증 가능한 사실과 논리로 추론
5. 답변 불가: "Unverifiable — 제안에 증거 없음"

## Step 5: 비교 + 판정

| Verdict | 조건 |
|---------|------|
| **FAIL** | 독립 답변이 제안과 사실적 불일치를 발견 |
| **CONCERN** | 제안에 언급되지 않은 중요한 사실 발견 |
| **PASS** | 불일치나 중요 누락 없음 |

불확실하면 CONCERN (PASS가 아님).

## Step 6: 보고서 출력

```
## Verifyself Report

### 1. Exploration Depth
- Question: [질문]
- Answer: [독립 답변 + 증거]
- Verdict: PASS | CONCERN | FAIL
- Evidence: [구체적 파일:라인, 문서 섹션, 사실 근거]

### 2. Impact Scope
...

### 3. Alternative Consideration
...

### 4. Temporal Perspective
...

### 5. Context Alignment
...

### 6. Evidence Sufficiency
...

### Summary
- FAIL: N건
- CONCERN: N건
- PASS: N건
```

규칙:
- 6개 차원 모두 고정 순서로 포함 (N/A 포함)
- Evidence에 "seems correct", "likely fine" 금지 — 구체적 사실만

## Step 7: 수정

**전부 PASS:** 보고서만 출력. 수정 없음.

**FAIL 또는 CONCERN 있음:**
1. FAIL: 검증에서 발견한 사실에 맞게 제안 수정
2. CONCERN: 누락된 정보를 보충
3. PASS: 원본 유지

```
---
Revised proposal:
---
[수정된 내용]
---
```

## After Verification

사용자 응답을 기다린다:
- **승인** → 검증 완료, (수정된) 제안으로 진행
- **`/verifyself` 재호출** → 수정된 제안에 대해 재검증
- **피드백** → 피드백에 직접 대응 (6차원 재실행 불필요)
