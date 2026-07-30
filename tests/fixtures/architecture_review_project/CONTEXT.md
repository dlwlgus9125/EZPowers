# Domain Context

- **Order intake** accepts an Order request, enforces item invariants, computes
  its quoted total, persists the Order, and emits an acceptance notice.
- **Order request** is untrusted input from either HTTP or batch ingestion.
- **Acceptance notice** is emitted only after persistence succeeds.
