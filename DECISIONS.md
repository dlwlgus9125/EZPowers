# EZPowers Decision Log

Durable architecture decisions live under `docs/decisions/` when all three ADR
conditions in `docs/decisions/README.md` are met.

## Active Decisions

- 2026-07-22: Adopt a host-native, project-local verification core and retire
  the external executor and duplicated orchestration layers. See
  `docs/decisions/0001-host-native-project-local-core.md`.
- 2026-07-22: Merge the former `grill-with-docs` behavior into
  `deep-interview` as an explicit `stress-test` mode. Keep `spec` separate and
  limited to acceptance-contract generation.
- 2026-07-22: Supersede the preceding `deep-interview` mode decision after
  cross-host prior-art research. Keep only session-local clarification of a
  vague user request; retain assumption and boundary challenges as question
  techniques, but remove artifact review, persistence, and automatic handoff.
  `spec` remains a separate, explicitly invoked skill in the same session.
- 2026-07-22: Keep frontend readiness and the Codex HUD independent of the core;
  the HUD remains a user-approved global change and is never project-installed.
