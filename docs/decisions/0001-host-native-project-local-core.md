# 0001. Use a host-native, project-local verification core

**Status:** accepted

EZPowers will store project-specific spec/plan data, checks, evidence, and
resume state locally while Claude Code or Codex owns code execution and agent
orchestration. The prior external `EasyPowersHarness` executor, numbered
execution paths, plan-to-phase conversion, reviewer fleet, model router, and
generic retry layer are removed.

## Considered Options

- Keep the v4 orchestration stack for compatibility.
- Repair or recreate the external executor.
- Delegate everything to host instructions with no local runtime.
- Retain only a project-local deterministic verification and evidence core.

## Consequences

The public flow and compatibility surface become smaller, and old external
execution configurations are migrated only for safe project commands. In
return, an installed project is self-contained, both hosts use the same
completion verdict, stale/tampered evidence fails closed, and host-native
capabilities are not reimplemented. This decision can be reversed only by
reintroducing a second orchestration product and its maintenance burden.
