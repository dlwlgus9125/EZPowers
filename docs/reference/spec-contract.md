# Spec Contract

This contract defines the host-independent feature acceptance artifact. A spec
states observable claims; it does not choose an execution host, assign agents,
or embed commands.

## Preflight

Read repository instructions, `CONTEXT.md`, applicable ADRs, architecture and
frontend-design artifacts, existing specs, public entry points, tests, and
`.ezpowers/config.json`.

- Use `setup` when `.ezpowers/ezpowers.py` is missing.
- When a material product decision remains ambiguous, stop and recommend an
  explicit `deep-interview` invocation rather than interviewing inside `spec`.
- Return to `design-architecture` when implementation would otherwise invent a
  boundary, data flow, lifecycle, deployment, or verification decision.

## Human-Readable Contract

Write the spec under `docs/specs/`. Its Markdown should state:

- purpose and user or system outcome;
- included and excluded scope;
- settled architecture and design references;
- requirements and observable failure behavior;
- compatibility, migration, security, accessibility, or operational
  constraints that affect acceptance;
- risks and explicitly accepted limitations.

Use stable requirement IDs such as `R1`. Keep implementation choices out of
Given/When/Then-style claims unless they are themselves a public constraint.

## Managed JSON Block

Every spec contains exactly one block with these exact markers:

````markdown
<!-- ezpowers:spec:start -->
```json
{
  "schema_version": 1,
  "criteria": [
    {
      "id": "AC-1",
      "requirement_id": "R1",
      "claim": "The command exits zero and prints the generated file path.",
      "verify_type": "cli",
      "integration": false
    }
  ]
}
```
<!-- ezpowers:spec:end -->
````

The fenced body is one JSON object and is the machine source of truth.

### Criterion Rules

- `schema_version` is `1`.
- `criteria` is a non-empty array.
- `id` is unique, 1-64 characters, starts with a letter, and contains only
  letters, digits, `.`, `_`, or `-`.
- `requirement_id` is a non-empty stable requirement ID.
- `claim` is binary, externally observable, and independent of host or model.
- `verify_type` is a non-empty evidence classification. Prefer `pure`, `cli`,
  `lib`, `api`, `data`, or `e2e` consistently within a project.
- `integration` is a JSON boolean. Set it to `true` when proof must cross a real
  entry point, process, service, persistence boundary, or user-visible flow.

Include negative criteria when rejection or failure behavior is part of the
requirement. Do not put shell commands or host execution policy in the block.
`prepare-execute` binds criteria to exact project checks without weakening the
claims.

## Frontend Criteria

When a claim depends on visual structure, interaction state, responsive
behavior, accessibility, or a normative prototype, link the readable
requirement to `docs/ux/frontend-design.md`. The claim names the user-visible
outcome; the plan selects the project-local visual or interaction check.

## Validation

Run the installed runtime:

```text
python .ezpowers/ezpowers.py validate --spec <spec-path> --json
```

Invalid markers, invalid JSON, path traversal, duplicate IDs, empty claims,
missing fields, or a non-boolean `integration` value are blocking. Validation
does not prove product behavior; it proves the acceptance contract can be
planned deterministically.

Report the spec path, requirement-to-criterion mapping, integration criteria,
exclusions, design references, and unresolved risks. Continue to
`prepare-execute` only with a valid spec.
