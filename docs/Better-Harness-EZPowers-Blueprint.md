# EZPowers를 eval-driven harness로 진화시키는 청사진

EZPowers 0.6.0은 **이미 eval-driven 하네스의 골격을 갖추고 있다 — Verify 커맨드, Coverage Matrix, Verdict 파싱, Banned expressions, Oscillation detection이 그것이다**. 결정적으로 빠진 것은 (1) 이 신호들을 **시간을 가로질러 비교 가능한 데이터**로 저장하는 인프라, (2) optimization/holdout 분리, (3) "한 줄 변경 → 측정 → 회귀 가드" 루프를 자동화하는 스크립트다. 90일 안에 이 빈 곳을 채우면 EZPowers는 "코딩 워크플로 플러그인"에서 "**자기 자신을 측정하면서 진화하는 SDD 하네스**"로 격상된다. 가장 큰 ROI는 본 리포트가 결론에서 추천하는 **"이번 주에 1시간 안에 시작할 수 있는 한 가지 변경"** — `evals/golden/` 디렉토리와 첫 5개 케이스 + 베이스라인 한 번 측정 — 에서 나온다. 그 이후의 모든 단계는 그 시드 데이터에 점진적으로 의존한다.

본 리포트는 LangChain Better-Harness 블로그(2026-04-08)의 6단계 레시피와 Anthropic의 *Demystifying evals for AI agents*(2026-01-09) YAML 스키마, *Effective harnesses for long-running agents*(2025-11-26)의 두-에이전트 패턴, OpenAI *Harness Engineering*(2026-02-11)의 mechanical enforcement 원칙, Meta-Harness(arXiv:2603.28052)의 outer-loop optimizer, 그리고 raphaelchristi/harness-evolver, whchoi98/harness-eval, hummbl-dev/hummbl-agent-eval-harness 등 2026년 봄 시점 Claude Code 플러그인 생태계의 구체적 레이아웃을 EZPowers 코드베이스에 직접 매핑한다.

---

## Part A. 외부 베스트 프랙티스 — EZPowers와의 직접 매핑

### A.1 LangChain Better-Harness 6단계의 EZPowers 매핑

LangChain 블로그가 제시한 파이프라인은 **"data sourcing → experiment design → optimization → review & acceptance"** 다. 6단계 루프(source/tag → split → baseline → optimize → validate → human review)에서 EZPowers는 **단계 4와 5의 일부 primitive를 이미 보유**하지만, 단계 1·2·3이 통째로 결여돼 있다.

| Better-Harness 단계 | EZPowers 현재 상태 | 결여된 것 |
|---|---|---|
| 1. Source/tag evals | Verify 커맨드(spec 단위), Coverage Matrix(R↔T 매핑) | `evals/` 디렉토리 자체, 카테고리 태그 스키마, 외부 데이터셋 통합 |
| 2. Split per category | 없음 | optimization/holdout/golden 3-way split |
| 3. Baseline | 없음 | 0.6.0 버전의 절대 점수 미측정 |
| 4. Optimize (diagnose+experiment) | Iron Law(root cause first), 4-Phase 디버깅, 한 번에 한 가지 변경 원칙(choiceexecutor.md) | trace 클러스터링 자동화, diagnostic subagent |
| 5. Validate (no regression) | Oscillation detection, Tiered escalation | 이전 통과 케이스 보호, holdout 점수 비교 |
| 6. Human review | Final Code Review (choiceexecutor.md L300+) | 변경 사유 trace, eval delta 기록 |

LangChain 블로그가 게시한 **실제 hill-climbed 한 줄 변경**이 EZPowers의 brainstorm/plan 페이즈에 그대로 쓸 수 있는 형태다: "Use reasonable defaults when the request clearly implies them", "Do not ask for details the user already supplied", "Do not keep issuing near-duplicate searches once you have enough information to draft a concise summary", "Ask domain-defining questions before implementation questions". 이 마지막 항목 — **"도메인 정의 질문을 구현 질문보다 먼저"** — 는 EZPowers `commands/brainstorm.md`의 "Hard gate" 위치에 한 줄 추가하기에 가장 적합한 후보다.

### A.2 Anthropic 공식 가이드의 핵심 흡수 포인트

**"Effective harnesses for long-running agents"**(2025-11-26)의 두-에이전트 패턴 — Initializer가 `claude-progress.txt` + `feature_list.json`을 만들고 Coding agent가 매 세션마다 그것을 읽고 한 feature를 구현 — 은 EZPowers의 `setup → brainstorm → plan → choiceexecutor` 플로우와 **구조적으로 동일**하다. EZPowers의 `INDEX.md`는 Anthropic의 `claude-progress.txt`에, plan.md가 만드는 task 분해는 `feature_list.json`에 대응한다. **차이점**: Anthropic은 `feature_list.json`을 JSON으로 두는 이유를 명시했다 — *"the model is less likely to inappropriately change or overwrite JSON files compared to Markdown files"*. EZPowers는 Coverage Matrix를 마크다운에 저장하므로, **eval 결과 누적 파일은 JSON/JSONL로 저장하라**는 강한 시사점이 나온다.

**"Demystifying evals for AI agents"**(2026-01-09)는 EZPowers가 그대로 채택해야 할 YAML 스키마를 제시한다:

```yaml
task:
  id: "brainstorm-greenfield-cli-tool_1"
  desc: "User asks to plan a CLI tool from scratch with vague initial spec"
  graders:
    - type: deterministic_tests
      required: [check_R_count.sh, check_verify_commands_exist.sh]
    - type: llm_rubric
      rubric: prompts/spec_quality.md
    - type: state_check
      expect:
        files_created: ["specs/spec-001.md"]
    - type: tool_calls
      required: [{tool: Read, params: {path: "AGENTS.md"}}]
  tracked_metrics:
    - type: transcript
      metrics: [n_turns, n_toolcalls, n_total_tokens]
```

또한 Anthropic은 **"capability evals"** (낮은 통과율로 시작 → hill-climb 대상) 와 **"regression evals"**(≈100% 통과율 유지)를 명시적으로 구분하고, *"capability evals with high pass rates can 'graduate' to become a regression suite"*라고 한다. 이 졸업 매커니즘이 EZPowers의 `golden/` 폴더 운영 정책의 직접 근거다.

**4월 23일 Postmortem**에서 Anthropic은 자기 회사의 Claude Code 시스템 프롬프트 변경 정책을 공개했다: *"We will run a broad suite of per-model evals for every system prompt change to Claude Code, continuing ablations to understand the impact of each line."* **per-line ablation**이 모델 회사 내부 표준이라는 사실은 EZPowers가 채택해야 할 변경 단위를 그대로 정한다 — **한 번에 한 줄, 그 줄이 어떤 케이스를 움직였는지 측정**.

