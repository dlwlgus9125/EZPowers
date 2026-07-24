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

The plugin root exposes exactly these thirteen skills:

```text
setup
deep-interview
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
`prepare-execute`, `execute`, `harness-chain`, and `hud`. The skills
`deep-interview`, `diagnose`, `codebase-design`, `frontend-design`, and `wiki`
may be matched implicitly from their descriptions. Both hosts must
encode the same intent using their own policy field; one host's field is not
evidence that the other host enforces it.

An explicit `/ezpowers:diagnose` or `$ezpowers:diagnose` invocation selects the
fix-complete path unless the user says analysis-only or no edits. The
project-local `/diagnose` and `$diagnose` variants have the same contract.
Reproduction, hypotheses, and root cause are progress checkpoints; both hosts
continue through the source-cause patch and original-symptom verification.

`deep-interview` uses a host-native structured question surface when one is
callable and appropriate, and otherwise asks one plain-text question. The
shared contract is one consequential question per turn and a confirmed request
in the current conversation, not identical question UI capabilities. In an
already active Plan Mode, its final confirmation makes continuation explicit
and then resumes that same host-native planning process. The confirmed request
is the source of truth for clarified user intent, so planning does not repeat
settled product questions. This mode continuation does not invoke another
skill, create a project artifact, or authorize implementation.

## Project Installation

`setup` copies twelve project workflow skills to the canonical
`.ezpowers/kit/skills/` tree and byte-identical host trees under
`.claude/skills/` and `.agents/skills/`. `hud` is not copied because it manages
global Codex UI rather than project completion.

After installation, the target project must be usable without the EZPowers
plugin checkout. Claude and Codex discover their project-local copies through
their native skill locations. A missing host copy, byte drift from the
canonical kit, or missing Codex skill metadata is an installation failure.

Codex plugin and project skill names are not interchangeable. Each retained
skill's plugin metadata invokes `$ezpowers:<name>`. The twelve project-installed
skills carry a distribution-only metadata variant that invokes `$<name>`; the
manifest copies that variant to the installed metadata filename expected by
Codex. `hud` has no project variant.

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

SubagentStart binds a host-native reviewer ID and injects a read-only rubric.
Only that agent's SubagentStop marker can produce the hashed gate receipt.
PreToolUse is an early guard for frozen files; runtime hash checks before
verify/certify remain authoritative. Details are in
`harness-chain-contract.md`.

## Official Host Evidence

Verified on 2026-07-24:

- Claude documents project and plugin skill locations, plugin namespaces, and
  `disable-model-invocation` in
  [Extend Claude with skills](https://code.claude.com/docs/en/slash-commands).
- Claude documents plugin layout and `/plugin-name:skill-name` in
  [Create plugins](https://code.claude.com/docs/en/plugins).
- Claude documents Stop's block-only `decision` contract in
  [Hooks reference](https://code.claude.com/docs/en/hooks#stop).
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
queries actual Codex `skills/list`. It requires all twelve local skills and all
thirteen namespaced plugin skills to be enabled, error-free, and paired with the
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
