---
description: Define project architecture, test strategy, structure, and roadmap
allowed-tools: [Bash, Read, Write, Glob, WebSearch, Agent, AskUserQuestion]
---

# /design_architecture - Architecture And Test Design

## Purpose

Convert the initialized harness into a project-specific operating model:
backend/frontend direction, project structure, roadmap, lifecycle constraints,
and verification methodology. Do not implement product code.

## Read

- `docs/reference/design-architecture-contract.md`
- `docs/reference/mattpocock-harness-adapter.md`
- `docs/reference/reviewer-placement-contract.md`
- `docs/reference/setup-contract.md`
- `docs/reference/architecture-readiness-contract.md`
- `docs/reference/ui-verification-adapter-contract.md`
- `docs/reference/verification-contract.md`
- `.harness/config.json`, `AGENTS.md`, `CONTEXT.md`, `phases/index.json`
- Source tree, manifests, existing architecture docs, UI routes, API surfaces,
  CI/deploy files, tests, and recent git changes

## Rules

- If setup is missing or the local kit ledger is invalid, route to `/setup`.
- Set architecture `in_progress` in `phases/index.json` before writes.
- Read repo evidence before asking. Ask one question at a time.
- Use web research only for current framework, frontend, deployment, or test
  best practices that cannot be inferred locally. Record source URLs in the
  design artifact.
- Select verification profiles by capability, not by one tool name. Playwright
  is preferred for browser e2e when viable, but equivalent adapters are valid
  only when they preserve the same user-observable oracle.
- For UI projects, write the chosen UI verification adapter, fallback adapter,
  oracle, command, and screenshot/accessibility expectations.
- Do not leave implementation agents to invent architecture, folder structure,
  data flow, lifecycle, deploy target, or test methodology.
- Dispatch `ezpowers:architecture-reviewer` through the reviewer placement gate.

## Stop conditions

- `.harness/config.json` or `.harness/ezpowers/ledger.json` is missing or
  unverifiable.
- The project type, deploy surface, or UI/API boundary cannot be inferred and
  the user has not supplied it.
- A UI surface exists but no automatable adapter can be selected or planned.
- Writing would overwrite human-authored architecture docs without approval.

## Outputs

- Updated `docs/reference/architecture.md`.
- Updated `docs/reference/testing-methodology.md`.
- Updated `docs/reference/project-structure.md`.
- Updated `docs/product/ROADMAP.md`.
- Updated `docs/ux/README.md` or `docs/release/README.md` when applicable.
- Updated `.harness/config.json` verification, app_delivery, and model defaults.
- Updated `phases/index.json` architecture state.
- Architecture reviewer verdict.
- Next command: `/spec`.
