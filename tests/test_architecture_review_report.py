import importlib.util
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[1]
RENDERER = REPO_ROOT / "scripts" / "architecture-review-report.py"
ARCHITECTURE_FIXTURE = REPO_ROOT / "tests" / "fixtures" / "architecture_review_project"
WRAPPER = (
    REPO_ROOT
    / "skills"
    / "improve-codebase-architecture"
    / "scripts"
    / "render-report.py"
)
SPEC = importlib.util.spec_from_file_location("architecture_review_report", RENDERER)
assert SPEC is not None and SPEC.loader is not None
REPORT_MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(REPORT_MODULE)


def report_value() -> dict:
    return {
        "schema_version": 2,
        "language": "en",
        "repository": {
            "name": "renderer-fixture",
            "revision": "abc123",
            "dirty": True,
        },
        "scope": "Exercise <script>alert('scope')</script> safely",
        "scope_basis": "user_named",
        "scope_rationale": "The user selected the order-intake product path.",
        "generated_at": "2026-07-24T00:00:00Z",
        "top_recommendation": {
            "candidate_id": "order-intake",
            "rationale": "It concentrates repeated policy behind one test surface.",
        },
        "candidates": [
            {
                "id": "order-intake",
                "title": "Deepen order intake",
                "strength": "strong",
                "files": ["src/order.py", "tests/test_order.py"],
                "evidence": [
                    {
                        "path": "src/order.py",
                        "line": 1,
                        "role": "product",
                        "finding": "Callers repeat validation and retry policy.",
                    },
                    {
                        "path": "tests/test_order.py",
                        "line": 1,
                        "role": "test",
                        "finding": "The test bypasses the product interface.",
                    },
                    {
                        "path": "docs/adr/0001-order-boundary.md",
                        "line": 1,
                        "role": "decision",
                        "finding": "The existing decision predates the repeated policy.",
                    }
                ],
                "problem": "The <script>alert('problem')</script> interface leaks policy.",
                "solution": "Move validation and retry behavior behind one interface.",
                "benefits": ["Callers learn less.", "Tests cross one stable seam."],
                "test_effect": "Existing behavior tests survive internal refactors.",
                "compatibility": "Keep the current intake entry point during migration.",
                "migration": "Move one caller at a time, then remove the pass-through path.",
                "adr": {
                    "status": "revisit",
                    "references": ["docs/adr/0001-order-boundary.md"],
                    "finding": "The existing split is explicit but the repeated policy is new evidence.",
                },
                "before": {
                    "nodes": [
                        {"id": "caller-a", "label": "Caller A", "layer": 0, "kind": "caller"},
                        {"id": "caller-b", "label": "Caller B", "layer": 0, "kind": "caller"},
                        {
                            "id": "thin-module",
                            "label": "Thin module",
                            "layer": 1,
                            "kind": "module",
                            "emphasis": "shallow",
                        },
                    ],
                    "edges": [
                        {
                            "from": "caller-a",
                            "to": "thin-module",
                            "label": "policy leak",
                            "kind": "leak",
                        },
                        {"from": "caller-b", "to": "thin-module"},
                    ],
                },
                "after": {
                    "nodes": [
                        {"id": "caller", "label": "Callers", "layer": 0, "kind": "caller"},
                        {
                            "id": "deep-module",
                            "label": "Order intake",
                            "layer": 1,
                            "kind": "module",
                            "emphasis": "deep",
                        },
                        {"id": "gateway", "label": "Gateway", "layer": 2, "kind": "adapter"},
                    ],
                    "edges": [
                        {"from": "caller", "to": "deep-module", "label": "simple input"},
                        {"from": "deep-module", "to": "gateway", "kind": "seam"},
                    ],
                },
            }
        ],
    }


