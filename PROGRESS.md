# EZPowers Progress

## Current State

EZPowers v5.11.0 plugin and v5.11.0 project kit are present in the working tree
on `main`. F27 is complete. F19 remains explicitly deferred because its
semantic dual-host diagnosis probe still needs external access; it is not part
of the v5.11 completion claim.

F27 aligns the harness chain's Claude Code host adapter with the hook payloads
Claude Code 2.1.327 really sends, and adds the Claude Code team's verification
practice to the workflow skills. A live probe showed that the chain could not
reach `READY` on a real session: SessionStart carries no permission mode, the
default `auto` mode was not accepted, a reviewer's report arrives through a
hand-back tool call in `auto`, waiting for a background reviewer spent
continuation budget, and the frozen-file guard denied the runtime's own
`verify` command. The decisions are recorded in
`docs/decisions/0011-current-host-chain-adapter.md`.

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
  wording, the comparison of installed matchers, and a finished run no longer
  ending a pending oracle audit.
- `test_chain_hook_is_fail_safe_on_corrupt_state` failed once on 2026-10-17
  with exit 1 and empty output and was never reproduced or explained. It
  passed in every run of this release.
- This repository's own `unit` project check has a 600-second timeout, shorter
  than the full suite's run time, so release evidence here is the gates run
  directly rather than an in-repository all-scope certificate.

The v5.11 project kit installs thirteen project skills, eleven canonical
contracts, and three deterministic tools. The plugin exposes fifteen skills:
the project skills plus the plugin-only global `hud` utility and the
plugin-only `teach` learning skill.

## Verification Evidence

v5.11.0 current-host flow alignment validation on 2026-11-18 and 2026-11-19:

- Claude plugin and marketplace versions are `5.11.0`; Codex is
  `5.11.0+codex.20261118121755`. The project kit is `5.11.0` at
  `project-kit/v5.11.0/manifest.json`, moved from the v5.10.0 directory so one
  live manifest remains. The v5.7.0 and v5.8.0 kit manifests, which no runtime
  or gate read, were removed; they are last present at commit `e5a4151`.
  Installed global plugins and project copies were not refreshed.
- Live probe before any repository edit: two `claude -p` runs of Claude Code
  2.1.327 in a throwaway folder whose project hooks logged raw hook input, one
  in `auto` and one in `dontAsk`. Each started one background subagent that
  returned a gate-marker report. Observed: SessionStart input has no
  `permission_mode` in either mode while PreToolUse, Stop, and SubagentStop
  carry it; in `auto` the report arrives as `tool_input.message` of a
  PreToolUse event for `SubagentHandback` carrying the subagent's `agent_id`,
  and SubagentStop has no `last_assistant_message`; in `dontAsk` there is no
  hand-back and `last_assistant_message` carries the report; the Stop that
  fires while the subagent runs lists it in `background_tasks` with type
  `subagent`, status `running`, and an `id` equal to its `agent_id`. The hook
  logs are retained under `%TEMP%/ezpowers-f27-notes/`; their SHA-256 values
  are `1d0dc24561717fb94b80fbce0e65967e00706f820c7910ae43c558288e5a2b8f`
  (`auto`) and
  `9c1fae4e51ea21ec1cfa528dbd5a481ef5bd4b6df35f32568cfc6b47b24507c6`
  (`dontAsk`).
- The approved plan said to drop the `auto` and hand-back changes if
  SessionStart did not report `auto`. The probe showed that premise was wrong
  for every mode, and the user chose to fix where the mode is read instead.
- Design order: `docs/reference/architecture.md` and ADR 0011 were written
  first, then `docs/specs/f27-host-flow-alignment.md` and
  `docs/plans/f27-host-flow-alignment.md`. `validate --spec` and
  `validate --plan` pass with waves `[T1] [T2] [T3]` and assurance graph
  `50ccbaafc6bb40641f99c587d3f3d80eee4fde3ff42aa21ceb0e720b8722d984`, which
  includes the tenth criterion added by the final review; before that
  criterion the graph was `00c3b329...d149`. The F26 plan still validates with
  graph `058a7049...c275` and the F24 plan with `70ad1b16...835d`.
- Baseline before any edit: `python -m unittest tests.test_harness_chain` in
  UTF-8 mode on Python 3.14.3 passed 26 tests in 248.287 seconds.
- Eight new chain tests were added first and failed on the unmodified runtime
  with 40 failures including subtests: the guard denied the runtime's own
  `verify`, `certify`, `trace`, and `validate` commands, a test run, and
  mention-only content, and allowed PowerShell, NotebookEdit, redirection, and
  inline-interpreter writes; `auto` was not accepted; a running chain became
  `NEEDS_REAPPROVAL` after a SessionStart without a mode; a hand-back created
  no receipt; a Stop with a running background subagent blocked and counted;
  the matchers lacked `fork`; and the rubric lacked the blocking/observation
  split. All eight pass after the runtime change.
