# EZPowers 개선 프롬프트 — Claude Code 실행용

블루프린트 문서(`Better-Harness-EZPowers-Blueprint.md`)를 Claude Code에 입력으로 주고 단계별로 실행시키는 프롬프트 세트.

## 사전 준비

1. 블루프린트 markdown을 EZPowers 리포 루트의 `docs/Better-Harness-EZPowers-Blueprint.md`로 저장
2. 새 git branch 생성: `git checkout -b feature/eval-driven-harness`
3. Claude Code를 EZPowers 리포 루트에서 실행 (`cd EZPowers && claude`)
4. **각 Phase는 별도 세션으로 실행 권장** (컨텍스트 격리, 회귀 차단)

## 실행 원칙

- Phase 0부터 순서대로. **Phase N의 verification이 통과해야 Phase N+1 진입**
- 각 Phase 끝나면 `git commit`. branch는 그대로 두고 다음 Phase 시작
- 프롬프트 안의 `[BRACKETS]`는 그대로 두지 말고 실제 값으로 치환
- 모든 변경은 단일 PR로 합치지 말고 Phase별로 분리 PR

---

# Phase 0 — 1시간 안에 시작 (Golden Eval Seed)

> 블루프린트 결론에서 추천한 단일 다음 행동. EZPowers의 4개 inviolable invariant를 골든 이밸 케이스로 박제.

**예상 시간**: 60-90분
**산출물**: 4 golden cases, 1 baseline JSON, 1 INDEX.md

```
You are working on the EZPowers Claude Code plugin (https://github.com/dlwlgus9125/EZPowers, version 0.6.0).

Read this blueprint document first and understand the full context:
@docs/Better-Harness-EZPowers-Blueprint.md

Your task is the "1시간 안에 시작할 수 있는 한 가지 변경" specified in the blueprint's conclusion section. Execute it precisely, no more no less.

## HARD-GATE — DO NOT VIOLATE

1. Do NOT modify any existing file under `commands/`, `agents/`, or `skills/`.
2. Do NOT add hooks, do NOT install dependencies, do NOT touch CLAUDE.md.
3. Only create files under `evals/` and update `.gitignore` and `.claudeignore`.
4. Each golden case YAML must be a valid YAML file passing the schema in the blueprint Part B.1.
5. The 4 golden cases must cover the 4 invariants listed in blueprint Part B.2 "Golden regression set 정의" section verbatim:
   - banned-expression-detection
   - coverage-matrix-completeness
   - verdict-parsing-format
   - oscillation-stop-3iter

## Steps

### Step 1: Read context

- Read `CLAUDE.md` to understand current "no hooks / no skill chaining" policy.
- Read `commands/brainstorm.md` lines 192-208 to extract the exact 14 banned expressions.
- Read `commands/plan.md` lines 51-83 for Coverage Matrix structure.
- Read `commands/choiceexecutor.md` for Verdict parsing format and oscillation detection logic.
- Read `agents/spec-reviewer.md` and `agents/plan-reviewer.md` for Verdict header format.

### Step 2: Create directories

```bash
mkdir -p evals/{optimization,holdout,golden,honeypot,rubrics,results/baselines,results/runs}
```

### Step 3: Create schema and INDEX

- Create `evals/schema.json` — JSON Schema validating the YAML case format defined in blueprint Part B.1.
- Create `evals/INDEX.md` using the template from blueprint Part D.3.
- Create `evals/rubrics/spec_quality.md` using the template from blueprint Part D.3.

### Step 4: Create 4 golden case YAMLs

Each case file must include:
- `case_id` following `golden.<invariant>.001` pattern
- `split: golden`
- `stratum` with all 6 keys (command, difficulty, pattern, model_family, language, verify_type)
- `input.user_message` — a concrete fake user prompt that should trigger the invariant check
- `graders` — at least one `deterministic_tests` and one `llm_rubric`
- `tracked_metrics`

The 4 files:

1. **`evals/golden/banned-expression-detection.yaml`**
   - Input: A fake spec containing ALL 14 banned expressions (7 Korean, 7 English) embedded in R sections
   - Expected: spec-reviewer agent must detect and FAIL
   - Grader: deterministic test that greps the reviewer output for "FAIL" and checks all 14 expressions are listed in Issues Found

2. **`evals/golden/coverage-matrix-completeness.yaml`**
   - Input: A fake plan with 3 R requirements but Coverage Matrix only maps R1 and R2 (R3 unmapped)
   - Expected: plan-reviewer must FAIL with "Unmapped R: R3"
   - Grader: deterministic test that exact-matches "R3" in unmapped list

3. **`evals/golden/verdict-parsing-format.yaml`**
   - Input: Two reviewer outputs — one with correct `## Verdict: PASS` header, one with non-standard `Verdict: PASS` (no `##`)
   - Expected: First parsed as PASS, second treated as FAIL per choiceexecutor.md rule
   - Grader: parse simulation script