class ArchitectureReviewReportTests(unittest.TestCase):
    def run_renderer(
        self,
        project_root: Path,
        input_path: Path,
        *extra: str,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(WRAPPER),
                "--project-root",
                str(project_root),
                "--input",
                str(input_path),
                "--json",
                *extra,
            ],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

    def fixture(self, root: Path, value: dict | None = None) -> tuple[Path, Path]:
        project = root / "project"
        (project / "src").mkdir(parents=True)
        (project / "tests").mkdir()
        (project / "docs" / "adr").mkdir(parents=True)
        (project / "src" / "order.py").write_text("def intake():\n    return 1\n", encoding="utf-8")
        (project / "tests" / "test_order.py").write_text("assert True\n", encoding="utf-8")
        (project / "docs" / "adr" / "0001-order-boundary.md").write_text(
            "# Order boundary\n",
            encoding="utf-8",
        )
        input_path = root / "report.json"
        input_path.write_text(
            json.dumps(value or report_value(), ensure_ascii=False),
            encoding="utf-8",
        )
        return project, input_path

    def test_valid_input_renders_deterministic_offline_escaped_html(self) -> None:
        with tempfile.TemporaryDirectory() as temp_name:
            root = Path(temp_name)
            project, input_path = self.fixture(root)
            first = self.run_renderer(project, input_path)
            second = self.run_renderer(project, input_path)
            self.assertEqual(first.returncode, 0, first.stderr + first.stdout)
            self.assertEqual(second.returncode, 0, second.stderr + second.stdout)
            first_value = json.loads(first.stdout)
            second_value = json.loads(second.stdout)
            self.assertEqual(first_value["status"], "PASS")
            self.assertEqual(first_value["schema_version"], 2)
            self.assertEqual(first_value["candidate_count"], 1)
            self.assertFalse(first_value["opened"])
            self.assertEqual(first_value["report_sha256"], second_value["report_sha256"])
            self.assertEqual(first_value["input_sha256"], second_value["input_sha256"])
            self.assertEqual(first_value["source_sha256"], second_value["source_sha256"])
            for payload in (first_value, second_value):
                output = Path(payload["report_path"])
                self.assertTrue(output.is_file())
                self.assertFalse(output.is_relative_to(project))
                html = output.read_text(encoding="utf-8")
                self.assertIn("Content-Security-Policy", html)
                self.assertIn("&lt;script&gt;", html)
                self.assertNotIn("<script>", html)
                self.assertNotIn("https://", html)
                self.assertIn("Top recommendation", html)
                self.assertIn("Why this candidate", html)
                self.assertIn("Compatibility", html)
                self.assertIn("Migration", html)
                self.assertIn("ADR context", html)
                self.assertIn("edge-leak", html)
                self.assertIn("emphasis-deep", html)
                self.assertIn("<svg", html)
                output.unlink()

    def test_invalid_paths_edges_and_output_location_fail_without_output(self) -> None:
        scenarios = []
        unsafe = report_value()
        unsafe["candidates"][0]["files"][0] = "../outside.py"
        scenarios.append(("unsafe path", unsafe))
        dangling = report_value()
        dangling["candidates"][0]["before"]["edges"][0]["to"] = "missing-node"
        scenarios.append(("dangling endpoint", dangling))
        unknown = report_value()
        unknown["candidates"][0]["surprise"] = True
        scenarios.append(("unknown fields", unknown))

        for expected, value in scenarios:
            with self.subTest(expected=expected), tempfile.TemporaryDirectory() as temp_name:
                root = Path(temp_name)
                project, input_path = self.fixture(root, value)
                result = self.run_renderer(project, input_path)
                self.assertEqual(result.returncode, 2, result.stderr + result.stdout)
                payload = json.loads(result.stdout)
                self.assertEqual(payload["status"], "ERROR")
                self.assertIn(expected, payload["error"])

        with tempfile.TemporaryDirectory() as temp_name:
            root = Path(temp_name)
            project, input_path = self.fixture(root)
            inside = project / "report.html"
            result = self.run_renderer(project, input_path, "--output", str(inside))
            self.assertEqual(result.returncode, 2, result.stderr + result.stdout)
            self.assertIn("outside the project root", json.loads(result.stdout)["error"])
            self.assertFalse(inside.exists())

    def test_evidence_lines_and_candidate_files_are_bound(self) -> None:
        scenarios = []
        missing_line = report_value()
        del missing_line["candidates"][0]["evidence"][0]["line"]
        scenarios.append(("is missing fields: line", missing_line))
        out_of_range = report_value()
        out_of_range["candidates"][0]["evidence"][0]["line"] = 99
        scenarios.append(("exceeds the file length", out_of_range))
        unlisted = report_value()
        unlisted["candidates"][0]["files"] = ["tests/test_order.py"]
        scenarios.append(("must cover every candidate file", unlisted))

        for expected, value in scenarios:
            with self.subTest(expected=expected), tempfile.TemporaryDirectory() as temp_name:
                root = Path(temp_name)
                project, input_path = self.fixture(root, value)
                result = self.run_renderer(project, input_path)
                self.assertEqual(result.returncode, 2, result.stderr + result.stdout)
                self.assertIn(expected, json.loads(result.stdout)["error"])

    def test_source_fingerprint_changes_with_evidence_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_name:
            root = Path(temp_name)
            project, input_path = self.fixture(root)
            first = self.run_renderer(project, input_path)
            self.assertEqual(first.returncode, 0, first.stderr + first.stdout)
            first_value = json.loads(first.stdout)
            Path(first_value["report_path"]).unlink()

            (project / "src" / "order.py").write_text(
                "def intake():\n    return 2\n",
                encoding="utf-8",
            )
            second = self.run_renderer(project, input_path)
            self.assertEqual(second.returncode, 0, second.stderr + second.stdout)
            second_value = json.loads(second.stdout)
            Path(second_value["report_path"]).unlink()

            self.assertNotEqual(
                first_value["source_sha256"],
                second_value["source_sha256"],
            )

    def test_input_fingerprint_binds_bytes_used_for_rendering(self) -> None:
        with tempfile.TemporaryDirectory() as temp_name:
            root = Path(temp_name)
            project, input_path = self.fixture(root)
            original_bytes = input_path.read_bytes()
            expected_sha256 = hashlib.sha256(original_bytes).hexdigest()
            original_atomic_write = REPORT_MODULE._atomic_write

            def mutate_input_then_write(output: Path, content: str) -> None:
                changed = report_value()
                changed["scope"] = "concurrently changed scope"
                input_path.write_text(json.dumps(changed), encoding="utf-8")
                original_atomic_write(output, content)

            with mock.patch.object(
                REPORT_MODULE,
                "_atomic_write",
                side_effect=mutate_input_then_write,
            ):
                receipt = REPORT_MODULE.render(
                    project_root=project,
                    input_path=input_path,
                    output=str(root / "bound-input.html"),
                    open_report=False,
                )

            self.assertEqual(receipt["input_sha256"], expected_sha256)
            self.assertNotEqual(
                receipt["input_sha256"],
                hashlib.sha256(input_path.read_bytes()).hexdigest(),
            )

    def test_representative_fixture_excludes_out_of_scope_source(self) -> None:
        with tempfile.TemporaryDirectory() as temp_name:
            root = Path(temp_name)
            project = root / "project"
            shutil.copytree(ARCHITECTURE_FIXTURE, project)
            value = report_value()
            value["repository"]["name"] = "architecture-review-project"
            value["scope"] = "Order intake boundary named in AGENTS.md"
            value["scope_rationale"] = "AGENTS.md names the exact Order intake files."
            candidate = value["candidates"][0]
            candidate["files"] = [
                "src/http_checkout.py",
                "src/batch_checkout.py",
                "src/order_rules.py",
                "tests/test_checkout.py",
            ]
            candidate["evidence"] = [
                {
                    "path": "src/http_checkout.py",
                    "line": 6,
                    "role": "product",
                    "finding": "HTTP owns the repeated intake sequence.",
                },
                {
                    "path": "src/batch_checkout.py",
                    "line": 6,
                    "role": "product",
                    "finding": "Batch owns the same intake sequence.",
                },
                {
                    "path": "src/order_rules.py",
                    "line": 1,
                    "role": "product",
                    "finding": "The rules module exposes the required ordering.",
                },
                {
                    "path": "tests/test_checkout.py",
                    "line": 31,
                    "role": "test",
                    "finding": "The shared scenario protects both public entry points.",
                },
                {
                    "path": "AGENTS.md",
                    "line": 7,
                    "role": "context",
                    "finding": "Repository guidance freezes the scan boundary.",
                },
                {
                    "path": "CONTEXT.md",
                    "line": 3,
                    "role": "context",
                    "finding": "Domain context defines the complete responsibility.",
                },
                {
                    "path": "docs/adr/0001-order-entrypoints.md",
                    "line": 3,
                    "role": "decision",
                    "finding": "Both entry points are compatibility boundaries.",
                },
            ]
            candidate["adr"] = {
                "status": "aligned",
                "references": ["docs/adr/0001-order-entrypoints.md"],
                "finding": "Internal convergence preserves both public entry points.",
            }
            input_path = root / "representative-report.json"
            input_path.write_text(json.dumps(value), encoding="utf-8")

            first = self.run_renderer(project, input_path)
            self.assertEqual(first.returncode, 0, first.stderr + first.stdout)
            first_value = json.loads(first.stdout)
            self.assertEqual(first_value["source_file_count"], 7)
            Path(first_value["report_path"]).unlink()

            (project / "src" / "health.py").write_text(
                'def health_status():\n    return {"status": "changed"}\n',
                encoding="utf-8",
            )
            second = self.run_renderer(project, input_path)
            self.assertEqual(second.returncode, 0, second.stderr + second.stdout)
            second_value = json.loads(second.stdout)
            Path(second_value["report_path"]).unlink()

            self.assertEqual(
                first_value["source_sha256"],
                second_value["source_sha256"],
            )

    def test_wrapper_resolves_installed_renderer_from_nested_workdir(self) -> None:
        with tempfile.TemporaryDirectory() as temp_name:
            root = Path(temp_name)
            project, input_path = self.fixture(root)
            installed = (
                project
                / ".ezpowers"
                / "tools"
                / "architecture-review-report.py"
            )
            installed.parent.mkdir(parents=True)
            shutil.copy2(RENDERER, installed)
            nested = project / "src" / "nested"
            nested.mkdir()

            result = subprocess.run(
                [
                    sys.executable,
                    str(WRAPPER),
                    "--project-root",
                    str(project),
                    "--input",
                    str(input_path),
                    "--json",
                ],
                cwd=nested,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["schema_version"], 2)
            Path(payload["report_path"]).unlink()

    def test_existing_output_is_never_overwritten(self) -> None:
        with tempfile.TemporaryDirectory() as temp_name:
            root = Path(temp_name)
            project, input_path = self.fixture(root)
            output = root / "existing.html"
            output.write_text("user-owned", encoding="utf-8")
            result = self.run_renderer(project, input_path, "--output", str(output))
            self.assertEqual(result.returncode, 2, result.stderr + result.stdout)
            self.assertEqual(output.read_text(encoding="utf-8"), "user-owned")

    def test_output_race_is_rejected_without_overwriting_the_winner(self) -> None:
        with tempfile.TemporaryDirectory() as temp_name:
            root = Path(temp_name)
            project, input_path = self.fixture(root)
            output = root / "raced.html"
            original_render = REPORT_MODULE.render_html

            def create_raced_output(report: dict) -> str:
                output.write_text("race-winner", encoding="utf-8")
                return original_render(report)

            with mock.patch.object(
                REPORT_MODULE,
                "render_html",
                side_effect=create_raced_output,
            ):
                with self.assertRaisesRegex(
                    REPORT_MODULE.ReportError,
                    "output already exists",
                ):
                    REPORT_MODULE.render(
                        project_root=project,
                        input_path=input_path,
                        output=str(output),
                        open_report=False,
                    )
            self.assertEqual(output.read_text(encoding="utf-8"), "race-winner")


if __name__ == "__main__":
    unittest.main()
