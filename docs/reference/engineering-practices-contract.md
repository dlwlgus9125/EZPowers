# Engineering Practices Contract

This contract defines three optional product-code disciplines distributed by
EZPowers. They improve diagnosis and code design without becoming a second
executor, completion authority, or documentation owner.

## Provenance

The skills are EZPowers-owned adaptations of Matt Pocock's engineering skills
at upstream commit
`ed37663cc5fbef691ddfecd080dff42f7e7e350d`:

- upstream `diagnosing-bugs` maps to EZPowers `diagnose`;
- upstream `codebase-design` maps to EZPowers `codebase-design`;
- upstream `improve-codebase-architecture` maps to the same EZPowers name.

The adaptations preserve the feedback-loop and deep-module principles while
removing Claude-only agent assumptions, live upstream dependencies,
automatic documentation mutation, and CDN-backed report output.

Upstream source:
https://github.com/mattpocock/skills/tree/ed37663cc5fbef691ddfecd080dff42f7e7e350d/skills/engineering

Third-party notice:

```text
MIT License

Copyright (c) 2026 Matt Pocock

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

Updates are explicit source reviews. Installation and skill execution never
fetch upstream content.

The upstream `improve-codebase-architecture/SKILL.md` at `main` was reviewed
again on 2026-07-30 and was byte-identical to the pinned source. Upstream
hotspot scoping, organic exploration, visual before/after comparison, and
post-selection design remain behavioral benchmarks. Claude-only exploration,
automatic `CONTEXT.md` or ADR mutation, and CDN report assets remain
intentional non-goals rather than parity defects.

## Shared authority boundary

Claude Code or Codex owns repository inspection, commands, edits, and any
host-native assistance. EZPowers supplies the skill instructions and a
deterministic advisory report renderer.

These skills do not:

- create another retry or continuation loop;
- change harness-chain attempts, receipts, approval, or terminal state;
- promote task-scoped checks into completion evidence;
- certify work without fresh all-scope verification;
- silently edit canonical documentation, `CONTEXT.md`, or ADRs.

Read repository instructions, Git state, registered documentation when
present, relevant ADRs, and existing tests before using any discipline.
Repository evidence overrides conversation memory and wiki candidates.

## Invocation and role separation

`diagnose` and `codebase-design` may be matched implicitly. A matched skill
provides discipline inside the current user request; it does not expand that
request's write authority. An explicit `diagnose` invocation, or a request to
fix, debug, repair, resolve, or make a failure pass, selects FIX-COMPLETE
unless the user also limits the task to analysis or no edits. A bare symptom
matched implicitly starts read-only and asks once before editing only when the
requested outcome is genuinely ambiguous.

`improve-codebase-architecture` is explicit-only because it performs a broad
scan and creates a temporary report. It analyzes existing product code.
`design-architecture` remains the owner of durable project boundary,
deployment, data-flow, and verification-design decisions.

## Diagnostic completion

A diagnosis has a hard reproduction gate. Before any hypothesis, root-cause
claim, fix proposal, or product-behavior edit, the host must name a command it
already ran and retain the exit result and output that show the user's exact
symptom red. A merely red-capable command, adjacent failing test, nearby
exception, suspicious implementation, or unrelated nonzero exit is not
reproduction evidence.

Before that exact-red observation, repository edits are limited to tests,
fixtures, captured replays, throwaway harnesses, and explicitly approved
temporary instrumentation that does not change product behavior. The host must
then minimise the reproduced scenario by rerunning after each reduction and
preserve the original unminimised command. Only after exact-red and
minimised-red evidence may it rank falsifiable hypotheses, instrument
predictions, or trace the first divergence. Hypotheses consume reproduction
evidence; they never substitute for it.

For flaky behavior, the red signal is a recorded repeatable failure rate high
enough to debug. For performance, it is a measured comparable baseline and
threshold crossed by the reported regression. ANALYSIS-ONLY requests observe
the same reproduction gate and stop before code or regression-test edits.

If no exact-red loop can be built, the host stops without hypotheses or a
product patch. It reports the commands and methods already tried with their
results and requests the specific environment access, captured artifact, or
temporary instrumentation permission required to continue.

In FIX-COMPLETE, root cause is an intermediate result. The host must continue
through a red regression signal, the smallest source-cause patch, the original
unminimised reproduction, affected caller/project checks, temporary-debug
cleanup, and final diff review. It must not hand control back merely because a
reproduction, hypothesis, first divergence, or targeted green result exists.

The regression test must cross the honest interface seam and fail before the
fix. If no honest seam exists, preserve the minimal command or harness as the
red/green regression signal, complete the authorized fix, and report the seam
as a follow-up rather than substituting a shallow test or abandoning the fix.
A failed patch becomes evidence; after three failed patch experiments, rebuild
the loop and hypotheses before another edit instead of ending with an
unverified explanation.

Targeted success is not EZPowers completion; fresh all-scope verify and certify
remain required during managed execution.

## Deep-module design

Use Module, Interface, Implementation, Depth, Seam, Adapter, Leverage, and
Locality consistently. The Interface includes invariants, ordering, error
modes, configuration, and performance characteristics, not only a type
signature.

Apply these rules:

- the deletion test distinguishes useful depth from pass-through structure;
- callers and tests should cross the same interface seam;
- one adapter is a hypothetical seam and two independently required adapters
  establish real variation;
- compare at least two materially different interfaces before settling a
  consequential design;
- do not add abstraction only to make an implementation mockable.

## Architecture report input v2

Schema version 2 replaces the temporary v1 input; reports are non-durable, so
project refresh upgrades the skill and renderer together. The renderer accepts
one UTF-8 JSON object up to 1 MiB:

```json
{
  "schema_version": 2,
  "language": "en",
  "repository": {
    "name": "example",
    "revision": "abc123",
    "dirty": false
  },
  "scope": "Recently changed Order intake modules",
  "scope_basis": "git_hotspot",
  "scope_rationale": "Order intake recurs in recent product changes.",
  "generated_at": "2026-07-30T00:00:00Z",
  "top_recommendation": {
    "candidate_id": "order-intake",
    "rationale": "Repeated policy gains the most locality."
  },
  "candidates": []
}
```

`scope_basis` is `user_named`, `git_hotspot`, or `widened`. There must be
1-8 candidates. A bounded scan with no evidence-backed candidate stops without
rendering rather than inventing one. Each rendered candidate has exactly:

- `id`, `title`, and `strength`, where strength is `strong`,
  `worth_exploring`, or `speculative`;
- 1-20 existing repository-relative affected product/test `files`;
- 1-20 `evidence` items containing `path`, required positive `line`, `finding`,
  and role `product`, `test`, `context`, or `decision`;
- non-empty `problem`, responsibility-level `solution`, `test_effect`,
  `compatibility`, `migration`, and 1-20 `benefits`;
- `adr` with status `none`, `aligned`, `conflicts`, or `revisit`, references,
  and a finding;
- `before` and `after` graphs.

Product/test evidence must cover the affected `files` exactly. Context and
decision evidence may cite additional files. Every non-`none` ADR status
requires an existing reference backed by line-specific decision evidence.

Each graph contains 1-24 unique nodes and 0-48 edges. A node has `id`, `label`,
integer `layer` from 0 through 7, `kind` from `caller`, `module`, `adapter`,
`dependency`, `data`, or `external`, and optional emphasis `normal`, `shallow`,
`deep`, or `faded`. An edge has `from`, `to`, optional `label`, and optional
kind `call`, `dependency`, `leak`, or `seam`; both endpoints must exist.

IDs use lower-case hyphen form and are at most 64 characters. Titles and graph
labels are at most 200 characters, paths at most 512, and prose fields at most
8,000. Unknown fields, duplicate values, unsafe or missing paths, nonexistent
evidence lines, uncovered affected files, dangling edges, invalid timestamps,
and an unknown top recommendation fail validation.

The installed skill carries the focused executable schema from
`skills/improve-codebase-architecture/references/report-contract.md`, so a scan
does not load the unrelated diagnosis contract. Its
`skills/improve-codebase-architecture/scripts/render-report.py` resolves the
same canonical renderer from an installed project kit or the plugin root.

## Renderer output and safety

The installed interface is:

```text
python .ezpowers/tools/architecture-review-report.py
  --project-root <root>
  --input <report.json>
  [--output <outside-repository.html>]
  [--open]
  [--json]
```

Without `--output`, use a unique file under the OS temporary directory. Reject
repository-internal output, non-HTML output, a missing output parent, and any
existing output file. Write atomically.

The report uses semantic HTML, inline CSS and SVG, a restrictive Content
Security Policy, and escaped input. It contains no script, remote request,
font, image, or analytics dependency. The JSON receipt contains `status`,
`schema_version`, `report_path`, `report_sha256`, `input_sha256`,
`source_sha256`, `source_file_count`, `candidate_count`, `opened`, and
`warnings`. `source_sha256` binds all cited and affected file bytes at render
time. Failure to open the browser is a warning after successful generation.

Reports are temporary local advisory data. The skill deletes its temporary
input JSON after rendering. Neither is registered documentation, a wiki page,
completion evidence, or a workspace fingerprint exclusion if a user manually
copies it into the repository.
