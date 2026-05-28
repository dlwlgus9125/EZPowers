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

The workflow files under `commands/` remain command documents. They are source
procedures for agents to read and execute when requested, but their existence
does not imply that Codex will list each workflow under the `/` command palette.

## Local Install Notes

For local development, prefer one active EZPowers install. This workspace uses
the personal marketplace entry `ezpowers@local`, where
`C:\Users\dlwlg\plugins\ezpowers` is a junction to `C:\Working\EZPowers`.

If both `ezpowers@local` and another EZPowers marketplace entry are enabled,
Codex can inject duplicate skill entries. Disable or remove the extra install
before checking whether discovery is fixed.

After changing plugin metadata or skills:

1. Run the plugin cachebuster update flow.
2. Reinstall the local plugin with `codex plugin add ezpowers@local`.
3. Start a new Codex thread before testing discovery.

## Verification

Use `codex debug prompt-input "probe"` to confirm that the prompt contains one
EZPowers skill set and that entries are prefixed as `ezpowers:<skill>`.
