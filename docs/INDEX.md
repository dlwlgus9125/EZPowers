# EZPowers Documentation Index

## Product

- [PRD](product/PRD.md): canonical product intent and responsibility boundary.
- [Roadmap](product/ROADMAP.md): current release and deliberately deferred work.
- [Visual skill guide](ezpowers-skills-guide.html): Korean workflow atlas with
  host-aware invocation examples, decision paths, and all fourteen plugin
  skill roles.

## Live Reference

- [Architecture](reference/architecture.md): v5.4 repository and installed-kit map.
- [Host Plugin Discovery](reference/codex-plugin-discovery.md): Claude Code and Codex discovery, invocation, hook, worktree, and sandbox differences.
- [Setup Contract](reference/setup-contract.md): self-contained install, refresh, clean-break legacy boundary, conflicts, and optional hooks.
- [Documentation Contract](reference/documentation-contract.md): repository analysis, adaptive Markdown graph, ownership, preview/apply, and lint.
- [Wiki Contract](reference/wiki-contract.md): local knowledge, CJK search, promotion, pruning, and SessionEnd privacy.
- [Design Architecture Contract](reference/design-architecture-contract.md): project architecture and verification-design artifact.
- [Frontend Design Contract](reference/frontend-design-contract.md): frontend readiness and tool-conditional visual lanes.
- [Spec Contract](reference/spec-contract.md): managed acceptance-criteria schema.
- [Plan Contract](reference/plan-contract.md): managed task/check schema and coverage rules.
- [Verification Contract](reference/verification-contract.md): command execution, evidence, certification, freshness, resume, and host verdict adapters.
- [Harness Chain Contract](reference/harness-chain-contract.md): explicit project configuration, frozen feature approval, asymmetric continuation, independent receipts, limits, and terminal states.
- [Engineering Practices Contract](reference/engineering-practices-contract.md): pinned provenance, diagnosis and deep-module disciplines, role boundaries, and the safe offline architecture-report schema.
- [Codex HUD](reference/codex-hud.md): explicit global native Codex footer utility.

## Decisions and Audit

- [ADR policy](decisions/README.md)
- [Host-native project-local core ADR](decisions/0001-host-native-project-local-core.md)
- [Managed documentation and local wiki ADR](decisions/0002-managed-documentation-and-local-wiki.md)
- [Explicit asymmetric harness chain ADR](decisions/0003-explicit-asymmetric-harness-chain.md)
- [Specialized engineering skills ADR](decisions/0004-specialized-engineering-skills.md)
- [Context-efficient evidence explanations ADR](decisions/0005-context-efficient-evidence-explanations.md)
- [2026-07-24 workflow harness audit](reports/workflow-harness-audit-2026-07-24.md)

## Generated Project Artifacts

- `docs/specs/`: feature acceptance contracts written by `spec`.
- `docs/plans/`: criterion-to-task/check mappings written by `prepare-execute`.
- [Skill guide frontend design](ux/frontend-design.md): selected visual
  direction, information architecture, responsive behavior, accessibility,
  and visual QA contract for the HTML guide.
- `.ezpowers/docs.json`: managed documentation graph and whole-file hashes in an installed project.
- `.ezpowers/wiki/`: optional untracked, worktree-local session knowledge.
- `.ezpowers/chain.json`, `.ezpowers/approvals/`, and chain evidence: created
  only by an explicitly configured harness chain.
