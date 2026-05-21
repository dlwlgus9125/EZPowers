---
doc_type: reference
authority: canonical
status: draft
---

# Project Structure

- `commands/`: public slash command controller prompts.
- `docs/reference/`: canonical workflow contracts and internal adapters.
- `agents/`: reviewer and workflow-runner agent procedures.
- `skills/`: independent skills and the Codex workflow adapter.
- `scripts/`: PowerShell and Python verification helpers.
- `harness-kit/`: versioned setup/reset setup local kit bundle.
- `evals/`: command and skill eval cases, baselines, and run outputs.
- `.claude-plugin/` and `.codex-plugin/`: plugin metadata.

Generated plugin mirrors under `plugins/` and eval run outputs under
`evals/results/runs/` are not source-of-truth files.
