# EZPowers Evaluation Index

## Counts
- Optimization: 30 cases (target 70%)
- Holdout: 0 cases (target 20%, pending Phase 1.5)
- Golden: 4 cases (target 10%)
- Honeypot: 0 cases

## Coverage by command
| Command | Opt | Hold | Gold | Total |
|---|---|---|---|---|
| brainstorm | 7 | 0 | 1 | 8 |
| plan | 6 | 0 | 1 | 7 |
| choiceexecutor | 10 | 0 | 2 | 12 |
| setup | 3 | 0 | 0 | 3 |
| executeharness | 2 | 0 | 0 | 2 |
| review | 2 | 0 | 0 | 2 |
| sync-docs | 2 | 0 | 0 | 2 |

Note: Contract cases (7) are distributed across brainstorm/plan/choiceexecutor by their `stratum.command` field.

## Optimization case directories
| Directory | Cases | Description |
|---|---|---|
| brainstorm/ | 5 | greenfield, brownfield, refactor, vague-spec-ko, multi-R |
| plan/ | 4 | simple-3R, large-10R, missing-verify, refactor-impact-scope |
| choiceexecutor/ | 5 | inline-trivial, harness-needed, security-keyword, oscillation, resume |
| setup/ | 3 | greenfield-empty, brownfield-existing, monorepo-root |
| executeharness/ | 2 | small-plan-conversion, multi-phase-recovery |
| review/ | 2 | spec-match, spec-drift |
| sync-docs/ | 2 | new-reference, outdated-reference |
| contract/ | 7 | stage interface contracts |

## Last baseline
- Version: 0.6.0
- Date: 2026-04-25
- File: evals/results/baselines/0.6.0.json
- Git SHA: fe424cf
- Automated pass rate: 0/19 (0%) — expected: graders check for live execution outputs
- Manual-only cases: 15/30 — require live execution or LLM rubric
- Golden: 0/4 automated (graders require $REVIEW_OUTPUT from live run)
