# 0005. Add context-efficient evidence explanations

## Status

Accepted on 2026-07-27.

## Context

The upstream `j-explain-style` skill provides useful ordering, concrete
evidence, and uncertainty rules, but importing its mandatory 6.26 KB skill and
7.31 KB sample context would make a broad implicit skill expensive. Its fixed
Korean default, required rejected option and reversal, discovery-order
narrative, and open ending can also conflict with user language, short result
reports, canonical artifact schemas, and exact EZPowers verdicts.

## Decision

Pin upstream commit `08c368e4e0a63b3c4c40abbb3fab22913d1518f6`
and distribute a substantially modified Apache-2.0 adaptation named
`explain-with-evidence`.

The skill:

- infers language from the latest substantive natural-language user message,
  falls back to recent conversation for short or mixed input, and lets an
  explicit language instruction win;
- chooses a compact result report by default and a narrative explanation only
  when the user asks for depth;
- includes alternatives, reversals, chronology, objections, and measurements
  only when actually considered or observed;
- does not reshape fixed-schema artifacts or reinterpret exact completion
  states; and
- adds no workflow, write, retry, or completion authority.

No upstream samples are shipped. A complete Apache-2.0 copy, pinned source,
and modification notice travel beside the skill without being loaded into
model context. The plugin exposes fourteen skills and the project kit installs
thirteen; `hud` remains plugin-only.

## Consequences

- Claude Code and Codex receive the same compact skill body and host-specific
  invocation metadata.
- Normal explanations gain language matching and evidence discipline without
  forcing empty narrative stages or weakening terminal verdicts.
- Existing projects receive the skill only through explicit
  `setup --refresh`; the v5.4.0 kit identity stales prior completion evidence.
- Catalog, manifest, license installation, prompt size, discovery, and fixed
  output boundaries require regression coverage.
