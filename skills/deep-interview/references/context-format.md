# CONTEXT.md Format

Use `CONTEXT.md` only for project-specific domain language that future sessions
must interpret consistently.

```markdown
# Domain Language

## Language

**Order** — A customer's request to purchase one or more products. _Avoid:_
"transaction" when it means an Order.

## Relationships

- An **Order** contains one or more **Line Items**.

## Flagged Ambiguities

- **Account** — Used for both Customer and User. Status: **unresolved**.
```

Keep definitions short, name conflicting alternatives, and record
relationships only when they constrain product behavior.

Place an ADR at `docs/decisions/NNNN-slug.md`. Record the decision, context,
meaningful alternatives, tradeoff, and consequences in the smallest form that
will prevent future re-litigation.
