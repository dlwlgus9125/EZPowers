# Interface Design

When the user wants to explore alternative interfaces for a chosen deepening
candidate, use this parallel sub-agent pattern. Based on "Design It Twice"
(Ousterhout) -- your first idea is unlikely to be the best.

## Process

### 1. Frame the problem space

Before spawning sub-agents, write a user-facing explanation:

- Constraints any new interface must satisfy.
- Dependencies and their category (see [deepening.md](deepening.md)).
- A rough illustrative code sketch to ground the constraints.

Show this to the user, then immediately proceed to Step 2.

### 2. Spawn sub-agents

Spawn 3+ sub-agents in parallel using the Agent tool. Each must produce a
**radically different** interface for the deepened module.

Give each agent a different design constraint:

- Agent 1: "Minimize the interface -- aim for 1-3 entry points max."
- Agent 2: "Maximise flexibility -- support many use cases and extension."
- Agent 3: "Optimise for the most common caller -- make the default case trivial."
- Agent 4 (if applicable): "Design around ports & adapters for cross-seam dependencies."

Include both architecture-language vocabulary and `CONTEXT.md` vocabulary in the
brief so each sub-agent names things consistently.

Each sub-agent outputs:

1. Interface (types, methods, params -- plus invariants, ordering, error modes).
2. Usage example showing how callers use it.
3. What the implementation hides behind the seam.
4. Dependency strategy and adapters (see [deepening.md](deepening.md)).
5. Trade-offs -- where leverage is high, where it's thin.

### 3. Present and compare

Present designs sequentially, then compare in prose. Contrast by **depth**
(leverage at the interface), **locality** (where change concentrates), and
**seam placement**.

Give your recommendation: which design is strongest and why. If elements from
different designs would combine well, propose a hybrid. Be opinionated.
