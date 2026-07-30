# Architecture Report Contract

Use this focused execution contract for `improve-codebase-architecture`. The
canonical provenance and authority boundary remain in
`docs/reference/engineering-practices-contract.md`; this reference contains
only the report input and output needed during a scan.

## Input schema version 2

Pass one UTF-8 JSON object of at most 1 MiB:

```json
{
  "schema_version": 2,
  "language": "en",
  "repository": {
    "name": "example",
    "revision": "abc123",
    "dirty": false
  },
  "scope": "Order intake product code and tests",
  "scope_basis": "user_named",
  "scope_rationale": "The user named Order intake.",
  "generated_at": "2026-07-30T00:00:00Z",
  "top_recommendation": {
    "candidate_id": "order-intake",
    "rationale": "Repeated policy gains the most locality."
  },
  "candidates": [
    {
      "id": "order-intake",
      "title": "Deepen Order intake",
      "strength": "strong",
      "files": ["src/order.py", "tests/test_order.py"],
      "evidence": [
        {
          "path": "src/order.py",
          "line": 17,
          "role": "product",
          "finding": "Two callers repeat the required ordering."
        },
        {
          "path": "tests/test_order.py",
          "line": 12,
          "role": "test",
          "finding": "Tests bypass the intended product interface."
        }
      ],
      "problem": "Ordering policy leaks into callers.",
      "solution": "Concentrate the complete responsibility in one module; defer its interface until selection.",
      "benefits": ["Locality: one implementation owns ordering."],
      "test_effect": "Existing behavior tests survive internal refactoring.",
      "compatibility": "Preserve current public entry points.",
      "migration": "Delegate one caller at a time.",
      "adr": {
        "status": "none",
        "references": [],
        "finding": "No applicable ADR exists."
      },
      "before": {
        "nodes": [
          {
            "id": "thin-module",
            "label": "Thin module",
            "layer": 0,
            "kind": "module",
            "emphasis": "shallow"
          }
        ],
        "edges": []
      },
      "after": {
        "nodes": [
          {
            "id": "deep-module",
            "label": "Deep module",
            "layer": 0,
            "kind": "module",
            "emphasis": "deep"
          }
        ],
        "edges": []
      }
    }
  ]
}
```

Use `scope_basis` `user_named`, `git_hotspot`, or `widened`. Use strength
`strong`, `worth_exploring`, or `speculative`. Keep 1–8 candidates, 1–20
affected files, 1–20 evidence items, and 1–20 benefits per candidate.

Every evidence item requires an existing repository-relative UTF-8 file, an
actual positive line within that file, a finding, and role `product`, `test`,
`context`, or `decision`. `files` contains only affected product and test
paths; product/test evidence must cover that set exactly. Context and decision
evidence may cite additional files.

Use ADR status `none`, `aligned`, `conflicts`, or `revisit`. `none` requires no
references. Every other status requires at least one existing reference with
line-specific `decision` evidence.

Each before/after graph has 1–24 unique nodes and 0–48 edges. Node `kind` is
`caller`, `module`, `adapter`, `dependency`, `data`, or `external`; optional
`emphasis` is `normal`, `shallow`, `deep`, or `faded`. An edge contains `from`,
`to`, optional `label`, and optional `kind` `call`, `dependency`, `leak`, or
`seam`. Both endpoints must exist.

IDs use lower-case hyphen form and are at most 64 characters. Unknown fields,
duplicates, unsafe or missing paths, nonexistent evidence lines, uncovered
affected files, dangling edges, invalid timestamps, and unknown top candidates
fail validation.

## Output and safety

The renderer writes semantic HTML with inline CSS/SVG and a restrictive Content
Security Policy. It uses no scripts, remote requests, fonts, images, analytics,
or third-party packages. Output must be a new `.html` file outside the project
root and is written atomically.

The JSON receipt contains `status`, `schema_version`, `report_path`,
`report_sha256`, `input_sha256`, `source_sha256`, `source_file_count`,
`candidate_count`, `opened`, and `warnings`. `source_sha256` binds all cited
and affected file bytes at render time. Browser-open failure is a warning after
successful generation.

The report is temporary local advice, not repository documentation, completion
evidence, or a workspace-fingerprint exclusion.
