# Architecture Review Fixture

This repository models Order intake through HTTP and batch entry points.
Architecture reviews are read-only: do not modify product code, tests,
`CONTEXT.md`, or ADRs.

When the user names Order intake, keep the scan to `src/http_checkout.py`,
`src/batch_checkout.py`, `src/order_rules.py`, and their tests. Preserve both
public entry points for compatibility.

Do not run tests or builds during an advisory architecture scan. A later
authorized refactor verifies behavior with:

```text
python -m unittest discover -s tests
```
