# OMO OpenAgent 활용 가능성 분석

분석일: 2026-05-19
분석 대상: `https://github.com/code-yeongyu/oh-my-openagent`
로컬 클론: `C:\Working\Research\oh-my-openagent`
브랜치/커밋: `dev` / `49066e7eccc319ff88e728bc147655ba3d7a9f8f`
참고: 최신 태그 목록의 최상단은 `v4.2.2`였고, 클론된 `package.json`의 버전은 `4.2.0`이었다. 즉 dev 브랜치 메타데이터와 태그 사이에 차이가 있다.

## 결론

OMO는 "AI agent harness"라는 이름을 쓰지만, EZPowers와 같은 문서 기반 SDD/검증 하네스를 대체하는 제품이라기보다 OpenCode 안에서 동작하는 플러그인 런타임이다. 핵심 자산은 거대한 프롬프트가 아니라, 에이전트 실행을 안전하게 만드는 작은 강제장치들이다.

EZPowers에 바로 유용한 후보는 다음 순서다.

1. Hashline 기반 anchored edit/읽기 증강
2. Doctor check registry와 JSON/text formatter 구조
3. Hook tier 분리와 safe hook factory 패턴
4. Background task lifecycle의 상태/동시성/완료판정 모델
5. Skill-embedded MCP의 세션 격리와 secret redaction
6. Category/model routing ledger
7. Boulder state의 work plan persistence
8. Team Mode의 durable mailbox/task-state 일부
9. Rules/context injector의 중복 주입 방지 패턴
10. AST-grep/LSP 도구 체계

반대로 Sisyphus 프롬프트 전체, Team Mode 전체, OpenCode raw prompt hook, Array prototype shim은 EZPowers에 직접 들여오면 유지보수 비용과 충돌 위험이 크다.

## OMO 구조 요약

OMO의 실제 진입점은 `src/testing/create-plugin-module.ts`의 `createPluginModule()`이다. 이 함수가 OpenCode plugin interface를 만들고, 설정 로드, manager 생성, tool registry, hook registry, event handler, experimental compaction hook을 묶는다.

구성은 크게 다음과 같다.

- `src/agents`: Sisyphus, Hephaestus, Oracle, Librarian, Atlas 등 built-in agent 정의
- `src/hooks`: session/tool/transform/continuation/skill hook 묶음
- `src/tools`: delegate task, background task, hashline edit, skill MCP, interactive bash 등
- `src/features`: background-agent, team-mode, boulder-state, skill-mcp-manager, loader 계층
- `src/cli`: doctor, boulder, auth, setup, update 등 운영 CLI
- `src/config`: Zod 기반 설정 schema
- `packages/ast-grep-mcp`, `packages/rules-core`: AST/규칙 계층

규모상 TypeScript 파일은 `src` 아래 2천 개 이상이고, 테스트 파일도 700개 이상이다. 전체를 이식하기보다 검증/상태/도구 격리 패턴을 골라 쓰는 방식이 맞다.

## EZPowers 하네스와의 접점

EZPowers는 이미 다음 축을 갖고 있다.

- 계획 변환: `scripts/harness-convert.ps1`
- 단계 실행: `scripts/harness-run.ps1`
- 단계 검증: `scripts/verify-step.py`
- 최종 wiring gate: `scripts/harness-gate.ps1`
- 환경 진단: `scripts/harness-doctor.ps1`
- 계약 문서: `docs/reference/harness-execution-contract.md`, `docs/reference/verification-contract.md`, `docs/reference/dispatch-protocol.md`
- 오케스트레이션: `commands/choiceexecutor.md`

따라서 OMO를 "새 오케스트레이터"로 가져올 필요는 낮다. 활용 가능성이 높은 부분은 EZPowers의 기존 계약을 더 엄격하게 만드는 보조 장치다.

## 활용 후보 상세

### 1. Hashline anchored edit

관련 OMO 위치:

- `src/tools/hashline-edit/hash-computation.ts`
- `src/tools/hashline-edit/validation.ts`
- `src/tools/hashline-edit/edit-operations.ts`
- `src/tools/hashline-edit/tool-description.ts`
- `src/hooks/hashline-read-enhancer/hook.ts`
- `src/hooks/hashline-edit-diff-enhancer/hook.ts`

