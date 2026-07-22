---
doc_type: reference
authority: canonical
status: active
---

# Codex Usage HUD

## Mechanism

Codex CLI v0.101.0 and newer has a native TUI footer configured by
`[tui].status_line` in the global `~/.codex/config.toml`. EZPowers uses that
host surface on Windows instead of tmux, ANSI scroll regions, terminal title
polling, or a wrapper around the Codex process.

The design follows the two-layer boundary demonstrated by oh-my-codex: native
Codex status-line items carry Codex session data, while plugin-specific runtime
state belongs in a separate optional display. EZPowers needs only the native
usage layer and implements its own ownership and update flow.

Design evidence reviewed on 2026-07-22:

- oh-my-codex commit `435d4a9`: its
  [HUD skill](https://github.com/Yeachan-Heo/oh-my-codex/blob/435d4a9cc982ffaf83fabbfbb8711ae6c178ffca/skills/hud/SKILL.md)
  defines the native Codex status line as layer 1, and its
  [config generator](https://github.com/Yeachan-Heo/oh-my-codex/blob/435d4a9cc982ffaf83fabbfbb8711ae6c178ffca/src/config/generator.ts)
  manages the preset with an ownership comment.
- OpenAI Codex tag `rust-v0.145.0` (`25af12f`):
  [status_line_setup.rs](https://github.com/openai/codex/blob/rust-v0.145.0/codex-rs/tui/src/bottom_pane/status_line_setup.rs)
  defines the selectable item IDs,
  [status_surfaces.rs](https://github.com/openai/codex/blob/rust-v0.145.0/codex-rs/tui/src/chatwidget/status_surfaces.rs)
  maps live rate-limit and context data to display strings, and
  [status_line_style.rs](https://github.com/openai/codex/blob/rust-v0.145.0/codex-rs/tui/src/bottom_pane/status_line_style.rs)
  applies theme colors.

These sources are design references only; EZPowers uses a new stdlib Python
config manager and its own paired-marker conflict policy.

## Display Contract

EZPowers selects these native items in order:

```toml
[tui]
# >>> ezpowers:managed-codex-hud >>>
status_line = ["five-hour-limit", "weekly-limit", "context-used"]
status_line_use_colors = true
# <<< ezpowers:managed-codex-hud <<<
```

Codex renders the primary rate-limit window, secondary/weekly window, and
context use directly in its persistent footer. A typical native line is:

```text
5h 88% left · weekly 74% left · Context 34% used
```

Unavailable API values are omitted independently by Codex, so one missing
window does not suppress the other segments. The footer remains owned and
redrawn by Codex itself during prompts, tool calls, resize, and alternate-screen
transitions.

Codex owns the wording and semantics of native items: rate limits are displayed
as percentage remaining, while context is percentage used. Codex v0.145.0 does
not expose a custom clock item, reset-countdown formatter, arbitrary renderer,
or percentage-threshold style callback. `status_line_use_colors = true` enables
the active Codex theme's native item colors; EZPowers does not patch or proxy the
TUI to imitate the Claude-only formatter.

## Install and Status

The helper is stdlib-only Python and does not install a harness:

```powershell
python scripts/codex-hud.py status
python scripts/codex-hud.py preview
python scripts/codex-hud.py install --approve
```

`status` and `preview` never write. `install` refuses to write without
`--approve`. After installation, start a new Codex session; `/statusline` opens
Codex's live native status-line picker and preview.

When running from an installed plugin instead of this checkout, invoke
`$ezpowers:hud`; the skill resolves the script from its plugin root.

## Ownership and Conflicts

The paired `ezpowers:managed-codex-hud` comments are the ownership boundary.
EZPowers may update or remove only an exact known managed block.

- An unmarked `status_line` or `status_line_use_colors` assignment is
  user-owned. Installation stops with `conflict` and preserves it byte-for-byte.
- Root dotted assignments such as `tui.status_line = [...]` are handled by the
  same conflict rule; an inline `tui = {...}` table is rejected as unsafe to
  merge automatically.
- A marked block whose contents were edited is treated as `customized` and
  preserved.
- Replacing either case requires showing the exact existing assignments,
  receiving explicit approval, and adding `--replace-existing`.
- Unrelated global Codex keys, other `[tui]` keys, newline style, and a UTF-8 BOM
  are preserved.
- Duplicate `[tui]` sections or incomplete ownership markers are malformed
  input and are never rewritten.

## Uninstall

```powershell
python scripts/codex-hud.py uninstall --approve
```

Uninstall removes only the exact owned block. It intentionally leaves an empty
`[tui]` section rather than guessing whether the section header belongs to the
user. Start a new Codex session after removal.

## Verification

Run the helper status check, a real Codex config-load smoke, and the unit tests:

```powershell
python scripts/codex-hud.py status --json
codex debug prompt-input "EZPowers Codex HUD config smoke"
python -m unittest tests.test_codex_hud
```

For the visible runtime check, start a new Codex CLI session and open
`/statusline`; the selected items must be `five-hour-limit`, `weekly-limit`, and
`context-used` in that order with theme colors enabled.
