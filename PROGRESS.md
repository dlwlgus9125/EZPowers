# EZPowers Progress

## Current State

EZPowers v5.12.0 plugin and v5.12.0 project kit are present in the working tree
on `main`. F29 is complete. F19 remains explicitly deferred because its
semantic dual-host diagnosis probe still needs external access; it is not part
of the v5.12 completion claim.

F29 gives a pending review challenge of the harness chain an owner and an end.
On the v5.11.1 runtime a run that ended at the iteration limit or through the
documented emergency stop left its review gate behind, and the next feature's
oracle audit could not begin without a hand edit of the state file. A gate
whose reviewer never reported could not be ended, a rejected audit receipt
could end another feature's running run, and nothing told the main agent that
a receipt was rejected. The gate of a finished run is now dropped, a new
subject of the same kind replaces a pending challenge, `chain gate abandon`
ends a challenge whose bound reviewer cannot report, an oracle audit waits for
the running feature, and the rejection is repeated to the main agent with its
reason. Every ending without a receipt is fail-closed once a reviewer is
involved. The decisions are recorded in
`docs/decisions/0013-review-gate-lifecycle.md`.

F28 (v5.11.1) gave the optional ordinary completion Stop hook a wait rule for
a running background subagent on Claude Code, a rule for its own failure, and
an ASCII-only answer. Its decisions are recorded in
`docs/decisions/0012-completion-hook-wait-and-failure.md`.

F27 (v5.11.0) aligned the harness chain's Claude Code host adapter with the
hook payloads Claude Code 2.1.327 really sends and added the Claude Code
team's verification practice to the workflow skills. Its decisions are
recorded in `docs/decisions/0011-current-host-chain-adapter.md`.

The release keeps the host-native verification core, documentation graph,
local wiki, explicit harness chain, and Plan Mode-aware clarification:

- a typed criterion-to-task-to-check-to-evidence-to-review-to-certificate view
  derived from existing authorities, with stable task waves and graph hashes
  but no second executor, agent router, or mutable task state machine;
- an explicit `software` or `planning` project profile selected at setup and
  changed only by explicit migration, with legacy v1/v2 projects continuing
  to mean software and refresh preserving the current choice;
- planning config/plan v3 contracts that bind named binary inputs, logical
  deliverable groups, one deliverable per criterion, actual project checks,
  and direct or project-inspected review sources without a file-format
  whitelist or built-in Markdown/XLSX validator;
- planning verification and certification that bind declared bytes even when
  Git ignores them, reject missing or check-mutated outputs, and require one
  independent artifact-review PASS per logical deliverable plus conditional
  QA in an explicitly approved chain;
- per-check safety declarations, resource and implicit same-check locks,
  unsafe global barriers, complete declaration-order evidence, and required
  project checks after task waves;
- opt-in content-bound check reuse that binds a declared check's PASS to its
  contract, selected file content, and installed kit, carries only a really
  executed PASS from a stable run, revokes it on a later failure, runs a
  declared check once per verification run, records every carried result in
  the evidence and certificate, and keeps `verify --no-reuse` as the explicit
  full run;
- repository analysis and an adaptive Markdown graph rooted at canonical
  `AGENTS.md`, exact `CLAUDE.md` import, and `docs/INDEX.md`;
- an existing-first canonical architecture artifact, conventional root
  `ARCHITECTURE.md` fallback, structural maintenance triggers, readable spec
  impact, and conditional chain freezing without a second manifest or
  semantic-freshness state machine;
- paired frontend authority: broad UX decisions in
  `docs/ux/frontend-design.md`, normative visual tokens/components in the
  nearest mapped `DESIGN.md`, a pinned Google-derived alpha profile, and
  deterministic offline lint/diff/mapping checks without export or codegen;
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
- a Claude Code chain adapter that reads the permission mode from the first
  hook event that reports it, accepts `auto`, takes the bound reviewer's
  receipt from its hand-back call or its SubagentStop message, releases the
  binding for a new reviewer when a handed-back report is rejected and bounds
  that replacement, defers a Stop while a background subagent runs, decodes
  hook input as UTF-8 whatever the console encoding is, and reports installed
  hooks that predate the current matchers;