핵심 아이디어는 파일을 읽을 때 각 라인에 `line#hash` 꼬리표를 붙이고, 수정 요청이 그 꼬리표를 기준으로 들어오게 하는 것이다. 수정 직전에 현재 파일의 hash를 다시 계산해 stale edit, 중복 라인, 잘못된 range를 거부한다.

EZPowers 활용도: 높음.

적용 방식:

- `harness-convert.ps1`이 생성한 `phases/{phase}/step*.md`에 anchor snapshot을 남긴다.
- `verify-step.py`가 step 파일의 Verify/파일 참조가 최신 anchor와 맞는지 검사한다.
- 별도 `scripts/anchored-edit.py` 또는 PowerShell module로 stale edit guard를 제공한다.
- 사람이 직접 편집한 계획/단계 문서의 라인 drift를 조기 탐지한다.

주의점:

- Codex의 `apply_patch`를 대체할 필요는 없다.
- OMO의 hashline edit tool 전체를 가져오면 도구 UI와 OpenCode hook에 묶인다.
- EZPowers에는 "검증용 anchor" 또는 "계획/step 파일 전용 guard"로 제한하는 편이 안전하다.

우선순위: P1.

### 2. Doctor check registry

관련 OMO 위치:

- `src/cli/doctor/runner.ts`
- `src/cli/doctor/types.ts`
- `src/cli/doctor/checks/index.ts`
- `src/cli/doctor/formatter.ts`
- `src/cli/doctor/format-default.ts`
- `src/cli/doctor/format-status.ts`
- `src/cli/doctor/format-verbose.ts`

OMO doctor는 check definition을 등록하고, 병렬 실행, timeout, text/status/verbose/json formatter, exit code를 분리한다. 각 check는 throw 대신 structured result를 반환한다.

EZPowers 활용도: 높음.

현재 `scripts/harness-doctor.ps1`는 이미 설정/경로/smoke/wiring/reviewer를 확인한다. 여기에 OMO식 registry를 붙이면 다음 이점이 있다.

- 개별 check 추가가 쉬워진다.
- `--json` 결과를 eval/gate에서 재사용할 수 있다.
- warning/error/skip의 의미가 명확해진다.
- CI와 사람이 보는 출력이 분리된다.

권장 방향:

- `harness-doctor.ps1`를 바로 갈아엎지 말고, check spec 배열과 result object를 먼저 도입한다.
- 텍스트 출력은 유지하고 `--json`을 추가한다.
- exit code는 `0 pass`, `1 error`, `2 warning only`로 고정한다.

우선순위: P1.

### 3. Hook tier와 safe hook factory

관련 OMO 위치:

- `src/plugin/hooks/create-core-hooks.ts`
- `src/plugin/hooks/create-session-hooks.ts`
- `src/plugin/hooks/create-tool-guard-hooks.ts`
- `src/plugin/hooks/create-transform-hooks.ts`
- `src/plugin/hooks/create-continuation-hooks.ts`
- `src/plugin/hooks/create-skill-hooks.ts`

OMO는 hook을 session, tool guard, transform, continuation, skill 계층으로 나눠 구성한다. 개별 hook 활성화 여부는 설정 기반으로 제어하고, hook 생성 실패가 전체 plugin init을 깨지 않게 감싼다.

EZPowers 활용도: 높음.

EZPowers에는 `hooks/hooks.json`, `bin/trace.sh`, lightpath gate, review/gate 스크립트가 이미 있다. 여기에 hook tier 문법을 도입하면 다음이 좋아진다.

- trace hook, validation hook, runtime smoke hook, docs sync hook을 분리해서 켜고 끌 수 있다.
- 실패 허용 hook과 fail-closed hook의 경계가 명확해진다.
- 나중에 plugin별 hook이 늘어도 `choiceexecutor.md`가 비대해지는 것을 막는다.

권장 tier:

- `preflight`: doctor, config, dependency
- `execution`: step 실행 전후 trace
- `verification`: Verify/Verify-type/runtime smoke
- `wiring`: lightpath/wiring gate
- `reporting`: run log, final summary, docs sync

