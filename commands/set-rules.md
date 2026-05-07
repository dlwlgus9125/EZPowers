---
description: Design project rules through guided conversation
allowed-tools: [Bash, Read, Write, Grep, Glob, AskUserQuestion]
---

# /set-rules — Project Rules Design

Design coding rules, code structure guidelines, and architecture constraints through conversation. Rules are written to `docs/reference/conventions.md` as the single source of truth, then wired into CLAUDE.md (@import) and AGENTS.md (pointer).

Can be invoked at any time after /setup. Adapts to available information:
- After /setup: stack-based coding rules, test conventions, basic structure
- After /brainstorm: + architecture decisions, requirement constraints
- After /plan: + verification commands, module isolation points

## 1. Pre-flight

**Required** (stop if missing):
- `.harness/config.json` — if missing → "Run `/setup` first." and stop
- `AGENTS.md`

**Always read:**
- `CLAUDE.md`
- Existing `docs/reference/conventions.md` (if any — update mode)

**Optional enrichment** (use what's available):
- Latest spec in `docs/specs/` (architecture decisions, requirements)
- Latest plan in `docs/plans/` (SI, module isolation, verification commands)

## 2. Analysis

Analyze all available inputs and identify rule-worthy areas.

**Always available (after /setup):**
- config.json stack → stack-specific coding conventions
- config.json test strategy → test structure rules
- AGENTS.md Conventions → existing rules to formalize/expand
- AGENTS.md Boundaries → enforceable no-change zones
- Directory structure → layer boundary candidates, code organization

**If spec exists (after /brainstorm):**
- Architecture decisions → structural constraints
- Requirements → enforceable constraints

**If plan exists (after /plan):**
- Structural Invariants → rules with verification commands
- File structure mapping → module isolation rules

Present findings:

```
Based on project analysis:

Rule areas identified:
1. Code style       — [evidence: TypeScript + React stack detected]
2. Architecture     — [evidence: src/api/ and src/db/ separate layers]
3. Testing          — [evidence: unit + e2e strategy, jest configured]

Which areas should we design rules for? Remove, add, or confirm.
```

## 3. Interactive Rule Design

**One rule at a time.** For each confirmed area:

```
[Code style] — Rule proposal:

  Rule: No `any` type — use `unknown` and narrow with type guards
  Category: TypeScript convention
  Why: Prevents type-safety erosion across the codebase

  → Accept / Modify / Skip / Done with this area
```

For rules derived from plan SI (when available):

```
[Architecture] — Rule proposal:

  Rule: DB layer must not import from API layer
  Scope: src/db/
  Verification: `grep -r "from.*api/" src/db/` returns no matches
  Source: Plan SI-1

  → Accept / Modify / Skip / Done with this area
```

### Design principles:
- Each rule should be specific and actionable
- Include verification command when possible (grep, lint, test)
- Check existing AGENTS.md Conventions and CLAUDE.md for duplicates before proposing
- Group related rules by area
- Keep total rules concise — quality over quantity

### Path-scoped rules (optional):
If a rule only applies to specific directories (e.g., "API input validation" only for src/api/):

```
This rule seems specific to src/api/.
1. Add to shared conventions (applies everywhere)
2. Add as path-scoped .claude/rules/api.md (Claude Code only, conditional loading)
3. Both
```

Path-scoped rules go to `.claude/rules/` with `paths:` YAML frontmatter. Only offer when clearly directory-specific. Default: shared conventions.

## 4. File Generation

### Primary: `docs/reference/conventions.md` (SSOT)

```markdown
---
doc_type: reference
authority: canonical
status: active
---

# Project Conventions

## Code Style
- [accepted rules...]

## Architecture
- [accepted rules...]
- Verification: `[command]` (when available)

## Testing
- [accepted rules...]
```

### CLAUDE.md wiring

If not already present, add `@docs/reference/conventions.md` to the project CLAUDE.md:

```markdown
# Conventions
@docs/reference/conventions.md
```

### AGENTS.md update

Update Conventions section with pointer + summary:

```markdown
## Conventions
Coding rules: see `docs/reference/conventions.md` for full list.
- [1-line summary per area: e.g., "Code style: strict TypeScript, no any"]
```

### Optional: `.claude/rules/*.md` (path-scoped only)

Only created when the user explicitly chose path-scoped rules in Section 3. These contain ONLY the path-scoped rules, not duplicated from conventions.md.

```markdown
---
paths:
  - "src/api/**"
---

# API Rules
- All endpoints must validate input
- Use standard error response format
```

## 5. Completion

List created/updated files:
```
Created/Updated:
  - docs/reference/conventions.md (N rules across M areas)
  - CLAUDE.md (added @import)
  - AGENTS.md (updated Conventions pointer)
  [- .claude/rules/api.md (path-scoped, if any)]

Rules auto-load in Claude Code via CLAUDE.md @import.
Other agents access via AGENTS.md → docs/reference/conventions.md.
```

## Key Principles

- **One question at a time** — don't overwhelm
- **Prefer choices** — Accept/Modify/Skip for each proposal
- **SSOT** — conventions.md is the single truth, no duplication
- **Adapt** — use whatever information is available at the current stage
- **Quality over quantity** — few well-designed rules > many vague ones
