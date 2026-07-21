# EZPowers Harness Pipeline Efficiency Audit

Date: 2026-05-19
Repository: `C:\Working\EZPowers`
Scope: sequence efficiency, per-stage efficiency, verification maturity
Evaluation mode: balanced, evidence-only

## Executive Judgment

EZPowers has a structurally sound harness pipeline for AI-assisted software
delivery. The sequence follows a defensible pattern: decompose work into
explicit stages, gate intermediate artifacts, route execution by task size and
recovery needs, then require machine evidence before completion.

The current pipeline is not yet objectively proven efficient end to end. The
strongest measured components are the lightpath task gate, hashline anchor
verification, final wiring gate, and fail-closed runtime-evidence checks. The
weakest measured components are live command evaluation, setup/brainstorm/plan
eval automation, and the gap between documented audit dimensions and executable
measurement.

Overall verdict: **WARN, not FAIL**.

- **Keep the current stage order** for non-trivial work.
- **Add a fast path** for small docs/library/single-task work to reduce repeated
  audits and duplicate Verify execution.
- **Do not claim eval-driven optimization maturity yet**. Current evals are
  partially automated and many command cases are manual or static-fixture
  dependent.

## Evidence Snapshot

### Local State

- Git SHA at audit start: `1bf1a30`.
- Worktree was already dirty before this report. Existing modified/untracked
  files were not reverted.
- `docs/specs/` and `docs/plans/` do not exist in the repo root at audit time,
  which directly affects static graders that check for generated artifacts.

### Test Results

- `python -m unittest discover -s tests`: **10 tests passed**.
- `python -m unittest`: **0 tests discovered**, so the explicit discovery
  command is the reliable local unit-test command.

### Eval Results

The sandboxed environment could not run Git Bash: `run_baseline.find_bash()`
returned `None`, and Bash-based graders failed as Windows shell errors. After
running the same eval summary outside the sandbox with Git Bash available:

- Total command/honeypot/golden cases: **49**
- Automated cases: **32**
- Manual-only cases: **17**
- Automated pass rate: **18/32 = 56.25%**
- Golden: **7/7 automated pass**
- Optimization: **11/24 automated pass**, **16 manual**
- Honeypot: **0/1 automated pass**, **1 manual**

Important limitation: `scripts/run_baseline.py` explicitly says live execution
that spawns the agent is not implemented. Therefore these numbers measure the
current grader/static harness state, not full live `/brainstorm`, `/plan`, or
`/choiceexecutor` behavior.

### Disposable Fixture Execution

Fixture root: `C:\tmp\ezpowers-harness-audit`

Observed results:

- `scripts/lightpath-gate.ps1 -Scope prepare`: **pass**
- `scripts/lightpath-gate.ps1 -Scope task -TaskNumber 1`: **pass**
- `scripts/lightpath-gate.ps1 -Scope final`: **pass**
- `scripts/harness-doctor.ps1 -Status`: **fail**, because `harness.root` is
  empty. This is correct for strict `/executeharness`; it confirms that external
  harness execution is fail-closed when the external executor is unavailable.
- `scripts/harness-gate.ps1` with `echo ok`: **spec_gap**, correctly rejected
  as a trivial gate command.
- `scripts/harness-gate.ps1` with command pass but no runtime artifact:
  **test_gap**, correctly rejected for missing `runtime-probe.json` or
  `smoke-output.json`.

The task gate artifact also shows `verify-step.py` ran the same fixture command
three times. That is evidence of redundant Verify extraction after plan
conversion, not a correctness failure.

## Pipeline Map

Observed intended sequence:

```text
/setup
  -> /brainstorm
  -> /pipeline-audit post-brainstorm
  -> /plan
  -> /pipeline-audit post-plan
  -> /choiceexecutor
     -> inline | subagent-driven | /executeharness
  -> task Verify gates
  -> runtime smoke / wiring gate
  -> quality budget / code review / docs sync / eval check
```

This is aligned with external agent-system guidance:

- Anthropic recommends simple composable workflows first, then added complexity
  only when the latency/cost tradeoff is justified. It also describes prompt
  chaining with intermediate gates, routing, parallelization, and evaluator
  loops as production patterns.
- OpenAI eval guidance frames evals as describing the task, running test inputs,
  analyzing results, and iterating, similar to behavior-driven development.
- OpenAI trace grading guidance supports structured grading of agent traces to
  identify regressions and validate improvements.
- SWE-agent research supports the idea that the agent-computer interface itself
  affects coding-agent performance, so EZPowers' scripts, gates, and artifacts
  are not incidental; they are part of the agent interface.

## Sequence Efficiency

