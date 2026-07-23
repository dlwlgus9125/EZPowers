# Frontend Design Contract

This contract prevents implementation from inventing product appearance,
interaction states, or accessibility policy while coding. It is a design
artifact contract, not a UI implementation workflow.

## Required Artifact

Create or update `docs/ux/frontend-design.md` when a new or materially changed
web, mobile, desktop, or TUI surface needs design decisions. Reuse an existing
canonical artifact when it already owns the same information.
When `.ezpowers/docs.json` registers the artifact as EZPowers-owned, stage and
apply its update under `documentation-contract.md`; do not hand-edit managed
bytes. An external registered artifact remains user-owned.

Record:

- product surface, audience, and design direction;
- two or three considered directions, selected direction, and tradeoffs;
- screen or route inventory and information architecture;
- loading, empty, error, permission, offline, validation, cancellation,
  success, and long-running states when applicable;
- existing design-system source or the repo-owned token and primitive policy;
- component taxonomy and state variants;
- responsive and input-method rules;
- accessibility target and observable checks;
- asset provenance and licensing constraints;
- visual QA oracle and expected evidence;
- normative mock/prototype paths, token/component mapping, and freshness
  rule, or an explicit statement that they are reference-only;
- unresolved questions that must return to `deep-interview` or architecture.

Use `not applicable` with a reason instead of leaving a required topic blank.

## Interaction Contract

1. Read manifests, routes, views, components, styles, tests, and existing
   design evidence.
2. Offer two or three materially different directions with tradeoffs.
3. Record the selected direction, hybrid, or delegated choice.
4. Write the artifact without implementing product UI.
5. Hand the artifact path and unresolved questions to `spec`.

Prefer existing project conventions. Figma or another external design file is
optional input, never an implicit dependency.

## Tool-Conditional Visual Lanes

The installed detector is:

```text
python .ezpowers/tools/frontend-visual-readiness.py --mode detect
python .ezpowers/tools/frontend-visual-readiness.py --mode check
```

`detect` is advisory. `check` is a gate only after the architecture or plan
declares the detected lane required. Use `--frontend-root` for explicit
monorepo application roots.

Require component isolation, screenshot baselines, or visual diff only when
repository evidence already configures those tools or the plan adds a
prerequisite to configure them. Playwright availability alone is not enough to
require screenshot baselines. Screenshot-specific tests, snapshot files, or
visual-regression configuration do.

Equivalent project-local tooling is valid when it preserves the same oracle.
Examples include Storybook, Ladle, or Histoire for component isolation and
Chromatic, Percy, Loki, BackstopJS, Argos, Applitools,
`jest-image-snapshot`, `pixelmatch`, or `lost-pixel` for visual comparison.

## Carry-Forward

- Architecture records the artifact path, chosen direction, and verification
  oracle.
- The spec references the artifact for any criterion that depends on visual,
  responsive, interaction-state, or accessibility behavior.
- The plan preserves that oracle in exact project checks. If no suitable design
  system exists, order work as `tokens -> primitives -> component states/stories -> screens -> e2e/visual`.
- `execute` uses host-native implementation and review, then the project-local
  runtime records the declared checks.

Missing design decisions or missing deterministic adapters are blocking gaps;
they are not permission to downgrade a user-visible claim. Readiness comes from
the artifact and its declared evidence, not a separate orchestration layer.
