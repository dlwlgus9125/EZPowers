# EZPowers Progress

## Current State

EZPowers v5.11.1 plugin and v5.11.1 project kit are present in the working tree
on `main`. F28 is complete. F19 remains explicitly deferred because its
semantic dual-host diagnosis probe still needs external access; it is not part
of the v5.11 completion claim.

F28 gives the optional ordinary completion Stop hook the wait rule the chain
hook received in v5.11.0, a rule for its own failure, and an answer that
survives any console encoding. A live session on Claude Code 2.1.327 showed
the hook blocking nine Stops in a row while a background reviewer ran, until
the host overrode it. On Claude Code a Stop that reports a running background
subagent is now a wait and is not blocked, a failure of the hook itself warns
the user instead of blocking, and the answer is ASCII-only JSON. The decisions
are recorded in `docs/decisions/0012-completion-hook-wait-and-failure.md`.

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
- The v5.11.0 chain adapter was exercised only through `claude -p`. Not run on
  a live host: an interactive session, a forked session, compaction during a
  run, the one-replacement cap of an oracle audit, the correction path after a
  finished run, a replacement started by the default model, `NotebookEdit`, an
  outdated-matcher project, and a classifier denial in `auto`. The full list
  is in the v5.11.0 changelog entry.
- `test_chain_hook_is_fail_safe_on_corrupt_state` failed once on 2026-10-17
  with exit 1 and empty output and was never reproduced or explained. It
  passed in every run of the v5.11.0 and v5.11.1 releases.
- This repository's own `unit` project check has a 600-second timeout, shorter
  than the full suite's run time, so release evidence here is the gates run
  directly rather than an in-repository all-scope certificate.

The v5.11 project kit installs thirteen project skills, eleven canonical
contracts, and three deterministic tools. The plugin exposes fifteen skills:
the project skills plus the plugin-only global `hud` utility and the
plugin-only `teach` learning skill.

## Verification Evidence

v5.11.1 completion hook validation on 2026-11-19:

- Claude plugin and marketplace versions are `5.11.1`; Codex is
  `5.11.1+codex.20261119013121`. The project kit is `5.11.1` at
  `project-kit/v5.11.1/manifest.json`, moved from the v5.11.0 directory so one
  live manifest remains. Installed global plugins and project copies were not
  refreshed.
- Baseline on the v5.11.0 runtime, without a host: the hook blocked a Stop
  that listed a running background subagent on both hosts; unreadable state, a
  deleted plan, and a missing Git executable blocked with their error as the
  reason; under a cp949 console a project folder with a Korean name gave an
  answer that is not valid UTF-8 with a garbled reason, and a folder name with
  a character cp949 cannot encode made the hook exit 1 with empty output.
- Baseline on the real host: Claude Code 2.1.327, `claude -p` in `auto` with
  the `sonnet` alias (`claude-sonnet-5-5`), a throwaway project in status
  `READY` whose Stop hook was routed through a recorder. The session started
  one background reviewer, ended its turn to wait, and certified after the
  report. The hook blocked nine Stops in a row while the reviewer ran, each
  answered by a turn that only repeated that the session was waiting, and the
  host then ended the turn with "A hook blocked the turn from ending 9
  consecutive times". The Stop after the report was judged afresh. An earlier
  run of the same kind, whose fixture was left `STALE` by a mistake in the
  fixture script, showed the same nine blocks while the subagent ran. Trace
  SHA-256 values under `%TEMP%/ezpowers-f28-notes/`: `before-trace.jsonl`
  `64285cf8d43b56c05f5264acb2c13f2a984ac92ec699f83cb5d05e676c1eaa07`,
  `before-stale-trace.jsonl`
  `c2913109c646063c10dc77677a54ce0b74e1c94c2a0745fc8f987490389df2b5`.
- The user decided three points before any repository edit: do not block
  while a subagent runs, warn and pass when the hook itself fails, and add no
  observe mode.
- Design order: `docs/reference/architecture.md` and ADR 0012 were written
  first, then `docs/specs/f28-completion-hook-wait.md` and
  `docs/plans/f28-completion-hook-wait.md`. `validate --spec` and
  `validate --plan` pass with waves `[T1] [T2] [T3]` and assurance graph
  `fe18bb1fb9db580c9ae555c4b0d7f08b32aa4f8b93ac90f7a68705d14a01d6d7`. The F27,
  F26, F24, and F23 plans still validate with unchanged graphs.