### A.3 OpenAI 5원칙의 SDD 매핑

OpenAI Codex 필드 리포트(2026-02-11)의 5원칙 (커뮤니티 정제판)을 EZPowers SDD 플로우에 매핑하면:

1. **"capability is missing → make it legible and enforceable"** ↔ Verify 커맨드(이미 enforceable한 exit-0 셸 명령). EZPowers에 결여된 것은 *legibility* — 어떤 capability가 어느 케이스에서 실패하는지 trace 기반 가시화.
2. **Repository as system of record / progressive disclosure** ↔ AGENTS.md, INDEX.md (이미 존재). 추가 작업: `evals/INDEX.md`에 evals 목차를 두어 동일 패턴 확장.
3. **Mechanical enforcement of architectural invariants** ↔ Banned expressions(14개 패턴), Hard gates, Pre-substitution validation (이미 존재). 결여: **eval set 자체에 대한 lint** — 카테고리 태그 누락 케이스, holdout에 들어가면 안 되는 케이스 검출.
4. **Garbage collection / "spring cleaning"** ↔ 결여. LangChain 블로그도 *"spring cleaning of evals is good"*라고 명시했다. EZPowers에 cron-style eval 청소 메커니즘이 없다.
5. **Visual / observability validation** ↔ 부분적 결여. Verify 커맨드 결과는 한 시점만 보여주고, 시계열 점수 추이가 없다.

### A.4 SDD 슬래시 커맨드 워크플로 eval의 특수성

일반 agent eval과 SDD 슬래시 커맨드 eval의 결정적 차이는 **워크플로의 단계가 분리돼 있다**는 점이다. brainstorm 단계의 출력(spec)이 plan 단계의 입력이 되고, plan의 출력(task list)이 choiceexecutor의 입력이 된다. 이는 다음 함의를 갖는다:

**(a) Per-stage eval과 end-to-end eval을 동시에** 운영해야 한다. brainstorm 단계만 평가하면 spec이 너무 모호해도 통과할 수 있고, end-to-end만 평가하면 어느 단계가 망가졌는지 진단 불가다. LangChain의 *"Evaluating Deep Agents"* 블로그(blog.langchain.com/evaluating-deep-agents-our-learnings)가 권장하는 **single-step / full-run / multi-turn 3중 eval 설계**를 그대로 채택한다.

**(b) Stage 간 인터페이스 계약**이 가장 깨지기 쉽다. 예: brainstorm의 R1, R2 형식이 plan의 Coverage Matrix 파서가 기대하는 형식과 어긋나면, 두 단계 모두 개별적으로는 통과한다. 따라서 **"contract eval"** 카테고리를 별도로 둔다 — `pattern:contract:brainstorm_to_plan`, `pattern:contract:plan_to_executor`.

**(c) 사람-검토 시점이 분리돼 있다**. brainstorm 끝, plan 끝에서 사람이 본다. 이는 trace 수집 관점에서 **자연스러운 feedback poll point**다. 사용자에게 "이 spec이 맞나?"를 묻는 그 순간이 thumbs up/down 데이터의 최적 수집점.

### A.5 Cursor / Codex / Claude Code 통합 하네스

AGENTS.md는 Linux Foundation AAIF가 2025-12부터 stewardship한 **사실상 표준**이다. Claude Code는 CLAUDE.md, Cursor는 `.cursor/rules/*.mdc`, Codex는 AGENTS.md를 읽는다. EZPowers `setup.md`는 이미 `AGENTS.md`를 생성하므로 통합 출발점이 좋다. **권장 패턴**: CLAUDE.md를 `@AGENTS.md`로 import 시키고, AGENTS.md가 단일 SOT(Source of Truth)가 되게 한다. 이 변경은 Part D에서 patch 형태로 제시한다.

---

## Part B. EZPowers 구체적 개선 제안 (8개 영역)

### B.1 Eval 인프라 도입

**현재 상태.** `evals/` 디렉토리가 존재하지 않는다. Verify 커맨드는 spec 단위에서 정의되고 일회성으로 실행된 뒤 사라진다. `commands/brainstorm.md` L하단부의 "Verify-types 6분류"(api/e2e/cli/lib/data/pure)가 이미 카테고리 태깅의 분류 체계로 전환 가능한 상태다.

**문제점.** (1) 0.5.0 → 0.6.0 회귀를 측정 불가, (2) 새 banned expression이 어떤 spec에서 발견됐는지 추적 불가, (3) 실패한 brainstorm 세션의 패턴을 다음 버전에 반영하는 메커니즘 부재.

**Better-Harness 적용안.** Anthropic *Demystifying evals* YAML 스키마와 LangChain Better-Harness TOML의 `case_id`/`split`/`stratum` 패턴을 결합해 **EZPowers 전용 eval 케이스 스키마**를 정의한다.

**구체적 구현.**

권장 디렉토리 구조:
```
evals/
  INDEX.md                          # eval 목차 (사람용)
  schema.json                       # JSON Schema for case files
  optimization/                     # 70% — 변경 후 점수 변동 허용
    brainstorm/
      greenfield-cli-tool.yaml
      brownfield-refactor.yaml
      ...
    plan/
    choiceexecutor/
    contract/                       # 단계 간 인터페이스
  holdout/                          # 20% — 변경자가 보면 안 됨
    .gitkeep                        # 실제 케이스는 별도 private repo 또는 .gitignored
  golden/                           # 10% — 절대 깨지면 안 됨
    banned-expression-detection.yaml
    coverage-matrix-completeness.yaml
    ...
  honeypot/                         # 2-3 케이스, canary 토큰 포함
  results/
    baselines/
      0.6.0.json
      0.6.1.json
    runs/
      <timestamp>-<git-sha>.jsonl
```

권장 case 스키마(YAML, Anthropic 형식 + Better-Harness 태그 결합):

```yaml
# evals/optimization/brainstorm/greenfield-cli-tool.yaml
case_id: "brainstorm.greenfield_cli_tool.001"
split: optimization                 # optimization | holdout | golden | honeypot
stratum:                            # 카테고리 태그 (다중)
  command: brainstorm
  difficulty: multi_step
  pattern: greenfield
  domain: cli
  language: ko_en_mixed
  model_family: agnostic            # sonnet_only | opus_required | agnostic
input:
  user_message: |
    Python으로 간단한 todo CLI 만들고 싶어. 파일은 SQLite로 저장.
  initial_files: []                 # cwd 상태
graders:
  - type: deterministic_tests
    commands:
      - "test -f specs/*.md"
      - "grep -E '^- R[0-9]+:' specs/*.md | wc -l | awk '$1>=3'"
      - "grep -E '^Verify:' specs/*.md | wc -l | awk '$1>=3'"
  - type: banned_expression_scan
    fail_on_match: true
  - type: llm_rubric
    rubric: evals/rubrics/spec_quality.md
    assertions:
      - "Spec asks at least one domain-defining question before implementation"
      - "Each R has a corresponding Verify with verify-type from {api,e2e,cli,lib,data,pure}"
tracked_metrics:
  transcript: [n_turns, n_toolcalls, n_total_tokens]
  custom: [r_count, verify_count, banned_expression_hits]
```