- After the runtime change, `tests.test_harness_chain` and
  `tests.test_planning_profile` passed 41 tests in 398.853 seconds, and after
  the bounded-replacement change 46 tests in 477.665 seconds.
- First full chain run on the real host (a throwaway project built with the
  suite's own helpers, an approved `RUNNING` run, `claude -p` in `auto` with
  the project-local skill): the session reported `auto`, the guard allowed
  `verify --plan`, and the reviewer bound and handed back a valid PASS marker,
  but the run ended `FAILED` at the total iteration limit. Three causes were
  reproduced and fixed. The hook decoded UTF-8 input with the cp949 locale,
  so one ellipsis in the report made it exit with an error before storing the
  hand-back; replaying the logged event without UTF-8 mode gave exit 1 and no
  stored report. A probe showed that a blocked SubagentStop is not honored
  after a hand-back, so a rejected report now releases the binding for a new
  reviewer. The reviewer's copy of the frozen oracle to a temporary folder was
  denied, so a copy is now denied only onto a frozen file. Further probes
  showed that the host waits for a slow PreToolUse hook on `SubagentHandback`
  before SubagentStop, that an alternation matcher receives the hand-back, and
  that a subagent's shell call can arrive as `PowerShell`.
- Second real-host run on a fresh project from the fixed kit: `CERTIFIED`.
  The guard allowed `verify`, the code-review gate bound one subagent, its
  hand-back (4,242 characters, one marker) created a PASS receipt, `certify`
  passed, and the final Stop was allowed. Every counter stayed at zero.
- Third real-host run, driven only by the Stop hook with every chain hook
  answer traced: the Stop that fired while a background subagent was running
  was answered with `{}` and not counted; later Stops blocked with "Implement
  the approved plan, then run verify --all.", "Begin a fresh independent
  code-review gate.", and "Run certify for the fresh evidence and gate
  receipts."; the run ended `CERTIFIED` with `iterations` 3 and no review
  failure. Log SHA-256 values under `%TEMP%/ezpowers-f27-notes/`:
  first run `c87d78680ca981316aff39f3a97a52660c3bbad4e434388bc5e06a5de521df5b`,
  second `8e6086e43a3dd2da60c10d6e7d56fff6e98fc45608b969db38ccf92d6b46e47b`,
  third (trace) `af80eb770879d3304f8e28840a1dbeb3f13f9d8886d879f6c5d3dcd90e635e1b`.
- Final review on 2026-11-19: releasing the binding after a rejected hand-back
  went beyond the approved plan and had no bound before a run. A comparison
  run of the committed v5.10.0 runtime (a `git archive` of `e5a4151`) showed
  an older defect of the same kind in every permission mode. With a finished
  run left in state, each rejected oracle-audit receipt cleared the pending
  gate, and four reviewers in a row each received a fresh challenge; with no
  run in state the same reviewer was blocked and no other could bind. The
  user chose to bound the replacement: one replacement per oracle-audit
  challenge with the preview closed on the second rejected hand-back, the
  approved review limit inside a run, and a finished run no longer ending a
  pending oracle audit. Four tests were added first. The two audit tests
  failed on the previous runtime for exactly those reasons, the two run-path
  tests already passed, and all four pass after the change. Probe outputs
  under `%TEMP%/ezpowers-f27-notes/`: `stale-run-head.json`
  `088c002ab62b639b18a7399f9d241ec6227d91e650e5debc20bc5d582c88fb71` and
  `stale-run-worktree.json`
  `65fcbb86d3a91a68748bf7e96efa98103a8a928ae069c1c92cd21aadc128a236`.
- Fourth and fifth real-host runs exercised the replacement inside a run. A
  hook wrapper hid the gate marker of the first reviewer's hand-back from the
  runtime only, so the host still delivered the reviewer's real report while
  the runtime rejected it as it rejects a malformed receipt. In the fourth run
  (default model) the runtime counted one review failure and released the
  binding, but the main agent declined to start a second reviewer, naming the
  2-dollar budget cap of the probe and the wrapper's file name, which said
  what it did; it stopped until the iteration limit ended the run `FAILED`.
  That run says nothing about the replacement. The fifth run used a neutrally
  named wrapper and the `sonnet` model alias (`claude-sonnet-5-5`): the first
  reviewer's hand-back was rejected and counted, the Stop hook answered "Begin
  a fresh independent code-review gate.", the main agent reran
  `chain gate begin`, a second real subagent bound to the same challenge, its
  hand-back created the PASS receipt, and the run ended `CERTIFIED` with
  `iterations` 4 and `review_failures` 1. Trace SHA-256 values: fourth
  `deedbde20d26793904c008bfc620ab20539cf783815869d149dc31fd523c5ad5`, fifth
  `0523e00fabccd85815133a9430d9945510b1af833da107ae1478f3b034b25e04`.