4. **`evals/golden/oscillation-stop-3iter.yaml`**
   - Input: Simulated 3-iteration sequence where same `{section}:{check_number}` key appears in iterations 1, 2, 3
   - Expected: Oscillation detected at iteration 3, user escalation triggered
   - Grader: deterministic test on log output

### Step 5: Manually verify each case

For each of the 4 cases, run a manual mock execution:
- Read the case YAML
- Read the relevant existing EZPowers command/agent file
- Trace through what the existing logic would do given the input
- Confirm the expected output matches
- Document the trace in `evals/results/baselines/0.6.0.json`

### Step 6: Write baseline JSON

Create `evals/results/baselines/0.6.0.json`:
```json
{
  "version": "0.6.0",
  "date": "<today ISO>",
  "model": "manual-trace-only",
  "scores": {
    "golden": {
      "banned-expression-detection.001": {"pass": true, "trace_summary": "..."},
      "coverage-matrix-completeness.001": {"pass": true, "trace_summary": "..."},
      "verdict-parsing-format.001": {"pass": true, "trace_summary": "..."},
      "oscillation-stop-3iter.001": {"pass": true, "trace_summary": "..."}
    }
  },
  "notes": "Phase 0 manual baseline. No automated runner yet."
}
```

### Step 7: Update ignore files

- Add to `.gitignore`:
  ```
  # Holdout eval cases — never commit, see blueprint Part B.2
  evals/holdout/**
  !evals/holdout/.gitkeep
  evals/results/runs/**
  ```
- Create `.claudeignore` (or update if exists) with:
  ```
  evals/holdout/**
  ```
- Create `evals/holdout/.gitkeep` empty file.

### Step 8: Update INDEX.md and verify counts

Update `evals/INDEX.md` "Counts" section to reflect actual numbers (4 golden, 0 others).

### Step 9: Final verification

Run these checks and report results:
1. `find evals -type f -name "*.yaml" | wc -l` returns 4
2. `cat evals/results/baselines/0.6.0.json | jq '.scores.golden | length'` returns 4
3. `git status` shows only new files under `evals/`, `.gitignore`, `.claudeignore`
4. No file under `commands/`, `agents/`, `skills/`, `CLAUDE.md` was modified

If ALL 4 checks pass, output:
```
## Verdict: PASS

Phase 0 complete. Created 4 golden cases + baseline + INDEX.
Next: commit with message "feat: add golden eval seed (Phase 0)" then start Phase 1.
```

If ANY check fails:
```
## Verdict: FAIL

[list specific failures]
```

## Anti-patterns to avoid

- DO NOT make up new banned expressions; copy verbatim from brainstorm.md L192-208.
- DO NOT skip Step 5 manual verification; the baseline must reflect actual behavior, not assumed.
- DO NOT add cases beyond the 4 specified; scope creep defeats the purpose of Phase 0.
- DO NOT modify CLAUDE.md "no hooks" policy yet — that is Phase 2's job.
```

**Phase 0 Verification (사용자 직접 확인)**:
```bash
ls evals/golden/        # 4 yaml 파일 보여야 함
cat evals/results/baselines/0.6.0.json | jq '.scores.golden'
git diff --stat         # commands/, agents/ 건드리지 않았는지
```

통과하면 commit:
```bash
git add evals/ .gitignore .claudeignore
git commit -m "feat: add golden eval seed (Phase 0)

- 4 inviolable invariants captured as golden eval cases
- evals/ tree initialized per blueprint Part B.1
- holdout gitignored + claudeignored per blueprint Part B.2
- 0.6.0 manual baseline established"
```

---

# Phase 1 — Eval Infrastructure 본격 구축 (Optimization Cases)

**전제 조건**: Phase 0 commit 완료
**예상 시간**: 4-6시간 (분할 권장)
**산출물**: 30개 optimization cases + run_baseline.py + 첫 자동 베이스라인

```
Continue improving EZPowers based on the blueprint at:
@docs/Better-Harness-EZPowers-Blueprint.md

Phase 0 has completed: golden cases exist at evals/golden/ and baseline 0.6.0 is recorded.

This is Phase 1: build the optimization eval set + automated baseline runner.

## HARD-GATE

