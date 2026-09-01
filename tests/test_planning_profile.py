import hashlib
import json
import pathlib
import re
import sys
import tempfile
import unittest

from tests.test_ezpowers_runtime import (
    EZPOWERS,
    REPO_ROOT,
    RuntimeProject,
    managed_block,
    run_cli,
)
from tests.test_harness_chain import ChainProject


def check_contract(check_id: str, code: str) -> dict:
    return {
        "id": check_id,
        "argv": [sys.executable, "-c", code],
        "cwd": ".",
        "timeout_seconds": 30,
        "kind": "integration",
        "concurrency": {"safe": False, "resource_locks": []},
    }


def write_planning_flow(
    project: RuntimeProject,
    *,
    slug: str,
    criteria: list[str],
    checks: dict[str, dict],
    tasks: list[dict],
    inputs: list[dict],
    deliverables: list[dict],
) -> pathlib.Path:
    spec_path = project.root / "docs" / "specs" / f"{slug}.md"
    plan_path = project.root / "docs" / "plans" / f"{slug}.md"
    spec_path.parent.mkdir(parents=True, exist_ok=True)
    plan_path.parent.mkdir(parents=True, exist_ok=True)
    spec = {
        "schema_version": 1,
        "design_context": {
            "required": False,
            "reason": "The planning fixture has no user interface.",
        },
        "criteria": [
            {
                "id": criterion_id,
                "requirement_id": f"R-{criterion_id}",
                "claim": f"Planning deliverable {criterion_id} is validated by a real command.",
                "verify_type": "integration",
                "integration": True,
            }
            for criterion_id in criteria
        ],
    }
    plan = {
        "schema_version": 3,
        "spec": f"docs/specs/{slug}.md",
        "inputs": inputs,
        "deliverables": deliverables,
        "checks": checks,
        "tasks": tasks,
    }
    spec_path.write_text(managed_block("spec", spec), encoding="utf-8")
    plan_path.write_text(managed_block("plan", plan), encoding="utf-8")
    return plan_path


def planning_project(root: pathlib.Path) -> RuntimeProject:
    project = RuntimeProject(root)
    installed = project.install("--project-profile", "planning")
    if installed.returncode != 0:
        raise AssertionError(installed.stdout + installed.stderr)
    return project