- a pending oracle audit that an earlier finished run can no longer end, so a
  rejected audit report keeps its reviewer instead of opening the audit to the
  next one;
- an exact frozen-file early guard shared by both hosts: file tools are judged
  by their target, shell and PowerShell commands by write intent toward a
  named frozen file, and the runtime's own commands always pass;
- an optional ordinary completion Stop hook that waits for a running
  background subagent on Claude Code, warns instead of blocking when the hook
  itself fails, keeps blocking a status the runtime reads as invalid, and
  answers with ASCII-only JSON;
- a review challenge lifecycle: a product gate ends with the run that began
  it, an oracle audit belongs to its preview hash and waits for the running
  feature, a new subject of the same kind replaces a pending challenge,
  `chain gate abandon` ends a challenge whose bound reviewer cannot report,
  and each such ending closes the audited preview or counts a review failure;
- a rejection notice: the runtime's one-line reason for a rejected receipt is
  repeated by the Stop reason, the run status, and the `chain gate begin`
  answer together with the next step;
- a session-only `deep-interview` that separates stated gaps from an always-run
  internal blind-spot pass, exposes only plausible consequential candidates,
  challenges framing when material, avoids ritual questions, and ends with a
  proceed, correct, or summary-only choice; ordinary-mode proceed resumes host
  work through relevant verification, while Plan Mode proceed continues
  planning only and never authorizes implementation;
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
- an explicit, plugin-only `teach` learning utility adapted from a pinned MIT
  upstream skill, which keeps one topic's mission, resources, lessons, and
  learning records in the directory the user invokes it in, warns before
  writing inside an EZPowers-managed project, is never installed into a
  project kit, and adds no workflow, verification, or completion authority;
- workflow guidance to exercise a change on the real running system before the
  certification candidate, treat a flaky check as a defect, choose checks that
  observe a real boundary, and use the host's own review, with the runtime
  verdict still the only completion evidence;
- an exact fifteen-skill plugin and thirteen-skill project catalog with distinct
  namespaced and project-local Codex prompt metadata;
- clean retirement of pre-v5 workflow input plus Claude 2.1.217 and Codex
  0.145.0 minimums before host-specific writes.

Documentation proposals are staged, previewed with a hash that binds the
bundle, registry, config, and current targets, then applied transactionally.
Unmanaged documents require explicit adoption; edited/adopted targets require
force and are backed up first. A ready graph registers `ezpowers.docs` as an
exact required project check and, when a managed frontend mapping exists,
registers the exact self-contained `ezpowers.design` check too.

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
- `F21`: maintainable paired `DESIGN.md` frontend contract.
- `F22`: portable architecture artifact lifecycle.
- `F23`: evidence-gated assurance graph and safe parallel verification.
- `F24`: planning-artifact project profile and artifact assurance.
- `F25`: plugin-only explicit `teach` learning skill.
- `F26`: opt-in content-bound check reuse.
- `F27`: current-host chain adapter alignment and verification guidance.
- `F28`: completion hook wait and failure rules.
- `F29`: review gate lifecycle and rejection notice.

## Deferred Item

- `F19`: exact-reproduction-gated `diagnose`. The skill, contract, metadata,
  deterministic receipts, and opt-in dual-host probe are implemented. Its
  semantic completion remains deferred until an authenticated Claude call and
  a Codex host can execute the authoritative isolated-fixture command
  (`python scripts/plugin_smoke.py --host both --live-diagnose`). Earlier
  attempts were blocked by a logged-out Claude CLI and by the Codex CLI
  rejecting file reads and execution under its policy. Claude model calls work
  on this machine now and were used for the F27 probes, but the F19 probe
  itself was not rerun. No later release result is presented as evidence for
  it.

Open notes carried forward:

- No part of the Codex harness chain has been run on a live host. The earlier
  deferral stands: its terminal Stop response emits `continue`/`stopReason`,
  and its readiness uses the mode names `dontAsk` and `bypassPermissions`. Its
  matchers and continuation behavior were not changed in v5.11. The changes
  that do not branch on the host apply to it too: the frozen-file guard
  classification, taking the mode from a later event when SessionStart
  reported none, UTF-8 hook input with ASCII answers, the code-review rubric
  wording, the comparison of installed matchers, a finished run no longer
  ending a pending oracle audit, and the v5.12.0 review gate lifecycle.
