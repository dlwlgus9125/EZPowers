# Design Architecture Contract

This contract defines the durable project decisions that must be settled before
`spec` can state observable feature claims. It does not prescribe how Claude
Code or Codex should implement the work.

## Preflight

Read repository instructions, `CONTEXT.md`, applicable ADRs, manifests, entry
points, public interfaces, data schemas, CI and deployment files, existing
architecture documents, and tests. When the local kit is installed, also read:

```text
.ezpowers/contracts/design-architecture-contract.md
.ezpowers/contracts/verification-contract.md
```

If `.ezpowers/ezpowers.py` is absent, use `setup`. If a material product or
domain decision is still ambiguous, use `deep-interview` before fixing the
architecture. Ask the user only for consequential choices repository evidence
cannot settle.

## Required Decisions

Record the subset that applies to the project:

- purpose, primary users, and system boundary;
- entry points and public interfaces;
- module boundaries, allowed dependencies, forbidden dependencies, and data
  ownership;
- cross-module and external-system data flow;
- state ownership, concurrency, error and cancellation behavior;
- startup, shutdown, health, recovery, and migration behavior;
- packaging, deployment, compatibility, and rollback boundaries;
- security, reliability, performance, accessibility, cost, or maintainability
  constraints that can change the design;
- project-local checks that can observe those constraints;
- unresolved risks and the decision that would close each risk.

Do not add model selection, context budgets, subagent placement, worktree
policy, sandbox settings, general retries, or reviewer routing. Those are host
execution concerns unless the target project itself has an independently
documented product requirement for one.

## Artifacts

Update the project's existing canonical architecture documents. When no
equivalent exists, use these conventional paths:

- `docs/reference/architecture.md`
- the project's existing testing methodology, when present;
- the project's existing structure or architecture document, when present;
- `docs/product/ROADMAP.md` when delivery order matters
- `docs/ux/frontend-design.md` when UI design decisions are required
- `docs/decisions/` only for accepted ADRs

Do not create empty slots merely to satisfy a filename. Each generated artifact
must state its authority and link to the document that owns overlapping rules.

## Decision Ledger And ADRs

Consequential decisions use a compact ledger:

| ID | Decision | Source | Affected artifacts | Open follow-up |
| --- | --- | --- | --- | --- |

`Source` is `user`, `repo`, `default`, or `delegated`. A default must include
the evidence that made it safe. Carry applicable IDs into the spec's readable
Markdown so the origin of a constraint remains inspectable.

Offer an ADR only when a decision is all three of:

- hard to reverse;
- surprising without context;
- the result of a real tradeoff.

Create it only after the user accepts the offer. Do not use an ADR as a routine
meeting note or to duplicate the architecture document.

## Verification Design

Every automated check is ultimately represented as:

```json
{
  "argv": ["python", "-m", "unittest"],
  "cwd": ".",
  "timeout_seconds": 120,
  "kind": "test"
}
```

Choose commands from executable repository evidence. `argv` is exact and runs
without an implicit shell; pipelines, redirections, shell control operators,
and placeholders are invalid. `cwd` is an existing project-relative directory,
and the timeout is a positive integer.

For executable behavior, identify a check that crosses the real entry point.
For an integration or user-visible claim, use an `integration`, `e2e`, or
`smoke` check with the same observable oracle. If the adapter does not yet
exist, record adding it as a prerequisite rather than weakening the claim.

## Frontend Readiness

For UI work, follow `frontend-design-contract.md`. Record the chosen design
artifact and deterministic visual, accessibility, browser, terminal, or native
window oracle. Use the installed non-mutating detector at:

```text
python .ezpowers/tools/frontend-visual-readiness.py --mode detect
```

Tool presence is project-local evidence only; a globally installed executable
does not silently expand project requirements.

## Readiness To Specify

Proceed to `spec` when:

- no implementation-critical boundary or ownership choice remains open;
- relevant failure and lifecycle behavior is explicit;
- every completion claim can be mapped to an observable project check or to a
  named prerequisite that will create that check;
- UI implementation will not have to invent visual direction or accessibility
  policy;
- accepted decisions are reflected in their canonical artifacts.

Report changed artifacts, decisions and evidence sources, exact verification
design, and remaining risks. Artifact readiness and deterministic validation
are the only gates owned by this contract.
