# Graph Engineering paper evaluation for EZPowers

## Source and evidence level

This evaluation pins arXiv v1 of [Graph Engineering in the Era of LLM Agents:
From Individual Intelligence to System Intelligence](https://arxiv.org/abs/2608.21156),
submitted 2026-08-21, and its companion
[Awesome Graph Engineering collection](https://github.com/DEEP-JLU/Awesome-Graph-Engineering).
The paper is a survey and position framework. It organises prior work and
proposes evaluation dimensions; it is not one integrated runtime, and it does
not benchmark EZPowers. No upstream implementation is vendored.

## Observed EZPowers gaps

Repository inspection of v5.6 found three concrete gaps that overlap the
paper's task-organisation and runtime-state recommendations:

1. Human plan prose may describe dependencies, but plan schema v1 has no
   machine dependency field. Unknown fields are ignored, so a misspelled or
   cyclic dependency cannot be diagnosed.
2. Evidence is strongly hash-bound, but `status` presents flat reasons. It
   does not expose the criterion-to-task-to-check-to-evidence path that narrowed
   a blocker.
3. All task and required checks execute serially. A read-only observation on
   2026-08-25 ran `repo-check`, `kit-manifest`, and the file-only dual-host
   plugin smoke independently in about 5.19 s, 2.42 s, and 2.50 s; running the
   same three concurrently completed in about 5.4 s instead of their 10.1 s
   summed duration. This is directional baseline evidence, not the release
   performance gate.

## Decision matrix

| Paper direction | EZPowers decision | Repository reason | Required proof |
| --- | --- | --- | --- |
| Explicit, typed, versioned task relations | Adopt as a derived assurance graph | Plan coverage already has stable criteria, tasks, checks, evidence, and certificates but lacks explicit task dependencies | Invalid dependency and cycle fixtures; stable graph hashes; ordinary/chain parity |
| Runtime state recording and fault localisation | Adapt | Immutable evidence exists; a safe derived trace can expose blocking paths without a new event-sourced authority | Tamper/stale tests and a trace that makes no causal overclaim |
| Workflow optimisation | Adapt only to check execution | Three current read-only checks showed overlap potential; host implementation scheduling remains out of scope | Serial/parallel result equivalence and three-run median improvement of at least 30% |
| Provenance, validation, replay, rollback for evolution | Adopt as governance, not autonomous evolution | Existing hashes, previews, approvals, and refresh rules already provide the right control points | Graph-bound evidence/certificates and legacy-chain reapproval |
| Dynamic agent/team/capability graphs | Defer | Hosts already own subagents and model choice; no reproducible EZPowers gap or benefit was shown | Separate benchmark and boundary decision |
| Automatic capability/model routing and reviewer fleets | Reject for v5.7 | Duplicates host authority and conflicts with ADR 0001/0003 | New explicit product decision would be required |
| Unrestricted self-evolution or graph operating system | Reject | Expands trust, privacy, rollback, and execution authority without local evidence | Not eligible under the evidence-gated adoption threshold |

## Applied design

The accepted subset is deliberately smaller than the paper's system vision:

- plan v2 records task dependencies, while config v2 records a bounded worker
  cap and per-check concurrency safety/resource locks;
- the runtime derives and hashes a typed assurance graph; no second graph file
  or mutable execution state becomes authoritative;
- `trace` reports sorted topology, task waves, node state, and blocking paths;
- only explicitly safe check processes may overlap, and unsafe checks remain
  global barriers;
- plan/config v1 remains readable and serial;
- plan-v2 evidence, certificates, and new chain approvals bind the graph hash;
- a nonterminal legacy approval without that binding must be approved again.

## Evaluation protocol

Release acceptance uses matched commands and budgets, three or more runs per
mode, median wall time, stable declaration-order result comparison, and a
minimum 30% median improvement. Functional evaluation also covers malformed
and cyclic graphs, resource locks, repeated check occurrences, timeouts,
spawn failures, workspace mutation detection, evidence tampering, chain
approval freshness, and both host discovery surfaces. Performance does not
override correctness: a failed equivalence or freshness assertion rejects the
parallel path even if it is faster.

## Final measured results

Both release lanes used three matched alternating serial/parallel runs and
preserved their declared comparison contract:

- the controlled four-check fixture improved from a 1.445024-second serial
  median to a 0.403820-second parallel median (72.05%), with identical full
  stdout/stderr hashes and every check passing;
- the current allowlisted `repo-check`, `kit-manifest`, and file-only
  `plugin-files` checks improved from a 2.344398-second serial median to a
  1.488881-second parallel median (36.49%), with equivalent process outcomes
  and every check passing.

The complete repository suite passed 188 tests in 968.000 seconds. The
structural repository gate, installed-runtime graph smoke, v5.7 kit manifest,
actual Claude 2.1.238 manifest validation, Codex 0.149.0 isolated skill
discovery, and the existing frontend-design checks also passed. Exact command
evidence and remaining limits are recorded in `PROGRESS.md` and the v5.7
changelog entry.
