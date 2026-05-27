---
description: Prepare and verify package, release, and deployment work
allowed-tools: [Bash, Read, Write, Agent, AskUserQuestion]
---

# /deploy - Release And Deployment

## Purpose

Prepare deployment or release work as harness-tracked evidence. Validate build
artifacts, configuration, rollout, rollback, and post-deploy checks before
reporting release readiness.

## Read

- `docs/reference/app-delivery-contract.md`
- `docs/reference/mattpocock-harness-adapter.md`
- `docs/reference/verification-contract.md`
- `docs/reference/plan-contract.md`
- `docs/reference/reviewer-placement-contract.md`
- `docs/reference/domain-language.md`
- `.harness/config.json`, `docs/release/`, active specs/plans, CI config,
  package manifests, deployment manifests, environment docs, and recent diffs

## Rules

- If deployment behavior or release surface is not specified, route to
  `/design_architecture` or `/spec`.
- Require build artifact verification, environment readiness, smoke or health
  checks, rollback rule, and release notes when deployment is in scope.
- Deployment tasks still go through `/prepare_execute` and `/choice_execute`
  unless the command is only producing a release readiness report.
- UI deployments must preserve the configured UI verification adapter or add a
  deployment-specific equivalent oracle.
- Never mark release ready from build success alone.

## Stop conditions

- Required environment variables, preview target, artifact path, or rollback
  rule is missing.
- Required smoke, health, UI, or API verification cannot run.
- Release would bypass an unresolved audit, review, or wiring gate.

## Outputs

- Release readiness report.
- Artifact paths and verification commands.
- Rollout and rollback evidence.
- Route decision for any missing spec, plan, or execution work.
