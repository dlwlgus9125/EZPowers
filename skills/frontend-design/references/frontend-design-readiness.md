# Frontend Design Readiness

Load this reference when producing or reviewing `docs/ux/frontend-design.md`.

## Required Artifact Shape

`docs/ux/frontend-design.md` must include:

- Product surface and audience: primary users, jobs, domain constraints, and
  whether the UI is operational, consumer, editorial, game, marketing, mobile,
  desktop, or mixed.
- Design direction decision: 2-3 options considered, selected option or hybrid,
  rejected tradeoffs, and user confirmation or delegated choice.
- Screen inventory: routes, screens, dialogs, empty states, and error screens.
- IA and navigation: primary navigation, local navigation, cross-screen flows,
  and entry/exit points.
- UX state matrix: loading, empty, error, permission, offline, validation,
  cancellation, success, and long-running states for each user journey.
- Design system source: existing system, generated repo-owned system, or Figma
  handoff source with ownership.
- Token policy: color roles, typography scale, spacing, radius, shadows,
  density, motion, and dark/light mode decision.
- Component taxonomy: primitives, composed components, page sections, forms,
  data display, feedback, navigation, overlays, and charts when applicable.
- Responsive rules: supported breakpoints, layout shifts, min/max dimensions,
  touch targets, and text overflow policy.
- Accessibility target: keyboard path, focus management, semantic labels,
  contrast policy, reduced motion, and screen-reader-visible names.
- Asset policy: real/generated images, icons, fonts, licensing, and fallback.
- Visual QA strategy: Storybook, component DOM, browser e2e, screenshot/visual
  diff, accessibility check, or approved adapter fallback.
- Mock/prototype artifact handling: artifact path/link, fidelity, owner,
  normative or reference-only status, token/component mapping, and freshness
  rule when mockups or prototypes influence implementation.
- Visual readiness lanes: Storybook or equivalent component state-story
  coverage, Playwright screenshot baseline, visual diff baseline, and
  screenshot/visual review loop when those tools are available or planned.

## Defaults

- Use code-owned tokens and components when no external design source exists.
- Prefer Storybook, Ladle, Histoire, or equivalent component isolation for
  complex component states when the project already has it or when the plan can
  add it.
- Prefer Playwright or equivalent browser e2e for rendered web routes. Require
  screenshot/visual baselines only when screenshot-specific evidence exists,
  such as `toHaveScreenshot`, visual snapshots, visual diff scripts, or plan
  tasks that add screenshot baselines.
- Keep visual automation tool-conditional: if the tool is missing, planning must
  add a prerequisite adapter task or record an accepted non-visual equivalent
  only when the same user-visible claim is proven.
- Treat project-local evidence as the trigger for hard visual gates: checked-in
  config, package scripts/dependencies, existing stories/tests, or explicit
  plan prerequisite tasks. Do not require visual automation only because a
  binary exists on global PATH.
- In monorepos, inspect the project root plus workspace frontend roots, or pass
  the target app with `scripts/frontend-visual-readiness.py --frontend-root`.
- Equivalent visual tools include Chromatic, Percy, Loki, reg-suit, BackstopJS,
  Argos, Applitools, jest-image-snapshot, pixelmatch, and lost-pixel when they
  are configured in the project.
- Normative mock/prototype artifacts require token/component mapping and a
  freshness rule. Reference-only artifacts may inform direction, but the
  design artifact remains the implementation source of truth.
- `scripts/frontend-visual-readiness.py` can detect whether visual readiness
  lanes are advisory or hard-gated; it does not install tools or create
  screenshots. Use `--mode detect` for advisory inspection and `--mode check`
  for gating.

## Review Questions

- Would an implementer still need to invent visual direction, token values,
  component states, layout behavior, or accessibility policy?
- Does every screen have states beyond the happy path?
- Are tokens and component layers ordered before screen implementation?
- Does visual QA verify user-observable design claims, not only that tests run?
- If Storybook, Playwright, screenshots, or visual diff tooling exists or is
  planned, does the plan include the corresponding baseline and review loop?
