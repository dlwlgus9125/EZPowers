# F23: Evidence-gated assurance graph and safe parallel verification

## Outcome

EZPowers users can validate and trace an explicit assurance graph and can
reduce verification wall time for checks whose independence is declared and
reproducibly proven, without moving implementation orchestration away from
Claude Code or Codex.

## Scope

Included are compatible plan/config v2 contracts, deterministic graph
derivation, a JSON trace surface, safe check-process concurrency, graph-bound
evidence/certification, harness-chain approval binding, legacy reapproval, and
release evaluation. Excluded are task assignment, model routing, reviewer
fleets, host-independent retries, autonomous graph evolution, and any external
executor.

Architecture impact: `docs/reference/architecture.md` and ADR 0007 settle the
new derived graph, verification scheduler, schema lifecycle, and evidence
boundary. The graph remains a view over existing authorities rather than a new
source of truth.

## Requirements

- R1: Existing schema-v1 projects remain readable and always execute checks
  serially without automatic rewriting.
- R2: Plan v2 makes task dependencies explicit, validates the DAG, and exposes
  one deterministic typed graph and hash through a safe trace interface.
- R3: Concurrent execution is bounded and per-check opt-in, honours explicit
  and implicit locks plus unsafe barriers, preserves task/required phases, and
  records all outcomes in declaration order even after failures.
- R4: Plan-v2 evidence and certificates bind the graph snapshot/hash and
  retain exact argv, logs, hashes, workspace freshness, and process cleanup.
- R5: The explicit harness chain uses the same normalisation and graph hash;
  new approvals freeze it and nonterminal legacy approvals require approval
  again after refresh.
- R6: Parallel adoption requires equivalent results and at least 30% median
  wall-time improvement across three controlled runs, plus repeated evidence
  on the currently allowlisted EZPowers checks.
- R7: Product guidance, contracts, ADRs, the paper evaluation, dual-host
  distribution, and release state describe the same bounded behavior.

## Risks and accepted limitations

Dependency paths identify candidates and blockers but do not prove causality.
Only checks explicitly reviewed as independent may opt in. A check that writes
to untracked or tracked workspace state still fails freshness; the trace may
list parallel candidates but does not assign blame. Existing config/plan v1
files require an explicit authoring refresh to gain v2 behavior.

<!-- ezpowers:spec:start -->
```json
{
  "schema_version": 1,
  "design_context": {
    "required": false,
    "reason": "The guide receives content-only updates; no UI structure, tokens, or reusable styling changes."
  },
  "criteria": [
    {
      "id": "AC-1",
      "requirement_id": "R1",
      "claim": "Schema-v1 plans and configs remain valid, are not rewritten, and execute every check serially in declaration order.",
      "verify_type": "integration",
      "integration": true
    },
    {
      "id": "AC-2",
      "requirement_id": "R2",
      "claim": "Plan-v2 validation rejects missing, duplicate, unknown, self, and cyclic dependencies and emits a stable typed graph hash and topological waves.",
      "verify_type": "cli",
      "integration": true
    },
    {
      "id": "AC-3",
      "requirement_id": "R3",
      "claim": "Verification overlaps only explicitly safe non-conflicting check occurrences within the worker cap and preserves complete declaration-order results and the required-check phase.",
      "verify_type": "integration",
      "integration": true
    },
    {
      "id": "AC-4",
      "requirement_id": "R4",
      "claim": "Plan-v2 evidence and certificates bind the current assurance graph and fail freshness after graph, log, workspace, or binding tampering.",
      "verify_type": "integration",
      "integration": true
    },
    {
      "id": "AC-5",
      "requirement_id": "R5",
      "claim": "Ordinary and staged-chain flows share dependency validation, new chain approvals freeze the graph hash, and a nonterminal approval without it becomes NEEDS_REAPPROVAL.",
      "verify_type": "e2e",
      "integration": true
    },
    {
      "id": "AC-6",
      "requirement_id": "R6",
      "claim": "Three matched controlled runs show at least 30 percent median wall-time improvement with serial-equivalent check outcomes, and the allowlisted repository checks are measured separately.",
      "verify_type": "cli",
      "integration": false
    },
    {
      "id": "AC-7",
      "requirement_id": "R7",
      "claim": "The v5.7 source, contracts, reports, guide, manifests, feature state, and both host discovery surfaces expose the same bounded assurance behavior.",
      "verify_type": "smoke",
      "integration": true
    }
  ]
}
```
<!-- ezpowers:spec:end -->