우선순위: P1.

### 4. Background task lifecycle

관련 OMO 위치:

- `src/features/background-agent/manager.ts`
- `src/features/background-agent/types.ts`
- `src/features/background-agent/concurrency.ts`
- `src/features/background-agent/task-poller.ts`
- `src/features/background-agent/session-status-classifier.ts`
- `src/features/background-agent/loop-detector.ts`
- `src/features/background-agent/fallback-retry-handler.ts`

OMO background-agent는 pending/running/completed/error/cancelled/interrupt 상태, provider/model별 concurrency key, fallback attempt history, parent notification, stability-based completion detection을 갖는다.

EZPowers 활용도: 중상.

현재 EZPowers는 `choiceexecutor`에서 subagent/harness/inline 경로를 나누고, harness는 step 파일을 순차 실행한다. 향후 다중 step 병렬 실행이나 reviewer 분산 실행을 할 경우 OMO의 상태 모델이 유용하다.

바로 가져올 부분:

- `attempts` 배열과 `currentAttemptID`
- status enum
- concurrency group/key 개념
- 완료 판정 시 단일 signal이 아니라 안정화 조건을 두는 방식
- fallback retry reason 기록

바로 가져오지 말 부분:

- OpenCode session 직접 생성/주입 로직
- parent session notification
- tmux callback

우선순위: P2.

### 5. Skill-embedded MCP manager

관련 OMO 위치:

- `src/features/skill-mcp-manager/manager.ts`
- `src/features/skill-mcp-manager/types.ts`
- `src/features/skill-mcp-manager/connection.ts`
- `src/features/skill-mcp-manager/env-cleaner.ts`
- `src/features/skill-mcp-manager/error-redaction.ts`
- `src/tools/skill-mcp/*`

OMO는 skill이 선언한 MCP 서버를 세션별로 lazy connect하고, stdio/http transport, OAuth retry, idle cleanup, secret redaction을 처리한다.

EZPowers 활용도: 중상.

EZPowers의 `skills/`와 `plugins/ezpowers/skills/`가 앞으로 도구 실행을 포함하게 되면 이 구조가 바로 필요해진다. 특히 `sessionID:skillName:serverName` 형태의 client key, pending connection dedupe, secret redaction은 재사용 가치가 높다.

권장 방향:

- 지금 당장 MCP manager를 넣기보다, skill spec에 tool dependency 선언 영역을 예약한다.
- 외부 도구 실행 로그에는 redaction filter를 먼저 도입한다.
- 세션 단위 cleanup과 idle TTL은 나중에 MCP 도입 시 사용한다.

우선순위: P2.

### 6. Category/model routing ledger

관련 OMO 위치:

- `src/shared/model-requirements.ts`
- `src/shared/model-resolution-types.ts`
- `src/agents/sisyphus.ts`
- `src/tools/delegate-task/constants.ts`

OMO는 agent/category별 모델 요구사항과 fallback chain을 명시한다. 카테고리는 quick, deep, artistry, visual-engineering, writing 등으로 나뉜다.

EZPowers 활용도: 중상.

EZPowers의 `dispatch-protocol.md`는 reviewer backend와 verdict 형식을 갖고 있다. 여기에 "작업 유형별 reviewer/model policy"를 더하면 dispatch가 더 예측 가능해진다.

권장 방향:

- OMO 모델 이름을 그대로 쓰지 않는다.
- EZPowers 전용 category를 만든다: `harness-script`, `contract-review`, `frontend-runtime`, `doc-sync`, `security-scan`, `quick-fix`.
- 각 category에 required evidence와 reviewer backend preference를 연결한다.

우선순위: P2.

### 7. Boulder state

관련 OMO 위치:

- `src/features/boulder-state/storage.ts`
- `src/features/boulder-state/types.ts`
- `src/features/boulder-state/top-level-task.ts`
- `src/cli/boulder/*`

Boulder는 활성 계획, 세션 목록, task session 재사용, elapsed time, worktree path를 `.omo/boulder.json`에 저장한다. temp file + rename + lock으로 파일 손상을 줄인다.

EZPowers 활용도: 중간.

