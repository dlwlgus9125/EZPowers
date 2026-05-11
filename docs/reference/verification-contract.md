# Verification Contract

This document is the canonical contract for EZPowers acceptance criteria,
Verify commands, runtime probes, integration evidence, and wiring gates.
Commands and agents may add local procedure details, but must not weaken this
contract.

## Acceptance Criteria Interface

Every behavior-bearing requirement must expose an acceptance criterion with:

- `Given`: observable precondition or state before the action.
- `When`: user or system action, not an implementation call.
- `Then`: concrete observable result.
- `Verify`: automated command where exit 0 means pass.
- `Verify-type`: one of `pure`, `cli`, `lib`, `api`, `e2e`, or `data`.

For `pure` criteria, `Input`, `Transform`, and `Output` may replace
Given/When/Then when the behavior has no side effects.

Given/When/Then text must describe observable behavior and must not depend on
function names, class names, internal variables, or private file structure.

## Verify-Type Evidence

| Verify-type | Required evidence |
| --- | --- |
| `pure` | Deterministic transform assertion with no external side effects. |
| `cli` | CLI invocation or script command that checks stdout, stderr, exit code, generated file, or other observable CLI result. |
| `lib` | Consumer-level script or test that imports the public entry point and asserts behavior. |
| `api` | HTTP, RPC, or similar request against the configured server plus a response/status assertion. |
| `e2e` | User-facing or entry-path probe that observes the Then clause, not only process survival. |
| `data` | Query, migration check, schema check, or file/data assertion against the persisted result. |

Broad suite commands are allowed only when they include a feature-specific
assertion or filter. A command such as `pytest`, `npm test`, or `cargo test`
without a feature-specific oracle is weak evidence and should be reported as a
warning by planning or audit.

## Automatable Criteria

Acceptance criteria default to `Automatable: true`. If a spec marks a criterion
as `Automatable: false`, the plan must replace it with an automated probe before
implementation.

`Automatable: false` with `Verify-type: e2e` or `api` is not executable until a
probe exists. The executor must treat a missing, empty, placeholder-only,
`echo`, `true`, or `:` Verify command as a failure.

## Planning Translation

Plans must copy relevant spec acceptance criteria into task completion criteria
without changing the behavior claim. If the Verify command changes between spec
and plan, the plan must preserve the same oracle strength and the audit should
report the drift.

Behavior-bearing tasks must include a TDD Slice Contract with:

- public interface
- behavior under test
- test oracle
- setup or fixtures
- minimal implementation boundary
- non-goals
- missing-info handling

Plans that modify executable entry points must include runtime verification in
addition to acceptance criteria verification.

## Execution Verification

The executor must run Verify commands and check exit codes. Passing unit tests
alone is not completion.

Recommended command timeouts:

| Verify-type | Timeout |
| --- | --- |
| `pure` | 30 seconds |
| `cli` | 30 seconds |
| `lib` | 30 seconds |
| `api` | 30 seconds after server readiness |
| `data` | 60 seconds |
| `e2e` | 120 seconds |

For `api` and `e2e` criteria that need a server, use configured start, health
check, and stop commands when available. If no server command exists, the audit
should warn before execution.

## Runtime Probe

Runtime probes prove executable artifacts start and survive long enough for
basic readiness. They are separate from feature verification.

A runtime probe passes only when:

- the process starts
- the process survives the configured interval
- fatal stdout or stderr patterns are absent
- GUI artifacts also satisfy configured window, screenshot, non-blank pixel
  variance, and optional UI Automation text/name checks

Executable artifacts (`cli`, `server`, `desktop`) require runtime smoke. A
missing required smoke command is failure, not skip. Only `docs` and `library`
artifacts may skip runtime smoke with `smoke.required: false`.

Vision checks may be used as advisory evidence, but the v1 hard gate is
deterministic process/window/screenshot/UI Automation evidence.

Runtime probe success never replaces a Verify command whose Then clause
describes feature behavior.

## Integration And Wiring

A plan needs a Full-Feature Wiring Gate when work crosses connected tasks,
multiple layers, executable entry points, or any route, registration, binding,
subscription, integration, milestone, or end-to-end path.

The gate must define:

- required status
- Verify-type (`e2e`, `api`, or `cli`)
- covered tasks or pipeline IDs
- expected observable result
- non-trivial automated Verify command

The wiring Verify command must drive the user-facing path or the same entry path
described by the gate. Single-component unit tests do not prove connected
features.

## Arbiter Verdicts

Independent arbiters and wiring reviewers classify gaps as:

- `PASS`: evidence observes the entry path and no connection gap remains.
- `TEST_GAP`: implementation may be wired, but evidence does not prove the Then clause.
- `CODE_GAP`: registration, route, import, binding, subscription, or call site is missing.
- `SPEC_GAP`: the plan lacks an automatable oracle or enough path detail to judge wiring.
