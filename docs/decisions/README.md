# Architecture Decision Records (ADR)

## Writing Criteria — 3-Condition Gate

Write an ADR only when **all three conditions are true**:

1. **Hard to reverse** — the cost of changing your mind later is significant
2. **Surprising without context** — a future reader would ask "why was this done this way?"
3. **Real trade-off** — genuine alternatives existed and one was chosen for a specific reason

Skip the ADR if any condition is missing.

## Format

Filename: `NNNN-slug.md` (4-digit sequence, e.g., `0001-event-sourced-orders.md`)

```markdown
# NNNN. Short title

[1-3 sentences: context, decision, rationale]
```

### Optional Sections

- **Status**: proposed / accepted / deprecated
- **Considered Options**: alternatives reviewed
- **Consequences**: outcomes of the decision

## Numbering

Scan for the highest existing number and add one. Do not fill gaps.

## Examples That Warrant An ADR

- Architecture shape, such as monolith versus microservices
- Integration pattern, such as event sourcing versus CRUD
- Technology lock-in to a specific database or framework
- Module or ownership boundary
- Intentional deviation from an established convention
- Rejected alternative with non-obvious rationale

## Examples That Do Not

- Variable naming conventions
- Library minor-version selection
- Following a standard pattern with no meaningful trade-off
