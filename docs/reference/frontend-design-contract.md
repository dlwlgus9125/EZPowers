# Frontend Design Contract

This contract separates durable product-surface decisions from normative visual
tokens while keeping both available to later specification, planning,
implementation, and maintenance. It is advisory until the artifacts are
registered or referenced by a managed spec/plan; it never grants authority to
write UI code.

## Paired artifacts and authority

Every new UI design produces or updates:

- `docs/ux/frontend-design.md`, which owns audience and outcome, information
  architecture, screen/state matrix, component taxonomy, responsive and input
  behavior, accessibility, assets, and visual-QA oracles;
- one or more `DESIGN.md` files, which own machine-readable tokens and reusable
  component styling.

The default is one `DESIGN.md` at the repository root. An independently
branded frontend root may own a nearer `DESIGN.md`. The nearest declared
mapping wins; mappings do not merge. When code and the applicable `DESIGN.md`
disagree, the mismatch is implementation alignment work. A maintainer changes
the document only when the intended design itself changes, then aligns code.
Mocks, screenshots, generated exports, and current CSS do not silently outrank
the mapped document.

The broad artifact contains exactly one managed block:

````text
<!-- ezpowers:frontend-design:start -->
```json
{
  "schema_version": 1,
  "design_systems": [
    {
      "path": "DESIGN.md",
      "profile": "google-alpha-0.4.0-ezpowers-1",
      "frontend_roots": ["."],
      "implementation_paths": ["src/app"]
    }
  ]
}
```
<!-- ezpowers:frontend-design:end -->
````

Paths are project-relative, stay outside runtime, dependency, build, and host
metadata directories, and must exist for a gating check. Every mapping names at
least one frontend root and implementation path. Duplicate roots, ambiguous
nearest mappings, a path not ending in `DESIGN.md`, or an implementation path
claimed by a non-nearest mapping fails validation.

## DESIGN.md profile

The installed `.ezpowers/contracts/design-md-profile.json` is the executable
profile registry. Profile `google-alpha-0.4.0-ezpowers-1` selectively adapts the
Google design.md alpha format reviewed at commit
`9bf8eae67128b6cc55ad9bf86665767deb4c11cd` and CLI version `0.4.0`.

Machine-readable frontmatter may contain `version`, `name`, `description`,
`omitted`, `colors`, `typography`, `rounded`, `spacing`, and `components`.
Tokens are normative; Markdown prose explains their use. Known level-two
sections follow this order: Overview, Colors, Typography, Layout, Elevation &
Depth, Shapes, Components, and Do's and Don'ts. Unknown sections are preserved;
duplicate headings fail. The local subset rejects YAML aliases, anchors, tags,
merge keys, and multiline scalars so validation remains deterministic without
a YAML dependency.

The standard-library tool supports:

```text
python .ezpowers/tools/design-md.py lint --file <path> --profile <id> --json
python .ezpowers/tools/design-md.py diff --before <path> --after <path> --profile <id> --json
python .ezpowers/tools/design-md.py check-project --project-root . --frontend-design <path> --json
```

Exit `0` means valid/no regression, `1` means validation failure or a reviewed
regression, and `2` means unsafe input or a tool/profile error. Diff treats an
invalid result, removed token, new error, or new warning as a regression.
Unknown prose survives. EZPowers adopts writing, lint, diff, and review
semantics only; it does not export Tailwind/DTCG tokens or generate UI code.
Because a complete implementation inventory legitimately contains leaf tokens,
the local profile records `orphaned-tokens` as informational rather than an
official-CLI warning. This is an explicit severity override, not an omitted
rule; the optional official cross-check retains its own diagnostics.

If local `node_modules/@google/design.md` is exactly the pinned version,
`check-project` runs `npx --no-install designmd lint --format json <path>` as a
second opinion. It never installs a package or accesses the network. A missing
CLI is normal. A locally installed mismatched version is explicit review work,
not a reason to reinterpret the profile.

## Direction and readiness

When visual direction is unsettled, compare two or three materially different
directions and select one with evidence. The broad artifact records:

- surfaces, audience, outcome, and selected direction;
- navigation/information hierarchy and every meaningful state, including
  empty, loading, validation, error, success, offline, permission, and long
  running states when applicable;
- reusable component taxonomy and the token/component mapping boundary;
- responsive breakpoints and keyboard, pointer, touch, zoom, reduced-motion,
  localization, and overflow behavior;
- WCAG target and concrete contrast, focus, semantic, and assistive-technology
  checks;
- asset provenance and licensing;
- executable visual-QA oracles and honest tool prerequisites.

Storybook or equivalent becomes a hard state/story lane only when project
tooling exists or the plan explicitly adds it. Screenshot/visual baselines
become hard only when screenshot-specific or visual-diff tooling exists or is
an explicit prerequisite. A normative external mock must name token/component
mapping and freshness; otherwise it is reference-only.

The evidence ladder remains
`tokens -> primitives -> component states/stories -> screens -> e2e/visual`.
Playwright availability alone is not enough to make
screenshots a gate; screenshot assertions or an explicit prerequisite are
required. BackstopJS and equivalent visual-diff tools do make that lane
applicable. Workspace detection may scan package roots, and maintainers may
scope the readiness runner with repeated `--frontend-root` arguments.

`mock/prototype` artifacts remain advisory unless explicitly normative with the
required mapping and freshness evidence. Tool availability must come from
project-local tooling, never a globally installed executable.

`.ezpowers/tools/frontend-visual-readiness.py` preserves those conditional lanes and also
hard-gates every managed DESIGN.md mapping. It reports evidence; it does not
install browser, component, image, or package tooling.

## Ownership, migration, and downstream use

When a documentation graph exists, stage both artifact types through
documentation preview/apply. A DESIGN.md entry uses validator `design-md` and
an explicit `validator_profile`. Existing unmanaged files are detected and
reported but never auto-adopted. Adoption, replacement, or an old-profile
migration requires an explicit preview/approval; force-backed changes retain a
backup. A profile update adds a new profile and keeps old profiles readable
until their registered documents are explicitly migrated.

New specs always record `design_context`. UI work sets `required: true`, names
the broad artifact, and lists every applicable `DESIGN.md`; non-UI work sets
`required: false` with a reason. Plans include mapping alignment and the exact
local checks. Execute reads the nearest mapping before changing UI. A managed
ready graph registers both `ezpowers.docs` and `ezpowers.design`. Without a
managed graph, a plan carries `check-project` as a plan-local static check.

An explicit harness-chain UI run freezes the broad frontend artifact and every
listed design-system file alongside spec, plan, and oracles. Any frozen input
change produces `NEEDS_REAPPROVAL`; it is never repaired by rewriting hashes.

## Provenance and maintenance

The profile records the upstream repository, pinned commit, CLI version,
review date, license, and hashes of watched spec/lint/diff/package files. Normal
runtime behavior is fully offline and uses only installed bytes. Maintainers
may run source-only `python scripts/check-design-md-upstream.py --json`:

- `CURRENT` means every watched byte still matches;
- `REVIEW_REQUIRED` means at least one watched file changed;
- `UNAVAILABLE` means the network comparison could not complete.

The checker performs no writes and is not scheduled CI. A breaking upstream
change is reviewed and represented as a new profile; it never mutates the old
profile in place. EZPowers independently implements its subset and copies no
upstream source code. Upstream design.md is Apache-2.0; if future work copies
material source or prose, the distribution must add the applicable notice
before release.
