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

## Architecture report input v1

The renderer accepts one UTF-8 JSON object up to 1 MiB:

```json
{
  "schema_version": 1,
  "language": "en",
  "repository": {
    "name": "example",
    "revision": "abc123",
    "dirty": false
  },
  "scope": "Recently changed order-processing modules",
  "generated_at": "2026-07-24T00:00:00Z",
  "top_recommendation_id": "order-intake",
  "candidates": []
}
```

There must be 1-8 candidates. Each candidate has exactly:

- `id`, `title`, and `strength`, where strength is `strong`,
  `worth_exploring`, or `speculative`;
- 1-20 existing repository-relative `files`;
- 1-20 `evidence` items containing `path`, optional positive `line`, and
  `finding`;
- non-empty `problem`, `solution`, `test_effect`, and 1-20 `benefits`;
- `before` and `after` graphs.

Each graph contains 1-24 unique nodes and 0-48 edges. A node has `id`, `label`,
integer `layer` from 0 through 7, and `kind` from `caller`, `module`, `adapter`,
`dependency`, `data`, or `external`. An edge has `from`, `to`, and an optional
`label`; both endpoints must exist in that graph.

IDs use lower-case hyphen form and are at most 64 characters. Titles and graph
labels are at most 200 characters, paths at most 512, and prose fields at most
8,000. Unknown fields, duplicate values, unsafe paths, missing paths, dangling
edges, invalid timestamps, and an unknown top recommendation fail validation.

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
`report_path`, `report_sha256`, `candidate_count`, `opened`, and `warnings`.
Failure to open the browser is a warning after successful generation.

Reports and their input JSON are temporary local advisory data. They are not
registered documentation, wiki pages, completion evidence, or workspace
fingerprint exclusions if a user manually copies them into the repository.
