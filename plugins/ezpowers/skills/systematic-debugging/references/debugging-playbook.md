# Systematic Debugging Playbook

Use this reference when the short `SKILL.md` needs more concrete tactics.

## Feedback Loop Options

Try the fastest deterministic loop that reaches the bug:

1. Failing unit, integration, or e2e test.
2. Curl or HTTP script against a dev server.
3. CLI invocation with fixture input and expected output.
4. Headless browser script with DOM, console, and network assertions.
5. Replay captured trace: HAR, event log, request payload, or saved state.
6. Throwaway harness that exercises one service or function with mocked dependencies.
7. Property or fuzz loop for intermittent wrong outputs.
8. `git bisect run` when the bug appeared between known commits.
9. Differential loop against old/new versions or two configs.
10. Human-in-the-loop script only as a last resort.

Improve the loop before debugging deeply: make it faster, sharper, and more deterministic. For nondeterministic bugs, raise reproduction rate with loops, stress, seeded randomness, or narrowed timing windows.

If no loop can be built, stop and ask for reproducible access, captured artifacts, or permission for temporary instrumentation. Do not guess.

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

## After Environmental Root Cause

If the root cause is environmental, external, or timing-related, document the evidence, add appropriate handling such as retries/timeouts/messages, and add monitoring or logging for future investigation.

