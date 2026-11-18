# F26: Content-bound check reuse

## Outcome

EZPowers users can make verification time follow what a change can affect. A
check that declares the paths its outcome depends on is not executed again
while that content, its contract, and the installed kit are unchanged, and the
completion verdict records exactly which results were carried.

## Scope

Included are the optional `reuse` declaration on plan/config schema 2 and 3
checks, the runtime-defined pattern language, content identity and the reuse
key, carrying an earlier executed PASS, one execution per run for a declared
check, `verify --no-reuse`, the evidence, freshness, certificate, and status
rules, harness-chain and planning-profile integration, a reproducible
benchmark, the real install smoke, contract and skill guidance, and the 5.10.0
kit and plugin surfaces.

Excluded are change-size tiers that shrink the required-check set, a new
verification scope, a time limit on a carried PASS, any change to harness-chain
gate, rework, or limit rules, shared execution for undeclared checks, and edits
to installed projects or to this repository's own `.ezpowers/config.json`.

Architecture impact: `docs/reference/architecture.md` and ADR 0010
(`docs/decisions/0010-content-bound-check-reuse.md`) settle the changed
completion basis, the evidence and state boundary, and the chain binding.

## Decisions carried from design

| ID | Decision | Source |
| --- | --- | --- |
| D26-1 | A declared check's PASS binds to its contract, selected file content, kit identity, profile, artifact inventory, project root, and platform instead of every workspace byte. | user |
| D26-2 | Reuse is opt-in per check; undeclared checks and projects keep exact behavior, evidence shape, and verdicts. | user |
| D26-3 | One execution per run applies to declared checks only. | user |
| D26-4 | Ordinary and harness-chain flows both apply reuse; gate, rework, and limit rules are unchanged; a chain carries only from its own approved run. | user; narrowed by soundness review |
| D26-5 | The declaration is an additive field of schema 2 and 3 checks; a schema-1 check that carries it is rejected. | default; plan v3 is planning-only and config v3 carries the profile |
| D26-6 | Single hop, stable runs only, failure revokes, source evidence is the authority, and unrepresentable occurrences execute. | default; soundness review |
| D26-7 | A carried PASS has no time limit; `verify --no-reuse` forces a full run. | user-approved plan |
| D26-8 | No additional verification scope is introduced. | user-approved plan |

## Requirements

- R1: A project whose checks declare no reuse keeps its validation and trace
  output, evidence, certificate, and state shapes, execution counts, and
  verdicts.
- R2: The declaration is validated fail-closed, is accepted only on schema 2
  and 3 checks, and is bound into the check contract and assurance-graph hash.
- R3: A declared check whose reuse key matches a valid earlier executed PASS is
  carried without execution; changed selected content, a changed contract or
  kit, an ineligible occurrence, an earlier failure, an invalid source record,
  or `--no-reuse` executes it.
- R4: A declared check executes at most once per verification run.
- R5: Freshness and certification accept valid reuse records, reject altered or
  incomplete ones, and the certificate lists carried occurrences.
- R6: Harness-chain flows carry only within the approved run, never in the
  baseline, and keep gate and limit behavior; planning flows bind the artifact
  inventory.
- R7: Re-verification after a change that affects only some checks is at least
  50 percent faster by three-run median than a full run, with equal verdicts,
  through the real CLI on an installed fixture.
- R8: Contracts, skills, product documents, the guide, manifests, and both host
  discovery surfaces describe the same behavior at 5.10.0.

## Risks and accepted limitations

An incomplete declaration can carry a PASS that a real run would fail. The
reuse key does not bind Git history, Git-ignored files, environment variables,
toolchain versions, the clock, the network, or external services. A flaky check
is carried until its selected content changes. A pattern that selects no file,
a symlink, gitlink, unreadable entry, or a case-only spelling difference makes
the occurrence execute instead of carrying. Installed projects gain the
behavior only after `setup --refresh` and an explicit declaration.

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
      "claim": "A project whose checks declare no reuse produces evidence, certificate, and state documents with the same key sets and the same number of started check processes as before, with and without --no-reuse.",
      "verify_type": "cli",
      "integration": true
    },
    {
      "id": "AC-2",
      "requirement_id": "R2",
      "claim": "Validation rejects a reuse declaration on a schema-1 check and every malformed declaration or pattern, and adding, editing, or removing a declaration changes the assurance-graph hash while an undeclared plan keeps its hash.",
      "verify_type": "cli",
      "integration": true
    },
    {
      "id": "AC-3",
      "requirement_id": "R3",
      "claim": "After a recorded PASS, a verification run that leaves a declared check's selected files, contract, and installed kit unchanged records that check as carried without starting its process, while a changed selected file, a changed contract, an ineligible occurrence, an earlier failure, an invalid source record, or --no-reuse starts the process.",
      "verify_type": "cli",
      "integration": true
    },
    {
      "id": "AC-4",
      "requirement_id": "R4",
      "claim": "A declared check referenced by several occurrences starts one process per verification run and each occurrence receives its own result entry and log files, while an undeclared repeated check still starts one process per occurrence.",
      "verify_type": "cli",
      "integration": true
    },
    {
      "id": "AC-5",
      "requirement_id": "R5",
      "claim": "Status and certify accept an all-scope result that contains carried entries, the certificate lists each carried occurrence with its source run, and a result whose reuse records, execution trace, summary, or certificate were altered is reported stale.",
      "verify_type": "cli",
      "integration": true
    },
    {
      "id": "AC-6",
      "requirement_id": "R6",
      "claim": "In an approved harness chain the first verification starts every check process, a rework verification carries an unaffected declared check without changing gate or counter behavior, the baseline never carries, and a preview whose reuse-declared oracle check omits its oracle file is rejected.",
      "verify_type": "e2e",
      "integration": true
    },
    {
      "id": "AC-7",
      "requirement_id": "R6",
      "claim": "In a planning project a declared check is carried after a change outside the declared artifacts and starts its process again after any declared input or deliverable byte changes, including a Git-ignored deliverable.",
      "verify_type": "e2e",
      "integration": true
    },
    {
      "id": "AC-8",
      "requirement_id": "R7",
      "claim": "On an installed fixture, three matched runs show at least 50 percent median wall-time improvement for re-verification after a change that affects only some checks compared with a forced full run, with equal per-check outcomes and a certified result in both modes.",
      "verify_type": "cli",
      "integration": true
    },
    {
      "id": "AC-9",
      "requirement_id": "R8",
      "claim": "The 5.10.0 source, contracts, skills, guide, manifests, feature state, and both host discovery surfaces expose the same content-bound reuse behavior.",
      "verify_type": "cli",
      "integration": true
    }
  ]
}
```
<!-- ezpowers:spec:end -->
