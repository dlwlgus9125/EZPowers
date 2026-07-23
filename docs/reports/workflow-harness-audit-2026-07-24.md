---
doc_type: report
authority: supporting
status: active
---

# Workflow And Harness Audit — 2026-07-24

## Verdict

The v5.2 workflow is coherent after cleanup: ten skills are available from the
plugin, nine are installed into projects, and one deterministic runtime owns
configuration, checks, evidence, certification, documentation state, wiki
state, and the explicit harness-chain verdict. Claude Code and Codex retain
implementation and orchestration authority.

The audit found two live defects and three unnecessary legacy surfaces:

1. Codex plugin metadata used project-local `$<name>` prompts even though
   installed plugin skills are namespaced as `$ezpowers:<name>`.
2. The Codex smoke exercised only implicit prompt injection, so explicit-only
   skills could be broken without failing verification.
3. Setup still interpreted retired pre-v5 workflow input.
4. The HUD silently recognized and upgraded an older managed fragment.
5. A redundant architecture advisory, superseded kit manifests, duplicate
   decisions, and historical generated reports remained in the live tree.

All five are corrected in this change. No evidence, freshness, approval, or
verification rule was weakened.

## Scope And Method

The audit used repository evidence rather than prior conversation:

- canonical guidance, product state, manifests, contracts, skills, metadata,
  runtime, hook builders, HUD helper, tests, and distribution hashes;
- exact live file and skill inventories;
- Claude 2.1.217 manifest validation;
- Codex 0.145.0 isolated project installation, temporary local-plugin
  installation under a temporary `CODEX_HOME`, app-server `skills/list`, and
  prompt-input discovery;
- focused regression tests followed by every repository verification command
  in `AGENTS.md`;
- final diff, whitespace, removed-reference, and dead-path review.

The generic plugin-creator validator is not treated as the dual-host
frontmatter authority: it requires `disable-model-invocation` to be false and
therefore rejects all seven intentional Claude explicit-only skills. The
repository validator accepts only the documented Claude/Codex union used here,
and actual Claude validation plus Codex `skills/list` are required in
addition.

## Skill Decisions

| Skill | Decision | Evidence-backed boundary |
| --- | --- | --- |
| `setup` | Keep and strengthen | Sole installer/documentation bootstrap; now uses a clean pre-v5 boundary and host-version preflight. |
| `deep-interview` | Keep | Session-only clarification with no artifact or execution authority. |
| `design-architecture` | Keep | Settles technical boundaries and verification design before specification. |
| `spec` | Keep | Owns traceable acceptance criteria only. |
| `prepare-execute` | Keep | Owns criterion coverage and exact checks only. |
| `execute` | Keep | Activates a settled plan and delegates implementation to the host before verify/certify. |
| `frontend-design` | Keep | Independent UI-readiness advisory with a distinct artifact and trigger. |
| `wiki` | Keep | Local supporting knowledge with deterministic lifecycle and no completion authority. |
| `harness-chain` | Keep | Explicit, approval-bound composition of existing artifacts, native continuation, review receipts, and terminal limits. |
| `hud` | Keep and strengthen | Plugin-only global Codex utility; install now requires Codex 0.145.0 and preserves every non-current block as user-owned. |
| `improve-codebase-architecture` | Remove | General refactoring advice overlapped native reasoning and produced no unique managed artifact or runtime evidence. |

The resulting catalog is exact:

- plugin: `setup`, `deep-interview`, `design-architecture`, `spec`,
  `prepare-execute`, `execute`, `frontend-design`, `wiki`, `harness-chain`,
  and `hud`;
- project kit: the same catalog without plugin-only `hud`.

## Runtime And Harness Decisions

| Surface | Decision |
| --- | --- |
| `scripts/ezpowers.py` | Keep as the single standard-library runtime. Remove retired config migration; add write-before-version preflight for selected host features. |
| `.ezpowers/config.json` | Keep the small exact-argv v5 schema. Retired pre-v5 files are ignored and preserved, never translated. |
| Documentation graph and wiki | Keep. They are independently owned, linted, and excluded from accidental completion authority. |
| Ordinary Stop and SessionEnd hooks | Keep opt-in. Their distinct verdict/privacy roles and host-specific schemas remain tested. |
| Explicit harness-chain hooks | Keep opt-in and asymmetric. Configuration now reports and enforces selected-host minimum versions before writes. |
| `scripts/check-repo.ps1` | Keep the one repository entry point; remove the unused `ChangedFiles` compatibility parameter. |
| `scripts/plugin_smoke.py` | Strengthen with exact dual metadata validation and actual Codex `skills/list` for all explicit and implicit skills. |
| `scripts/codex-hud.py` | Keep. Remove silent legacy-fragment upgrade and require Codex 0.145.0 before install. |
| Project-kit history | Keep only the current v5.2 manifest in the live distribution. |
| Historical archive and root decisions | Remove. ADRs, changelog, current product state, and this audit retain the useful decisions without duplicate authority. |

## Codex Metadata Repair

Plugin invocation and project invocation require different prompts:

```text
plugin metadata:  $ezpowers:<name>
project metadata: $<name>
```

Each of the nine project skills now has a `project-openai.yaml` distribution
variant. The v5.2 manifest copies that file to the installed Codex metadata
path while the plugin continues to use `openai.yaml`. Display names, short
descriptions, and invocation policy must match; only the invocation token may
change.

The smoke installs a compact copy of the plugin into a temporary local
marketplace and filters discovered skills by the actual installed plugin path.
It then requires exact names, `enabled: true`, no load errors, and exact
default prompts. Global plugin state is never changed.

## Compatibility Floor

The supported minimums are:

| Host | Minimum | Enforced when |
| --- | --- | --- |
| Claude Code | 2.1.217 | Claude completion/wiki hook install and Claude harness-chain configuration |
| Codex CLI | 0.145.0 | Codex completion/wiki hook install, Codex harness-chain configuration, HUD install, and host smoke |

Basic project-kit installation remains host-CLI independent. Status, preview,
and safe HUD removal also remain available when the install prerequisite is
not met.

## Removed Live Material

- the redundant `improve-codebase-architecture` skill tree;
- the root `DECISIONS.md` duplicate;
- all files under the former `docs/archive/` directory;
- the superseded v5.0 and v5.1 project-kit manifests;
- the 2026-07-22 audit, replaced by this current record;
- retired migration code, migration-warning state, an unused PowerShell gate
  parameter, and HUD legacy-fragment recognition.

## Verification Record

| Check | Result |
| --- | --- |
| `python -m unittest discover -s tests` | PASS — 134 tests in 530.261 seconds |
| `scripts/check-repo.ps1` | PASS |
| `scripts/harness-runtime-smoke.ps1` | PASS — real install → validate → verify → certify → stale |
| `python scripts/verify-harness-kit.py` | PASS — v5.2, nine project skills, nine contracts |
| `python scripts/plugin_smoke.py --host both` | PASS — Claude 2.1.217 manifests; Codex 0.145.0 project and plugin `skills/list` plus prompt-input |
| `python scripts/plugin_smoke.py --host both --live-advisory` | PARTIAL — Codex behavior PASS; Claude loader PASS, model request blocked by external HTTP 401 authentication, zero cost |
| Final diff and `git diff --check` | PASS — no whitespace errors; planned removals and pre-existing user changes preserved in the final review |
