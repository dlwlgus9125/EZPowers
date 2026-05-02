---
name: systematic-debugging
description: Use when encountering any bug, test failure, or unexpected behavior, before proposing fixes
---

# Systematic Debugging

## Overview

Random fixes waste time and create new bugs. Quick patches mask underlying issues.

**Core principle:** ALWAYS find root cause before attempting fixes. Symptom fixes are failure.

**Violating the letter of this process is violating the spirit of debugging.**

## The Iron Law

```
NO FIXES WITHOUT ROOT CAUSE INVESTIGATION FIRST
```

Do not propose a fix without completing Phase 1.

## When to Use

ANY technical issue:
- Test failures, bugs, unexpected behavior
- Performance problems, build failures
- Integration issues

**ESPECIALLY when:**
- Under time pressure (urgency tempts guessing)
- "One quick fix should do it"
- Multiple fixes already attempted
- The issue is not fully understood

**Don't skip when:**
- The issue looks simple (simple bugs still have root causes)
- In a hurry (systematic debugging is faster than guessing)

## The Four Phases

Complete each phase before proceeding to the next.

**Phase completion declaration:** Explicitly declare completion in this format before entering the next phase:

```
✓ Phase N complete: [1-line summary — what was found/confirmed]
→ Entering Phase N+1
```

Starting next-phase activities without this declaration is a violation.

### Phase 1: Root Cause Investigation

**Before attempting any fix:**

#### Step 0: Build a Feedback Loop

**This is the core skill.** Everything else is mechanical. With a fast, deterministic, agent-executable pass/fail signal, the cause can be found. Without one, no amount of code reading will solve it.

**Invest disproportionate effort here. Aggressively. Creatively. Refuse to give up.**

Build the feedback loop (try in this order):

1. **Failing test** — at the seam that reaches the bug (unit/integration/e2e)
2. **Curl / HTTP script** — run against a dev server
3. **CLI invocation** — run with fixture input, diff against known-good snapshot
4. **Headless browser script** — drive UI with Playwright/Puppeteer, assert DOM/console/network
5. **Replay captured trace** — save real network requests/payloads/event logs to disk, replay in isolation against code path
6. **Throwaway harness** — minimal subset of the system (one service, mocked deps) that exercises the buggy code path via a single function call
7. **Property / fuzz loop** — "sometimes wrong output" -> explore failure modes with 1000 random inputs
8. **Bisection harness** — bug appeared between two known states -> automate `git bisect run`
9. **Differential loop** — run same input through old vs new (or two configs), diff the output
10. **HITL script** — last resort. If a human must click, provide a structured script that guides them and captures output as feedback

**Refine the loop like a product:**
- Faster? (cache setup, skip unnecessary init, narrow test scope)
- Sharper signal? (assert on specific symptom, not just "no crash")
- More deterministic? (freeze time, seed RNG, isolate filesystem, freeze network)

A 30-second flaky loop is almost useless. A 2-second deterministic loop is a debugging superpower.

**Non-deterministic bugs:** Aim for **high reproduction rate**, not clean reproduction. Loop the trigger 100x, parallelize, add stress, shrink timing windows, inject sleeps. A 50% flake is debuggable; 1% is not — raise the rate.

**When loop construction fails:** Stop explicitly and declare it. List what was tried. Ask the user for: (a) access to an environment where it reproduces, (b) captured artifacts (HAR files, log dumps, core dumps, screen recordings), (c) permission for temporary production instrumentation. Do **not** form hypotheses without a loop.

---

1. **Read error messages carefully**
   - Read the entire stack trace
   - Note line numbers, file paths, error codes
   - Do not skip errors — they may contain the exact answer

2. **Reproduce consistently**
   - What are the exact reproduction steps?
   - Does it happen every time?
   - Cannot reproduce -> gather more data, do not guess

3. **Check recent changes**
   - `git diff`, recent commits
   - New dependencies, config changes, environment differences

4. **Collect evidence in multi-component systems**
   - Log data input/output at each component boundary
   - Run once to gather evidence of where it breaks
   - Then investigate that component

5. **Trace the data flow**
   - Where does the wrong value originate?
   - Walk the call stack backward to find the source
   - Fix at the source, not the symptom
   - Detailed backtracing techniques: see [root-cause-tracing.md](root-cause-tracing.md)

#### Confusion Management

Surface contradictory information explicitly during investigation:

```
CONFUSION: [describe the contradiction]
- Evidence A: [claim from Source A] (source: [file/log])
- Evidence B: [claim from Source B] (source: [file/log])

Options:
  A) Trust [Source A] — [reason]
  B) Trust [Source B] — [reason]
  C) Need more evidence — [what to check]
```

Use when:
- Error message contradicts actual behavior (e.g., "file not found" but file exists)
- Spec and code disagree
- Two logs show different states for the same variable
- Stack trace points to a line that looks correct
- Passes locally, fails in CI

Rules:
- Do not silently pick one side — surface the conflict
- If additional evidence can resolve it, try that first (Option C)
- Ask the user only after exhausting investigation options

