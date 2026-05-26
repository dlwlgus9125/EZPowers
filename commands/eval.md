---
description: Run eval suite and report scores per version
allowed-tools: [Bash, Read, Write, Agent]
---

# /eval — Eval Suite Execution and Score Report

Run EZPowers eval cases and report scores per version. Can be invoked independently at any time.

<HARD-GATE>
When using the `--baseline` flag, the golden split must pass 100% before recording the baseline. Do not force-record a baseline with golden failures.
</HARD-GATE>

## Anti-Pattern: "Too few cases, eval isn't needed yet"

Even 4 cases make the regression guard work. Changes without measurement are not allowed. Deferring eval lets regressions accumulate.

## Usage

```
/eval                      # Run all splits, compact results
/eval <split>              # Single split (optimization | holdout | golden | honeypot)
/eval --case <case_id>     # Single case execution
/eval --baseline           # Record current scores as new baseline (golden 100% required)
/eval --diff <version>     # Compare against specified version baseline
/eval --live               # Reserved for future live slash-command execution; fail loudly until implemented
```

## Process Flow

```
Parse arguments
  -> Pre-flight checks (evals/ exists, plugin.json version)
  -> Collect cases (per split or single case)
  -> Call scripts/run_baseline.py
  -> Parse results
  -> Format output (per-split, per-stratum, regressions, capabilities)
  -> Verdict
```

## 1. Pre-flight Checks

Verify:
- `evals/` directory exists
- Read current version from `.codex-plugin/plugin.json` (fallback: `.claude-plugin/plugin.json`)
- Read `docs/reference/reviewer-placement-contract.md`
- Identify latest baseline file in `evals/results/baselines/`
- Default runner mode is `static`: deterministic graders run against current
  files and fixture data. Do not present static scores as live command quality.

If `evals/` directory is missing: "Run `/setup --with-evals` first." then stop.

## 2. Subcommand Execution

### 2-1. `/eval` (full run)

Run all splits:

```bash
python scripts/run_baseline.py --version <current_version> --mode static --splits optimization holdout golden honeypot
```

### 2-2. `/eval <split>`

Run a single split:

```bash
python scripts/run_baseline.py --version <current_version> --mode static --splits <split>
```

### 2-3. `/eval --case <case_id>`

Run a single case file. Resolve file path from `case_id`:
- `case_id` format: `<split>.<slug>.<seq>` (e.g., `golden.banned_expression_detection.001`)
- Recursively search under `evals/` for a matching `case_id` file

```bash
python scripts/run_baseline.py --version <current_version> --mode static --cases <resolved_path>
```

### 2-4. `/eval --baseline`

Record current scores as a new baseline.

**Hard gate**: Golden split must pass 100%. If golden has failures, block:
```
BLOCKED: golden must pass <total>/<total>. Currently <N>/<total> passing.
Resolve golden failures before recording baseline.
```

On pass:
```bash
python scripts/run_baseline.py --version <current_version> --mode static --baseline --splits optimization holdout golden honeypot
```

After recording, auto-update the "Last baseline" section in `evals/INDEX.md`.

### 2-5. `/eval --live`

Live mode is the future runner path that must execute the actual slash-command
workflow in a disposable target repo, then grade the produced artifacts and
trace. Until implemented, call:

```bash
python scripts/run_baseline.py --version <current_version> --mode live --splits golden
```

and report the explicit not-implemented failure. Do not silently downgrade live
mode to static mode.

### 2-6. `/eval --diff <version>`

Load baseline file `evals/results/baselines/<version>.json` and compare with current run results.

If baseline file missing: "Baseline `<version>` not found. Available: [list]".

## 3. Output Format

### 3-1. Per-split Pass Rate

```
## Split Summary

| Split | Pass | Total | Rate |
|-------|------|-------|------|
| golden | 7 | 7 | 100% |
| optimization | 18 | 30 | 60% |
| holdout | 5 | 8 | 63% |
| honeypot | 1 | 2 | 50% |
```

Cases that cannot be auto-run (mode=manual) are excluded from Total and shown separately:
```
Manual-only (requires live execution): 19 cases
```

Also print the runner mode:

```
Eval mode: static
```

### 3-2. Per-stratum Breakdown

```
## Stratum Breakdown

| Command | Pass | Auto | Manual | Rate |
|---------|------|------|--------|------|
| spec | 3 | 11 | 2 | 27% |
| prepare_execute | 4 | 7 | 1 | 57% |
| choice_execute | 1 | 3 | 10 | 33% |
| setup | 2 | 4 | 0 | 50% |
| ... | | | | |
```

### 3-3. Regressions vs Last Baseline (with `--diff`)

Show up to 3 cases that were PASS in the previous baseline but now FAIL:

```
## Top Regressions (vs 0.6.0)

1. golden.banned_expression_detection.001 — PASS → FAIL
2. optimization.greenfield_cli_tool.001 — PASS → FAIL
3. holdout.api_integration_ko.001 — PASS → FAIL
```

If no regressions: "No regressions."

### 3-4. New Capabilities

Show up to 3 cases that were FAIL but now PASS:

```
## New Capabilities (vs 0.6.0)

1. optimization.vague_spec_ko.004 — FAIL → PASS
2. optimization.simple_three_r_spec.001 — FAIL → PASS
```

### 3-5. Verdict

Final verdict at the end of all output:

```
## Verdict: PASS
```

**PASS conditions:**
- Golden split 100% pass (auto-runnable cases only)
- With `--diff`: no golden regressions + holdout average not dropped >10%

**FAIL conditions:**
- Golden has failed cases
- With `--diff`: golden regression or holdout >10% drop

```
## Verdict: FAIL
Reason: golden 6/7 -> banned-expression-detection FAIL
```

## Verification

Verify this command works correctly:
- `/eval golden` outputs results for the current golden cases
- `/eval --live` reports that live execution is not implemented
- `/eval --diff 0.6.0` outputs baseline comparison
- Output ends with `## Verdict: PASS` or `## Verdict: FAIL`

## Common Rationalizations

| Rationalization | Why It Doesn't Work |
|----------------|---------------------|
| "Only 1 golden failed, can we record baseline anyway?" | Golden is an inviolable invariant. Even 1 failure blocks recording. |
| "Ignore manual cases, just look at auto?" | Manual cases are excluded from pass rate Total but shown separately. Auto-ratio itself is an eval maturity indicator. |
| "Static passed, so live workflow is good?" | Static only proves contracts and fixtures. Live workflow quality requires `--mode live`, which is not implemented yet. |
| "No previous baseline, skip diff" | If first run, record with `--baseline` first. Per-split results are always shown even without diff. |
