# EZPowers Progress

## Current State

EZPowers v5.4.0 project kit and plugin candidate are present in the working tree
on `main`. F20 is complete; F19 remains the release blocker because its live
dual-host diagnosis probe still needs external host access. The candidate
preserves the host-native verification core, documentation graph, local wiki,
explicit harness chain, and Plan Mode-aware clarification while adding a
context-efficient evidence explanation skill, tightening diagnosis around an
exact-reproduction gate, and retaining the harness-chain loop hardening (a
reviewer rubric whose embedded template matches the receipt parser exactly and
stays FAIL when copied unedited, chain hooks that degrade to a fail-safe no-op
instead of exit 2 on unreadable runtime state, and `PENDING_LOOP` activation
blocks counted against `total_iterations`):

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
- a session-only `deep-interview` that separates stated gaps from an always-run
  internal blind-spot pass, exposes only plausible consequential candidates,
  challenges framing when material, avoids ritual questions, and resumes an
  already active Plan Mode without artifacts or implementation authority;
- an implicit 374-word `explain-with-evidence` presentation skill that follows
  the latest substantive user language, uses only observed narrative stages,
  keeps fixed artifacts and exact verdicts unchanged, and ships its pinned
  Apache-2.0 notice outside model context;
- fix-complete `diagnose`, which forbids hypotheses and product edits until a
  command has shown the user's exact symptom red and the scenario has been
  minimised; if that gate cannot open it requests the missing evidence without
  guessing, while a reproducible path still owns the source-cause patch,
  original-symptom rerun, and affected checks unless analysis-only/no-edit
  behavior is explicit;
- focused deep-module `codebase-design`, and an explicit
  `improve-codebase-architecture` product-code scan that freezes named scope,
  binds candidates to real source lines and decision context, defers interface
  design until selection, and emits input/source/report hashes in a temporary
  schema-v2 offline report that never becomes repository documentation or
  completion evidence;
- an exact fourteen-skill plugin and thirteen-skill project catalog with distinct
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
- `F17`: fix-complete `diagnose` loop.
- `F18`: decision-ready `deep-interview` blind-spot pass.
- `F20`: context-efficient evidence explanations.

## In-Progress Item

- `F19`: exact-reproduction-gated `diagnose`. The skill, contract, metadata,
  deterministic receipts, and opt-in dual-host probe are implemented. Release
  completion is waiting on an authenticated Claude call and a Codex host where
  the isolated fixture can execute its authoritative Python command inside the
  configured workspace sandbox.

The v5.4 project kit installs thirteen project skills, ten canonical contracts,
and two deterministic tools. The plugin exposes those skills plus the
plugin-only global `hud` utility.

## Verification Evidence

v5.4.0 architecture-scan boundary hardening verification on 2026-07-30:

- `python -m unittest discover -s tests`: 158 tests passed in 723.289
  seconds.
- `python -m unittest tests.test_architecture_review_report
  tests.test_v5_workflow_surface`: 19 focused tests passed in 7.166 seconds.
- The self-contained dual-host install and distribution-removal tests passed
  with the skill-local report contract and renderer resolver installed
  byte-identically for both hosts.
- An actual two-turn Codex 0.146.0 call on the isolated Order intake fixture
  kept the named scope, ran no tests or builds, produced a schema-v2 receipt
  with one candidate and input/source/report hashes, deleted its temporary
  JSON, preserved a clean Git state, stopped for candidate selection before
  interface design, then compared two materially different seams in the
  selected candidate's `Refactor brief`.
- The rendered report cited all six affected/context files, excluded the
  out-of-scope health module, contained compatibility, migration, ADR, and top
  rationale sections, had no remote/script dependency, and its observed file
  hash matched the receipt.
- Claude Code 2.1.220 accepted the plugin manifest, but
  `claude auth status` reported `loggedIn: false` and `authMethod: none`; the
  actual `claude -p` architecture call exited 1 before returning a model
  response. This is recorded as an external authentication blocker, not a
  semantic pass or product failure.
- `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/check-repo.ps1`:
  PASS.
- `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/harness-runtime-smoke.ps1`:
  PASS for real install -> validate -> verify -> certify -> stale.
- `python scripts/verify-harness-kit.py`: v5.4 project kit manifest valid with
  thirteen project skills, ten contracts, and two tools.
- `python scripts/plugin_smoke.py --host both`: both file surfaces passed,
  Claude 2.1.220 accepted the manifests, and Codex 0.146.0 loaded all project
  and namespaced skills with matching prompts and the required architecture
  resources in isolation.

v5.4.0 context-efficient evidence explanation verification on 2026-07-27:

- `python -m unittest discover -s tests`: 153 tests passed in 696.690
  seconds.
- `python -m unittest tests.test_v5_workflow_surface
  tests.test_codex_plugin_discovery tests.test_repo_check`: 27 focused tests
  passed in 7.243 seconds.
