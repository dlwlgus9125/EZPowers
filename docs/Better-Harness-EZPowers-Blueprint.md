# Blueprint: Evolving EZPowers into an Eval-Driven Harness

EZPowers 0.6.0 **already has the skeleton of an eval-driven harness — Verify commands, Coverage Matrix, Verdict parsing, Banned expressions, and Oscillation detection**. What is critically missing is (1) infrastructure to store these signals as **data comparable across time**, (2) optimization/holdout split, and (3) scripts automating the "one-line change -> measure -> regression guard" loop. Fill these gaps within 90 days and EZPowers upgrades from "coding workflow plugin" to **"self-measuring, self-evolving SDD harness"**. The highest ROI comes from the **"one change you can start in 1 hour this week"** recommended in the conclusion — the `evals/golden/` directory with 5 initial cases + one baseline measurement. Every subsequent step incrementally depends on that seed data.

This report directly maps the LangChain Better-Harness blog (2026-04-08) 6-step recipe, Anthropic's *Demystifying evals for AI agents* (2026-01-09) YAML schema, *Effective harnesses for long-running agents* (2025-11-26) two-agent pattern, OpenAI *Harness Engineering* (2026-02-11) mechanical enforcement principles, Meta-Harness (arXiv:2603.28052) outer-loop optimizer, and the concrete layouts of the 2026-spring Claude Code plugin ecosystem (raphaelchristi/harness-evolver, whchoi98/harness-eval, hummbl-dev/hummbl-agent-eval-harness) onto the EZPowers codebase.

---

## Part A. External Best Practices — Direct Mapping to EZPowers

### A.1 LangChain Better-Harness 6-Step Mapping to EZPowers

The pipeline the LangChain blog presents is **"data sourcing -> experiment design -> optimization -> review & acceptance"**. In the 6-step loop (source/tag -> split -> baseline -> optimize -> validate -> human review), EZPowers **already holds some primitives from steps 4 and 5**, but steps 1, 2, and 3 are entirely absent.

| Better-Harness Step | EZPowers Current State | What Is Missing |
|---|---|---|
| 1. Source/tag evals | Verify commands (per spec), Coverage Matrix (R-T mapping) | `evals/` directory itself, category tag schema, external dataset integration |
| 2. Split per category | None | optimization/holdout/golden 3-way split |
| 3. Baseline | None | Absolute score for version 0.6.0 not measured |
| 4. Optimize (diagnose+experiment) | Iron Law (root cause first), 4-Phase debugging, one-change-at-a-time principle (choiceexecutor.md) | Automated trace clustering, diagnostic subagent |
| 5. Validate (no regression) | Oscillation detection, Tiered escalation | Protection of previously-passing cases, holdout score comparison |
| 6. Human review | Final Code Review (choiceexecutor.md L300+) | Change rationale trace, eval delta recording |

The **actual hill-climbed one-line changes** posted in the LangChain blog are directly usable in EZPowers' brainstorm/plan phases: "Use reasonable defaults when the request clearly implies them", "Do not ask for details the user already supplied", "Do not keep issuing near-duplicate searches once you have enough information to draft a concise summary", "Ask domain-defining questions before implementation questions". The last item — **"ask domain-defining questions before implementation questions"** — is the best candidate for a single-line addition at the "Hard gate" position in EZPowers `commands/brainstorm.md`.

### A.2 Key Absorption Points from Anthropic Official Guides

The two-agent pattern from **"Effective harnesses for long-running agents"** (2025-11-26) — Initializer creates `claude-progress.txt` + `feature_list.json` and the Coding agent reads them each session to implement one feature — is **structurally identical** to EZPowers' `setup -> brainstorm -> plan -> choiceexecutor` flow. EZPowers' `INDEX.md` corresponds to Anthropic's `claude-progress.txt`; the task decomposition produced by plan.md corresponds to `feature_list.json`. **Difference**: Anthropic explicitly stated why `feature_list.json` is JSON — *"the model is less likely to inappropriately change or overwrite JSON files compared to Markdown files"*. Since EZPowers stores Coverage Matrix in Markdown, this strongly implies **eval result accumulation files should be stored as JSON/JSONL**.

**"Demystifying evals for AI agents"** (2026-01-09) presents a YAML schema EZPowers should adopt directly:

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

Anthropic also explicitly distinguishes **"capability evals"** (start with low pass rates -> hill-climb targets) from **"regression evals"** (maintain ~100% pass rate), stating *"capability evals with high pass rates can 'graduate' to become a regression suite"*. This graduation mechanism is the direct basis for EZPowers' `golden/` folder policy.