- `python -m unittest discover -s tests` in UTF-8 mode on Python 3.14.3 passed
  242 tests in 904.594 seconds with one POSIX-only skip, on the final runtime.
  Earlier runs passed 237 tests in 829.359 seconds before the three live-run
  fixes and 238 tests in 828.775 seconds before the bounded-replacement
  change.
- New coverage is thirteen tests in `tests/test_harness_chain.py` and one phrase
  test in `tests/test_v5_workflow_surface.py`. The chain tests use payload
  shapes recorded from the live host. The encoding test runs the hook with
  `PYTHONUTF8=0` and a cp949 stream encoding, because the suite itself runs in
  UTF-8 mode and would otherwise hide the defect again.
- `scripts/check-repo.ps1`: PASS. `scripts/harness-runtime-smoke.ps1`: PASS
  for a real v5.11 install, trace, verify, certify, stale, and reuse flow.
  `scripts/verify-harness-kit.py`: v5.11 manifest valid.
  `scripts/plugin_smoke.py --host both`: file surfaces matched, Claude 2.1.327
  accepted both manifests, and Codex 0.169.1 loaded every project and
  namespaced skill in isolation.
- Scheduler measurements passed on the final runtime: fixture median 1.195403
  seconds serial versus 0.311174 parallel (73.97 percent improvement); project
  median 1.171361 versus 0.767044 (34.52 percent improvement); equivalent
  outcomes in both.
- `python scripts/benchmark_check_reuse.py --runs 3 --minimum-improvement 50`:
  PASS with a median of 2.882039 seconds against 8.144923 for a forced full
  run, a 64.62 percent improvement, equal outcomes, and one process start for
  a thrice-referenced declared check.
- Five interleaved software compatibility runs against
  `08f9f84d24c59ec130dd6b3bf26555503910cbab` produced equivalent output.
  Baseline median was 4.216813 seconds and candidate median 4.210924 seconds,
  a -0.14 percent regression against the 5 percent limit.
- `DESIGN.md` lint, the project design check, and the visual-readiness check
  passed for the content-only guide edit. The guide was not rendered or
  inspected at the three documented viewports.
- Not exercised: any live Codex chain step, and the shared guard on a live
  Codex host; an interactive Claude Code session (every live run used
  `claude -p`), a forked session, and compaction during a run; the
  one-replacement cap of an oracle audit and the correction path after a
  finished run, `NotebookEdit`, and an outdated-matcher project on a live host
  (tests only); a replacement started by the default model, which declined in
  the fourth run for reasons of the probe itself; a first reviewer that the
  main agent continues with a message after its hand-back, which the host
  offers and whose binding is unknown; a classifier denial or
  pause in `auto` and the eight-continuation cutoff inside a chain; the new
  `execute` and `prepare-execute` wording through a live model; any installed
  project (none was refreshed); the POSIX execute-bit test, skipped on Windows;
  in-repository `verify --all`; F19 remains deferred.

Earlier per-release verification evidence was pruned from this file. It
remains in `harness_versions/changelog.jsonl` (one entry per release from
v5.2.0 through v5.10.0) and in this file's Git history, last complete at
commit `e5a4151`. The v5.3.3 and v5.3.4 candidate records have no changelog
entry and exist only in that Git history.

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

### Candidates not acted on in v5.11

These were found while comparing the harness with current hosts and with the
Claude Code team's verification practice. They were reported, not changed.

- The ordinary completion Stop hook still blocks while a background subagent
  runs, has no fail-safe wrapper, and has no observe mode or escape hatch.
- Certification becomes stale when the certified tree is committed, because
  the workspace fingerprint includes Git HEAD; commits carry no record of how
  they were verified.
- In ordinary execution nothing reports that a change edited its own checks.
- The Codex chain path is unused by the maintainer and unverified.
- The local wiki overlaps the hosts' own memory features.
- Chain hooks give up on the runtime lock after one second, and no command
  abandons a pending review gate.
- A rejected oracle-audit receipt that arrives while another feature's run is
  `RUNNING` is counted against that run's review limit.
- Nothing tells the main agent that a receipt was rejected or why. In the
  fifth live run it inferred the rejection from `review_failures` in the state
  file; the Stop reason and the `chain gate begin` answer do not say it.
- Outside `auto`, the same reviewer may correct a rejected oracle-audit
  receipt any number of times before approval; only replacement by another
  reviewer is bounded.
- The article's "delete a flaky test and record why" conflicts with the rule
  that a required check is never omitted.
- The same rule is restated across many documents, so each release touches a
  large version-coupled file set.
