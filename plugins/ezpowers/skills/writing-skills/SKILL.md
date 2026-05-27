---
name: writing-skills
description: Use when creating new skills, editing existing skills, or verifying skills work before deployment
---

# Writing Skills

## Overview

**Skill authoring is TDD applied to process documentation.**

**Core principle:** If you have not observed the agent failing without the skill, you do not know the skill teaches the right thing.

**Official guidance:** See [anthropic-best-practices.md](anthropic-best-practices.md) for the Anthropic official guide.

## What is a Skill?

**Skill:** A reference guide to verified techniques, patterns, and tools.

- **Skills are:** Reusable techniques, patterns, tools, references
- **Skills are NOT:** Narratives of how a problem was solved once

## TDD Mapping for Skills

| TDD Concept | Skill Creation |
|-------------|----------------|
| **Test case** | Subagent pressure scenario |
| **Production code** | Skill document (SKILL.md) |
| **Test fails (RED)** | Agent violates rules without skill (baseline) |
| **Test passes (GREEN)** | Agent complies with skill present |
| **Refactor** | Close loopholes while maintaining compliance |
| **Write test first** | Run baseline scenario before writing skill |
| **Watch it fail** | Record agent rationalizations verbatim |
| **Minimal code** | Write minimal skill addressing specific violations |
| **Watch it pass** | Confirm agent now complies |
| **Refactor cycle** | New rationalization -> counter -> re-verify |

## Skill Types

| Type | Description | Example |
|------|-------------|---------|
| **Technique** | Concrete method with steps | diagnose |
| **Pattern** | Mental model for a problem | flatten-with-flags |
| **Reference** | API docs, syntax, tool reference | office docs |

## Directory Structure

```
skills/
  skill-name/
    SKILL.md              # Main reference (required)
    supporting-file.*     # Only when needed
```

### File Organization Patterns

**Self-contained** — All content inline in SKILL.md:
```
defense-in-depth/
  SKILL.md    # Everything inline
```
When: Content is short and needs no separate reference

**With reusable tool** — Reusable scripts/utilities:
```
condition-based-waiting/
  SKILL.md    # Overview + patterns
  example.ts  # Working helpers to adapt
```
When: Tool contains reusable code

**With heavy reference** — 100+ line reference material:
```
pptx/
  SKILL.md       # Overview + workflows
  pptxgenjs.md   # 600 lines API reference
  scripts/       # Executable tools
```
When: Reference is too large to inline

## SKILL.md Structure

### Frontmatter (YAML)

- `name`: Letters, numbers, hyphens only (no special characters)
- `description`: 3rd person, starts with "Use when...", describe trigger conditions only
  - **Never summarize the skill's workflow/process** (see CSO)

```markdown
---
name: skill-name
description: Use when [specific triggering conditions]
---

# Skill Name

## Overview
Core principle in 1-2 sentences.

## When to Use
List of symptoms/situations. Include when NOT to use.

## Core Pattern
Before/after comparison or core flow.

## Quick Reference
Table or list for quick scanning.

## Common Mistakes
Frequent errors + fixes.
```

## Claude Search Optimization (CSO)

### Layer 1: Description Field Rules

- 1-2 sentences, <120 words
- Start with "Use when..."
- Trigger conditions and searchable keywords only
- Exclude workflow steps, outputs, process verb lists
- Optionally add "Not for..." anti-triggers
- **CSO self-test:** If reading only the description lets you attempt the skill workflow -> rewrite it

```yaml
# BAD: workflow summary — Claude may follow this instead of the body
description: Use when executing plans - dispatches subagent per task with code review

# GOOD: trigger conditions only
description: Use when executing implementation plans with independent tasks
```

**Why it matters:** When the description summarizes the workflow, Claude creates a shortcut path following the description instead of the body.

### Keyword Coverage

Use words Claude will search for:
- Error messages: "Hook timed out", "ENOTEMPTY", "race condition"
- Symptoms: "flaky", "hanging", "zombie", "pollution"
- Synonyms: "timeout/hang/freeze", "cleanup/teardown/afterEach"
- Tools: Actual commands, libraries, file types

### Naming

- Active voice, verb-first: `creating-skills` (not `skill-creation`)
- No generic names: `condition-based-waiting` (not `async-test-helpers`)
- Gerund (-ing) fits processes well

### Cross-Referencing Rules

```markdown
# GOOD: requirement marker + skill name only
**REQUIRED SUB-SKILL:** Use test-driven-development
**REQUIRED BACKGROUND:** You MUST understand diagnose

# BAD: path reference — ambiguous
See skills/testing/test-driven-development

# BAD: @ link — loads immediately, wastes context
@skills/testing/test-driven-development/SKILL.md
```

**No @ links because:** `@` syntax loads files immediately, consuming context budget before needed.

### Token Efficiency

| Skill type | Target |
|-----------|--------|
| Frequently loaded skills | <200 words |
| Others | <500 words |

Techniques: Delegate details to `--help`, deduplicate via cross-references, one excellent example beats many mediocre ones.

## Flowchart Usage

**Use when:**
- Non-obvious decision points
- Process loops that may exit too early
- "A vs B when to use" decisions

