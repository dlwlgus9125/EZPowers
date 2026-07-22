---
doc_type: reference
authority: canonical
status: active
---

# Codex Model and Usage HUD

The HUD is a plugin-only, global, explicit opt-in. It is not installed by
`setup`, copied into a target project's local kit, or used as completion
evidence. Claude Code project status lines are outside this feature.

## Native Mechanism

EZPowers configures Codex's native TUI footer in the user's global
`config.toml`:

```toml
[tui]
# >>> ezpowers:managed-codex-hud >>>
status_line = ["model-with-reasoning", "five-hour-limit", "weekly-limit", "context-used"]
status_line_use_colors = true
# <<< ezpowers:managed-codex-hud <<<
```

The leading `model-with-reasoning` item follows
[OMX's native HUD example](https://github.com/Yeachan-Heo/oh-my-codex/blob/main/skills/hud/SKILL.md)
and shows the active session model together with its reasoning effort. Codex
owns rendering, wording, refresh, missing-value behavior, and theme colors.
EZPowers does not wrap, patch, or proxy the Codex process.

## Read Before Write

From the plugin checkout or the path resolved by `$ezpowers:hud`:

```text
python scripts/codex-hud.py status --json
python scripts/codex-hud.py preview --json
```

Both commands are read-only. Show the resolved config path and the exact
proposed fragment. `install` or `uninstall` requires explicit approval:

```text
python scripts/codex-hud.py install --approve
python scripts/codex-hud.py uninstall --approve
```

Use `--replace-existing` only after displaying the conflicting assignments and
receiving explicit approval to replace them.

## Ownership And Conflicts

The paired markers are the ownership boundary.

- The current exact managed block may be repaired or removed.
- The prior exact usage-only block is reported as `outdated` and may be
  upgraded or removed without treating it as user-owned.
- Unmarked `status_line` values, inline `tui` tables, incomplete markers, and
  edited managed values are user-owned or malformed and are preserved.
- Unrelated global keys, other `[tui]` values, newline style, and UTF-8 BOM are
  preserved.
- The helper never edits project `.ezpowers` state or Claude settings.

## Verification

After an approved write:

```text
python scripts/codex-hud.py status --json
codex debug prompt-input "EZPowers Codex HUD config smoke"
```

Report both exit codes and the before/after SHA-256 values. Start a new Codex
session and use `/statusline` for the visible check. Removing the HUD removes
only the exact owned block.
