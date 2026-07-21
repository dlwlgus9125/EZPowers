---
doc_type: reference
authority: generated
status: active
---

# Architecture

Maintained by `/sync-docs`. Generated overview; contracts own enforceable rules.

EZPowers is organized as a harness interface around workflow skills, reference
contracts, reviewer agents, and local verification scripts.

## System Context

The repo is consumed by Claude/Codex-style coding agents as a workflow plugin.
Agents read short workflow-skill controllers and load detailed contracts only
when a stage requires them.

## Module Boundaries

- `skills/`: workflow-skill controllers plus independent agent skills.
- `agents/`: reviewer and workflow-runner prompt templates.
- `docs/`: product contract, reference contracts, ADRs, specs, and plans.
- `scripts/`: deterministic PowerShell/Python gates and helper utilities.
- `tests/`: Python unit tests for contracts and runners.
- `harness-kit/`: bundled verified local kit installed by `/setup`.
- `phases/`: harness phase state generated during setup and execution.
- `harness_versions/`: append-only harness change log.
- `.githooks/`: pre-commit gate wiring (`core.hooksPath`).
- `.claude-plugin/`, `.codex-plugin/`: Claude and Codex plugin manifests.

## Lifecycle And Operations

Setup creates root state, design_architecture fixes architecture and test
methodology, spec creates feature specs, prepare_execute creates task slices,
choice_execute routes implementation, and the structural commit gate
(`scripts/check-repo.ps1`) protects changes.

## Decision Log

Durable decisions live in `docs/decisions/`.
