# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Identity

EZPowers is a personal Claude Code skill plugin.
- References 2 source projects for design patterns — **built fresh**, not copied
  - `C:\Working\EasyPowersHarness` (v0.7.7) — harness/execution structure reference
  - `C:\Working\EasyPowers` (v3.1.5) — skill pattern reference
- SDD (Spec-Driven Development) based: humans design and review, agents implement

## Main Flow

```
/setup → /design_architecture → /spec → internal pipeline audit → /prepare_execute → internal pipeline audit → /choice_execute
```

Codex discovery note: the Codex plugin manifest exposes EZPowers via skills
such as `$ezpowers:diagnose`, `$ezpowers:frontend-design`, and
`$ezpowers:verifyself`. The slash-style names in this document are command
documents under `commands/`; Codex is not expected to list each skill in the
host `/` palette. See `docs/reference/codex-plugin-discovery.md`.

| Command | Role |
|---------|------|
| `/setup` | Initialize project harness and install verified local kit |
| `/design_architecture` | Define architecture, test methodology, project structure, roadmap, and UI verification adapter |
| `/spec` | Deepen approved architecture into detailed feature specs |
| `internal pipeline audit` | Cross-stage completeness gate (D1-D9, mandatory before /prepare_execute and /choice_execute) |
| `/prepare_execute` | Spec → step decomposition + agent assignment |
| `/choice_execute` | Choose execution path (subagent / harness / inline) |
| `/choice_execute Path 2` | Delegate to EasyPowersHarness executor (plan → phase conversion + step execution) |

## Independent Utilities

| Name | Type | Role |
|------|------|------|
| `/set-rules` | command | Design coding rules through conversation → docs/reference/conventions.md |
| `/review` | command | Review changes (implementation completeness vs spec) |
| `/sync-docs` | command | Sync reference docs with codebase (standalone + suggested after /choice_execute) |
| `/eval` | command | Run eval suite, report scores by version |
| `/feedback` | command | Attach user scores to current session trace |
| `/reset_setup` | command | Reinstall verified local kit and migrate setup docs |
| `/maintain` | command | Route bug, refactor, and issue-response work |
| `/deploy` | command | Prepare release and deployment verification |
| `diagnose` | skill | 6-phase diagnosis loop (feedback-loop-first + post-mortem) |
| `grill-with-docs` | skill | Plan/design stress test with CONTEXT.md and ADR side effects |
| `improve-codebase-architecture` | skill | Find deepening opportunities (Module/Depth/Seam vocabulary) |
| `verifyself` | skill | CoVe (Chain-of-Verification) self-verification (6 dimensions) |
| `writing-skills` | skill | Meta-skill for writing new skills (TDD-based) |
| `frontend-design` | skill | Frontend design readiness and design-direction selection before UI implementation |
| `zoom-out` | skill | Raise abstraction one level (module map) |
| `caveman` | skill | Token-saving compressed communication mode |
| `handoff` | skill | Session handoff document for fresh agent continuation |
| `deep-interview` | skill | Socratic interview to clarify vague requests into actionable requirements |
| `ezpowers-workflow` | skill | Direct-invocation Codex adapter for EZPowers command documents |

## Directory Structure

