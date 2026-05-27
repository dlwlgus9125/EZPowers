# Debugging Playbook

Use this reference when the short `SKILL.md` needs more concrete tactics.

## Feedback Loop Options

Try the fastest deterministic loop that reaches the bug:

1. Failing unit, integration, or e2e test.
2. Curl or HTTP script against a dev server.
3. CLI invocation with fixture input and expected output.
4. Headless browser script with DOM, console, and network assertions.
5. Replay captured trace: HAR, event log, request payload, or saved state.
6. Throwaway harness that exercises one service or function with mocked
   dependencies.
7. Property or fuzz loop for intermittent wrong outputs.
8. `git bisect run` when the bug appeared between known commits.
9. Differential loop against old/new versions or two configs.
10. Human-in-the-loop script only as a last resort.

Improve the loop before debugging deeply: make it faster, sharper, and more
deterministic. For non-deterministic bugs, raise the reproduction rate with
loops, stress, seeded randomness, or narrowed timing windows.

If no loop can be built, stop and ask for reproducible access, captured
artifacts, or permission for temporary instrumentation. Do not guess.

## Confusion Format

```text
CONFUSION: [contradiction]
- Evidence A: [claim] (source: [file/log/tool])
- Evidence B: [claim] (source: [file/log/tool])

Options:
  A) Trust [source] because [reason]
  B) Trust [source] because [reason]
  C) Need more evidence: [specific check]
```

Use this when logs, specs, stack traces, or observed behavior disagree.

## Red Flags

Return to Phase 1 if any of these appear:

- "Let me just change X and see."
- "Quick fix now, investigate later."
- "Probably X."
- "Multiple fixes at once saves time."
- "Manual check is enough."
- "I already know the pattern, no need to read it."
- "One more try" after multiple failed attempts.

## Root Cause Tracing

Bugs often surface deep in the call stack. The instinct is to fix where the
error appears, but that treats the symptom.

**Core principle:** Trace the call chain backward until the original trigger is
found, and fix at the source.

### 5-Step Backward Trace

1. **Observe the symptom** — the exact error message or wrong output.
2. **Find the direct cause** — what code directly produces this?
3. **What called this?** — trace the call chain upward.
4. **Trace the passed values** — where does the wrong value originate?
5. **Find the original trigger** — the first point where correct behaviour
   diverges.

### Adding Stack Traces

When manual tracing is insufficient:

- Use `console.error()` in tests (loggers may be suppressed).
- Log **before** dangerous operations, not after.
- Include context: directory, cwd, environment variables, timestamps.

**Do not fix only where the error appears.** Trace backward until the original
trigger is found. After fixing at the root cause, add validation at each layer
via defense-in-depth.

## Defense-in-Depth Validation

When fixing a bug, adding validation in one place feels sufficient. But a
single check can be bypassed by other code paths, refactoring, or mocks.

**Core principle:** Validate at every layer the data passes through. Make the
bug structurally impossible.

### The 4 Layers

1. **Entry Point Validation** — reject obviously invalid input at the API
   boundary.
2. **Business Logic Validation** — verify data is appropriate for the current
   operation.
3. **Environment Guards** — prevent dangerous operations in specific contexts
   (e.g. refuse `git init` outside temp dir during tests).
4. **Debug Instrumentation** — capture context for forensic analysis.

### Applying the Pattern

1. Trace the data flow — where the wrong value originates and where it is
   consumed.
2. Map all checkpoints — every point the data passes through.
3. Add validation at each layer — entry, business, environment, debug.
4. Test each layer — verify Layer 2 catches what bypasses Layer 1.

**Do not stop at a single validation point.** Add checks at every layer.

## After Environmental Root Cause

If the root cause is environmental, external, or timing-related, document the
evidence, add appropriate handling such as retries/timeouts/messages, and add
monitoring or logging for future investigation.
