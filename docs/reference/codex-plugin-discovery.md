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

The plugin root exposes exactly these nine skills:

```text
setup
deep-interview
design-architecture
spec
prepare-execute
execute
frontend-design
improve-codebase-architecture
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

The explicitly invoked workflow skills are `setup`, `design-architecture`,
`spec`, `prepare-execute`, `execute`, and `hud`. The skills
`deep-interview`, `frontend-design`, and `improve-codebase-architecture` may be
matched implicitly from their descriptions. Both hosts must encode the same
intent using their own policy field; one host's field is not evidence that the
other host enforces it.

## Project Installation

`setup` copies eight project workflow skills to the canonical
`.ezpowers/kit/skills/` tree and byte-identical host trees under
`.claude/skills/` and `.agents/skills/`. `hud` is not copied because it manages
global Codex UI rather than project completion.

After installation, the target project must be usable without the EZPowers
plugin checkout. Claude and Codex discover their project-local copies through
their native skill locations. A missing host copy, byte drift from the
canonical kit, or missing Codex skill metadata is an installation failure.

## Optional Completion Hooks

Hooks are disabled by default and installed only with explicit
`--enable-hooks claude|codex|both`. The installer resolves and safely quotes
the current Python executable and the target project's runtime so the hook does
not depend on the host session's working directory. The stored command is
equivalent to:

```text
<absolute-python> <absolute-project>/.ezpowers/ezpowers.py hook --host <host>
```

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

## Official Host Evidence

Verified on 2026-07-22:

- Claude documents project and plugin skill locations, plugin namespaces, and
  `disable-model-invocation` in
  [Extend Claude with skills](https://code.claude.com/docs/en/slash-commands).
- Claude documents plugin layout and `/plugin-name:skill-name` in
  [Create plugins](https://code.claude.com/docs/en/plugins).
- Claude documents Stop's block-only `decision` contract in
  [Hooks reference](https://code.claude.com/docs/en/hooks#stop).
- Codex documents `$` invocation, `.agents/skills`, and its per-skill
  invocation policy metadata in
  [Build skills](https://learn.chatgpt.com/docs/build-skills).
- Codex documents `.codex-plugin/plugin.json`, bundled skill namespaces, and
  plugin lifecycle in
  [Build plugins](https://learn.chatgpt.com/docs/build-plugins) and
  [Plugins](https://learn.chatgpt.com/docs/plugins).
- Codex documents Stop continuation with `decision: "block"` and `reason`,
  and the separate hook-run `continue` control, in
  [Hooks](https://learn.chatgpt.com/codex/hooks).
- Host-native execution boundaries are supported by Codex's official
  [Subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents),
  [Worktrees](https://learn.chatgpt.com/docs/environments/git-worktrees), and
  [agent approvals and sandboxing](https://learn.chatgpt.com/docs/agent-approvals-security),
  and by Claude's official
  [subagents](https://code.claude.com/docs/en/sub-agents),
  [worktrees](https://code.claude.com/docs/en/worktrees),
  and [permissions](https://code.claude.com/docs/en/permissions) documentation.

## Verification

Repository validation is non-installing:

```text
python scripts/plugin_smoke.py --host both
```

The smoke validates both manifests, the exact retained inventory, invocation
metadata, and absence of removed components. When the CLIs are available it
uses Claude's non-installing plugin validator and an isolated Codex project
created from actual installer output. Installation tests separately prove that
the Claude and Codex local skill trees are byte-identical to the canonical kit.
The smoke must not install, reinstall, or edit global plugin state.
