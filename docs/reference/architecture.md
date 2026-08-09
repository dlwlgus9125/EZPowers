---
doc_type: reference
authority: canonical
status: active
---

# Architecture

EZPowers is a thin, dual-host project workflow plus a deterministic,
project-local verification runtime. It does not replace Claude Code or Codex as
the execution host.

## System Context And Product Boundary

The host owns code editing, shell execution, subagents, worktrees, sandbox and
approval policy, review, and retry decisions. EZPowers owns only the parts that
must remain stable across hosts and sessions:

- settled project intent and architecture decisions;
- a repository-evidenced Markdown graph with explicit ownership and lint;
- paired frontend UX and nearest DESIGN.md contracts with pinned offline
  profiles and deterministic mapping/diff validation;
- one managed JSON contract in each feature spec and plan;
- project-specific checks represented as exact argument arrays;
- check output, hashes, workspace freshness, certification, and resume state;
- optional worktree-local session knowledge that has no completion authority;
- explicit, hash-frozen feature approvals, bound independent-review receipts,
  and hard terminal limits when a harness chain is requested;
- thin, optional host hook adapters over the same completion verdict.

There is no second executor, numbered execution path, parallel task-state
machine, or generic host-independent orchestration policy in the v5
architecture. The optional chain composes the existing artifacts and verdict;
the selected host still performs every implementation action.

## Distribution And Installation

The plugin repository contains the fourteen retained skills and the Claude and
Codex manifests. `setup` installs the project kit into the target repository:

```text
plugin distribution
  -> .ezpowers/                  canonical runtime, config, state, ledger, kit
  -> .claude/skills/             Claude project skill copies
  -> .agents/skills/             Codex project skill copies
  -> .claude/settings.json       optional Claude Stop adapter
  -> .codex/hooks.json           optional Codex Stop adapter
  -> AGENTS.md + docs/           separately previewed documentation graph
  -> .ezpowers/wiki/             optional local session knowledge
  -> .ezpowers/chain.json        explicitly configured chain policy
  -> .ezpowers/approvals/        immutable feature approvals
  -> DESIGN.md                   separately previewed normative visual tokens
```

The installed `.ezpowers/ezpowers.py` is standard-library only and is the
runtime entry point after installation. The kit is self-contained: installing
or repairing a project must not require this checkout, another repository, or
a hidden user-local script. The target project root is also the Git worktree
root because Git state is part of every completion fingerprint.

Thirteen skills are installed in a project, including
`explain-with-evidence`, `diagnose`, `codebase-design`,
`improve-codebase-architecture`, `wiki`, and
`harness-chain`.
`hud` is
intentionally excluded from the project kit. It is a plugin-only, global Codex
opt-in described in `docs/reference/codex-hud.md`.

## Workflow And Data Flow

```text
setup
  -> documentation preview/apply/lint
  -> deep-interview (while material ambiguity or a plausible consequential
                     blind spot remains)
  -> frontend-design (for UI: broad artifact + mapped DESIGN.md)
  -> design-architecture
  -> spec
  -> prepare-execute
  -> execute with host-native facilities
  -> .ezpowers verify --all
  -> .ezpowers certify

explicit harness-chain
  -> project questions + hash-bound config apply
  -> staged spec/plan/oracle + isolated baseline
  -> bound independent oracle audit
  -> one feature approval
  -> one native Codex goal OR one Claude Stop loop
  -> implement/rework + verify --all
  -> bound code review + conditional adversarial QA
  -> certify or terminal verdict
```

`deep-interview` remains session-only. It checks stated gaps and performs a
context-specific internal blind-spot pass, exposing only plausible candidates
that could materially change the request. When invoked inside an already
active Plan Mode, explicit confirmation returns the clarified intent to that
same host mode so planning can finish without a second command. It does not
invoke `design-architecture`, `spec`, or an execution workflow, and it grants
no implementation authority.

`explain-with-evidence` is an implicit presentation discipline around
user-facing explanations and result reports. It infers language from the
latest substantive natural-language request, falls back to recent conversation
when needed, and uses only alternatives, reversals, measurements, and
verification actually observed. It does not reshape specs, plans, JSON,
receipts, certificates, or exact completion states, and it adds no task or
workflow authority.

`diagnose` and `codebase-design` are implicit disciplines inside the current
request. Explicit diagnose invocation or fix/debug intent selects an
end-to-end path, but exact-red reproduction and minimisation are hard gates
before hypotheses or product-behavior edits. An adjacent failure or merely
red-capable command is not enough. If exact red cannot be produced, the host
requests the missing access, capture, or instrumentation and does not guess.
After the gate it continues through first-divergence evidence, a regression
signal, source-cause patch, original-symptom rerun, and affected checks. Only
an explicit analysis-only/no-edit request stops a reproducible path at
evidence.
`codebase-design` compares focused module interfaces and honest seams.
`improve-codebase-architecture` is explicit-only. It scans existing product
code within a frozen scope and invokes the same standard-library renderer
through a skill-local resolver in project and plugin installations. Report
schema v2 binds real source lines, decision context, semantic before/after
graphs, and input/source/report hashes in an escaped, dependency-free HTML
report under the OS temporary directory. Interface design begins only after
the user selects a candidate. The scan preserves Git status and neither
replaces `design-architecture` nor owns durable architecture artifacts.