### Phase 2: Pattern Analysis

**Find patterns before fixing:**

1. **Find similar code that works in the same codebase**
   - What code is similar to the broken code but works?

2. **Read reference implementations completely**
   - No skimming — read every line
   - Fully understand the pattern before applying

3. **List all differences between working and broken**
   - List even the smallest differences
   - No "this probably doesn't matter" assumptions

4. **Identify dependency, config, and environment assumptions**
   - Does it need other components?
   - What config and environment does it assume?

### Phase 3: Hypothesis and Testing

**Scientific method:**

1. **Form a single hypothesis**
   - "I believe X is the root cause because Y"
   - Write it down, be specific

2. **Test with minimal change**
   - Test with the smallest possible change
   - One variable at a time
   - Do not stack multiple fixes

3. **Verify**
   - Success -> Phase 4
   - Failure -> form new hypothesis (do not stack more fixes)

4. **When uncertain**
   - Admit "I don't know X"
   - Do not pretend to know
   - Ask for help or investigate further

### Phase 4: Implementation

**Fix the root cause, not the symptom:**

1. **Write a failing test case** (before the fix)
   - Simplest possible reproduction
   - Automate if possible
   - Must exist before the fix

2. **Implement a single fix**
   - Only the identified root cause
   - One change at a time
   - No "while I'm at it" improvements, no bundled refactoring

3. **Verify the fix**
   - Does the test pass?
   - Do other tests still pass?
   - Is the issue actually resolved?

4. **After 3+ failed fixes — STOP**
   - Count fix attempts
   - **3+ failures: suspect the architecture**
   - Do not attempt Fix #4 without an architecture discussion

5. **Signs of architectural problems:**
   - Each fix reveals new shared-state/coupling issues elsewhere
   - The fix requires "massive refactoring"
   - Each fix creates new symptoms elsewhere
   - STOP and question the foundation: is the pattern itself sound? Are we continuing out of inertia?
   - **Discuss with the user before proceeding**

## Red Flags — STOP

Return to Phase 1 if any of these thoughts arise:
- "Let me just change X and see if it works"
- "Quick fix now, investigate later"
- "Change several things at once and test"
- "Skip tests, verify manually"
- "Probably X, let me fix it"
- "Don't fully understand but this might work"
- "The pattern says X but I'll apply it differently"
- "Key issues: [list of fixes without investigation]"
- Proposing solutions before tracing data flow
- **"Let me try one more thing" (after 2+ failed attempts)**
- **Each fix reveals new problems elsewhere**

**ALL of these mean: STOP. Return to Phase 1.**

**3+ fix failures: suspect the architecture (see Phase 4.5)**

## Your Human Partner's Signals

Watch for these redirections:
- "That won't work, will it?" — assumed without verifying
- "Can you show me that?" — should have collected evidence
- "Stop guessing" — proposing fixes without understanding
- "Think about it properly" — question the root cause, not the symptom
- "Are we stuck?" (frustration) — the approach is not working

**On any of these signals: STOP. Back to Phase 1.**

## Common Rationalizations

| Excuse | Reality |
|--------|---------|
| "Simple issue, no process needed" | Simple issues still have root causes. The process is fast for simple bugs. |
| "Too urgent, no time" | Systematic debugging is faster than guessing. |
| "Try one fix then investigate" | The first fix sets the pattern. Do it right from the start. |
| "Tests after the fix is confirmed" | A fix without tests does not last. |
| "Multiple fixes at once saves time" | Cannot isolate what worked. Introduces new bugs. |
| "Reference is too long, apply the pattern loosely" | Partial understanding guarantees bugs. Read completely. |
| "I can see the problem, let me fix it" | Seeing a symptom != understanding root cause. |
| "One more try" (after 2+ failures) | 3+ failures = architectural problem. Question the pattern, do not fix again. |

## Quick Reference

| Phase | Key Activities | Success Criteria |
|-------|---------------|------------------|
| **1. Root Cause** | Read errors, reproduce, check changes, collect evidence | Understand WHAT and WHY |
| **2. Pattern** | Find working examples, compare | Differences identified |
| **3. Hypothesis** | Form theory, test minimally | Confirmed or new hypothesis |
| **4. Implementation** | Write test, fix, verify | Bug resolved, tests pass |

## When Process Reveals "No Root Cause"

When systematic investigation reveals the issue is environmental, timing-related, or external:

1. The process is complete
2. Document the investigation
3. Implement appropriate handling (retries, timeouts, error messages)
4. Add monitoring/logging for future investigation

**But:** 95% of "no root cause" cases are incomplete investigations.

## Supporting Techniques

Available in this directory:

- **`root-cause-tracing.md`** — Trace the call stack backward to find the original trigger
- **`defense-in-depth.md`** — Add multi-layer validation after discovering the root cause

## Real-World Impact

Debugging session experience:
- Systematic approach: fix in 15-30 minutes
- Guessing approach: 2-3 hours of flailing
- First-attempt fix success rate: 95% vs 40%
- New bugs introduced: near zero vs frequent
