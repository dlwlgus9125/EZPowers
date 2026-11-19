---
doc_type: reference
authority: canonical
status: active
---

# Claude And Codex Discovery

This document keeps its historical filename, but its contract covers both
supported hosts. A feature documented for one host must not be inferred for the
other.

## Retained Plugin Surface

The plugin root exposes exactly these fifteen skills:

```text
setup
deep-interview
explain-with-evidence
diagnose
codebase-design
improve-codebase-architecture
design-architecture
spec
prepare-execute
execute
frontend-design
wiki
harness-chain
hud
teach
```

The plugin ships no agents and no plugin-root hooks. Coding, subagents,
worktrees, sandboxing, review, and retries remain host-native capabilities.

## Plugin Invocation

| Concern | Claude Code | Codex |
| --- | --- | --- |
| Manifest | `.claude-plugin/plugin.json` | `.codex-plugin/plugin.json` |
| Bundled skill root | `skills/<name>/SKILL.md` | manifest `"skills": "./skills/"` |
| Plugin namespace | `/ezpowers:<name>` | `$ezpowers:<name>` |
| Explicit-only policy | `disable-model-invocation: true` in `SKILL.md` | `policy.allow_implicit_invocation: false` in Codex skill metadata |
| Local project skill root | `.claude/skills/<name>/` | `.agents/skills/<name>/` |
| Local invocation | `/<name>` | `$<name>` |

The explicitly invoked workflow skills are `setup`,
`improve-codebase-architecture`, `design-architecture`, `spec`,
`prepare-execute`, `execute`, `harness-chain`, `hud`, and `teach`. The skills
`deep-interview`, `explain-with-evidence`, `diagnose`, `codebase-design`,
`frontend-design`, and `wiki` may be matched implicitly from their
descriptions. Both hosts must
encode the same intent using their own policy field; one host's field is not
evidence that the other host enforces it.

`explain-with-evidence` changes presentation only. It matches the user's active
conversational language, uses a compact result or deep-explanation shape, and
omits alternatives, reversals, measurements, or chronology that were not
actually observed. Fixed-schema artifacts and exact states such as `BLOCKED`
or `CERTIFIED` remain byte- and meaning-preserving inputs rather than narrative
material.

`teach` is explicit-only on both hosts and exists only in the plugin namespace
as `/ezpowers:teach` or `$ezpowers:teach`. It keeps one topic's mission,
resources, lessons, and learning records in the directory the user invokes it
in, warns before writing inside an EZPowers-managed project, and has no
project-local variant, hook, or completion role.

An explicit `/ezpowers:diagnose` or `$ezpowers:diagnose` invocation selects the
fix-complete path unless the user says analysis-only or no edits. The
project-local `/diagnose` and `$diagnose` variants have the same contract.
Both hosts must run a command that shows the user's exact symptom red and
minimise it before stating hypotheses or editing product behavior. If that
gate cannot be opened, they request the missing access, captured artifact, or
instrumentation and stop without guessing. After the gate, hypotheses and root
cause remain progress checkpoints; both hosts continue through the
source-cause patch and original-symptom verification.

`deep-interview` uses a host-native structured question surface when one is
callable and appropriate, and otherwise asks one plain-text question. Before
each question and before stopping, it checks both stated gaps and
context-specific blind spots; only plausible candidates that could materially
change the request become questions. The shared contract is one consequential
question per turn and a confirmed request in the current conversation, not
identical question UI capabilities. Its final question offers confirm and
proceed, correct, or confirm and finish with the summary. Ordinary-mode proceed
ends the interview and resumes the host's work on the clarified request,
including implementation and verification when requested. In Plan Mode, that
choice is explicitly confirm and continue planning; it authorizes no
implementation, even if the mode later changes. The confirmed request remains
the source of truth, with no repeated product questions or second continuation
approval. The interview writes no files and dispatches no companion workflow;
subsequent approved work follows the host's project instructions and permissions.

Use only a question surface callable in the current mode, with the same choices
in plain text as the fallback. Do not switch modes merely to obtain a question
UI. Wait for a submitted answer, including with asynchronous tools; preselection,
silence, and agreement with the wording alone do not authorize execution.
Correction returns to clarification, while summary-only and stop requests end
without work.