`spec` records host-independent observable criteria. `prepare-execute` maps
each criterion to exact project checks. `execute` does not create a second
task-state machine; it implements the plan and asks the local runtime for the
completion verdict.

New specs also state whether a design context applies. UI specs carry the
broad frontend artifact and every applicable nearest `DESIGN.md`; plans and
execute preserve the same mapping. DESIGN.md tokens outrank implementation
drift. The installed standard-library validator follows a pinned, selective
Google alpha profile and uses a locally installed exact official CLI only as a
`--no-install` cross-check.

`harness-chain` does not replace this data flow. It freezes the chosen inputs,
adds explicit approval and independent-evidence gates, and records bounded
resume state. Codex Stop observes its native goal; Claude Stop supplies
continuation. The runtime never assigns implementation tasks or chooses a
review model.

Documentation bootstrap is orthogonal to feature planning. Setup analyzes
repository evidence, stages whole-file Markdown proposals, and presents a
hash-bound preview. Apply preserves unmanaged or edited files unless explicit
adoption and force-backed replacement are approved. `.ezpowers/docs.json`
holds the graph and `ezpowers.docs` becomes a required check. `AGENTS.md` is
canonical; `CLAUDE.md` is only `@AGENTS.md`.
Graphs with DESIGN.md also register `ezpowers.design`; unmanaged design files
and profile migrations require the same explicit preview/adoption/backup
boundary as other repository documentation.

The optional `.ezpowers/wiki/` stores candidates, a derived index, a local
operation log, and backups. Keyword/tag search supports CJK without an
embedding service. Promotion binds a page to an already-authored canonical
document; it does not write or own that document. SessionEnd capture is
separately opt-in and retains only allowlisted repository metadata.

The runtime executes checks without an implicit shell, stores logs and hashes
under `.ezpowers/evidence/`, and binds a PASS to the current spec, plan,
config, installed-kit identity, Git HEAD, tracked diff, and untracked-file
digest. A bounded project-local lock serializes state writers.
`.ezpowers/state.json` holds only revalidated resume pointers; it never turns a
stale result into PASS. Plan validation is read-only until execution explicitly
activates a resume target. Task-scope pointers are independently revalidated
for resume guidance but cannot promote the all-scope completion verdict.

## Source Of Truth

- Architecture and testing decisions: project architecture artifacts.
- Observable feature claims: the spec managed JSON block.
- Task coverage and exact commands: the plan managed JSON block plus named
  checks in `.ezpowers/config.json`.
- Completion: fresh all-scope evidence and its certificate.
- Host discovery and adapter differences:
  `docs/reference/codex-plugin-discovery.md`.
- Documentation ownership and graph rules:
  `docs/reference/documentation-contract.md`.
- Architecture creation, maintenance, and no-second-state decision:
  `docs/reference/design-architecture-contract.md` and
  `docs/decisions/0006-architecture-artifact-lifecycle.md`.
- Frontend artifact split, DESIGN.md mapping, pinned profile, and maintenance:
  `docs/reference/frontend-design-contract.md` and
  `docs/reference/design-md-profile.json`.
- Local wiki, promotion, pruning, and capture privacy:
  `docs/reference/wiki-contract.md`.
- Explicit chain configuration, approval, independent receipts, limits, and
  host asymmetry: `docs/reference/harness-chain-contract.md`.
- Evidence and freshness rules: `docs/reference/verification-contract.md`.

Human-readable Markdown may explain these contracts but must not duplicate or
override the managed JSON values.

## Maintenance

This file is the canonical architecture artifact for the EZPowers repository.
Update it through `design-architecture` before `spec` when a change affects a
module or host-adapter boundary, a public interface, managed data ownership, a
cross-boundary flow, runtime lifecycle or recovery, distribution/deployment,
or the verification and completion authority. Link an accepted ADR when the
decision is hard to reverse, surprising without context, and based on a real
tradeoff.

Do not edit this file merely because implementation files, dependencies, or
internal organization changed without altering those boundaries. A feature
spec records `Architecture impact: none` with evidence in that case. If
implementation discovers a different structural need, return to
`design-architecture`, update this artifact, and revalidate the spec and plan
instead of adding a post-hoc description of the code.

The documentation graph and `ezpowers.docs` check protect paths, links,
ownership, and managed bytes. They do not prove semantic freshness. An
explicit harness-chain run additionally freezes this file by full-file hash
when `design_architecture` was selected, so later changes require reapproval.
