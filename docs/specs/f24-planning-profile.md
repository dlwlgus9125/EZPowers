# F24: Planning-artifact project profile

## Outcome

EZPowers users can configure a repository whose product is a set of planning
artifacts, validate format-unrestricted deliverables with project-owned exact
commands, and obtain the same fresh evidence and bounded harness-chain verdict
as a software project without changing the legacy software path.

## Scope

Included are a project-level profile, fail-closed config/plan v3, byte-hashed
inputs, logical multi-file deliverables, direct or inspected review sources,
planning assurance nodes, artifact-bound evidence, a required independent
artifact-review chain gate, explicit profile migration, and a v5.8 dual-host
distribution. Excluded are built-in Markdown/XLSX validators, directory or
glob artifacts, external business actions, a new executor, and per-plan
profile overrides.

Architecture impact: `docs/reference/architecture.md` and ADR 0008 establish
the project-profile policy seam, planning artifact ownership and hashing, and
the profile-specific independent-review boundary. The shared exact-command,
evidence, freshness, certification, state, and host-adapter core remains the
same authority.

## Requirements

- R1: Existing config/plan v1 and v2 projects retain software validation,
  graph bytes, code-review gates, check order, evidence, and performance.
- R2: Setup explicitly selects a project profile, preserves it on refresh, and
  changes it later only through an explicit migration that stales completion
  and reapproves any active chain.
- R3: Planning config/plan v3 fail closed on older or mismatched runtimes and
  validate named byte inputs, logical deliverables, criterion coverage, and
  direct/inspected review sources without a format whitelist.
- R4: Every planning criterion maps to an executable project check and exactly
  one deliverable; verify binds declared input/output hashes even for ignored
  files and rejects missing or mutated artifacts.
- R5: Planning assurance traces, evidence, certificates, approvals, and
  freshness bind the profile, graph, declared paths, bytes, commands, and
  inspection logs without weakening existing tamper rules.
- R6: A planning harness chain freezes inputs and acceptance adapters, leaves
  outputs mutable until verification, and certifies only after every
  deliverable receives a bound artifact-review PASS plus conditional QA.
- R7: Failed artifact review requires an actual byte change in each failed
  logical deliverable and a new all-scope PASS before another review.
- R8: Contracts, skills, product state, guide, v5.8 kit, plugin manifests, and
  both host discovery surfaces expose the same profile behavior and unchanged
  catalog counts.
- R9: Five interleaved baseline/candidate measurements show equivalent
  software outputs and no more than five percent median validation/trace
  regression, while existing scheduler benchmarks retain thirty percent
  improvement.

## Risks and accepted limitations

Independent review remains a host-native judgement rather than a semantic
parser. External validator dependencies are project-owned and are not made
reproducible by EZPowers alone. Hashes detect changed declared bytes but are
not a signing boundary. A planning project may contain support code, but a
repository whose product is software continues to use the software profile.

<!-- ezpowers:spec:start -->
```json
{
  "schema_version": 1,
  "design_context": {
    "required": false,
    "reason": "The offline guide receives content-only updates and retains its existing DESIGN.md contract."
  },
  "criteria": [
    {
      "id": "AC-1",
      "requirement_id": "R1",
      "claim": "Existing config and plan v1/v2 fixtures retain identical software graph hashes, code-review gates, check order, and public validation results.",
      "verify_type": "integration",
      "integration": true
    },
    {
      "id": "AC-2",
      "requirement_id": "R2",
      "claim": "Setup creates or explicitly migrates a project profile without implicit refresh changes and invalidates prior completion and active-chain approval when the profile changes.",
      "verify_type": "integration",
      "integration": true
    },
    {
      "id": "AC-3",
      "requirement_id": "R3",
      "claim": "Planning config/plan v3 validates safe inputs, logical deliverables, exact criterion coverage, and direct or inspected review sources and rejects mismatched or unsafe contracts.",
      "verify_type": "cli",
      "integration": true
    },
    {
      "id": "AC-4",
      "requirement_id": "R4",
      "claim": "Planning verification executes real project checks and binds every declared input and output byte hash, including Git-ignored files, while rejecting missing or check-mutated artifacts.",
      "verify_type": "integration",
      "integration": true
    },
    {
      "id": "AC-5",
      "requirement_id": "R5",
      "claim": "Planning trace, evidence, certificate, approval, and freshness data bind the profile-specific graph and declared artifact inventory and detect path, byte, log, or receipt tampering.",
      "verify_type": "integration",
      "integration": true
    },
    {
      "id": "AC-6",
      "requirement_id": "R6",
      "claim": "A planning chain freezes binary inputs without UTF-8 decoding and requires a bound per-deliverable artifact-review PASS and conditional QA before certification.",
      "verify_type": "e2e",
      "integration": true
    },
    {
      "id": "AC-7",
      "requirement_id": "R7",
      "claim": "Artifact-review failure blocks another review until every failed logical deliverable changes bytes and a new all-scope verification passes.",
      "verify_type": "e2e",
      "integration": true
    },
    {
      "id": "AC-8",
      "requirement_id": "R8",
      "claim": "The v5.8 contracts, skills, guide, manifests, product state, kit hashes, and Claude and Codex discovery surfaces expose the same planning profile with unchanged skill, contract, and tool counts.",
      "verify_type": "smoke",
      "integration": true
    },
    {
      "id": "AC-9",
      "requirement_id": "R9",
      "claim": "Five interleaved runs preserve equivalent software validation and trace outputs within a five percent median slowdown and both scheduler benchmarks retain at least thirty percent improvement.",
      "verify_type": "cli",
      "integration": false
    }
  ]
}
```
<!-- ezpowers:spec:end -->