| Stage order | Evidence | Efficiency judgment |
| --- | --- | --- |
| `/setup` before all other stages | Commands require `.harness/config.json`; doctor fails closed when key config is missing. | **PASS for safety**, but current automated setup evals all fail because no live setup execution creates fixture outputs. |
| `/brainstorm` before `/plan` | Spec contract requires architecture, ASR, quality budgets, app delivery baseline, wiring map for executable artifacts. | **PASS for non-trivial work**. Too heavy for trivial docs/library tasks unless a fast path is added. |
| Post-brainstorm `/pipeline-audit` before `/plan` | Audit D2/D6/D7 can catch weak Verify, vague behavior, missing architecture before tasking. | **PASS**, because defects are cheaper to fix before task decomposition. |
| `/plan` before `/choiceexecutor` | Plan contract requires Coverage Matrix, task shape, TDD slice, wiring probes, task routing. | **PASS**, aligns with prompt chaining and agent interface best practices. |
| Post-plan `/pipeline-audit` before execution | D1-D8 check traceability, file ordering, integration readiness, sensor completeness. | **PASS for complex work**, **WARN for small work** due repeated audit overhead. |
| `/choiceexecutor` routing | Existing rule: 1-3 independent tasks inline, 4+ subagent, strict harness only when `harness.root` and recovery/log needs exist. | **PASS**, because the route matches cost/recovery tradeoffs. |
| Strict `/executeharness` | Doctor requires `harness.root` and external `execute.py`. | **PASS as an optional strict path**, not usable without configured external harness. |
| Final gates after task completion | Fixture proved final wiring pass for exempt library, `spec_gap` for trivial command, `test_gap` for missing runtime evidence. | **PASS**, strong fail-closed behavior. |

## Per-Stage Efficiency

### `/setup`

Efficiency verdict: **WARN**

The config-first design is correct. However, current setup evals are not
evidence of setup failure because the runner does not perform live command
execution. It only checks whether `.harness/config.json`, `AGENTS.md`, and
`phases/index.json` exist in the current repo state.

Required improvement: split setup evals into static contract checks and live
fixture execution checks.

### `/brainstorm`

Efficiency verdict: **WARN**

The stage is strong for quality because it forces architecture, operational
concerns, acceptance criteria, Verify commands, and wiring maps before tasking.
This reduces downstream ambiguity. The cost is high for trivial tasks.

Current automated brainstorm optimization cases mostly fail because no
`docs/specs/*.md` artifact exists in the current repo state. That is not valid
evidence that `/brainstorm` itself fails live.

Required improvement: implement live eval execution or fixture generation for
brainstorm cases.

### `/pipeline-audit`

Efficiency verdict: **PASS with implementation gap**

The audit dimensions are well placed:

- D1-D3 protect spec-to-plan traceability and AC granularity.
- D4 catches file sequencing conflicts before execution.
- D5/D8 check integration and verification sensor coverage.
- D6/D7 catch vague requirements and architecture gaps before implementation.

Gap: the command says D9 App Delivery Readiness is mandatory when triggered,
but the report template and verdict aggregation list only D1-D8. D9 should be
included explicitly in the output contract and aggregation rules.

### `/plan`

Efficiency verdict: **PASS with small-work caveat**

Plan structure is comprehensive and turns requirements into vertical slices,
which is appropriate for AI implementers. The Coverage Matrix, TDD Slice
Contract, and Wiring Probe sections are effective agent-interface design.

Measured issue: `harness-convert.ps1` plus `verify-step.py` extracted and ran
the same Verify command three times in the disposable fixture. That is wasted
work and should be deduplicated without weakening the oracle.

### `/choiceexecutor`

Efficiency verdict: **PASS**

The route selection is pragmatic:

- inline for 1-3 independent tasks
- subagent-driven for 4+ tasks
- strict harness only when external logs/recovery or `harness.root` exists

This matches the external recommendation to avoid unnecessary agentic
complexity and route work by complexity/cost.

The Verify Fidelity Check is an important efficiency feature because it blocks
wrong prompts before dispatch. Preventing a bad implementer run is cheaper than
debugging a weakened oracle after code changes.

### Lightpath Gate

Efficiency verdict: **PASS**

The disposable fixture demonstrated:

- plan-to-phase conversion works
- hashline anchor verification works
- structural/content/command dimensions work
- final exempt wiring gate works

This path is currently the best measured execution path for small or
library-only tasks.

### Strict `/executeharness`

Efficiency verdict: **INCOMPLETE EVIDENCE**

The strict path correctly fails when `harness.root` is empty. That proves
preflight is fail-closed, but not that strict harness execution is efficient.
The eval case `optimization.runtime_probe_live.006` also fails because
`..\EasyPowersHarness\scripts\probe_runtime.py` is missing in this environment.

To judge strict harness efficiency, configure `harness.root` and run a real
external harness phase.

### Final Wiring / Runtime Evidence

