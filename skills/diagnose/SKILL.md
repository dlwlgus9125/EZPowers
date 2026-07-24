---
name: diagnose
description: Diagnose bugs, failing tests or builds, integration failures, performance regressions, and unexpected behavior by establishing a reproducible root cause before proposing fixes. Use when the user says diagnose, debug this, broken, failing, throwing, flaky, or slow; stop at evidence when only diagnosis was requested, and fix only when the request authorizes changes.
---

# Diagnose

Establish the root cause before changing product behavior.

## Load and ground

Read `.ezpowers/contracts/engineering-practices-contract.md` when installed, or
the same contract under the EZPowers plugin's `docs/reference/` directory.
Read repository instructions, current Git state, relevant project
documentation, `CONTEXT.md` when present, applicable ADRs, and the code and
tests on the failing path.

Classify the request before acting:

- **Diagnosis only:** use existing read-only probes and tests. Do not edit
  product code or tests. Ask before adding repository-local instrumentation or
  a reproduction harness.
- **Diagnosis and fix:** investigate first, then make only the authorized fix
  and regression-test changes.

## Investigate

1. Build or identify one fast, deterministic, agent-runnable command that can
   go red on the user's exact symptom. Run it and retain its real output.
2. Reproduce the reported failure, then minimise inputs, configuration, and
   callers while preserving the symptom.
3. State 3-5 ranked, falsifiable hypotheses and the observation that would
   distinguish each one. Share the ranking as a non-blocking checkpoint.
4. Test one prediction at a time. Prefer debugger or REPL inspection, then
   narrowly tagged logs. Measure performance regressions before changing code.
5. Trace incorrect values and control flow backwards to the first divergence.
   Do not call a nearby exception or failing assertion the root cause without
   that trace.

If no red-capable loop can be built, stop and list what was tried. Request the
specific access, captured artifact, or temporary instrumentation permission
needed to continue; do not guess.

## Fix only when authorized

When the request includes a fix, turn the minimal reproduction into a failing
regression test at the real interface seam before changing behavior. If no
honest test seam exists, record that architectural finding instead of adding a
shallow test that cannot catch the bug.

Apply the smallest source-cause fix, rerun the minimal and original
reproductions, then run the applicable project checks. During an active
EZPowers execution, only fresh all-scope verification and certification can
establish completion.

After three failed fix attempts, stop changing code and reassess the
hypotheses and test seam. Do not spend another attempt on an unmeasured guess.
Remove temporary tagged instrumentation and throwaway artifacts before
finishing.

## Report

Report these sections with repository evidence:

- **Symptom**
- **Feedback loop** — exact command, exit result, and observed signal
- **Minimal reproduction**
- **Hypotheses and evidence**
- **Root cause** — path, symbol, and first divergence
- **Action boundary** — diagnosis only or diagnosis and fix
- **Regression and verification** — commands and results, when applicable
- **Remaining uncertainty**

Do not automatically invoke another workflow, create a canonical document, or
change harness-chain limits, receipts, or completion state.
