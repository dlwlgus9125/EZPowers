# UI Verification Adapter Contract

UI verification is capability-based. Playwright is the preferred browser e2e
adapter when it can run, but a project may use another adapter when it preserves
the same user-observable oracle.

## Config Shape

`.harness/config.json` should include:

```json
{
  "ui_verification": {
    "required": false,
    "capability": "",
    "adapter": "",
    "command": "",
    "oracle": "",
    "fallback_adapter": "",
    "evidence": []
  }
}
```

Set `required: true` for web, mobile, desktop, CLI/TUI, or any user-facing UI
surface.

## Capability Matrix

| Capability | Valid adapters | Required oracle |
| --- | --- | --- |
| `browser-e2e` | Playwright, Cypress, WebDriver, framework browser runner | DOM state, route, network, accessibility, and visible result |
| `component-dom` | Storybook interaction tests, Testing Library, Vitest browser mode | Rendered component behavior and accessibility-visible state |
| `framework-headless` | Framework renderer or test harness | View model, bindings, events, and rendered tree |
| `desktop-gui` | UI automation, process plus screenshot, framework headless runner | Window opens, controls render, interaction changes observable state |
| `mobile-emulator` | Simulator/emulator integration test | Screen, navigation, gesture, and persisted state |
| `cli-tui` | Terminal runner, stdout/screen probe, snapshot with interaction | User-visible terminal output and keyboard flow |
| `custom` | Project-specific adapter documented in config | Same observable behavior as the acceptance criterion |

## Selection Rules

`/design_architecture` selects the strongest viable adapter from repo evidence
and user confirmation. It records the adapter, command, oracle, and evidence in
the testing methodology.

`/prepare_execute` must copy that adapter into relevant tasks. If no adapter is
installed or runnable, it inserts a prerequisite task before feature work to
install or build the adapter.

`/choice_execute` treats adapter failure as a real Verify failure. A skipped UI
adapter is valid only when the plan includes an approved non-UI replacement
that proves the same user-observable result.

`adapter_fallback_task_required`: when a UI acceptance criterion needs an
adapter and the selected adapter cannot run in the project, the plan must add a
prerequisite adapter task instead of downgrading the criterion.

## Equivalence Rule

Equivalent means the replacement verifies the same observable claim, not merely
that it runs in the same test stage. For example, a component test can replace a
browser test only when route integration, data loading, and user interaction are
not part of the acceptance criterion, or when those concerns are covered by
separate automated probes.

## Audit Rule

Internal pipeline audit fails UI work when:

- `ui_verification.required` is true and no adapter is selected.
- A UI task lacks a task-level adapter command or approved prerequisite task.
- The command does not assert user-visible behavior.
- Visual or accessibility evidence is advisory-only for an acceptance criterion
  that depends on it.
