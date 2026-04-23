# /setup — 프로젝트 하네스 초기화

프로젝트에 EZPowers 하네스를 셋업한다. 설정 파일과 steering 문서 뼈대를 만드는 대화형 절차. 코드는 작성하지 않는다.

## Phase 1: 프로젝트 상태 판별

현재 작업 디렉터리를 읽고 기존/신규 프로젝트를 판단한다.

확인 항목:
1. 디렉터리 목록
2. 매니페스트 존재 여부 (package.json / Cargo.toml / pyproject.toml / go.mod 등)
3. 소스 디렉터리 존재 여부 (src/ / lib/ / app/)
4. `.harness/config.json` 존재 여부
5. `AGENTS.md` 존재 여부
6. `CLAUDE.md` 존재 여부

판별 규칙:
- `.harness/config.json`이 이미 있으면 → 덮어쓸지 사용자에게 묻는다
- 매니페스트 또는 소스 디렉터리가 있으면 → 기존 프로젝트
- 둘 다 없으면 → 신규 프로젝트

`phases/index.json`이 아직 없으면 즉시 생성하여 setup phase를 `in_progress`로 설정:
```json
{ "current_phase": "setup", "phases": { "setup": { "status": "in_progress" } } }
```

## Phase 2A: 기존 프로젝트 분석

기존 프로젝트라면 현재 상태를 분석한다.

읽을 것:
- 매니페스트 파일
- 상위 디렉터리 구조
- 기존 test/build/lint 스크립트
- `docs/` 내용
- `AGENTS.md`가 있으면 그 내용

사용자에게 요약:
```
Project: {name}
Stack: {추론값}
Test command: {추론값}
Build command: {추론값}
Lint command: {추론값}
Smoke command: {추론값 또는 빈 문자열}
Test strategy: {unit/integration/e2e 등}
```

모르는 값은 추측하지 않고 사용자에게 직접 묻는다.

## Phase 2B: 신규 프로젝트 설정

신규 프로젝트라면 대화를 통해 기본 설정을 만든다.

순서:
1. 프로젝트 이름과 한 줄 설명
2. 기술 스택
3. 테스트 전략
4. build/lint/test 명령
5. smoke.command 필요 여부
6. `/choiceexecutor`에 사용할 실행 방식 선호도 (서브에이전트 vs 하네스 vs 인라인)

가능하면 preset을 제안:
- Next.js + TypeScript
- Python + FastAPI
- Rust + CLI
- Library
- MCP server

## Phase 2.5: Executor 정보 확정

`/plan`이 step 크기 예산을 계산할 수 있도록 executor 정보를 반드시 받는다.

필수 값:
- `executor.agent` — 서브에이전트에 사용할 모델
- `executor.context_window` — 컨텍스트 윈도우 크기
- `executor.budget_ratio` — step당 허용 비율

권장 기본값:
```json
{
  "agent": "claude-sonnet-4-6",
  "context_window": 200000,
  "budget_ratio": 0.40
}
```

## Phase 2.7: 문서 거버넌스 확인

사용자에게 아래를 확인한다:

- "이 프로젝트의 canonical product document가 있습니까?" (있으면 경로 확인)
- "기존 아키텍처 문서가 있습니까?" (있으면 `docs/reference/`에 연결)
- "ADR(Architecture Decision Record)을 사용하시겠습니까?"
- "이 프로젝트에 UI가 있습니까?" (예이면 `docs/ux/` 슬롯 생성, 아니면 생략)

## Phase 3: 파일 생성

다음 파일을 만든다.

### 디렉터리 생성 (파일 생성 전)

파일을 생성하기 전에 필요한 디렉터리를 먼저 만든다:

```bash
mkdir -p .harness
mkdir -p phases
mkdir -p docs/product
mkdir -p docs/reference
mkdir -p docs/specs
mkdir -p docs/plans
```

ADR 사용 시: `mkdir -p docs/decisions`
UI 프로젝트: `mkdir -p docs/ux`

### 필수 파일

**`.harness/config.json`** — 프로젝트 설정 (전체 스키마는 아래 참고)

**`AGENTS.md`** — 에이전트 컨텍스트 문서:
```markdown
# {Project Name}
> {한 줄 설명}

## Steering
- spec location: docs/specs/
- plan location: docs/plans/

## Stack
{기술 스택 요약}

## Conventions
{프로젝트별 규칙 — 네이밍, 구조, 에러 처리 패턴 등}

## Boundaries
{변경 금지 영역, 외부 계약, 주의사항}

## Review Settings
review-skip: {리뷰 스킵할 파일 패턴 — 없으면 비워둠}
```

**`phases/index.json`** — phase 상태 추적:
```json
{
  "current_phase": "setup",
  "phases": {
    "setup": { "status": "complete", "completed_at": "2025-01-15T10:30:00Z" },
    "brainstorm": { "status": "pending", "artifact": null },
    "plan": { "status": "pending", "artifact": null },
    "build": { "status": "pending", "artifact": null }
  }
}
```

`status` 값: `pending` | `in_progress` | `complete` | `failed`
`artifact`: 해당 phase가 생성한 산출물 경로 (spec, plan 등). `complete` 시 필수.
`completed_at`: ISO 8601 타임스탬프. `complete` 시 필수.

