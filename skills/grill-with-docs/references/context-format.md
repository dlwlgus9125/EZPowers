# CONTEXT.md Format

Use this format when creating or updating `CONTEXT.md` in the target project.

## Structure

```markdown
# Domain Language

## Language

**Order** — A customer's request to purchase one or more products. An Order
is always associated with exactly one Customer. _Avoid:_ "purchase",
"transaction" (too generic).

**Line Item** — A single product entry within an Order, including quantity
and unit price. _Avoid:_ "order item", "product line".

## Relationships

- An **Order** contains one or more **Line Items**.
- A **Customer** places zero or more **Orders**.

## Flagged Ambiguities

- **"Account"** — Currently used to mean both Customer (billing context) and
  User (auth context). Resolution: rename to Customer and User respectively.
  Status: **unresolved**.
```

## Rules

- **Be opinionated.** The glossary should make naming arguments unnecessary.
- **Flag conflicts.** When a term in code diverges from the glossary, surface
  it during grilling sessions.
- **Keep definitions tight.** One sentence. If you need two, the concept might
  need splitting.
- **Show relationships.** Terms that only make sense in relation to each other
  should appear together.
- **Only project-specific terms.** Generic programming terms (function, module,
  class) do not belong unless the project gives them domain-specific meaning.

## Lazy Creation

Do not create `CONTEXT.md` during `/setup` if there are no terms to record.
Create it when the first term is resolved during a grilling or design session.

## ADR Path

When an ADR is needed, place it in `docs/decisions/` with sequential numbering:
`docs/decisions/0001-slug.md`. An ADR can be a single paragraph — the value is
in recording _that_ a decision was made and _why_.
