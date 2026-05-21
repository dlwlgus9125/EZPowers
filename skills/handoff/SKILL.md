---
name: handoff
description: Compact the current conversation into a handoff document so a fresh session can continue. Use when ending a session mid-workflow, switching context, or the user says "handoff", "handoff note", or "session summary".
argument-hint: "What will the next session focus on?"
---

# Handoff

Write a handoff document summarizing the current conversation so a fresh agent can continue the work.

## Output Path

Save to `docs/handoff-session{N}.md` where `{N}` is the next available number (check existing files in `docs/`).

## Required Sections

```markdown
# Handoff - Session {N}

## Workflow State
- **Current stage**: which EZPowers command was last completed or is in progress
- **Next action**: the command or skill the next session should run first
- **Blocking issues**: anything unresolved that prevents progress

## Context Summary
(What was discussed, decided, or attempted; only content NOT already in artifacts)

## Artifact References
(Paths to specs, plans, ADRs, CONTEXT.md, or other generated docs; do not duplicate their content)

## Open Questions
(Decisions deferred or unresolved; include why they were deferred)

## Suggested Skills
(Skills or commands recommended for the next session)
```

## Rules

1. **No duplication** - if it is already in a spec, plan, ADR, or CONTEXT.md, reference by path only
2. **Capture what artifacts miss** - reasoning, failed approaches, deferred decisions, verbal agreements
3. **Include workflow position** - the next session must know exactly where to resume in the `/setup` -> `/design_architecture` -> `/spec` -> internal audit -> `/prepare_execute` -> internal audit -> `/choice_execute` flow
4. **Tailor to arguments** - if the user describes what the next session will focus on, shape the document accordingly
5. **Keep it short** - a handoff that is longer than the conversation it summarizes has failed