EZPowers는 이미 `phases/{phase}/index.json`, `wiring-gate.json`, run log를 갖고 있다. Boulder는 별도 대체재가 아니라 "장기 실행 plan state"의 참고 모델이다.

적용 후보:

- phase index에 `active_work_id`, `updated_at`, `attempt_history` 추가
- run resume 시 이전 step/session 상태를 보여주는 inspector 추가
- 장기 plan의 pause/resume 상태를 명시화

우선순위: P2.

### 8. Team Mode mailbox/task state

관련 OMO 위치:

- `src/features/team-mode/types.ts`
- `src/features/team-mode/team-mailbox/send.ts`
- `src/features/team-mode/team-runtime/create.ts`
- `src/features/team-mode/tasks.ts`
- `src/features/team-mode/team-registry/validator.ts`

OMO Team Mode는 lead/member, task claim, mailbox, backpressure, file lock, tmux layout, worktree creation까지 포함한다.

EZPowers 활용도: 중간.

전체 이식은 과하다. 하지만 mailbox와 task claim 모델은 미래의 병렬 harness에 유용하다.

가져올 만한 부분:

- task status: `pending`, `claimed`, `in_progress`, `completed`
- owner/session binding
- mailbox payload size limit
- duplicate message id 방지
- deleting/shutdown state guard

피해야 할 부분:

- tmux visualization
- OpenCode background session launch
- team agent eligibility prompt

우선순위: P3.

### 9. Rules/context injector

관련 OMO 위치:

- `src/hooks/rules-injector/*`
- `src/features/context-injector/*`
- `src/features/hook-message-injector/*`
- `src/hooks/keyword-detector/*`
- `src/hooks/thinking-block-validator/*`
- `src/hooks/tool-pair-validator/*`

OMO는 세션 메시지나 tool 결과에 규칙과 컨텍스트를 주입한다. 또한 중복 주입, 잘못된 tool pair, thinking block 형식 등을 검사한다.

EZPowers 활용도: 중간.

EZPowers는 이미 계약 문서와 command prompt가 강하다. 추가 주입은 과하면 노이즈가 된다. 대신 다음 두 가지는 유용하다.

- 같은 규칙이 반복 주입되는지 감지하는 duplicate-injection guard
- step 검증에서 "필수 계약 조항이 누락되었는지" 확인하는 lightweight context check

우선순위: P3.

### 10. AST-grep/LSP tools

관련 OMO 위치:

- `packages/ast-grep-mcp`
- `src/cli/doctor/checks/tools-lsp.ts`
- `src/cli/doctor/checks/dependencies.ts`
- `src/tools/grep`
- `src/tools/glob`

OMO는 LSP/AST-grep 기반 코드 탐색을 도구로 제공한다. EZPowers에서 직접 코딩 도구로 포함하기보다, audit/eval 보조 도구로 쓰는 편이 맞다.

활용 후보:

- verification-contract의 `Verify-type`을 AST-grep rule로 보강
- pipeline audit에서 금지 패턴 검출
- docs sync 누락을 구조 검색으로 탐지

우선순위: P3.

## 이식하지 않는 것이 좋은 부분

### Sisyphus 프롬프트 전체

Sisyphus는 OMO의 primary orchestrator지만 prompt surface가 매우 크고 OpenCode 도구 목록, agent taxonomy, skill category, IntentGate에 강하게 묶여 있다. EZPowers의 `choiceexecutor.md`, `harness-execution-contract.md`, `verification-contract.md`와 역할이 겹친다.

활용한다면 전체 프롬프트가 아니라 다음 개념만 가져온다.

- category별 도구/skill 추천
- delegation 전 context-completion gate
- 병렬화 가능 작업과 blocking 작업 구분

### Team Mode 전체

Team Mode는 파일 mailbox, tmux, worktree, background session, agent eligibility까지 포함한다. EZPowers 현재 하네스에는 과하다. 병렬 실행이 실제 요구사항이 될 때 task claim/messaging 일부만 별도 설계하는 것이 낫다.

### Agent sort shim / prototype patch