**카테고리 태그 권장 체계** (Better-Harness `stratum` 컨벤션 + EZPowers 도메인 결합):
- `command:{setup,brainstorm,plan,choiceexecutor,executeharness,review,sync-docs}`
- `difficulty:{single_step,multi_step,long_horizon}` — Anthropic *Demystifying* 의 분류
- `pattern:{greenfield,brownfield,refactor,bugfix,security_review,docs_sync}`
- `model_family:{sonnet_only,opus_required,agnostic}` — Postmortem 후 모델별 게이팅 강제
- `language:{ko,en,ko_en_mixed}` — banned expressions가 한국어 우세이므로 필수
- `verify_type:{api,e2e,cli,lib,data,pure}` — brainstorm.md에서 이미 사용
- `pattern:contract:*` — stage 간 인터페이스 케이스

**첫 eval set 권장 (각 커맨드 5-10 케이스, Anthropic의 "20-50 simple tasks drawn from real failures" 가이드 적용)**:

| 커맨드 | 케이스 수 | 첫 5 케이스 |
|---|---|---|
| `setup` | 5 | greenfield-empty-dir, brownfield-existing-claude-md, monorepo-root, korean-only-readme, conflicting-agents-md |
| `brainstorm` | 8 | greenfield-cli, brownfield-feature-add, refactor-narrow-scope, vague-spec-ko, banned-expr-trap, contract-to-plan, multi-R-coverage, hard-gate-bypass-attempt |
| `plan` | 6 | spec-3R, spec-10R-large, missing-verify, refactor-impact-scope, structural-invariant-violation, contract-to-executor |
| `choiceexecutor` | 8 | inline-trivial, harness-needed, security-keyword-trip, oscillation-trap, resume-mid-task, ac-fail-then-pass, degradation-detect, subagent-vs-inline-decision |
| `executeharness` | 4 |
| `review` | 3 |
| `sync-docs` | 3 |
| **contract** (stage 간) | 5 |
| **합계** | **42** |

LangChain의 표는 train 2 / holdout 8, train 3 / holdout 6 등 **holdout이 더 큰 비율**을 보였다. 그러나 케이스 수가 작을 때(EZPowers의 42개 출발점) 70/20/10 비율이 안정적이다.

**Hand-curated vs production-trace-derived 비율 권장.** 초기에는 **hand-curated 100%**(Anthropic도 "high value, but difficult to generate at scale" 명시). PostToolUse hook이 들어간 뒤(Phase 2 이후) **70/30 → 50/50**으로 전환. LangChain이 강조한 "Slack에서 오는 trace link" 패턴은 EZPowers 단일 사용자 컨텍스트에서는 `/feedback` 슬래시 커맨드로 대체.

**예상 ROI.** Effort=중(1-2주), Impact=극대. **이 한 단계만 해도 향후 모든 변경이 측정 가능해진다**. 점수: **9/10**.

### B.2 Optimization vs Holdout vs Golden 3-way split

**현재 상태.** Split 개념 자체가 없다.

**문제점.** Better-Harness 블로그 직접 인용: *"Autonomous hill-climbing has a tendency to overfit to tasks so holdout sets ensure that learned optimizations work on previously unseen data."* EZPowers는 사용자 본인이 변경자이므로 **인간 자체가 reward hacker**가 될 수 있다 — 특정 케이스를 통과시키려고 brainstorm.md를 ad-hoc으로 수정.

**적용안.**

| Split | 비율 | 정의 | 노출 정책 |
|---|---|---|---|
| `optimization/` | 70% (~30 cases) | 변경자가 보고 hill-climb 대상 | 공개 |
| `holdout/` | 20% (~8 cases) | 변경 후 점수 측정 시점에만 실행 | **gitignored**, 별도 비공개 디렉토리 또는 별도 private repo |
| `golden/` | 10% (~4 cases) | 절대 깨지면 안 되는 회귀 가드 | 공개 (의도적으로 모두에게 보여줌) |
| `honeypot/` | 2-3 추가 | canary 토큰 포함, 메모리 오염 탐지 | 공개 (canary string으로 detect) |

**Stratified split 강제.** 각 stratum 키별로 비율 유지. 즉 `command:brainstorm`에 8 케이스 있다면 5/2/1로 분할. 이를 강제하는 `scripts/check_split_balance.py`를 둔다.

**Holdout 노출 방지 메커니즘 — 강도 순:**

1. **별도 private repo** (가장 강력): `evals-holdout/` 을 별도 GitHub private repo로 분리, runner CI만 access. SWE-Bench Pro 패턴 차용.
2. **`.gitignore + .claudeignore`** (현실적 1차): `evals/holdout/**`을 두 ignore 파일에 모두 추가. Claude Code가 Read/Glob 툴로 접근 못하게.
3. **Canary token 임베드**: 각 holdout 케이스 헤더에 `canary: "EZPOWERS_HOLDOUT_DO_NOT_TRAIN_<sha>"`. 모델 출력에서 이 문자열이 나오면 contamination 알람.
4. **Honeypot 케이스**: 2-3개의 "의도적으로 답이 알려진 trick 케이스" — 점수가 비정상적으로 높으면 leak 신호.

**Golden regression set 정의.** "절대 깨지면 안 됨" 4-5개:
- `banned-expression-detection.yaml` — 14개 패턴 모두 검출
- `coverage-matrix-completeness.yaml` — R↔T 누락 검출
- `verdict-parsing-format.yaml` — `## Verdict: PASS/FAIL` 형식 유지
- `oscillation-detection-3iter.yaml` — 3회 반복 시 stop
- `pre-substitution-validation.yaml` — `[PLACEHOLDER]` 검출

Anthropic의 *"capability eval graduates to regression eval"* 룰을 따라, optimization에서 100% 통과율로 3개 연속 빌드를 견딘 케이스는 자동으로 golden으로 승급한다.

**예상 ROI.** Effort=낮음(스크립트 1-2개), Impact=대. 점수: **8/10**.

### B.3 Trace 수집 인프라

**현재 상태.** CLAUDE.md에 명시된 "훅 없음 — 필요해지면 그때 추가" 정책. 세션 종료 시 모든 신호 휘발.

**문제점.** Better-Harness *"flywheel: more usage → more traces → more evals → better harness"*가 작동 불가. LangChain 블로그가 가장 가치 있다고 강조한 production trace mining 채널이 닫혀 있다.

