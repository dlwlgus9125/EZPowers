# EZPowers Documentation Index

## Product

- [PRD](product/PRD.md): canonical product intent and responsibility boundary.
- [Roadmap](product/ROADMAP.md): current release and deliberately deferred work.

## Live Reference

- [Architecture](reference/architecture.md): v5 repository and installed-kit map.
- [Host Plugin Discovery](reference/codex-plugin-discovery.md): Claude Code and Codex discovery, invocation, hook, worktree, and sandbox differences.
- [Setup Contract](reference/setup-contract.md): self-contained install, refresh, migration, conflicts, and optional hooks.
- [Design Architecture Contract](reference/design-architecture-contract.md): project architecture and verification-design artifact.
- [Frontend Design Contract](reference/frontend-design-contract.md): frontend readiness and tool-conditional visual lanes.
- [Spec Contract](reference/spec-contract.md): managed acceptance-criteria schema.
- [Plan Contract](reference/plan-contract.md): managed task/check schema and coverage rules.
- [Verification Contract](reference/verification-contract.md): command execution, evidence, certification, freshness, resume, and host verdict adapters.
- [Codex HUD](reference/codex-hud.md): explicit global native Codex footer utility.

## Decisions and Audit

- [ADR policy](decisions/README.md)
- [Host-native project-local core ADR](decisions/0001-host-native-project-local-core.md)
- [2026-07-22 workflow harness audit](reports/workflow-harness-audit-2026-07-22.md)

## Generated Project Artifacts

- `docs/specs/`: feature acceptance contracts written by `spec`.
- `docs/plans/`: criterion-to-task/check mappings written by `prepare-execute`.
- `docs/ux/frontend-design.md`: created only for projects with a UI surface.

## Archive

`archive/` contains historical evidence only. It has no runtime or contract
authority and may mention removed commands, external paths, or old versions.
