---
doc_type: report
authority: derived
status: active
audited_revision: 86f23ef
audit_date: 2026-07-22
implementation_status: implemented
---

# EZPowers Workflow Harness Independent Audit

## Scope and decision rule

This report records the pre-v5 live surface independently from the structure's
names or its passing tests. The audited baseline is Git revision `86f23ef`: 22
skills, 9 agents, 22 `docs/reference` documents, 22 tracked scripts, project
config/state, the v2 local kit, and the Claude/Codex plugin manifests.
`docs/archive/` was used only for history and is not current authority.

Each component is classified as follows:

- **Keep**: current responsibility still has distinct user value.
- **Strengthen**: distinct value exists, but self-containment, fail-closed
  behavior, parity, or user-flow testing is incomplete.
- **Integrate**: preserve only the valuable behavior in a simpler owner and
  remove the separate component.
- **Remove**: native host behavior or a simpler component fully replaces it.

Existence, passing tests, and compatibility alone are not retention evidence.
Retention requires project-specific deterministic completion, equal verdicts
on Claude Code and Codex, durable evidence/resume state, a fail-closed check
that prompt instructions cannot enforce, or a materially more trustworthy
user-visible result.

## Evidence and audit baseline

- `git status --short --branch` initially showed `main...origin/main` and only
  user-owned `.playwright-mcp/` and `.pytest-cache/` as untracked. They were
  preserved.
- Baseline verification before v5 work passed: 70 unit tests, the repository
  gate, the 14/14 harness runtime smoke, and the kit manifest verifier.
  Passing did not establish product fitness: the kit test copied manifest
  entries into a temporary directory but asserted only helper-file presence.
- `harness-kit/v2.0.0/manifest.json` installs
  `skills/README.md`, `contracts/README.md`, and helper scripts. It installs no
  `SKILL.md`, agent, or canonical contract body. Moreover,
  `scripts/verify-harness-kit.py` rejects any source whose filename is
  `SKILL.md`. A target project therefore cannot run the promised workflow from
  installed state alone.
- `tests/test_codex_plugin_discovery.py` validates manifest strings and static
  inventory, not a target-project workflow. Frontend and HUD runners have real
  behavioral unit tests; most skill/contract tests assert text or paths.
- `scripts/harness-smoke.ps1` creates an empty fake `execute.py`, and the broad
  runtime smoke exercises synthetic phases/executors. This verifies helper
  mechanics, not an external EasyPowersHarness user flow.
- Git history separates original intent from later implementation:
  `61ff376` (v0.3) centered project-local stack/build/test/lint configuration
  and host execution; `dbfe29f` (v0.4) later added the external
  EasyPowersHarness `execute.py` path and plan-to-phase conversion;
  `a7ed584` introduced the v2 kit; `009f274` migrated commands to skills.
- The v4 completion commit is `0cce191`, while `feature_list.json` still marks
  F10 `in_progress`. `PROGRESS.md` and F10 say 21 contracts, but the later HUD
  contract makes the live count 22.

