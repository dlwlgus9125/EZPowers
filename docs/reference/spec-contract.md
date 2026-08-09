# Spec Contract

This contract defines the host-independent feature acceptance artifact. A spec
states observable claims; it does not choose an execution host, assign agents,
or embed commands.

## Preflight

Read repository instructions, `CONTEXT.md`, applicable ADRs, architecture and
frontend-design artifacts, every applicable nearest `DESIGN.md`, existing
specs, public entry points, tests, and `.ezpowers/config.json`.
Read `.ezpowers/docs.json` when present. Wiki candidates are supporting hints
only and must be confirmed against repository evidence before becoming a
requirement.

- Use `setup` when `.ezpowers/ezpowers.py` is missing.
- When a material product decision remains ambiguous, stop and recommend an
  explicit `deep-interview` invocation rather than interviewing inside `spec`.
- Return to `design-architecture` when implementation would otherwise invent a
  boundary, data flow, lifecycle, deployment, or verification decision.

## Human-Readable Contract

Write the spec under `docs/specs/`. Its Markdown should state:

- purpose and user or system outcome;
- included and excluded scope;
- an `Architecture impact` statement: `none` with evidence, or the settled
  canonical artifact paths and decision IDs;
- settled architecture and design references;
- requirements and observable failure behavior;
- compatibility, migration, security, accessibility, or operational
  constraints that affect acceptance;
- risks and explicitly accepted limitations.

Use stable requirement IDs such as `R1`. Keep implementation choices out of
Given/When/Then-style claims unless they are themselves a public constraint.
If implementation would require a boundary different from the referenced
architecture, return to `design-architecture` instead of treating the
architecture document as an implementation task.

## Managed JSON Block

Every spec contains exactly one block with these exact markers:

````markdown
<!-- ezpowers:spec:start -->
```json
{
  "schema_version": 1,
  "design_context": {
    "required": true,
    "frontend_artifact": "docs/ux/frontend-design.md",
    "systems": ["DESIGN.md"]
  },
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

Every newly written spec includes `design_context`. UI work uses `required:
true`, names the broad frontend artifact, and lists every applicable
project-relative `DESIGN.md`. Non-UI work records the decision explicitly:

```json
"design_context": {
  "required": false,
  "reason": "No UI surface or visual-system behavior changes."
}
```

Legacy specs without this field remain readable and valid. Their omission is
not permission for a new or revised UI spec to skip design-system discovery.

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
behavior, accessibility, or reusable styling, link the readable requirement to
the `design_context` artifacts. The broad artifact owns UX behavior; each
listed nearest `DESIGN.md` owns tokens and reusable-component rules. The claim
names the user-visible outcome; the plan selects the project-local mapping,
visual, or interaction check.

## Validation

Run the installed runtime:

```text
python .ezpowers/ezpowers.py validate --spec <spec-path> --json
```

Invalid markers, invalid JSON, unsafe or malformed design context, path
traversal, duplicate IDs, empty claims, missing fields, or a non-boolean
`integration` value are blocking. Validation
does not prove product behavior; it proves the acceptance contract can be
planned deterministically.

Report the spec path, requirement-to-criterion mapping, integration criteria,
exclusions, design references, and unresolved risks. Continue to
`prepare-execute` only with a valid spec.