1. Do NOT modify the 4 golden cases.
2. Do NOT touch holdout/ — those are Phase 1.5 (separate session).
3. The runner script must be self-contained Python, no external dependencies beyond stdlib + PyYAML.
4. Follow blueprint Part B.1 case schema EXACTLY. Validate every YAML against evals/schema.json before saving.

## Target case counts (blueprint Part B.1 table)

| Command | Optimization cases |
|---|---|
| brainstorm | 5 |
| plan | 4 |
| choiceexecutor | 5 |
| setup | 3 |
| executeharness | 2 |
| review | 2 |
| sync-docs | 2 |
| contract (stage interfaces) | 7 |
| **Total** | **30** |

## Steps

### Step 1: Generate cases iteratively

For EACH command, work through this loop:
1. Read the command file (e.g., `commands/brainstorm.md`)
2. Identify N distinct realistic user input scenarios
3. For each scenario, write a case YAML at `evals/optimization/<command>/<scenario-slug>.yaml`
4. Run `python -c "import yaml; yaml.safe_load(open('<path>'))"` to validate parsing
5. Run schema validation against `evals/schema.json`

### Step 2: Diversity requirements per command

Brainstorm 5 cases MUST cover:
- 1 greenfield (empty repo)
- 1 brownfield (existing code, feature add)
- 1 refactor (narrow scope)
- 1 vague-spec-ko (Korean input with ambiguity, banned expression trap)
- 1 multi-R-coverage (>=5 requirements expected)

Plan 4 cases MUST cover:
- 1 simple 3-R spec
- 1 large 10-R spec
- 1 missing-verify spec (should be caught)
- 1 refactor with impact-scope analysis

ChoiceExecutor 5 cases MUST cover:
- 1 inline-trivial (single-task plan)
- 1 harness-needed (>=4 tasks, recommend harness)
- 1 security-keyword-trip (auth/token in task description)
- 1 oscillation-trap (3 same-issue iterations)
- 1 resume-mid-task (Resume Protocol triggered)

Contract 7 cases MUST cover stage interfaces:
- brainstorm → plan: spec format consumed correctly
- plan → choiceexecutor: task structure parsed
- choiceexecutor → security-reviewer: changed-files passed correctly
- choiceexecutor → code-reviewer: diff range passed correctly
- spec-reviewer → brainstorm: Verdict header parsing
- plan-reviewer → plan: Verdict header parsing
- code-reviewer → choiceexecutor: Verdict header parsing

### Step 3: Stratification check

Before proceeding, verify case distribution:
```bash
python3 << 'EOF'
import yaml, glob
from collections import Counter
cases = [yaml.safe_load(open(f)) for f in glob.glob('evals/optimization/**/*.yaml', recursive=True)]
print("Total:", len(cases))
print("By command:", Counter(c['stratum']['command'] for c in cases))
print("By difficulty:", Counter(c['stratum']['difficulty'] for c in cases))
print("By language:", Counter(c['stratum']['language'] for c in cases))
print("By model_family:", Counter(c['stratum']['model_family'] for c in cases))
EOF
```

Expected: Total=30, command counts match the table, difficulty has all 3 levels (single_step, multi_step, long_horizon), language has at least 2 of {ko, en, ko_en_mixed}.

### Step 4: Build run_baseline.py

Create `scripts/run_baseline.py` per blueprint Part D.3 skeleton. Key requirements:
- argparse with `--version`, `--model`, `--splits`, `--cases` (single case override)
- For each case YAML, execute via headless mode: `claude --no-interactive < case.input.user_message`
  - If headless mode unavailable, skip and log "manual" mode
- Parse output for `## Verdict: PASS|FAIL`
- Run each grader:
  - `deterministic_tests`: shell exec, exit 0 = pass
  - `llm_rubric`: skip in v1 (requires separate Claude call, mark as "not_run")
- Write results to `evals/results/baselines/0.6.0.json` (overwrite if `--baseline` flag) or `evals/results/runs/<timestamp>-<git-sha>.jsonl`

### Step 5: Run baseline on golden + optimization

```bash
python scripts/run_baseline.py --version 0.6.0 --model claude-opus-4-5 --splits golden optimization
```

Expected: golden 4/4 pass, optimization variable (this is the actual baseline).

### Step 6: Update INDEX.md counts

Update `evals/INDEX.md` to show:
- Optimization: 30 cases
- Holdout: 0 (still pending)
- Golden: 4
- Honeypot: 0

### Step 7: Generate report