**Do not use when:**
- Reference material -> table/list
- Code examples -> markdown blocks
- Linear instructions -> numbered list

## Code Examples

**One excellent example > many mediocre ones**

Language selection guide:
- Test techniques -> TypeScript/JavaScript
- System debugging -> Shell/Python
- Data processing -> Python

Good examples: Complete and runnable, comments explaining WHY, extracted from real scenarios.
Bad examples: 5+ language implementations, fill-in-the-blank templates, contrived scenarios.

## RED-GREEN-REFACTOR for Skills

### RED: Test Without Skill

Run pressure scenario via subagent without the skill:
- What choices did the agent make?
- What rationalizations did the agent give? (Record verbatim)
- What pressure triggered the violation?

### GREEN: Write Minimal Skill

Write minimal documentation addressing specific violations found in RED. Re-run -> agent must comply.

### REFACTOR: Close Loopholes

New rationalization found -> add explicit counter. Re-test. Repeat until robust.

**Testing methodology:** See [testing-skills-with-subagents.md](testing-skills-with-subagents.md).

## Testing All Skill Types

### Discipline-Enforcing Skills (rules/requirements)

**Test with:**
- Academic questions: Does the agent understand the rules?
- Pressure scenarios: Does the agent comply under stress?
- Combined pressure: Time + sunk cost + fatigue combined

**Success:** Rule compliance under maximum pressure

### Technique Skills (methodology)

**Test with:**
- Application scenarios: Does the agent apply the technique correctly?
- Variant scenarios: Does it handle edge cases?
- Insufficient information tests: Are there gaps in the instructions?

**Success:** Successful application of technique to new scenarios

### Pattern Skills (mental models)

**Test with:**
- Recognition scenarios: Does the agent recognize when to apply the pattern?
- Application scenarios: Can it use the mental model?
- Counterexamples: Does it know when NOT to apply?

**Success:** Correct identification of when/how to apply

### Reference Skills (docs/API)

**Test with:**
- Search scenarios: Does the agent find the right information?
- Application scenarios: Does it use what it found correctly?
- Gap tests: Are common use cases covered?

**Success:** Correctly find and apply reference information

## Bulletproofing Against Rationalization

### Close Every Loophole Explicitly

Do not just state the rule — explicitly forbid specific workarounds:

```markdown
Wrote code before the test? Delete it. Start over.

**No exceptions:**
- Do not keep it "for reference"
- Do not "fix" it while writing the test
- Delete means delete
```

### Counter "Spirit vs Letter"

```markdown
**Violating the letter of the rules is violating the spirit of the rules.**
```

Block the entire class of "I'm following the spirit" rationalizations.

### Build a Rationalization Table

Put every rationalization captured in baseline testing into a table:

```markdown
| Rationalization | Reality |
|-----------------|---------|
| "Too simple to need tests" | Simple code breaks too. Test takes 30 seconds. |
| "Will test later" | Tests that pass later prove nothing. |
```

### Build a Red Flags List

```markdown
## Red Flags — STOP
- Writing code before test
- "I already tested manually"
- "I'm following the spirit, not the letter"
- "This case is different..."
-> All of these: delete and start over.
```

## Anti-Patterns

### Narrative Example
"In the 2025-10-03 session, an empty projectDir..." — Too specific, not reusable

### Multi-Language Dilution
example-js.js, example-py.py — Mediocre quality, maintenance burden

### Code in Flowcharts
`step1 [label="import fs"]` — Cannot copy, hard to read

### Generic Labels
helper1, step3, pattern4 — Use meaningful names

## Common Rationalizations

| Rationalization | Reality |
|-----------------|---------|
| "The skill is obviously clear" | Clear to you != clear to the agent. Test it. |
| "It's just a reference" | References have gaps too. Test with search scenarios. |
| "Testing is overkill" | Untested skills always have issues. 15 min saves hours. |
| "Will test when there's a problem" | Problem = agent can't use it. Test before deployment. |
| "Testing is boring" | Debugging bad skills in production is more boring. |
| "I'm confident" | Overconfidence guarantees issues. Test anyway. |
| "Academic review is enough" | Reading != using. Test with application scenarios. |
| "No time to test" | Untested deployment wastes more time later. |

## STOP: Before Moving to Next Skill

Complete the deployment process after writing each skill.

**Do not:**
- Batch-create multiple skills without testing
- Move to the next skill before verifying the current one
- Skip testing because "batching is more efficient"

## Checklist

**RED Phase:**
- [ ] Create pressure scenario (discipline skills: 3+ combined pressures)
- [ ] Run without skill — document baseline
- [ ] Identify rationalizations/failure patterns

**GREEN Phase:**
- [ ] Frontmatter: name + description (max 1024 chars)
- [ ] Description: starts with "Use when...", triggers only, no workflow summary
- [ ] Minimal skill addressing specific baseline failures
- [ ] Re-run with skill — confirm agent compliance

**REFACTOR Phase:**
- [ ] Identify new rationalizations
- [ ] Add explicit counters
- [ ] Update rationalization table + Red Flags
- [ ] Re-test — repeat until robust

**Quality:**
- [ ] Keyword coverage (errors, symptoms, tools)
- [ ] Commit
