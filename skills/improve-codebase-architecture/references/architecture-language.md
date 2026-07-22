# Architecture Language

Shared vocabulary for every suggestion the improve-codebase-architecture skill
makes. Use these terms exactly -- don't substitute "component," "service,"
"API," or "boundary."

## Terms

**Module** -- Anything with an interface and an implementation. Deliberately
scale-agnostic -- applies equally to a function, class, package, or
tier-spanning slice. _Avoid:_ unit, component, service.

**Interface** -- Everything a caller must know to use the module correctly.
Includes the type signature, but also invariants, ordering constraints, error
modes, required configuration, and performance characteristics. _Avoid:_ API,
signature (too narrow).

**Implementation** -- What's inside a module. Distinct from **Adapter**: a thing
can be a small adapter with a large implementation (a Postgres repo) or a large
adapter with a small implementation (an in-memory fake).

**Depth** -- Leverage at the interface -- the amount of behaviour a caller can
exercise per unit of interface they have to learn. **Deep** = large behaviour
behind a small interface. **Shallow** = interface nearly as complex as the
implementation.

**Seam** _(from Michael Feathers)_ -- A place where you can alter behaviour
without editing in that place. The location at which a module's interface lives.
_Avoid:_ boundary (overloaded with DDD's bounded context).

**Adapter** -- A concrete thing that satisfies an interface at a seam. Describes
role (what slot it fills), not substance (what's inside).

**Leverage** -- What callers get from depth. More capability per unit of
interface they have to learn.

**Locality** -- What maintainers get from depth. Change, bugs, knowledge, and
verification concentrate at one place rather than spreading across callers.

## Principles

- **Depth is a property of the interface, not the implementation.** A deep
  module can be internally composed of small parts -- they just aren't part of
  the interface.
- **The deletion test.** Imagine deleting the module. If complexity vanishes,
  it was a pass-through. If complexity reappears across N callers, the module
  was earning its keep.
- **The interface is the test surface.** Callers and tests cross the same seam.
- **One adapter means a hypothetical seam. Two adapters means a real one.**
  Don't introduce a seam unless something actually varies across it.

## Relationships

- A **Module** has exactly one **Interface**.
- **Depth** is a property of a **Module**, measured against its **Interface**.
- A **Seam** is where a **Module**'s **Interface** lives.
- An **Adapter** sits at a **Seam** and satisfies the **Interface**.
- **Depth** produces **Leverage** for callers and **Locality** for maintainers.

## Rejected Framings

- **Depth as ratio of implementation-lines to interface-lines**: rewards padding
  the implementation. Use depth-as-leverage instead.
- **"Interface" as the TypeScript `interface` keyword**: too narrow -- interface
  here includes every fact a caller must know.
- **"Boundary"**: overloaded with DDD's bounded context. Say **seam** or
  **interface**.

EZPowers uses the same terms in `docs/reference/design-architecture-contract.md`
and the target project's `CONTEXT.md` for domain language. This
reference goes deeper for codebase-level architecture review.
