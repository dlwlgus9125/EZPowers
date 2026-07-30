# 0004. Add bounded specialized engineering skills

## Status

Accepted on 2026-07-24.

## Context

EZPowers has durable architecture, implementation, verification, and explicit
harness-chain roles, but it lacks reusable disciplines for evidence-first bug
diagnosis, focused module-interface design, and broad product-code
architecture discovery. Matt Pocock's public engineering skills provide useful
feedback-loop and deep-module vocabulary, but importing them unchanged would
introduce Claude-specific assumptions, automatic documentation behavior, a
CDN-backed report, and ambiguous overlap with EZPowers completion authority.

A full optional skill pack would also create multiple catalogs and make
project installation, discovery, and maintenance harder to verify.

## Decision

Pin upstream commit `ed37663cc5fbef691ddfecd080dff42f7e7e350d` and maintain
three EZPowers-owned MIT adaptations in the core catalog:

1. `diagnose`, implicitly matchable, requires a command already observed red
   on the user's exact symptom and a minimised reproduction before hypotheses,
   root-cause claims, or product-behavior edits. If that gate cannot be opened,
   it requests the missing access, captured artifact, or instrumentation and
   does not guess. After the gate, falsifiable hypotheses guide one-variable
   probes. Explicit invocation or fix/debug intent defaults to FIX-COMPLETE and
   cannot finish at root cause: it continues through a red regression signal,
   source-cause patch, original-symptom rerun, affected checks, and cleanup.
   Only an explicit analysis-only/no-edit request stops before changes.
2. `codebase-design`, implicitly matchable, compares at least two focused
   interfaces using Module, Interface, Depth, Seam, Adapter, Leverage, and
   Locality vocabulary. It neither scans the whole repository nor owns durable
   architecture documents.
3. `improve-codebase-architecture`, explicit-only, scans existing product code,
   produces one to eight evidence-backed candidates, renders a temporary
   offline HTML report, defers interface design until selection, and explores
   one user-selected candidate without implementing it.

Install a shared `engineering-practices-contract.md`, a focused report contract
beside the broad-scan skill, a cross-host renderer resolver, and a
standard-library `architecture-review-report.py`. Schema v2 binds actual
file-line evidence, compatibility, migration, ADR context, semantic graph
styles, and the top recommendation rationale. The renderer escapes all input,
uses inline CSS and SVG under a restrictive Content Security Policy, rejects
repository-internal or existing outputs, writes atomically, and returns
input/source/report hashes. Installation never fetches upstream.

The plugin therefore exposes thirteen skills and the project kit installs
twelve; `hud` remains plugin-only. Move the single live kit manifest to
v5.3.0. Existing v5.2 projects update only through explicit `setup --refresh`;
managed-file conflicts remain fail-closed and prior completion becomes stale
when kit identity changes.

## Consequences

- Diagnosis and refactor advice become consistent across Claude Code and Codex
  without gaining implementation or certification authority.
- Opt-in dual-host live fixtures verify that the first exact-red receipt
  predates a product patch and that missing production evidence blocks edits;
  deterministic repository tests remain free of model calls and account cost.
- `design-architecture` remains the durable architecture owner, and
  `harness-chain` limits, receipts, frozen inputs, and terminal verdicts remain
  unchanged.
- Broad scans create temporary advisory data, not repository documentation,
  wiki knowledge, or completion evidence.
- The scan preserves its initial Git status, avoids test/build cache writes,
  deletes its temporary structured input, and does not design an interface
  before the user selects a candidate.
- The exact catalog, both metadata variants, project manifest hashes, renderer
  safety, installation copies, and host discovery require regression tests.
  A representative isolated fixture supports actual host probes, with
  authentication or sandbox failures recorded separately from semantic
  behavior.
- Upstream updates are deliberate source reviews rather than runtime sync.
- Other Matt Pocock skills are not bundled; any future addition needs a
  separate bounded role and catalog decision.
