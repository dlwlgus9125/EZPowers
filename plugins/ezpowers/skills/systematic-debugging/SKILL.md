---
name: systematic-debugging
description: Use when encountering any bug, test failure, build failure, performance issue, integration issue, or unexpected behavior before proposing fixes.
---

# Systematic Debugging

Core rule:

```text
NO FIXES WITHOUT ROOT CAUSE INVESTIGATION FIRST
```

Read deeper tactics only when needed: [references/debugging-playbook.md](references/debugging-playbook.md), [root-cause-tracing.md](root-cause-tracing.md), [defense-in-depth.md](defense-in-depth.md).

## Required Flow

Complete each phase in order. Before moving on, write:

```text
Phase N complete: [what was found or confirmed]
Entering Phase N+1
```

For the first transition, this means the report must include `Phase 1 complete:`.

### Phase 1: Root Cause Investigation

Build or identify a feedback loop first: failing test, CLI reproduction, HTTP script, browser probe, trace replay, or throwaway harness.

Then gather evidence:
- Read the full error or stack trace.
- Reproduce consistently or state exactly why reproduction failed.
- Check recent diffs, config changes, dependency changes, and environment differences.
- Trace data flow to where the wrong value first appears.
- If evidence conflicts, surface `CONFUSION:` with both sides and resolve it before choosing.

Do not propose a fix before Phase 1 is complete.

### Phase 2: Pattern Analysis

Find similar working code in the repo. Read it completely. List material differences between the working pattern and the broken path, including dependency and config assumptions.

### Phase 3: Hypothesis Testing

State one hypothesis: `I believe X is the root cause because Y`.

Test one variable at a time. If the test fails, form a new hypothesis; do not stack fixes.

### Phase 4: Implementation

Write or identify the failing test before the fix. Implement one fix for the confirmed root cause. Verify the focused test and relevant regression checks.

## Stop Conditions

- After 3 failed fixes, suspect architecture and start an architecture discussion before fix number four.
- If the thought is "quick fix", "probably", "try one more thing", or "skip the test", return to Phase 1.
- Fix the source cause, not the symptom.
