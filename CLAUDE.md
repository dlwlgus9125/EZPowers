# Claude Code Guidance

EZPowers supports Claude Code and Codex from one repository. Its product value
is project-local specification, deterministic completion checks, durable
evidence, and resume state—not a second agent orchestrator.

## Workflow

```text
/ezpowers:setup
  -> /ezpowers:deep-interview          # optional session-only clarification
  -> /ezpowers:design-architecture     # when architecture is unsettled
  -> /ezpowers:spec
  -> /ezpowers:prepare-execute
  -> /ezpowers:execute
```

Codex uses `$ezpowers:<name>`. A project-local installation copies the same
skill bytes to `.claude/skills/` and `.agents/skills/`; each host discovers
those files through its own native mechanism.

| Skill | Responsibility |
|---|---|
| `setup` | Install or refresh the self-contained local kit and configure real checks |
| `deep-interview` | Turn vague intent into a clear, user-confirmed request in the current session |
| `design-architecture` | Record project boundaries and verification design |
| `spec` | Write settled decisions as machine-readable acceptance criteria |
| `prepare-execute` | Map every criterion exactly once to ordered tasks and checks |
| `execute` | Implement with native host features, then verify and certify |
| `frontend-design` | Produce frontend design readiness before UI implementation |
| `improve-codebase-architecture` | Find product-code module deepening opportunities |
| `hud` | Explicitly manage the global native Codex footer; plugin-only |

## Execution Boundary

Use Claude Code's native shell, subagents, worktrees, sandbox settings, hooks,
tests, and review facilities where appropriate. Do not add a parallel model
router, reviewer fleet, task graph, generic retry loop, phase conversion, or
external harness dependency. Do not infer Codex capabilities from Claude
Code behavior.

EZPowers completion is mechanical:

```text
python .ezpowers/ezpowers.py validate --plan <plan> --activate
python .ezpowers/ezpowers.py verify --plan <plan> --all --json
python .ezpowers/ezpowers.py certify --plan <plan> --json
python .ezpowers/ezpowers.py status --json
```

Activation is explicit at execution entry; ordinary spec/plan validation is
read-only. Only fresh, untampered, all-scope evidence can certify completion.
Optional project hooks adapt that same verdict to each host's distinct hook
schema.

## Repository Work

- Follow the reading order and preservation rules in `AGENTS.md`.
- Treat `docs/reference/*-contract.md` as canonical for installed workflow
  behavior.
- Keep host adapters thin and test both hosts independently.
- Do not install plugins, change global configuration, commit, or push without
  explicit user authorization.
- Run all verification commands in `AGENTS.md` for repository changes.
