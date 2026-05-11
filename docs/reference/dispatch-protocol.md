# Reviewer Dispatch Protocol

Backend-aware dispatch for reviewer subagents. Commands reference this document
before dispatching any reviewer or workflow-runner agent.

## Config Read

Read `.harness/config.json` → `executor` block:

```json
{
  "executor": {
    "reviewer_backend": "claude-code",
    "reviewer_model": "",
    "codex_reviewer_model": ""
  }
}
```

If `.harness/config.json` is missing or `reviewer_backend` is absent, default to `"claude-code"`.

## Path A: `reviewer_backend: "claude-code"` (default)

Use the standard `Agent tool` with `subagent_type` as documented in each command.

**Model override:** If `executor.reviewer_model` is non-empty, add `model: <value>`
to the Agent tool call. Accepted values: `"sonnet"`, `"opus"`, `"haiku"`.
If empty, omit the `model` parameter (agent definition default applies).

Example with override:

```
Agent tool:
  subagent_type: "ezpowers:plan-reviewer"
  model: opus
  description: "Review plan document"
  prompt: |
    **Plan to review:** <path>
    **Spec for reference:** <path>
```

Example without override (existing behavior):

```
Agent tool:
  subagent_type: "ezpowers:plan-reviewer"
  description: "Review plan document"
  prompt: |
    **Plan to review:** <path>
    **Spec for reference:** <path>
```

## Path B: `reviewer_backend: "codex-cli"`

Dispatch the review task through `codex:codex-rescue` instead of the native
plugin agent. The reviewer agent's `.md` file contains the review checklist —
instruct Codex to read it and execute the procedure.

**Model selection:** If `executor.codex_reviewer_model` is non-empty, append
`--model <value>` to the Codex task. Available models:

| Model | Use Case |
|-------|----------|
| `gpt-5.5` | Latest flagship (1M context, strong reasoning) |
| `gpt-5.5-pro` | Highest accuracy |
| `gpt-5.4` | Previous default |
| `gpt-5.3-codex-spark` | Lightweight / cost-efficient (alias: `spark`) |

If empty, Codex uses its active default model.

### Dispatch Template

For each reviewer, replace the `Agent tool: subagent_type: "ezpowers:<agent>"` block
with the following pattern:

```
Agent tool:
  subagent_type: "codex:codex-rescue"
  description: "<same description> (Codex)"
  prompt: |
    Read the file agents/<agent-name>.md for the full review checklist.
    Execute every check in that document on the inputs below.
    [--model <codex_reviewer_model> if configured]

    <paste the same dynamic parameters as the claude-code path>

    ## Output Contract
    End your response with exactly one of:
      ## Verdict: PASS
      ## Verdict: FAIL
      ## Verdict: PASS_WITH_ISSUES
    Then list issues in the format specified by the agent document.
    Do not use any other verdict format.
```

### Agent Mapping

| Claude-code path | Codex-cli path | Agent file |
|-----------------|----------------|------------|
| `ezpowers:spec-reviewer` | `codex:codex-rescue` + agents/spec-reviewer.md | agents/spec-reviewer.md |
| `ezpowers:architecture-reviewer` | `codex:codex-rescue` + agents/architecture-reviewer.md | agents/architecture-reviewer.md |
| `ezpowers:plan-reviewer` | `codex:codex-rescue` + agents/plan-reviewer.md | agents/plan-reviewer.md |
| `ezpowers:code-reviewer` | `codex:codex-rescue` + agents/code-reviewer.md | agents/code-reviewer.md |
| `ezpowers:security-reviewer` | `codex:codex-rescue` + agents/security-reviewer.md | agents/security-reviewer.md |
| `ezpowers:wiring-reviewer` | `codex:codex-rescue` + agents/wiring-reviewer.md | agents/wiring-reviewer.md |
| `ezpowers:workflow-runner` | `codex:codex-rescue` + agents/workflow-runner.md | agents/workflow-runner.md |

### Verdict Parsing

Verdict parsing is identical for both paths:

1. Scan the response for `## Verdict: PASS`, `## Verdict: FAIL`, or `## Verdict: PASS_WITH_ISSUES`
2. If Verdict header is missing or malformed: treat as `FAIL`
3. On 2 consecutive missing Verdict headers from Codex: escalate to user
   ("Codex reviewer is not returning verdicts in the standard format. Consider switching reviewer_backend to claude-code.")

### Error Handling

- **Codex timeout / connection failure:** Report the error to the user. Do not auto-fallback to claude-code (the backend choice is explicit).
- **Parse failure (no verdict found):** Treat as `FAIL`. Log: "Codex reviewer output did not contain a valid verdict header."
- **Codex returns empty output:** Treat as `FAIL`. Escalate after 2 consecutive empty responses.

## Agents NOT Covered by This Protocol

- **eval-diagnostician** (`model: claude-opus-4-6`): Called only from `scripts/propose_edit.py`, not from user-facing commands. Not subject to backend dispatch.
- **implementer-prompt.md**: Template for task implementation subagents. Dispatch is handled by `/choiceexecutor` Section 4 directly, not through this protocol.
