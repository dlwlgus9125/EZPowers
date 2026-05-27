# Architecture Decision Records (ADR)

## Writing Criteria — 3-Condition Gate

Write an ADR only when **all three conditions are true**:

1. **Hard to reverse** — the cost of changing your mind later is significant
2. **Surprising without context** — a future reader would ask "why was this done this way?"
3. **Real trade-off** — genuine alternatives existed and one was chosen for a specific reason

Skip the ADR if any condition is missing.

## Format

Filename: `NNNN-slug.md` (4-digit sequence, e.g. `0001-event-sourced-orders.md`)

```markdown
# NNNN. Short title

[1-3 sentences: context, decision, rationale]
```

### Optional Sections (add only when needed)

- **Status**: proposed / accepted / deprecated
- **Considered Options**: list of alternatives reviewed
- **Consequences**: outcomes of this decision

## Numbering

Scan for the highest existing number and add +1. Do not fill gaps.

## Examples (decisions that warrant an ADR)

- Architecture shape (monolith vs microservices)
- Integration pattern (event sourcing vs CRUD)
- Technology lock-in (specific DB or framework choice)
- Boundary decision (module separation strategy)
- Intentional deviation (consciously breaking a convention)
- Rejected alternative with non-obvious rationale

## Examples (decisions that do NOT need an ADR)

- Variable naming conventions (easy to change)
- Library minor-version selection (not surprising)
- Following a standard pattern (no trade-off)