- The v5.11.0 chain adapter was exercised only through `claude -p`. Not run on
  a live host: an interactive session, a forked session, compaction during a
  run, the one-replacement cap of an oracle audit, the correction path after a
  finished run, a replacement started by the default model, `NotebookEdit`, an
  outdated-matcher project, and a classifier denial in `auto`. The full list
  is in the v5.11.0 changelog entry.
- `test_chain_hook_is_fail_safe_on_corrupt_state` failed once on 2026-10-17
  with exit 1 and empty output and was never reproduced or explained. It
  passed in every run of the v5.11.0, v5.11.1, and v5.12.0 releases.
- This repository's own `unit` project check has a 600-second timeout, shorter
  than the full suite's run time, so release evidence here is the gates run
  directly rather than an in-repository all-scope certificate.

The v5.12 project kit installs thirteen project skills, eleven canonical
contracts, and three deterministic tools. The plugin exposes fifteen skills:
the project skills plus the plugin-only global `hud` utility and the
plugin-only `teach` learning skill.

## Verification Evidence

v5.12.0 review gate lifecycle validation on 2026-11-19:

- Claude plugin and marketplace versions are `5.12.0`; Codex is
  `5.12.0+codex.20261119031503`. The project kit is `5.12.0` at
  `project-kit/v5.12.0/manifest.json`, moved from the v5.11.1 directory so one
  live manifest remains. Installed global plugins and project copies were not
  refreshed.
- Baseline on the v5.11.1 runtime with synthetic hook events and no host:
  after a rejected hand-back inside a run the Stop reason and the run status
  said only "Begin a fresh independent code-review gate." and the
  `chain gate begin` answer carried nothing about the rejection; a rejected
  oracle-audit receipt for a second feature ended another feature's `RUNNING`
  run as `FAILED` at a review limit of 1; before approval a gate bound to a
  reviewer that never reported refused `chain gate begin` for a changed
  preview and bound no second reviewer; inside a run the same sentence was
  repeated until the iteration limit ended the run.
- Second baseline on the same runtime: a run that ended `FAILED` at the
  iteration limit and a run stopped by the documented emergency stop each
  left a bound code-review gate behind, and the next feature's oracle audit
  was refused with "another independent review challenge is already
  pending". Result SHA-256 values under `%TEMP%/ezpowers-f29-notes/`:
  `rejection-baseline.json`
  `78a77edce86bd3d14ec1aaad977eb1e2651c73c77424cadbea7932b1402e0e49`,
  `dead-run-gate.json`
  `d41c2aded5d89528dbd6d019cd4ba64c7649aada5c3a56e670dd032d02a75b88`.
- The user decided three points: an oracle-audit rejection must not count
  against a run; the missing way to end a pending gate is fixed properly and
  not by a stopgap; and the lifecycle of ADR 0013 ships in this release as
  v5.12.0 with its visible changes, namely the `chain gate abandon` command,
  no oracle audit while a run is nonterminal, and a closed preview after an
  abandoned or replaced audit that had a reviewer.
- Design order: `docs/reference/architecture.md` and ADR 0013 were written
  first, then `docs/specs/f29-review-gate-lifecycle.md` and
  `docs/plans/f29-review-gate-lifecycle.md`. `validate --spec` and
  `validate --plan` pass with waves `[T1] [T2] [T3]` and assurance graph
  `c0b8f6cab94a7908da87f5fe065997a003c5132bfc74eb4ca3b7a4abbbc3687b`. The F28,
  F27, F26, F24, and F23 plans still validate with the graphs they have at
  commit `929f8fe`.
- Tests were written before each runtime change. Of four rejection-notice
  tests three were red on the unchanged runtime: the Stop reason was the old
  sentence, the gate answer had no `previous_receipt`, and the function that
  bounds the reason did not exist. The fourth pinned behavior that already
  held. Twelve lifecycle tests, one of them that pin rewritten for the new
  rules, were all red on the runtime before the lifecycle change, with twelve
  failures and one error counting subtests. All fifteen pass afterwards.
  `python -m unittest tests.test_harness_chain tests.test_planning_profile`
  passed 50 tests in 514.140 seconds after the notice change and 61 tests in
  681.761 seconds after the lifecycle change, before the version move.
