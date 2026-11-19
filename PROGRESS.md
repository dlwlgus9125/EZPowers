# EZPowers Progress

## Current State

EZPowers v5.12.1 plugin and v5.12.1 project kit are present in the working tree
on `main`. F30 is complete. F19 remains explicitly deferred because its
semantic dual-host diagnosis probe still needs external access; it is not part
of the v5.12 completion claim.

F30 keeps the chain hooks working while a verification runs its checks. On the
v5.12.0 runtime `verify` held the one runtime lock for its whole run and a
hook waited a second for it, so a reviewer's report that arrived meanwhile was
dropped, the gate stayed bound, and freeing it cost a review failure; a
reviewer started meanwhile was not bound, and frozen files were not guarded.
The runtime now has a command lock, held by a command for its whole run, and
a state lock that `verify` gives up while its checks run and that hooks take
alone. A reviewer's stop that arrives during a verification is recorded and
judged when the verification has ended, so no verdict is taken while a check
runs. The decisions are recorded in
`docs/decisions/0014-hooks-during-verification.md`.

F29 (v5.12.0) gave a pending review challenge of the harness chain an owner
and an end, added `chain gate abandon`, and repeats a rejection with its
reason to the main agent. Its decisions are recorded in
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
- two runtime locks: a command lock that keeps commands from running together
  and a state lock that `verify` holds only around its reads and writes of
  state, so chain hooks still bind a reviewer, keep its report, and guard
  frozen files while checks run, and a reviewer's stop that arrives meanwhile
  is recorded and judged when the verification has ended;
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
- `F30`: hooks during verification.

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
  ending a pending oracle audit, the v5.12.0 review gate lifecycle, and the
  v5.12.1 runtime locks with the review report judged after a verification.
- The v5.11.0 chain adapter was exercised only through `claude -p`. Not run on
  a live host: an interactive session, a forked session, compaction during a
  run, the one-replacement cap of an oracle audit, the correction path after a
  finished run, a replacement started by the default model, `NotebookEdit`, an
  outdated-matcher project, and a classifier denial in `auto`. The full list
  is in the v5.11.0 changelog entry.
- `test_chain_hook_is_fail_safe_on_corrupt_state` failed once on 2026-10-17
  with exit 1 and empty output and was never reproduced or explained. It
  passed in every run of the v5.11.0, v5.11.1, v5.12.0, and v5.12.1
  releases.
- This repository's own `unit` project check has a 600-second timeout, shorter
  than the full suite's run time, so release evidence here is the gates run
  directly rather than an in-repository all-scope certificate.

The v5.12 project kit installs thirteen project skills, eleven canonical
contracts, and three deterministic tools. The plugin exposes fifteen skills:
the project skills plus the plugin-only global `hud` utility and the
plugin-only `teach` learning skill.

## Verification Evidence

v5.12.1 hooks-during-verification validation on 2026-11-19:

- Claude plugin and marketplace versions are `5.12.1`; Codex is
  `5.12.1+codex.20261119073327`. The project kit is `5.12.1` at
  `project-kit/v5.12.1/manifest.json`, moved from the v5.12.0 directory so one
  live manifest remains. Installed global plugins and project copies were not
  refreshed.
- Baseline on the v5.12.0 runtime with a real `verify --task` whose check took
  twelve seconds and synthetic hook events: `chain run status` answered busy,
  and the bound reviewer's hand-back with a valid `PASS` marker, its
  SubagentStop, a write to the frozen oracle, and a Stop were each answered
  `{}` after about 1.3 seconds with "EZPowers chain hook fail-safe no-op:
  runtime is busy" on stderr. After the verification the gate was still bound
  with no report stored and no receipt, although its subject was still the
  latest all-scope evidence, and `chain gate abandon` released it with one
  review failure. A reviewer started during the verification was not bound.
  The same events without a verification bound the reviewer, denied the
  write, blocked the Stop, and created the receipt. Result SHA-256 under
  `%TEMP%/ezpowers-f30-notes/`: `lock-contention.json`
  `42cc3c257012e08f48e1c9cc3d6eab252fd8db93ba085b55678a9e5237782d7f`.
