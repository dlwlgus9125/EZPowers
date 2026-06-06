---
doc_type: reference
authority: canonical
status: active
---

# Architecture

EZPowers is organized as a harness interface around command prompts, reference
contracts, reviewer agents, skills, and local verification scripts.

## System Context

The repo is consumed by Claude/Codex-style coding agents as a workflow plugin.
Agents read short command controllers and load detailed contracts only when a
stage requires them.

## Module Boundaries

- `commands/`: slash-command controllers.
- `docs/reference/`: canonical contracts and schemas.
- `agents/`: reviewer and worker prompt templates.
- `skills/`: reusable agent workflows.
- `scripts/`: deterministic gates, eval runners, and helper utilities.
- `evals/`: command and skill regression/capability cases.
- `bin/`: observation-only JSONL trace collector (`trace.sh`).
- `hooks/`: opt-in trace-hook policy metadata.
- `harness-kit/`: bundled verified local kit installed by `/setup`.
- `harness_versions/`: append-only harness change log.
- `phases/`: harness phase state generated during setup and execution.
- `plugins/`: generated Claude/Codex plugin mirror for packaging.
- `.claude-plugin/`, `.codex-plugin/`: Claude and Codex plugin manifests.

## Lifecycle And Operations

Setup creates root state, design_architecture fixes architecture and test
methodology, spec creates feature specs, prepare_execute creates task slices,
choice_execute routes implementation, and eval/validation gates protect changes.

## Decision Log

Durable decisions live in `docs/decisions/`.