- Upgrade path: a project built with the committed v5.11.1 tree was left in
  the stuck state, a `FAILED` run with a bound code-review gate and a refused
  oracle audit. After `install --refresh` with the 5.12.0 runtime (103
  managed files) its `.claude/settings.json` was byte-identical,
  `chain config status` was `READY` as before, the preview hash had changed
  with the installation identity, and the oracle audit began. Result
  `upgrade-path.json`
  `cc5258f453fef7c32e06f8995a722baebbed991d0efff98d4083ab38cc1aea01`.
- Real host: Claude Code 2.1.327, `claude -p` in `auto` with the `sonnet`
  alias (`claude-sonnet-5-5`), a throwaway project with an approved `RUNNING`
  run whose chain hooks were routed through a recorder, driven only by the
  Stop hook without the harness-chain skill loaded. Three sessions, each
  ended `CERTIFIED` after 4 iterations:
  - Rejected receipt: the recorder let the first reviewer's hand-back reach
    the runtime without a usable marker. The next Stop reason was "The last
    code-review receipt was rejected: the reviewer's hand-back carried no
    gate marker. Spawn one new independent reviewer for the pending
    code-review challenge." The main agent repeated that reason in its own
    text, read the gate section of the state file once, and started exactly
    one new reviewer for the same challenge without another
    `chain gate begin`; that reviewer's hand-back created the PASS receipt.
    One review failure was counted. Because that session did not ask again,
    the `chain gate begin` answer after a rejected receipt was seen only in
    tests.
  - Lost reviewer: the recorder kept the first reviewer's hand-back and
    SubagentStop from the runtime. The next Stop reason was "The pending
    code-review challenge is bound to a reviewer whose receipt has not
    arrived. If that reviewer is still running, wait for it. If it has
    ended, run chain gate abandon and spawn one new independent reviewer."
    The main agent ran `chain gate abandon`, which answered `RELEASED` with
    one review failure, and `chain gate begin`, whose answer carried
    `previous_receipt` and `next_step`, and started a second reviewer, whose
    hand-back created the PASS receipt. The state file was not read in
    between.
  - Background reviewer, nothing altered: no `chain gate abandon` call,
    every Stop while a subagent ran was answered `{}`, and no review failure
    was counted. After "Begin a fresh independent code-review gate." the
    main agent first started a reviewer without `chain gate begin`; that
    reviewer was not bound and its report was not used.
  Trace SHA-256 values under `%TEMP%/ezpowers-f29-notes/`:
  `rejected-trace.jsonl`
  `0c0a411753a2465b98f753b5e3ec1dcd101bb4d9c1bbccdeeb58fa88f98790fe`,
  `lost-trace.jsonl`
  `979ae75761dbc4675f322ef5512164c9055ddf70e1cb4f759f2c3093485b05ed`,
  `background-trace.jsonl`
  `ebf700caeffa15a7a6fe09d2d2e7fa6dc0f2d2fd6afa8a4f19ae18fce4b43298`.
- `python -m unittest discover -s tests` in UTF-8 mode on Python 3.14.3 passed
  265 tests in 1143.654 seconds with one POSIX-only skip, on the final
  runtime, contract, and skill.
- `scripts/check-repo.ps1`: PASS. `scripts/harness-runtime-smoke.ps1`: PASS
  for a real v5.12 install, trace, verify, certify, stale, and reuse flow.
  `scripts/verify-harness-kit.py`: v5.12 manifest valid.
  `scripts/plugin_smoke.py --host both`: file surfaces matched, Claude 2.1.327
  accepted both manifests, and Codex 0.169.1 loaded every project and
  namespaced skill in isolation.
- Scheduler measurements passed: fixture median 1.194420 seconds serial versus
  0.310424 parallel (74.01 percent improvement); project median 1.214233
  versus 0.791145 (34.84 percent improvement); equivalent outcomes in both.