## Project Installation

`setup` copies thirteen project workflow skills to the canonical
`.ezpowers/kit/skills/` tree and byte-identical host trees under
`.claude/skills/` and `.agents/skills/`. `hud` is not copied because it manages
global Codex UI rather than project completion. `teach` is not copied because
it is a learner-facing utility with no project completion role.

After installation, the target project must be usable without the EZPowers
plugin checkout. Claude and Codex discover their project-local copies through
their native skill locations. A missing host copy, byte drift from the
canonical kit, or missing Codex skill metadata is an installation failure.

Codex plugin and project skill names are not interchangeable. Each retained
skill's plugin metadata invokes `$ezpowers:<name>`. The thirteen project-installed
skills carry a distribution-only metadata variant that invokes `$<name>`; the
manifest copies that variant to the installed metadata filename expected by
Codex. `hud` and `teach` have no project variant.

## Ordinary Optional Completion Hooks

Hooks are disabled by default and installed only with explicit
`--enable-hooks claude|codex|both`. The installer resolves and safely quotes
the current Python executable and the target project's runtime so the hook does
not depend on the host session's working directory. The stored command is
equivalent to:

```text
<absolute-python> <absolute-project>/.ezpowers/ezpowers.py hook --host <host>
```

The installer requires Claude Code 2.1.217 or newer before writing Claude
hooks and Codex CLI 0.145.0 or newer before writing Codex hooks. The same
minimums gate the selected hosts in harness-chain configuration preview.

They derive the same allow/block verdict and block reason from the same local
status. Their configuration wire formats differ:

- Claude stores the absolute interpreter in `command` and the remaining tokens
  in a no-shell `args` array.
- Codex stores a POSIX-safe `command` and a Windows-safe `commandWindows`
  string because its schema has no separate argument array.

Both runtimes emit the same documented Stop response: `{}` for a fresh
certified state, or `{"decision":"block","reason":"..."}` for a stale or
uncertified state. In Codex, `continue: false` stops the hook run itself and is
not the completion-continuation response.

Two rules keep the adapter out of the session's way. On Claude Code a Stop
whose `background_tasks` lists a running subagent is a wait and is not
blocked; the host starts the next turn when the subagent reports, and that
Stop is judged as usual. Codex's Stop input has no such list, so Codex keeps
blocking. An adapter that fails with an error the runtime does not recognise
answers `{"systemMessage":"..."}` and does not block, while an invalid status
still blocks. The adapter reads its input as UTF-8 and answers with ASCII-only
JSON.

The adapter does not rerun tests or reinterpret evidence. Project hooks are
thin lifecycle integrations, not a second completion engine.

SessionEnd wiki capture is a separate, disabled-by-default adapter installed
only with `--enable-wiki-hooks claude|codex|both`. It invokes
`wiki capture --host <host>`, always returns `{}`, and never changes the Stop
verdict. Its allowlisted local storage rules are defined in
`wiki-contract.md`.

## Explicit Harness Chain Hooks

`harness-chain` is installed in projects but dormant by default. Its own
hash-bound configuration approval installs SessionStart, Stop, PreToolUse,
SubagentStart, and SubagentStop handlers. It removes the runtime-owned ordinary
completion Stop entry so one host cannot have two EZPowers continuation
authorities.

The hosts deliberately differ:

- Codex uses one native goal with the exact approved objective. Its chain Stop
  hook observes state and emits only a terminal brake; it does not create a
  second continuation loop.
- Claude Code uses the project Stop hook as the sole chain continuation loop.
  Claude Code's own `/goal` is a session-scoped, model-judged Stop hook and is
  never combined with it for one feature.

SessionStart records the handshake. Claude Code sends no permission mode on
that event, so the runtime takes the mode from the first later hook event of
the same session that reports one. Claude Code is unattended-capable in
`auto`, `dontAsk`, or `bypassPermissions`.