Latest official host documentation was checked separately for
[Claude Code skills](https://code.claude.com/docs/en/skills),
[subagents](https://code.claude.com/docs/en/sub-agents),
[hooks](https://code.claude.com/docs/en/hooks),
[worktrees](https://code.claude.com/docs/en/worktrees), and
[sandboxing](https://code.claude.com/docs/en/sandboxing), and for Codex
[skills](https://learn.chatgpt.com/docs/build-skills),
[plugins](https://learn.chatgpt.com/docs/build-plugins),
[subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents),
[hooks](https://learn.chatgpt.com/docs/hooks), and
[worktrees](https://learn.chatgpt.com/docs/environments/git-worktrees).
The hosts are not assumed equivalent: Claude's native Windows sandbox requires
WSL2, Codex managed worktrees are a Desktop capability, Codex custom agents use
host-specific configuration rather than this repository's Claude agent
Markdown, and hook configuration/lifecycles differ. In particular, current
Codex Stop documentation uses `decision: "block"` plus `reason` to continue the
agent; `continue: false` stops the flow and is not the Codex equivalent of a
Claude block decision.

## Decisive findings

1. **The local kit is not a local workflow kit.** It copies mechanical helpers
   but none of the procedures and contracts that tell an agent how to use them.
2. **Path 2 is accidental product scope.** The numbered Path is an execution
   method choice, while `harness.root` is the external executor's filesystem
   location; they are related inputs, not the same concept. The external mode
   was introduced after the original project-local configuration workflow and
   remains disabled when `harness.root` is empty. External EasyPowersHarness is
   not installed by setup and is not part of the v5 target.
3. **Execution orchestration is over-owned.** Task graphs, agent prompts, model
   routing, generic retry, context compaction, reviewer dispatch, worktree, and
   sandbox policy duplicate host-native responsibilities and differ by host.
4. **The durable verification core is valuable.** Exact project commands,
   no-op rejection, timeout/exit handling, runtime/wiring observations,
   evidence fingerprints, certification, and freshness-aware resume are the
   defensible product center.
5. **Rules have drifted across too many sources.** Spec/plan schemas, wiring
   validation, reviewer placement, frontend readiness, model selection, and kit
   allowlists are repeated across skills, agents, contracts, scripts, and tests.
6. **Host parity is claimed more strongly than installed reality.** The Codex
   manifest exposes only skills. Reviewer dispatch depends on an unbundled
   `codex:codex-rescue` plus repository-relative `agents/*.md`; setup configures
   Claude settings but no equivalent Codex project installation.

## Skill inventory (pre-change: 22)

No pre-change skill body is installed by `/setup`; all require the plugin root.
“Native overlap” refers to current Claude Code/Codex capabilities, not an
assumption that both hosts implement them identically.

| Skill | Actual responsibility and call graph | Native overlap, unique value, and evidence | Decision and v5 action |
|---|---|---|---|
| `caveman` | User-triggered persistent compressed writing style; no workflow caller. | Complete overlap with host/user instructions; no deterministic evidence. | **Remove.** Unrelated cognitive surface. |
| `choice-execute` | Routes a plan among subagent, external harness, and inline paths; calls nearly every harness helper, implementer/reviewer agent, model routing, certification, resume, and docs sync. | Execution, agents, retry, routing, and context duplicate hosts. Exact Verify, evidence, certification, and resume freshness are unique. | **Integrate** valuable gates into one `execute`/CLI flow; remove all three Paths and this controller. |
| `deep-interview` | Clarifies rough requests; pre-change had no caller, stress-test mode, CONTEXT update, or ADR policy. | Conversation itself is native, but a consistent cross-host decision interview is useful. RED test reduced “grill me” to generic scope clarification. | **Strengthen.** Retain the name; absorb `grill-with-docs` as explicit `stress-test`, keep `spec` separate, and preserve offer-before-write ADR policy. |
| `deploy` | Reads delivery/verification/plan contracts and routes missing work to design, spec, prepare, or choice execution. | Generic release work is native. Project build, health, artifact, and rollback commands are valuable. | **Integrate** those checks into spec/plan/config and normal execute flow. |
| `design-architecture` | Produces architecture, testing method, structure, roadmap, lifecycle, and UI adapter; invokes frontend design and architecture review. | Design/research/subagents are native. Project-specific architecture and verification decisions are durable input to later checks. | **Strengthen** and slim to project decisions/check selection; no host orchestration. |
| `diagnose` | Six-stage reproduce/hypothesize/instrument/fix loop; called by `maintain`. | Native debugging and test-first diagnosis overlap; no durable workflow evidence of its own. | **Integrate** as host-native debugging guidance, then remove separate core skill. |
| `frontend-design` | Creates `docs/ux/frontend-design.md`; calls the visual-readiness detector. | UI design is partly native, but project tooling detection, state matrix, token/component, accessibility, and visual-oracle handoff are distinct. | **Keep**, decoupled from core harness; install with its required local artifacts. |
| `grill-with-docs` | Called by `spec` and directly by users; challenges terms, assumptions, alternatives, dependencies, scope, and edge cases; updates CONTEXT/ADRs. | Duplicates deep-interview interaction; domain durability is useful. | **Integrate** into `deep-interview stress-test`; remove separate public skill and references. |
| `handoff` | Writes numbered conversation handoff documents and workflow position. | Host compaction overlaps. Durable resume pointers are better derived from evidence/state. | **Integrate** into `status` and `.ezpowers/state.json`. |
| `hud` | Safely previews/installs/removes the EZPowers-owned global Codex TUI fragment through `codex-hud.py`. | Thin adapter over native status line. Ownership markers, conflict handling, atomic write, and hashes provide real safety. | **Keep**, explicitly plugin-only and independent of project setup. |
| `improve-codebase-architecture` | General codebase deepening review using Module/Interface/Depth/Seam vocabulary; called by `maintain`. | High native reasoning overlap; no deterministic harness evidence, but it is a standalone user utility. | **Keep** outside core; remove the stale instruction to use pipeline audit for harness product audits. |
| `maintain` | Classifies maintenance and routes to diagnose, architecture, spec, prepare, or execute. | Pure routing is host-native. | **Integrate** project checks into normal flow and remove. |
| `prepare-execute` | Converts spec requirements into coverage, task slices, exact Verify commands, wiring and agent assignment; invokes plan/UI reviewers and pipeline audit. | Agent assignment and task orchestration are native. AC-to-command traceability is unique. | **Strengthen** as a small plan/check compiler; remove agent assignment and audit dispatch. |
| `reset-setup` | Reinstalls the same manifest, migrates slots/config, records ledger, repairs Claude status line. | Duplicates setup and couples HUD/config. | **Integrate** as `setup --refresh`; preserve conflict-safe managed-file refresh. |
| `review` | Reviews diff/spec and optionally runs configured build/test/lint. | Native code review overlaps. Deterministic project checks remain valuable. | **Integrate** commands into verify/execute; use host-native review. |
| `set-rules` | Conversationally writes conventions, CLAUDE import, AGENTS pointer, optional `.claude/rules`, and optional hook checks. | Host-specific instruction editing, with no Codex parity. Project critical commands can be useful. | **Integrate** managed cross-host instruction blocks and required checks into setup. |
| `setup` | Detects project, creates config/state/docs slots, copies local kit, and offers Claude settings/statusline edits. | Host installation is adapter-specific. Project checks, managed-file ownership, migration, and hashes are core value. | **Strengthen** into a real self-contained installer with thin Claude/Codex adapters. |
| `spec` | Carries architecture into requirements and observable Given/When/Then/Verify criteria; invokes grill, three reviewers, and pipeline audit. | General spec writing is native. Host-neutral observable criteria are unique. | **Strengthen** around the acceptance contract; `deep-interview` becomes optional pre-work, not an embedded responsibility. |
| `sync-docs` | Scans code, updates generated reference docs, and auto-commits; workflow-runner invokes it after choice execution. | Native agent work; automatic commit violates the default no-commit boundary. | **Integrate** fact checks into explicit docs work; remove automatic chaining/commit. |
| `verifyself` | Chain-of-verification review of the agent's own judgment. | Native reasoning/review overlap; no independent oracle. | **Remove.** |
| `writing-skills` | TDD-style meta guide for authoring skills. | Duplicates official/system skill-authoring guidance and is unrelated to project completion evidence. | **Remove.** |
| `zoom-out` | One-sentence request for a higher-level module/caller map. | Fully native behavior. | **Remove.** |

## Agent inventory (pre-change: 9)

No agent is installed by setup. Claude plugin discovery can expose root agents,
but the Codex manifest has no equivalent agent component. The Codex dispatch
contract instead assumes the unbundled `codex:codex-rescue` and access to this
repository's `agents/*.md`.

| Agent | Actual callers and responsibility | Evidence value and overlap | Decision and v5 action |
|---|---|---|---|
| `architecture-reviewer` | Called by design/spec contracts; checks ASR, options, lifecycle, budgets, ADRs, and reference alignment. | Many checks are schema-like; LLM verdict is not deterministic and host availability differs. | **Integrate** mechanical checks into `validate`; use host review for judgment; remove agent. |
| `code-reviewer` | Called at choice-execute completion; reviews plan diff, evidence, invariants, dependencies, and observability. | Duplicates native review. | **Remove** after deterministic checks run. |
| `frontend-experience-reviewer` | Called during design/spec/plan UI stages; repeats frontend artifact/readiness rules. | Duplicates frontend contract, runner, and plan checks; verdict is model-dependent. | **Integrate** into frontend validator; remove agent. |
| `implementer-prompt` | Template filled by choice-execute for one-task subagents; requires commits, TDD, scope guard, and self-review. | Direct duplicate of host task agents and conflicts with no-auto-commit. | **Remove.** Host executes the plan. |
| `plan-reviewer` | Called by prepare-execute; checks coverage, exact task fields, impact scope, ICM, wiring, and TDD shape. | Large deterministic subset belongs in plan validation; subjective subset is native review. | **Integrate** then remove agent. |
| `security-reviewer` | Conditional choice-execute reviewer for input/auth/crypto/files/network/dependencies. | Native security review plus project SAST/dependency commands supersede it. | **Remove.** |
| `spec-reviewer` | Called by spec; validates requirement sections, vague language, Given/When/Then, Verify types, and negative ACs. | Mostly deterministic text/schema rules. | **Integrate** into spec validation; remove agent. |
| `wiring-reviewer` | Called when final wiring gate is `review_pending`; classifies TEST/CODE/SPEC gap. | Binding a verdict to an evidence fingerprint is valuable; an LLM verdict cannot replace observable entry-path evidence. | **Integrate** fingerprint/fail-closed mechanics into core; remove mandatory agent. |
| `workflow-runner` | Wrapper that runs only pipeline audit or sync-docs with scoped writes. | Extra dispatch layer adds no user value and is not Codex-local/self-contained. | **Remove**; core CLI validates state, explicit docs work updates docs. |

## Reference inventory (pre-change: 22)

The canonical contract bodies below are not installed in target projects.
Generated files with similar names are slots, not copies of the governing
contract.

| Reference | Actual responsibility and callers | Unique value, duplication, and installation | Decision and v5 action |
|---|---|---|---|
| `app-delivery-contract.md` | Repeats frontend/backend/package/deploy rules across setup, design, spec, plan, audit, and deploy. | Project build/health/rollback evidence is valuable; separate cross-stage contract causes drift. | **Integrate** into spec, plan, config checks, and verification. |
| `architecture.md` | Generated repository/project overview read by design/spec/review and maintained by design/sync. | Durable project architecture context is useful; no enforcement authority. | **Keep** as a project artifact, maintained explicitly rather than auto-sync ceremony. |
| `codex-hud.md` | Defines native Codex HUD fragment, ownership, install, verification, and removal. | Host-specific, tested, intentionally outside kit. | **Keep** decoupled. |
| `codex-plugin-discovery.md` | Documents Codex skill discovery, explicit invocation, cache refresh, and HUD separation. | Host asymmetry is real, but Claude behavior is missing from the title/scope. | **Strengthen** into a dual-host discovery contract; retain the historical filename so existing links do not become dead references. |
| `config.md` | Generated pointer to `.harness/config.json`; setup contract owns actual rules. | No independent rule or evidence. | **Integrate** into setup/config schema. |
| `conventions.md` | Generated output of set-rules and input to review. | Project rules matter, but a separate harness contract does not. | **Integrate** into managed host instructions and required checks. |
| `design-architecture-contract.md` | Owns architecture artifacts, ASR ledger, options, quality budgets, frontend, ADR, and phase state. | Project decisions are useful; phase/reviewer ceremony is duplicated. | **Keep and slim** to decision artifacts and check selection. |
| `dispatch-protocol.md` | Owns reviewer placement, Claude Agent calls, Codex rescue mapping, models, verdict parsing, and retries. | Nearly complete native-host duplication and not locally runnable on Codex. | **Remove.** |
| `domain-language.md` | Canonical vocabulary for phases, steps, gates, reviewers, evidence, and wiring. | Much vocabulary exists only because of layers being removed; definitions are repeated elsewhere. | **Integrate** retained terms into schemas/verification contract. |
| `frontend-design-contract.md` | Defines UI design artifact and tool-conditional Storybook/screenshot/visual readiness. | Distinct project readiness and observable UI oracle value; runner-backed. | **Keep and strengthen**, decoupled from core execution. |
| `harness-execution-contract.md` | Source of truth for external Path 2 and inline Path 3, plan conversion, steps, recovery, wiring, certificate, resume. | External path and separate execution layers are unnecessary; evidence concepts are useful. | **Remove** after evidence/certify/resume rules move to core. |
| `harness-kit-contract.md` | Defines manifest allowlist, no-synthesis, hashes, ledger, reset, and public chain. | Deterministic managed install is core, but current “no synthesis” policy results in no skills/contracts installed. | **Integrate** into v5 installer/manifest contract. |
| `model-routing-contract.md` | Defines profiles for reviewers, implementers, Codex CLI, and external harness. | Host owns model selection and availability; model tables age quickly. | **Remove.** |
| `pipeline-audit-contract.md` | D1-D9 cross-document gate run after spec and plan; writes phase audit verdict. | Cross-artifact traceability is valuable; a separate LLM workflow-runner gate is not. | **Integrate** deterministic dimensions into `validate`; remove gate/phase ceremony. |
| `plan-contract.md` | Owns coverage, exact commands, task shape, TDD slice, ICM, and wiring gate. | Exact criterion-to-command mapping is core; agent assignments and execution graph are native. | **Keep and slim.** |
| `project-structure.md` | Generated directory map maintained by design/sync. | Duplicates architecture/AGENTS and provides no machine verdict. | **Integrate** into architecture or AGENTS. |
| `protocol.md` | Pointer listing all other contracts. | No independent behavior; becomes stale when components change. | **Remove/integrate** navigation into `docs/INDEX.md`. |
| `schema.md` | Generated inventory of config/state/manifest files. | No schema enforcement. | **Integrate** actual JSON validation into CLI and document it near interfaces. |
| `setup-contract.md` | Owns detection, generated files, large config schema, kit install, Claude permissions/statusline, and phase initialization. | Setup ownership and project checks are core; app/model/HUD/external fields are over-coupled. | **Keep and slim** to install/config/migration/host adapters. |
| `spec-contract.md` | Owns architecture carry-forward, requirement schema, Verify, ADRs, reviewers, and audit transition. | Observable acceptance contract is core; reviewers/audit and mandatory grill chaining duplicate owners. | **Keep and slim.** |
| `testing-methodology.md` | Generated record of root/target test commands and UI adapter requirement. | Project-specific commands are valuable but belong in config/plan. | **Integrate** into design and verification inputs. |
| `verification-contract.md` | Canonical AC, Verify types, runtime, UI adapter, wiring, evidence, and quality gates. | Highest unique value; current text duplicates several scripts/agents and mixes host review with machine proof. | **Keep and strengthen** as the single semantic source for deterministic verdicts. |

## Script inventory (pre-change: 22)

“Kit” below means listed by the pre-change v2 manifest. Installed scripts are
still insufficient without controller skills/contracts.

| Script | Actual callers and behavior | Kit, evidence quality, and native overlap | Decision and v5 action |
|---|---|---|---|
| `check-repo.ps1` | `.githooks/pre-commit` and users call it for frontmatter, dead paths, version parity, kit, optional tests. | Not in kit; real repo gate, but hard-codes old workflow names and PowerShell. | **Strengthen/integrate** into cross-platform `check_repo.py`; retain this exact command as a thin wrapper. |
| `codex-hud.py` | `hud` skill manages a marked global Codex TOML fragment with preview, conflict detection, atomic write, hashes. | Plugin-only; extensive behavioral tests; thin native adapter with clear user value. | **Keep** decoupled. |
| `context-injector.py` | Builds/verifies sentinel-delimited context prompt blocks; choice-execute checks them. | In kit; tied to custom implementer prompt/context management now owned by hosts. | **Remove.** |
| `frontend-visual-readiness.py` | Detects project-local component isolation, screenshot, visual diff, mock/prototype lanes; detect/check modes. | In kit; real behavioral tests and deterministic frontend value. | **Keep** decoupled and make its local invocation self-contained. |
| `harness-certify.ps1` | Aggregates task gates/runtime artifacts into `completion-certificate.json`. | In kit; certification is valuable but tied to phase/step schema and PowerShell. | **Integrate** freshness-aware certification into Python core; remove script. |
| `harness-common.ps1` | Shared process, config, runtime/desktop/client-server evidence, task gate, model, and JSON helpers. | In kit; contains much load-bearing evidence logic but also routing and external harness coupling. | **Integrate** only evidence/process primitives into core; remove. |
| `harness-convert.ps1` | Converts plan tasks into phase context, step Markdown/index, and wiring gate. | In kit; entire layer exists for external executor and duplicates the plan. | **Remove.** |
| `harness-doctor.ps1` | Checks config, external harness root/execute.py, phase backup, smoke, wiring, reviewers, model routing, anchors/tools. | In kit; much preflight targets removed layers. | **Integrate** minimal install/config diagnostics into `ezpowers.py validate`; remove. |
| `harness-gate.ps1` | Runs/finalizes wiring gate and fingerprints evidence/reviewer verdict. | In kit; fail-closed fingerprinting is valuable, mandatory reviewer is not. | **Integrate** entry-path evidence/fingerprint into verify/certify; remove. |
| `harness-phase.ps1` | Displays phase status, resets a step, and invalidates task/runtime/certificate artifacts. | In kit; step control duplicates host execution. Invalidation semantics are useful. | **Integrate** evidence invalidation into state/status; remove. |
| `harness-resume-proof.ps1` | Proves a checked task prefix has fresh task-gate/runtime evidence. | In kit; strong unique resume value, but bound to plan checkboxes/phases. | **Integrate** freshness checks into `.ezpowers/state.json` and `status`; remove. |
| `harness-run.ps1` | Loops over external harness pending steps, invokes configured executor/model, records run log. | In kit; requires external `harness.root`/`execute.py`; host execution duplicate. | **Remove.** |
| `harness-runtime-smoke.ps1` | Broad synthetic regression suite for convert/doctor/run/gates/certify/resume/router/anchors/context/frontend. | Repo-only; 14/14 can pass with synthetic executor and does not prove target user flow. | **Strengthen/integrate** into Python user-flow smoke; retain exact command as thin wrapper. |
| `harness-smoke.ps1` | Creates a temporary fake harness, empty `execute.py`, plan, and synthetic project. | Repo-only; explicitly fake executor, so no external execution evidence. | **Remove.** |
| `hashline-anchor.py` | Creates/verifies per-line hash sidecars for generated step files. | In kit; supports redundant step representation, not plan/evidence freshness. | **Remove.** |
| `lightpath-gate.ps1` | Gives Path 1/3 prepare/task/final gates by reusing convert, Verify, runtime, wiring, reviewer, certificate. | In kit; adds parity only because three execution paths exist. Useful checks belong in one core. | **Integrate** into verify/certify; remove. |
| `model-router.py` | Resolves changing model names from stable profiles and availability cache for three backends. | In kit; host-native model selection/agent config supersedes it. | **Remove.** |
| `shared.py` | Timeout, progress, timestamp, and banned-language scan utilities. | Repo-only; small reusable logic, not a user interface. | **Integrate** needed primitives into new Python modules; remove standalone file. |
| `smoke-plugin.ps1` | Validates manifests, workflow skill strings, referenced files, and optional host discovery. | Repo-only; old hard-coded surface and PowerShell; mostly static assertions. | **Replace/integrate** with cross-host `plugin_smoke.py`; remove old script. |
| `statusline.py` | Project-local Claude status line installed by setup, showing time/context/usage. | In kit; independent Codex HUD now exists, and display is unrelated to verification core. | **Remove** from core/kit. Host-specific HUDs must remain explicit standalone features. |
| `verify-harness-kit.py` | Validates v2 public command list, helper allowlist, source hashes; forbids `SKILL.md`. | Repo-only; protects the non-self-contained design and tests no full workflow. | **Strengthen/rewrite** for the v5 project kit; retain required command compatibility. |
| `verify-step.py` | Parses generated step Markdown and performs structural/content/relational/command/static checks with timeout/no-op rejection. | In kit; real deterministic value, but shell/step representation is overbroad and some tests are synthetic. | **Integrate** safe argv execution and validators into `ezpowers.py`; remove step-specific layer. |

## Config, state, kit, manifest, and steering inventory

| Component | Actual role and current evidence | Decision and v5 action |
|---|---|---|
| `.harness/config.json` | Project commands plus app/UI/smoke/wiring, reviewer/model, retry, external `harness.root`, HUD-era fields. Root `harness.root` is empty. | **Strengthen/migrate** to minimal `.ezpowers/config.json`: project name, checks, required checks. Warn and ignore retired fields; do not silently delete user config. |
| `phases/index.json` | Setup/architecture/spec/plan/build phase, audit, docs-sync state. It says current phase setup while product work is F10. | **Integrate** into minimal `.ezpowers/state.json` containing active plan/evidence pointers and recomputable status. |
| `feature_list.json` | Product backlog/state machine F1-F10; F10 remains `in_progress` with empty evidence despite v4 completion commits. | **Keep and repair** to actual repository state; never use as task execution state. |
| `PROGRESS.md` | Human-readable current state/evidence/next actions; still frames external harness configuration as an open choice. | **Keep and update** to v5 reality; remove stale contract counts and external-path action. |
| `DECISIONS.md` | Session pointer with stale external Path 2 and retired eval decisions. Durable ADRs live elsewhere. | **Integrate/clean** as a pointer only; archive historical decisions or supersede explicitly. |
| `harness_versions/changelog.jsonl` | Append-only historical releases, including retired eval/command/external harness references. | **Keep as history**, never live authority; add v5 transition without rewriting old entries. |
| `AGENTS.md` | Cross-host entry, current flow, paths, contract precedence, verification commands. | **Strengthen** as the small cross-host entry; point to v5 flow and actual local interfaces. |
| `CLAUDE.md` | Full inventory and Claude-oriented procedures, but also claims Codex behavior and external harness flow. | **Integrate/slim** to Claude adapter guidance; shared semantics belong in cross-host/local artifacts. |
| `docs/INDEX.md` | Navigates product, contracts, specs/plans, decisions, archive; currently registers all 22 references as live. | **Keep and update** atomically with contract removal/rename and this report. |
| `.githooks/pre-commit` | Calls only the PowerShell repo gate; fails when PowerShell is unavailable. | **Strengthen** to call cross-platform Python core while retaining the PowerShell compatibility command for users. |
| `harness-kit/v2.0.0/manifest.json` | Hashes helper scripts; advertises old public commands/internal adapters; contains no real skills/contracts. | **Replace** with versioned v5 project-kit manifest containing runnable local skills/runtime and managed-file metadata. |
| `harness-kit/v2.0.0/skills/README.md` | Placeholder saying setup installs this directory but contains no skill. | **Remove** with v2 kit; real skill trees replace it. |
| `harness-kit/v2.0.0/contracts/README.md` | Placeholder saying setup installs contracts but contains no contract. | **Remove** with v2 kit; retained semantics must be bundled or compiled into local runtime/skills. |
| `.claude-plugin/plugin.json` | Claude package metadata v4.0.3; relies on root directory conventions and advertises old flow/reviewer agents. | **Strengthen** to v5 surface/version; keep Claude-specific discovery truthful. |
| `.claude-plugin/marketplace.json` | Marketplace entry duplicating Claude description/version. | **Keep synchronized** with Claude manifest; update only actual public surface. |
| `.codex-plugin/plugin.json` | v4.0.3+build manifest exposing only `./skills/`; default prompts advertise diagnose/verifyself and old choice flow. | **Strengthen** to the retained v5 skill surface; do not claim agents or slash commands; keep cachebuster/version parity. |
| `.agents/plugins/marketplace.json` | Repository-local Codex marketplace entry points at this plugin root and controls availability/install metadata. | **Keep and validate** as a Codex-specific discovery adapter; it must advertise only the current local `ezpowers` plugin. |

## Implemented v5 live-surface disposition

The inventories above classify every component that was live at the audited
revision. This section separately accounts for every logical component left or
created by the v5 implementation. Files under a skill's `agents/` directory
are Codex display/invocation metadata, not custom subagents. There are no live
custom agent definitions in v5.

| Live skill | Final decision | Retention evidence and installed behavior |
|---|---|---|
| `setup` | **Keep** | Installs or conflict-safely refreshes the complete hashed local kit, migrates safe project checks, and optionally writes thin host hooks. Installed for both hosts. |
| `deep-interview` | **Keep/Integrate** | One cross-host name now owns clarification and the former grill stress-test behavior; domain context/ADR writes remain conditional. Installed for both hosts. |
| `design-architecture` | **Keep** | Persists project-specific boundaries and verification choices used by specs/plans; no longer dispatches reviewers or phases. Installed for both hosts. |
| `spec` | **Keep** | Turns settled decisions into observable, validated acceptance criteria; it is deliberately separate from interview behavior. Installed for both hosts. |
| `prepare-execute` | **Keep** | Maps each criterion exactly once to safe argv checks and ordered slices without owning task execution. Installed for both hosts. |
| `execute` | **Keep/Integrate** | Thin handoff to host-native implementation plus explicit plan activation, deterministic verify, certify, and resume reporting. Installed for both hosts. |
| `frontend-design` | **Keep** | Produces project-specific UI readiness/design artifacts and calls the non-installing detector only when relevant. Installed for both hosts, independent of non-UI completion. |
| `improve-codebase-architecture` | **Keep** | Standalone product-code architecture utility with no claim to audit this workflow harness. Installed for both hosts, outside completion authority. |
| `hud` | **Keep** | Safely manages only the owned Codex TUI fragment. Plugin-only; deliberately absent from project setup. |

| Live contract/reference | Final decision | Single responsibility |
|---|---|---|
| `setup-contract.md` | **Keep** | Canonical install, managed ownership, config, state, migration, and thin-hook rules. |
| `design-architecture-contract.md` | **Keep** | Canonical durable architecture-decision artifacts and verification design. |
| `frontend-design-contract.md` | **Keep** | Canonical optional UI readiness and observable frontend-oracle rules. |
| `spec-contract.md` | **Keep** | Canonical acceptance-criterion schema and semantics. |
| `plan-contract.md` | **Keep** | Canonical criterion coverage, task, and exact-check schema. |
| `verification-contract.md` | **Keep/Strengthen** | Sole authority for exact execution, evidence, freshness, certification, task resume, and hook verdicts. |
| `architecture.md` | **Keep** | Current product boundary/data-flow reference; it does not override contracts. |
| `codex-plugin-discovery.md` | **Keep** | Records tested Claude/Codex discovery differences and cache/trust requirements. |
| `codex-hud.md` | **Keep** | Isolated contract for the opt-in global Codex utility. |

| Live script | Final decision | Caller and evidence |
|---|---|---|
| `ezpowers.py` | **Keep/Strengthen** | Installed runtime called by all eight project skills and optional hooks; executes safe argv, binds evidence, revalidates task/all pointers, certifies, and installs without third-party packages. |
| `verify-harness-kit.py` | **Keep/Strengthen** | Repository/release gate that verifies every manifest source hash and logical installed item; `--stamp` is an explicit maintainer action. |
| `check_repo.py` | **Keep** | Cross-platform repository structural gate used directly and by pre-commit. |
| `check-repo.ps1` | **Integrate** | Thin Windows adapter preserving the required command while delegating all rules to `check_repo.py`. |
| `runtime_smoke.py` | **Keep/Strengthen** | Creates a real temporary Git project and runs install, managed-plan validation, real unittest, all-scope evidence, certification, and stale detection. |
| `harness-runtime-smoke.ps1` | **Integrate** | Thin Windows adapter for `runtime_smoke.py`; contains no second test implementation. |
| `plugin_smoke.py` | **Keep/Strengthen** | Validates both manifests/marketplaces and probes Claude/Codex independently where their CLIs are available, using installer output for Codex. |
| `frontend-visual-readiness.py` | **Keep** | Deterministic, non-installing project tooling/readiness detector with behavioral tests. |
| `codex-hud.py` | **Keep** | Conflict-safe, ownership-marked preview/install/remove adapter for native Codex configuration, with behavioral tests. |

| Live config/state/distribution adapter | Final decision | Reason |
|---|---|---|
| `.ezpowers/config.json` | **Keep** | Minimal project-specific named and required argv checks; validated independently of plans. |
| `.ezpowers/state.json` | **Keep/Strengthen** | Durable active-plan and artifact pointers only; malformed state fails closed and every task/all pointer is revalidated. |
| `project-kit/v5.0.0/manifest.json` | **Keep/Strengthen** | Hash-bound allowlist for all installed runtime, skill, contract, metadata, and tool bytes. |
| `.claude-plugin/plugin.json` and marketplace | **Keep** | Claude-specific package discovery only; no Codex capability claims. |
| `.codex-plugin/plugin.json` and `.agents/plugins/marketplace.json` | **Keep** | Codex-specific skill discovery, cachebuster, ordering, and availability metadata; no custom-agent claim. |
| `.githooks/pre-commit` | **Keep/Strengthen** | Optional local fail-closed entry to the cross-platform repository gate with explicit Python interpreter fallback. |

The manifest's logical project-kit items are individually retained and hashed:
the `ezpowers.py` runtime; `setup`, `deep-interview`, `design-architecture`,
`spec`, `prepare-execute`, `execute`, `frontend-design`, and
`improve-codebase-architecture` skill trees (including their listed metadata
and references); the six canonical contracts named above; and
`frontend-visual-readiness.py`. Each skill tree is installed as a canonical
`.ezpowers/kit` copy and byte-identical `.claude/skills` and `.agents/skills`
copies. The runtime, manifest, ledger, and every managed target participate in
the installed identity. A regression flow deletes the source distribution
after installation and still reaches `CERTIFIED`, so no hidden plugin checkout
or external EasyPowersHarness is required.

## Implemented v5 architecture

```text
Claude Code / Codex
  ├─ native: implementation, subagents, model choice, retry, review,
  │          worktree, sandbox, and general context management
  └─ thin host adapter
       └─ project-local EZPowers
            ├─ spec and plan acceptance artifacts
            ├─ .ezpowers/config.json (safe argv project checks)
            ├─ .ezpowers/state.json (active plan/evidence pointers)
            ├─ .ezpowers/evidence/ (logs, hashes, verdicts)
            └─ ezpowers.py
                 ├─ install / migrate / validate
                 ├─ status
                 ├─ verify
                 ├─ certify
                 └─ optional host hook adapter
```

Target invariants:

- The installed project contains every skill/runtime artifact needed for its
  promised local workflow. A shared external repository is never implicit.
- `deep-interview` settles ambiguous or challenged decisions; `spec` records
  settled observable acceptance; `prepare-execute` maps criteria to exact safe
  argv checks; the host implements; `execute` verifies and certifies.
- Configured commands are argv arrays with project-relative working
  directories and timeouts, executed without a shell by default. Placeholder
  or no-op checks fail validation.
- Evidence binds command result, timeout, duration, stdout/stderr logs or
  hashes, spec/plan/config hashes, installed-kit identity, Git HEAD, and
  dirty/untracked content fingerprint. Certification accepts only fresh PASS
  evidence matching the current workspace and runtime distribution.
- Claude and Codex adapters call the same local verdict engine. Hooks are
  optional and host-specific; their semantics are not treated as identical.
- External EasyPowersHarness, `harness.root`, `execute.py`, plan-to-phase
  conversion, separate steps, model router, workflow-runner, and mandatory
  reviewer agents have no v5 core role.
- Frontend readiness and the Codex HUD remain independent capabilities. They
  do not become prerequisites for non-UI verification.

## Implemented regression and acceptance coverage

The v5 automated coverage establishes:

1. A temporary target project can install, then run validate/status/verify/
   certify after the source plugin path is made unavailable.
2. The same plan/config/workspace yields the same core verdict through Claude
   and Codex adapters.
3. PASS, command failure, timeout, no-op, missing command, plan/config change,
   source change, untracked-content change, and evidence tampering are handled
   fail-closed.
4. Resume accepts only fresh evidence and never plan checkboxes or agent prose.
5. Refresh replaces only unchanged managed files, preserves user edits, and
   reports conflicts without destructive overwrite.
6. Legacy `.harness` migration preserves command-bearing user data, warns for
   retired model/reviewer/HUD/external fields, and does not delete the source.
7. Static skill-contract coverage checks that `deep-interview` declares
   `stress-test` for `grill me`, `그릴미`, and literal `grill-with-docs`, and
   requires resolution before domain-context or qualifying ADR writes. This is
   not a model-behavior test.
8. Plugin packaging is exercised through Claude's non-installing validator and
   Codex project discovery from actual installer output where those CLIs are
   available, rather than only manifest-string tests.
9. No live invocation or advertised path targets a removed skill, agent,
   contract, script, Path 2, `harness.root`, `execute.py`, or stale eval/trace
   command. Remaining names occur only in history/ADRs, explicit legacy
   migration warnings, trigger aliases, or negative repository gates.

The final suite contains 82 tests. The repository gate, real runtime smoke,
project-kit hash verifier, and both-host plugin smoke pass. The runtime suite
also covers read-only candidate validation, explicit plan activation,
revalidated task `MISSING`/`FRESH_PASS`/`STALE` states, orphan reporting, and
the rule that task evidence never promotes the all-scope completion verdict.
Claude local-skill mode selection and the conversational question/write order
remain prompt contracts rather than deterministic runtime claims.

Repository completion commands remain:

```powershell
python -m unittest discover -s tests
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/check-repo.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/harness-runtime-smoke.ps1
python scripts/verify-harness-kit.py
```

Plugin discovery/wiring smoke and direct Python checks are additionally
required when their surfaces change. Final acceptance must include
`git diff --check`, a live-reference search, state/manifest consistency, and an
independent reread of the complete diff. No verification command or runtime
evidence rule may be weakened to make the transition pass.
