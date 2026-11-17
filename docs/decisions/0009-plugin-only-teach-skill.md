# 0009. Add a plugin-only explicit teach skill

## Status

Accepted on 2026-11-17.

## Context

EZPowers has no bounded role for learning a topic across sessions. Matt
Pocock's public `teach` skill provides one: a mission, vetted resources, short
HTML lessons, reference documents, and learning records kept as files in the
directory it runs in. Importing it unchanged would let it take over an
EZPowers-managed project directory, where its untracked lesson files change
the workspace fingerprint and stale completion evidence. Its wording also
mixes the skill directory with the workspace, names one host's invocation
syntax, and carries two defects that its own documentation records: an
unlinked glossary format and a correct quiz answer that lands in the first
position.

ADR 0004 requires a separate bounded role and catalog decision for any further
Matt Pocock skill, and the roadmap requires a bounded role, a maintenance
owner, and deterministic validation before the core catalog grows.

## Decision

Pin upstream commit `5863806dd4e15c63174bee4e7515a4256792ecfa` and distribute
an EZPowers-owned MIT adaptation named `teach`.

The skill:

- is explicit-only on both hosts and plugin-only: it has no project metadata,
  is absent from the v5.8.0 project-kit manifest, and is never copied by
  `setup`;
- treats the directory it is invoked in as the teaching workspace and keeps
  the skill directory read-only, loading four format references from it and
  never fetching upstream content at runtime;
- stops before its first write when the workspace sits inside a Git worktree
  whose root contains `.ezpowers/`, and continues there only after an explicit
  user choice;
- writes lessons in the user's language, states when sources could not be
  checked, links the glossary format, and requires a quiz component that
  shuffles answers at render time; and
- adds no workflow, documentation, wiki, spec, plan, verification, retry, or
  completion authority.

A complete MIT copy, the pinned source, and a modification notice travel
beside the skill without being loaded into model context. The upstream
documentation page is not shipped. The plugin exposes fifteen skills and the
project kit installs thirteen; `hud` and `teach` are plugin-only. The plugin
moves to 5.9.0 while the project kit stays at v5.8.0 with unchanged hashes.

EZPowers maintainers own the adaptation. Upstream updates are deliberate
source reviews rather than runtime sync. Repository gates validate the exact
inventory, both hosts' invocation policy, the absence of project metadata, the
pinned provenance, the reference files, project-install absence, and isolated
host discovery.

## Considered options

- Install the skill in the project kit with a workspace subfolder excluded
  from freshness: rejected because it changes the runtime and the kit identity
  and stales existing projects for a skill that has no project role.
- Allow implicit invocation: rejected because a one-off explanation must not
  create a workspace.

## Consequences

- Both hosts get the same explicit namespaced skill; there is no project-local
  variant.
- Existing projects need no `setup --refresh`; kit identity and completion
  evidence are unaffected.
- Catalog, manifest, guide, license, and discovery require regression
  coverage.
- Lesson quality still depends on the host model and web access;
  deterministic gates validate packaging and policy, not teaching behavior.
- Further third-party skills still need their own decision.
