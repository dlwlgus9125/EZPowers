---
name: ezpowers-workflow
description: Use when the user wants to run or adapt an EZPowers workflow in Codex, including setup, brainstorm, pipeline-audit, plan, choiceexecutor, executeharness, review, sync-docs, eval, or feedback.
---

# EZPowers Workflow

## Purpose

This is the Codex adapter for the existing EZPowers workflow documents. Keep the workflow source of truth in `commands/`; this skill only maps user intent to the right command document and explains how to apply it from Codex.

## Command Mapping

Use these files as the procedure reference:

| User intent | Reference |
| --- | --- |
| Initialize project harness or steering docs | `commands/setup.md` |
| Turn an idea into a spec | `commands/brainstorm.md` |
| Audit spec/plan readiness | `commands/pipeline-audit.md` |
| Decompose an approved spec into tasks | `commands/plan.md` |
| Choose and run an execution path | `commands/choiceexecutor.md` |
| Delegate execution to EasyPowersHarness | `commands/executeharness.md` |
| Review implementation against spec | `commands/review.md` |
| Sync references and docs | `commands/sync-docs.md` |
| Run eval suite or inspect scores | `commands/eval.md` |
| Promote feedback or traces into eval cases | `commands/feedback.md` |

## Codex Adaptation Rules

- Read the matching `commands/*.md` file before acting, then follow its intent and gates.
- Preserve existing Claude plugin behavior: do not rewrite `.claude-plugin/`, `commands/`, `agents/`, or `hooks/` just to adapt a workflow for Codex.
- Translate Claude-specific tool names to Codex equivalents only at execution time. For example, use normal shell reads/searches for `Read` or `Grep`, and use Codex subagents only when the active Codex instructions allow delegation.
- Treat Claude hook setup as Claude-specific. Do not enable or invoke `hooks/hooks.json` from Codex unless the user explicitly asks for Claude hook work.
- Keep evidence-based verification from the referenced command: run the stated checks where possible and report any check that cannot run.

## Default Flow

For a normal feature request:

1. Use `commands/setup.md` only if the target project has no EZPowers harness context.
2. Use `commands/brainstorm.md` to produce or refine the spec.
3. Use `commands/pipeline-audit.md` after the spec is accepted.
4. Use `commands/plan.md` after the audit passes.
5. Use `commands/pipeline-audit.md` again after the plan is accepted.
6. Use `commands/choiceexecutor.md` to implement the plan.
7. Use `commands/review.md` before final handoff when implementation changed code.

When a user asks for one named EZPowers command, use only that command's reference unless it explicitly requires an earlier artifact.
