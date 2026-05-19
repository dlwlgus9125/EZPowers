# EZPowers Decision Log

This file is a session-level pointer. Durable architecture decisions belong in
`docs/decisions/` when all ADR criteria in `docs/decisions/README.md` are met.

## Active Decisions

- 2026-05-19: Treat this repository as a plugin/library artifact for root
  harness config. Runtime smoke is disabled at the repo root; generated target
  projects still require smoke according to `docs/reference/setup-contract.md`.
- 2026-05-19: Keep strict `/executeharness` disabled until a real external
  EasyPowersHarness executor is configured. Lightpath gates remain the measured
  local execution path.
- 2026-05-19: Make eval runner semantics explicit: static mode is the current
  implemented default; live slash-command execution must be opt-in and fail
  loudly until implemented.
