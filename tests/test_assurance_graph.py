import json
import hashlib
import pathlib
import sys
import tempfile
import time
import unittest

from tests.test_ezpowers_runtime import (
    RuntimeProject,
    managed_block,
    run_cli,
)


def check_contract(
    check_id: str,
    *,
    delay: float = 0.12,
    exit_code: int = 0,
    safe: bool = True,
    locks: list[str] | None = None,
) -> dict:
    return {
        "id": check_id,
        "argv": [
            sys.executable,
            "-c",
            f"import time; time.sleep({delay}); raise SystemExit({exit_code})",
        ],
        "cwd": ".",
        "timeout_seconds": 10,
        "kind": "integration",
        "concurrency": {
            "safe": safe,
            "resource_locks": list(locks or []),
        },
    }


def write_v2_flow(
    project: RuntimeProject,
    tasks: list[dict],
    *,
    slug: str,
    checks: dict[str, dict] | None = None,
) -> pathlib.Path:
    spec_path = project.root / "docs" / "specs" / f"{slug}.md"
    plan_path = project.root / "docs" / "plans" / f"{slug}.md"
    spec_path.parent.mkdir(parents=True, exist_ok=True)
    plan_path.parent.mkdir(parents=True, exist_ok=True)
    criterion_ids = [
        criterion_id
        for task in tasks
        for criterion_id in task["criteria"]
    ]
    spec = {
        "schema_version": 1,
        "design_context": {
            "required": False,
            "reason": "The fixture has no UI surface.",
        },
        "criteria": [
            {
                "id": criterion_id,
                "requirement_id": f"R-{criterion_id}",
                "claim": f"The {criterion_id} fixture outcome is observable.",
                "verify_type": "integration",
                "integration": True,
            }
            for criterion_id in criterion_ids
        ],
    }
    plan = {
        "schema_version": 2,
        "spec": f"docs/specs/{slug}.md",
        "checks": checks or {},
        "tasks": tasks,
    }
    spec_path.write_text(managed_block("spec", spec), encoding="utf-8")
    plan_path.write_text(managed_block("plan", plan), encoding="utf-8")
    return plan_path


def configure_required_checks(
    project: RuntimeProject,
    checks: dict[str, dict],
    required: list[str],
    *,
    workers: int = 4,
) -> None:
    path = project.root / ".ezpowers" / "config.json"
    value = json.loads(path.read_text(encoding="utf-8"))
    value["schema_version"] = 2
    value["verification"] = {"max_parallel_checks": workers}
    value["checks"] = checks
    value["required_checks"] = required
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def rehash_evidence(project: RuntimeProject, evidence_path: pathlib.Path) -> str:
    data = evidence_path.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    evidence_path.with_name("result.json.sha256").write_text(
        digest + "\n", encoding="ascii"
    )
    state_path = project.root / ".ezpowers" / "state.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    state["latest_evidence"]["all"]["sha256"] = digest
    state_path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    return digest


