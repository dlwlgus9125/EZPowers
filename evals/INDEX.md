# EZPowers Evaluation Index

## Counts
- Optimization: 40 cases (target 70%)
- Holdout: 0 tracked cases (target 20%, gitignored/local)
- Golden: 7 cases (target 10%)
- Honeypot: 2 cases
- Skill: 9 cases (separate runner: `scripts/run_skill_evals.py`)

## Coverage by command
| Command | Opt | Hold | Gold | Honeypot | Total |
|---|---|---|---|---|---|
| brainstorm | 8 | 0 | 2 | 2 | 12 |
| plan | 8 | 0 | 2 | 0 | 10 |
| choiceexecutor | 10 | 0 | 3 | 0 | 13 |
| setup | 3 | 0 | 0 | 0 | 3 |
| executeharness | 6 | 0 | 0 | 0 | 6 |
| review | 2 | 0 | 0 | 0 | 2 |
| sync-docs | 3 | 0 | 0 | 0 | 3 |

Note: Contract cases (12 optimization) are distributed across brainstorm/plan/choiceexecutor by their `stratum.command` field.

Skill cases are intentionally separate from command cases. They guard skill hot-path size, protected skill paths, reference links, and behavior invariants.

## Optimization case directories
| Directory | Cases | Description |
|---|---|---|
| brainstorm/ | 5 | greenfield, brownfield, refactor, vague-spec-ko, multi-R |
| plan/ | 4 | simple-3R, large-10R, missing-verify, refactor-impact-scope |
| choiceexecutor/ | 5 | inline-trivial, harness-needed, security-keyword, oscillation, resume |
| setup/ | 3 | greenfield-empty, brownfield-existing, monorepo-root |
| executeharness/ | 6 | small-plan-conversion, multi-phase-recovery, full-feature-wiring-gate, harness-smoke-gate, wiring-code-gap, runtime-probe-live |
| review/ | 2 | spec-match, spec-drift |
| sync-docs/ | 3 | new-reference, outdated-reference, auto-from-choiceexecutor |
| contract/ | 12 | stage interface contracts |

## Last baseline
- Version: 1.5.2
- Date: 2026-05-15
- File: evals/results/baselines/1.5.2.json
- Git SHA: edfe932
- Automated pass rate: 14/32 (44%)
- Manual-only cases: 17/49 require live execution or LLM rubric
- Golden: 7/7 automated
- Optimization: 7/24 automated, 16 manual
- Holdout: 0 tracked cases
- Honeypot: 0/1 automated, 1 manual
