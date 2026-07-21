# EZPowers Evaluation Index

## Counts
- Optimization: 46 cases (target 70%)
- Holdout: 0 tracked cases (target 20%, gitignored/local)
- Golden: 8 cases (target 10%)
- Honeypot: 2 cases
- Skill: 17 cases (separate runner: `scripts/run_skill_evals.py`)

## Runner Modes
- Static: implemented default. Deterministic graders run against current files
  and fixture data.
- Live: reserved for future disposable-repo slash-command execution. The runner
  fails loudly in this mode until that path is implemented.

## Coverage by command
| Command | Opt | Hold | Gold | Honeypot | Total |
|---|---|---|---|---|---|
| spec | 8 | 0 | 2 | 2 | 12 |
| prepare_execute | 8 | 0 | 3 | 0 | 11 |
| choice_execute | 18 | 0 | 3 | 0 | 21 |
| setup | 4 | 0 | 0 | 0 | 4 |
| review | 3 | 0 | 0 | 0 | 3 |
| sync-docs | 3 | 0 | 0 | 0 | 3 |

Note: Contract cases (12 optimization) are distributed across spec/prepare_execute/choice_execute by their `stratum.command` field.

Skill cases are intentionally separate from command cases. They guard skill hot-path size, protected skill paths, reference links, and behavior invariants.

## Optimization case directories
| Directory | Cases | Description |
|---|---|---|
| brainstorm/ | 5 | legacy directory name; spec greenfield, brownfield, refactor, vague-spec-ko, multi-R |
| plan/ | 4 | legacy directory name; prepare_execute simple-3R, large-10R, missing-verify, refactor-impact-scope |
| choiceexecutor/ | 5 | legacy directory name; choice_execute inline-trivial, harness-needed, security-keyword, oscillation, resume |
| setup/ | 3 | greenfield-empty, brownfield-existing, monorepo-root |
| executeharness/ | 8 | legacy directory name; strict adapter cases run under choice_execute |
| review/ | 2 | spec-match, spec-drift |
| sync-docs/ | 3 | new-reference, outdated-reference, auto-from-choice_execute |
| contract/ | 14 | stage interface contracts plus v2 command-chain setup determinism |

## Last baseline
- Version: 2.0.7
- Date: 2026-05-29
- File: evals/results/baselines/3.0.0.json
- Git SHA: 1fd7846
- Eval mode: static
- Automated pass rate: 29/40 (72%)
- Manual-only cases: 16/56 require live execution or LLM rubric
- Golden: 8/8 automated
- Optimization: 21/31 automated, 15 manual
- Holdout: 0 tracked cases
- Honeypot: 0/1 automated, 1 manual

## Latest local static run
- Date: 2026-07-21
- File: evals/results/baselines/3.0.0.json
- Automated pass rate: 29/40 (72%)
- Golden: 8/8 automated
- Optimization: 21/31 automated, 15 manual
- Setup: 4/4 automated
- Remaining non-live failures are mostly absent generated spec/prepare-execute artifacts
  plus the external runtime probe dependency.
