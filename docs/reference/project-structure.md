---
doc_type: reference
authority: generated
status: draft
---

# Project Structure

Maintained by `/design-architecture` and `/sync-docs`. Generated structure map.

- `skills/`: workflow-skill controllers (user-invoked) and independent skills.
- `docs/reference/`: canonical workflow contracts and supporting references.
- `docs/product/`, `docs/specs/`, `docs/plans/`, `docs/decisions/`: product
  contract, feature specs, plans, and ADRs.
- `docs/ux/`: project UI design readiness artifacts when UI is present.
- `agents/`: reviewer and workflow-runner agent procedures.
- `scripts/`: PowerShell and Python verification helpers, including the
  frontend visual readiness lane detector and the `check-repo.ps1` commit gate.
- `tests/`: Python unit tests for contracts and runners.
- `harness-kit/`: versioned setup/reset local kit bundle.
- `phases/`: generated harness phase state.
- `harness_versions/`: append-only harness change log.
- `.githooks/`: pre-commit gate wiring.
- `.claude-plugin/` and `.codex-plugin/`: plugin metadata.

The canonical contracts under `docs/reference/` own enforceable rules;
generated slots and the state files under `phases/` and `harness_versions/`
are derived and append-only, not hand-edited source.
