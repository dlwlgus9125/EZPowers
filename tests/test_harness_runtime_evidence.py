import json
import pathlib
import subprocess
import sys
import tempfile
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]


class HarnessRuntimeEvidenceTests(unittest.TestCase):
    def make_project(
        self,
        root: pathlib.Path,
        *,
        artifact_kind: str,
        runtime_probe: dict,
        reviewer_verdict: str = "PASS",
        server_config: dict | None = None,
        app_delivery: dict | None = None,
        ui_verification: dict | None = None,
        expected_observation: str = "desktop UI shows server API data",
    ) -> pathlib.Path:
        phase = "sample"
        phase_dir = root / "phases" / phase
        phase_dir.mkdir(parents=True)
        (root / ".harness").mkdir(exist_ok=True)

        config = {
            "smoke": {
                "required": True,
                "artifact_kind": artifact_kind,
                "command": f'"{sys.executable}" -c "print(\'smoke\')"',
                "screenshot_path": ".harness/artifacts/gui-smoke.png",
                "min_pixel_variance": 12.0,
            },
            "wiring": {
                "enabled": True,
                "exempt_reason": "",
                "view_extensions": [],
            },
        }
        if server_config is not None:
            config["server"] = server_config
        if app_delivery is not None:
            config["app_delivery"] = app_delivery
        if ui_verification is not None:
            config["ui_verification"] = ui_verification
        (root / ".harness" / "config.json").write_text(
            json.dumps(config),
            encoding="utf-8",
        )

        gate = {
            "phase": phase,
            "required": True,
            "verify_type": "e2e",
            "commands": ["if (1 -eq 1) { Write-Output gate } else { exit 1 }"],
            "covered_tasks": ["T1", "T2"],
            "covered_edges": ["T1->T2"],
            "expected_observation": expected_observation,
            "status": "pending",
            "reviewer_verdict": reviewer_verdict,
            "attempts": [],
        }
        (phase_dir / "wiring-gate.json").write_text(
            json.dumps(gate),
            encoding="utf-8",
        )
        (phase_dir / "runtime-probe.json").write_text(
            json.dumps(runtime_probe),
            encoding="utf-8",
        )
        return phase_dir

    def run_gate(self, root: pathlib.Path) -> tuple[subprocess.CompletedProcess, dict]:
        proc = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(REPO_ROOT / "scripts" / "harness-gate.ps1"),
                "-ProjectRoot",
                str(root),
                "-Phase",
                "sample",
                "-TimeoutSeconds",
                "30",
            ],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
            timeout=60,
        )
        gate = json.loads(
            (root / "phases" / "sample" / "wiring-gate.json").read_text(
                encoding="utf-8-sig",
            ),
        )
        return proc, gate

    def bind_reviewer_verdict(self, root: pathlib.Path, verdict: str = "PASS") -> None:
        gate_path = root / "phases" / "sample" / "wiring-gate.json"
        gate = json.loads(gate_path.read_text(encoding="utf-8-sig"))
        gate["verdict_fingerprint"] = gate["evidence_fingerprint"]
        gate["reviewer_verdict"] = verdict
        gate_path.write_text(json.dumps(gate), encoding="utf-8")

    def completed_probe(
        self,
        desktop_evidence: dict | None = None,
        client_server_evidence: dict | None = None,
    ) -> dict:
        probe = {
            "status": "completed",
            "step": 0,
            "command": "smoke",
            "exit_code": 0,
            "timed_out": False,
            "stdout_tail": "",
            "stderr_tail": "",
            "timestamp": "2026-05-28T00:00:00Z",
        }
        if desktop_evidence is not None:
            probe["desktop_evidence"] = desktop_evidence
        if client_server_evidence is not None:
            probe["client_server_evidence"] = client_server_evidence
        return probe

    def test_desktop_runtime_probe_without_desktop_evidence_fails_even_with_reviewer_pass(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = pathlib.Path(temp_dir)
            self.make_project(
                root,
                artifact_kind="desktop",
                runtime_probe=self.completed_probe(),
                reviewer_verdict="PASS",
            )

            proc, gate = self.run_gate(root)

            self.assertNotEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            self.assertEqual(gate["status"], "test_gap")
            self.assertEqual(gate["evidence_status"], "runtime_gap")
            self.assertIn("desktop evidence", gate["message"])

    def test_desktop_runtime_probe_with_screenshot_ui_and_api_evidence_passes(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = pathlib.Path(temp_dir)
            screenshot = root / ".harness" / "artifacts" / "gui-smoke.png"
            screenshot.parent.mkdir(parents=True)
            screenshot.write_bytes(b"fake screenshot bytes")
            self.make_project(
                root,
                artifact_kind="desktop",
                runtime_probe=self.completed_probe(
                    {
                        "window_found": True,
                        "screenshot_path": ".harness/artifacts/gui-smoke.png",
                        "pixel_variance": 18.5,
                        "ui_text": "Dashboard loaded",
                        "automation_names": ["DashboardWindow"],
                        "api_observation": "GET /api/dashboard returned 200",
                    },
                ),
                reviewer_verdict="PASS",
                server_config={"health_check_url": "http://localhost:3000/health"},
            )

            # An unbound pre-injected verdict is not honored; the reviewer must
            # bind their verdict to the evidence fingerprint the gate records.
            first_proc, first_gate = self.run_gate(root)
            self.assertEqual(first_proc.returncode, 5, first_proc.stdout + first_proc.stderr)
            self.assertEqual(first_gate["status"], "review_pending")

            self.bind_reviewer_verdict(root)
            proc, gate = self.run_gate(root)

            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            self.assertEqual(gate["status"], "pass")
            self.assertIn("runtime-probe.json", gate["runtime_artifacts"])
            self.assertIn(".harness/artifacts/gui-smoke.png", gate["runtime_artifacts"])

    def test_cli_and_server_runtime_probe_success_are_not_desktop_gated(self):
        for artifact_kind in ("cli", "server"):
            with self.subTest(artifact_kind=artifact_kind):
                with tempfile.TemporaryDirectory() as temp_dir:
                    root = pathlib.Path(temp_dir)
                    self.make_project(
                        root,
                        artifact_kind=artifact_kind,
                        runtime_probe=self.completed_probe(),
                        reviewer_verdict="PASS",
                        expected_observation=f"{artifact_kind} entry point starts",
                    )

                    first_proc, first_gate = self.run_gate(root)
                    self.assertEqual(first_proc.returncode, 5, first_proc.stdout + first_proc.stderr)
                    self.assertEqual(first_gate["status"], "review_pending")

                    self.bind_reviewer_verdict(root)
                    proc, gate = self.run_gate(root)

                    self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
                    self.assertEqual(gate["status"], "pass")

    def test_desktop_server_wiring_requires_api_observation(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = pathlib.Path(temp_dir)
            screenshot = root / ".harness" / "artifacts" / "gui-smoke.png"
            screenshot.parent.mkdir(parents=True)
            screenshot.write_bytes(b"fake screenshot bytes")
            self.make_project(
                root,
                artifact_kind="desktop",
                runtime_probe=self.completed_probe(
                    {
                        "window_found": True,
                        "screenshot_path": ".harness/artifacts/gui-smoke.png",
                        "pixel_variance": 18.5,
                        "ui_text": "Dashboard loaded from local fixture",
                    },
                ),
                reviewer_verdict="PASS",
                server_config={"health_check_url": "http://localhost:3000/health"},
            )

            proc, gate = self.run_gate(root)

            self.assertNotEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            self.assertEqual(gate["status"], "test_gap")
            self.assertIn("API observation", gate["message"])

    def test_web_client_server_wiring_requires_api_observation_even_with_reviewer_pass(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = pathlib.Path(temp_dir)
            self.make_project(
                root,
                artifact_kind="web",
                runtime_probe=self.completed_probe(),
                reviewer_verdict="PASS",
                server_config={"health_check_url": "http://localhost:3000/health"},
                app_delivery={
                    "surface_kind": "web",
                    "frontend": {"present": True},
                    "backend": {"present": True},
                },
                ui_verification={"required": True, "capability": "browser-e2e"},
                expected_observation="web client renders data from an API endpoint",
            )

            proc, gate = self.run_gate(root)

            self.assertNotEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            self.assertEqual(gate["status"], "test_gap")
            self.assertEqual(gate["evidence_status"], "runtime_gap")
            self.assertIn("client-server evidence", gate["message"])
            self.assertIn("API observation", gate["message"])

    def test_web_client_server_wiring_accepts_client_server_evidence(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = pathlib.Path(temp_dir)
            self.make_project(
                root,
                artifact_kind="web",
                runtime_probe=self.completed_probe(
                    client_server_evidence={
                        "api_observation": "GET /api/dashboard returned 200 and rendered Dashboard",
                        "endpoint": "/api/dashboard",
                        "status_code": 200,
                    },
                ),
                reviewer_verdict="PASS",
                server_config={"health_check_url": "http://localhost:3000/health"},
                app_delivery={
                    "surface_kind": "web",
                    "frontend": {"present": True},
                    "backend": {"present": True},
                },
                ui_verification={"required": True, "capability": "browser-e2e"},
                expected_observation="web client renders data from an API endpoint",
            )

            first_proc, first_gate = self.run_gate(root)
            self.assertEqual(first_proc.returncode, 5, first_proc.stdout + first_proc.stderr)
            self.assertEqual(first_gate["status"], "review_pending")

            self.bind_reviewer_verdict(root)
            proc, gate = self.run_gate(root)

            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            self.assertEqual(gate["status"], "pass")
            self.assertIn("runtime-probe.json", gate["runtime_artifacts"])


if __name__ == "__main__":
    unittest.main()
