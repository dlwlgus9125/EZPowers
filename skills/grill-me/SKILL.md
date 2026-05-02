---
name: grill-me
description: Stress-test a plan or design through relentless questioning until shared understanding is reached. Use when user says "grill me", wants to stress-test a plan, challenge assumptions, or validate design decisions before implementation.
---

# Grill Me

사용자의 계획/설계를 공유된 이해에 도달할 때까지 집요하게 인터뷰한다.

## Process

결정 트리의 모든 가지를 하나씩 걸어간다. 의존 관계가 있는 결정은 순서대로 해결한다.

**Rules:**

1. **한 번에 하나의 질문만** — 여러 질문을 한꺼번에 던지지 않는다
2. **각 질문에 추천 답변 제시** — 빈 질문 금지, 근거 있는 제안과 함께
3. **코드베이스 탐색으로 답할 수 있으면 탐색** — 사용자에게 묻기 전에 코드를 확인
4. **피드백을 기다린 후 다음으로** — 사용자 응답 없이 진행하지 않는다

## What to Challenge

- **모호한 용어** — "적절히", "필요하면", "등등" → 구체적 정의 요구
- **숨은 가정** — 명시되지 않은 전제를 표면화
- **엣지 케이스** — 정상 경로만 다룬 설계에 예외 시나리오 투척
- **대안 미검토** — "왜 X가 아닌 Y인가?" 첫 아이디어 고착 방지
- **의존성 순서** — A를 결정하지 않으면 B를 결정할 수 없는 관계 식별
- **스코프 경계** — 포함/제외 기준이 명확한지

## Completion

모든 결정 가지가 해결되고 사용자가 만족을 표현하면 종료. 인위적 종료 강제 없음.