SubagentStart binds a host-native reviewer ID and injects a read-only rubric.
Only that agent's final report can produce the hashed gate receipt: on Claude
Code the message of its `SubagentHandback` call when it has that tool (auto
mode), otherwise its SubagentStop message.

A Claude Stop that arrives while a background subagent is still running is a
wait, not a continuation. The hook neither blocks nor counts it, and the host
starts the next turn when the subagent reports.

PreToolUse is an early guard for frozen files; runtime hash checks before
verify/certify remain authoritative. The Claude matcher covers `Bash`,
`PowerShell`, `Write`, `Edit`, `NotebookEdit`, and `SubagentHandback`; the
Codex matcher is unchanged. The guard's classification reads only the tool
payload and is shared by both hosts. Details are in
`harness-chain-contract.md`.

## Official Host Evidence

Three kinds of evidence are kept apart. A documentation statement is not a
live observation, and neither covers a host that was not run.

Live-verified on 2026-11-18 with Claude Code 2.1.327 (`claude -p`, one run in
`auto` and one in `dontAsk`, raw hook input recorded):

- SessionStart input has no `permission_mode`; PreToolUse, Stop, and
  SubagentStop carry it.
- In `auto` a subagent's report arrives as `tool_input.message` of a
  PreToolUse event for `SubagentHandback` that carries the subagent's
  `agent_id`, and SubagentStop has no `last_assistant_message`.
- In `dontAsk` there is no hand-back and SubagentStop's
  `last_assistant_message` carries the report.
- A Stop that fires while a background subagent runs lists it in
  `background_tasks` with `type` `subagent`, `status` `running`, and an `id`
  equal to its `agent_id`.
- A PreToolUse hook whose matcher is an alternation that includes
  `SubagentHandback` receives the hand-back, and the host waits for that hook
  before it fires SubagentStop.
- A SubagentStop `decision: "block"` is not honored after a hand-back: the
  subagent is not continued.
- A subagent's shell call can arrive with `tool_name` `PowerShell`.
- The hook process does not run in Python UTF-8 mode. On a Korean Windows
  console its text streams default to cp949 while the host sends UTF-8.

Live-verified on 2026-11-19 with Claude Code 2.1.327 (`claude -p` in `auto`
with the `sonnet` alias, the ordinary completion Stop hook, every Stop input
and answer recorded):

- A Stop input carries `background_tasks`, `cwd`, `effort`,
  `hook_event_name`, `last_assistant_message`, `permission_mode`, `prompt_id`,
  `session_crons`, `session_id`, `stop_hook_active`, and `transcript_path`.
- The host ends the turn after nine consecutive Stop blocks with no tool call
  between them, says so, and names `CLAUDE_CODE_STOP_HOOK_BLOCK_CAP`. The
  documentation says eight.
- `stop_hook_active` is false on the first Stop of a turn and true on a Stop
  that follows a block. The Stop after a background subagent reports is a
  first Stop again.
- A Stop answer `{}` while a subagent runs ends the turn, and the host starts
  the next turn when the subagent reports.
- A Stop answer that carries only `systemMessage` does not continue the turn.
  The host shows it as a notice that begins "Stop says:".
- A Stop hook that exits 1 with nothing on stdout does not block. The host
  shows a generic "stop hook reported a problem" notice.

Doc-verified on 2026-11-19:

