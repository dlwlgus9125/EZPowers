---
name: diagnose
description: Reproduce, root-cause, fix, and verify bugs, failing tests or builds, integration failures, flaky behavior, performance regressions, and unexpected results. Use when the user invokes diagnose or says debug, fix, broken, failing, throwing, flaky, slow, repair, resolve, or make it pass. An explicit diagnose invocation or fix/debug request defaults to end-to-end fix completion; stop at analysis only when the user explicitly asks for explanation/root cause only or no changes.
---

# Diagnose

Drive a reported defect from an exact red signal to a verified source-cause
fix. Root cause is a milestone, not completion.

## Load and ground

Read `.ezpowers/contracts/engineering-practices-contract.md` when installed, or
the same contract under the EZPowers plugin's `docs/reference/` directory.
Read repository instructions, current Git state, relevant project
documentation, `CONTEXT.md` when present, applicable ADRs, and the code and
tests on the failing path.

Choose one mode once:

- **FIX-COMPLETE:** use when the user explicitly invokes this skill or asks to
  debug, fix, repair, resolve, make a failure pass, or otherwise restore
  working behavior. Own reproduction, diagnosis, regression coverage, the
  source-cause patch, cleanup, and verification. Do not ask for another
  authorization after the request already grants it.
- **ANALYSIS-ONLY:** use only when the user explicitly asks for root cause,
  explanation, investigation only, or no edits. Use read-only probes and
  existing tests. Stop before the first repository edit.

For a bare symptom report matched implicitly, begin read-only investigation.
Ask once before the first edit only when intent remains genuinely ambiguous.
After FIX-COMPLETE begins, intermediate findings are progress updates, not a
reason to hand the task back.

## Phase 1 — Build the red loop

Spend disproportionate effort on one fast, deterministic, agent-runnable
command that drives the real defect path and asserts the user's exact symptom.
Prefer, in order: an existing or new test at the real seam; HTTP/CLI script;
headless UI assertion; captured trace replay; throwaway harness; repeated
property/stress loop; automated bisection; or differential old/new execution.

Run the command and retain its invocation, exit result, and exact red signal.
Tighten it until unrelated setup is removed and the signal can distinguish the
broken behavior from the fixed behavior. For flaky defects, raise and record a
repeatable failure rate. For performance, record a comparable baseline and
threshold before changing code.

If no red-capable loop can be built, stop and list what was tried. Request the
specific access, captured artifact, or temporary instrumentation permission
needed to continue; do not guess.

## Phase 2 — Reproduce and minimise

Run the loop enough times to confirm it catches the reported defect rather than
a nearby failure. Remove inputs, callers, configuration, data, and steps one
at a time, rerunning after every cut. Keep only elements whose removal makes
the loop green. Preserve the original, unminimised scenario for final proof.

## Phase 3 — Find the first divergence

State 3-5 ranked, falsifiable hypotheses and the observation that separates
each one. Share the ranking as a non-blocking checkpoint and continue unless
the user pauses the work. Test one prediction at a time. Prefer debugger or
REPL inspection, then narrowly placed logs tagged with one unique
`[DEBUG-<token>]` prefix. Never log everything and grep.

Trace bad values and control flow backwards from the symptom to the earliest
point where actual state diverges from expected state. A nearby exception or
failing assertion is not the root cause without that trace.

## Phase 4 — Lock the regression

In FIX-COMPLETE mode, turn the minimised reproduction into a regression test
at the real call-site seam before changing product behavior. Record the red
regression signal and confirm that it fails for the intended reason.

If no honest automated test seam exists, do not add a shallow test. Keep the
red command or harness as the executable regression signal, continue the
authorized fix, and report the missing seam as an architectural follow-up
after the defect is fixed. Lack of a good seam does not cancel FIX-COMPLETE.

## Phase 5 — Fix and iterate

Apply the smallest change that corrects the first divergence rather than
masking its downstream symptom. Then run, in order:

1. the new regression test or executable minimal loop;
2. the original Phase 1 loop against the unminimised scenario;
3. nearby tests for the changed module and its callers.

If any signal remains red, treat the output as new evidence. Re-rank the
hypotheses, change one variable, and continue. Do not end the task after a
failed patch or a plausible explanation. After three failed patch experiments,
make no fourth speculative edit: rebuild the loop and hypothesis set first,
then continue only from a new falsifiable prediction.

## Phase 6 — Prove completion

FIX-COMPLETE finishes only when all applicable checks are true:

- the exact original symptom is green on the Phase 1 command;
- the regression signal was observed red before the fix and green after it;
- flaky/performance results meet the recorded repeated-run or measurement
  threshold;
- relevant module, caller, integration, and configured project checks pass;
- the diff contains the source-cause fix rather than only a test expectation,
  retry, suppression, timeout increase, or weakened assertion;
- all `[DEBUG-<token>]` instrumentation and throwaway artifacts are removed;
- the final diff is reviewed for unrelated or user-owned changes.

During an active EZPowers execution, run fresh all-scope verification and
certification; targeted green results are not completion evidence.

Do not stop FIX-COMPLETE at reproduction, hypotheses, root cause, a red
regression test, or the first green targeted test. End only with the verified
fix above or a concrete external blocker after safe in-scope alternatives are
exhausted. Name the exact missing access or state change when blocked.

## Report

Report these sections with repository evidence:

- **Symptom**
- **Feedback loop** — exact command, exit result, and observed signal
- **Minimal reproduction**
- **Hypotheses and evidence**
- **Root cause** — path, symbol, and first divergence
- **Mode** — FIX-COMPLETE or ANALYSIS-ONLY
- **Fix** — changed paths/symbols and why the change corrects the first
  divergence
- **Regression and verification** — red-before and green-after commands,
  original-symptom rerun, project checks, and certification when applicable
- **Remaining uncertainty**

Do not automatically invoke another workflow, create a canonical document, or
change harness-chain limits, receipts, or completion state.
