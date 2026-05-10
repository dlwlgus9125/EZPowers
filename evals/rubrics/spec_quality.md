# Spec Quality Rubric (Korean+English)

Score the brainstorm output on the following dimensions, each 0-1:

1. **Domain clarity** — Did the agent ask domain-defining questions before
   implementation questions? (LangChain Better-Harness recommendation)
2. **R completeness** — Are extracted requirements (R1, R2, ...) covering
   the user's intent without redundancy?
3. **Verify coverage** — Does each R have at least one Verify command with
   a valid verify-type ∈ {api, e2e, cli, lib, data, pure}?
4. **Banned expression absence** — No vague phrases from the banned list.
5. **Language consistency** — Output matches the user's input language
   (or appropriately mixes ko/en if user did so).
6. **Architecture readiness** -- Does the spec include Architecture Baseline,
   ASR Ledger, Option Matrix, Lifecycle And Operations, Quality Budgets, and
   Decision Log with R-to-ASR linkage?
7. **Lifecycle and quality budgets** -- Are lifecycle, operational constraints,
   and performance/reliability/security/cost/maintainability budgets concrete
   enough to guide planning?
