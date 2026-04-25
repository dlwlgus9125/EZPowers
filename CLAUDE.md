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
/setup → /brainstorm → /plan → /choiceexecutor
```

| Command | 역할 |
|---------|------|
| `/setup` | 프로젝트 하네스 초기화 (config, steering 문서, agents.md) |
| `/brainstorm` | 대화형 설계 → spec + plan 문서 생성 |
| `/plan` | 설계문서 → step 분해 + 에이전트 배치 |
| `/choiceexecutor` | 실행 경로 선택 (서브에이전트 / 하네스 / 인라인) |
| `/executeharness` | EasyPowersHarness executor 위임 (plan → phase 변환 + step 실행) |

## Independent Utilities

| 이름 | 유형 | 역할 |
|------|------|------|
| `/review` | command | 변경사항 리뷰 (spec 대비 구현 완전성) |
| `/sync-docs` | command | 레퍼런스 문서를 코드베이스와 동기화 (독립 호출 + /choiceexecutor 완료 시 제안) |
| `/eval` | command | eval suite 실행, 버전별 점수 보고 |
| `/feedback` | command | 현재 세션 트레이스에 사용자 점수 부착 |
| `systematic-debugging` | skill | 근본 원인 추적 프로토콜 (4-Phase) |
| `verifyself` | skill | CoVe(Chain-of-Verification) 자기검증 (6차원) |
| `writing-skills` | skill | 새 스킬 작성 메타 스킬 (TDD 기반) |

## Directory Structure

```
.claude-plugin/       # plugin.json
commands/             # 슬래시 명령어 (setup, brainstorm, plan, choiceexecutor, executeharness, review, sync-docs, eval, feedback)
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
agents/               # 플러그인 에이전트 + 프롬프트 템플릿
  code-reviewer.md          # Plugin Agent — 최종 코드 리뷰 (inherit, Read/Grep/Glob/Bash)
  security-reviewer.md      # Plugin Agent — 보안 취약점 스캔 (inherit, Read/Grep/Glob/Bash)
  spec-reviewer.md          # Plugin Agent — Spec 문서 검증 (sonnet, Read/Grep/Glob)
  plan-reviewer.md          # Plugin Agent — Plan 문서 검증 (sonnet, Read/Grep/Glob)
  implementer-prompt.md     # Template — 구현 서브에이전트 (placeholder 치환 방식 유지)
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
phases/               # /executeharness가 생성하는 phase 디렉터리 (하네스 경로 선택 시)
hooks/
  hooks.json          # opt-in trace collection hooks (/setup --enable-traces로 활성화)
bin/
  trace.sh            # observation-only JSONL trace writer (hooks에서 호출)
```

## Key Conventions

- **스킬 체이닝 없음** — 각 스킬은 독립 호출, 필요하면 나중에 추가. Diagnostic subagent
  (`agents/eval-diagnostician.md`)는 유일한 예외로, `scripts/propose_edit.py`에서만 호출되며
  사용자 대면 커맨드에서는 호출되지 않는다.
- **훅: opt-in observation-only** — 기본 상태: 훅 없음. `/eval`, 베이스라인 측정, 회귀 추적이
  필요할 때 `/setup --enable-traces`로 활성화. 트레이스는 `${CLAUDE_PLUGIN_DATA}/traces/`에
  기록된다 (기본 gitignored). 훅은 모델 동작을 변경해서는 안 된다 — 관찰과 로깅만 허용.
  금지: 도구 입출력 변경, 도구 호출 차단, 시스템 명령 주입. 허용: append-only JSONL 쓰기.
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
