# EZPowers Progress

## Current State

- v4.0.0 slim-core reorganization in progress on branch `slim-core-4.0.0`:
  the doc-eval and trace infrastructure and the 3-line diff rule are retired,
  contracts are consolidated 27 -> 21, and the structural commit gate
  `scripts/check-repo.ps1` (wired via `core.hooksPath`) replaces the retired
  harness-docs gate. Active item: `F10` in `feature_list.json`.
- Frontend v2 visual readiness (items `F7`-`F9`) is complete; continue future
  visual work from `docs/reference/frontend-design-contract.md`.
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

The pre-4.0.0 doc-eval, skill-eval, and harness-docs evidence is retired along
with that tooling. Current root verification is
`python -m unittest discover -s tests`, `scripts/check-repo.ps1`,
`scripts/harness-runtime-smoke.ps1`, and `python scripts/verify-harness-kit.py`.

- `scripts/harness-doctor.ps1 -Status`: expected strict-path failure until an
  external EasyPowersHarness executor is configured.

## Open Problems

- Full visual automation is not implemented; v2 currently provides contracts
  and a non-installing readiness detector.

## Next Actions

1. Decide whether to configure a real external `harness.root` or keep strict
   `/choice_execute Path 2` disabled for this repository.
2. If reviewer placement behavior changes again, update the Reviewer Placement
   section of `docs/reference/dispatch-protocol.md` first and let tests catch
   command or skill matrix drift.
3. Future frontend visual automation work can add real Storybook/Playwright
   baseline generation and visual diff execution behind the existing
   tool-conditional readiness lanes.
