---
doc_type: reference
authority: canonical
status: draft
---

# Codex Plugin Discovery

EZPowers is installed in Codex as a plugin bundle with skills, not as a host
slash-command provider. The Codex manifest exposes skills through
`.codex-plugin/plugin.json`:

```json
{
  "skills": "./skills/"
}
```

Codex currently loads these skills into the model-visible skill list with names
such as `ezpowers:diagnose`, `ezpowers:frontend-design`, and
`ezpowers:verifyself`. Invoke them by naming the skill explicitly, for example
`$ezpowers:diagnose Investigate this failure`, or by asking naturally when the
skill description clearly matches the request.

Workflow commands ship as skills (`skills/<name>/SKILL.md`), so Codex lists
them alongside the independent skills as `ezpowers:<name>`. Each workflow skill
sets `policy.allow_implicit_invocation: false` in `agents/openai.yaml`: it is
hidden from the ambient skill list and runs only on explicit
`$ezpowers:<name>` invocation, mirroring `disable-model-invocation` on Claude.

## Codex Execution Notes

- Translate Claude-specific tool names to Codex tools only at execution time.
- Preserve each workflow's evidence and verification gates when executing on
  Codex; the dispatch protocol's `codex-cli` backend covers reviewer dispatch.

## Local Install Notes

For local development, prefer one active EZPowers install. This workspace uses
the personal marketplace entry `ezpowers@local`, where
`C:\Users\dlwlg\plugins\ezpowers` is a junction to `C:\Working\EZPowers`.

If both `ezpowers@local` and another EZPowers marketplace entry are enabled,
Codex can inject duplicate skill entries. Disable or remove the extra install
before checking whether discovery is fixed.

Codex also activates plugin root hook files during tool use. EZPowers trace
collection is opt-in, so Codex plugin roots must not contain an active
`hooks/hooks.json`; keep the trace hook body as
`docs/reference/trace-hooks-template.json` until `/setup --enable-traces`
creates a project-local hook file.

After changing plugin metadata or skills:

1. Run the plugin cachebuster update flow.
2. Reinstall the local plugin with `codex plugin add ezpowers@local`.
3. Start a new Codex thread before testing discovery.

## Verification

Use `codex debug prompt-input "probe"` to confirm that the prompt contains one
EZPowers skill set and that entries are prefixed as `ezpowers:<skill>`.
