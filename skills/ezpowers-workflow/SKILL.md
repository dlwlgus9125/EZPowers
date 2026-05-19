---
name: ezpowers-workflow
description: Direct-invocation Codex adapter for EZPowers command documents. Use only when the user explicitly asks for the adapter itself or for a Codex translation of an EZPowers command; for named EZPowers commands, read the target commands/*.md file directly.
---

# EZPowers Workflow

This skill adapts EZPowers command documents for Codex. The source of truth stays in plugin-root `commands/*.md`.

Resolve command docs from this skill's plugin root. From `skills/ezpowers-workflow/SKILL.md`, use `../../commands/<name>.md`.

Do not use this skill as a background router. If the user invokes a named EZPowers command, read that command document directly and follow it.

## Command Map

| Intent | Source |
| --- | --- |
| Setup harness | `../../commands/setup.md` |
| Brainstorm/spec | `../../commands/brainstorm.md` |
| Pipeline audit | `../../commands/pipeline-audit.md` |
| Plan tasks | `../../commands/plan.md` |
| Choose execution | `../../commands/choiceexecutor.md` |
| Execute harness | `../../commands/executeharness.md` |
| Review | `../../commands/review.md` |
| Sync docs | `../../commands/sync-docs.md` |
| Eval | `../../commands/eval.md` |
| Feedback | `../../commands/feedback.md` |

## Adapter Rules

- Read the matching command before acting.
- Translate Claude-specific tool names to Codex tools only at execution time.
- Do not rewrite `.claude-plugin/`, `commands/`, `agents/`, or `hooks/` just to adapt a workflow.
- Treat hooks as Claude-specific unless the user asks for hook work.
- Preserve each command's evidence and verification gates.
