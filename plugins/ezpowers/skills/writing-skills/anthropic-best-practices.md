# Skill Authoring Best Practices (Anthropic Guide Summary)

> Core summary of the Anthropic official skill authoring guide.

## Core Principles

### 1. Concise is Key

The context window is a shared resource. Skills share space with system prompts, conversation history, and other skill metadata.

**Default assumption:** Claude is already very smart. Only add context Claude does not know.

- "Is this explanation really needed?"
- "Doesn't Claude already know this?"
- "Does this paragraph justify its token cost?"

### 2. Set Appropriate Degrees of Freedom

| Freedom | When | Example |
|---------|------|---------|
| High | Multiple approaches valid, context-dependent | Code review process |
| Medium | Preferred pattern exists, minor variations OK | Template with parameters |
| Low | Task is fragile and error-prone | DB migration script |

### 3. Test with All Models

- Haiku: Does it provide enough guidance?
- Sonnet: Is it clear and efficient?
- Opus: Is it over-explained?

## Skill Structure

### Naming

Prefer gerund form: "Processing PDFs", "Testing code", "Writing documentation"
Avoid: Vague names like "Helper", "Utils", "Tools"

### Effective Descriptions

- Write in 3rd person (injected into system prompt)
- Be specific and include key terms
- Cover both what it does and when to use it
- No vague descriptions like "Helps with documents"

### Progressive Disclosure

- SKILL.md contains overview + pointers to detail files
- SKILL.md body under 500 lines
- Reference files linked at 1-depth from SKILL.md
- Reference files over 100 lines include a table of contents

## Workflows and Feedback Loops

- Break complex tasks into clear sequential steps
- Track progress with checklist patterns
- Verify -> fix -> repeat feedback loop

## Content Guidelines

- No time-sensitive information (date-based branching, etc.)
- Consistent terminology (one term per concept)
- Concrete examples (not abstract)

## Common Patterns

- **Template pattern:** Provide output format, calibrate strictness
- **Examples pattern:** Provide input/output pairs
- **Conditional workflow:** Guide at branch points

## Anti-Patterns

- No Windows paths (`\`) — always use forward slashes
- No excessive option presentation — provide defaults + escape hatch
- No tool installation assumptions — state dependencies explicitly