- `quick_validate.py skills/explain-with-evidence`: skill structure valid.
- `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/check-repo.ps1`:
  PASS.
- `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/harness-runtime-smoke.ps1`:
  PASS for real install -> validate -> verify -> certify -> stale.
- `python scripts/verify-harness-kit.py`: v5.4 project kit manifest valid with
  thirteen project skills, ten contracts, and two tools.
- `python scripts/plugin_smoke.py --host both`: both file surfaces passed,
  Claude 2.1.220 accepted the manifests, and Codex 0.145.0 loaded all project
  and namespaced skills with matching prompts in isolation.
- The language-selection and evidence rules are covered by deterministic
  contract tests and actual host discovery. No live model-response probe was
  used, so this evidence does not claim semantic output conformance from a
  hosted model.

v5.3.4 candidate harness-chain loop hardening verification on 2026-07-26:

- `python -m unittest discover -s tests` (UTF-8 mode): 152 tests passed in
  619.895 seconds, including six new chain Stop/PreToolUse/rubric-roundtrip
  cases that pin iteration counting, the terminal iteration limit, the bounded
  `PENDING_LOOP` block, corrupt-state fail-safe hook responses, frozen-path
  denial, and that the injected rubric template parses as a valid receipt.
- `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/check-repo.ps1`:
  PASS.
- `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/harness-runtime-smoke.ps1`:
  PASS for real install -> validate -> verify -> certify -> stale.
- `python scripts/verify-harness-kit.py`: v5.3 manifest valid with refreshed
  runtime, harness-chain skill, and harness-chain contract hashes.
- `python scripts/plugin_smoke.py --host both`: both file surfaces passed,
  Claude 2.1.220 accepted the manifests, and Codex 0.145.0 loaded all project
  and namespaced skills with matching prompts in isolation.
- Deferred by user decision (Codex does not run the harness chain): the Codex
  chain Stop terminal response still emits `continue`/`stopReason` and chain
  unattended detection still reads Claude permission-mode names.

v5.3.3 candidate verification on 2026-07-26:

- `python -m unittest discover -s tests`: 146 tests passed in 593.061 seconds.
- `python -m unittest tests.test_codex_plugin_discovery tests.test_v5_workflow_surface`:
  19 focused tests passed on the final candidate.
- `quick_validate.py skills/diagnose` with UTF-8 mode: skill structure valid.
- `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/check-repo.ps1`:
  PASS.
- `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/harness-runtime-smoke.ps1`:
  PASS for real install -> validate -> verify -> certify -> stale.
- `python scripts/verify-harness-kit.py`: v5.3 manifest valid with refreshed
  diagnose skill, project metadata, and engineering-contract hashes.
- `python scripts/plugin_smoke.py --host both`: both file surfaces passed,
  Claude 2.1.220 accepted the manifests, and Codex 0.145.0 loaded all project
  and namespaced skills with matching prompts in isolation.
- The real Codex diagnose call attempted `python reproduce_exact.py`, received
  an execution-policy rejection before launch, made no product edit or
  hypothesis, and requested the missing command/write access. This confirms
  the no-reproduction blocker discipline but does not earn fixed-path
  red-to-green evidence.
- `claude auth status` reported `loggedIn: false` and `authMethod: none`, so no
  authenticated Claude diagnose model call could run.

The candidate is not release-complete until both live hosts pass the fixable
baseline-red-before-patch case and the missing-capture no-edit case. No v5.3.3
completion event has been appended to `harness_versions/changelog.jsonl`.

Final v5.3.2 plugin patch verification on 2026-07-26:

- `python -m unittest discover -s tests`: 141 tests passed in 601.146 seconds.
- `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/check-repo.ps1`:
  PASS.
- `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/harness-runtime-smoke.ps1`:
  PASS for real install → validate → verify → certify → stale.
- `python scripts/verify-harness-kit.py`: v5.3 manifest valid with refreshed
  skill and metadata hashes.
- `python scripts/plugin_smoke.py --host both`: both file surfaces passed,
  Claude 2.1.220 accepted the plugin and marketplace manifests, and Codex
  0.145.0 loaded all project and namespaced skills with matching prompts.
- Independent forward-tests made an irreversible deletion request expose paid,
  contractual, and legal-retention exceptions; challenged public customer
  details in a general team policy; and returned a concise confirmation without
  inventing a blind spot for an already-settled retrospective request.
- The revised skill is 974 words versus the prior 964, while adding the
  explicit-gap/blind-spot split, plausibility/consequence filter, and
  no-ritual-question rule.

### Previous v5.3.1 baseline

Final v5.3.1 plugin patch verification on 2026-07-24:

- `python -m unittest discover -s tests`: 141 tests passed.
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
- An isolated `diagnose` forward-test reproduced a tenant-scoped event
  filtering failure, preserved the existing regression test, changed only
  product code, and finished with the minimal and full fixture commands green.

### Previous v5.3.0 baseline

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
