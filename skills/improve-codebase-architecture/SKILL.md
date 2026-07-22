---
name: improve-codebase-architecture
description: Find deepening opportunities in product code using Module/Interface/Depth/Seam vocabulary. Use when the user wants refactoring candidates, clearer module boundaries, or more testable and navigable code. Not for auditing workflow or harness product architecture.
context: fork
---

# Improve Codebase Architecture

Surface architectural friction and propose **deepening opportunities** --
refactors that turn shallow modules into deep ones. The aim is testability and
AI-navigability.

## Glossary (compact)

Use these terms exactly. Full definitions in [references/architecture-language.md](references/architecture-language.md).

- **Module** -- anything with an interface and an implementation.
- **Interface** -- everything a caller must know (types, invariants, error modes, ordering).
- **Depth** -- leverage at the interface. **Deep** = high leverage. **Shallow** = interface nearly as complex as the implementation.
- **Seam** -- where an interface lives; a place behaviour can be altered without editing in place.
- **Adapter** -- a concrete thing satisfying an interface at a seam.
- **Leverage** -- what callers get from depth.
- **Locality** -- what maintainers get from depth.

**Deletion test:** imagine deleting the module. If complexity reappears across N callers, it was earning its keep.

**The interface is the test surface.** Callers and tests cross the same seam.

## Domain Awareness

Read `CONTEXT.md` for domain vocabulary. Use domain terms for modules, not code
names. Check ADRs in `docs/decisions/` to avoid re-litigating settled decisions.

## Process

### 1. Explore

Read the project's domain glossary and any ADRs in the area you are touching.

Then inspect the codebase with the active host's native search and, when useful,
its native subagent support. Do not assume the two hosts expose the same agent
interface. Note where you experience friction:

- Where does understanding one concept require bouncing between many small modules?
- Where are modules **shallow** -- interface nearly as complex as the implementation?
- Where have pure functions been extracted just for testability, but the real bugs hide in how they are called (no **locality**)?
- Where do tightly-coupled modules leak across their seams?
- Which parts of the codebase are untested, or hard to test through their current interface?

Apply the **deletion test** to anything you suspect is shallow.

### 2. Present candidates

Present a numbered list of deepening opportunities. For each candidate:

- **Files** -- which files/modules are involved
- **Problem** -- why the current architecture causes friction
- **Solution** -- plain English description of what would change
- **Benefits** -- explained in terms of locality and leverage, and how tests would improve

Use `CONTEXT.md` vocabulary for the domain and architecture-language vocabulary
for the architecture. If `CONTEXT.md` defines "Order," talk about "the Order
intake module" -- not "the FooBarHandler."

**ADR conflicts:** if a candidate contradicts an existing ADR, only surface it
when the friction is real enough to warrant revisiting. Mark it clearly.

Do NOT propose interfaces yet. Ask: "Which of these would you like to explore?"

### 3. Grilling loop

Once the user picks a candidate, walk the design tree with them -- constraints,
dependencies, the shape of the deepened module, what sits behind the seam, what
tests survive.

Side effects happen inline as decisions crystallise:

- **Naming a deepened module after a concept not in `CONTEXT.md`?** Add the term.
- **Sharpening a fuzzy term?** Update `CONTEXT.md` right there.
- **User rejects a candidate with a load-bearing reason?** Offer an ADR in
  `docs/decisions/` so future reviews do not re-suggest it.
- **Want to explore alternative interfaces?** See [references/interface-design.md](references/interface-design.md).

Deeper tactics: [references/architecture-language.md](references/architecture-language.md), [references/deepening.md](references/deepening.md).

Do not use this skill as an EZPowers workflow-harness audit method. A harness
product audit must trace installed files, callers, runtime evidence, and host
capability overlap directly.
