# EZPowers Agent Guide

EZPowers is a dual-host workflow plugin that keeps repository documentation,
local supporting knowledge, project-specific intent, verification commands,
completion evidence, and resume state in the target repository. Claude Code
and Codex perform implementation and orchestration; EZPowers supplies the same
local completion verdict to both.

## Start Here

Read these files in order before changing this repository:

1. `AGENTS.md`
2. `PROGRESS.md`
3. `feature_list.json`
4. `docs/INDEX.md`

Preserve user changes shown by `git status --short --branch`. Use repository
evidence before conversation memory.

## Current Workflow

```text
setup -> documentation preview/apply/lint
      -> deep-interview (when the request is ambiguous or has a plausible
                         consequential blind spot)
      -> design-architecture (when technical boundaries are unsettled)
      -> spec -> prepare-execute -> execute

explicit harness-chain:
configure once -> feature preview -> independent oracle audit
               -> one feature approval -> host-native loop
               -> verify -> independent review/conditional QA -> certify
```

Plugin invocation differs by host: Claude Code uses `/ezpowers:<name>` and
Codex uses `$ezpowers:<name>`. Project-local copies use the host's normal local
skill syntax. See `docs/reference/codex-plugin-discovery.md`.

Roles are intentionally narrow:

- `deep-interview`: session-only clarification that resolves stated ambiguity
  and plausible consequential blind spots before rewriting the request; it
  does not review artifacts, write files, or invoke another workflow. After
  explicit confirmation, an already active Plan Mode resumes host-native
  planning without granting implementation authority.
- `diagnose`: exact-reproduction-gated, end-to-end bug fixing by default for
  explicit invocation or fix/debug requests. It forbids hypotheses and product
  edits until the user's symptom has run red and been minimised, then continues
  through a source-cause patch and original-symptom verification. If exact red
  cannot be produced it requests the missing evidence and does not guess; only
  an explicit analysis-only/no-edit request stops an otherwise reproducible
  path before changes.
- `codebase-design`: implicit focused advisory for deep modules, small
  interfaces, honest seams, and refactor-surviving tests.
- `improve-codebase-architecture`: explicit-only product-code scan that
  renders a temporary offline report and explores one selected candidate; it
  does not audit the workflow harness or implement the refactor.
- `spec`: settled decisions only, expressed as traceable acceptance criteria.
- `prepare-execute`: criterion coverage and exact project checks.
- `execute`: host-native implementation followed by local verify/certify.
- `setup --refresh`: installation repair; there is no separate reset skill.
- `setup --refresh-docs`: explicit repository re-analysis and conflict-safe
  documentation staging; it is a skill workflow flag, not an installer flag.
- `wiki`: local knowledge query, capture, promotion, and pruning; candidates
  never override repository evidence, and risky operations still require
  explicit preview/approval.
- `harness-chain`: explicit-only project questions and one-feature approval
  for an unattended, limit-bounded run; it freezes acceptance inputs and binds
  host-native independent review without becoming a task executor.

`frontend-design` is an independent advisory skill. `hud` is an explicit,
plugin-only global Codex utility and is never installed into a project kit.

## Responsibility Boundary

- Claude Code or Codex owns editing, shell execution, subagents, worktrees,
  sandboxing, general retry policy, and code review.
- EZPowers owns the registered documentation graph, managed spec/plan data,
  project-specific argv checks, real command execution, hashed evidence,
  certification freshness, and resume state. In an explicitly approved chain
  it also owns frozen hashes, review challenges/receipts, hard limits, and the
  terminal verdict.
- `AGENTS.md` is canonical project guidance. Claude projects use an exact
  `CLAUDE.md` import shim containing `@AGENTS.md`.
- `.ezpowers/wiki/` is local supporting memory, excluded from completion
  freshness, and never a canonical or completion authority.
- Do not reintroduce model routing, shipped reviewer agents, plan-to-phase
  conversion, numbered execution paths, or an implicit external executor.
- A chain review uses a real host-native subagent bound at runtime; main-agent
  prose or a bundled reviewer persona is not equivalent evidence.
- Codex chain continuation comes only from one native goal. Claude chain
  continuation comes only from its project Stop hook. Never run both
  authorities for one feature.
- Do not claim identical host capabilities. Only the core EZPowers verdict is
  host-independent; hook response schemas remain thin host adapters.

## Source of Truth

- Project config: `.ezpowers/config.json`
- Explicit chain config: `.ezpowers/chain.json`
- Feature approvals: `.ezpowers/approvals/`
- Documentation graph: `.ezpowers/docs.json`
- Local supporting knowledge: `.ezpowers/wiki/`
- Resume/evidence pointer: `.ezpowers/state.json`
- Runtime: `scripts/ezpowers.py`
- Distribution manifest: `project-kit/v5.3.0/manifest.json`
- Specs and plans: `docs/specs/`, `docs/plans/`
- Canonical contracts: `docs/reference/*-contract.md`
- Product state: `PROGRESS.md`, `feature_list.json`
- Audit record: `docs/reports/workflow-harness-audit-2026-07-24.md`

The installed runtime, manifest, skills, references, contracts, frontend
readiness tool, and architecture report renderer must be self-contained.
Preserve exact check argv unless the approved spec or plan changes. Never
weaken validation, evidence, or freshness rules merely to pass a gate.

Do not install plugins, change global configuration, commit, or push without
explicit user authorization.

## Repository Verification

```powershell
python -m unittest discover -s tests
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/check-repo.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/harness-runtime-smoke.ps1
python scripts/verify-harness-kit.py
python scripts/plugin_smoke.py --host both
```

Completion requires applicable command output and a clean final diff review,
not a prose claim or a test-name/string-presence check.