```
.claude-plugin/       # plugin.json
commands/             # Slash commands (setup, design_architecture, spec, prepare_execute, choice_execute, maintain, deploy, reset_setup, set-rules, review, sync-docs, eval, feedback)
skills/               # Independent skills
  diagnose/
    SKILL.md          # 6-Phase diagnosis loop (feedback-loop-first + post-mortem)
    references/debugging-playbook.md
  grill-with-docs/
    SKILL.md          # Plan/design stress test with CONTEXT.md and ADR side effects
    references/context-format.md
  improve-codebase-architecture/
    SKILL.md          # Find deepening opportunities (Module/Depth/Seam vocabulary)
    references/architecture-language.md
    references/interface-design.md
    references/deepening.md
  verifyself/
    SKILL.md          # CoVe self-verification (6 dimensions)
  writing-skills/
    SKILL.md          # Skill-writing meta-skill (TDD-based)
    anthropic-best-practices.md
    testing-skills-with-subagents.md
  frontend-design/
    SKILL.md          # Frontend design readiness workflow
    references/frontend-design-readiness.md
  zoom-out/
    SKILL.md          # Raise abstraction (prompt-only)
  caveman/
    SKILL.md          # Token-saving compressed mode
  handoff/
    SKILL.md          # Session handoff document for fresh agent continuation
  deep-interview/
    SKILL.md          # Socratic interview to clarify vague requests into actionable requirements
  ezpowers-workflow/
    SKILL.md          # Direct-invocation Codex adapter for EZPowers command documents
agents/               # Plugin agents + prompt templates
  code-reviewer.md          # Plugin Agent — final code review (inherit, Read/Grep/Glob/Bash)
  security-reviewer.md      # Plugin Agent — security vulnerability scan (inherit, Read/Grep/Glob/Bash)
  wiring-reviewer.md        # Plugin Agent — full-feature wiring gate after harness execution
  workflow-contract-reviewer.md # Plugin Agent — workflow, utility, and skill contract review
  frontend-experience-reviewer.md # Plugin Agent — frontend design readiness review
  spec-reviewer.md          # Plugin Agent — spec document verification (sonnet, Read/Grep/Glob)
  architecture-reviewer.md  # Plugin Agent — architecture readiness verification (sonnet, Read/Grep/Glob)
  plan-reviewer.md          # Plugin Agent — plan document verification (sonnet, Read/Grep/Glob)
  workflow-runner.md        # Plugin Agent — scoped command runner for explicit skill chains
  implementer-prompt.md     # Template — implementation subagent (placeholder substitution)
  eval-diagnostician.md     # Plugin Agent — failing eval analysis + 1-line change proposal (opus, Read/Grep/Glob)
phases/               # Phase state tracking generated by /setup
docs/
  INDEX.md            # Document navigation map generated by /setup
  product/            # PRD and product docs slot
  reference/          # Architecture, protocol, schema, config, conventions slot
  decisions/          # ADR (3-condition gate: hard to reverse + surprising + tradeoff)
  ux/                 # UI projects only (optional)
  specs/              # Spec documents generated by /spec
  plans/              # Plan documents generated by /prepare_execute
  handoff-session{N}.md  # Generated by /handoff skill
phases/               # Phase directories generated by /choice_execute Path 2 (harness path)
hooks/
  hook-policy.json    # trace hook policy metadata; /setup --enable-traces creates active hooks
docs/reference/
  trace-hooks-template.json # opt-in trace hook template copied into projects by setup
harness_versions/
  changelog.jsonl     # append-only structured change log (date, version, diff, eval delta)
scripts/
  validate.py         # eval gate (pre-commit hook calls this)
  run_baseline.py     # eval runner + baseline writer
  run_skill_evals.py  # deterministic skill regression eval runner
  frontend-visual-readiness.py # frontend v2 visual readiness lane detector
  promote_trace.py    # trace → eval case converter
  model-router.py     # resolve model profiles to backend model selections
  context-injector.py # build/validate context injection blocks
  hashline-anchor.py  # create/verify sidecar line anchors for harness step files
  verify-step.py      # multi-dimensional step verification (structural/content/relational/command)
  verify-harness-kit.py # validate the bundled harness kit manifest
  shared.py           # shared constants/utilities for eval and verification scripts
  check-harness-docs.ps1 # non-Python harness contract check
  harness-convert.ps1 # non-Python plan-to-phase conversion helper
  harness-doctor.ps1  # non-Python /choice_execute Path 2 pre-flight helper
  harness-certify.ps1 # non-Python completion certificate gate
  harness-gate.ps1    # non-Python wiring gate executor
  harness-phase.ps1   # non-Python harness phase status/reset helper
  harness-run.ps1     # controlled /choice_execute Path 2 step runner with timeout/logging
  harness-smoke.ps1   # non-Python helper flow smoke check
  harness-resume-proof.ps1 # non-Python harness resume-proof generator
  harness-common.ps1  # shared PowerShell harness helpers sourced by other scripts
  lightpath-gate.ps1  # non-Python light-path gate (prepare/task/final scopes)
  smoke-plugin.ps1    # non-Python plugin smoke check
.githooks/
  pre-commit          # runs harness docs gate or validate.py by changed path
bin/
  trace.sh            # observation-only JSONL trace writer (called from hooks)
```

## Key Conventions