- Claude documents a hook that exits with a code other than 0 or 2, or prints
  JSON that cannot be parsed, as a non-blocking error, and `systemMessage` as
  a warning shown to the user, in
  [Hooks reference](https://code.claude.com/docs/en/hooks).
- Codex documents Stop input as `turn_id`, `stop_hook_active`, and
  `last_assistant_message`, with no list of background tasks, and
  `systemMessage` as a warning surfaced in the UI or event stream, in
  [Hooks](https://learn.chatgpt.com/docs/hooks).

Doc-verified on 2026-11-18:

- Claude documents project and plugin skill locations, plugin namespaces, and
  `disable-model-invocation` in
  [Extend Claude with skills](https://code.claude.com/docs/en/skills).
- Claude documents Stop's `decision` contract, the eight-consecutive
  continuation cap, `background_tasks`, SubagentStart context injection, and
  the `SubagentHandback` report in
  [Hooks reference](https://code.claude.com/docs/en/hooks).
- Claude documents `auto` as the starting mode of terminal sessions and the
  other mode names in
  [Permission modes](https://code.claude.com/docs/en/permission-modes).
- Claude documents `/goal` as a session-scoped prompt-based Stop hook in
  [Goal](https://code.claude.com/docs/en/goal).
- Codex documents its hook events, the review required for new or changed
  hooks, and the Stop output contract in
  [Hooks](https://learn.chatgpt.com/docs/hooks).

Carried from 2026-07-24 and not fetched again:

- Claude documents plugin layout and `/plugin-name:skill-name` in
  [Create plugins](https://code.claude.com/docs/en/plugins).
- Codex 0.145.0 exposes complete explicit and implicit skill inventory,
  enabled state, metadata, and load errors through the app-server
  [`skills/list`](https://github.com/openai/codex/blob/rust-v0.145.0/codex-rs/app-server/README.md#skills)
  request.
- Codex's versioned Stop output schema defines `decision: "block"` and
  `reason` separately from hook-run continuation in the
  [0.145.0 schema](https://github.com/openai/codex/blob/rust-v0.145.0/codex-rs/hooks/schema/generated/stop.command.output.schema.json).
- Host-native execution boundaries are supported by Codex's official
  [Subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents),
  [Worktrees](https://learn.chatgpt.com/docs/environments/git-worktrees), and
  [agent approvals and sandboxing](https://learn.chatgpt.com/docs/agent-approvals-security),
  and by Claude's official
  [subagents](https://code.claude.com/docs/en/sub-agents),
  [worktrees](https://code.claude.com/docs/en/worktrees),
  and [permissions](https://code.claude.com/docs/en/permissions) documentation.

Unverified:

- No part of the Codex harness chain has been run on a live host: native-goal
  continuation, its terminal Stop response, subagent binding, and its use of
  Claude permission-mode names. Its hook matchers and continuation behavior
  are unchanged. The changes that do not branch on the host apply to it too:
  the frozen-file guard classification, taking the mode from a later event
  when SessionStart reported none, UTF-8 hook input with ASCII answers, the
  code-review rubric wording, the comparison of installed matchers, and a
  finished run no longer ending a pending oracle audit.
- The ordinary completion hook was not run on a live Codex host. Whether
  Codex shows a Stop answer that carries only `systemMessage`, and what it
  does with a Stop hook that exits with an error, comes from its
  documentation alone.
- An interactive Claude Code session, a forked session, and compaction during
  a run were not probed.

## Verification

Repository validation is globally non-mutating:

```text
python scripts/plugin_smoke.py --host both
```

The smoke validates both manifests, the exact retained inventory, both Codex
metadata variants, invocation policy, and absence of removed components. When
the CLIs are available it uses Claude's non-installing plugin validator,
installs the project kit into a temporary Git worktree, installs the plugin
from a compact temporary local marketplace under an isolated `CODEX_HOME`, and
queries actual Codex `skills/list`. It requires all thirteen local skills and
all fifteen namespaced plugin skills to be enabled, error-free, and paired with the
expected prompt. The implicit prompt-input probe remains a second discovery
check. The smoke never installs, reinstalls, or edits global plugin state.

For release audits, an explicit mixed behavioral probe is also available:

```text
python scripts/plugin_smoke.py --host both --live-advisory
```

This makes one real model call per selected host and may consume account quota.
Claude loads the namespaced plugin for that process only; Codex uses a
temporary project-kit install and an ephemeral read-only session. Both must
execute `deep-interview` and return exactly one clarification question without
writing the fixture.

The exact-red ordering contract has a separate, explicit release probe:

```text
python scripts/plugin_smoke.py --host both --live-diagnose
```

This makes two real model calls per selected host. Each read-only reproduction
prints a source-bound evidence token that the host transcript must retain. The
fixable fixture requires baseline red before patched green. The blocked fixture
withholds a production capture and requires the product and reproduction to
remain unchanged while the host requests that specific evidence. Normal
repository and host smoke commands make no model calls.