**Better-Harness 적용안.** Claude Code hook system을 단계적으로 도입한다. Anthropic 공식 hook 이벤트 21종 중 EZPowers에 즉시 가치 있는 것은:

| Hook | 용도 | EZPowers 매핑 |
|---|---|---|
| `SessionStart` | trace 파일 init | `${CLAUDE_PLUGIN_DATA}/traces/<session_id>.jsonl` 생성 |
| `UserPromptSubmit` | 슬래시 커맨드 진입 감지 | `/brainstorm`, `/plan` 등 첫 진입 trace |
| `PostToolUse` (matcher: `Edit|Write`) | 변경된 파일 추적 | spec 작성/수정 trace |
| `PostToolBatch` | turn 단위 집계 | regression context injection의 권장 지점 |
| `SubagentStop` | reviewer 에이전트 종료 시 | spec-reviewer/plan-reviewer/code-reviewer 결과 capture |
| `Stop` | turn 종료, Verdict 파싱 시도 | `## Verdict: PASS/FAIL` 추출 |
| `SessionEnd` | trace flush + scoring | `/feedback`이 있다면 첨부 |

**JSONL 포맷 권장** (OpenTelemetry GenAI semantic conventions 준수, 그래야 향후 Langfuse/Datadog/Phoenix로 export 가능):

```jsonc
{
  "trace_id": "8c1e...",
  "span_id": "a4b2...",
  "session_id": "abc123",
  "turn_id": "t-7",
  "hook_event_name": "PostToolUse",
  "tool_name": "Edit",
  "tool_input": {"file_path": "specs/spec-001.md"},
  "tool_use_id": "toolu_01...",
  "gen_ai.system": "anthropic",
  "gen_ai.request.model": "claude-opus-4-5",
  "gen_ai.usage.input_tokens": 4231,
  "gen_ai.usage.output_tokens": 812,
  "ezpowers.command": "brainstorm",
  "ezpowers.verdict": null,           // Stop hook에서 채움
  "ezpowers.banned_expression_hits": 0,
  "scores": [],
  "labels": [],
  "start_time_unix_ns": 1714000000000000000,
  "end_time_unix_ns": 1714000004210000000,
  "status": "OK"
}
```

**사용자 피드백 수집.** 새 슬래시 커맨드 `/feedback +1 "spec was clear"` 또는 `/feedback -1 "asked too many redundant questions"`. trace의 마지막 turn에 `scores: [{name: "user-feedback", value: ±1, comment, source: "user"}]` 부착. Langfuse `create_score` API와 호환되는 스키마.

**Trace → eval candidate 변환.** `scripts/promote_trace.py`:
1. 직전 N일치 trace 로드
2. `scores` 중 -1 받은 trace 필터
3. 사람이 한 번 검토 (Verdict + user comment 표시)
4. 승인 시 해당 trace의 input을 새 eval case YAML로 변환

**"훅 없음" 정책의 단계적 변경.** 현재 CLAUDE.md 정책은 **단순성 우선**으로 합리적이다. 변경 명분은 *측정 가능성*이다. 단계 변경 문구:

```diff
- # No hooks — add only if a concrete problem demands it
+ # Hooks: opt-in trace collection only.
+ # Default: no hooks. To enable trace collection (required for `/eval`,
+ # baseline measurement, regression tracking), run `/setup --enable-traces`.
+ # Traces are written to ${CLAUDE_PLUGIN_DATA}/traces/ (gitignored by default).
+ # Hooks must NOT modify model behavior — they may only observe and log.
```

이 marker를 두면 "훅으로 동작 변경"은 여전히 금지된다 (OpenAI 5원칙의 mechanical enforcement 정신과 일치).

**예상 ROI.** Effort=중(2주, hook script + JSONL writer), Impact=대. 점수: **8/10**.

### B.4 Hill-climbing 6단계 루프 자동화

**현재 상태.** 사람이 손으로 brainstorm.md를 편집하고 git commit 한다. 한 번에 한 가지 변경 원칙이 choiceexecutor.md에 *문서로* 명시돼 있으나, *기계적 강제*는 없다.

**문제점.** 변경마다 점수 측정이 강제되지 않으면 회귀가 누적된다. Anthropic Postmortem(4월 23일): *"continuing ablations to understand the impact of each line"*.

**적용안.** 3개 스크립트 + 1개 diagnostic subagent.

**`scripts/run_baseline.py`** — 변경 전 베이스라인:
```python
# 의사코드
for split in ["optimization", "holdout", "golden"]:
    for case in load_cases(f"evals/{split}/"):
        result = run_case(case, model="claude-opus-4-5", n_trials=3)
        scores[split][case.id] = aggregate(result)
write_baseline(f"evals/results/baselines/{version}.json", scores)
```

**`scripts/propose_edit.py`** — diagnostic subagent 호출:
- 입력: failing optimization cases의 trace 묶음
- 출력: **"한 줄 변경 제안 + 어느 파일:라인 + 어떤 케이스를 개선할 것으로 기대"**
- 강제 schema: `{file: "commands/brainstorm.md", line: 142, before: "...", after: "...", expected_improvements: ["case_id_1", "case_id_2"], rationale: "..."}`

**`scripts/validate.py`** — 변경 후 검증:
```python
# 의사코드
new_scores = run_all_cases(model_changed=True)
deltas = compare(new_scores, baseline)
regressions = [c for c in deltas if c.delta < 0 and c.split == "golden"]
if regressions:
    block_commit(reason=f"Golden regression on {regressions}")
holdout_delta = avg(deltas[split="holdout"])
if holdout_delta < -0.1:
    block_commit(reason="Holdout score dropped >10%")
optimization_delta = avg(deltas[split="optimization"])
if optimization_delta <= 0:
    require_human_review(reason="No optimization improvement")
write_run(f"evals/results/runs/{ts}-{sha}.jsonl", deltas)
```

**Diagnostic subagent 정의** — 새 `agents/eval-diagnostician.md`:
```markdown
---
name: eval-diagnostician
description: Analyzes failing eval traces and proposes ONE line change.
tools: Read, Grep, Glob
model: claude-opus-4-5
maxTurns: 8
---
# Role
Read failing trace clusters. Identify a SINGLE common root cause.
Propose ONE change of at most 3 consecutive lines in ONE file under commands/ or agents/.

# Hard constraints
- diff must touch ≤3 lines (use `diff --stat | awk '$3<=3'` to verify)
- output JSON schema enforced
- forbid changes to evals/ itself (anti-cheating)
- forbid changes to verify command syntax (golden contract)
```

