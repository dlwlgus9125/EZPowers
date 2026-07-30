---
name: explain-with-evidence
description: Structure user-facing explanations and work-result reports in the user's active conversational language, grounded in observed evidence and honest limits. Use when explaining completed work, technical decisions, knowledge, concepts, numbers, or rationale beyond a one-line confirmation or status update; not to rewrite fixed-schema artifacts or machine-readable output.
---

# Explain With Evidence

Improve presentation only. Do not change the task, authority, evidence, or
completion contract supplied by the user, repository, host, or another skill.

## Match the user's language

- Infer the response language from the latest substantive natural-language
  user message. An explicit language instruction overrides inference.
- If that message is too short or genuinely mixed, use the dominant language
  of the recent conversation.
- Ignore code, commands, paths, identifiers, model names, quoted material, and
  required proper nouns when inferring or translating. Preserve them as needed.

## Choose the smallest useful shape

- **Result report:** outcome, reason when useful, material change, observed
  verification, then remaining limits.
- **Deep explanation:** context, alternatives actually considered, useful
  discovery sequence, decisive finding, observed evidence, then remaining
  uncertainty or the next check.

Use the result shape for ordinary task completion. Use the deep shape only
when the user requests a detailed explanation, rationale, retrospective, or
similar narrative. Follow a user-requested format instead of either shape.
Omit stages that add no information; do not repeat an opening conclusion at
the end.

## Ground every stage

- Include an alternative, objection, reversal, or discovery sequence only
  when it was actually considered or observed and helps explain the result.
- Distinguish direct observation from inference and unverified possibility.
- Never invent a measurement. Tie numbers and PASS/FAIL claims to commands,
  artifacts, sources, or other evidence actually inspected.
- Prefer concrete cases and exact evidence over analogy. Use analogy only when
  it materially helps an unfamiliar audience.

## Preserve fixed contracts

Do not reshape code, commands, specs, plans, JSON, tool output, receipts,
certificates, or other fixed-schema artifacts. Explain around them when useful.
Never soften or narratively reinterpret exact states such as `PASS`, `FAIL`,
`BLOCKED`, `READY`, or `CERTIFIED`. This skill adds no tools, workflow
transition, write authority, retry policy, or completion authority.

Adaptation notice: this file is a substantially modified EZPowers adaptation
of `j-explain-style`; see `LICENSE` in this skill directory.
