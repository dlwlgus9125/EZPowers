# App Delivery Contract

This contract makes user-facing app delivery a first-class part of setup,
design_architecture, spec, prepare_execute, audit, and execution. It covers frontend, backend,
packaging, deployment, and release verification.

## Source Contracts

- `docs/reference/setup-contract.md`
- `docs/reference/design-architecture-contract.md`
- `docs/reference/spec-contract.md`
- `docs/reference/plan-contract.md`
- `docs/reference/verification-contract.md`
- `docs/reference/ui-verification-adapter-contract.md`
- `docs/reference/frontend-design-contract.md`
- `docs/reference/architecture-readiness-contract.md`

## Setup: App Delivery Profile

`/setup` records an `app_delivery` block in `.harness/config.json`.

```json
{
  "app_delivery": {
    "surface_kind": "web",
    "frontend": {
      "present": true,
      "framework": "",
      "routes": "",
      "design_system": "",
      "view_extensions": [],
      "viewport_matrix": ["mobile", "desktop"],
      "accessibility_baseline": "keyboard navigation and semantic labels",
      "design_readiness_required": true,
      "design_artifact": "docs/ux/frontend-design.md",
      "token_source": "",
      "component_inventory": "",
      "visual_qa": "",
      "mock_prototype_artifacts": "",
      "visual_baseline": ""
    },
    "backend": {
      "present": false,
      "api_style": "",
      "auth_session": "",
      "persistence": "",
      "background_jobs": "",
      "external_services": []
    },
    "packaging": {
      "artifact": "static_site",
      "build_output": "",
      "installer_or_image": ""
    },
    "deployment": {
      "target": "local",
      "provider": "",
      "preview_default": true,
      "required_env": [],
      "rollback": "revert commit or redeploy previous artifact"
    },
    "qa": {
      "browser_or_e2e": "",
      "visual_regression": "",
      "release_checklist": []
    }
  }
}
```

Defaults:

- `surface_kind`: one of `web`, `mobile`, `desktop`, `cli`, `api`,
  `library`, or `docs`.
- `deployment.target`: `local` unless the repo or user identifies a preview,
  staging, or production target.
- `deployment.preview_default`: `true` for web/mobile/desktop apps. Production
  deployment requires an explicit user request.
- `frontend.present`: `true` when UI files, routes, components, or declared UI
  intent exist.
- `frontend.design_readiness_required`: `true` when a UI surface is present.
  The artifact path defaults to `docs/ux/frontend-design.md`.
- `backend.present`: `true` when API routes, server processes, persistence, or
  external services exist.

## Spec: App Experience And Delivery Baseline

Every spec for `web`, `mobile`, `desktop`, `cli`, or `api` includes an
`App Experience And Delivery Baseline` section before requirements. `docs` and
`library` specs may state `not applicable` with the reason.

Required fields:

- Surface inventory: user-facing surfaces, entry points, routes, commands, or
  screens affected by the work.
- UX flow map: primary user journeys plus loading, empty, error, permission,
  offline, and cancellation states when applicable.
- Frontend contract: frontend design artifact path, design system or component
  source, token policy, component taxonomy, UX state matrix, assets,
  responsive breakpoints, accessibility baseline, and state ownership.
- Frontend visual readiness: mock/prototype artifact handling, Storybook or
  equivalent component state-story coverage, Playwright screenshot or visual
  diff baseline, and screenshot/visual review loop when project-local tooling
  exists or the plan adds it as a prerequisite. Playwright e2e-only evidence
  does not require screenshot baselines.
- Backend contract: API style, endpoint/event/schema ownership, auth/session
  behavior, persistence, external service handling, and error response shape.
- Packaging contract: build artifact, output path, bundle/container/installer
  target, and local run command.
- Deployment contract: local, preview, staging, or production target; provider;
  required environment variables; readiness signal; rollback rule.
- QA contract: unit, API, e2e, visual, smoke, accessibility, and release
  verification commands that are in scope for the feature.

## Plan: Experience/Delivery Matrix