Create `evals/results/baselines/0.6.0-report.md`:
- Overall pass rate
- Per-command breakdown
- Top 3 weakest commands (by pass rate)
- Top 3 strongest commands

This report will guide which command to hill-climb first in Phase 4.

## Verdict requirements

Output `## Verdict: PASS` only if:
1. 30 optimization YAMLs created and schema-valid
2. Stratification check passes per Step 3
3. run_baseline.py executes without error
4. evals/results/baselines/0.6.0.json now contains both golden AND optimization scores
5. Report generated

Otherwise `## Verdict: FAIL` with specific list.
```

**Phase 1 Verification**:
```bash
find evals/optimization -name "*.yaml" | wc -l    # 30
python scripts/run_baseline.py --version 0.6.0 --splits golden
cat evals/results/baselines/0.6.0-report.md
```

---

# Phase 1.5 — Holdout Set 작성 (별도 세션 필수)

> Reward hacking 방지의 핵심. 이 Phase는 **별도 git branch + 별도 세션**에서, 이후 Phase에서 노출되지 않도록 분리.

**전제 조건**: Phase 1 commit 완료, **별도 worktree 또는 새 Claude Code 세션**
**예상 시간**: 2-3시간

```
You are working on EZPowers in ISOLATION mode.

CRITICAL: This session creates HOLDOUT eval cases. These cases must NEVER be referenced in any future optimization work, prompt edits, or hill-climbing iterations. Treat them as test set in ML — sacred unseen data.

Read blueprint Part B.2 "Holdout 노출 방지 메커니즘" section.
@docs/Better-Harness-EZPowers-Blueprint.md

## Pre-flight check

```bash
cat .gitignore | grep "evals/holdout"   # must show
cat .claudeignore | grep "evals/holdout" # must show
```

If either missing, STOP and report.

## Steps

### Step 1: Generate 8 holdout cases

Same diversity criteria as optimization (Phase 1 Step 2) but DIFFERENT specific scenarios. The holdout cases must be DISTINCT from optimization cases — not reworded duplicates.

Distribution:
- brainstorm: 2
- plan: 1
- choiceexecutor: 2
- contract: 2
- setup or executeharness: 1

### Step 2: Add canary tokens

Each holdout case MUST include in metadata:
```yaml
canary: "EZPOWERS_HOLDOUT_DO_NOT_TRAIN_<random-8-char-hex>"
```

Generate the hex per case: `python3 -c "import secrets; print(secrets.token_hex(4))"`

### Step 3: Generate 2 honeypot cases

Place at `evals/honeypot/`:
- 1 case with intentionally-trivial expected answer (any reasonable agent should pass; if score is suspiciously high it suggests training contamination)
- 1 case with a deliberately-misleading premise that should trigger the agent to ASK rather than ANSWER

### Step 4: Verify isolation

```bash
git status                              # holdout files NOT tracked
git check-ignore evals/holdout/*.yaml   # must return paths (= ignored)
```

### Step 5: Backup outside repo

Copy `evals/holdout/` to a private location outside the repo:
- macOS/Linux: `~/.ezpowers-private/holdout/`
- Windows: `%USERPROFILE%\.ezpowers-private\holdout\`

This is the canonical store. The repo's `evals/holdout/` exists only for runner script lookups.

### Step 6: Update INDEX.md

Update count to "Holdout: 8 cases (gitignored)".

DO NOT list case names. DO NOT describe scenarios. Only the count.

### Step 7: Run holdout baseline

```bash
python scripts/run_baseline.py --version 0.6.0 --splits holdout
```

Append results to `evals/results/baselines/0.6.0.json` under `scores.holdout`.

## Verdict

`## Verdict: PASS` only if:
1. 8 holdout YAMLs in evals/holdout/
2. Each has unique canary token
3. 2 honeypot YAMLs in evals/honeypot/
4. git status clean for evals/holdout/ (untracked AND ignored)
5. Backup exists outside repo
6. INDEX.md shows count only, no descriptions
7. Baseline includes holdout scores

After PASS, this session ENDS. Do not continue. Start a fresh session for Phase 2.
```

**Phase 1.5 commit (홀드아웃은 ignore되므로 INDEX.md 업데이트만 commit)**:
```bash
git add evals/INDEX.md evals/results/baselines/0.6.0.json evals/honeypot/
git commit -m "feat: add holdout (gitignored) + honeypot eval sets (Phase 1.5)"
```

---

# Phase 2 — Trace Hooks 단계적 도입

**전제 조건**: Phase 1 + 1.5 완료
**예상 시간**: 1일

```
EZPowers Phase 2: opt-in trace collection hooks.