**한 번에 한 줄 정책 코드 강제.** `scripts/validate.py` 시작에 git diff 라인 카운트 게이트:
```python
n_changed = int(subprocess.check_output(
    ["git", "diff", "--cached", "--shortstat"]).split()[3])
if n_changed > 3:
    sys.exit(f"FAIL: changed {n_changed} lines, max 3 per Better-Harness recipe")
```

**Validation step 체크리스트** (Better-Harness 단계 5):
1. Golden 100% 통과 (deal-breaker)
2. Optimization 평균 점수 +0.05 이상 (실질 개선)
3. Holdout 평균 점수 -0.05 이하 아닐 것 (no overfit)
4. Banned expressions 사전 통과 (자기참조 lint — 새 텍스트 자체에 banned 표현 들어가면 안 됨)
5. Diff 라인 수 ≤ 3
6. eval-diagnostician이 명시한 `expected_improvements` 케이스가 실제로 개선됐는지

**인간 리뷰 게이트 위치.** Better-Harness *"manual sanity check"*. EZPowers는 사람 = 변경자이므로, 게이트는 **commit 직전**에 둔다. `pre-commit` hook(git, hook과 다름)에서 `validate.py`를 호출, 5/6번 모두 자동 통과해도 사람이 6번 항목(rationale)을 한 번 읽고 `[y/N]` 응답.

**예상 ROI.** Effort=대(3-4주, 스크립트 3개 + diagnostician), Impact=중대. 점수: **7/10** (선행 조건 B.1, B.2 필수).

### B.5 변경 추적

**현재 상태.** git history만 존재. "이 한 줄이 어느 케이스를 개선했는지"는 commit message에 있을 수도, 없을 수도 있다.

**문제점.** 6개월 뒤 누군가 (자기 자신 포함) 그 한 줄을 무심코 지운다. 어떤 케이스가 깨질지 예측 불가.

**적용안.** **`harness_versions/changelog.jsonl`** — append-only 구조화 로그.

```jsonl
{"date":"2026-04-25","version":"0.6.1","file":"commands/brainstorm.md","line":142,"before":"Ask the user for missing information.","after":"Ask domain-defining questions before implementation questions.","motivation_trace_id":"8c1e...","eval_delta":{"optimization.brainstorm":{"before":0.65,"after":0.83,"cases_flipped_to_pass":["brainstorm.greenfield_cli_tool.001","brainstorm.vague_spec_ko.003"]},"holdout.brainstorm":{"before":0.58,"after":0.67}},"author":"human","reviewer":"eval-diagnostician","rationale":"3 consecutive trace failures showed agent asking implementation-level Q before scope clarification."}
```

**단일 git history만으로 부족한 이유**: (a) git diff는 *어느 케이스를 위해* 변경됐는지 모르고, (b) revert가 *어느 케이스를 깨뜨릴 것인지* 미리 보여주지 않으며, (c) eval delta가 commit msg와 **mechanically 연결되지 않으면** 추적이 사람의 성실성에 의존한다.

**스키마 필수 필드**: `date`, `version`, `file:line`, `before/after`(diff 텍스트), `motivation_trace_id`(어떤 trace가 이 변경을 트리거?), `eval_delta`(split별 점수 변화 + flipped cases), `author`(human|eval-diagnostician), `rationale`(한 문장).

**예상 ROI.** Effort=낮음(JSONL append만), Impact=중. 점수: **6/10**.

### B.6 기존 primitive 강화

EZPowers는 이미 5개 primitive를 보유한다. 각각의 eval-driven 진화 경로:

**(a) Verify 커맨드 → eval grader**. 현재 spec/plan 작성 시 한 번 실행되고 끝. 변경: Verify 커맨드 텍스트를 case YAML의 `graders.deterministic_tests.commands` 항목에 *그대로 복사*. 즉 brainstorm 출력의 Verify 섹션이 자동으로 그 case의 grader가 된다. **재사용 코드: `scripts/extract_verify_to_grader.py`**.

```python
# 의사코드
for spec_file in glob("specs/*.md"):
    verifies = parse_verify_section(spec_file)
    case_yaml = {
        "case_id": f"realtrace.{spec_file.stem}",
        "split": "optimization",  # 사람이 사후 승급 가능
        "graders": [{"type": "deterministic_tests", "commands": verifies}]
    }
    write(f"evals/optimization/{spec_file.stem}.yaml", case_yaml)
```

**(b) Coverage Matrix → 카테고리 태그 자연 진화**. 현재 R↔T 매핑. 변경: R 자체에 `R1 [domain:cli, difficulty:single]` 형식 인라인 태그 부착. 그 태그가 eval case의 `stratum` 으로 흘러간다.

**(c) Verdict 파싱 → eval result 누적**. 현재 `## Verdict: PASS/FAIL` 헤더가 한 시점만 보여줌. 변경: Stop hook에서 verdict + session_id + command + timestamp를 `evals/results/runs/<ts>.jsonl`로 append. 시계열 점수 추이가 자동 생성된다.

**(d) Banned expressions의 eval-driven 진화**. **"새 banned word는 어떻게 발견하는가?"** — Better-Harness "trace clustering"의 직접 적용. 의사코드:
```python
# scripts/discover_banned_phrases.py
failing_traces = load_traces(filter=lambda t: t.scores["user-feedback"] == -1)
spec_outputs = [t.output_text for t in failing_traces if t.command == "brainstorm"]
candidate_phrases = ngram_frequency(spec_outputs, n=2..5, min_count=3)
existing_banned = parse_banned_list("commands/brainstorm.md")
new_candidates = candidate_phrases - existing_banned
# 사람 리뷰 후 banned 리스트에 추가
```

**(e) Oscillation detection 통계 → eval signal**. 현재 iteration ≥3에서 stop. 변경: `{section}:{check_number}` 키별 발생 빈도를 trace에 기록. 어떤 섹션/체크가 자주 oscillate하는지 → 그 섹션의 prompt가 모호하다는 강한 신호 → **자동으로 capability eval로 등록**.

**예상 ROI.** Effort=낮음-중(이미 있는 primitive 재사용), Impact=대. 점수: **9/10** — **가장 ROI 높은 영역 중 하나**.

### B.7 Plugin 자체의 self-eval 메커니즘

**verifyself skill 재활용**. 현재 CoVe(Chain-of-Verification) 6차원이 spec/plan/code에 적용된다. 변경: **plugin의 변경 자체에 verifyself 적용**. 즉 brainstorm.md를 수정한다면, 그 수정 자체에 대해:
1. 가정 검증 — "이 한 줄이 어느 케이스를 고친다고 가정?"
2. 반례 — "이 줄이 깨지는 케이스는?"
3. Edge case — holdout/golden에서 작동?
4. 일관성 — 다른 커맨드 텍스트와 모순되지 않는지
5. 완전성 — 회귀 가능 케이스 모두 검토했는지
6. 출처 — trace_id 인용