- Baseline on the real host: Claude Code 2.1.327, `claude -p` in `auto` with
  the `sonnet` alias (`claude-sonnet-5-5`), a throwaway project at the review
  stage whose chain hooks were routed through a recorder, and a prompt that
  told the session to begin the gate, start one background reviewer, and then
  run a foreground `verify --task` that a delay outside the project kept busy
  for 75 seconds. The host delivered the reviewer's hooks while the main
  agent's shell call ran. The reviewer's own shell call, its hand-back, and
  its SubagentStop each ended as the fail-safe no-op after about 1.3 seconds.
  After the verification the Stop said the challenge was bound to a reviewer
  whose receipt had not arrived; the session ran `chain gate abandon`, started
  a second reviewer, and certified after 2 iterations with one review failure.
  Trace `before-trace.jsonl`
  `3e362d007b64bc98ca2085b795c0a9deca85fe04725969f9ca9cc56a35d661a3`.
- Facts behind the options: the installed chain hook entry has a 30 second
  timeout, and the Claude documentation says a timed-out command hook renders
  no decision. On this Windows machine `os.replace` over a file fails with
  `PermissionError` while another handle has it open, so a hook must not read
  the state file without the lock.
- The user chose the lock split over waiting longer for the lock, writing the
  report to a side file, and guidance only, with its stated costs: a change to
  the verification path and the lock contract, a second lock file in every
  project, and a POSIX lock path that was not run. This machine has no
  POSIX environment: `wsl -l -q` reports that the Windows Subsystem for
  Linux is not installed.
- Design order: `docs/reference/architecture.md` and ADR 0014 were written
  first, then `docs/specs/f30-hooks-during-verification.md` and
  `docs/plans/f30-hooks-during-verification.md`. `validate --spec` and
  `validate --plan` pass with waves `[T1] [T2] [T3]` and assurance graph
  `862734e2e740c5e376b83b69201591e5fbae79863b7e1f320947585e702ade84`. The F29,
  F28, F27, F26, F24, and F23 plans still validate with the graphs they have
  at commit `a4c6c0e`.
- Tests were written before the runtime change. Eleven chain tests ran on the
  unchanged runtime: ten were red for the expected reasons (the report was
  not stored, the reviewer was not bound, the stored report was never judged,
  the lock file did not exist, the baseline copy failed on the held lock
  file), and one pinned what must not change, the Stop answer and the busy
  result of a second command during a verification. A twelfth test for the
  Codex path was red on the exported v5.12.0 tree. All twelve pass on the
  changed runtime. `python -m unittest tests.test_harness_chain
  tests.test_planning_profile tests.test_ezpowers_runtime` passed 111 tests in
  1063.739 seconds before the version move and the Codex test.
- Upgrade path: a project built with the committed v5.12.0 tree at the review
  stage dropped a report sent while the command lock was held. After
  `install --refresh` with the 5.12.1 runtime (103 managed files) its
  `.claude/settings.json` was byte-identical, `chain config status` was
  `READY` as before, the same report was stored under the held command lock
  and judged by the next Stop without a review failure, `verify --all`
  passed, and the run was still `RUNNING`. Result `upgrade-path.json`
  `61ffe17fa5167b7b892f0a209f1ff5c996e8a46060ddc391c7d916d7688fcef7`.
- Same real-host session on the 5.12.1 kit: the reviewer's shell call and its
  hand-back were answered in about 0.4 seconds with nothing on stderr, its
  SubagentStop arrived 10 seconds into the 75 second verification and was
  answered `{}` after the one second wait for the command lock, and the
  receipt was created when the verification ended. The next Stop said "Run
  certify for the fresh evidence and gate receipts.", and the run certified
  after 1 iteration with no review failure and no `chain gate abandon`. Trace
  `after-trace.jsonl`
  `66ea8dd311ae33439815dcd313f64b0e0cc6129f54f6c5f6d265a39b9d25aace`.
