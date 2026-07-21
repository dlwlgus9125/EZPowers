---
doc_type: reference
authority: generated
status: draft
---

# Conventions

Maintained by `/set-rules`. Generated project conventions; edit through `/set-rules`.

- Use `AGENTS.md` as the cross-agent entry point.
- Keep progress in `PROGRESS.md` and active work in `feature_list.json`.
- Keep workflow-skill controllers short and move detailed rules into
  `docs/reference/`.
- Run unit tests and the repo gate (`scripts/check-repo.ps1`) before reporting
  done.
- Do not weaken Verify commands to make a change pass.
