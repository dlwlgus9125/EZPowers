---
name: wiki
description: Use when the user asks to capture, search, inspect, promote, refresh, lint, or prune EZPowers project-local session knowledge.
---

# Wiki

Manage the local, worktree-specific knowledge store under `.ezpowers/wiki/`.
The wiki is supporting memory, never canonical project authority, completion
evidence, or a substitute for specs, plans, repository instructions, or source
files.

## Load the contract

Read `.ezpowers/contracts/wiki-contract.md` before using the installed skill.
Before installation, resolve the same contract from the plugin distribution's
`docs/reference/wiki-contract.md`. Follow its storage, privacy, query,
promotion, backup, and pruning rules exactly.

## Choose an operation

- Use `wiki query` before implementation when the user asks whether the project
  has a prior decision, convention, debugging note, or environment fact.
- Use `wiki add` only for concise reusable knowledge supplied or confirmed by
  the user. Put operation inputs in one JSON object.
- Use `wiki read`, `wiki list`, and `wiki lint` for non-mutating inspection.
- Use `wiki refresh` to rebuild the derived index after a recoverable local
  inconsistency.
- Use `wiki promote` only after the knowledge has been authored into an
  existing canonical Markdown target. Preview first, show the exact target and
  binding hash, then confirm with the unchanged preview hash.
- Use `wiki prune` only for explicitly named unpromoted pages. Preview first;
  confirm only after the user accepts the page list. The runtime creates a
  local backup before removal.

Run the installed runtime from the worktree root:

```text
python .ezpowers/ezpowers.py wiki <operation> ... --json
```

Do not edit `index.md`, `log.md`, page frontmatter, promotion bindings, or
backup records by hand when the runtime can perform the operation.

## Session capture

SessionEnd capture is opt-in setup behavior, separate from the completion Stop
hook. Never enable it without explicit approval. It may retain only the
allowlisted session identifier fingerprint, host/event metadata, changed
project paths, active plan, and check IDs/statuses. Never place transcripts,
prompts, responses, tool payloads, command output, environment variables,
secrets, or arbitrary hook fields into the wiki.

Capture is best effort and must return an empty host response even when local
recording fails. Inspect `.ezpowers/wiki/errors/` only when diagnosing a
capture problem.

## Preserve authority boundaries

Treat candidate pages as hints that require repository verification. A
promoted page records the canonical target and its hash but does not own or
rewrite that target. Never make completion depend on local wiki content, and
never add `.ezpowers/wiki/` to a commit unless the user explicitly changes the
product's local-only policy.
