# EZPowers Evaluation Index

## Counts
- Optimization: 37 cases (target 70%)
- Holdout: 8 cases (target 20%, gitignored)
- Golden: 7 cases (target 10%)
- Honeypot: 2 cases
- Skill: 9 cases (separate runner: `scripts/run_skill_evals.py`)

## Coverage by command
| Command | Opt | Hold | Gold | Total |
|---|---|---|---|---|
| brainstorm | 8 | 3 | 2 | 13 |
| plan | 7 | 1 | 2 | 10 |
| choiceexecutor | 9 | 3 | 3 | 15 |
| setup | 3 | 1 | 0 | 4 |
| executeharness | 5 | 0 | 0 | 5 |
| review | 2 | 0 | 0 | 2 |
| sync-docs | 3 | 0 | 0 | 3 |

Note: Contract cases (10 optimization + 2 holdout) are distributed across brainstorm/plan/choiceexecutor by their `stratum.command` field.

Skill cases are intentionally separate from command cases. They guard skill hot-path size, protected skill paths, reference links, and behavior invariants.

## Optimization case directories
| Directory | Cases | Description |
|---|---|---|
| brainstorm/ | 5 | greenfield, brownfield, refactor, vague-spec-ko, multi-R |
| plan/ | 4 | simple-3R, large-10R, missing-verify, refactor-impact-scope |
| choiceexecutor/ | 5 | inline-trivial, harness-needed, security-keyword, oscillation, resume |
| setup/ | 3 | greenfield-empty, brownfield-existing, monorepo-root |
| executeharness/ | 5 | small-plan-conversion, multi-phase-recovery, full-feature-wiring-gate, harness-smoke-gate, wiring-code-gap |
| review/ | 2 | spec-match, spec-drift |
| sync-docs/ | 3 | new-reference, outdated-reference, auto-from-choiceexecutor |
| contract/ | 10 | stage interface contracts |

## Last baseline
- Version: 0.6.0
- Date: 2026-04-25
- File: evals/results/baselines/0.6.0.json
- Git SHA: fe424cf
- Automated pass rate: 0/25 (0%) — expected: graders check for live execution outputs
- Manual-only cases: 23/48 — require live execution or LLM rubric
- Golden: 0/4 automated (graders require $REVIEW_OUTPUT from live run)
- Holdout: 0/5 automated, 3 manual — baseline recorded
- Honeypot: 0/1 automated, 1 manual — baseline recorded