**Backward transition 시:** 복귀 대상 phase를 `in_progress`로, 그 이후 phase들을 `pending`으로 리셋. artifact는 유지 (이전 산출물 참조용).

**`docs/INDEX.md`** — 문서 내비게이션 맵 (필수):
```markdown
# {Project Name}
> 프로젝트 한 줄 설명

## Product Contract
- [PRD](product/PRD.md): [canonical] 제품 요구사항 정의

## System Reference
- [Architecture](reference/architecture.md): [canonical] 시스템 아키텍처
- [Protocol](reference/protocol.md): [canonical] 프로토콜 계약
- [Schema](reference/schema.md): [canonical] DB 스키마
- [Config](reference/config.md): [canonical] 설정 계약

## Decisions
- [ADR Index](decisions/README.md): 아키텍처 결정 기록

## UX Spec (UI 프로젝트만)
- [UX Index](ux/README.md): UI 스펙 인덱스
```

### 문서 슬롯 (빈 파일 + frontmatter)

- `docs/product/PRD.md`
- `docs/reference/architecture.md`
- `docs/reference/protocol.md`
- `docs/reference/schema.md`
- `docs/reference/config.md`
- `docs/decisions/README.md` (ADR 사용 시)
- `docs/ux/README.md` (UI 프로젝트만)
- `docs/specs/.gitkeep` (spec 문서 저장 디렉터리)
- `docs/plans/.gitkeep` (plan 문서 저장 디렉터리)

### Frontmatter 스펙

모든 docs 슬롯에 3-field YAML frontmatter 포함:

```yaml
---
doc_type: reference
authority: canonical
status: draft
---

이 문서는 {주제}에 대한 SSOT(Single Source of Truth)입니다.
내용은 사람이 작성합니다.
```

`authority` 값: `canonical` (SSOT) / `supporting` (보조) / `derived` (자동 생성)

INDEX.md에 각 문서의 authority 마커를 `[canonical]`, `[supporting]`, `[derived]`로 표시한다.

### 기타 파일

- `CLAUDE.md` — 없으면 최소 가이드 생성

## config.json 스키마

```json
{
  "project": "my-project",
  "stack": ["next.js", "typescript", "react"],
  "test": {
    "command": "npm test",
    "strategy": "unit + e2e"
  },
  "build": {
    "command": "npm run build"
  },
  "lint": {
    "command": "npm run lint"
  },
  "smoke": {
    "command": "",
    "description": ""
  },
  "server": {
    "start_command": "",
    "stop_command": "",
    "health_check_url": "",
    "health_check_timeout": 15
  },
  "executor": {
    "agent": "claude-sonnet-4-6",
    "context_window": 200000,
    "budget_ratio": 0.40,
    "backend": "claude-code",
    "reviewer_backend": "claude-code"
  },
  "harness": {
    "root": ""
  },
  "defaults": {
    "spec_location": "docs/specs/",
    "plan_location": "docs/plans/",
    "max_retries": 3,
    "timeout": 1800,
    "auto_push": false,
    "prompt_logging": false,
    "verifier": "off",
    "verifier_max_rounds": 1
  }
}
```

필드 설명:
- `project`: 프로젝트 이름
- `stack`: 기술 스택 목록 (배열)
- `test.command`: 테스트 실행 명령
- `test.strategy`: 테스트 전략 설명 (unit, integration, e2e 등)
- `build.command`: 빌드 명령
- `lint.command`: 린트 명령
- `smoke.command`: 실제 엔트리포인트를 확인하는 smoke 명령
- `smoke.description`: smoke가 무엇을 검증하는지 설명
- `server.start_command`: Verify-type `api`/`e2e` 실행 전 서버 시작 명령 (빈 문자열이면 서버 관리 건너뜀)
- `server.stop_command`: Verify 완료 후 서버 종료 명령
- `server.health_check_url`: 서버 준비 확인 URL (예: `http://localhost:3000/health`)
- `server.health_check_timeout`: health check 최대 대기 시간 (초, 기본 15)
- `executor.agent`: `/choiceexecutor` 서브에이전트에 사용할 모델
- `executor.context_window`: 컨텍스트 윈도우 크기
- `executor.budget_ratio`: step당 허용 비율
- `executor.backend`: `/executeharness` 실행 백엔드 (`claude-code` | `codex-cli` | `openai-api`, 기본 `claude-code`)
- `executor.reviewer_backend`: verifier 서브에이전트 백엔드 (기본 `claude-code`)
- `harness.root`: EasyPowersHarness 설치 경로 (빈 문자열이면 `/executeharness` 경로 비활성)
- `defaults.spec_location`: spec 문서 저장 디렉터리
- `defaults.plan_location`: plan 문서 저장 디렉터리
- `defaults.max_retries`: step 재시도 횟수
- `defaults.timeout`: step timeout (초)
- `defaults.auto_push`: 완료 후 자동 push 여부
- `defaults.prompt_logging`: 프롬프트 로그 저장 여부
- `defaults.verifier`: `off` 또는 `sub-agent`
- `defaults.verifier_max_rounds`: verifier 최대 라운드 수

## Phase 4: 완료 안내

생성이 끝나면:
1. 만든 파일 목록
2. 사용자가 채워야 할 항목 (특히 AGENTS.md의 Conventions, Boundaries)
3. 다음 명령: `/brainstorm`
