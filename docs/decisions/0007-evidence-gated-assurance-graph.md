# ADR 0007: Evidence-gated assurance graph and safe parallel verification

- Status: accepted
- Date: 2026-08-25
- Decision owners: EZPowers maintainers
- Related: `docs/reference/architecture.md`,
  `docs/reports/graph-engineering-paper-evaluation-2026-08-25.md`

## Context

EZPowers v5.6 validates criterion coverage and records strong immutable check
evidence, but it does not make task dependencies machine-readable. Its status
surface reports flat reasons, and all checks execute serially even when a
small, measured subset is independent. The Graph Engineering survey describes
typed workflow relations, versioned provenance, replayable state, fault
localisation, and structural evaluation as useful system-level disciplines.
It does not provide an integrated implementation or evidence that its broader
agent-organisation proposals improve EZPowers.

The existing product boundary is deliberate: Claude Code or Codex owns
implementation, subagents, model choice, worktrees, and retry decisions.
EZPowers must not turn task dependencies into a second implementation
scheduler or mutable task-state machine.

## Decision

EZPowers v5.7 adds a versioned assurance graph derived deterministically from
the current spec, plan, config, evidence, chain receipts, and certificate.
The graph is a view, not an editable source of truth. It gives each criterion,
task, check occurrence, evidence result, independent chain review, and
certificate a typed node and records stable typed edges and topological task
waves. A dedicated `trace --plan ... --json` command reports the graph hash,
runtime states, and candidate blocking paths. Dependency paths are never
labelled as proven causes.

Plan and config schema v2 are additive, explicit opt-ins:

- plan v2 requires `depends_on` for every task and rejects unknown, duplicate,
  self-referential, or cyclic dependencies;
- config v2 requires `verification.max_parallel_checks` from 1 through 32;
- a check is concurrent only when its own v2 contract declares
  `concurrency.safe: true`;
- resource locks plus an implicit same-check lock prevent conflicting check
  occurrences from overlapping;
- every unmarked check is a global barrier;
- task failures do not skip later checks, and required project checks remain a
  separate phase after all task waves.

Plan-v2 evidence and certificates use schema v2 and bind the complete graph
snapshot and hash. New chain approvals use schema v2 and freeze the same graph
hash. A refreshed nonterminal v5.6 approval without that binding becomes
`NEEDS_REAPPROVAL`. Existing plan/config v1 files are neither rewritten nor
silently upgraded and always retain serial execution.

## Consequences

The graph improves auditability without adding a new authority. Safe projects
can reduce verification wall time, but parallelism is intentionally opt-in and
must pass equivalence and repeated timing gates. More schema branches and
scheduler tests are required. Graph hashes become freshness and chain
approval inputs, so a changed dependency or concurrency declaration correctly
invalidates prior v2 evidence.

Dynamic agent teams, capability/model routing, automatic reviewer fleets,
unrestricted self-evolution, and a graph operating system remain outside the
product. They require separate reproducible evidence and a new boundary
decision before adoption.
