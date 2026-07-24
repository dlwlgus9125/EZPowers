# EZPowers Progress

## Current State

EZPowers v5.3.0 is complete in the working tree on `main`. It preserves the
host-native verification core, documentation graph, local wiki, explicit
harness chain, and Plan Mode-aware clarification while adding bounded
specialized engineering disciplines:

- repository analysis and an adaptive Markdown graph rooted at canonical
  `AGENTS.md`, exact `CLAUDE.md` import, and `docs/INDEX.md`;
- a local session wiki with deterministic CJK keyword/tag search, explicit
  promotion, backup-first pruning, and separately opt-in allowlisted
  SessionEnd capture;
- project questions for enabled hosts, acceptance oracles, QA triggers, and
  exact continuation limits, followed by a hash-bound preview and one feature
  approval;
- an isolated current-workspace baseline and bound independent oracle audit
  before approval;
- one native Codex goal or one Claude Stop loop, with real project checks,
  bound independent code review, and conditional adversarial QA before
  certification;
- a session-only `deep-interview` whose explicitly confirmed request resumes an
  already active Plan Mode without another command, repeated product questions,
  artifact creation, downstream skill invocation, or implementation authority;
- evidence-first `diagnose`, focused deep-module `codebase-design`, and an
  explicit `improve-codebase-architecture` product-code scan whose temporary
  offline report never becomes repository documentation or completion evidence;
- an exact thirteen-skill plugin and twelve-skill project catalog with distinct
  namespaced and project-local Codex prompt metadata;
- clean retirement of pre-v5 workflow input plus Claude 2.1.217 and Codex
  0.145.0 minimums before host-specific writes.

Documentation proposals are staged, previewed with a hash that binds the
bundle, registry, config, and current targets, then applied transactionally.
Unmanaged documents require explicit adoption; edited/adopted targets require
force and are backed up first. A ready graph registers `ezpowers.docs` as an
exact required project check.

The wiki remains supporting memory under `.ezpowers/wiki/`. It is excluded from
completion fingerprints, never stores transcripts through automatic capture,
and never becomes canonical or completion evidence without a separate
repository workflow.

The existing core remains unchanged in authority: Claude Code and Codex own
implementation and orchestration; EZPowers owns exact project checks, real
stdout/stderr evidence, hashes, Git-workspace freshness, certification, and
resume state. `harness-chain` is dormant until explicitly configured and run.
It does not install a second Codex executor or ask for approval on every
iteration. Frozen-input changes require reapproval; ordinary failed checks
force product rework until a configured limit becomes terminal.

## Completed Items

- `F11`: host-native, project-local verification core.
- `F12`: repository documentation bootstrap and local session wiki.
- `F13`: explicit project-specific verified harness chain.
- `F14`: workflow surface audit and host compatibility hardening.
- `F15`: Plan Mode-aware `deep-interview` continuation.
- `F16`: bounded specialized engineering skills.

The v5.3 project kit installs twelve project skills, ten canonical contracts,
and two deterministic tools. The plugin exposes those skills plus the
plugin-only global `hud` utility.

## Verification Evidence

Final v5.3.0 verification on 2026-07-24:

- `python -m unittest discover -s tests`: 140 tests passed.
- `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/check-repo.ps1`:
  PASS.
- `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/harness-runtime-smoke.ps1`:
  PASS for real install → validate → verify → certify → stale.
- `python scripts/verify-harness-kit.py`: v5.3 manifest valid with twelve
  project skills, ten contracts, and two tools.
- `python scripts/plugin_smoke.py --host both`: both file surfaces passed,
  Claude 2.1.217 accepted the plugin and marketplace manifests, and Codex
  0.145.0 loaded all twelve project and thirteen namespaced plugin skills with
  exact prompts in isolation.
- Renderer regression coverage passed for deterministic escaped offline HTML,
  strict schema/path/graph validation, repository-output rejection, atomic
  writes, and pre-existing or racing output no-overwrite behavior.

### Previous v5.2.1 baseline

Final v5.2.1 plugin patch verification on 2026-07-24:

- `python -m unittest discover -s tests`: 134 tests passed.
- `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/check-repo.ps1`:
  PASS.
- `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/harness-runtime-smoke.ps1`:
  PASS for real install → validate → verify → certify → stale.
- `python scripts/verify-harness-kit.py`: v5.2 manifest valid with nine project
  skills and nine contracts.
- `python scripts/plugin_smoke.py --host both`: both file surfaces passed,
  Claude 2.1.217 accepted both manifests, and Codex 0.145.0 loaded all nine
  project skills and all ten namespaced plugin skills enabled, error-free, and
  with exact prompts in isolation.
- Independent forward-tests passed: confirmation inside Plan Mode continued
  with the highest-impact implementation question, while confirmation outside
  Plan Mode stopped without a workflow handoff or artifact.
- The earlier `python scripts/plugin_smoke.py --host both --live-advisory`
  release probe remains recorded for v5.2.0: Codex executed the project-local
  `deep-interview` behavior; Claude's loader passed but its model call was
  externally blocked by HTTP 401 authentication with zero cost.
- `python -m unittest tests.test_harness_chain -v`: 14 chain scenarios passed,
  including isolated destructive-oracle defense, limit-one terminal behavior,
  forged receipt rejection, failed-audit hash consumption, mandatory product
  rework, same-reviewer correction, reapproval, review, QA, receipt-tamper
  detection, certification, and post-certification staleness.
- Documentation/wiki regression coverage includes stale previews, explicit
  adoption, force backups, required lint, Korean search, promotion binding,
  backup-first prune, hook idempotence/privacy, and fingerprint exclusion.

## Remaining Candidates

Full screenshot generation and visual-diff execution remain outside the core.
The readiness detector hard-gates those lanes only when the target project
already has suitable tooling or its plan explicitly adds it.

Documentation quality still depends on the host grounding generated prose in
repository evidence; the runtime can enforce provenance references, structure,
links, ownership, and hashes, but cannot prove that every natural-language
claim is semantically complete.

Cryptographic hashes detect accidental or partial tampering but are not an
authenticity boundary against an attacker who can rewrite state, artifacts,
sidecars, and hashes together. Hostile environments need repository/CI
permissions or signing outside this local core.