- `python -m unittest tests.test_ezpowers_runtime` passed 33 tests in 143.636
  seconds before any edit. Six tests were added first. On the unchanged
  runtime four failed: the wait rule blocked, the answer under cp949 exited 1
  with `UnicodeEncodeError`, a UTF-8 event under cp949 blocked, and an
  injected `RuntimeError` escaped the hook. Two already passed and pin
  behavior that must not change: an unreadable event blocks, and a deleted
  plan blocks. All six pass after the runtime change, and the module passes 39
  tests in 170.611 seconds.
- Same real-host session on the 5.11.1 kit: two Stops, none blocked. The Stop
  while the reviewer ran was answered `{}`, the host resumed the session when
  the reviewer reported, the session certified, and the final Stop was
  allowed. A second session without a subagent was blocked once with
  "EZPowers completion evidence is fresh but not certified", certified, and
  was then allowed. Trace SHA-256 values: `after-trace.jsonl`
  `d92d6480e08df966548bd10b66b5fb4099df757c8a06c9cba93bd6de45ac80a4`,
  `after-nosub-trace.jsonl`
  `d86de1d48e6a19b946fcc05715cf7dae5b6fb48d2735fbd9751b04c48daabe88`.
- Two host probes with a fixed Stop answer, in an empty project: an answer
  that carries only `systemMessage` ended the turn after one hook call and
  the host showed "Stop says:" followed by the notice; a hook that exits 1
  with nothing on stdout also ended the turn after one call, with only a
  generic "stop hook reported a problem" notice. The hook's own failure path
  was exercised by a test that injects the error, not on the host.
- Upgrade path: a project installed from the committed v5.11.0 tree with the
  completion hook enabled blocked a Stop with and without a running subagent.
  After `install --refresh` with the 5.11.1 runtime its
  `.claude/settings.json` was byte-identical, the installed kit was 5.11.1,
  the Stop with a running subagent was answered `{}`, and the Stop with
  nothing running was blocked.
- `python -m unittest discover -s tests` in UTF-8 mode on Python 3.14.3 passed
  249 tests in 927.964 seconds with one POSIX-only skip, on the final runtime.
- `scripts/check-repo.ps1`: PASS. `scripts/harness-runtime-smoke.ps1`: PASS
  for a real v5.11 install, trace, verify, certify, stale, and reuse flow.
  `scripts/verify-harness-kit.py`: v5.11 manifest valid.
  `scripts/plugin_smoke.py --host both`: file surfaces matched, Claude 2.1.327
  accepted both manifests, and Codex 0.169.1 loaded every project and
  namespaced skill in isolation.
- Scheduler measurements passed: fixture median 1.193888 seconds serial versus
  0.311331 parallel (73.92 percent improvement); project median 1.176528
  versus 0.768892 (34.65 percent improvement); equivalent outcomes in both.
- `python scripts/benchmark_check_reuse.py --runs 3 --minimum-improvement 50`:
  PASS with a median of 2.920966 seconds against 8.177094 for a forced full
  run, a 64.28 percent improvement, equal outcomes, and one process start for
  a thrice-referenced declared check.
- Five interleaved software compatibility runs against
  `08f9f84d24c59ec130dd6b3bf26555503910cbab` produced equivalent output.
  Baseline median was 4.230037 seconds and candidate median 4.225222 seconds,
  a -0.11 percent regression against the 5 percent limit.
- `DESIGN.md` lint, the project design check, and the visual-readiness check
  passed for the version-only guide edit. The guide was not rendered or
  inspected at the three documented viewports.
- Not exercised: the completion hook on a live Codex host, including how
  Codex shows a `systemMessage`-only Stop answer; an interactive Claude Code
  session (every live run used `claude -p`); the default model (the live runs
  used the `sonnet` alias); a real crash of the hook on the host; a subagent
  that never reports; background `workflow` or `teammate` tasks, which do not
  defer; any installed project (none was refreshed); the POSIX execute-bit
  test, skipped on Windows; in-repository `verify --all`; F19 remains
  deferred.

Earlier per-release verification evidence was pruned from this file. It
remains in `harness_versions/changelog.jsonl` (one entry per release from
v5.2.0 through v5.11.0) and in this file's Git history: the v5.11.0 record is
complete at commit `ddd53a2`, and the records up to v5.10.0 at commit
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

### Candidates not acted on in v5.11

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
