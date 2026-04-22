# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Identity

EZPowers는 개인 전용 Claude Code 스킬 플러그인.
- 소스 프로젝트 2개를 참고하되 **새로 구성** (그대로 복사하지 않음)
  - `C:\Working\EasyPowersHarness` (v0.7.7) — 하네스/실행 구조 참고
  - `C:\Working\EasyPowers` (v3.1.5) — 스킬 패턴 참고
- SDD(Spec-Driven Development) 기반: 사람은 설계와 리뷰, 에이전트는 구현

## Main Flow

```
/setup → /brainstorm → /plan → /build
```

| Command | 역할 |
|---------|------|
| `/setup` | 프로젝트 하네스 초기화 (config, steering 문서, agents.md) |
| `/brainstorm` | 대화형 설계 → spec + plan 문서 생성 |
| `/plan` | 설계문서 → step 분해 + 에이전트 배치 |
| `/build` | 작업 실행 (서브에이전트 or 하네스 실행 선택) |

## Independent Utilities

| 이름 | 유형 | 역할 |
|------|------|------|
| `/review` | command | 변경사항 리뷰 (spec 대비 구현 완전성) |
| `systematic-debugging` | skill | 근본 원인 추적 프로토콜 (4-Phase) |
| `verifyself` | skill | CoVe(Chain-of-Verification) 자기검증 (6차원) |
| `writing-skills` | skill | 새 스킬 작성 메타 스킬 (TDD 기반) |

## Directory Structure

```
.claude-plugin/       # plugin.json
commands/             # 슬래시 명령어 (setup, brainstorm, plan, build, review)
skills/               # 독립 스킬
  systematic-debugging/
    SKILL.md          # 4-Phase 디버깅 프로토콜
    root-cause-tracing.md
    defense-in-depth.md
  verifyself/
    SKILL.md          # CoVe 자기검증 (6차원)
  writing-skills/
    SKILL.md          # 스킬 작성 메타 스킬 (TDD 기반)
    anthropic-best-practices.md
    testing-skills-with-subagents.md
agents/               # 에이전트 서브에이전트 프롬프트
  code-reviewer.md
  implementer-prompt.md
  security-reviewer-prompt.md
  spec-document-reviewer-prompt.md
  plan-document-reviewer-prompt.md
phases/               # /setup이 생성하는 phase 상태 추적
docs/
  INDEX.md            # /setup이 생성하는 문서 내비게이션 맵
  product/            # PRD 등 제품 문서 슬롯
  reference/          # 아키텍처, 프로토콜, 스키마, 설정 슬롯
  decisions/          # ADR (선택적)
  ux/                 # UI 프로젝트만 (선택적)
  specs/              # /brainstorm이 생성하는 spec 문서
  plans/              # /plan이 생성하는 plan 문서
  handoff-session1.md
  handoff-session2.md
```

## Key Conventions

- **스킬 체이닝 없음** — 각 스킬은 독립 호출, 필요하면 나중에 추가
- **훅 없음** — 필요해지면 그때 추가
- **문서는 가볍게** — 어떤 에이전트가 와도 맥락을 이해할 수 있도록 필요한 곳에 배치
- **증거 기반 검증** — "should work" 금지, 실행 결과로 증명
- **가정 명시** — 설계/플래닝 전 가정을 선언하고 사용자 확인

## Versioning

`git push` 전에 반드시 `.claude-plugin/plugin.json`의 `version` 필드를 patch 범프.
- 커밋 메시지: `chore: bump version to X.Y.Z`
- minor/major는 사용자 명시 요청 시에만

## Design Principles

1. **기존 구조에 매몰되지 않는다** — 소스 프로젝트는 참고 자료, 새로운 플로우 설계
2. **YAGNI** — 당장 필요하지 않으면 만들지 않는다
3. **한 번에 하나의 질문** — brainstorm에서 사용자를 압도하지 않는다
4. **Steering** — /setup이 프로젝트 컨텍스트를 모든 단계에 자동 주입할 문서 생성
