---
name: verifyself
description: Use when the user invokes /verifyself or asks the agent to verify its own proposal, design, code judgment, or recommendation before proceeding.
---

# Verifyself

Verify the agent's own proposal with CoVe: plan verification questions, answer them independently from evidence, then compare against the original claim.

Read deeper examples only when needed: [references/verification-playbook.md](references/verification-playbook.md).

## Process

1. Identify the verification target.
   - With argument: use it as the target; if it is a file path, read the file before judging.
   - Without argument: use the most recent code block, design proposal, decision recommendation, or analysis conclusion. Ignore simple questions.

2. Show the target:

```text
Verification target:
---
[target content]
---
```

3. Classify it as `code`, `document`, or `judgment`. Default to `judgment` when ambiguous.

4. Generate verification questions across these dimensions:
   - Exploration depth
   - Impact scope
   - Alternative consideration
   - Temporal perspective
   - Context alignment
   - Evidence sufficiency

5. Answer each question independently.
   - Do not rely on the original conclusion.
   - For code, inspect files and behavior.
   - For documents, read the referenced documents.
   - For judgments, verify premises and counterarguments.
   - If evidence is missing, write `Unverifiable - [reason]`.

6. Compare answers to the target and assign `PASS | CONCERN | FAIL`.
   - `FAIL`: evidence contradicts the target.
   - `CONCERN`: important evidence or scope is missing.
   - `PASS`: no contradiction or significant omission.
   - When uncertain, use CONCERN.

7. Output `## Verifyself Report` with question, answer, verdict, and concrete evidence for each dimension. Evidence must cite files, lines, sections, tool output, or explicit facts.

8. Revise only if any verdict is `FAIL` or `CONCERN`. Preserve passed parts; correct contradicted claims and add missing context.
