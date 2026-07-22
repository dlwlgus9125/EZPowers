# EZPowers Roadmap

## Current: v5.0.0

- Merge clarification and “grill me” stress-testing under `deep-interview`.
- Keep `spec` narrow: settled decisions become acceptance criteria.
- Replace `choice-execute` and all external/phase execution machinery with one
  host-native `execute` flow.
- Install complete project-local skills, contracts, runtime, and frontend tool
  for both hosts from a hash manifest.
- Bind verification evidence to real command output, spec/plan/config hashes,
  installed-kit identity, and Git workspace state; certify only fresh
  all-scope results.
- Keep candidate validation read-only, make execution activation explicit, and
  expose revalidated task evidence without promoting it to completion.
- Keep Codex HUD global and opt-in, separate from project setup.

## Later, only with demonstrated demand

- Real visual-baseline generation and visual-diff execution behind the current
  frontend readiness detector.
- Additional host adapters when their official APIs provide a measurable user
  benefit that the shared verdict alone cannot deliver.

Model routing, reviewer fleets, generic retries, custom task graphs, phase
conversion, and an external executor are not roadmap items; supported hosts
already own those execution concerns.