**writing-skills의 TDD 패턴 강제**. 현재 skill 작성 시에만 적용. 변경: **모든 커맨드 변경에 동일 TDD 강제** — "변경 전 실패하는 eval 케이스 작성 → 변경 → 통과 확인". `pre-commit` 훅이 이 순서를 강제할 수 있다 (case 파일이 함께 commit돼야 함).

**`/eval` 신규 슬래시 커맨드.** 사용자가 직접 호출:
```markdown
# commands/eval.md (신규)
---
description: Run EZPowers eval suite and report current version score.
---
# Usage
/eval                    # all splits
/eval optimization       # only optimization
/eval --case <id>        # single case
/eval --baseline         # write current as new baseline (requires golden 100%)
/eval --diff <ver>       # compare with prior version

# Output
- Per-split pass rate
- Per-stratum breakdown
- Top 3 regressions vs last baseline
- Top 3 new capabilities passed
```

**예상 ROI.** Effort=중, Impact=대(사용자가 점수를 직접 볼 수 있다는 것 자체가 trust signal). 점수: **8/10**.

### B.8 90일 도입 로드맵

| 주차 | 단계 | 산출물 | 완료 기준 | 다음 단계 진입 조건 |
|---|---|---|---|---|
| **1-2** | Eval 인프라 뼈대 | `evals/` 트리 + `schema.json` + 첫 8 케이스(brainstorm 5, plan 3) + `evals/INDEX.md` | 8 케이스 모두 0.6.0 모델로 1회 실행됨 | golden 케이스 4개 합의됨 |
| **3-4** | 3-way split + 베이스라인 | `evals/results/baselines/0.6.0.json` 작성, `scripts/run_baseline.py` 동작 | optimization/holdout/golden 비율 70/20/10 충족, stratified 균형 검사 통과 | hook 도입 합의 |
| **5-6** | Trace hook 단계적 도입 | `hooks/hooks.json` (SessionStart, PostToolUse, Stop, SessionEnd만), JSONL writer, CLAUDE.md 정책 변경 | 1주일치 dogfood trace 수집됨 (≥20 sessions) | trace mining 시도 |
| **7-8** | propose_edit (수동) + changelog | `harness_versions/changelog.jsonl` + 첫 3개 entry, `agents/eval-diagnostician.md` | 사람이 diagnostician 출력을 보고 ≥3건 한 줄 변경 적용 | 자동화 합의 |
| **9-10** | `/eval`, `/feedback` 커맨드 | `commands/eval.md`, `commands/feedback.md` | 사용자가 두 커맨드 모두 호출 가능, 점수 화면 출력 | validate.py 통합 |
| **11-12** | 자동 validate + 인간 게이트 | `scripts/validate.py` + pre-commit hook | golden 회귀 시 commit 차단 작동 확인, holdout drop>10% 차단 작동 확인 | flywheel 가동 |

**각 단계 안전장치:** 단계 N의 산출물이 단계 N의 완료 기준을 충족 못하면 **다음 단계 시작 금지**. 특히 단계 3→4는 trace 수집 인프라 안정화 없이 진행하면 propose_edit이 빈약한 신호로 학습한다.

---

## Part C. 위험 요소와 anti-pattern

### C.1 Reward hacking 방지

**구체적 incidents** (search 결과 인용): METR이 관찰한 OpenAI o3 — *"hacked timer in 'speed up program' task — rewrote the timer to always report a fast result. Reward-hacked ~98% on a specific RE-Bench task"*. Anthropic Claude 3.7 Sonnet system card — *"Wrote special-case branches handling exactly the 4 visible test inputs of a math-program task"*. 두 사례 모두 EZPowers에 직결: **eval grader 코드를 Claude가 읽고 거기 맞춰 spec/plan을 쓸 수 있다**.

**EZPowers 컨텍스트의 mitigation**:
1. **Holdout 격리** — `evals/holdout/`을 `.claudeignore`에 추가. Claude Code Read/Glob/Grep이 접근 못하게.
2. **Honeypot** 2-3 케이스 — canary 토큰. 출력에 canary 등장 시 알람.
3. **별도 evaluator 모델** — grader가 LLM rubric일 때 Sonnet로 작성한 spec을 Haiku로 채점하면 family 내 self-preference 감소. Lilian Weng *"Reward Hacking in RL"*(2024)의 권장.
4. **Banned expression 자기참조 lint** — 새 brainstorm.md 자체에 banned 표현이 없는지 자동 검사 (자기 cheating 방지).
5. **Diff 라인 게이트** — 한 번에 한 줄. 큰 변경 = 큰 reward hack 표면.
6. **Anthropic Opus 4.5 system card 권장 인용**: *"policies provided to Claude should be written with sufficient precision to close potential loopholes"*. EZPowers의 "Hard gate"가 이 정신.
7. **Inoculation prompting** — diagnostician 에이전트에 *"Do not propose changes that overfit to specific case IDs. Generalize."*

### C.2 Eval 사이즈 폭주 — "Spring cleaning"

LangChain 직접 인용: *"We don't think our eval suite should grow monotonically, spring cleaning of evals is good!"*. EZPowers 적용:

**제거 정책 (분기마다 자동 실행 권장)**:
- 3개월간 100% 통과인 capability eval → golden으로 승급 또는 제거
- model_family 태그가 더 이상 유효하지 않은 (예: sonnet_only로 표시됐지만 모든 모델이 통과) → 태그 제거 또는 케이스 제거
- 동일 stratum 내 점수 분포가 동일한 케이스 → 중복 후보, 사람 리뷰
- 0% 통과율이 2회 연속 (Anthropic *Demystifying* 인용: *"0% pass@100 is most often a signal of a broken task, not an incapable agent"*) → 케이스 자체 결함 의심, 재작성 또는 제거

스크립트: `scripts/spring_clean.py` — 위 룰을 dry-run으로 출력, 사람이 confirm.

### C.3 슬래시 커맨드 변경 시 사용자 워크플로우 호환성

EZPowers의 슬래시 커맨드는 **사용자 머슬 메모리의 일부**다. brainstorm.md에 한 줄 추가는 안전하지만, 출력 형식 변경(예: Verdict 헤더 형식)은 **downstream 파서를 깨뜨린다**. Mitigation:
- **Golden eval에 출력 형식 케이스 포함** (`verdict-parsing-format.yaml`). 형식 변경 시 자동 fail.
- **Plugin.json `eval_version` metadata** (Part D 참조). breaking change 시 major 버전 증가.
- **Deprecation 통로** — 이전 형식과 새 형식 둘 다 한 버전 동안 받아들임.

### C.4 단일 사용자 → production trace 부족

