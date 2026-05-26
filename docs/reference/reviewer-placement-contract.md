# Reviewer Placement Contract

This contract is the source of truth for mandatory reviewer placement after
EZPowers commands and explicit skill invocations.

## Source Contracts

- `docs/reference/dispatch-protocol.md`
- `docs/reference/model-routing-contract.md`
- `docs/reference/domain-language.md`
- `docs/reference/verification-contract.md`
- `docs/reference/spec-contract.md`
- `docs/reference/plan-contract.md`
- `docs/reference/harness-execution-contract.md`

## Completion Rule

Every successful command or explicit skill invocation must end with at least
one reviewer verdict. A preflight abort with no artifact is exempt because no
workflow result was produced.

Use specialized reviewers when their artifact exists. Use
`ezpowers:workflow-contract-reviewer` for workflow reports, setup state,
documentation sync, eval reports, feedback records, handoff notes, and skill
outputs that do not fit a specialized reviewer.

Security review is mandatory whenever changed files or artifacts expose user
input, auth, crypto, filesystem paths, network I/O, dependency manifests, or
secrets. If no security surface exists, record that decision in the Review
Packet.

## Review Packet

Before dispatching the required reviewer set, prepare a Review Packet with:

- Invocation name.
- Invocation mode.
- Working directory.
- Artifact paths.
- Source contracts read.
- Changed files or diff range when files changed.
- Evidence commands and results.
- Required reviewers from the matrices below.
- Reviewer verdicts already received.
- Security surface decision.

Pass paths and short dynamic facts to reviewers. Do not paste full specs,
plans, diffs, logs, or previous reviewer reasoning when a path is enough.

## Command Matrix

<!-- REVIEWER-MATRIX-COMMANDS-BEGIN -->
| Invocation | Required reviewers | Required inputs |
| --- | --- | --- |
| `/setup` | `ezpowers:workflow-contract-reviewer` | harness config, kit ledger, installed file list, setup evidence |
| `/design_architecture` | `ezpowers:architecture-reviewer` | architecture, testing methodology, project structure, roadmap, config |
| `/spec` | `ezpowers:spec-reviewer`, `ezpowers:architecture-reviewer` | spec path, architecture reference, config, post-spec audit result |
| `/prepare_execute` | `ezpowers:plan-reviewer` | plan path, spec path, post-prepare_execute audit result |
| `/choice_execute` | `ezpowers:security-reviewer` when triggered, `ezpowers:wiring-reviewer`, `ezpowers:code-reviewer` | plan path, diff range, changed files, gate artifacts, runtime evidence |
| `/review` | `ezpowers:workflow-contract-reviewer` | review target, spec path if present, checks run, findings |
| `/sync-docs` | `ezpowers:workflow-contract-reviewer` | sync proposal or applied docs, verification results, changed docs |
| `/set-rules` | `ezpowers:workflow-contract-reviewer` | conventions artifact, accepted rules, verification commands |
| `/maintain` | `ezpowers:workflow-contract-reviewer` plus routed stage reviewers | issue classification, failing signal, route decision |
| `/deploy` | `ezpowers:workflow-contract-reviewer` plus routed stage reviewers for changes | release report, artifact evidence, rollout and rollback checks |
| `/reset_setup` | `ezpowers:workflow-contract-reviewer` | manifest, ledger, migrated config fields, phase review flags |
| `/eval` | `ezpowers:workflow-contract-reviewer` | eval command, result artifact, split summary, verdict |
| `/feedback` | `ezpowers:workflow-contract-reviewer` | trace path, appended feedback entry, verification evidence |
<!-- REVIEWER-MATRIX-COMMANDS-END -->

## Skill Matrix

<!-- REVIEWER-MATRIX-SKILLS-BEGIN -->
| Skill | Required reviewers | Required inputs |
| --- | --- | --- |
| `diagnose` | `ezpowers:workflow-contract-reviewer`; add `ezpowers:code-reviewer` and `ezpowers:security-reviewer` when fixes change code or security surfaces | phase findings, feedback loop, repro evidence, fix evidence |
| `grill-with-docs` | `ezpowers:architecture-reviewer` | design decisions, CONTEXT or ADR changes, unresolved branches |
| `improve-codebase-architecture` | `ezpowers:architecture-reviewer` | architecture candidates, selected candidate, ADR conflicts |
| `verifyself` | `ezpowers:workflow-contract-reviewer` | verification target, evidence table, final verdict |
| `writing-skills` | `ezpowers:workflow-contract-reviewer` | RED/GREEN evidence, skill eval results, changed skill paths |
| `handoff` | `ezpowers:workflow-contract-reviewer` | handoff document path, workflow state, next action |
| `deep-interview` | `ezpowers:workflow-contract-reviewer` | clarified goal, scope, constraints, success criteria |
| `zoom-out` | `ezpowers:workflow-contract-reviewer` | module map, evidence paths, caller summary |
| `caveman` | `ezpowers:workflow-contract-reviewer` | mode change, persistence rule, technical accuracy check |
| `ezpowers-workflow` | `ezpowers:workflow-contract-reviewer` | adapter request, command source path, preserved contracts |
<!-- REVIEWER-MATRIX-SKILLS-END -->

## Verdict Handling

Standard reviewers return `## Verdict: PASS`, `## Verdict: PASS_WITH_ISSUES`,
or `## Verdict: FAIL` unless their own agent file defines a narrower verdict
set. `ezpowers:wiring-reviewer` keeps its wiring verdicts: `PASS`,
`TEST_GAP`, `CODE_GAP`, and `SPEC_GAP`.

`PASS_WITH_ISSUES` follows `docs/reference/dispatch-protocol.md`: one focused
fix-and-review round is allowed for Important issues.

`FAIL`, `TEST_GAP`, `CODE_GAP`, or `SPEC_GAP` block completion and route back
to the command, skill, or earlier workflow stage named by the reviewer.

## Recording

When `phases/index.json` is available, record reviewer results under the active
phase using the invocation name as the key. For standalone utility commands or
skills without phase state, include the Review Packet and verdict summary in
the command output or generated artifact.