- `python -m unittest discover -s tests` in UTF-8 mode on Python 3.14.3 passed
  278 tests in 1351.418 seconds with one POSIX-only
  skip, on the final runtime, contracts, and skill.
- `scripts/check-repo.ps1`: PASS. `scripts/harness-runtime-smoke.ps1`: PASS
  for a real v5.12 install, trace, verify, certify, stale, and reuse flow.
  `scripts/verify-harness-kit.py`: v5.12 manifest valid.
  `scripts/plugin_smoke.py --host both`: file surfaces matched, Claude 2.1.327
  accepted both manifests, and Codex 0.169.1 loaded every project and
  namespaced skill in isolation.
- Scheduler measurements passed: fixture median 1.208169 seconds
  serial versus 0.315219 parallel (73.91 percent
  improvement); project median 1.337247 versus 0.826581
  (38.19 percent improvement); equivalent outcomes in both.
- `python scripts/benchmark_check_reuse.py --runs 3 --minimum-improvement 50`:
  PASS with a median of 3.135828 seconds against 8.992617 for a
  forced full run, a 65.13 percent improvement, equal outcomes, and
  one process start for a thrice-referenced declared check. That run directly
  followed the full suite. A back-to-back rerun measured 2.909671 against
  8.222236 seconds on this tree and 3.011965 against 8.263874 on the v5.12.0
  tree.
- Five interleaved software compatibility runs against
  `08f9f84d24c59ec130dd6b3bf26555503910cbab` produced equivalent output.
  Baseline median was 4.358565 seconds and candidate median
  4.353407 seconds, a -0.12 percent regression
  against the 5 percent limit.
- `DESIGN.md` lint, the project design check, and the visual-readiness check
  passed for the version-only guide edit. The guide was not rendered or
  inspected at the three documented viewports.
- Not exercised: anything on a live Codex host, including whether Codex
  delivers a subagent's hooks while the main agent's command runs; the POSIX
  lock path; an interactive Claude Code session (both live runs used
  `claude -p`); the default model (they used the `sonnet` alias); a session
  that verifies during its review without being told to; on a live host, an
  all-scope verification during a review, a rejected recorded report, a
  reviewer started during a verification, and a verification that never
  finishes, which are covered only by tests; a hook that meets a command
  other than `verify` holding the state lock for more than a second; any
  installed project (none was refreshed); the POSIX execute-bit test, skipped
  on Windows; in-repository `verify --all`; F19 remains deferred.

Earlier per-release verification evidence was pruned from this file. It
remains in `harness_versions/changelog.jsonl` (one entry per release from
v5.2.0 through v5.12.0) and in this file's Git history: the v5.12.0 record is
complete at commit `a4c6c0e`, the v5.11.1 record at commit `929f8fe`, the
v5.11.0 record at commit `ddd53a2`, and the records up to v5.10.0 at commit
`e5a4151`. The v5.3.3 and v5.3.4 candidate records have no changelog entry
and exist only in the Git history at `e5a4151`.

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
- For a report that arrives during a verification: waiting longer for the
  lock, writing the report to a side file, and guidance only. The user chose
  the lock split; ADR 0014 records the reasons.

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
- A chain hook that arrives while a command other than `verify` holds the
  state lock for more than a second is still a no-op. `chain run apply`
  holds it while it reruns the baseline.
- `chain run preview` takes no lock and judges nothing. Before approval an
  audit report that was only recorded during a command still shows
  `REVIEW_REQUIRED` there until a Stop, `chain gate begin`, or
  `chain run apply` judges it.
- On Windows a state write fails when a reader that takes no lock, such as
  `status` or the completion hook, has the state file open at that instant.
  The write is not retried.
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
