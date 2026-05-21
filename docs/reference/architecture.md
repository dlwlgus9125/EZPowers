---
doc_type: reference
authority: canonical
status: draft
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

## Lifecycle And Operations

Setup creates root state, design_architecture fixes architecture and test
methodology, spec creates feature specs, prepare_execute creates task slices,
choice_execute routes implementation, and eval/validation gates protect changes.

## Decision Log

Durable decisions live in `docs/decisions/`.
