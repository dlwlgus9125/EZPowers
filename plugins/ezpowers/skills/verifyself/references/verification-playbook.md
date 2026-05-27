# Verifyself Playbook

Use this reference when the short `SKILL.md` is not enough to design questions or output the full report.

## Question Patterns

| Dimension | Code | Document | Judgment |
| --- | --- | --- | --- |
| Exploration depth | Does the function actually behave as assumed? | Does the document state the cited claim? | Is premise X factually true? |
| Impact scope | What modules depend on this component? | What docs reference this one? | What downstream decision changes if this is wrong? |
| Alternative consideration | Is there a smaller or existing-code approach? | Would another structure fit better? | What is the strongest counterargument? |
| Temporal perspective | Does this hardcode a future constraint? | Can this format expand? | Does this create future lock-in? |
| Context alignment | Do adjacent files use this pattern? | Does this match repo conventions? | Is this consistent with project direction? |
| Evidence sufficiency | Can claim X be verified in code or tests? | Does the referenced file exist? | Is the source of claim X inspectable? |

Mark inapplicable dimensions as `N/A - [reason]`, but keep the fixed order.

## Report Template

```markdown
## Verifyself Report

### 1. Exploration Depth
- Question: [question]
- Answer: [independent answer]
- Verdict: PASS | CONCERN | FAIL
- Evidence: [file:line, document section, command output, or factual basis]

### 2. Impact Scope
...

### 3. Alternative Consideration
...

### 4. Temporal Perspective
...

### 5. Context Alignment
...

### 6. Evidence Sufficiency
...

### Summary
- FAIL: N
- CONCERN: N
- PASS: N
```

## Revision Rule

- All PASS: output the report only.
- Any FAIL: revise contradicted claims to match evidence.
- Any CONCERN: add missing scope, caveat, or evidence requirement.
- Never use "seems correct" or "probably fine" as evidence.

