---
name: set-rules
description: Design project rules through guided conversation
disable-model-invocation: true
allowed-tools: [Bash, Read, Write, Grep, Glob, Agent, AskUserQuestion]
---

# /set-rules — Project Rules Design

Design coding rules, code structure guidelines, and architecture constraints through conversation. Rules are written to `docs/reference/conventions.md` as the single source of truth, then wired into CLAUDE.md (@import) and AGENTS.md (pointer).

Can be invoked at any time after /setup. Adapts to available information:
- After /setup: stack-based coding rules, test conventions, basic structure
- After /spec: + architecture decisions, requirement constraints
- After /prepare-execute: + verification commands, module isolation points

## 1. Pre-flight

**Required** (stop if missing):
- `.harness/config.json` — if missing → "Run `/setup` first." and stop
- `AGENTS.md`

**Always read:**
- `CLAUDE.md`
- `docs/reference/reviewer-placement-contract.md`
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

**If spec exists (after /spec):**
- Architecture decisions → structural constraints
- Requirements → enforceable constraints

**If plan exists (after /prepare-execute):**
- Structural Invariants → rules with verification commands
- File structure mapping → module isolation rules

Present findings and probe for tacit knowledge (two steps):

**Step A — Probe recurring issues:**

```
Based on project analysis:

Rule areas identified:
1. Code style       — [evidence: TypeScript + React stack detected]
2. Architecture     — [evidence: src/api/ and src/db/ separate layers]
3. Testing          — [evidence: unit + e2e strategy, jest configured]

Before we lock in these areas: What mistakes keep recurring in this project?
(e.g., "PRs often break the API contract", "people forget to add tests for edge cases")
```

Wait for the user's response. If they mention recurring issues, fold them into the area list (add new areas or enrich existing ones). If they say "none" or "looks good," proceed as-is.

**Step B — Confirm areas:**

```
Updated rule areas:
1. Code style       — [evidence: ...]
2. Architecture     — [evidence: ...]
3. Testing          — [evidence: ...]
4. Error handling   — [evidence: user reported recurring API contract breaks]

Which areas should we design rules for? Remove, add, or confirm.
```

### Budget notice

After the user confirms areas, display the rule budget:

```
Confirmed areas: {N}
Rule budget: ~20 rules total
(Claude Code effective instruction limit: 100-150; conventions.md shares space
with CLAUDE.md and other @imports. Fewer precise rules > many vague ones.)
```

If update mode (existing conventions.md has rules):
```
Existing rules: {M} | Remaining budget: ~{20-M}
```

Path-scoped rules in `.claude/rules/` are conditionally loaded and do NOT count against the main budget.

## 3. Interactive Rule Design

**One rule at a time.** For each confirmed area:

```
[Code style] — Rule proposal:

  Rule: No `any` type — use `unknown` and narrow with type guards
  Priority: important
  Why: Prevents type-safety erosion across the codebase
  Verification: `grep -rn ": any" src/ --include="*.ts"` returns no matches
  Example:
    BAD:  function parse(data: any) { return data.value; }
    GOOD: function parse(data: unknown) { if (isRecord(data)) return data.value; }

  → Accept / Modify / Skip / Done with this area
```

For rules derived from plan SI (when available):

```
[Architecture] — Rule proposal:

  Rule: DB layer must not import from API layer
  Priority: critical
  Scope: src/db/
  Why: Enforces layer isolation; prevents circular dependencies
  Verification: `grep -r "from.*api/" src/db/` returns no matches
  Source: Plan SI-1

  → Accept / Modify / Skip / Done with this area
```

### Priority tiers

Each rule gets one of three priority levels:
- **critical** — Violation breaks build, causes data loss, or creates security vulnerability. MUST have a Verification command.
- **important** — Degrades maintainability or consistency but doesn't break immediately.
- **advisory** — Best practice; deviations acceptable with justification.

### Design principles:
- Each rule must be specific and actionable (use "must" not "should")
- Include verification command for every rule when possible (grep, lint, test)
- Critical-priority rules MUST have a verification command
- For unverifiable rules: show `Verification: (manual review)`
- Include a BAD/GOOD example pair for code pattern rules; omit for structural rules where Verification already illustrates
- Check existing AGENTS.md Conventions and CLAUDE.md for duplicates before proposing
- Group related rules by area
- Respect the ~20 rule budget — propose only what matters most

### Area transition

When the user says "Done with this area," ask one bounded follow-up before moving on:

```
[Architecture] area complete (3 rules accepted).

Before moving to Testing: anything else for Architecture that I didn't propose?

→ Type a rule idea, or continue to next area
```

If the user adds something, give it the standard Accept/Modify/Skip treatment. If the user says nothing or continues, move on immediately.

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

### [critical]
- **No raw SQL in API handlers** — use query builder only
  - Why: Prevents SQL injection at the handler boundary
  - Verification: `grep -rn "db.query\|db.exec" src/api/` returns no matches
  - Example: BAD: `db.query("SELECT * FROM " + table)` / GOOD: `db.select().from(table)`

### [important]
- **No `any` type** — use `unknown` and narrow with type guards
  - Why: Prevents type-safety erosion across the codebase
  - Verification: `grep -rn ": any" src/ --include="*.ts"` returns no matches
  - Example: BAD: `data: any` / GOOD: `data: unknown`

### [advisory]
- **Prefer early return** — reduce nesting depth
  - Why: Reduces cognitive load when reading control flow

## Architecture

### [critical]
- **DB layer must not import from API layer**
  - Why: Enforces layer isolation; prevents circular dependencies
  - Verification: `grep -r "from.*api/" src/db/` returns no matches

## Testing
- [accepted rules with same structure...]
```

### Enforceable rule suggestion (optional)

If any accepted rules have `Priority: critical` AND a `Verification:` command, present:

```
{N} critical rules have verification commands.
These could be enforced as pre-commit hooks instead of relying on AI compliance:

  1. `No raw SQL in API handlers` — `grep -rn "db.query|db.exec" src/api/`
  2. `DB layer isolation` — `grep -r "from.*api/" src/db/`

Add these as pre-commit checks?
1. Yes — generate .githooks/pre-commit additions
2. No — keep as conventions only
3. Later — add TODO to AGENTS.md Boundaries (default)
```

Default: 3 (Later). Do not pressure toward hooks.

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

List created/updated files with budget summary:
```
Created/Updated:
  - docs/reference/conventions.md (N rules across M areas)
    Budget: N/~20 rules used (critical: X, important: Y, advisory: Z)
  - CLAUDE.md (added @import)
  - AGENTS.md (updated Conventions pointer)
  [- .claude/rules/api.md (path-scoped, if any — does not count against main budget)]

Rules auto-load in Claude Code via CLAUDE.md @import.
Other agents access via AGENTS.md → docs/reference/conventions.md.

To add more rules later: run `/set-rules` again (update mode).
To review rules against code: run `/review`.
```

## Key Principles

- **One question at a time** — don't overwhelm
- **Prefer choices** — Accept/Modify/Skip for each proposal
- **SSOT** — conventions.md is the single truth, no duplication
- **Adapt** — use whatever information is available at the current stage
- **Quality over quantity** — few well-designed rules > many vague ones
- **Budget-aware** — ~20 rule cap; fewer precise rules > many vague ones
- **Example-driven** — BAD/GOOD code pairs make rules unambiguous
- **Assertive language** — "must" not "should" (research: improves LLM compliance)
