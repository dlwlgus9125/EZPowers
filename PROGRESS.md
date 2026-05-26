# EZPowers Progress

## Current State

- Stage: reviewer placement gate rollout.
- Active item: `F6` in `feature_list.json` is complete.
- Last verified baseline: `evals/results/baselines/2.0.0.json`.
- Strict external harness path: disabled until `.harness/config.json` gets a
  real `harness.root` containing `scripts/execute.py`.

## Latest Evidence

- `python -m unittest discover -s tests`: 18 tests passed on 2026-05-26.
- `scripts/check-harness-docs.ps1`: passed on 2026-05-26.
- `python scripts/run_skill_evals.py`: 9/9 skill evals passed on 2026-05-26.
- `scripts/smoke-plugin.ps1`: PASS with the known implementer-prompt
  frontmatter warning on 2026-05-26.
- `scripts/validate.py --changed-files ...reviewer-placement...`: eval sync
  passed with 52 command cases on 2026-05-26.
- `scripts/run_baseline.py --version local --splits golden optimization honeypot`:
  17/35 automated cases passed on 2026-05-26; golden was 8/8 and the new
  `optimization.reviewer_placement.014` case passed.
- `scripts/run_baseline.py --mode static --splits golden optimization honeypot`:
  23/34 automated cases passed on 2026-05-20; golden was 8/8 and setup was
  4/4.
- `scripts/validate.py` eval-sync check: 51 command cases synced with
  `evals/results/baselines/2.0.0.json` on 2026-05-20.
- Skill eval gate: 9/9 skill evals passed on 2026-05-20.
- `scripts/harness-doctor.ps1 -Status`: expected strict-path failure until an
  external EasyPowersHarness executor is configured.

## Open Problems

- Live slash-command eval is not implemented; current runner default is static
  grader mode.
- Holdout has no tracked cases by design, but no private holdout store is wired.
- `plugins/ezpowers/` is an untracked generated mirror and remains generated,
  not source of truth.

## Next Actions

1. Decide whether to configure a real external `harness.root` or keep strict
   `/choice_execute Path 2` disabled for this repository.
2. If reviewer placement behavior is changed again, update
   `docs/reference/reviewer-placement-contract.md` first and let tests catch
   command or skill matrix drift.