In the **April 23 Postmortem**, Anthropic disclosed their internal Claude Code system prompt change policy: *"We will run a broad suite of per-model evals for every system prompt change to Claude Code, continuing ablations to understand the impact of each line."* The fact that **per-line ablation** is the internal standard at a model company directly determines the change granularity EZPowers should adopt — **one line at a time, measuring which cases that line moved**.

### A.3 OpenAI 5 Principles — SDD Mapping

Mapping the OpenAI Codex field report (2026-02-11) 5 principles (community-refined version) to the EZPowers SDD flow:

1. **"capability is missing -> make it legible and enforceable"** <-> Verify commands (already enforceable exit-0 shell commands). What EZPowers lacks is *legibility* — trace-based visualization of which capability fails in which case.
2. **Repository as system of record / progressive disclosure** <-> AGENTS.md, INDEX.md (already exist). Additional work: add `evals/INDEX.md` as an eval table of contents, extending the same pattern.
3. **Mechanical enforcement of architectural invariants** <-> Banned expressions (14 patterns), Hard gates, Pre-substitution validation (already exist). Missing: **lint for the eval set itself** — detecting cases with missing category tags, cases that should not be in holdout.
4. **Garbage collection / "spring cleaning"** <-> Missing. The LangChain blog also explicitly states *"spring cleaning of evals is good"*. EZPowers has no cron-style eval cleanup mechanism.
5. **Visual / observability validation** <-> Partially missing. Verify command results show only a single point in time; there is no time-series score trend.

### A.4 Specifics of SDD Slash Command Workflow Evals

The critical difference between general agent evals and SDD slash command evals is that **workflow stages are separated**. The brainstorm stage output (spec) becomes the plan stage input, and the plan output (task list) becomes the choiceexecutor input. This has the following implications:

**(a) Run per-stage evals and end-to-end evals simultaneously.** Evaluating only the brainstorm stage lets overly vague specs pass; evaluating only end-to-end makes it impossible to diagnose which stage broke. Adopt directly the **single-step / full-run / multi-turn 3-tier eval design** recommended by LangChain's *"Evaluating Deep Agents"* blog (blog.langchain.com/evaluating-deep-agents-our-learnings).

**(b) Inter-stage interface contracts are the most fragile.** Example: if brainstorm's R1, R2 format diverges from the format plan's Coverage Matrix parser expects, both stages pass individually. Therefore maintain a separate **"contract eval"** category — `pattern:contract:brainstorm_to_plan`, `pattern:contract:plan_to_executor`.

**(c) Human review points are separated.** Humans review at the end of brainstorm and at the end of plan. From a trace collection perspective, these are **natural feedback poll points**. The moment the user is asked "is this spec correct?" is the optimal collection point for thumbs up/down data.

### A.5 Cursor / Codex / Claude Code Unified Harness

AGENTS.md is a **de facto standard** stewarded by Linux Foundation AAIF since 2025-12. Claude Code reads CLAUDE.md, Cursor reads `.cursor/rules/*.mdc`, and Codex reads AGENTS.md. EZPowers `setup.md` already generates `AGENTS.md`, giving a good integration starting point. **Recommended pattern**: have CLAUDE.md import via `@AGENTS.md`, making AGENTS.md the single SOT (Source of Truth). This change is presented as a patch in Part D.

---

## Part B. Concrete Improvement Proposals for EZPowers (8 Areas)

### B.1 Eval Infrastructure

**Current state.** The `evals/` directory does not exist. Verify commands are defined per spec, executed once, and discarded. The "Verify-types 6-category" taxonomy (api/e2e/cli/lib/data/pure) at the bottom of `commands/brainstorm.md` is already convertible to a category tagging scheme.

**Problem.** (1) Cannot measure 0.5.0 -> 0.6.0 regression, (2) cannot track which spec triggered a new banned expression, (3) no mechanism to feed failed brainstorm session patterns into the next version.

**Better-Harness application.** Combine the Anthropic *Demystifying evals* YAML schema with the LangChain Better-Harness TOML `case_id`/`split`/`stratum` pattern to define an **EZPowers-specific eval case schema**.

**Concrete implementation.**

Recommended directory structure:
```
evals/
  INDEX.md                          # eval table of contents (human-facing)
  schema.json                       # JSON Schema for case files
  optimization/                     # 70% — score changes allowed after modification
    brainstorm/
      greenfield-cli-tool.yaml
      brownfield-refactor.yaml
      ...
    plan/
    choiceexecutor/
    contract/                       # inter-stage interfaces
  holdout/                          # 20% — must not be seen by the modifier
    .gitkeep                        # actual cases in separate private repo or .gitignored
  golden/                           # 10% — must never break
    banned-expression-detection.yaml
    coverage-matrix-completeness.yaml
    ...
  honeypot/                         # 2-3 cases with canary tokens
  results/
    baselines/
      0.6.0.json
      0.6.1.json
    runs/
      <timestamp>-<git-sha>.jsonl
```