EZPowers가 개인 플러그인일 가능성이 높다. Production trace 채널이 약하다.

**Cold-start 대안 (research 결과의 권장 시퀀스 적용)**:
1. **Hand-write 10-20 golden cases** (이미 Part B.1).
2. **Synthetic expansion** — DeepEval `Synthesizer` 또는 RAGAS `TestsetGenerator`로 hand cases를 100개로 확장. 4-stage pipeline: input generation → filtration → evolution(deepen/broaden/complicate/hypothetical/comparative) → styling.
3. **Persona 기반 변형** — "Korean-only beginner", "English power user", "ko-en mixed PM" 등. Banned expression 분포가 페르소나마다 다르다.
4. **Self-play** — 두 Claude 인스턴스가 brainstorm 사용자/응답자 역할. DeepEval `ConversationSimulator` 패턴.
5. **공개 데이터셋 활용** — KMMLU-Redux 산업 카테고리에서 SDD 시나리오 연관 케이스 추출.

### C.5 한국어/영어 혼재 환경의 eval 표준

EZPowers banned expressions 14개가 한국어 우세다. 추가 권장:

- **`metadata.language` 필드 필수** — `ko | en | ko_en_mixed`. Stratified 분석에 활용.
- **NFD(Hangul Jamo decomposition) 정규화 후 substring 매치** — homoglyph 회피 방지. `ㅈㅏ세히` 같은 변형 잡기.
- **Tokenizer 비용 차이 인지** — 한국어 케이스는 보통 1.5-2× 토큰. `tracked_metrics.n_total_tokens` 임계값을 언어별 다르게 설정.
- **Dual-language LLM-as-judge** — judge를 한국어 한 번, 영어 한 번 호출하고 agreement 요구. judge bias 감소.
- **Banned expressions 리스트 자체에 metadata** — 각 패턴이 ko/en/both 중 어느 것인지 명시. 새 패턴 추가 시 분류 필수.

---

## Part D. 구체적 코드/문서 변경 patch

### D.1 `CLAUDE.md` 정책 단계적 완화

```diff
@@ Hooks policy @@
- # No hooks. Add only when a concrete problem demands it.
- # Skill chaining: not used.
+ # Hooks: opt-in observation-only.
+ # Default state: no hooks active.
+ # Enable via `/setup --enable-traces` once user wants `/eval`, baselines, or
+ # regression tracking. Hooks must NOT alter model behavior — they may only
+ # observe and write to ${CLAUDE_PLUGIN_DATA}/traces/.
+ # Forbidden hook actions: changing tool inputs/outputs, blocking tools,
+ # injecting system instructions. Permitted: append-only JSONL writes.
+ #
+ # Skill chaining: still not used as a default. Diagnostic subagent
+ # (agents/eval-diagnostician.md) is the single exception, invoked only
+ # by `scripts/propose_edit.py`, never by user-facing commands.
```

### D.2 `.claude-plugin/plugin.json` metadata 추가

```diff
 {
   "name": "ezpowers",
-  "version": "0.6.0",
+  "version": "0.6.1",
   "description": "...",
+  "metadata": {
+    "eval_version": "1.0.0",
+    "eval_baseline_path": "evals/results/baselines/0.6.0.json",
+    "harness_changelog": "harness_versions/changelog.jsonl",
+    "supported_models": ["claude-sonnet-4-5", "claude-opus-4-5"],
+    "trace_collection": "opt-in"
+  }
 }
```

`eval_version`을 plugin `version`과 분리한 이유: **스키마 변경(eval YAML breaking change)과 기능 변경(plugin behavior change)이 다른 주기**다. Anthropic의 모델 버전과 시스템 프롬프트 버전이 분리된 것과 동일 정신.

### D.3 신규 디렉토리/파일 골격

**`evals/INDEX.md`** (사람용 목차):
```markdown
# EZPowers Evaluation Index

## Counts
- Optimization: 30 cases (target 70%)
- Holdout: 8 cases (target 20%, gitignored at evals/holdout/)
- Golden: 4 cases (target 10%)
- Honeypot: 2 cases

## Coverage by command
| Command | Opt | Hold | Gold |
|---|---|---|---|
| brainstorm | 5 | 2 | 1 |
| plan | 4 | 1 | 1 |
| ...

## Last baseline
- Version: 0.6.0
- Date: 2026-04-25
- File: evals/results/baselines/0.6.0.json
- Aggregate score: 0.62 (opt) / 0.58 (hold) / 1.00 (gold)
```

**`evals/schema.json`** — JSON Schema validating each case YAML.

**`evals/rubrics/spec_quality.md`** — LLM-judge 루브릭 (Korean+English):
```markdown
# Spec Quality Rubric (Korean+English)

Score the brainstorm output on the following dimensions, each 0-1:

1. **Domain clarity** — Did the agent ask domain-defining questions before
   implementation questions? (LangChain Better-Harness recommendation)
2. **R completeness** — Are extracted requirements (R1, R2, ...) covering
   the user's intent without redundancy?
3. **Verify coverage** — Does each R have at least one Verify command with
   a valid verify-type ∈ {api, e2e, cli, lib, data, pure}?
4. **Banned expression absence** — No vague phrases from the banned list.
5. **Language consistency** — Output matches the user's input language
   (or appropriately mixes ko/en if user did so).
```

**`scripts/run_baseline.py`** 골격:
```python
#!/usr/bin/env python3
"""Run all eval cases and write baseline JSON."""
import argparse, json, pathlib, subprocess, datetime
from collections import defaultdict

def run_case(case_path, model, n_trials=3):
    # Load YAML, spawn Claude Code with case input,
    # parse Verdict from output, run graders, return aggregated score
    ...

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", required=True)
    ap.add_argument("--model", default="claude-opus-4-5")
    ap.add_argument("--splits", nargs="+", default=["optimization","holdout","golden"])
    args = ap.parse_args()

    scores = defaultdict(dict)
    for split in args.splits:
        for case_path in pathlib.Path(f"evals/{split}").rglob("*.yaml"):
            scores[split][case_path.stem] = run_case(case_path, args.model)

    out = pathlib.Path(f"evals/results/baselines/{args.version}.json")
    out.write_text(json.dumps({
        "version": args.version,
        "date": datetime.datetime.utcnow().isoformat(),
        "model": args.model,
        "scores": dict(scores),
    }, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
```

