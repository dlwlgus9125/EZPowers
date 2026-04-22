# Skill Authoring Best Practices (Anthropic Guide Summary)

> Anthropic 공식 스킬 작성 가이드의 핵심 요약.

## Core Principles

### 1. Concise is Key

컨텍스트 윈도우는 공공재. 스킬은 시스템 프롬프트, 대화 히스토리, 다른 스킬 메타데이터와 공간을 공유.

**Default assumption:** Claude는 이미 매우 똑똑하다. Claude가 모르는 컨텍스트만 추가.

- "이 설명이 정말 필요한가?"
- "Claude가 이미 아는 것 아닌가?"
- "이 문단이 토큰 비용을 정당화하는가?"

### 2. Set Appropriate Degrees of Freedom

| Freedom | When | Example |
|---------|------|---------|
| High | 여러 접근이 유효, 컨텍스트에 의존 | 코드 리뷰 프로세스 |
| Medium | 선호 패턴 존재, 약간의 변형 허용 | 파라미터가 있는 템플릿 |
| Low | 작업이 취약하고 오류 발생 가능 | DB 마이그레이션 스크립트 |

### 3. Test with All Models

- Haiku: 충분한 가이드 제공하는가?
- Sonnet: 명확하고 효율적인가?
- Opus: 과잉 설명이 아닌가?

## Skill Structure

### Naming

Gerund form 권장: "Processing PDFs", "Testing code", "Writing documentation"
피할 것: "Helper", "Utils", "Tools" 같은 모호한 이름

### Effective Descriptions

- 3인칭으로 작성 (시스템 프롬프트에 주입)
- 구체적이고 핵심 용어 포함
- 무엇을 하고 언제 사용하는지 모두 포함
- "Helps with documents" 같은 모호한 설명 금지

### Progressive Disclosure

- SKILL.md는 개요 + 상세 파일 포인터
- SKILL.md body는 500줄 이하
- 참조 파일은 SKILL.md에서 1-depth로 연결
- 100+ 줄 참조 파일은 목차 포함

## Workflows and Feedback Loops

- 복잡한 작업은 명확한 순차 단계로 분해
- 체크리스트 패턴으로 진행 추적
- 검증 -> 수정 -> 반복 피드백 루프

## Content Guidelines

- 시간에 민감한 정보 금지 (날짜 기반 분기 등)
- 일관된 용어 사용 (한 개념에 한 용어)
- 구체적 예시 (추상적이지 않게)

## Common Patterns

- **Template pattern:** 출력 형식 제공, 엄격도 맞춤
- **Examples pattern:** input/output 쌍 제공
- **Conditional workflow:** 분기점에서 가이드

## Anti-Patterns

- Windows 경로 (`\`) 금지 — 항상 forward slash
- 너무 많은 옵션 제시 금지 — 기본값 + escape hatch
- 도구 설치 가정 금지 — 의존성 명시