OMO에는 agent ordering을 위해 런타임 동작을 우회하는 shim이 있다. EZPowers에서는 하네스의 결정성을 해치기 쉬우므로 가져오지 않는다.

### OpenCode raw prompt hook

OMO의 raw prompt hook은 OpenCode plugin surface에 최적화되어 있다. EZPowers에는 재현 가능한 문서 계약과 스크립트 gate가 더 중요하다.

## 권장 적용 로드맵

### P1: 검증 안전장치 강화

1. `harness-doctor.ps1`에 check registry 구조와 `--json` 출력 추가
2. step/plan 문서용 hashline anchor prototype 작성
3. hook tier 문서화: preflight/execution/verification/wiring/reporting
4. stale edit, missing wiring, invalid smoke config eval 추가

예상 효과:

- 하네스 실행 전 실패를 더 빨리 잡는다.
- 사람이 수정한 plan/step drift를 감지한다.
- CI와 로컬 진단 결과를 같은 구조로 비교할 수 있다.

### P2: 상태/재시도 모델 강화

1. phase index에 attempt history와 updated_at 도입
2. reviewer/model category policy 문서 추가
3. runtime smoke/reviewer fallback reason을 structured log로 저장
4. boulder-style resume inspector prototype 검토

예상 효과:

- 실패한 step의 재시도 원인이 남는다.
- 장기 작업 재개 시 현재 위치를 쉽게 복원한다.
- backend 선택이 prompt 암묵지에서 정책으로 이동한다.

### P3: 병렬/도구 격리 확장

1. skill tool dependency schema 초안 작성
2. secret redaction filter를 외부 도구 로그에 적용
3. task claim/mailbox 모델을 별도 experimental phase로 검토
4. AST-grep 기반 Verify-type 보조 검사 추가

예상 효과:

- plugin/skill이 외부 도구를 써도 로그 안전성이 오른다.
- 병렬 harness 설계의 기반이 생긴다.
- 구조적 코드 검증을 사람이 직접 검색하는 비용이 줄어든다.

## 테스트 전략

Hashline anchor:

- 동일한 내용이 여러 줄에 반복될 때 올바른 줄을 식별하는지
- CRLF/BOM/빈 줄에서 hash가 안정적인지
- stale hash가 들어오면 수정을 거부하고 새 위치 후보를 제시하는지
- 겹치는 range 수정이 거부되는지
- step 파일 재생성 후 anchor snapshot이 갱신되는지

Doctor registry:

- `.harness/config.json` 누락
- `execute.py` 경로 오류
- smoke config와 runtime artifact 불일치
- wiring gate 누락
- reviewer backend 누락
- warning only일 때 exit code 2
- `--json` schema 안정성

Hook tier:

- fail-closed hook 실패 시 실행 중단
- reporting hook 실패 시 본 실행 결과는 보존
- hook disable 설정이 의도한 hook에만 적용
- trace artifact가 append-only로 남는지

Background/task state:

- 같은 task를 동시에 claim할 때 한 쪽만 성공
- retry attempt가 순서대로 기록
- crash 이후 pending/running 상태 복구
- concurrency limit 초과 시 queue 상태 유지

Skill MCP/redaction:

- `_KEY`, `_SECRET`, `_TOKEN` 계열 환경변수가 로그에 남지 않는지
- 동일 skill/server에 동시 연결 요청이 들어와도 하나만 생성되는지
- session delete 시 client cleanup이 실행되는지

## 최종 판단

OMO의 활용 가능성은 높지만, "에이전트 제품 전체"를 가져오는 방식은 부적합하다. EZPowers의 강점은 이미 하네스 계약, Verify/Verify-type, wiring gate, choiceexecutor에 있다. OMO에서 가져올 것은 그 위에 붙는 방어적 실행 패턴이다.

가장 먼저 할 만한 작업은 세 가지다.

1. `harness-doctor.ps1`를 registry/JSON 구조로 개선
2. plan/step 파일을 위한 hashline-style stale edit guard prototype 추가
3. hook tier 정책을 EZPowers reference 문서로 고정

이 세 가지는 EZPowers의 기존 흐름을 바꾸지 않으면서도 실패 조기 발견, 편집 안정성, 확장성을 바로 높인다.