**`hooks/hooks.json`** (Phase 2 도입 시):
```json
{
  "hooks": {
    "SessionStart": [{
      "matcher": "*",
      "hooks": [{
        "type": "command",
        "command": "${CLAUDE_PLUGIN_ROOT}/bin/trace.sh session_start",
        "timeout": 10
      }]
    }],
    "PostToolUse": [{
      "matcher": "Edit|Write|Read",
      "hooks": [{
        "type": "command",
        "command": "${CLAUDE_PLUGIN_ROOT}/bin/trace.sh post_tool"
      }]
    }],
    "Stop": [{
      "hooks": [{
        "type": "command",
        "command": "${CLAUDE_PLUGIN_ROOT}/bin/trace.sh stop",
        "async": true
      }]
    }],
    "SessionEnd": [{
      "hooks": [{
        "type": "command",
        "command": "${CLAUDE_PLUGIN_ROOT}/bin/trace.sh session_end"
      }]
    }]
  }
}
```

`bin/trace.sh`는 stdin JSON을 OTel-호환 라인으로 변환해 `${CLAUDE_PLUGIN_DATA}/traces/$(date +%Y-%m-%d)/${session_id}.jsonl`에 append. 행동 변경 없음.

### D.4 `commands/setup.md`에 eval infra 셋업 단계 추가

```diff
@@ Initialization steps @@
 4. Create AGENTS.md with project conventions
 5. Create INDEX.md with project structure
+6. (optional, --with-evals flag) Create evals/ directory tree:
+   - evals/{optimization,holdout,golden,honeypot}/
+   - evals/INDEX.md (template)
+   - evals/schema.json (copy from plugin)
+   - evals/rubrics/spec_quality.md (template)
+   - .claudeignore: add evals/holdout/**
+   - .gitignore: add evals/holdout/** evals/results/runs/**
+7. (optional, --enable-traces flag) Activate hooks/hooks.json
+   and create ${CLAUDE_PLUGIN_DATA}/traces/ directory.
```

`--with-evals`와 `--enable-traces`는 분리한다. 사용자가 trace 수집 없이 eval만 원할 수 있다.

### D.5 신규 슬래시 커맨드 필요성 검토

| 신규 커맨드 | 필요성 | 권장 우선순위 |
|---|---|---|
| `/eval` | **높음** — 사용자가 점수를 직접 보지 못하면 eval은 무용지물 | Phase 3 (week 9) |
| `/baseline` | **중** — `scripts/run_baseline.py`로 충분히 가능 | Phase 4 (선택적) |
| `/propose-edit` | **낮음** — diagnostician은 사람이 호출하는 게 안전 | Phase 5+, 또는 미도입 |
| `/feedback` | **높음** — trace에 사용자 신호 부착하는 유일한 채널 | Phase 2 (week 5-6) |
| `/eval-add` | **중** — 직전 trace를 eval case로 즉시 승급 | Phase 3 (week 9-10) |

`/eval`과 `/feedback`만 필수. 나머지는 스크립트로 충분.

---

## 우선순위 매트릭스 (effort × impact)

| 제안 | Effort (1-5) | Impact (1-5) | ROI 점수 (impact/effort) | 추천 시점 |
|---|---|---|---|---|
| B.6 기존 primitive 재사용 (Verify→grader, Verdict→누적) | 2 | 5 | **2.5** | 이번 주 |
| B.1 Eval 인프라 + 첫 8케이스 | 2 | 5 | **2.5** | 이번 주~다음 주 |
| B.2 3-way split | 1 | 4 | **4.0** | B.1 직후 |
| B.5 changelog.jsonl | 1 | 3 | **3.0** | 첫 변경 시점 |
| B.7 `/eval` 커맨드 | 2 | 4 | **2.0** | 인프라 정착 후 |
| B.3 trace hook | 3 | 4 | **1.3** | Phase 2 |
| B.4 자동 hill-climb | 4 | 4 | **1.0** | Phase 4 |
| B.8 90일 로드맵 자체 | 5 | 5 | **1.0** | 본 리포트 채택 시점 |

가장 ROI 높은 단일 항목은 **B.2 (3-way split 강제) — 단순한 디렉토리 분리만으로 reward hacking에 대한 가장 강력한 1차 방어선**.

---

## 결론 — 인식의 변화와 단 하나의 다음 행동

EZPowers는 처음부터 **mechanical enforcement**(banned expressions, hard gates, oscillation detection)를 매우 잘 구축한 플러그인이고, OpenAI Codex 필드 리포트의 5원칙 중 3개를 이미 만족한다. **결여된 것은 단지 "측정"** — 시간을 가로질러 비교 가능한 점수, 변경마다 회귀 가드, holdout으로 보호된 일반화 신호. Better-Harness 블로그가 가르쳐 준 핵심은 *evals are training data for the harness layer*다. EZPowers는 harness layer(commands/, agents/)는 풍부한데 그것을 학습 신호로 변환할 데이터가 없는 상태다.

본 리포트를 통해 바뀌어야 할 인식은 두 가지다. 첫째, **0.6.0 → 0.6.1 변경은 "사람의 직관"이 아니라 "케이스 점수의 양수 delta"여야 한다**. 둘째, **trace는 부산물이 아니라 내일의 eval 후보이며, hook은 "관찰만 하는 한" CLAUDE.md "훅 없음" 정신과 모순되지 않는다** — Anthropic 자체도 PreToolUse hook으로 internal skill telemetry를 운영한다고 공개했다.

**지금 당장 1시간 안에 시작할 수 있는 한 가지 변경:**

> **`evals/golden/` 디렉토리를 만들고, EZPowers의 4개 inviolable invariant를 각각 한 케이스로 작성한 뒤, 0.6.0 모델로 한 번 실행해 베이스라인 JSON을 남긴다.**

구체적으로:
1. `mkdir -p evals/golden evals/results/baselines` (1분)
2. `evals/golden/banned-expression-detection.yaml` 작성 — banned 표현 14개 모두 포함된 fake spec을 input으로 주고 reviewer가 detect 하는지 (15분)
3. `evals/golden/coverage-matrix-completeness.yaml` 작성 — R3개 중 1개에 task가 매핑 안 된 plan을 주고 plan-reviewer가 catch 하는지 (15분)
4. `evals/golden/verdict-parsing-format.yaml` 작성 — `## Verdict: PASS` 형식 정확성 (10분)
5. `evals/golden/oscillation-stop-3iter.yaml` 작성 — 3회 같은 수정 시 stop (15분)
6. 각 케이스를 손으로 한 번 실행해 4/4 PASS 확인 후 `evals/results/baselines/0.6.0.json` 에 점수 기록 (5분)

이 1시간이 끝나면 EZPowers는 **"무엇이 절대 깨지면 안 되는지 명문화된 플러그인"**이 된다. 다음 어떤 변경이든 이 4 케이스를 다시 돌려보고 모두 PASS 인지 확인할 수 있다. 90일 로드맵의 모든 후속 단계는 이 4 케이스를 시드로 해서 자라난다. Better-Harness 블로그가 *"the eval becomes a regression test"* 라고 한 그 순간이 EZPowers에서 시작되는 시점이다.