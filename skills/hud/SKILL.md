---
name: hud
description: Use when the user asks to enable, configure, inspect, repair, or remove a global Codex model and usage HUD or statusline without installing a project harness.
disable-model-invocation: true
---

# /hud - Codex Model and Usage HUD

## Purpose

Manage the EZPowers model and usage HUD through Codex's native TUI status line.
This is a global Codex configuration task; do not install or refresh a project harness.
Do not use the Claude Code `statusLine` script.

## Read

- `docs/reference/codex-hud.md`

## Procedure

1. Resolve the EZPowers plugin root that contains this skill and
   `scripts/codex-hud.py`.
2. Run `codex --version`. Stop when the installed CLI is older than v0.145.0 or
   when `codex` is unavailable.
3. Run the helper in read-only mode:

   ```powershell
   python <ezpowers-root>/scripts/codex-hud.py status --json
   python <ezpowers-root>/scripts/codex-hud.py preview --json
   ```

4. Show the exact managed fragment and config path. If the helper reports
   `conflict` or `customized`, show the existing `status_line` and
   `status_line_use_colors` assignments and ask replace-or-skip.
5. Ask for an explicit yes before any write. Prior approval for plugin install,
   marketplace refresh, or harness setup is not approval to edit the global
   Codex config.
6. After approval, install or repair the HUD:

   ```powershell
   python <ezpowers-root>/scripts/codex-hud.py install --approve
   ```

   Add `--replace-existing` only when the preview showed the exact conflicting
   assignments and the user explicitly approved replacing them.
7. Verify the owned fragment and that Codex can load the resulting config:

   ```powershell
   python <ezpowers-root>/scripts/codex-hud.py status --json
   codex debug prompt-input "EZPowers Codex HUD config smoke"
   ```

   The second command is a config-load smoke; its JSON body may be discarded,
   but report its real exit code. Start a new Codex session for the footer to
   load, then `/statusline` shows the active native item selection.

## Removal

Preview the current state, ask for an explicit yes, then run:

```powershell
python <ezpowers-root>/scripts/codex-hud.py uninstall --approve
```

Remove only the exact EZPowers-owned block. A marked block whose value was
edited is user-owned until the user explicitly approves `--replace-existing`.

## Output

- Codex CLI version.
- Config path and before/after SHA-256 values.
- Installed, unchanged, removed, conflict, or skipped result.
- Config-load smoke exit code.
- Reminder to start a new Codex session after a change.
