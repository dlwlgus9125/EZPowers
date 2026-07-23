# 0003. Use an explicit asymmetric harness chain

## Status

Accepted on 2026-07-23.

## Context

Some users want to approve a feature once and leave while implementation,
rework, review, and QA continue. The ordinary v5 flow intentionally delegates
continuation and retry behavior to the host. Codex has a native goal
continuation mechanism, while Claude Code can use a project Stop hook. Adding
the same custom loop to both would duplicate Codex's native harness; relying
only on agent prose would not freeze acceptance inputs or prevent validation
theater.

The hard trade-off is between unattended progress and user control. Repeated
approval prompts strand an absent user's run, but unlimited self-approval lets
the implementer weaken checks, invent proof, or continue indefinitely.

## Decision

Add `harness-chain` as an explicit-only, project-installed skill. It first
configures repository-specific stage choices, QA triggers, and hard limits
through questions and one hash-bound configuration apply.

Each feature then requires:

1. settled staged spec, plan, and executable acceptance oracle;
2. a real baseline run plus a host-native independent oracle audit;
3. one human approval bound to all inputs and limits;
4. exactly one host continuation authority;
5. fresh verification, bound independent code review, conditional adversarial
   QA, and certification.

Codex uses one native goal and its Stop hook remains an observer/terminal
brake. Claude Code uses its project Stop hook as the sole continuation loop.
EZPowers does not own implementation tasks, model selection, worktrees, or a
generic retry strategy.

The runtime freezes chain config, project checks, spec, plan, oracle files, and
approval by SHA-256. A change becomes `NEEDS_REAPPROVAL`. Review receipts are
accepted only from the subagent ID bound by SubagentStart to a runtime
challenge. Validation/review/QA/continuation counters become terminal as soon
as an approved limit is reached.

## Consequences

- Ordinary `execute` remains lightweight and does not double Codex's native
  continuation behavior.
- An approved feature can proceed while the user is absent through recoverable
  product failures without manufacturing repeated approvals.
- The main agent cannot substitute its own “review complete” prose for a bound
  receipt, and passing checks cannot substitute for required review.
- A failed oracle audit cannot be retried against the same preview, and a
  failed product review requires changed repository content plus a new
  all-scope PASS before another review.
- Host trust, sandbox, login, secrets, billing, and external-system prompts
  remain outside EZPowers and may still interrupt an unattended run.
- Changing acceptance intent is deliberately expensive: it requires a new
  preview, oracle audit, and human approval rather than silently thawing the
  contract.
