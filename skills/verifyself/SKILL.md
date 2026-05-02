---
name: verifyself
description: Use when the user wants to verify the agent's own proposal or judgment
---

# Verifyself

## Overview

Verify the agent's own proposals/judgments using the CoVe (Chain-of-Verification) pattern. Instead of subjective self-assessment, generate concrete verification questions, answer them independently, then compare against the original proposal.

**Core principle:** "Is this fact correct?" is answerable. "Did I think deeply enough?" is not. Convert the latter into the former.

## When to Use

- On `/verifyself` invocation
- `/verifyself [target]` — when a specific target is given

## Step 1: Identify Verification Target

**With argument:** Use the argument as target (read if file path, use directly if text)
**Without argument:** Use the most recent proposal/judgment from the current conversation. "Proposal/judgment" means: code implementation presented in a code block, design/architecture proposal, decision recommendation, or analysis conclusion — whichever is most recent. Exclude simple questions or information requests.

Show the target to the user:
```
Verification target:
---
[target content]
---
```

## Step 2: Classify Target Type

| Type | Indicators |
|------|-----------|
| **code** | Implementation, refactoring, bug fix, code design |
| **document** | Spec, plan, design doc, architecture |
| **judgment** | Recommendation, decision, analysis, opinion |

Default to "judgment" when ambiguous.

## Step 3: Generate 6-Dimension Verification Questions

Generate 1-2 verification questions per dimension.

### 1. Exploration Depth — Verified fact or unchecked assumption?
- code: "Does this function actually behave as [assumed]?"
- document: "Does the referenced document actually state [claim]?"
- judgment: "Is premise [X] of this claim factually true?"

### 2. Impact Scope — Did I consider everything affected?
- code: "What other files/modules depend on the changed component?"
- document: "What other documents reference this one?"
- judgment: "What other areas does this judgment affect?"

### 3. Alternative Consideration — Did I adopt the first idea without alternatives?
- code: "Can this be solved with a different approach?"
- document: "Is a different structure possible?"
- judgment: "What is the strongest counterargument to this position?"

### 4. Temporal Perspective — Will this hold up over time?
- code: "Will hardcoding/tight coupling/assumptions need to change in the future?"
- document: "Does this structure accommodate expanding requirements?"
- judgment: "Does this create unacknowledged future constraints?"

### 5. Context Alignment — Does this fit the project, not a vacuum design?
- code: "Do adjacent files in the same module follow the same pattern?"
- document: "Does this follow the project's existing documentation conventions?"
- judgment: "Is this consistent with the project's established direction?"

### 6. Evidence Sufficiency — Are key claims grounded in verifiable facts?
- code: "Can key claim [X] be verified in the codebase?"
- document: "Does the referenced document actually exist and contain the claimed content?"
- judgment: "Is the source/basis for claim [X] verifiable?"

For inapplicable dimensions: mark "N/A — [reason]" and move on.

## Step 4: Answer Each Question Independently

For each verification question:
1. **Do not reference the original proposal's conclusion** — judge from the question and evidence alone
2. code questions: Collect evidence via file reads and grep
3. document questions: Open and check referenced documents directly
4. judgment questions: Reason from verifiable facts and logic
5. If unanswerable: "Unverifiable — no evidence in proposal"

## Step 5: Compare + Verdict

| Verdict | Condition |
|---------|-----------|
| **FAIL** | Independent answer finds factual inconsistency with the proposal |
| **CONCERN** | Important fact discovered that the proposal does not mention |
| **PASS** | No inconsistencies or significant omissions |

When uncertain, use CONCERN (not PASS).

## Step 6: Output Report

```
## Verifyself Report

### 1. Exploration Depth
- Question: [question]
- Answer: [independent answer + evidence]
- Verdict: PASS | CONCERN | FAIL
- Evidence: [specific file:line, document section, factual basis]

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
- FAIL: N items
- CONCERN: N items
- PASS: N items
```

Rules:
- Include all 6 dimensions in fixed order (including N/A)
- No "seems correct", "likely fine" in Evidence — concrete facts only

## Step 7: Revision

**All PASS:** Output report only. No revision.

**FAIL or CONCERN present:**
1. FAIL: Revise proposal to match facts discovered during verification
2. CONCERN: Supplement missing information
3. PASS: Keep original

```
---
Revised proposal:
---
[revised content]
---
```

## After Verification

Wait for user response:
- **Approval** — Verification complete, proceed with (revised) proposal
- **`/verifyself` re-invocation** — Re-verify the revised proposal
- **Feedback** — Address feedback directly (no need to re-run all 6 dimensions)
