import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[1]
RENDERER = REPO_ROOT / "scripts" / "architecture-review-report.py"
SPEC = importlib.util.spec_from_file_location("architecture_review_report", RENDERER)
assert SPEC is not None and SPEC.loader is not None
REPORT_MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(REPORT_MODULE)


def report_value() -> dict:
    return {
        "schema_version": 1,
        "language": "en",
        "repository": {
            "name": "renderer-fixture",
            "revision": "abc123",
            "dirty": True,
        },
        "scope": "Exercise <script>alert('scope')</script> safely",
        "generated_at": "2026-07-24T00:00:00Z",
        "top_recommendation_id": "order-intake",
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
                        "finding": "Callers repeat validation and retry policy.",
                    }
                ],
                "problem": "The <script>alert('problem')</script> interface leaks policy.",
                "solution": "Move validation and retry behavior behind one interface.",
                "benefits": ["Callers learn less.", "Tests cross one stable seam."],
                "test_effect": "Existing behavior tests survive internal refactors.",
                "before": {
                    "nodes": [
                        {"id": "caller-a", "label": "Caller A", "layer": 0, "kind": "caller"},
                        {"id": "caller-b", "label": "Caller B", "layer": 0, "kind": "caller"},
                        {"id": "thin-module", "label": "Thin module", "layer": 1, "kind": "module"},
                    ],
                    "edges": [
                        {"from": "caller-a", "to": "thin-module", "label": "policy"},
                        {"from": "caller-b", "to": "thin-module"},
                    ],
                },
                "after": {
                    "nodes": [
                        {"id": "caller", "label": "Callers", "layer": 0, "kind": "caller"},
                        {"id": "deep-module", "label": "Order intake", "layer": 1, "kind": "module"},
                        {"id": "gateway", "label": "Gateway", "layer": 2, "kind": "adapter"},
                    ],
                    "edges": [
                        {"from": "caller", "to": "deep-module", "label": "simple input"},
                        {"from": "deep-module", "to": "gateway"},
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
                str(RENDERER),
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
        (project / "src" / "order.py").write_text("def intake():\n    return 1\n", encoding="utf-8")
        (project / "tests" / "test_order.py").write_text("assert True\n", encoding="utf-8")
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
            self.assertEqual(first_value["candidate_count"], 1)
            self.assertFalse(first_value["opened"])
            self.assertEqual(first_value["report_sha256"], second_value["report_sha256"])
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
