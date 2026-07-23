# Plan Contract

This contract maps every spec criterion exactly once to ordered work and exact
project-local checks. The plan does not decide how Claude Code or Codex edits,
delegates, isolates worktrees, reviews, or retries.

## Preflight

Read the selected valid spec, architecture and frontend-design artifacts,
repository instructions, the registered documentation graph when present,
source and tests, CI commands, and
`.ezpowers/config.json`. Run:

```text
python .ezpowers/ezpowers.py validate --spec <spec-path> --json
```

Return to `spec` when a claim is ambiguous or cannot be automated without
weakening it. Add a prerequisite when the project lacks a required adapter.

## Human-Readable Plan

Write the plan under `docs/plans/`. Explain the goal, ordered vertical slices,
dependencies, expected files, architecture/design constraints, non-goals, and
risks in Markdown. Keep the machine coverage and command data in one managed
block.

## Managed JSON Block

````markdown
<!-- ezpowers:plan:start -->
```json
{
  "schema_version": 1,
  "spec": "docs/specs/example.md",
  "checks": {
    "feature-cli": {
      "argv": ["python", "-m", "unittest", "tests.test_feature"],
      "cwd": ".",
      "timeout_seconds": 120,
      "kind": "test"
    }
  },
  "tasks": [
    {
      "id": "T1",
      "criteria": ["AC-1"],
      "checks": ["feature-cli"]
    }
  ]
}
```
<!-- ezpowers:plan:end -->
````

The block markers occur exactly once and contain one fenced JSON object.

## Plan Rules

- `schema_version` is `1`.
- `spec` is a contained project-relative path to a valid managed spec;
  absolute POSIX or Windows paths and drive-prefixed paths are invalid.
- `tasks` is a non-empty array with unique IDs that follow the same 1-64
  character identifier rule as spec criteria.
- Every task has a non-empty `criteria` array and `checks` array.
- Every spec criterion appears in exactly one task. Unknown, duplicate, or
  uncovered criteria fail validation.
- Optional top-level `checks` is an object of named checks. Every declared
  top-level check is used by a task.
- A task check is either a named check from the plan or config, or an inline
  check object that includes its own unique `id`.
- Check IDs do not collide across config, plan, and inline checks.
- A criterion with `integration: true` is mapped to at least one
  `integration`, `e2e`, or `smoke` check.

Named checks in `.ezpowers/config.json` provide stable project commands.
Plan-local checks are appropriate for feature-specific filters or oracles.
Avoid mapping the same config check as both a task check and a required project
check unless running it twice during `verify --all` is intentional.
When documentation status is ready, `ezpowers.docs` is a required project
check and must remain exact.

## Exact Check Contract

```json
{
  "id": "feature-cli",
  "argv": ["python", "-m", "unittest", "tests.test_feature"],
  "cwd": ".",
  "timeout_seconds": 120,
  "kind": "test"
}
```

- `argv` is a non-empty array of non-empty strings. It is passed directly to
  the operating system with no implicit shell.
- `cwd` is an existing project-relative directory contained by the project
  root; absolute POSIX or Windows paths and drive-prefixed paths are invalid.
- `timeout_seconds` is an integer from 1 through 86400.
- `kind` is `build`, `custom`, `e2e`, `integration`, `lint`, `security`,
  `smoke`, `static`, `test`, `typecheck`, or `visual`.
- `echo`, `true`, trivial zero-exit snippets, shell pipelines, redirections,
  opaque PowerShell command forms, `cmd /K`, path traversal, and synthetic PASS
  output are invalid.

Preserve the exact argv tokens established by repository evidence. Do not
convert a command to a shell string or drop a feature filter for convenience.

## UI And Delivery Work

Carry applicable constraints from `docs/ux/frontend-design.md` into the human
task description and bind their observable claims to real visual,
accessibility, browser, terminal, or native-window checks. Detect configured
visual lanes with:

```text
python .ezpowers/tools/frontend-visual-readiness.py --mode check
```

Use it as a gate only when the architecture or a prerequisite declares that
lane required. Missing tooling produces a prerequisite task, not a weaker
oracle.

## Validation And Handoff

Run:

```text
python .ezpowers/ezpowers.py validate --plan <plan-path> --json
```

Report the plan path, task order, exact criterion coverage, each exact check,
project required checks, and unresolved prerequisites. Continue to `execute`
only with a valid plan; the host chooses its own execution mechanics.
