---
name: diagnose
description: Use when encountering any bug, test failure, build failure, performance issue, integration issue, or unexpected behavior before proposing fixes. Also triggers on diagnose this, debug this, something is broken/throwing/failing, performance regression.
---

# Diagnose

Core rule:

```text
NO FIXES WITHOUT ROOT CAUSE INVESTIGATION FIRST
```

Read deeper tactics only when needed: [references/debugging-playbook.md](references/debugging-playbook.md).

Read `CONTEXT.md` for a domain mental model; check ADRs in `docs/decisions/`.

## Required Flow

Complete each phase in order. Before moving on, write `Phase 1 complete: [finding]`.

### Phase 1: Build a Feedback Loop

**This is the skill.** Spend disproportionate effort here. Be aggressive.

Build a fast, deterministic, agent-runnable pass/fail signal for the bug.
See [references/debugging-playbook.md](references/debugging-playbook.md) for
the 10 feedback loop options. Iterate: make it faster, sharper, more
deterministic.

For non-deterministic bugs, raise the reproduction rate until debuggable.

If no loop can be built, stop and say so. Ask for reproducible access,
captured artifacts, or permission for temporary instrumentation.

### Phase 2: Reproduce

Run the loop. Confirm the failure matches what the **user** described (not a
nearby failure), is reproducible, and the exact symptom is captured.

### Phase 3: Hypothesise

Generate **3-5 ranked hypotheses** before testing any. Each must be falsifiable:
"If X is the cause, then changing Y makes the bug disappear."

Show the ranked list to the user before testing. Proceed with your ranking if AFK.

### Phase 4: Instrument

Each probe maps to a prediction from Phase 3. Change one variable at a time.
Prefer debugger/REPL > targeted logs > never "log everything and grep".

**Tag every debug log** with `[DEBUG-xxxx]`. For performance: measure first,
bisect second.

### Phase 5: Fix + Regression Test

Write the regression test **before the fix** at the correct seam. Turn the
repro into a failing test, watch it fail, apply the fix, watch it pass, re-run
the Phase 1 loop.

If no correct seam exists, note it -- the architecture is preventing lockdown.

### Phase 6: Cleanup + Post-Mortem

- Re-run Phase 1 loop: original repro gone.
- All `[DEBUG-...]` instrumentation removed (grep the prefix).
- Correct hypothesis stated in the commit/PR message.

Then ask: **what would have prevented this bug?** If architectural, hand off to
`improve-codebase-architecture`.

## Stop Conditions

- After 3 failed fixes, suspect architecture and start an architecture
  discussion before fix number four.
- If the thought is "quick fix", "probably", "try one more thing", or "skip the
  test", return to Phase 1.
- Fix the source cause, not the symptom.
