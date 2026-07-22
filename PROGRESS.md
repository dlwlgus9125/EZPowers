# EZPowers Progress

## Current State

EZPowers v5.0.0 is finalized in the working tree on `main`. The 2026-07-22 independent audit
found that v4's external executor, plan-to-phase layer, reviewer fleet, model
routing, retry policy, and placeholder local kit duplicated host features or
were not self-contained. The live v5 implementation replaces them with one
standard-library Python runtime installed inside each target project.

The retained core is:

- optional `deep-interview` clarification and stress-test modes;
- architecture, frontend design, spec, and plan artifacts;
- project-specific argv checks and complete criterion coverage;
- real stdout/stderr logs, hashes, Git-workspace freshness, certification, and
  resume state, including revalidated task evidence;
- thin, opt-in Claude Code and Codex hook adapters sharing one core verdict.

Candidate plan validation is read-only. Execution explicitly activates its
resume target, and task evidence can guide resumption without ever replacing
fresh all-scope certification.

`frontend-design`, its non-installing readiness detector, the Codex-native HUD,
and product-code architecture analysis remain independent features. The HUD is
not part of project setup.

## Completed Item

`F11` in `feature_list.json`: the host-native, project-local v5 core is complete.
Every pre-v5 live component and every retained v5 component has a disposition
in the independent audit report.

## Evidence

Pre-change baseline on 2026-07-22:

- `python -m unittest discover -s tests`: 70 tests passed.
- `scripts/check-repo.ps1`: passed.
- `scripts/harness-runtime-smoke.ps1`: 14/14 passed, but the audit confirmed it
  used a blank external executor and hand-authored/fake evidence.
- `python scripts/verify-harness-kit.py`: passed, but the manifest installed
  README placeholders rather than the promised workflow.

Final v5 verification on 2026-07-22:

- `python -m unittest discover -s tests`: 82 tests passed in 237.180 seconds.
- `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/check-repo.ps1`:
  PASS.
- `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/harness-runtime-smoke.ps1`:
  PASS for real install -> validate -> unittest -> verify -> certify -> stale.
- `python scripts/verify-harness-kit.py`: v5 manifest valid.
- `python scripts/plugin_smoke.py --host both`: manifests accepted by Claude
  CLI and retained Codex project skills discovered in isolation.

## Remaining Candidates

Full screenshot generation and visual-diff execution are still outside the
core. The readiness detector continues to hard-gate those lanes only when the
target project already has suitable tooling or its plan explicitly adds it.
`deep-interview` trigger/mode and conditional CONTEXT/ADR behavior have static
skill-contract coverage, not a deterministic two-host model-behavior oracle.
Cryptographic hashes detect accidental or partial tampering but are not an
authenticity boundary against an attacker who can rewrite state, artifacts,
sidecars, and hashes together; hostile environments need repository/CI
permissions or signing outside this local core.