- `python scripts/benchmark_check_reuse.py --runs 3 --minimum-improvement 50`:
  PASS with a median of 2.891716 seconds against 8.148852 for a forced full
  run, a 64.51 percent improvement, equal outcomes, and one process start for
  a thrice-referenced declared check.
- Five interleaved software compatibility runs against
  `08f9f84d24c59ec130dd6b3bf26555503910cbab` produced equivalent output.
  Baseline median was 4.242847 seconds and candidate median 4.227545 seconds,
  a -0.36 percent regression against the 5 percent limit.
- `DESIGN.md` lint, the project design check, and the visual-readiness check
  passed for the version-only guide edit. The guide was not rendered or
  inspected at the three documented viewports.
- Not exercised: any part of the chain, including this lifecycle, on a live
  Codex host; an interactive Claude Code session (every live run used
  `claude -p`); the default model (the live runs used the `sonnet` alias); a
  session with the harness-chain skill loaded; on a live host, abandoning or
  replacing an oracle audit, the refusal of an audit while a run is
  nonterminal, the dropped gate of a finished run, a run that reaches its
  review limit through abandonment, a stored hand-back judged by
  `chain gate abandon`, and a rejected receipt outside `auto`, all of which
  are covered only by tests with synthetic hook events; a receipt lost to
  runtime lock contention, which is unchanged; any installed project (none
  was refreshed); the POSIX execute-bit test, skipped on Windows;
  in-repository `verify --all`; F19 remains deferred.

Earlier per-release verification evidence was pruned from this file. It
remains in `harness_versions/changelog.jsonl` (one entry per release from
v5.2.0 through v5.11.1) and in this file's Git history: the v5.11.1 record is
complete at commit `929f8fe`, the v5.11.0 record at commit `ddd53a2`, and the
records up to v5.10.0 at commit `e5a4151`. The v5.3.3 and v5.3.4 candidate
records have no changelog entry and exist only in the Git history at
`e5a4151`.

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

### Considered and declined

- Stopping ordinary `execute` after three failed rounds to call a human. The
  user declined it; ADR 0011 records the reasons.
- An observe mode for the completion hook that reports instead of blocking,
  and blocking when the hook itself fails. The user declined both for now; ADR
  0012 records the reasons.
- Letting only a new preview hash replace a pending oracle audit. The user
  declined it as a stopgap; ADR 0013 records the lifecycle chosen instead.

### Candidates not acted on

These were found while comparing the harness with current hosts and with the
Claude Code team's verification practice. They were reported, not changed.

- No installer option removes an installed completion hook again; it has to be
  deleted from the host settings by hand.
- The completion hook's block reason describes the state ("fresh but not
  certified") and does not name the next command.
- Background `workflow` and `teammate` tasks do not defer a Stop in either
  hook. No live payload for them was recorded, so no rule was written.
- Certification becomes stale when the certified tree is committed, because
  the workspace fingerprint includes Git HEAD; commits carry no record of how
  they were verified.
- In ordinary execution nothing reports that a change edited its own checks.
- The Codex chain path is unused by the maintainer and unverified.
- The local wiki overlaps the hosts' own memory features.
- Chain hooks give up on the runtime lock after one second, and `verify`
  holds that lock for its whole run. A receipt that arrives meanwhile is
  dropped by the hook's fail-safe; the gate then stays bound until it is
  abandoned, and the frozen-file early guard does not run either.
- Inside a run the next action "Begin a fresh independent code-review gate."
  does not name `chain gate begin`. The three live sessions, which did not
  load the skill, looked the command up with `--help`, and one of them
  started a reviewer before any challenge existed.
- A report from an abandoned or replaced reviewer is ignored, also when it
  arrives before a new reviewer is bound.
- The runtime does not detect a lost reviewer by itself; the main agent has
  to run `chain gate abandon`.
- Outside `auto`, the same reviewer may correct a rejected oracle-audit
  receipt any number of times before approval; only replacement by another
  reviewer is bounded.
- The article's "delete a flaky test and record why" conflicts with the rule
  that a required check is never omitted.
- The same rule is restated across many documents, so each release touches a
  large version-coupled file set.
