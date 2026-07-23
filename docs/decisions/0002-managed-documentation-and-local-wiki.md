# 0002. Separate managed documentation from local supporting knowledge

**Status:** accepted

EZPowers will treat root `AGENTS.md` as canonical cross-host guidance, use an
exact `CLAUDE.md` import shim, and manage generated documentation as a
hash-registered whole-file graph. Session knowledge lives separately under
the fingerprint-excluded `.ezpowers/wiki/` and never gains authority merely by
being captured.

## Considered Options

- Generate only specs and plans and leave repository guidance unstructured.
- Copy OMC-style hierarchical guidance into every directory.
- Keep one mutable generated section inside user-owned Markdown.
- Use a small adaptive graph with explicit external/managed ownership.
- Store session notes in tracked docs or completion evidence.
- Keep an optional local wiki with explicit promotion into existing canonical
  documents.

## Consequences

Repository context becomes navigable and shared across Claude Code and Codex
without duplicating root instructions. Existing documents and manual edits are
preserved unless the user explicitly approves adoption or a backed-up forced
replacement. Whole-file hashes make ownership and drift deterministic at the
cost of requiring staged regeneration for managed edits.

The wiki can compound useful local knowledge without invalidating completion
evidence or leaking transcripts into the repository. Its candidates must be
verified and promoted through canonical workflows, and worktrees do not share
wiki state automatically.