class PlanningProfileRuntimeTests(unittest.TestCase):
    def test_setup_selects_and_explicitly_migrates_the_project_profile(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = RuntimeProject(pathlib.Path(temp_dir))
            installed = project.install()
            self.assertEqual(0, installed.returncode, installed.stdout + installed.stderr)
            config_path = project.root / ".ezpowers" / "config.json"
            software_bytes = config_path.read_bytes()
            software = json.loads(software_bytes)
            self.assertEqual(2, software["schema_version"])
            self.assertNotIn("project_profile", software)

            unchanged = project.install("--project-profile", "software")
            self.assertEqual(0, unchanged.returncode, unchanged.stdout + unchanged.stderr)
            self.assertEqual(software_bytes, config_path.read_bytes())

            state_path = project.root / ".ezpowers" / "state.json"
            state = json.loads(state_path.read_text(encoding="utf-8"))
            state["latest_evidence"]["all"] = {"path": "old", "sha256": "0" * 64}
            state["latest_certificate"] = {"path": "old", "sha256": "1" * 64}
            state["chain_run"] = {"status": "RUNNING", "run_id": "old-run"}
            state_path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")

            migrated = project.install("--project-profile", "planning")
            self.assertEqual(0, migrated.returncode, migrated.stdout + migrated.stderr)
            planning = json.loads(config_path.read_text(encoding="utf-8"))
            self.assertEqual(3, planning["schema_version"])
            self.assertEqual("planning", planning["project_profile"])
            migrated_state = json.loads(state_path.read_text(encoding="utf-8"))
            self.assertIsNone(migrated_state["latest_evidence"]["all"])
            self.assertIsNone(migrated_state["latest_certificate"])
            self.assertEqual("NEEDS_REAPPROVAL", migrated_state["chain_run"]["status"])

            back = project.install("--project-profile", "software")
            self.assertEqual(0, back.returncode, back.stdout + back.stderr)
            software_v3 = json.loads(config_path.read_text(encoding="utf-8"))
            self.assertEqual(3, software_v3["schema_version"])
            self.assertEqual("software", software_v3["project_profile"])

    def test_planning_contract_fails_closed_and_rejects_unsafe_or_ambiguous_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = planning_project(pathlib.Path(temp_dir))
            input_path = project.root / "inputs" / "source.xlsx"
            input_path.parent.mkdir(parents=True)
            input_path.write_bytes(b"\x00planning-input\xff")
            output_path = project.root / "deliverables" / "report.md"
            output_path.parent.mkdir(parents=True)
            output_path.write_text("report\n", encoding="utf-8")
            plan_path = write_planning_flow(
                project,
                slug="contract",
                criteria=["AC-1"],
                checks={
                    "inspect": check_contract(
                        "inspect",
                        "from pathlib import Path; assert Path('deliverables/report.md').is_file()",
                    )
                },
                tasks=[
                    {
                        "id": "T1",
                        "depends_on": [],
                        "criteria": ["AC-1"],
                        "checks": ["inspect"],
                    }
                ],
                inputs=[{"id": "source", "path": "inputs/source.xlsx"}],
                deliverables=[
                    {
                        "id": "report",
                        "paths": ["deliverables/report.md"],
                        "criteria": ["AC-1"],
                        "input_ids": ["source"],
                        "review": {"mode": "direct", "checks": []},
                    }
                ],
            )
            valid = run_cli(
                project.runtime,
                "validate",
                "--plan",
                str(plan_path),
                "--json",
                cwd=project.root,
            )
            self.assertEqual(0, valid.returncode, valid.stdout + valid.stderr)

            match = re.search(
                r"```json\s*(\{.*?\})\s*```",
                plan_path.read_text(encoding="utf-8"),
                re.DOTALL,
            )
            self.assertIsNotNone(match)
            value = json.loads(match.group(1))
            value["schema_version"] = 2
            plan_path.write_text(managed_block("plan", value), encoding="utf-8")
            mismatch = run_cli(
                project.runtime,
                "validate",
                "--plan",
                str(plan_path),
                "--json",
                cwd=project.root,
            )
            self.assertNotEqual(0, mismatch.returncode)
            self.assertIn("requires plan schema_version 3", mismatch.stdout)

            value["schema_version"] = 3
            value["inputs"][0]["path"] = "../source.xlsx"
            value["deliverables"][0]["paths"] = ["inputs/source.xlsx"]
            plan_path.write_text(managed_block("plan", value), encoding="utf-8")
            unsafe = run_cli(
                project.runtime,
                "validate",
                "--plan",
                str(plan_path),
                "--json",
                cwd=project.root,
            )
            self.assertNotEqual(0, unsafe.returncode)
            self.assertIn("safe project product path", unsafe.stdout)

    def test_verify_binds_binary_inputs_ignored_outputs_trace_and_certificate(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = planning_project(pathlib.Path(temp_dir))
            (project.root / ".gitignore").write_text(
                "__pycache__/\n*.py[cod]\ndeliverables/\n.ezpowers/evidence/\n",
                encoding="utf-8",
            )
            input_path = project.root / "inputs" / "source.xlsx"
            input_path.parent.mkdir(parents=True)
            input_path.write_bytes(b"PK\x03\x04\x00\xffinput")
            md_path = project.root / "deliverables" / "brief.md"
            xlsx_path = project.root / "deliverables" / "budget.xlsx"
            md_path.parent.mkdir(parents=True)
            md_path.write_text("# Brief\n", encoding="utf-8")
            xlsx_path.write_bytes(b"PK\x03\x04budget")
            checks = {
                "md-check": check_contract(
                    "md-check",
                    "from pathlib import Path; assert Path('deliverables/brief.md').read_text(encoding='utf-8').startswith('# Brief')",
                ),
                "xlsx-inspect": check_contract(
                    "xlsx-inspect",
                    "from pathlib import Path; data=Path('deliverables/budget.xlsx').read_bytes(); assert data.startswith(b'PK'); print('budget rows inspected')",
                ),
            }
            plan_path = write_planning_flow(
                project,
                slug="evidence",
                criteria=["AC-1", "AC-2"],
                checks=checks,
                tasks=[
                    {
                        "id": "T1",
                        "depends_on": [],
                        "criteria": ["AC-1"],
                        "checks": ["md-check"],
                    },
                    {
                        "id": "T2",
                        "depends_on": ["T1"],
                        "criteria": ["AC-2"],
                        "checks": ["xlsx-inspect"],
                    },
                ],
                inputs=[{"id": "source", "path": "inputs/source.xlsx"}],
                deliverables=[
                    {
                        "id": "brief",
                        "paths": ["deliverables/brief.md"],
                        "criteria": ["AC-1"],
                        "input_ids": ["source"],
                        "review": {"mode": "direct", "checks": []},
                    },
                    {
                        "id": "budget",
                        "paths": ["deliverables/budget.xlsx"],
                        "criteria": ["AC-2"],
                        "input_ids": ["source"],
                        "review": {"mode": "inspected", "checks": ["xlsx-inspect"]},
                    },
                ],
            )
            project.commit_all()

            validated = run_cli(
                project.runtime,
                "validate",
                "--plan",
                str(plan_path),
                "--activate",
                "--json",
                cwd=project.root,
            )
            self.assertEqual(0, validated.returncode, validated.stdout + validated.stderr)
            validation = json.loads(validated.stdout)
            self.assertRegex(validation["assurance_graph_sha256"], r"^[0-9a-f]{64}$")

            verified = run_cli(
                project.runtime,
                "verify",
                "--plan",
                str(plan_path),
                "--all",
                "--json",
                cwd=project.root,
            )
            self.assertEqual(0, verified.returncode, verified.stdout + verified.stderr)
            evidence = json.loads(verified.stdout)
            self.assertEqual(3, evidence["schema_version"])
            self.assertEqual("planning", evidence["project_profile"])
            self.assertEqual(hashlib.sha256(input_path.read_bytes()).hexdigest(), evidence["artifacts"]["inputs"][0]["sha256"])
            self.assertEqual(2, len(evidence["artifacts"]["deliverables"]))

            trace = run_cli(
                project.runtime,
                "trace",
                "--plan",
                str(plan_path),
                "--json",
                cwd=project.root,
            )
            self.assertEqual(0, trace.returncode, trace.stdout + trace.stderr)
            trace_value = json.loads(trace.stdout)
            self.assertEqual("planning", trace_value["project_profile"])
            self.assertEqual(2, trace_value["graph"]["schema_version"])
            self.assertEqual("planning", trace_value["graph"]["project_profile"])
            node_types = {node["type"] for node in trace_value["graph"]["nodes"]}
            self.assertTrue({"input", "deliverable"}.issubset(node_types))
            self.assertIn(
                "review:artifact-review",
                {item["id"] for item in trace_value["node_states"]},
            )

            certified = run_cli(
                project.runtime,
                "certify",
                "--plan",
                str(plan_path),
                "--json",
                cwd=project.root,
            )
            self.assertEqual(0, certified.returncode, certified.stdout + certified.stderr)
            status = run_cli(project.runtime, "status", "--json", cwd=project.root)
            self.assertEqual("CERTIFIED", json.loads(status.stdout)["status"])

            xlsx_path.write_bytes(b"PK\x03\x04tampered")
            stale = run_cli(project.runtime, "status", "--json", cwd=project.root)
            stale_value = json.loads(stale.stdout)
            self.assertEqual("STALE", stale_value["status"])
            self.assertIn("declared planning artifacts changed", " ".join(stale_value["reasons"]))

    def test_verify_rejects_missing_or_check_mutated_deliverables(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = planning_project(pathlib.Path(temp_dir))
            (project.root / ".gitignore").write_text(
                "deliverables/\n.ezpowers/evidence/\n",
                encoding="utf-8",
            )
            input_path = project.root / "inputs" / "source.bin"
            input_path.parent.mkdir(parents=True)
            input_path.write_bytes(b"source")
            output_path = project.root / "deliverables" / "result.bin"
            plan_path = write_planning_flow(
                project,
                slug="mutation",
                criteria=["AC-1"],
                checks={
                    "mutator": check_contract(
                        "mutator",
                        "from pathlib import Path; Path('deliverables/result.bin').write_bytes(b'changed')",
                    )
                },
                tasks=[
                    {
                        "id": "T1",
                        "depends_on": [],
                        "criteria": ["AC-1"],
                        "checks": ["mutator"],
                    }
                ],
                inputs=[{"id": "source", "path": "inputs/source.bin"}],
                deliverables=[
                    {
                        "id": "result",
                        "paths": ["deliverables/result.bin"],
                        "criteria": ["AC-1"],
                        "input_ids": ["source"],
                        "review": {"mode": "direct", "checks": []},
                    }
                ],
            )
            project.commit_all()
            missing = run_cli(
                project.runtime,
                "verify",
                "--plan",
                str(plan_path),
                "--all",
                "--json",
                cwd=project.root,
            )
            self.assertNotEqual(0, missing.returncode)
            self.assertIn("does not exist", missing.stdout)

            output_path.parent.mkdir(parents=True)
            output_path.write_bytes(b"before")
            mutated = run_cli(
                project.runtime,
                "verify",
                "--plan",
                str(plan_path),
                "--all",
                "--json",
                cwd=project.root,
            )
            self.assertNotEqual(0, mutated.returncode)
            self.assertIn("declared planning artifacts changed during verification", mutated.stdout)


def write_planning_chain_bundle(project: ChainProject, run_id: str) -> pathlib.Path:
    bundle = project.root / ".ezpowers" / "staging" / run_id
    bundle.mkdir(parents=True, exist_ok=True)
    spec = {
        "schema_version": 1,
        "design_context": {
            "required": False,
            "reason": "The planning chain fixture has no user interface.",
        },
        "criteria": [
            {
                "id": criterion_id,
                "requirement_id": f"R-{criterion_id}",
                "claim": f"Deliverable {criterion_id} passes its project-owned byte check.",
                "verify_type": "integration",
                "integration": True,
            }
            for criterion_id in ("AC-1", "AC-2")
        ],
    }
    check_id = "artifact-oracle"
    plan = {
        "schema_version": 3,
        "spec": f"docs/specs/{run_id}.md",
        "inputs": [{"id": "source", "path": "inputs/source.xlsx"}],
        "deliverables": [
            {
                "id": "workbook",
                "paths": ["deliverables/workbook.xlsx"],
                "criteria": ["AC-1"],
                "input_ids": ["source"],
                "review": {"mode": "direct", "checks": []},
            },
            {
                "id": "brief",
                "paths": ["deliverables/brief.md"],
                "criteria": ["AC-2"],
                "input_ids": ["source"],
                "review": {"mode": "direct", "checks": []},
            },
        ],
        "checks": {
            check_id: {
                "argv": [sys.executable, "checks/planning_oracle.py"],
                "cwd": ".",
                "timeout_seconds": 30,
                "kind": "integration",
                "concurrency": {"safe": False, "resource_locks": []},
            }
        },
        "tasks": [
            {
                "id": "T1",
                "depends_on": [],
                "criteria": ["AC-1", "AC-2"],
                "checks": [check_id],
            }
        ],
    }
    oracle = (
        "from pathlib import Path\n"
        "workbook = Path('deliverables/workbook.xlsx').read_bytes()\n"
        "brief = Path('deliverables/brief.md').read_bytes()\n"
        "assert workbook.startswith(b'PK') and len(workbook) > 3\n"
        "assert brief.startswith(b'#') and len(brief) > 1\n"
        "print('planning deliverables inspected')\n"
    )
    (bundle / "spec.md").write_text(managed_block("spec", spec), encoding="utf-8")
    (bundle / "plan.md").write_text(managed_block("plan", plan), encoding="utf-8")
    (bundle / "planning_oracle.py").write_text(oracle, encoding="utf-8")
    manifest = {
        "schema_version": 2,
        "project_profile": "planning",
        "run_id": run_id,
        "request": "Produce a workbook and planning brief from the frozen source.",
        "host": "claude",
        "stage_selection": {
            "deep_interview": {"selected": False, "reason": "The request is settled."},
            "frontend_design": {"selected": False, "reason": "There is no UI."},
            "design_architecture": {"selected": False, "reason": "No boundary changes."},
        },
        "risk_classes": [],
        "files": [
            {"role": "spec", "source": "spec.md", "target": f"docs/specs/{run_id}.md"},
            {"role": "plan", "source": "plan.md", "target": f"docs/plans/{run_id}.md"},
            {"role": "oracle", "source": "planning_oracle.py", "target": "checks/planning_oracle.py"},
        ],
        "oracles": [
            {
                "id": "planning-oracle",
                "criteria": ["AC-1", "AC-2"],
                "checks": [check_id],
                "boundary": "declared deliverable bytes",
                "artifact_paths": ["checks/planning_oracle.py"],
                "baseline": "fail",
                "positive_case": "both declared deliverables have inspectable content",
                "negative_case": "a missing or malformed deliverable fails the command",
            }
        ],
    }
    (bundle / "bundle.json").write_text(
        json.dumps(manifest, indent=2) + "\n",
        encoding="utf-8",
    )
    return bundle


def complete_artifact_gate(
    project: ChainProject,
    verdicts: dict[str, str],
) -> None:
    begin = project.command(
        "chain",
        "gate",
        "begin",
        "--kind",
        "artifact-review",
        "--json",
    )
    project.assert_success(begin)
    value = json.loads(begin.stdout)
    challenge = value["challenge_id"]
    reviewer_id = f"artifact-review-{challenge[:8]}"
    start = project.command(
        "chain",
        "hook",
        "--host",
        "claude",
        input_value={
            "hook_event_name": "SubagentStart",
            "session_id": "claude-session",
            "agent_id": reviewer_id,
            "agent_type": "general-purpose",
            "cwd": str(project.root),
        },
    )
    project.assert_success(start)
    marker = {
        "schema_version": 2,
        "challenge_id": challenge,
        "deliverables": [
            {
                "id": item["id"],
                "verdict": verdicts[item["id"]],
                "blocking_findings": (
                    []
                    if verdicts[item["id"]] == "PASS"
                    else ["The deliverable needs product rework."]
                ),
                "observations": ["Reviewed every bound source for this deliverable."],
                "reviewed_sources": [source["id"] for source in item["review_sources"]],
            }
            for item in value["deliverables"]
        ],
    }
    message = (
        "<!-- ezpowers:gate:start -->\n```json\n"
        + json.dumps(marker)
        + "\n```\n<!-- ezpowers:gate:end -->"
    )
    stop = project.command(
        "chain",
        "hook",
        "--host",
        "claude",
        input_value={
            "hook_event_name": "SubagentStop",
            "session_id": "claude-session",
            "agent_id": reviewer_id,
            "agent_type": "general-purpose",
            "cwd": str(project.root),
            "last_assistant_message": message,
            "stop_hook_active": False,
        },
    )
    project.assert_success(stop)


class PlanningProfileChainTests(unittest.TestCase):
    def test_chain_freezes_binary_inputs_and_requires_per_deliverable_rework_and_review(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = pathlib.Path(temp_dir)
            project = ChainProject(root)
            installed = run_cli(
                EZPOWERS,
                "install",
                "--project-root",
                str(root),
                "--project-profile",
                "planning",
                cwd=REPO_ROOT,
            )
            project.assert_success(installed)
            (root / ".gitignore").write_text(
                "__pycache__/\n*.py[cod]\ndeliverables/\n.ezpowers/evidence/\n.ezpowers/staging/\n.ezpowers/backups/\n",
                encoding="utf-8",
            )
            input_path = root / "inputs" / "source.xlsx"
            input_path.parent.mkdir(parents=True)
            input_path.write_bytes(b"PK\x03\x04\x00\xfffrozen-input")
            project.commit_all()
            project.configure()
            bundle = write_planning_chain_bundle(project, "planning-run")
            approved = project.approve_and_activate(bundle)
            self.assertEqual("planning", approved["project_profile"])

            approval = json.loads(
                (root / approved["approval_path"]).read_text(encoding="utf-8")
            )
            self.assertEqual(3, approval["schema_version"])
            self.assertEqual("planning", approval["project_profile"])
            self.assertEqual(
                hashlib.sha256(input_path.read_bytes()).hexdigest(),
                approval["inputs"][0]["sha256"],
            )
            denied = project.command(
                "chain",
                "hook",
                "--host",
                "claude",
                input_value={
                    "hook_event_name": "PreToolUse",
                    "session_id": "claude-session",
                    "tool_name": "Edit",
                    "tool_input": {"file_path": str(input_path)},
                },
            )
            self.assertEqual(
                "deny",
                json.loads(denied.stdout)["hookSpecificOutput"]["permissionDecision"],
            )

            workbook = root / "deliverables" / "workbook.xlsx"
            brief = root / "deliverables" / "brief.md"
            workbook.parent.mkdir(parents=True)
            workbook.write_bytes(b"PK10")
            brief.write_bytes(b"#1")
            plan_path = root / approved["plan_path"]
            verified = project.command(
                "verify",
                "--plan",
                str(plan_path),
                "--all",
                "--json",
            )
            project.assert_success(verified)

            complete_artifact_gate(
                project,
                {"workbook": "FAIL", "brief": "FAIL"},
            )
            unchanged = project.command(
                "verify",
                "--plan",
                str(plan_path),
                "--all",
                "--json",
            )
            self.assertNotEqual(0, unchanged.returncode)
            self.assertIn("workbook", unchanged.stdout)
            self.assertIn("brief", unchanged.stdout)

            workbook.write_bytes(b"PK20")
            partial = project.command(
                "verify",
                "--plan",
                str(plan_path),
                "--all",
                "--json",
            )
            self.assertNotEqual(0, partial.returncode)
            self.assertIn("brief", partial.stdout)

            brief.write_bytes(b"#2")
            reverified = project.command(
                "verify",
                "--plan",
                str(plan_path),
                "--all",
                "--json",
            )
            project.assert_success(reverified)
            complete_artifact_gate(
                project,
                {"workbook": "PASS", "brief": "PASS"},
            )
            certified = project.command(
                "certify",
                "--plan",
                str(plan_path),
                "--json",
            )
            project.assert_success(certified)
            self.assertEqual("PASS", json.loads(certified.stdout)["status"])


if __name__ == "__main__":
    unittest.main()
