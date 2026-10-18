# EZPowers Roadmap

## Current: v5.8.0 core and plugin

- Select one project-level `software` or `planning` profile at setup and allow
  only explicit later migration without coupling profile changes to refresh.
- Preserve config/plan v1/v2 software behavior while making planning config/
  plan v3 fail closed on older or mismatched runtimes.
- Bind arbitrary binary/text inputs, multi-file logical deliverables, exact
  criterion/check coverage, and direct or project-inspected review sources.
- Hash declared inputs and outputs independently of Git ignore state and reject
  missing, symlinked, or verification-mutated artifacts.
- Require per-deliverable `artifact-review` for planning chains while retaining
  `code-review` for software and conditional adversarial QA for both.
- Preserve software validation/trace outputs and hold median regression to at
  most 5% across five interleaved baseline/candidate runs.

- Derive one typed criterion-to-task-to-check-to-evidence-to-review-to-
  certificate assurance graph from existing authorities; do not create a
  second editable graph or implementation state machine.
- Add compatible plan/config v2 with required acyclic task dependencies,
  stable topological waves, a bounded worker cap, and per-check safety/resource
  locks. Preserve all v1 plans/configs as serial without automatic rewriting.
- Add `trace --plan ... --json`, graph-bound v2 evidence/certificates, and
  graph-bound chain approvals with explicit legacy reapproval.
- Allow only the measured `repo-check`, `kit-manifest`, and file-only plugin
  smoke checks to opt into concurrency in this repository; keep unit and
  runtime smoke serial barriers.
- Gate the optimisation on serial/parallel equivalence and at least 30%
  median improvement across three matched controlled runs, then repeat the
  measurement on the allowlisted repository checks.

- Preserve the v5.1 documentation graph and local wiki.
- Add an explicit project-question workflow for chain stages, QA triggers,
  enabled hosts, and hard retry/continuation limits.
- Require a real isolated baseline and a host-native independent oracle audit
  before one feature approval.
- Freeze spec, plan, oracle, config, checks, and approval by hash; require a
  new approval after any change.
- Use one native Codex goal or one Claude Stop loop, never a duplicated
  cross-host executor.
- Bind independent code-review and conditional adversarial-QA receipts to the
  exact fresh evidence before certification.
- Make limit exhaustion terminal on the attempt that reaches the limit.
- Add pinned, adapted `diagnose`, `codebase-design`, and
  `improve-codebase-architecture` disciplines with diagnosis/write,
  architecture-document, and completion-authority boundaries.
- Make explicit `diagnose` and fix/debug requests fix-complete by default:
  reproduction and root cause are progress, while the source-cause patch,
  original-symptom rerun, affected checks, and cleanup are completion gates.
- Make exact-red reproduction and minimisation a hard gate before diagnose can
  state hypotheses or edit product behavior; when the gate cannot be opened,
  require the specific missing access, capture, or instrumentation instead of
  a speculative patch.
- Render broad architecture reviews through a deterministic standard-library
  tool into a unique temporary offline HTML report.
- Enforce Claude Code 2.1.217 and Codex CLI 0.145.0 before host-specific
  project hook writes, and treat all pre-v5 workflow input as retired.
- End `deep-interview` with a single choice to confirm and proceed, correct,
  or confirm and finish with the summary. Ordinary-mode proceed resumes host
  work through relevant verification; Plan Mode proceed continues planning
  only. Clarification remains in the conversation without artifact creation.
- Make `deep-interview` distinguish stated ambiguity from plausible
  consequential blind spots, challenge framing only when material, and avoid
  ritual questions for requests that are already settled.
- Add a compact implicit `explain-with-evidence` presentation skill that
  follows the user's active conversational language, uses only observed
  alternatives and measurements, and leaves fixed artifacts and exact verdicts
  unchanged.
- Keep the broad frontend readiness document while adding root/app-local
  `DESIGN.md` as the authoritative token and reusable-component contract.
- Pin a selectively adapted Google design.md alpha profile and ship offline
  standard-library lint, diff, mapping, and explicit upstream-review tools;
  do not add token export or code generation.
- Carry design context through new specs, plans, execute, managed documentation
  checks, and explicit harness-chain frozen inputs while leaving legacy specs
  and old profiles readable until explicit migration.
- Keep canonical architecture in standard Markdown, create it only for real
  structural boundaries, record feature impact before implementation, and
  freeze affected artifacts in explicit harness-chain approvals without a
  second architecture state machine.
- Keep one exact catalog: fourteen plugin skills, thirteen project skills, and
  separate namespaced versus project-local Codex prompt metadata.
- Upgrade existing pre-v5.8 installations only through explicit
  `setup --refresh`;
  preserve customized managed files and fail atomically on conflicts.

## Later, only with demonstrated demand

- Complete F19's authenticated live Claude and sandbox-capable Codex diagnose
  probes when both external host environments are available; v5.8 does not
  claim those deferred probes.

- Real visual-baseline generation and visual-diff execution behind the current
  frontend readiness detector.
- Optional richer documentation templates only where repository evidence shows
  that the adaptive graph is insufficient.
- Additional host adapters when their official APIs provide a measurable user
  benefit that the shared verdict alone cannot deliver.
- Additional third-party engineering skills only when a bounded role,
  maintenance owner, and deterministic validation justify expanding the core
  catalog.

Model routing, bundled reviewer fleets, generic host-independent retries,
host-independent implementation task graphs, phase conversion, and an
external executor are not roadmap items; supported hosts already own those
execution concerns. The profile-aware assurance graph is a derived
verification view, not an exception to that boundary.