- **Canonical workflow contracts**: Use `docs/reference/domain-language.md`,
  `docs/reference/verification-contract.md`,
  `docs/reference/architecture-readiness-contract.md`, and
  `docs/reference/mattpocock-harness-adapter.md`, and
  `docs/reference/dispatch-protocol.md`, plus the command-specific contracts
  `docs/reference/setup-contract.md`,
  `docs/reference/reviewer-placement-contract.md`,
  `docs/reference/design-architecture-contract.md`,
  `docs/reference/frontend-design-contract.md`,
  `docs/reference/harness-kit-contract.md`,
  `docs/reference/ui-verification-adapter-contract.md`,
  `docs/reference/spec-contract.md`,
  `docs/reference/plan-contract.md`,
  `docs/reference/app-delivery-contract.md`,
  `docs/reference/model-routing-contract.md`,
  `docs/reference/pipeline-audit-contract.md`, and
  `docs/reference/harness-execution-contract.md` as the SSOT for workflow vocabulary,
  verification evidence, architecture readiness, Matt Pocock skill adaptation,
  reviewer dispatch, placement, verdicts, retries, workflow-runner scope, and long
  command templates. If command or agent wording conflicts
  with these references, preserve behavior and update the stale local wording.

- **Command lazy-loading**: EZPowers slash commands use default lazy-loading —
  descriptions appear in context for discoverability, but command bodies load
  only when the user explicitly invokes or another command delegates.
  Commands are workflow procedures, not reactive triggers; the model should not
  auto-invoke them. `/choice_execute Path 2` owns all EasyPowersHarness
  conversion/execution details; `/choice_execute` only delegates to it for Path 2.

- **Explicit skill chaining only** — skills are independent unless a command names a gate. `/spec`
  invokes `grill-with-docs` after `/design_architecture` approval and before requirement extraction.
  `/spec` and `/prepare_execute` dispatch `ezpowers:workflow-runner` for `internal pipeline audit`;
  `/choice_execute` dispatches it for `/sync-docs` after final verification. Diagnostic
  subagent (`agents/eval-diagnostician.md`) is internal-only (eval analysis) and is never called from user-facing commands.
- **Hooks: opt-in observation-only** — default: no active hooks in the plugin root. Activate via
  `/setup --enable-traces` when `/eval`, baseline measurement, or regression tracking is needed.
  Setup creates project-local `hooks/hooks.json` from `docs/reference/trace-hooks-template.json`.
  Traces are written to `${CLAUDE_PLUGIN_DATA}/traces/` (gitignored by default). Hooks must not alter
  model behavior — observe and log only. Forbidden: modifying tool I/O, blocking tool calls,
  injecting system commands. Allowed: append-only JSONL writes.
- **Keep docs lightweight** — place context where any agent can find it
- **Evidence-based verification** — "should work" is banned; prove with execution results
- **State assumptions explicitly** — declare assumptions before design/planning and get user confirmation
- **Architecture-first design** — capture ASRs, lifecycle, quality budgets, option tradeoffs, UI verification adapter, and ADR triggers before requirement extraction
- **Fully automated verification** — no user confirmation gates in the harness pipeline. e2e items without automated Verify commands are FAIL, not "manual batch". Code review uses tri-state verdicts (PASS / PASS_WITH_ISSUES / FAIL). Integration milestones require pipeline integration tests. GUI apps use multi-layer probes (process survival + stderr + window handle + optional vision oracle).

## Eval Gate

Harness-only prompt and doc changes for setup, design_architecture, spec,
prepare_execute, choice_execute, reset_setup, maintain, deploy, internal audit,
and strict execution run `scripts/check-harness-docs.ps1` and do not
invoke the Python eval gate. Other commits touching `commands/`, `agents/`,
skills, or skill-gate files run `scripts/validate.py`.
The commit is blocked if:
- Harness doc contracts fail the PowerShell harness docs gate
- Diff exceeds 3 lines per Better-Harness "one line at a time" rule
- `evals/` files modified in the same commit (isolation)
- Any golden eval codebase-invariant grader fails
- Optimization average regresses vs latest baseline
- Holdout average drops >5% vs latest baseline
- Added text contains banned vague expressions

Bypass (emergency only): `git commit --no-verify`

## Versioning

Before `git push`, always patch-bump the `version` field in `.claude-plugin/plugin.json`.
- Commit message: `chore: bump version to X.Y.Z`
- Minor/major bumps only on explicit user request

## Design Principles

1. **Don't get trapped by existing structure** — source projects are references; design new flows
2. **YAGNI** — don't build it unless it's needed now
3. **One question at a time** — don't overwhelm the user during design or spec
4. **Steering** — /setup generates documents that auto-inject project context into every step
