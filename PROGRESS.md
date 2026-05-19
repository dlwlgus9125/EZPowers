# EZPowers Progress

## Current State

- Stage: root harness bootstrap and measurement hardening.
- Active item: `F1` in `feature_list.json`.
- Last verified baseline: `evals/results/baselines/1.5.2.json`.
- Strict external harness path: disabled until `.harness/config.json` gets a
  real `harness.root` containing `scripts/execute.py`.

## Latest Evidence

- `python -m unittest discover -s tests`: 10 tests passed on 2026-05-19.
- `scripts/check-harness-docs.ps1`: passed on 2026-05-19.
- `scripts/run_baseline.py --mode static --splits golden optimization honeypot`:
  21/32 automated cases passed on 2026-05-19; golden was 7/7 and setup was
  3/3.
- `scripts/harness-doctor.ps1 -Status`: expected strict-path failure until an
  external EasyPowersHarness executor is configured.

## Open Problems

- Live slash-command eval is not implemented; current runner default is static
  grader mode.
- Holdout has no tracked cases by design, but no private holdout store is wired.
- `plugins/ezpowers/` is an untracked generated mirror and needs a packaging
  policy before committing.
- Root cleanup still has tracked empty files named `1)`, `2)`, `3)`, `4)`,
  `5)`, and `10)`.

## Next Actions

1. Finish P0/P1 implementation from `feature_list.json`.
2. Re-run unit, harness-doc, and eval checks.
3. Decide whether to configure a real external `harness.root` or keep strict
   `/executeharness` disabled for this repository.
