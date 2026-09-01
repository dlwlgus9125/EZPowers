# F24 implementation plan

## Goal and constraints

Add one project-profile policy seam around the current normalizer and chain
review boundary. Keep the exact-command scheduler, software graph, evidence
layout, host adapters, catalog counts, standard-library runtime, and current
DESIGN.md mapping unchanged.

## Ordered slices

1. Add compatible profile/config/plan contracts and planning assurance nodes
   while pinning legacy software outputs.
2. Bind declared artifact bytes into ordinary verification, freshness, trace,
   and certification.
3. Add planning bundle, approval, artifact-review receipt, rework, and
   dual-host chain behavior.
4. Update skills, contracts, release surfaces, kit hashes, and measured
   compatibility evidence.

<!-- ezpowers:plan:start -->
```json
{
  "schema_version": 2,
  "spec": "docs/specs/f24-planning-profile.md",
  "checks": {
    "planning-profile-tests": {
      "argv": ["python", "-m", "unittest", "tests.test_planning_profile"],
      "cwd": ".",
      "timeout_seconds": 600,
      "kind": "integration",
      "concurrency": {
        "safe": false,
        "resource_locks": []
      }
    },
    "harness-chain-tests": {
      "argv": ["python", "-m", "unittest", "tests.test_harness_chain"],
      "cwd": ".",
      "timeout_seconds": 900,
      "kind": "integration",
      "concurrency": {
        "safe": false,
        "resource_locks": []
      }
    },
    "software-profile-benchmark": {
      "argv": ["python", "scripts/benchmark_software_profile.py", "--baseline-ref", "08f9f84d24c59ec130dd6b3bf26555503910cbab", "--runs", "5", "--maximum-regression", "5"],
      "cwd": ".",
      "timeout_seconds": 300,
      "kind": "smoke",
      "concurrency": {
        "safe": false,
        "resource_locks": []
      }
    }
  },
  "tasks": [
    {
      "id": "T1",
      "depends_on": [],
      "criteria": ["AC-1", "AC-2", "AC-3"],
      "checks": ["planning-profile-tests"]
    },
    {
      "id": "T2",
      "depends_on": ["T1"],
      "criteria": ["AC-4", "AC-5"],
      "checks": ["planning-profile-tests"]
    },
    {
      "id": "T3",
      "depends_on": ["T1", "T2"],
      "criteria": ["AC-6", "AC-7"],
      "checks": ["planning-profile-tests", "harness-chain-tests"]
    },
    {
      "id": "T4",
      "depends_on": ["T3"],
      "criteria": ["AC-8"],
      "checks": ["repo-check", "kit-manifest", "plugin-files"]
    },
    {
      "id": "T5",
      "depends_on": ["T4"],
      "criteria": ["AC-9"],
      "checks": ["software-profile-benchmark"]
    }
  ]
}
```
<!-- ezpowers:plan:end -->