Efficiency verdict: **PASS**

Measured fail-closed behavior is strong:

- trivial command `echo ok` is rejected as `spec_gap`
- passing command with no runtime evidence is rejected as `test_gap`
- exempt library gate passes only when `required=false`

This is one of the strongest current parts of the pipeline.

### Eval System

Efficiency verdict: **WARN**

The eval corpus is useful as a regression scaffold, and golden invariants pass.
However, the runner does not yet execute the actual slash-command workflows.
Manual-only cases and static artifact checks limit the conclusions that can be
drawn from pass rates.

Current evals are good enough to protect some contracts. They are not yet good
enough to optimize the full harness objectively.

## High-Confidence Findings

1. **Current sequence is safer than a shorter direct-implementation path.**
   The gates catch distinct classes of errors before implementation and match
   established prompt-chain/routing/evaluator patterns.

2. **The pipeline is heavier than necessary for trivial work.**
   The documented workflow says small work still follows full design in
   `/brainstorm`. For docs/library/single-task changes, use a light path with
   explicit exemptions rather than full D1-D9 ceremony.

3. **Lightpath execution is currently better evidenced than strict harness.**
   Lightpath passed in a disposable fixture. Strict harness cannot be judged
   without `harness.root`.

4. **Eval pass rate should not be used as product quality score yet.**
   `run_baseline.py` says live execution is not implemented. Many failures are
   missing generated artifacts, not observed live command failures.

5. **D9 App Delivery is under-integrated in pipeline-audit output.**
   The source contract says include D9, but the command report template lists
   D1-D8.

6. **Verify extraction has measurable duplication.**
   The fixture task gate ran one command three times because the command
   appeared in multiple converted sections.

## Recommendations

### P0: Make measurement valid

- Add live execution support to `scripts/run_baseline.py`, or explicitly split
  static contract evals from live command evals.
- Store eval run environment facts: Bash path, shell type, Python version,
  sandbox/external execution, and missing external harness dependencies.
- Update `python -m unittest` guidance to use
  `python -m unittest discover -s tests`.

### P1: Reduce wasted work without weakening gates

- Deduplicate Verify commands after plan-to-step conversion while preserving
  exact command text and oracle strength.
- Add a fast-path policy for docs/library/single-task work:
  `/brainstorm-lite` is not required; instead use existing `/choiceexecutor`
  inline path plus lightpath gate when config says `artifact_kind=docs|library`.
- Keep post-plan audit mandatory for executable, multi-layer, or connected-task
  plans.

### P1: Close contract gaps

- Add D9 App Delivery Readiness to `/pipeline-audit` report template, verdict
  aggregation, and routing table.
- Add a deterministic test that fails if D9 is referenced in the source contract
  but missing from pipeline-audit output.
- Add an eval for Verify deduplication so the same command is not run multiple
  times from completion criteria plus verification method text.

### P2: Strict harness evidence

- Configure a real `harness.root` with `scripts/execute.py`.
- Re-run strict `/executeharness` fixture with:
  - one passing step
  - one failed Verify step
  - one reset-step recovery
  - one runtime smoke failure
- Only after that, judge strict harness time/recovery efficiency.

## Final Classification

| Area | Verdict | Reason |
| --- | --- | --- |
| Pipeline order | PASS | Stage order catches ambiguity before implementation and evidence gaps before completion. |
| Quality safeguards | PASS | Verify fidelity, runtime smoke, wiring gate, reviewer gates, and fail-closed statuses are well placed. |
| Speed/cost efficiency | WARN | Full flow is heavy for trivial work; duplicate Verify execution observed. |
| Eval maturity | WARN | Good golden scaffold, but live slash-command execution is not implemented. |
| Strict harness readiness | INSUFFICIENT_EVIDENCE | External harness dependency absent in this environment. |
| Lightpath readiness | PASS | Disposable fixture passed prepare, task, and final gates. |

## Sources

- Anthropic, [Building effective agents](https://www.anthropic.com/engineering/building-effective-agents)
- OpenAI, [Working with evals](https://platform.openai.com/docs/guides/evals?api-mode=responses)
- OpenAI, [Agent evals](https://platform.openai.com/docs/guides/agent-evals)
- OpenAI, [Trace grading](https://platform.openai.com/docs/guides/trace-grading)
- OpenAI, [Graders](https://platform.openai.com/docs/guides/graders/)
- OpenAI, [Introducing SWE-bench Verified](https://openai.com/index/introducing-swe-bench-verified/)
- OpenAI, [Why SWE-bench Verified no longer measures frontier coding capabilities](https://openai.com/index/why-we-no-longer-evaluate-swe-bench-verified/)
- Yang et al., [SWE-agent: Agent-Computer Interfaces Enable Automated Software Engineering](https://arxiv.org/abs/2405.15793)