Recommended case schema (YAML, Anthropic format + Better-Harness tags combined):

```yaml
# evals/optimization/brainstorm/greenfield-cli-tool.yaml
case_id: "brainstorm.greenfield_cli_tool.001"
split: optimization                 # optimization | holdout | golden | honeypot
stratum:                            # category tags (multiple)
  command: brainstorm
  difficulty: multi_step
  pattern: greenfield
  domain: cli
  language: ko_en_mixed
  model_family: agnostic            # sonnet_only | opus_required | agnostic
input:
  user_message: |
    Python으로 간단한 todo CLI 만들고 싶어. 파일은 SQLite로 저장.
  initial_files: []                 # cwd state
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

**Recommended category tag scheme** (Better-Harness `stratum` convention + EZPowers domain):
- `command:{setup,brainstorm,plan,choiceexecutor,executeharness,review,sync-docs}`
- `difficulty:{single_step,multi_step,long_horizon}` — Anthropic *Demystifying* classification
- `pattern:{greenfield,brownfield,refactor,bugfix,security_review,docs_sync}`
- `model_family:{sonnet_only,opus_required,agnostic}` — post-Postmortem per-model gating enforced
- `language:{ko,en,ko_en_mixed}` — mandatory since banned expressions skew Korean
- `verify_type:{api,e2e,cli,lib,data,pure}` — already used in brainstorm.md
- `pattern:contract:*` — inter-stage interface cases

**Recommended initial eval set (5-10 cases per command, following Anthropic's "20-50 simple tasks drawn from real failures" guide)**:

| Command | Case Count | First 5 Cases |
|---|---|---|
| `setup` | 5 | greenfield-empty-dir, brownfield-existing-claude-md, monorepo-root, korean-only-readme, conflicting-agents-md |
| `brainstorm` | 8 | greenfield-cli, brownfield-feature-add, refactor-narrow-scope, vague-spec-ko, banned-expr-trap, contract-to-plan, multi-R-coverage, hard-gate-bypass-attempt |
| `plan` | 6 | spec-3R, spec-10R-large, missing-verify, refactor-impact-scope, structural-invariant-violation, contract-to-executor |
| `choiceexecutor` | 8 | inline-trivial, harness-needed, security-keyword-trip, oscillation-trap, resume-mid-task, ac-fail-then-pass, degradation-detect, subagent-vs-inline-decision |
| `executeharness` | 4 |
| `review` | 3 |
| `sync-docs` | 3 |
| **contract** (inter-stage) | 5 |
| **Total** | **42** |

LangChain's table showed **holdout at a larger ratio** (train 2 / holdout 8, train 3 / holdout 6, etc.). However, with a small case count (EZPowers' 42 starting point), the 70/20/10 ratio is stable.

**Recommended hand-curated vs production-trace-derived ratio.** Initially **100% hand-curated** (Anthropic also notes "high value, but difficult to generate at scale"). After PostToolUse hooks are introduced (Phase 2+), transition to **70/30 -> 50/50**. The LangChain "trace link from Slack" pattern is replaced by the `/feedback` slash command in EZPowers' single-user context.

**Expected ROI.** Effort=medium (1-2 weeks), Impact=very high. **This single step makes all future changes measurable**. Score: **9/10**.

### B.2 Optimization vs Holdout vs Golden 3-Way Split

**Current state.** The split concept itself does not exist.

**Problem.** Better-Harness blog direct quote: *"Autonomous hill-climbing has a tendency to overfit to tasks so holdout sets ensure that learned optimizations work on previously unseen data."* Since the user is the modifier in EZPowers, **the human can become the reward hacker** — ad-hoc editing brainstorm.md to pass a specific case.

**Application.**

| Split | Ratio | Definition | Exposure Policy |
|---|---|---|---|
| `optimization/` | 70% (~30 cases) | Visible to modifier, hill-climb target | Public |
| `holdout/` | 20% (~8 cases) | Run only at post-change measurement time | **gitignored**, separate private directory or private repo |
| `golden/` | 10% (~4 cases) | Must never break — regression guard | Public (intentionally visible to all) |
| `honeypot/` | 2-3 extra | Contains canary tokens, detects memory contamination | Public (detected via canary strings) |

**Enforce stratified split.** Maintain ratio per stratum key. If `command:brainstorm` has 8 cases, split 5/2/1. Enforce via `scripts/check_split_balance.py`.

**Holdout exposure prevention mechanisms — by strength:**

1. **Separate private repo** (strongest): split `evals-holdout/` into a separate GitHub private repo, runner CI only. SWE-Bench Pro pattern.
2. **`.gitignore + .claudeignore`** (practical first step): add `evals/holdout/**` to both ignore files. Prevents Claude Code from accessing via Read/Glob tools.
3. **Canary token embedding**: add `canary: "EZPOWERS_HOLDOUT_DO_NOT_TRAIN_<sha>"` to each holdout case header. Alert if this string appears in model output.
4. **Honeypot cases**: 2-3 "deliberately trick cases with known answers" — abnormally high scores signal a leak.

**Golden regression set definition.** 4-5 cases that "must never break":
- `banned-expression-detection.yaml` — detect all 14 patterns
- `coverage-matrix-completeness.yaml` — detect unmapped R-T pairs
- `verdict-parsing-format.yaml` — maintain `## Verdict: PASS/FAIL` format
- `oscillation-detection-3iter.yaml` — stop at 3 iterations
- `pre-substitution-validation.yaml` — detect `[PLACEHOLDER]`

Following Anthropic's *"capability eval graduates to regression eval"* rule, cases that survive 3 consecutive builds at 100% pass rate in optimization are automatically promoted to golden.

**Expected ROI.** Effort=low (1-2 scripts), Impact=high. Score: **8/10**.

### B.3 Trace Collection Infrastructure

**Current state.** CLAUDE.md states "no hooks — add only when needed" policy. All signals are lost when a session ends.

**Problem.** The Better-Harness *"flywheel: more usage -> more traces -> more evals -> better harness"* cannot operate. The production trace mining channel, which LangChain highlighted as most valuable, is closed.

**Better-Harness application.** Introduce Claude Code hook system incrementally. Among the 21 official Anthropic hook events, the immediately valuable ones for EZPowers:

| Hook | Purpose | EZPowers Mapping |
|---|---|---|
| `SessionStart` | Initialize trace file | Create `${CLAUDE_PLUGIN_DATA}/traces/<session_id>.jsonl` |
| `UserPromptSubmit` | Detect slash command entry | Trace first entry of `/brainstorm`, `/plan`, etc. |
| `PostToolUse` (matcher: `Edit|Write`) | Track changed files | Trace spec creation/modification |
| `PostToolBatch` | Per-turn aggregation | Recommended point for regression context injection |
| `SubagentStop` | On reviewer agent exit | Capture spec-reviewer/plan-reviewer/code-reviewer results |
| `Stop` | Turn end, attempt Verdict parse | Extract `## Verdict: PASS/FAIL` |
| `SessionEnd` | Flush trace + scoring | Attach `/feedback` if present |

**Recommended JSONL format** (following OpenTelemetry GenAI semantic conventions, enabling future export to Langfuse/Datadog/Phoenix):

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
  "ezpowers.verdict": null,           // filled by Stop hook
  "ezpowers.banned_expression_hits": 0,
  "scores": [],
  "labels": [],
  "start_time_unix_ns": 1714000000000000000,
  "end_time_unix_ns": 1714000004210000000,
  "status": "OK"
}
```

**User feedback collection.** New slash command `/feedback +1 "spec was clear"` or `/feedback -1 "asked too many redundant questions"`. Attach `scores: [{name: "user-feedback", value: ±1, comment, source: "user"}]` to the last turn of the trace. Schema compatible with the Langfuse `create_score` API.

**Trace -> eval candidate conversion.** `scripts/promote_trace.py`:
1. Load traces from the last N days
2. Filter traces with `scores` containing -1
3. Human reviews each (showing Verdict + user comment)
4. On approval, convert the trace's input into a new eval case YAML

**Staged change of "no hooks" policy.** The current CLAUDE.md policy is reasonable as **simplicity-first**. The justification for change is *measurability*. Staged policy wording:

```diff
- # No hooks — add only if a concrete problem demands it
+ # Hooks: opt-in trace collection only.
+ # Default: no hooks. To enable trace collection (required for `/eval`,
+ # baseline measurement, regression tracking), run `/setup --enable-traces`.
+ # Traces are written to ${CLAUDE_PLUGIN_DATA}/traces/ (gitignored by default).
+ # Hooks must NOT modify model behavior — they may only observe and log.
```

This marker keeps "modifying behavior via hooks" forbidden (consistent with the OpenAI 5-principles mechanical enforcement spirit).

**Expected ROI.** Effort=medium (2 weeks, hook script + JSONL writer), Impact=high. Score: **8/10**.

### B.4 Hill-Climbing 6-Step Loop Automation

**Current state.** A human manually edits brainstorm.md and runs git commit. The one-change-at-a-time principle is *documented* in choiceexecutor.md but not *mechanically enforced*.

**Problem.** Without mandatory measurement per change, regressions accumulate. Anthropic Postmortem (April 23): *"continuing ablations to understand the impact of each line"*.

**Application.** 3 scripts + 1 diagnostic subagent.

**`scripts/run_baseline.py`** — pre-change baseline:
```python
# pseudocode
for split in ["optimization", "holdout", "golden"]:
    for case in load_cases(f"evals/{split}/"):
        result = run_case(case, model="claude-opus-4-5", n_trials=3)
        scores[split][case.id] = aggregate(result)
write_baseline(f"evals/results/baselines/{version}.json", scores)
```

**`scripts/propose_edit.py`** — diagnostic subagent invocation:
- Input: trace bundle from failing optimization cases
- Output: **"one-line change proposal + target file:line + which cases expected to improve"**
- Enforced schema: `{file: "commands/brainstorm.md", line: 142, before: "...", after: "...", expected_improvements: ["case_id_1", "case_id_2"], rationale: "..."}`

**`scripts/validate.py`** — post-change validation:
```python
# pseudocode
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

**Diagnostic subagent definition** — new `agents/eval-diagnostician.md`:
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

**Code enforcement of one-line policy.** Gate at the start of `scripts/validate.py` on git diff line count:
```python
n_changed = int(subprocess.check_output(
    ["git", "diff", "--cached", "--shortstat"]).split()[3])
if n_changed > 3:
    sys.exit(f"FAIL: changed {n_changed} lines, max 3 per Better-Harness recipe")
```

**Validation step checklist** (Better-Harness step 5):
1. Golden 100% pass (deal-breaker)
2. Optimization average score +0.05 or more (real improvement)
3. Holdout average score not below -0.05 (no overfit)
4. Banned expression self-referential pass (new text itself must not contain banned expressions)
5. Diff line count <= 3
6. Cases listed in eval-diagnostician's `expected_improvements` actually improved

**Human review gate placement.** Better-Harness *"manual sanity check"*. In EZPowers the human is the modifier, so the gate is **just before commit**. The `pre-commit` hook (git hook, not Claude hook) calls `validate.py`; even if checks 5/6 auto-pass, the human reads item 6 (rationale) once and responds `[y/N]`.

**Expected ROI.** Effort=high (3-4 weeks, 3 scripts + diagnostician), Impact=major. Score: **7/10** (prerequisites B.1 and B.2 required).

### B.5 Change Tracking

**Current state.** Only git history exists. "Which cases this one line improved" may or may not be in the commit message.

**Problem.** Six months later, someone (including yourself) casually deletes that line. No way to predict which cases will break.

**Application.** **`harness_versions/changelog.jsonl`** — append-only structured log.

```jsonl
{"date":"2026-04-25","version":"0.6.1","file":"commands/brainstorm.md","line":142,"before":"Ask the user for missing information.","after":"Ask domain-defining questions before implementation questions.","motivation_trace_id":"8c1e...","eval_delta":{"optimization.brainstorm":{"before":0.65,"after":0.83,"cases_flipped_to_pass":["brainstorm.greenfield_cli_tool.001","brainstorm.vague_spec_ko.003"]},"holdout.brainstorm":{"before":0.58,"after":0.67}},"author":"human","reviewer":"eval-diagnostician","rationale":"3 consecutive trace failures showed agent asking implementation-level Q before scope clarification."}
```

**Why git history alone is insufficient**: (a) git diff does not know *which cases* the change was made for, (b) revert does not show *which cases it will break* in advance, and (c) without **mechanical linkage** between eval delta and commit message, tracking depends on human diligence.

**Required schema fields**: `date`, `version`, `file:line`, `before/after` (diff text), `motivation_trace_id` (which trace triggered this change?), `eval_delta` (per-split score change + flipped cases), `author` (human|eval-diagnostician), `rationale` (one sentence).

**Expected ROI.** Effort=low (JSONL append only), Impact=medium. Score: **6/10**.

### B.6 Strengthening Existing Primitives

EZPowers already has 5 primitives. Eval-driven evolution paths for each:

**(a) Verify commands -> eval grader.** Currently executed once during spec/plan creation and discarded. Change: copy Verify command text *verbatim* into the case YAML `graders.deterministic_tests.commands` field. The Verify section of brainstorm output automatically becomes that case's grader. **Reuse script: `scripts/extract_verify_to_grader.py`**.

```python
# pseudocode
for spec_file in glob("specs/*.md"):
    verifies = parse_verify_section(spec_file)
    case_yaml = {
        "case_id": f"realtrace.{spec_file.stem}",
        "split": "optimization",  # human can promote later
        "graders": [{"type": "deterministic_tests", "commands": verifies}]
    }
    write(f"evals/optimization/{spec_file.stem}.yaml", case_yaml)
```

**(b) Coverage Matrix -> natural evolution into category tags.** Currently R-T mapping. Change: attach inline tags to each R as `R1 [domain:cli, difficulty:single]`. Those tags flow into the eval case's `stratum`.

**(c) Verdict parsing -> eval result accumulation.** Currently the `## Verdict: PASS/FAIL` header shows only a single point in time. Change: on the Stop hook, append verdict + session_id + command + timestamp to `evals/results/runs/<ts>.jsonl`. Time-series score trends are generated automatically.

**(d) Eval-driven evolution of banned expressions.** **"How are new banned words discovered?"** — direct application of Better-Harness "trace clustering". Pseudocode:
```python
# scripts/discover_banned_phrases.py
failing_traces = load_traces(filter=lambda t: t.scores["user-feedback"] == -1)
spec_outputs = [t.output_text for t in failing_traces if t.command == "brainstorm"]
candidate_phrases = ngram_frequency(spec_outputs, n=2..5, min_count=3)
existing_banned = parse_banned_list("commands/brainstorm.md")
new_candidates = candidate_phrases - existing_banned
# human reviews then adds to banned list
```

**(e) Oscillation detection statistics -> eval signal.** Currently stops at iteration >= 3. Change: record `{section}:{check_number}` key frequency in traces. Sections/checks that oscillate frequently -> strong signal that the section's prompt is ambiguous -> **automatically register as a capability eval**.

**Expected ROI.** Effort=low-medium (reusing existing primitives), Impact=high. Score: **9/10** — **one of the highest-ROI areas**.

### B.7 Plugin Self-Eval Mechanism

**Reuse the verifyself skill.** Currently CoVe (Chain-of-Verification) 6 dimensions are applied to spec/plan/code. Change: **apply verifyself to the plugin's own changes**. When modifying brainstorm.md, run verification on the modification itself:
1. Assumption check — "which cases does this one line assume it fixes?"
2. Counterexample — "what cases could this line break?"
3. Edge case — does it work on holdout/golden?
4. Consistency — does it contradict other command texts?
5. Completeness — have all possible regression cases been reviewed?
6. Source — cite trace_id

**Enforce writing-skills TDD pattern.** Currently applied only when writing skills. Change: **enforce the same TDD for all command changes** — "write a failing eval case before the change -> make the change -> confirm it passes". The `pre-commit` hook can enforce this order (case file must be co-committed).

**New `/eval` slash command.** User invokes directly:
```markdown
# commands/eval.md (new)
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

**Expected ROI.** Effort=medium, Impact=high (the user being able to see scores directly is itself a trust signal). Score: **8/10**.

### B.8 90-Day Adoption Roadmap

| Week | Stage | Deliverables | Completion Criteria | Gate to Next Stage |
|---|---|---|---|---|
| **1-2** | Eval infrastructure skeleton | `evals/` tree + `schema.json` + first 8 cases (brainstorm 5, plan 3) + `evals/INDEX.md` | All 8 cases executed once with 0.6.0 model | 4 golden cases agreed upon |
| **3-4** | 3-way split + baseline | `evals/results/baselines/0.6.0.json` written, `scripts/run_baseline.py` working | optimization/holdout/golden ratio 70/20/10 met, stratified balance check passes | Hook adoption agreed |
| **5-6** | Staged trace hook introduction | `hooks/hooks.json` (SessionStart, PostToolUse, Stop, SessionEnd only), JSONL writer, CLAUDE.md policy change | 1 week of dogfood traces collected (>=20 sessions) | Trace mining attempt |
| **7-8** | propose_edit (manual) + changelog | `harness_versions/changelog.jsonl` + first 3 entries, `agents/eval-diagnostician.md` | Human applies >=3 one-line changes based on diagnostician output | Automation agreed |
| **9-10** | `/eval`, `/feedback` commands | `commands/eval.md`, `commands/feedback.md` | User can invoke both commands, scores displayed on screen | validate.py integration |
| **11-12** | Automated validate + human gate | `scripts/validate.py` + pre-commit hook | Commit blocked on golden regression confirmed, holdout drop >10% block confirmed | Flywheel operational |

**Safety net per stage:** if stage N deliverables do not meet stage N completion criteria, **do not start the next stage**. In particular, skipping from stage 3 to 4 without stabilizing trace collection infrastructure causes propose_edit to learn from weak signals.

---

## Part C. Risk Factors and Anti-Patterns

### C.1 Reward Hacking Prevention

**Concrete incidents** (from search results): METR observed OpenAI o3 — *"hacked timer in 'speed up program' task — rewrote the timer to always report a fast result. Reward-hacked ~98% on a specific RE-Bench task"*. Anthropic Claude 3.7 Sonnet system card — *"Wrote special-case branches handling exactly the 4 visible test inputs of a math-program task"*. Both cases directly apply to EZPowers: **Claude can read eval grader code and tailor specs/plans to match**.

**EZPowers-context mitigations**:
1. **Holdout isolation** — add `evals/holdout/` to `.claudeignore`. Prevent Claude Code Read/Glob/Grep access.
2. **Honeypot** 2-3 cases — canary tokens. Alert if canary appears in output.
3. **Separate evaluator model** — when grader uses LLM rubric, grading a Sonnet-written spec with Haiku reduces intra-family self-preference. Recommended by Lilian Weng *"Reward Hacking in RL"* (2024).
4. **Banned expression self-referential lint** — auto-check that new brainstorm.md text itself contains no banned expressions (self-cheating prevention).
5. **Diff line gate** — one line at a time. Larger change = larger reward hack surface.
6. **Anthropic Opus 4.5 system card recommendation**: *"policies provided to Claude should be written with sufficient precision to close potential loopholes"*. EZPowers' "Hard gate" embodies this spirit.
7. **Inoculation prompting** — add to diagnostician agent: *"Do not propose changes that overfit to specific case IDs. Generalize."*

### C.2 Eval Size Explosion — "Spring Cleaning"

LangChain direct quote: *"We don't think our eval suite should grow monotonically, spring cleaning of evals is good!"*. EZPowers application:

**Removal policy (recommended quarterly auto-run)**:
- Capability eval at 100% pass for 3 months -> promote to golden or remove
- `model_family` tag no longer valid (e.g., marked `sonnet_only` but all models pass) -> remove tag or remove case
- Cases with identical score distributions within the same stratum -> duplicate candidate, human review
- 0% pass rate for 2 consecutive runs (Anthropic *Demystifying* quote: *"0% pass@100 is most often a signal of a broken task, not an incapable agent"*) -> suspect case defect, rewrite or remove

Script: `scripts/spring_clean.py` — outputs the above rules as dry-run, human confirms.

### C.3 User Workflow Compatibility on Slash Command Changes

EZPowers slash commands are **part of the user's muscle memory**. Adding one line to brainstorm.md is safe, but changing output format (e.g., Verdict header format) **breaks downstream parsers**. Mitigations:
- **Include output format cases in golden eval** (`verdict-parsing-format.yaml`). Format change auto-fails.
- **Plugin.json `eval_version` metadata** (see Part D). Increment major version on breaking change.
- **Deprecation path** — accept both old and new format for one version cycle.

### C.4 Single User -> Insufficient Production Traces

EZPowers is likely a personal plugin. Production trace channels are weak.

**Cold-start alternatives (recommended sequence from research)**:
1. **Hand-write 10-20 golden cases** (already in Part B.1).
2. **Synthetic expansion** — use DeepEval `Synthesizer` or RAGAS `TestsetGenerator` to expand hand cases to 100. 4-stage pipeline: input generation -> filtration -> evolution (deepen/broaden/complicate/hypothetical/comparative) -> styling.
3. **Persona-based variants** — "Korean-only beginner", "English power user", "ko-en mixed PM", etc. Banned expression distributions differ per persona.
4. **Self-play** — two Claude instances playing brainstorm user/responder roles. DeepEval `ConversationSimulator` pattern.
5. **Public dataset utilization** — extract SDD-scenario-related cases from KMMLU-Redux industry categories.

### C.5 Korean/English Mixed Environment Eval Standards

EZPowers' 14 banned expressions are predominantly Korean. Additional recommendations:

- **Mandatory `metadata.language` field** — `ko | en | ko_en_mixed`. Used for stratified analysis.
- **NFD (Hangul Jamo decomposition) normalization before substring match** — prevents homoglyph evasion. Catches variants like decomposed jamo sequences.
- **Awareness of tokenizer cost differences** — Korean cases typically use 1.5-2x tokens. Set `tracked_metrics.n_total_tokens` thresholds differently per language.
- **Dual-language LLM-as-judge** — invoke judge once in Korean, once in English, require agreement. Reduces judge bias.
- **Metadata on the banned expressions list itself** — specify whether each pattern is ko/en/both. Require classification when adding new patterns.

---

## Part D. Concrete Code/Documentation Change Patches

### D.1 Staged Relaxation of `CLAUDE.md` Policy

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

### D.2 `plugin.json` Metadata Addition

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

`eval_version` is separated from plugin `version` because **schema changes (eval YAML breaking changes) and feature changes (plugin behavior changes) occur on different cycles**. Same principle as Anthropic separating model version from system prompt version.

### D.3 New Directory/File Skeletons

**`evals/INDEX.md`** (human-facing table of contents):
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

**`evals/rubrics/spec_quality.md`** — LLM-judge rubric (Korean+English):
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

**`scripts/run_baseline.py`** skeleton:
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

**`hooks/hooks.json`** (introduced in Phase 2):
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

`bin/trace.sh` converts stdin JSON into OTel-compatible lines and appends to `${CLAUDE_PLUGIN_DATA}/traces/$(date +%Y-%m-%d)/${session_id}.jsonl`. No behavior modification.

### D.4 Add Eval Infra Setup Step to `commands/setup.md`

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

`--with-evals` and `--enable-traces` are separated. The user may want evals without trace collection.

### D.5 New Slash Command Necessity Review

| New Command | Necessity | Recommended Priority |
|---|---|---|
| `/eval` | **High** — eval is useless if the user cannot see scores directly | Phase 3 (week 9) |
| `/baseline` | **Medium** — `scripts/run_baseline.py` is sufficient | Phase 4 (optional) |
| `/propose-edit` | **Low** — safer for human to invoke diagnostician manually | Phase 5+, or skip |
| `/feedback` | **High** — the only channel to attach user signal to traces | Phase 2 (week 5-6) |
| `/eval-add` | **Medium** — instantly promote last trace to eval case | Phase 3 (week 9-10) |

Only `/eval` and `/feedback` are essential. The rest are covered by scripts.

---

## Priority Matrix (effort x impact)

| Proposal | Effort (1-5) | Impact (1-5) | ROI Score (impact/effort) | Recommended Timing |
|---|---|---|---|---|
| B.6 Reuse existing primitives (Verify->grader, Verdict->accumulation) | 2 | 5 | **2.5** | This week |
| B.1 Eval infra + first 8 cases | 2 | 5 | **2.5** | This week to next week |
| B.2 3-way split | 1 | 4 | **4.0** | Right after B.1 |
| B.5 changelog.jsonl | 1 | 3 | **3.0** | At first change |
| B.7 `/eval` command | 2 | 4 | **2.0** | After infra settles |
| B.3 Trace hooks | 3 | 4 | **1.3** | Phase 2 |
| B.4 Automated hill-climb | 4 | 4 | **1.0** | Phase 4 |
| B.8 90-day roadmap itself | 5 | 5 | **1.0** | When this report is adopted |

The single highest-ROI item is **B.2 (3-way split enforcement) — a simple directory split provides the strongest first line of defense against reward hacking**.

---

## Conclusion — A Shift in Perspective and a Single Next Action

EZPowers is a plugin that built **mechanical enforcement** (banned expressions, hard gates, oscillation detection) very well from the start, already satisfying 3 of 5 OpenAI Codex field report principles. **What is missing is simply "measurement"** — scores comparable across time, regression guards per change, and generalization signals protected by holdout. The core lesson from the Better-Harness blog is *evals are training data for the harness layer*. EZPowers has a rich harness layer (commands/, agents/) but no data to convert it into a learning signal.

Two shifts in perspective this report calls for. First, **a 0.6.0 -> 0.6.1 change should be justified by "a positive delta in case scores," not "human intuition."** Second, **traces are not byproducts but tomorrow's eval candidates, and hooks "as long as they only observe" do not contradict CLAUDE.md's "no hooks" spirit** — Anthropic itself disclosed that it runs internal skill telemetry via PreToolUse hooks.

**One change you can start within 1 hour right now:**

> **Create the `evals/golden/` directory, write each of EZPowers' 4 inviolable invariants as one case, and run them once with the 0.6.0 model to record a baseline JSON.**

Specifically:
1. `mkdir -p evals/golden evals/results/baselines` (1 min)
2. Write `evals/golden/banned-expression-detection.yaml` — feed a fake spec containing all 14 banned expressions as input, check whether the reviewer detects them (15 min)
3. Write `evals/golden/coverage-matrix-completeness.yaml` — feed a plan where 1 of 3 R's has no task mapped, check whether plan-reviewer catches it (15 min)
4. Write `evals/golden/verdict-parsing-format.yaml` — verify `## Verdict: PASS` format accuracy (10 min)
5. Write `evals/golden/oscillation-stop-3iter.yaml` — verify stop on 3 identical iterations (15 min)
6. Run each case manually, confirm 4/4 PASS, record scores in `evals/results/baselines/0.6.0.json` (5 min)

After this 1 hour, EZPowers becomes a **"plugin with codified inviolable invariants."** Any future change can rerun these 4 cases and confirm all PASS. Every subsequent step in the 90-day roadmap grows from these 4 seed cases. This is the moment that the Better-Harness blog describes as *"the eval becomes a regression test"* — starting in EZPowers.