class AssuranceGraphCompatibilityTests(unittest.TestCase):
    def test_v1_dependency_field_is_not_silently_ignored(self) -> None:
        """This assertion is red on v5.6, which accepted the unknown field."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project = RuntimeProject(pathlib.Path(temp_dir))
            self.assertEqual(0, project.install().returncode)
            plan_path = project.write_flow(
                [
                    {
                        "id": "pass",
                        "argv": [
                            "python",
                            "-c",
                            "from pathlib import Path; assert Path('.').is_dir()",
                        ],
                        "cwd": ".",
                        "timeout_seconds": 10,
                        "kind": "test",
                    }
                ]
            )
            plan = {
                "schema_version": 1,
                "spec": "docs/specs/demo.md",
                "tasks": [
                    {
                        "id": "T1",
                        "depends_on": ["missing-task"],
                        "criteria": ["AC-1"],
                        "checks": [
                            {
                                "id": "pass",
                                "argv": [
                                    "python",
                                    "-c",
                                    "from pathlib import Path; assert Path('.').is_dir()",
                                ],
                                "cwd": ".",
                                "timeout_seconds": 10,
                                "kind": "test",
                            }
                        ],
                    }
                ],
            }
            plan_path.write_text(managed_block("plan", plan), encoding="utf-8")

            result = run_cli(
                project.runtime,
                "validate",
                "--plan",
                str(plan_path),
                "--json",
                cwd=project.root,
            )

            self.assertNotEqual(0, result.returncode, result.stdout + result.stderr)
            errors = " ".join(json.loads(result.stdout)["errors"])
            self.assertIn("schema_version 2", errors)

    def test_v1_flow_remains_serial_and_is_not_rewritten(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = RuntimeProject(pathlib.Path(temp_dir))
            self.assertEqual(0, project.install().returncode)
            plan = project.write_flow(
                [
                    {
                        "id": "first",
                        "argv": [sys.executable, "-c", "import time; time.sleep(.2)"],
                        "cwd": ".",
                        "timeout_seconds": 10,
                        "kind": "integration",
                    },
                    {
                        "id": "second",
                        "argv": [sys.executable, "-c", "import time; time.sleep(.2)"],
                        "cwd": ".",
                        "timeout_seconds": 10,
                        "kind": "integration",
                    },
                ],
                integration=True,
                slug="legacy-serial",
            )
            project.commit_all()
            plan_before = plan.read_bytes()
            config_path = project.root / ".ezpowers" / "config.json"
            config_before = config_path.read_bytes()

            started = time.monotonic()
            verify = run_cli(
                project.runtime,
                "verify",
                "--plan",
                str(plan),
                "--all",
                "--json",
                cwd=project.root,
            )
            elapsed = time.monotonic() - started

            self.assertEqual(0, verify.returncode, verify.stdout + verify.stderr)
            payload = json.loads(verify.stdout)
            self.assertEqual(1, payload["schema_version"])
            self.assertNotIn("execution", payload)
            self.assertGreaterEqual(elapsed, 0.35)
            self.assertEqual(plan_before, plan.read_bytes())
            self.assertEqual(config_before, config_path.read_bytes())


class AssuranceGraphV2Tests(unittest.TestCase):
    def make_project(self, root: pathlib.Path) -> RuntimeProject:
        project = RuntimeProject(root)
        install = project.install()
        self.assertEqual(0, install.returncode, install.stdout + install.stderr)
        return project

    def test_v2_dependency_validation_and_graph_hash_are_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = self.make_project(pathlib.Path(temp_dir))
            tasks = [
                {
                    "id": "T1",
                    "depends_on": [],
                    "criteria": ["AC-1"],
                    "checks": [check_contract("one")],
                },
                {
                    "id": "T2",
                    "depends_on": ["T1"],
                    "criteria": ["AC-2"],
                    "checks": [check_contract("two")],
                },
            ]
            plan = write_v2_flow(project, tasks, slug="dag")
            project.commit_all()
            first = run_cli(
                project.runtime,
                "validate",
                "--plan",
                str(plan),
                "--json",
                cwd=project.root,
            )
            second = run_cli(
                project.runtime,
                "validate",
                "--plan",
                str(plan),
                "--json",
                cwd=project.root,
            )
            self.assertEqual(0, first.returncode, first.stdout + first.stderr)
            self.assertEqual(0, second.returncode, second.stdout + second.stderr)
            first_value = json.loads(first.stdout)
            second_value = json.loads(second.stdout)
            self.assertEqual(
                first_value["assurance_graph_sha256"],
                second_value["assurance_graph_sha256"],
            )
            self.assertEqual([["T1"], ["T2"]], first_value["task_waves"])

            original = {
                "schema_version": 2,
                "spec": "docs/specs/dag.md",
                "checks": {},
                "tasks": tasks,
            }
            invalid_variants = {
                "missing": lambda value: value["tasks"][1].pop("depends_on"),
                "duplicate": lambda value: value["tasks"][1].update(
                    {"depends_on": ["T1", "T1"]}
                ),
                "unknown": lambda value: value["tasks"][1].update(
                    {"depends_on": ["T9"]}
                ),
                "self": lambda value: value["tasks"][1].update(
                    {"depends_on": ["T2"]}
                ),
                "cycle": lambda value: (
                    value["tasks"][0].update({"depends_on": ["T2"]}),
                    value["tasks"][1].update({"depends_on": ["T1"]}),
                ),
            }
            for name, mutate in invalid_variants.items():
                with self.subTest(name=name):
                    candidate = json.loads(json.dumps(original))
                    mutate(candidate)
                    plan.write_text(
                        managed_block("plan", candidate), encoding="utf-8"
                    )
                    invalid = run_cli(
                        project.runtime,
                        "validate",
                        "--plan",
                        str(plan),
                        "--json",
                        cwd=project.root,
                    )
                    self.assertNotEqual(
                        0, invalid.returncode, invalid.stdout + invalid.stderr
                    )
                    self.assertTrue(json.loads(invalid.stdout)["errors"])

    def test_safe_checks_overlap_and_preserve_declaration_order(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = self.make_project(pathlib.Path(temp_dir))
            tasks = [
                {
                    "id": "T1",
                    "depends_on": [],
                    "criteria": ["AC-1"],
                    "checks": [
                        check_contract("first", delay=0.3),
                        check_contract("second", delay=0.3),
                        check_contract("third", delay=0.3),
                    ],
                }
            ]
            plan = write_v2_flow(project, tasks, slug="parallel")
            project.commit_all()
            verify = run_cli(
                project.runtime,
                "verify",
                "--plan",
                str(plan),
                "--all",
                "--json",
                cwd=project.root,
            )
            self.assertEqual(0, verify.returncode, verify.stdout + verify.stderr)
            payload = json.loads(verify.stdout)
            self.assertEqual(2, payload["schema_version"])
            self.assertEqual(
                ["first", "second", "third"],
                [item["id"] for item in payload["tasks"][0]["checks"]],
            )
            self.assertTrue(
                any(wave["parallel"] for wave in payload["execution"]["waves"])
            )
            self.assertEqual(
                payload["assurance_graph_sha256"],
                hashlib.sha256(
                    (
                        json.dumps(
                            payload["assurance_graph"],
                            ensure_ascii=False,
                            indent=2,
                            sort_keys=True,
                        )
                        + "\n"
                    ).encode("utf-8")
                ).hexdigest(),
            )
            certify = run_cli(
                project.runtime,
                "certify",
                "--plan",
                str(plan),
                "--json",
                cwd=project.root,
            )
            self.assertEqual(0, certify.returncode, certify.stdout + certify.stderr)
            certificate = json.loads(
                (
                    project.root
                    / json.loads(certify.stdout)["certificate_path"]
                ).read_text(encoding="utf-8")
            )
            self.assertEqual(2, certificate["schema_version"])
            self.assertEqual(
                payload["assurance_graph_sha256"],
                certificate["assurance_graph_sha256"],
            )

    def test_parallel_and_serial_outcomes_match_for_pass_fail_spawn_and_timeout(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = self.make_project(pathlib.Path(temp_dir))
            base_checks = [
                {
                    "id": "pass",
                    "argv": [sys.executable, "-c", "assert 2 + 2 == 4"],
                    "cwd": ".",
                    "timeout_seconds": 5,
                    "kind": "integration",
                },
                {
                    "id": "fail",
                    "argv": [sys.executable, "-c", "raise SystemExit(9)"],
                    "cwd": ".",
                    "timeout_seconds": 5,
                    "kind": "integration",
                },
                {
                    "id": "spawn",
                    "argv": ["ezpowers-missing-command-assurance-7f3a"],
                    "cwd": ".",
                    "timeout_seconds": 5,
                    "kind": "integration",
                },
                {
                    "id": "timeout",
                    "argv": [sys.executable, "-c", "import time; time.sleep(3)"],
                    "cwd": ".",
                    "timeout_seconds": 1,
                    "kind": "integration",
                },
            ]
            legacy = project.write_flow(
                base_checks,
                integration=True,
                slug="equivalence-v1",
            )
            v2_checks = [
                {
                    **check,
                    "concurrency": {"safe": True, "resource_locks": []},
                }
                for check in base_checks
            ]
            modern = write_v2_flow(
                project,
                [
                    {
                        "id": "T1",
                        "depends_on": [],
                        "criteria": ["AC-1"],
                        "checks": v2_checks,
                    }
                ],
                slug="equivalence-v2",
            )
            project.commit_all()
            serial = run_cli(
                project.runtime,
                "verify",
                "--plan",
                str(legacy),
                "--all",
                "--json",
                cwd=project.root,
            )
            parallel = run_cli(
                project.runtime,
                "verify",
                "--plan",
                str(modern),
                "--all",
                "--json",
                cwd=project.root,
            )
            self.assertEqual(1, serial.returncode, serial.stdout + serial.stderr)
            self.assertEqual(1, parallel.returncode, parallel.stdout + parallel.stderr)

            def outcomes(payload: str) -> list[tuple]:
                return [
                    (
                        item["id"],
                        item["status"],
                        item["exit_code"],
                        item["timed_out"],
                        bool(item["spawn_error"]),
                        item["stdout_sha256"],
                    )
                    for item in json.loads(payload)["tasks"][0]["checks"]
                ]

            self.assertEqual(outcomes(serial.stdout), outcomes(parallel.stdout))

    def test_dependencies_order_execution_but_do_not_skip_after_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = self.make_project(pathlib.Path(temp_dir))
            tasks = [
                {
                    "id": "T2",
                    "depends_on": ["T1"],
                    "criteria": ["AC-2"],
                    "checks": [check_contract("downstream", exit_code=0)],
                },
                {
                    "id": "T1",
                    "depends_on": [],
                    "criteria": ["AC-1"],
                    "checks": [check_contract("upstream", exit_code=7)],
                },
            ]
            plan = write_v2_flow(project, tasks, slug="failure-order")
            project.commit_all()
            verify = run_cli(
                project.runtime,
                "verify",
                "--plan",
                str(plan),
                "--all",
                "--json",
                cwd=project.root,
            )
            self.assertEqual(1, verify.returncode, verify.stdout + verify.stderr)
            payload = json.loads(verify.stdout)
            self.assertEqual(["T2", "T1"], [item["id"] for item in payload["tasks"]])
            by_task = {item["id"]: item for item in payload["tasks"]}
            self.assertEqual("FAIL", by_task["T1"]["checks"][0]["status"])
            self.assertEqual("PASS", by_task["T2"]["checks"][0]["status"])
            self.assertEqual(
                [0, 1],
                [
                    wave["task_wave"]
                    for wave in payload["execution"]["waves"]
                    if wave["phase"] == "task"
                ],
            )

    def test_parallel_workspace_mutation_lists_candidates_without_claiming_cause(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = self.make_project(pathlib.Path(temp_dir))
            writer = check_contract("writer", delay=0)
            writer["argv"] = [
                sys.executable,
                "-c",
                "from pathlib import Path; Path('mutation.txt').write_text('x')",
            ]
            tasks = [
                {
                    "id": "T1",
                    "depends_on": [],
                    "criteria": ["AC-1"],
                    "checks": [writer, check_contract("reader", delay=0.2)],
                }
            ]
            plan = write_v2_flow(project, tasks, slug="workspace-mutation")
            project.commit_all()
            verify = run_cli(
                project.runtime,
                "verify",
                "--plan",
                str(plan),
                "--all",
                "--json",
                cwd=project.root,
            )
            self.assertEqual(1, verify.returncode, verify.stdout + verify.stderr)
            payload = json.loads(verify.stdout)
            self.assertIn("workspace changed during verification", payload["reasons"])
            self.assertEqual("not-proven", payload["workspace_mutation_causality"])
            self.assertEqual(
                sorted(item["node_id"] for item in payload["tasks"][0]["checks"]),
                payload["parallel_workspace_mutation_candidates"],
            )

    def test_resource_locks_unsafe_barriers_and_duplicate_occurrences(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = self.make_project(pathlib.Path(temp_dir))
            repeated = check_contract("repeated", delay=0.1)
            tasks = [
                {
                    "id": "T1",
                    "depends_on": [],
                    "criteria": ["AC-1"],
                    "checks": [
                        check_contract("locked-a", locks=["shared"]),
                        check_contract("locked-b", locks=["shared"]),
                        "repeated",
                        "repeated",
                        check_contract("barrier", safe=False),
                    ],
                }
            ]
            plan = write_v2_flow(
                project,
                tasks,
                slug="locks",
                checks={"repeated": repeated},
            )
            project.commit_all()
            verify = run_cli(
                project.runtime,
                "verify",
                "--plan",
                str(plan),
                "--all",
                "--json",
                cwd=project.root,
            )
            self.assertEqual(0, verify.returncode, verify.stdout + verify.stderr)
            payload = json.loads(verify.stdout)
            waves = payload["execution"]["waves"]
            node_batches = [set(wave["node_ids"]) for wave in waves]
            locked_nodes = {
                item["node_id"]
                for item in payload["tasks"][0]["checks"]
                if item["id"] in {"locked-a", "locked-b"}
            }
            self.assertFalse(any(locked_nodes.issubset(batch) for batch in node_batches))
            repeated_results = [
                item for item in payload["tasks"][0]["checks"] if item["id"] == "repeated"
            ]
            self.assertEqual(2, len(repeated_results))
            self.assertEqual(2, len({item["node_id"] for item in repeated_results}))
            self.assertEqual(4, len({item["stdout_log"] for item in repeated_results for _ in (0,)} | {item["stderr_log"] for item in repeated_results}))
            barrier = next(
                item for item in payload["tasks"][0]["checks"] if item["id"] == "barrier"
            )
            self.assertTrue(
                any(wave["node_ids"] == [barrier["node_id"]] for wave in waves)
            )

    def test_required_checks_run_after_tasks_and_task_scope_ignores_dependencies(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = self.make_project(pathlib.Path(temp_dir))
            configure_required_checks(
                project,
                {
                    "required-a": check_contract("required-a"),
                    "required-b": check_contract("required-b"),
                },
                ["required-a", "required-b"],
            )
            tasks = [
                {
                    "id": "T1",
                    "depends_on": [],
                    "criteria": ["AC-1"],
                    "checks": [check_contract("dependency")],
                },
                {
                    "id": "T2",
                    "depends_on": ["T1"],
                    "criteria": ["AC-2"],
                    "checks": [check_contract("selected")],
                },
            ]
            plan = write_v2_flow(project, tasks, slug="scope")
            project.commit_all()
            task_only = run_cli(
                project.runtime,
                "verify",
                "--plan",
                str(plan),
                "--task",
                "T2",
                "--json",
                cwd=project.root,
            )
            self.assertEqual(0, task_only.returncode, task_only.stdout + task_only.stderr)
            task_value = json.loads(task_only.stdout)
            self.assertEqual(["T2"], [item["id"] for item in task_value["tasks"]])
            self.assertEqual([], task_value["project_checks"])
            self.assertTrue(
                all(
                    wave["task_wave"] is None
                    for wave in task_value["execution"]["waves"]
                )
            )

            all_scope = run_cli(
                project.runtime,
                "verify",
                "--plan",
                str(plan),
                "--all",
                "--json",
                cwd=project.root,
            )
            self.assertEqual(0, all_scope.returncode, all_scope.stdout + all_scope.stderr)
            phases = [wave["phase"] for wave in json.loads(all_scope.stdout)["execution"]["waves"]]
            self.assertEqual("required", phases[-1])
            self.assertNotIn("task", phases[phases.index("required") :])

    def test_trace_is_log_free_and_graph_tampering_blocks_certification(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = self.make_project(pathlib.Path(temp_dir))
            tasks = [
                {
                    "id": "T1",
                    "depends_on": [],
                    "criteria": ["AC-1"],
                    "checks": [check_contract("traceable")],
                }
            ]
            plan = write_v2_flow(project, tasks, slug="trace")
            project.commit_all()
            activate = run_cli(
                project.runtime,
                "validate",
                "--plan",
                str(plan),
                "--activate",
                "--json",
                cwd=project.root,
            )
            self.assertEqual(0, activate.returncode, activate.stdout + activate.stderr)
            trace = run_cli(
                project.runtime,
                "trace",
                "--plan",
                str(plan),
                "--json",
                cwd=project.root,
            )
            self.assertEqual(0, trace.returncode, trace.stdout + trace.stderr)
            trace_value = json.loads(trace.stdout)
            self.assertTrue(trace_value["blocking_paths"])
            self.assertIsNotNone(trace_value["primary_blocker"])
            self.assertNotIn('"argv"', trace.stdout)
            self.assertNotIn(".stdout.log", trace.stdout)
            self.assertEqual(
                sorted(node["id"] for node in trace_value["graph"]["nodes"]),
                [node["id"] for node in trace_value["graph"]["nodes"]],
            )
            status = json.loads(
                run_cli(project.runtime, "status", "--json", cwd=project.root).stdout
            )
            self.assertEqual(
                trace_value["assurance_graph_sha256"],
                status["assurance_graph_sha256"],
            )
            self.assertIsNotNone(status["primary_blocker"])

            verify = run_cli(
                project.runtime,
                "verify",
                "--plan",
                str(plan),
                "--all",
                "--json",
                cwd=project.root,
            )
            self.assertEqual(0, verify.returncode, verify.stdout + verify.stderr)
            evidence_path = project.root / json.loads(verify.stdout)["evidence_path"]
            evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
            evidence["assurance_graph"]["nodes"][0]["type"] = "tampered"
            evidence_path.write_text(
                json.dumps(evidence, ensure_ascii=False, indent=2, sort_keys=True)
                + "\n",
                encoding="utf-8",
            )
            rehash_evidence(project, evidence_path)
            certify = run_cli(
                project.runtime,
                "certify",
                "--plan",
                str(plan),
                "--json",
                cwd=project.root,
            )
            self.assertNotEqual(0, certify.returncode, certify.stdout + certify.stderr)
            self.assertIn(
                "assurance graph",
                " ".join(json.loads(certify.stdout)["reasons"]).lower(),
            )


if __name__ == "__main__":
    unittest.main()
