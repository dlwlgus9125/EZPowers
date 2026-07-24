---
name: codebase-design
description: Design or improve a module interface, choose a seam, reduce shallow abstractions, and make product code more testable and AI-navigable using deep-module vocabulary. Use for focused module or refactor design, interface alternatives, dependency placement, and test-surface decisions; not for a whole-codebase scan or durable project architecture documentation.
---

# Codebase Design

Design deep modules: substantial behavior behind a small interface at an
honest seam.

## Load and scope

Read `.ezpowers/contracts/engineering-practices-contract.md` when installed, or
the same contract under the EZPowers plugin's `docs/reference/` directory.
Read repository instructions, current Git state, the affected callers and
tests, `CONTEXT.md` when present, and applicable ADRs.

Keep the scope to the named module or change. Use these terms consistently:

- **Module:** implementation plus the interface it presents.
- **Interface:** every fact a caller must know, including invariants, ordering,
  errors, configuration, and performance constraints.
- **Depth:** leverage available through that interface.
- **Seam:** where behavior can vary without editing the caller.
- **Adapter:** a concrete implementation satisfying an interface at a seam.
- **Leverage:** capability callers gain per unit of interface.
- **Locality:** change, knowledge, bugs, and tests concentrated behind the
  interface.

Apply the deletion test: if deleting the module merely spreads its complexity
across callers, it earns its place; if complexity disappears, it is probably a
pass-through. Treat one adapter as a hypothetical seam and two independently
needed adapters as evidence of a real seam.

## Design

1. Name the callers, behavior to hide, current interface burden, dependencies,
   and required test observations.
2. Produce at least two materially different interface/seam options. Do not
   vary only names.
3. Compare the options on interface size, hidden behavior, locality, adapter
   reality, compatibility, failure modes, and tests that survive refactoring.
4. Recommend one option and state the tradeoff that disqualified each
   alternative. Ask for a choice only when the user has not delegated it.
5. Describe the selected Module, Interface contract, Seam, Adapters,
   dependency direction, migration boundary, and test surface.

Accept dependencies rather than constructing them invisibly at call sites.
Prefer returning explicit results over hidden side effects where the domain
permits it. Do not add a seam solely to make mocking convenient.

## Boundaries

Do not scan an entire repository; use `improve-codebase-architecture` only
when the user explicitly requests that broader analysis. Do not edit product
code, `CONTEXT.md`, ADRs, or canonical architecture documents unless the user
separately authorizes those changes. `design-architecture` owns durable
project boundary records.

Report design alternatives, the selected interface and seam, compatibility
effects, surviving tests, and unresolved risks.