Read these blueprint sections:
@docs/Better-Harness-EZPowers-Blueprint.md

Specifically Part B.3 (Trace 수집 인프라), Part D.1 (CLAUDE.md 정책 변경), Part D.3 (hooks.json 골격).

## HARD-GATE

1. Hooks must be OPT-IN. Default state: no hooks active.
2. Hooks must be OBSERVATION-ONLY. Forbidden:
   - Modifying tool inputs/outputs
   - Blocking tool calls
   - Injecting system instructions
   Permitted: append-only writes to ${CLAUDE_PLUGIN_DATA}/traces/
3. CLAUDE.md must be updated per blueprint Part D.1 diff EXACTLY.
4. golden eval cases must continue passing after this change.

## Steps

### Step 1: Update CLAUDE.md

Apply the diff from blueprint Part D.1 to the "Hooks" section. Do not change anything else in CLAUDE.md.

### Step 2: Create hooks/hooks.json

Use the skeleton from blueprint Part D.3. Only these 4 hooks:
- SessionStart
- PostToolUse (matcher: Edit|Write|Read)
- Stop
- SessionEnd

DO NOT add UserPromptSubmit, PreToolUse, PostToolBatch, SubagentStop in this phase. Those are Phase 3+.

### Step 3: Create bin/trace.sh

Single shell script that:
- Reads JSON from stdin (Claude Code hook input)
- Determines event type from $1 argument
- Appends a single OTel-compatible JSON line to `${CLAUDE_PLUGIN_DATA:-$HOME/.ezpowers-traces}/$(date +%Y-%m-%d)/${session_id}.jsonl`
- Returns exit 0 always (never blocks Claude Code)

Use the JSONL schema from blueprint Part B.3.

### Step 4: Update setup.md

Add the diff from blueprint Part D.4 — `--enable-traces` flag handling.

### Step 5: Update plugin.json

Apply diff from blueprint Part D.2:
- Bump version to 0.7.0 (this is a meaningful capability change)
- Add metadata block

### Step 6: Run regression check

```bash
python scripts/run_baseline.py --version 0.7.0 --splits golden
```

Compare against 0.6.0 golden scores. ALL 4 must still pass. If any regress, ROLLBACK and report.

Compare against 0.6.0 optimization scores. Average delta must be within ±5%. Larger delta suggests the documentation changes accidentally affected behavior.

### Step 7: Manual hook smoke test

```bash
# Enable hooks temporarily
mkdir -p ~/.claude/hooks
cp hooks/hooks.json ~/.claude/hooks/

# Run any EZPowers command
echo "test" | claude --no-interactive

# Verify trace was written
ls ~/.ezpowers-traces/$(date +%Y-%m-%d)/
cat ~/.ezpowers-traces/$(date +%Y-%m-%d)/*.jsonl | head
```

Trace file must exist with at least SessionStart and SessionEnd events. PostToolUse should fire if Read/Write was called.

## Verdict

PASS if:
1. CLAUDE.md diff applied (verify with `git diff CLAUDE.md`)
2. hooks/hooks.json valid JSON
3. bin/trace.sh executable and idempotent
4. plugin.json version 0.7.0 with metadata
5. Golden 4/4 still pass
6. Optimization average delta within ±5%
7. Manual smoke test produced trace file
```

**Phase 2 commit**:
```bash
git add CLAUDE.md hooks/ bin/ commands/setup.md .claude-plugin/plugin.json
git commit -m "feat: opt-in trace collection hooks (Phase 2)

- Hooks observation-only per CLAUDE.md updated policy
- 4 hooks: SessionStart, PostToolUse, Stop, SessionEnd
- bin/trace.sh writes OTel-compatible JSONL
- --enable-traces flag added to /setup
- Bump 0.6.0 → 0.7.0"
```

---

# Phase 3 — `/eval` 슬래시 커맨드 + `/feedback`

**전제 조건**: Phase 2 완료, 1주일치 trace 누적
**예상 시간**: 4-6시간

```
EZPowers Phase 3: user-facing eval and feedback slash commands.

Read blueprint Part B.7 ("/eval 신규 슬래시 커맨드") and Part B.3 ("사용자 피드백 수집").

@docs/Better-Harness-EZPowers-Blueprint.md

## Steps

### Step 1: Create commands/eval.md

