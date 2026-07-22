---
doc_type: product
authority: canonical
status: active
---

# EZPowers PRD

EZPowers gives each target project a small, local workflow layer for facts that
vary by repository: settled requirements, architecture and plan artifacts,
exact completion commands, durable evidence, and resume state. It supports both
Claude Code and Codex while leaving implementation mechanics to the host.

## User Outcome

A user can install EZPowers into a project, describe or stress-test intent,
write traceable acceptance criteria, map them to real project checks, implement
with either supported host, and receive the same pass/fail completion verdict
from evidence stored in the repository. A new session can determine what is
fresh without trusting conversation memory.

## Product Boundary

EZPowers owns:

- project-local spec and plan schemas;
- check argv, working directories, kinds, and timeouts;
- fail-closed execution, stdout/stderr logs and hashes;
- binding evidence to spec/plan/config, the installed-kit identity, and the
  Git workspace;
- certification, staleness, tamper detection, and resume status;
- thin host adapters and optional frontend readiness detection.

Claude Code and Codex own code changes, shell UX, model choice, subagents,
worktrees, sandboxing, general retries, and review. EZPowers does not require an
external shared repository or executor.

## Success Conditions

- Installation is hash-verified, conflict-safe, and self-contained.
- Both hosts receive byte-identical local workflow instructions.
- Every acceptance criterion is mapped exactly once to executable checks.
- Integration criteria require a real integration, end-to-end, or smoke check.
- Merely validating a candidate plan cannot alter the active resume target.
- Task evidence is revalidated for resume guidance without becoming completion.
- Only fresh, complete, untampered all-scope evidence certifies completion.
- Removed orchestration concepts have no live reference or advertised flow.
