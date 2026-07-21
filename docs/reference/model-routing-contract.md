# Model Routing Contract

This document is canonical for EZPowers model profile selection across reviewer
dispatch, subagent task execution, and external harness execution.

## Goal

Model names change. EZPowers therefore routes by stable work profiles, not by
hard-coded model names in command prompts.

Every routed execution records `profile`, `backend`, `selected`, `variant`,
`reasoning_effort`, `provenance`, `attempted`, `status`, and `reason`.

## Config

`.harness/config.json` may enable routing under `executor.model_routing`:

```json
{
  "executor": {
    "model_routing": {
      "enabled": true,
      "default_profile": "balanced",
      "fail_on_unresolved": false,
      "availability_cache": ".harness/model-availability.json",
      "profiles": {
        "balanced": {
          "claude_code": ["sonnet", "opus"],
          "codex_cli": ["gpt-5.5", "gpt-5.4"],
          "harness_env": ["claude-sonnet-4-6", "gpt-5.5"]
        }
      }
    }
  }
}
```

If `model_routing.enabled` is absent or false, existing defaults apply.

## Profiles

Built-in profiles: `quick-fix`, `balanced`, `deep-analysis`,
`contract-review`, `runtime-debug`, `frontend-visual`, `security-audit`, and
`docs-sync`. `frontend-experience-reviewer` uses `frontend-visual`.

Supported backends: `claude-code`, `codex-cli`, and `harness-env`.

Selection precedence:

1. Explicit model override supplied to the router
2. Legacy reviewer override: `reviewer_model` or `codex_reviewer_model`
3. Task/reviewer model profile
4. Profile fallback list
5. Backend current default

`/choice-execute` asks once per run whether to use the configured default or an
explicit execution override. That override applies to implementer dispatch and
strict Path 2 `EZPOWERS_MODEL`; reviewer routing remains governed by reviewer
settings unless the user explicitly changes it.

## Availability

The optional availability cache is read from `.harness/model-availability.json`:

```json
{
  "models": {
    "claude-code": ["sonnet", "opus"],
    "codex-cli": ["gpt-5.5", "gpt-5.4"],
    "harness-env": ["claude-sonnet-4-6"]
  }
}
```

When the cache is missing, the router selects the first fallback and returns
`status: "unverified"`. Doctor reports this as WARN.

When the cache exists but no fallback is available, the router returns
`status: "unresolved"`. This is FAIL only when `fail_on_unresolved` is true.

## Task Profiles

Plan tasks may specify:

```md
**Model profile:** deep-analysis
```

`scripts/harness-convert.ps1` preserves this as `model_profile` in
`phases/<phase>/index.json`. If omitted, the default is `balanced`.

## Harness Environment

External harness executors receive resolved routing through process environment:

- `EZPOWERS_MODEL_PROFILE`
- `EZPOWERS_MODEL`
- `EZPOWERS_MODEL_VARIANT`
- `EZPOWERS_REASONING_EFFORT`
- `EZPOWERS_MODEL_ROUTING_JSON`

The external executor may ignore these variables, but it must not silently
choose a different model without logging the reason when it consumes them.

## Selection Precedence

Model selection layers resolve in this order (first non-empty wins):

1. Agent frontmatter `model:` alias (`sonnet` / `opus` / `haiku` / `inherit`)
   — the default tier for that agent.
2. `.harness/config.json` `executor.reviewer_model` (or
   `codex_reviewer_model` on the codex-cli backend) — per-project override.
3. `scripts/model-router.py` profile resolution when
   `executor.model_routing.enabled` is true — per-profile, per-backend.
4. Explicit per-run override passed by the user through the dispatching
   workflow (for example the execution-model question in `/choice-execute`).

Aliases live in frontmatter and dispatch calls; versioned model IDs live only
in `scripts/model-router.py` profiles.
