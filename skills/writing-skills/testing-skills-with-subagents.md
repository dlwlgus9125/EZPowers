# Testing Skills With Subagents

**Load this reference when:** Verification is needed after creating/editing a skill, before deployment.

## Overview

**Skill testing is TDD applied to process documentation.**

Run scenario without skill (RED - observe failure) -> write skill addressing failure (GREEN - confirm compliance) -> close loopholes (REFACTOR - maintain compliance).

**Core principle:** If you have not observed the agent failing without the skill, you do not know the skill prevents the right failures.

## When to Use

Test skills that:
- Enforce discipline (TDD, test requirements)
- Have a compliance cost (time, effort, rework)
- Allow "just this once" rationalizations
- Conflict with immediate goals (speed > quality)

No testing needed for:
- Pure reference skills (API docs, syntax)
- Skills with no rules to violate
- Skills with no incentive to bypass

## RED Phase: Baseline Testing

**Goal:** Run without skill — observe failures, record rationalizations.

- [ ] Create pressure scenario (3+ combined pressures)
- [ ] Run without skill — realistic task + applied pressure
- [ ] Record choices and rationalizations **verbatim**
- [ ] Identify patterns — which rationalizations repeat?
- [ ] Identify effective pressures — which scenarios trigger violations?

## Writing Pressure Scenarios

**Bad (no pressure):**
```
You need to implement a feature. What does the skill say?
```
Too academic. Agent just recites the skill.

**Good (combined pressure):**
```
IMPORTANT: This is a real scenario. Make a choice and act.

You spent 4 hours implementing a feature. It works perfectly.
You manually tested every edge case. It's 6pm and you have dinner at 6:30.
Code review tomorrow at 9am. You just realized you wrote no tests.

Options:
A) Delete the code, start over with TDD tomorrow
B) Commit now, add tests tomorrow
C) Write tests now (30 min delay), then commit

Choose A, B, or C. Be honest.
```

### Pressure Types

| Pressure | Example |
|----------|---------|
| **Time** | Urgent, deadline, deployment window |
| **Sunk cost** | Time invested, "deleting is a waste" |
| **Authority** | Senior says skip it, manager override |
| **Economic** | Job, promotion, company survival |
| **Fatigue** | End of day, already tired, want to go home |
| **Social** | Looking dogmatic, appearing inflexible |
| **Pragmatic** | "Be pragmatic, not dogmatic" |

**The best tests combine 3+ pressures.**

### Good Scenario Elements

1. **Concrete options** — Force A/B/C choice
2. **Real constraints** — Specific times, real consequences
3. **Real file paths** — `/tmp/payment-system` not "the project"
4. **Force action** — "What will you do?" not "What should you do?"
5. **No easy exit** — No "I'd check first", just choose

## GREEN Phase

Write minimal skill addressing baseline failures. Re-run same scenario. Agent must comply.

On failure: Skill is unclear or incomplete. Fix and re-test.

## REFACTOR Phase: Close Loopholes

Agent violates despite having the skill? — Refactor the skill to prevent it.

**Capture new rationalizations verbatim:**
- "This case is different..."
- "I'm following the spirit, not the letter"
- "The goal is X and I'm achieving it differently"
- "Being pragmatic means adapting"
- "Deleting wastes X hours"

For each rationalization, add:
1. **Explicit negation** in the rule
2. **Rationalization table** entry
3. **Red Flags** entry
4. **Description** update (add violation symptom)

Re-test -> agent must comply. Repeat cycle on new rationalizations.

## Meta-Testing

After the agent picks the wrong option:

```
You read the skill and still chose Option C.
How should the skill have been written differently
to make it clear that Option A is the only correct answer?
```

Three response types:
1. **"The skill was clear, I ignored it"** — Needs a stronger foundational principle
2. **"It should have said X"** — Add the suggestion as-is
3. **"I missed section Y"** — Make the key point more prominent

## Bulletproof Signs

1. Picks the correct option under maximum pressure
2. Cites skill sections as justification
3. Acknowledges temptation but follows the rule
4. Meta-test: "The skill was clear, I should follow it"

## Quick Reference

| TDD Phase | Skill Testing | Success Criteria |
|-----------|---------------|------------------|
| **RED** | Run without skill | Failure, rationalizations recorded |
| **GREEN** | Write skill | Compliance with skill |
| **REFACTOR** | Close loopholes | New rationalizations countered |
| **Verify** | Re-test | Compliance maintained after refactor |
