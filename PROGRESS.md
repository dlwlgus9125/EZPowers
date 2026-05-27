# EZPowers Progress

## Current State

- Stage: frontend v2 visual readiness production hardening complete.
- Active item: `F9` in `feature_list.json` is complete.
- Last verified baseline: `evals/results/baselines/2.0.0.json`.
- Strict external harness path: disabled until `.harness/config.json` gets a
  real `harness.root` containing `scripts/execute.py`.

## Frontend Design Readiness Rollout

- Scope: v1 readiness plus v2 skeleton; not full visual automation.
- Goal: add a `frontend-design` skill, a frontend design contract, reviewer
  support, D9 audit coverage, and tests/evals that stop UI work from moving to
  implementation before design system, token, component, state, responsive,
  accessibility, and visual QA decisions are recorded.
- Result: complete. Continue future v2 work from
  `docs/reference/frontend-design-contract.md`,
  `skills/frontend-design/SKILL.md`, and
  `agents/frontend-experience-reviewer.md`.

## Frontend V2 Visual Readiness Skeleton

- Scope: mock/prototype artifact handling, Storybook/component-state lane,
  Playwright or equivalent screenshot baseline lane, visual diff lane, and
  screenshot/visual review loop contracts. This is not full visual automation.
- Result: complete. `scripts/frontend-visual-readiness.py` detects advisory
  versus required visual lanes from project-local tooling evidence or explicit
  plan prerequisite tasks without installing tools or generating screenshots.
- Contract behavior: visual automation is mandatory only when local tooling
  already exists or the plan adds it; normative mock/prototype artifacts require
  token/component mapping and a freshness rule.

## Frontend V2 Visual Readiness Production Hardening

- Scope: harden the F8 skeleton for production planning without adding full
  screenshot generation or visual diff execution.
- Result: complete. The runner now scans workspace frontend roots and explicit
  `--frontend-root` targets, separates Playwright e2e availability from
  screenshot-specific gates, recognizes equivalent component isolation and
  visual diff tools, emits versioned JSON with warnings/errors/evidence, and
  avoids reference-only or negated mock/prototype false positives.
- Contract behavior: `--mode detect` is advisory and exits 0; `--mode check`
  is the pipeline gate. Screenshot/visual lanes are mandatory only from
  project-local screenshot/visual evidence or explicit prerequisite tasks.

## Latest Evidence

- `python -m unittest discover -s tests`: 37 tests passed on 2026-05-27 after
  frontend visual readiness production hardening.
- `scripts/check-harness-docs.ps1`: passed on 2026-05-27 after updating the
  frontend visual readiness runner smoke check.
- `python scripts/run_skill_evals.py`: 19/19 skill evals passed on 2026-05-27.
- `python scripts/run_baseline.py --version local --splits golden optimization honeypot`:
  17/35 automated cases passed on 2026-05-27; golden was 8/8.
- `python -m unittest discover -s tests`: 28 tests passed on 2026-05-27 after
  adding the frontend v2 visual readiness skeleton.
- `scripts/check-harness-docs.ps1`: passed on 2026-05-27 and includes the
  frontend visual readiness runner smoke check.
- `python scripts/run_skill_evals.py`: 16/16 skill evals passed on 2026-05-27.
- `python scripts/run_baseline.py --version local --splits golden optimization honeypot`:
  17/35 automated cases passed on 2026-05-27; golden was 8/8.
- `python -m unittest discover -s tests`: 18 tests passed on 2026-05-26.
- `scripts/check-harness-docs.ps1`: passed on 2026-05-26.
- `python scripts/run_skill_evals.py`: 9/9 skill evals passed on 2026-05-26.
- `scripts/smoke-plugin.ps1`: PASS with the known implementer-prompt
  frontmatter warning on 2026-05-26.
- `scripts/validate.py --changed-files ...reviewer-placement...`: eval sync
  passed with 52 command cases on 2026-05-26.
- `scripts/run_baseline.py --version local --splits golden optimization honeypot`:
  17/35 automated cases passed on 2026-05-26 after the frontend design
  readiness rollout; golden was 8/8.
- `python -m unittest discover -s tests`: 22 tests passed on 2026-05-26 after
  the frontend design readiness rollout.
- `scripts/check-harness-docs.ps1`: passed on 2026-05-26 after the frontend
  design readiness rollout.
- `python scripts/run_skill_evals.py`: 13/13 skill evals passed on 2026-05-26
  after adding `frontend-design`.
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
- Full visual automation is not implemented; v2 currently provides contracts
  and a non-installing readiness detector.
- Holdout has no tracked cases by design, but no private holdout store is wired.
- `plugins/ezpowers/` is an untracked generated mirror and remains generated,
  not source of truth.

## Next Actions

1. Decide whether to configure a real external `harness.root` or keep strict
   `/choice_execute Path 2` disabled for this repository.
2. If reviewer placement behavior is changed again, update
   `docs/reference/reviewer-placement-contract.md` first and let tests catch
   command or skill matrix drift.
3. Future frontend visual automation work can add real Storybook/Playwright
   baseline generation and visual diff execution behind the existing
   tool-conditional readiness lanes.
