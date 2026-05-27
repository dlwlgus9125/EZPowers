---
doc_type: reference
authority: canonical
status: draft
---

# Config

Root harness configuration lives in `.harness/config.json`.

The canonical setup schema is defined in `docs/reference/setup-contract.md`.
This repository is configured as a plugin/library artifact, so runtime smoke is
not required at the repo root. Generated executable target projects still need
runtime smoke, wiring, UI adapter, and app-delivery verification according to
the contracts.