Follow EZPowers existing command file conventions (see commands/brainstorm.md, commands/plan.md for style):
- Frontmatter? No (existing commands don't use it for slash commands)
- Sections: Usage, Process Flow, Hard Gates, Output, Verification, Common Rationalizations
- Body must invoke scripts/run_baseline.py

Required subcommands:
- `/eval` — run all splits, compact output
- `/eval optimization` — single split
- `/eval --case <id>` — single case
- `/eval --baseline` — write current as new baseline (gated: golden 100% required)
- `/eval --diff <prior-version>` — compare two baselines

Output format must include:
- Per-split pass rate (X/Y, percentage)
- Per-stratum breakdown (markdown table)
- Top 3 regressions vs last baseline
- Top 3 new capabilities passed
- Final `## Verdict: PASS|FAIL` line per EZPowers convention

### Step 2: Create commands/feedback.md

Required behavior:
- `/feedback +1` — append positive score to last session's trace
- `/feedback -1 "reason"` — append negative score with comment
- `/feedback last "comment"` — comment-only, no score

Implementation:
- Reads `${CLAUDE_PLUGIN_DATA}/traces/$(date +%Y-%m-%d)/*.jsonl` newest file
- Modifies last entry's `scores` array per Langfuse `create_score` schema
- Reports back which trace was annotated

### Step 3: Create scripts/promote_trace.py

Per blueprint Part B.3 "Trace → eval candidate 변환":
- Load traces from last N days (arg)
- Filter by `scores.user-feedback == -1`
- Display each candidate trace with input/output summary
- Prompt user: "Promote to eval case? [y/N/skip]"
- If yes: prompt for split (optimization/holdout) and stratum tags
- Write new YAML at `evals/<split>/<command>/<auto-slug>.yaml`

### Step 4: Update CLAUDE.md "Main Flow" section

Add `/eval` and `/feedback` to the Independent Utilities table:

| Command | Purpose |
|---|---|
| `/eval` | Run eval suite, report version score |
| `/feedback` | Annotate current session's trace with user score |

### Step 5: Update plugin.json

Bump 0.7.0 → 0.7.1.

### Step 6: Self-test

Use `/eval` itself to verify:
```bash
# In Claude Code session
/eval golden
```

Expected: 4/4 pass, output formatted correctly, ends with `## Verdict: PASS`.

```bash
/eval --diff 0.6.0
```

Expected: shows delta vs 0.6.0 baseline.

### Step 7: Regression check

Golden 4/4 must still pass. Optimization average within ±5% of 0.7.0 baseline.

## Verdict

PASS if all 7 steps complete and self-test produces correct output.
```

**Phase 3 commit**:
```bash
git add commands/eval.md commands/feedback.md scripts/promote_trace.py CLAUDE.md .claude-plugin/plugin.json
git commit -m "feat: /eval and /feedback slash commands (Phase 3)

- /eval runs eval suite, reports per-split scores
- /feedback annotates last trace with user score
- scripts/promote_trace.py promotes negative-feedback traces to eval cases
- Bump 0.7.0 → 0.7.1"
```

---

# Phase 4 — 첫 Hill-Climb (수동, eval-diagnostician 도입)

**전제 조건**: Phase 3 완료. `/eval`로 약점 명령 식별됨.
**예상 시간**: 2-3시간

```
EZPowers Phase 4: first manual hill-climb iteration with diagnostic subagent.

Read blueprint Part B.4 (Hill-climbing 6단계 루프), Part B.5 (변경 추적).

@docs/Better-Harness-EZPowers-Blueprint.md

## HARD-GATE

1. Change MUST be a single line addition or modification (max 3 consecutive lines).
2. Change MUST target ONE file under commands/ or agents/.
3. Change MUST NOT modify evals/ (anti-cheating).
4. After change: golden 4/4 must still pass. Holdout average must not drop >10%.
5. After change: optimization average must increase. If not, ROLLBACK and try different change.

## Pre-flight

```bash
/eval optimization
```

Identify the command with lowest pass rate. This is the hill-climb target.

## Steps

### Step 1: Create agents/eval-diagnostician.md

Use the skeleton from blueprint Part B.4. Required frontmatter:
```yaml
---
name: eval-diagnostician
description: Analyzes failing eval traces and proposes ONE line change.
tools: [Read, Grep, Glob]
model: claude-opus-4-5
maxTurns: 8
---
```

Body must include:
- Hard constraints (≤3 line diff, single file, forbidden targets)
- Output JSON schema (file, line, before, after, expected_improvements, rationale)
- Trace cluster analysis instructions

### Step 2: Create harness_versions/changelog.jsonl

Initialize with header entry:
```json
{"date":"<today>","version":"0.7.1","event":"changelog_initialized","author":"human"}
```

### Step 3: Run diagnostician on failing cases

Dispatch the eval-diagnostician subagent with:
- Input: list of failing case IDs from Step 0
- Their trace files
- The relevant command file content

Expected output: one JSON object matching the schema.

### Step 4: Apply proposed change

- Verify diff line count ≤ 3
- Verify target file is under commands/ or agents/
- Apply with str_replace, NOT a manual rewrite
- Show the diff

### Step 5: Run validation

```bash
python scripts/run_baseline.py --version 0.7.2-rc --splits golden optimization
```

Compare with 0.7.1 baseline:
- Golden: must remain 4/4
- Optimization: must show net positive delta
- The specific cases listed in `expected_improvements` must flip from FAIL to PASS

If golden regresses or no improvement, ROLLBACK:
```bash
git checkout -- <changed-file>
```

### Step 6: Run holdout check

```bash
python scripts/run_baseline.py --version 0.7.2-rc --splits holdout
```

Compare holdout average with 0.7.1.
- Allowed: ±10% delta
- Beyond ±10%: ROLLBACK regardless of optimization gain (overfit signal)

### Step 7: Append changelog entry

If validation passes, append to `harness_versions/changelog.jsonl` per blueprint Part B.5 schema:
```json
{"date":"<today>","version":"0.7.2","file":"<path>","line":<n>,"before":"<text>","after":"<text>","motivation_trace_id":"<from diagnostician>","eval_delta":{"optimization":{"before":<x>,"after":<y>,"cases_flipped_to_pass":[...]},"holdout":{"before":<a>,"after":<b>}},"author":"human","reviewer":"eval-diagnostician","rationale":"<one sentence>"}
```

### Step 8: Bump version

plugin.json: 0.7.1 → 0.7.2.

Save new baseline:
```bash
python scripts/run_baseline.py --version 0.7.2 --baseline
```

## Verdict

PASS if:
1. eval-diagnostician.md created with valid frontmatter
2. Single change ≤3 lines applied
3. Golden 4/4 maintained
4. Optimization average increased
5. Holdout within ±10%
6. Expected cases flipped to PASS
7. changelog.jsonl entry recorded
8. New baseline 0.7.2 saved

If any fail: rollback the change file, but keep eval-diagnostician.md and changelog.jsonl skeleton (those are infrastructure, not the change).
```

**Phase 4 commit**:
```bash
git add agents/eval-diagnostician.md harness_versions/ <changed-command-file> .claude-plugin/plugin.json evals/results/baselines/0.7.2.json
git commit -m "feat: first eval-driven hill-climb (Phase 4)

- Add eval-diagnostician subagent
- Initialize harness_versions/changelog.jsonl
- Apply 1 hill-climb change to <file> (improved <N> cases)
- Bump 0.7.1 → 0.7.2"
```

---

# Phase 5 — 자동 Validation Gate (pre-commit hook)

**전제 조건**: Phase 4 완료, 한 번 이상 hill-climb 성공 경험
**예상 시간**: 3-4시간

```
EZPowers Phase 5: enforce eval gate on every commit touching commands/ or agents/.

Read blueprint Part B.4 "Validation step 체크리스트" and "한 번에 한 줄 정책 코드 강제".

@docs/Better-Harness-EZPowers-Blueprint.md

## Steps

### Step 1: Create scripts/validate.py

Implement the validate.py from blueprint Part B.4. Mandatory checks in order:
1. Diff line count ≤ 3 for files under commands/ or agents/
2. evals/ not modified (forbidden in same commit as commands/agents/ changes)
3. Golden 4/4 pass
4. Optimization delta ≥ 0 (no regression)
5. Holdout delta within ±10%
6. Self-referential banned expression scan on changed text

Each check outputs `[PASS|FAIL] <check_name>: <details>`.

Exit code: 0 if all pass, 1 if any fail.

### Step 2: Create .githooks/pre-commit

```bash
#!/usr/bin/env bash
set -e

# Only run if commands/ or agents/ changed
if git diff --cached --name-only | grep -qE '^(commands|agents)/'; then
  echo "EZPowers eval gate: commands/agents changed, running validate.py"
  python scripts/validate.py --staged
fi
```

### Step 3: Activate hook

```bash
git config core.hooksPath .githooks
chmod +x .githooks/pre-commit
```

### Step 4: Test the gate

Make a deliberately-bad change (e.g., add 5 lines to commands/brainstorm.md):
```bash
echo "test1" >> commands/brainstorm.md
echo "test2" >> commands/brainstorm.md
echo "test3" >> commands/brainstorm.md
echo "test4" >> commands/brainstorm.md
echo "test5" >> commands/brainstorm.md
git add commands/brainstorm.md
git commit -m "test gate"   # MUST FAIL with "diff line count > 3"
git checkout -- commands/brainstorm.md
```

Test golden regression detection: temporarily modify a banned expression in spec-reviewer.md to break detection.
```bash
# Make change that breaks golden case 1
git add agents/spec-reviewer.md
git commit -m "test golden gate"   # MUST FAIL with "Golden regression"
git checkout -- agents/spec-reviewer.md
```

### Step 5: Document the gate

Add a section to CLAUDE.md:
```markdown
## Eval Gate

Commits touching `commands/` or `agents/` automatically run `scripts/validate.py`.
The commit is blocked if:
- Diff exceeds 3 lines per Better-Harness "한 번에 한 줄" rule
- Any golden eval case fails
- Optimization average regresses
- Holdout average drops >10%

Bypass (emergency only): `git commit --no-verify`
```

### Step 6: Bump version

plugin.json: 0.7.2 → 0.8.0 (significant policy change = minor bump).

Save baseline 0.8.0.

## Verdict

PASS if:
1. validate.py exits 0 on clean state
2. pre-commit hook activated
3. Bad-change test 1 (5 lines) blocked
4. Bad-change test 2 (golden break) blocked
5. CLAUDE.md updated
6. plugin.json 0.8.0
7. Baseline 0.8.0 saved
```

**Phase 5 commit**:
```bash
git add scripts/validate.py .githooks/ CLAUDE.md .claude-plugin/plugin.json evals/results/baselines/0.8.0.json
git commit -m "feat: eval gate via pre-commit hook (Phase 5)

- scripts/validate.py enforces 6-check gate
- .githooks/pre-commit auto-runs on commands/ or agents/ changes
- 3-line diff cap, golden invariant, holdout protection
- Bump 0.7.2 → 0.8.0"
```

---

# Phase 6+ — 지속적 진화 (반복)

이후로는 다음 사이클을 반복:

```
1. /eval 으로 약점 식별
2. eval-diagnostician 호출 → 한 줄 변경 제안
3. 적용 → validate.py 자동 게이트
4. PASS → changelog 기록 + 버전 bump
5. FAIL → rollback, 다른 케이스 시도
6. 매 분기마다: scripts/spring_clean.py로 eval 청소 (blueprint Part C.2)
7. 매 분기마다: production trace에서 새 banned expression 발견 (blueprint Part B.6)
```

각 iteration용 짧은 프롬프트:

```
EZPowers hill-climb iteration #<N>.

@docs/Better-Harness-EZPowers-Blueprint.md
@harness_versions/changelog.jsonl

1. Run /eval optimization
2. Identify lowest-scoring command
3. Dispatch eval-diagnostician with failing traces
4. Apply proposed ≤3 line change (validate.py will gate)
5. If accepted: append changelog entry, bump patch version
6. If rejected: rollback, try alternative change up to 3 attempts
7. Output ## Verdict: PASS|FAIL

Hard constraints:
- No changes to evals/
- No diff >3 lines
- Golden must remain 4/4
- Holdout drift ≤10%
```

---

# 트러블슈팅

| 증상 | 원인 | 해결 |
|---|---|---|
| Phase 0 verification 실패 | banned expression 14개를 제대로 안 옮김 | brainstorm.md L192-208 직접 인용 후 재시도 |
| Phase 1 schema validation 실패 | YAML 들여쓰기 또는 stratum 키 누락 | `evals/schema.json`을 reviewer에게 직접 보여주고 수정 |
| Phase 2 trace 파일 안 생김 | hooks.json 경로 오류 또는 실행 권한 | `chmod +x bin/trace.sh`, `claude --debug` 모드로 재시도 |
| Phase 4 diagnostician이 4+ 라인 제안 | maxTurns 부족 또는 hard constraint 미반영 | 프롬프트에 "≤3 lines, no exceptions" 강조 |
| Phase 5 pre-commit hook 우회됨 | git config 미적용 | `git config core.hooksPath` 확인 |

---

# 한 가지 핵심 원칙

> **모든 Phase에서 의심스러우면 ROLLBACK한다.**

Better-Harness 블루프린트의 정신은 *"loss of trust in the eval signal"*보다 *"slow and verified progress"*가 백 배 낫다는 것. EZPowers 0.6.0은 충분히 좋은 출발점이고, 90일 동안 0.6.0을 *측정 가능한* 0.6.0+δ로 만드는 것이 목표지 0.6.0을 0.9.0으로 점프시키는 것이 목표가 아니다.