Every plan derived from a spec with an App Experience And Delivery Baseline
includes this section:

```markdown
## Experience/Delivery Matrix

| Surface | Requirements | Tasks | Verify |
|---------|--------------|-------|--------|
| UI route `/settings` | R1, R2 | T1, T3 | `pnpm test:e2e --grep settings` |
| API `PATCH /settings` | R2 | T2 | `pnpm test:api --grep settings` |
| Preview deploy | R3 | T4 | `vercel deploy --prebuilt --yes` |
```

Rules:

- Every user-facing surface from the spec appears in the matrix.
- UI rows include viewport coverage and a browser/e2e or visual verification
  command. A component-only unit test is not enough for a rendered route or
  screen.
- Backend/API rows include status, payload, error shape, and auth/session
  assertions through API, e2e, or contract tests.
- Packaging rows include build artifact existence and runnable artifact smoke.
- Deployment rows default to preview deployment and include readiness or URL
  verification. Production rows require explicit user intent.
- If a surface is intentionally out of scope, the row says `omitted by user`
  and names the accepted risk.

## Task Requirements

Tasks carry a `**Surface:**` field with one or more of `ui`, `api`, `data`,
`package`, `deploy`, `docs`, or `none`.

Additional task rules:

- `ui` tasks that create or modify view files include `**View wiring
  verification:**` plus a viewport/e2e or visual check covering at least one
  mobile and one desktop size when the app is responsive.
- `api` tasks include a Verify command that asserts status code, response
  shape, and at least one negative/error path when the spec defines one.
- `package` tasks include a build artifact check and runtime smoke for the
  packaged output.
- `deploy` tasks include preview deployment by default, deployment log
  inspection on failure, readiness verification, and rollback notes.
- Cross-surface flows use the Full-Feature Wiring Gate to drive the same entry
  path a user or deployment would use.

## D9: App Delivery Readiness

`internal pipeline audit` runs D9 whenever `app_delivery.surface_kind` is not `docs` or
`library`, or when a spec/prepare_execute declares an App Experience And Delivery
Baseline.

Spec-only checks:

- FAIL when a UI feature lacks App Experience And Delivery Baseline, UX flow
  map, frontend contract, or at least one browser/e2e/visual Verify command.
- FAIL when a UI feature lacks frontend design readiness: missing
  `docs/ux/frontend-design.md`, design direction decision, design-system
  source, token policy, component taxonomy, UX state matrix, responsive rules,
  accessibility target, or visual QA strategy.
- FAIL when available or planned Storybook/component isolation lacks component
  state-story coverage.
- FAIL when available or planned Playwright screenshot, visual diff, or
  equivalent tooling lacks screenshot/visual baseline and review loop coverage.
- FAIL when a normative mock/prototype artifact lacks token/component mapping
  or a freshness rule.
- FAIL when an API/server feature lacks backend contract, auth/session decision
  where applicable, error shape, or API Verify command.
- WARN when packaging or deployment is `none declared` for an executable app.
- FAIL when deployment is in scope but required env vars, preview/staging
  target, readiness signal, or rollback rule is missing.

Spec+plan checks:

- FAIL when the plan lacks an Experience/Delivery Matrix for a spec that has
  App Experience And Delivery Baseline.
- FAIL when any matrix row has no mapped task or no non-trivial Verify command.
- FAIL when UI tasks lack viewport/e2e or visual verification required by the
  available or planned adapter/tooling.
- FAIL when a plan starts UI screen implementation before tokens, primitives,
  and component states/stories when no suitable design system already exists.
- FAIL when package/deploy tasks lack build artifact, readiness, or rollback
  verification.
- FAIL when visual or accessibility verification is advisory-only for an
  acceptance criterion that depends on visual design or accessibility behavior;
  otherwise WARN and record the accepted risk in the report.

Routing:

- Setup gaps return to `/setup`.
- Missing baseline or product-surface decisions return to `/spec`.
- Missing matrix rows, task coverage, or Verify commands return to `/prepare_execute`.
