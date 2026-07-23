import hashlib
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
EZPOWERS = REPO_ROOT / "scripts" / "ezpowers.py"


def _write_fake_host_commands(
    directory: pathlib.Path,
    versions: dict[str, str],
) -> None:
    for host, version in versions.items():
        if os.name == "nt":
            (directory / f"{host}.cmd").write_text(
                f"@echo {host}-cli {version}\n",
                encoding="utf-8",
            )
        else:
            command = directory / host
            command.write_text(
                f"#!/bin/sh\nprintf '{host}-cli {version}\\n'\n",
                encoding="utf-8",
            )
            command.chmod(0o755)


def run_cli(
    script: pathlib.Path,
    *args: str,
    cwd: pathlib.Path,
    host_versions: dict[str, str] | None = None,
) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)
    versions = host_versions or {"claude": "2.1.217", "codex": "0.145.0"}
    with tempfile.TemporaryDirectory(prefix="ezpowers-test-hosts-") as host_dir:
        host_root = pathlib.Path(host_dir)
        _write_fake_host_commands(host_root, versions)
        env["PATH"] = str(host_root) + os.pathsep + env.get("PATH", "")
        return subprocess.run(
            [sys.executable, str(script), *args],
            cwd=cwd,
            text=True,
            capture_output=True,
            env=env,
            timeout=30,
            check=False,
        )


def managed_block(kind: str, payload: dict) -> str:
    return textwrap.dedent(
        f"""
        # Demo {kind.title()}

        <!-- ezpowers:{kind}:start -->
        ```json
        {json.dumps(payload, indent=2)}
        ```
        <!-- ezpowers:{kind}:end -->
        """
    ).strip() + "\n"


class RuntimeProject:
    def __init__(self, root: pathlib.Path) -> None:
        self.root = root
        subprocess.run(["git", "init", "-q"], cwd=root, check=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root, check=True)
        subprocess.run(["git", "config", "user.name", "EZPowers Test"], cwd=root, check=True)
        subprocess.run(["git", "config", "core.autocrlf", "false"], cwd=root, check=True)

    @property
    def runtime(self) -> pathlib.Path:
        return self.root / ".ezpowers" / "ezpowers.py"

    def install(self, *extra: str) -> subprocess.CompletedProcess:
        return run_cli(EZPOWERS, "install", "--project-root", str(self.root), *extra, cwd=REPO_ROOT)

    def write_flow(
        self,
        checks: list[dict],
        *,
        integration: bool = False,
        slug: str = "demo",
    ) -> pathlib.Path:
        spec_path = self.root / "docs" / "specs" / f"{slug}.md"
        plan_path = self.root / "docs" / "plans" / f"{slug}.md"
        spec_path.parent.mkdir(parents=True, exist_ok=True)
        plan_path.parent.mkdir(parents=True, exist_ok=True)
        spec = {
            "schema_version": 1,
            "criteria": [
                {
                    "id": "AC-1",
                    "requirement_id": "R1",
                    "claim": "The project-local verification command produces an observable result.",
                    "verify_type": "cli",
                    "integration": integration,
                }
            ],
        }
        plan = {
            "schema_version": 1,
            "spec": f"docs/specs/{slug}.md",
            "tasks": [{"id": "T1", "criteria": ["AC-1"], "checks": checks}],
        }
        spec_path.write_text(managed_block("spec", spec), encoding="utf-8")
        plan_path.write_text(managed_block("plan", plan), encoding="utf-8")
        return plan_path

    def commit_all(self) -> None:
        subprocess.run(["git", "add", "-A"], cwd=self.root, check=True)
        subprocess.run(["git", "commit", "-qm", "fixture"], cwd=self.root, check=True)


class EZPowersInstallTests(unittest.TestCase):
    def test_install_requires_the_git_worktree_root_before_writing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            plain = pathlib.Path(temp_dir) / "plain"
            plain.mkdir()
            proc = run_cli(
                EZPOWERS,
                "install",
                "--project-root",
                str(plain),
                cwd=REPO_ROOT,
            )
            self.assertNotEqual(proc.returncode, 0, proc.stderr + proc.stdout)
            self.assertIn("git", (proc.stdout + proc.stderr).lower())
            self.assertFalse((plain / ".ezpowers").exists())

        with tempfile.TemporaryDirectory() as temp_dir:
            root = pathlib.Path(temp_dir)
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            child = root / "child"
            child.mkdir()
            proc = run_cli(
                EZPOWERS,
                "install",
                "--project-root",
                str(child),
                cwd=REPO_ROOT,
            )
            self.assertNotEqual(proc.returncode, 0, proc.stderr + proc.stdout)
            self.assertIn("root", (proc.stdout + proc.stderr).lower())
            self.assertFalse((child / ".ezpowers").exists())

    def test_install_is_self_contained_for_both_hosts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = RuntimeProject(pathlib.Path(temp_dir))
            proc = project.install()
            self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)

            expected = {
                "setup",
                "deep-interview",
                "design-architecture",
                "spec",
                "prepare-execute",
                "execute",
                "frontend-design",
                "wiki",
                "harness-chain",
            }
            for name in expected:
                canonical = project.root / ".ezpowers" / "kit" / "skills" / name / "SKILL.md"
                claude = project.root / ".claude" / "skills" / name / "SKILL.md"
                codex = project.root / ".agents" / "skills" / name / "SKILL.md"
                self.assertTrue(canonical.is_file(), canonical)
                self.assertEqual(canonical.read_bytes(), claude.read_bytes())
                self.assertEqual(canonical.read_bytes(), codex.read_bytes())

            self.assertFalse((project.root / ".claude" / "skills" / "hud").exists())
            self.assertTrue((project.root / ".ezpowers" / "ledger.json").is_file())
            self.assertFalse((project.root / ".claude" / "settings.json").exists())
            self.assertFalse((project.root / ".codex" / "hooks.json").exists())

            isolated = run_cli(project.runtime, "--help", cwd=project.root)
            self.assertEqual(isolated.returncode, 0, isolated.stderr)
            self.assertNotIn("ModuleNotFoundError", isolated.stderr)

    def test_installed_runtime_survives_removal_of_the_plugin_distribution(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = pathlib.Path(temp_dir)
            distribution = temp_root / "distribution"
            project_root = temp_root / "project"
            distribution.mkdir()
            project_root.mkdir()

            manifest_path = REPO_ROOT / "project-kit" / "v5.2.0" / "manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            sources = {
                "project-kit/v5.2.0/manifest.json",
                manifest["runtime"]["source"],
                *(item["source"] for item in manifest.get("tools", [])),
                *(item["source"] for item in manifest.get("contracts", [])),
            }
            for skill in manifest["skills"]:
                sources.update(item["source"] for item in skill["files"])
            for relative_name in sources:
                source = REPO_ROOT / relative_name
                target = distribution / relative_name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)

            project = RuntimeProject(project_root)
            copied_runtime = distribution / manifest["runtime"]["source"]
            install = run_cli(
                copied_runtime,
                "install",
                "--project-root",
                str(project.root),
                cwd=distribution,
            )
            self.assertEqual(install.returncode, 0, install.stderr + install.stdout)

            shutil.rmtree(distribution)
            status = run_cli(project.runtime, "status", "--json", cwd=project.root)
            self.assertEqual(status.returncode, 0, status.stderr + status.stdout)
            self.assertEqual(json.loads(status.stdout)["status"], "UNCONFIGURED")
            plan = project.write_flow(
                [
                    {
                        "id": "self-contained",
                        "argv": [
                            sys.executable,
                            "-c",
                            "from pathlib import Path; assert Path('.ezpowers/config.json').is_file()",
                        ],
                        "cwd": ".",
                        "timeout_seconds": 10,
                        "kind": "test",
                    }
                ]
            )
            validate = run_cli(
                project.runtime,
                "validate",
                "--plan",
                str(plan),
                "--json",
                cwd=project.root,
            )
            self.assertEqual(validate.returncode, 0, validate.stderr + validate.stdout)
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
            self.assertEqual(verify.returncode, 0, verify.stderr + verify.stdout)
            certify = run_cli(
                project.runtime,
                "certify",
                "--plan",
                str(plan),
                "--json",
                cwd=project.root,
            )
            self.assertEqual(certify.returncode, 0, certify.stderr + certify.stdout)
            status = run_cli(project.runtime, "status", "--json", cwd=project.root)
            self.assertEqual(status.returncode, 0, status.stderr + status.stdout)
            self.assertEqual(json.loads(status.stdout)["status"], "CERTIFIED")

    def test_changed_plugin_distribution_requires_explicit_refresh(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = RuntimeProject(pathlib.Path(temp_dir))
            self.assertEqual(project.install().returncode, 0)
            ledger_path = project.root / ".ezpowers" / "ledger.json"
            ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
            ledger["version"] = "4.9.9"
            ledger_path.write_text(
                json.dumps(ledger, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )

            refused = project.install()
            self.assertNotEqual(refused.returncode, 0, refused.stderr + refused.stdout)
            self.assertIn("--refresh", refused.stderr + refused.stdout)
            refreshed = project.install("--refresh")
            self.assertEqual(refreshed.returncode, 0, refreshed.stderr + refreshed.stdout)
            repaired = json.loads(ledger_path.read_text(encoding="utf-8"))
            self.assertEqual(repaired["version"], "5.2.0")

    def test_opt_in_hooks_use_native_nested_shape_and_work_from_a_subdirectory(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = pathlib.Path(temp_dir) / "project with spaces"
            project_root.mkdir()
            project = RuntimeProject(project_root)
            proc = project.install("--enable-hooks", "both")
            self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)

            claude = json.loads(
                (project.root / ".claude" / "settings.json").read_text(encoding="utf-8")
            )["hooks"]["Stop"][0]
            codex = json.loads(
                (project.root / ".codex" / "hooks.json").read_text(encoding="utf-8")
            )["hooks"]["Stop"][0]
            self.assertEqual(set(claude), {"hooks", "matcher"})
            self.assertEqual(set(codex), {"hooks"})
            self.assertEqual(claude["matcher"], "")
            for host, entry, expected in (
                ("claude", claude, {}),
                ("codex", codex, {}),
            ):
                self.assertEqual(len(entry["hooks"]), 1)
                hook = entry["hooks"][0]
                self.assertEqual(hook["type"], "command")
                if host == "claude":
                    self.assertEqual(
                        set(hook), {"type", "command", "args", "timeout"}
                    )
                    self.assertEqual(hook["command"], sys.executable)
                    self.assertEqual(
                        hook["args"],
                        [str(project.runtime.resolve()), "hook", "--host", "claude"],
                    )
                    command = [hook["command"], *hook["args"]]
                    use_shell = False
                else:
                    self.assertEqual(
                        set(hook),
                        {"type", "command", "commandWindows", "timeout"},
                    )
                    self.assertIn(str(project.runtime.resolve()), hook["commandWindows"])
                    command = hook["commandWindows"] if os.name == "nt" else hook["command"]
                    use_shell = True
                subdir = project.root / "nested" / host
                subdir.mkdir(parents=True)
                result = subprocess.run(
                    command,
                    cwd=subdir,
                    input='{"hook_event_name":"Stop"}',
                    text=True,
                    capture_output=True,
                    shell=use_shell,
                    timeout=30,
                    check=False,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(json.loads(result.stdout), expected)

    def test_hook_install_rejects_an_outdated_host_before_writing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = RuntimeProject(pathlib.Path(temp_dir))
            proc = run_cli(
                EZPOWERS,
                "install",
                "--project-root",
                str(project.root),
                "--enable-hooks",
                "both",
                cwd=REPO_ROOT,
                host_versions={"claude": "2.1.217", "codex": "0.144.9"},
            )

            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("0.145.0", proc.stdout + proc.stderr)
            self.assertFalse((project.root / ".ezpowers").exists())
            self.assertFalse((project.root / ".claude").exists())
            self.assertFalse((project.root / ".codex").exists())

    def test_refresh_preserves_modified_managed_file_and_reports_conflict(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = RuntimeProject(pathlib.Path(temp_dir))
            self.assertEqual(project.install().returncode, 0)
            target = project.root / ".claude" / "skills" / "spec" / "SKILL.md"
            target.write_text(target.read_text(encoding="utf-8") + "\nuser-owned change\n", encoding="utf-8")

            proc = run_cli(
                project.runtime,
                "install",
                "--project-root",
                str(project.root),
                "--refresh",
                cwd=project.root,
            )
            self.assertNotEqual(proc.returncode, 0, proc.stderr + proc.stdout)
            self.assertIn("user-owned change", target.read_text(encoding="utf-8"))
            self.assertIn("conflict", (proc.stdout + proc.stderr).lower())

    def test_existing_install_detects_managed_copy_drift_without_refresh(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = RuntimeProject(pathlib.Path(temp_dir))
            self.assertEqual(project.install().returncode, 0)
            target = project.root / ".agents" / "skills" / "spec" / "SKILL.md"
            target.write_text(
                target.read_text(encoding="utf-8") + "\nlocal drift\n",
                encoding="utf-8",
            )

            proc = project.install()

            self.assertNotEqual(proc.returncode, 0, proc.stderr + proc.stdout)
            self.assertIn("conflict", (proc.stdout + proc.stderr).lower())
            self.assertIn("local drift", target.read_text(encoding="utf-8"))

    def test_installed_refresh_rejects_a_modified_local_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = RuntimeProject(pathlib.Path(temp_dir))
            self.assertEqual(project.install().returncode, 0)
            manifest = project.root / ".ezpowers" / "kit" / "manifest.json"
            manifest.write_text(
                manifest.read_text(encoding="utf-8") + " ", encoding="utf-8"
            )

            proc = run_cli(
                project.runtime,
                "install",
                "--project-root",
                str(project.root),
                "--refresh",
                cwd=project.root,
            )

            self.assertNotEqual(proc.returncode, 0, proc.stderr + proc.stdout)
            self.assertIn("conflict", (proc.stdout + proc.stderr).lower())

    def test_install_and_unconfigured_status_reject_invalid_config(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = RuntimeProject(pathlib.Path(temp_dir))
            config_path = project.root / ".ezpowers" / "config.json"
            config_path.parent.mkdir(parents=True)
            config_path.write_text(
                json.dumps(
                    {
                        "schema_version": 999,
                        "project_name": "invalid",
                        "checks": {},
                        "required_checks": ["missing"],
                    }
                ),
                encoding="utf-8",
            )
            install = project.install()
            self.assertNotEqual(install.returncode, 0, install.stderr + install.stdout)
            self.assertIn("schema_version", install.stderr + install.stdout)

        with tempfile.TemporaryDirectory() as temp_dir:
            project = RuntimeProject(pathlib.Path(temp_dir))
            self.assertEqual(project.install().returncode, 0)
            config_path = project.root / ".ezpowers" / "config.json"
            config = json.loads(config_path.read_text(encoding="utf-8"))
            config["required_checks"] = ["missing"]
            config_path.write_text(json.dumps(config), encoding="utf-8")
            status = run_cli(project.runtime, "status", "--json", cwd=project.root)
            self.assertNotEqual(status.returncode, 0, status.stderr + status.stdout)
            self.assertIn("unknown check", " ".join(json.loads(status.stdout)["reasons"]))

    def test_unconfigured_status_rejects_managed_kit_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = RuntimeProject(pathlib.Path(temp_dir))
            self.assertEqual(project.install().returncode, 0)
            target = project.root / ".agents" / "skills" / "spec" / "SKILL.md"
            target.write_text(
                target.read_text(encoding="utf-8") + "\nmanaged drift\n",
                encoding="utf-8",
            )
            status = run_cli(project.runtime, "status", "--json", cwd=project.root)
            self.assertNotEqual(status.returncode, 0, status.stderr + status.stdout)
            self.assertIn("managed file", " ".join(json.loads(status.stdout)["reasons"]))

    def test_pre_v5_harness_config_is_ignored_and_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = RuntimeProject(pathlib.Path(temp_dir))
            legacy = project.root / ".harness" / "config.json"
            legacy.parent.mkdir()
            legacy.write_text(
                json.dumps(
                    {
                        "project": "legacy-demo",
                        "test": {"command": f'"{sys.executable}" -c "assert 2 + 2 == 4"'},
                        "executor": {"model": "example", "max_retries": 9},
                        "harness": {"root": "C:/external/harness"},
                    }
                ),
                encoding="utf-8",
            )
            legacy_before = legacy.read_bytes()

            proc = project.install()
            self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
            config = json.loads((project.root / ".ezpowers" / "config.json").read_text(encoding="utf-8"))
            self.assertEqual(config["project_name"], project.root.name)
            self.assertEqual(config["checks"], {})
            self.assertEqual(config["required_checks"], [])
            self.assertEqual(legacy.read_bytes(), legacy_before)
            ledger = json.loads(
                (project.root / ".ezpowers" / "ledger.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertNotIn("migration_warnings", ledger)
            self.assertNotIn("legacy", (proc.stdout + proc.stderr).lower())


class EZPowersVerificationTests(unittest.TestCase):
    def passing_check(self) -> dict:
        return {
            "id": "pass",
            "argv": [
                sys.executable,
                "-c",
                "from pathlib import Path; assert Path('.ezpowers/config.json').is_file()",
            ],
            "cwd": ".",
            "timeout_seconds": 10,
            "kind": "test",
        }

    def test_validate_verify_certify_status_and_staleness(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = RuntimeProject(pathlib.Path(temp_dir))
            self.assertEqual(project.install().returncode, 0)
            plan = project.write_flow([self.passing_check()])
            source = project.root / "source.txt"
            source.write_text("one\n", encoding="utf-8")
            project.commit_all()

            validate = run_cli(project.runtime, "validate", "--plan", str(plan), cwd=project.root)
            self.assertEqual(validate.returncode, 0, validate.stderr + validate.stdout)
            verify = run_cli(project.runtime, "verify", "--plan", str(plan), "--all", "--json", cwd=project.root)
            self.assertEqual(verify.returncode, 0, verify.stderr + verify.stdout)
            result = json.loads(verify.stdout)
            self.assertEqual(result["status"], "PASS")
            check = result["tasks"][0]["checks"][0]
            self.assertEqual(check["exit_code"], 0)
            self.assertFalse(check["timed_out"])
            self.assertTrue((project.root / check["stdout_log"]).is_file())
            self.assertEqual(
                hashlib.sha256((project.root / check["stdout_log"]).read_bytes()).hexdigest(),
                check["stdout_sha256"],
            )

            certify = run_cli(project.runtime, "certify", "--plan", str(plan), "--json", cwd=project.root)
            self.assertEqual(certify.returncode, 0, certify.stderr + certify.stdout)
            self.assertEqual(json.loads(certify.stdout)["status"], "PASS")

            status = run_cli(project.runtime, "status", "--json", cwd=project.root)
            self.assertEqual(status.returncode, 0, status.stderr)
            self.assertTrue(json.loads(status.stdout)["fresh"])

            source.write_text("two\n", encoding="utf-8")
            stale = run_cli(project.runtime, "certify", "--plan", str(plan), "--json", cwd=project.root)
            self.assertNotEqual(stale.returncode, 0)
            self.assertEqual(json.loads(stale.stdout)["status"], "FAIL")
            self.assertIn("workspace", " ".join(json.loads(stale.stdout)["reasons"]).lower())

    def test_plan_validation_is_read_only_until_explicit_activation(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = RuntimeProject(pathlib.Path(temp_dir))
            self.assertEqual(project.install().returncode, 0)
            first = project.write_flow([self.passing_check()], slug="first")
            project.commit_all()
            self.assertEqual(
                run_cli(
                    project.runtime,
                    "verify",
                    "--plan",
                    str(first),
                    "--all",
                    "--json",
                    cwd=project.root,
                ).returncode,
                0,
            )
            self.assertEqual(
                run_cli(
                    project.runtime,
                    "certify",
                    "--plan",
                    str(first),
                    "--json",
                    cwd=project.root,
                ).returncode,
                0,
            )
            state_path = project.root / ".ezpowers" / "state.json"
            original_state = state_path.read_bytes()
            evidence_dirs = sorted(
                path.name
                for path in (project.root / ".ezpowers" / "evidence").iterdir()
                if path.is_dir()
            )

            same = run_cli(
                project.runtime,
                "validate",
                "--plan",
                str(first),
                "--json",
                cwd=project.root,
            )
            self.assertEqual(same.returncode, 0, same.stderr + same.stdout)
            self.assertEqual(state_path.read_bytes(), original_state)
            self.assertEqual(
                json.loads(same.stdout)["activation"],
                {"requested": False, "applied": False, "changed": False},
            )

            second = project.write_flow([self.passing_check()], slug="second")
            before_candidate = state_path.read_bytes()
            candidate = run_cli(
                project.runtime,
                "validate",
                "--plan",
                str(second),
                "--json",
                cwd=project.root,
            )
            self.assertEqual(candidate.returncode, 0, candidate.stderr + candidate.stdout)
            self.assertEqual(state_path.read_bytes(), before_candidate)

            invalid_bytes = second.read_bytes()
            second.write_text("not a managed plan\n", encoding="utf-8")
            invalid = run_cli(
                project.runtime,
                "validate",
                "--plan",
                str(second),
                "--activate",
                "--json",
                cwd=project.root,
            )
            self.assertNotEqual(invalid.returncode, 0)
            self.assertEqual(state_path.read_bytes(), before_candidate)
            second.write_bytes(invalid_bytes)

            activated = run_cli(
                project.runtime,
                "validate",
                "--plan",
                str(second),
                "--activate",
                "--json",
                cwd=project.root,
            )
            self.assertEqual(activated.returncode, 0, activated.stderr + activated.stdout)
            self.assertEqual(
                json.loads(activated.stdout)["activation"],
                {"requested": True, "applied": True, "changed": True},
            )
            state = json.loads(state_path.read_text(encoding="utf-8"))
            self.assertEqual(state["active_plan"], "docs/plans/second.md")
            self.assertEqual(state["latest_evidence"], {"all": None, "tasks": {}})
            self.assertIsNone(state["latest_certificate"])
            self.assertEqual(
                sorted(
                    path.name
                    for path in (project.root / ".ezpowers" / "evidence").iterdir()
                    if path.is_dir()
                ),
                evidence_dirs,
            )

            active_state = state_path.read_bytes()
            reactivated = run_cli(
                project.runtime,
                "validate",
                "--plan",
                str(second),
                "--activate",
                "--json",
                cwd=project.root,
            )
            self.assertEqual(reactivated.returncode, 0, reactivated.stderr + reactivated.stdout)
            self.assertEqual(state_path.read_bytes(), active_state)
            self.assertFalse(json.loads(reactivated.stdout)["activation"]["changed"])

            wrong_plan_certify = run_cli(
                project.runtime,
                "certify",
                "--plan",
                str(first),
                "--json",
                cwd=project.root,
            )
            self.assertNotEqual(wrong_plan_certify.returncode, 0)
            self.assertIn("not active", wrong_plan_certify.stdout)
            self.assertEqual(state_path.read_bytes(), active_state)

            third = project.write_flow([self.passing_check()], slug="third")
            unknown_task = run_cli(
                project.runtime,
                "verify",
                "--plan",
                str(third),
                "--task",
                "UNKNOWN",
                "--json",
                cwd=project.root,
            )
            self.assertNotEqual(unknown_task.returncode, 0)
            self.assertIn("unknown task", unknown_task.stdout)
            self.assertEqual(state_path.read_bytes(), active_state)

            spec_activation = run_cli(
                project.runtime,
                "validate",
                "--spec",
                str(project.root / "docs" / "specs" / "second.md"),
                "--activate",
                "--json",
                cwd=project.root,
            )
            self.assertNotEqual(spec_activation.returncode, 0)
            self.assertIn("requires --plan", spec_activation.stdout)
            self.assertEqual(state_path.read_bytes(), active_state)

    def test_status_revalidates_task_evidence_without_promoting_completion(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = RuntimeProject(pathlib.Path(temp_dir))
            self.assertEqual(project.install().returncode, 0)
            plan = project.write_flow([self.passing_check()])
            source = project.root / "source.txt"
            source.write_text("one\n", encoding="utf-8")
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
            self.assertEqual(activate.returncode, 0, activate.stderr + activate.stdout)
            initial = json.loads(
                run_cli(project.runtime, "status", "--json", cwd=project.root).stdout
            )
            self.assertEqual(initial["task_evidence"]["T1"]["status"], "MISSING")

            task_verify = run_cli(
                project.runtime,
                "verify",
                "--plan",
                str(plan),
                "--task",
                "T1",
                "--json",
                cwd=project.root,
            )
            self.assertEqual(task_verify.returncode, 0, task_verify.stderr + task_verify.stdout)
            task_status = json.loads(
                run_cli(project.runtime, "status", "--json", cwd=project.root).stdout
            )
            self.assertEqual(task_status["status"], "STALE")
            self.assertFalse(task_status["fresh"])
            self.assertEqual(
                task_status["task_evidence"]["T1"]["status"], "FRESH_PASS"
            )

            self.assertEqual(
                run_cli(
                    project.runtime,
                    "verify",
                    "--plan",
                    str(plan),
                    "--all",
                    "--json",
                    cwd=project.root,
                ).returncode,
                0,
            )
            self.assertEqual(
                run_cli(
                    project.runtime,
                    "certify",
                    "--plan",
                    str(plan),
                    "--json",
                    cwd=project.root,
                ).returncode,
                0,
            )
            state_path = project.root / ".ezpowers" / "state.json"
            state = json.loads(state_path.read_text(encoding="utf-8"))
            valid_task_pointer = dict(state["latest_evidence"]["tasks"]["T1"])
            state["latest_evidence"]["tasks"]["OLD"] = dict(
                valid_task_pointer
            )
            state["latest_evidence"]["tasks"]["T1"] = dict(
                state["latest_evidence"]["all"]
            )
            state_path.write_text(
                json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            certified = json.loads(
                run_cli(project.runtime, "status", "--json", cwd=project.root).stdout
            )
            self.assertEqual(certified["status"], "CERTIFIED")
            self.assertEqual(certified["task_evidence"]["T1"]["status"], "STALE")
            self.assertIn(
                "scope",
                " ".join(certified["task_evidence"]["T1"]["reasons"]).lower(),
            )
            self.assertEqual(
                certified["orphan_task_evidence"]["OLD"]["status"], "ORPHAN"
            )

            state["latest_evidence"]["tasks"]["T1"] = valid_task_pointer
            state_path.write_text(
                json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            source.write_text("two\n", encoding="utf-8")
            stale = json.loads(
                run_cli(project.runtime, "status", "--json", cwd=project.root).stdout
            )
            self.assertEqual(stale["task_evidence"]["T1"]["status"], "STALE")
            self.assertIn(
                "workspace",
                " ".join(stale["task_evidence"]["T1"]["reasons"]).lower(),
            )

    def test_status_rejects_malformed_task_pointer_container(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = RuntimeProject(pathlib.Path(temp_dir))
            self.assertEqual(project.install().returncode, 0)
            state_path = project.root / ".ezpowers" / "state.json"
            state = json.loads(state_path.read_text(encoding="utf-8"))
            state["latest_evidence"]["tasks"] = []
            state_path.write_text(
                json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )

            status = run_cli(project.runtime, "status", "--json", cwd=project.root)

            self.assertNotEqual(status.returncode, 0)
            self.assertIn("latest_evidence.tasks", status.stdout)

    def test_plan_config_and_untracked_changes_each_invalidate_certification(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = RuntimeProject(pathlib.Path(temp_dir))
            self.assertEqual(project.install().returncode, 0)
            plan = project.write_flow([self.passing_check()])
            project.commit_all()
            self.assertEqual(
                run_cli(project.runtime, "verify", "--plan", str(plan), "--all", "--json", cwd=project.root).returncode,
                0,
            )
            self.assertEqual(
                run_cli(project.runtime, "certify", "--plan", str(plan), "--json", cwd=project.root).returncode,
                0,
            )

            config_path = project.root / ".ezpowers" / "config.json"
            config_bytes = config_path.read_bytes()
            plan_bytes = plan.read_bytes()
            mutations = (
                (config_path, config_bytes + b" ", "config"),
                (plan, plan_bytes + b" ", "plan"),
            )
            for path, changed, expected_reason in mutations:
                path.write_bytes(changed)
                stale = run_cli(
                    project.runtime,
                    "certify",
                    "--plan",
                    str(plan),
                    "--json",
                    cwd=project.root,
                )
                self.assertNotEqual(stale.returncode, 0)
                self.assertIn(
                    expected_reason,
                    " ".join(json.loads(stale.stdout)["reasons"]).lower(),
                )
                path.write_bytes(config_bytes if path == config_path else plan_bytes)

            untracked = project.root / "untracked-change.txt"
            untracked.write_text("new\n", encoding="utf-8")
            stale = run_cli(
                project.runtime,
                "certify",
                "--plan",
                str(plan),
                "--json",
                cwd=project.root,
            )
            self.assertNotEqual(stale.returncode, 0)
            self.assertIn("workspace", " ".join(json.loads(stale.stdout)["reasons"]).lower())

    def test_ignored_spec_change_invalidates_certification(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = RuntimeProject(pathlib.Path(temp_dir))
            self.assertEqual(project.install().returncode, 0)
            plan = project.write_flow([self.passing_check()])
            spec_path = project.root / "docs" / "specs" / "demo.md"
            (project.root / ".gitignore").write_text(
                "docs/specs/demo.md\n", encoding="utf-8"
            )
            project.commit_all()
            self.assertEqual(
                run_cli(
                    project.runtime,
                    "verify",
                    "--plan",
                    str(plan),
                    "--all",
                    "--json",
                    cwd=project.root,
                ).returncode,
                0,
            )
            self.assertEqual(
                run_cli(
                    project.runtime,
                    "certify",
                    "--plan",
                    str(plan),
                    "--json",
                    cwd=project.root,
                ).returncode,
                0,
            )

            spec_path.write_text(
                spec_path.read_text(encoding="utf-8") + "\nignored edit\n",
                encoding="utf-8",
            )
            status = run_cli(project.runtime, "status", "--json", cwd=project.root)
            payload = json.loads(status.stdout)
            self.assertEqual(payload["status"], "STALE")
            self.assertIn("spec", " ".join(payload["reasons"]).lower())

    def test_refresh_invalidates_evidence_even_when_the_kit_is_gitignored(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = RuntimeProject(pathlib.Path(temp_dir))
            self.assertEqual(project.install().returncode, 0)
            plan = project.write_flow([self.passing_check()])
            (project.root / ".gitignore").write_text(
                ".ezpowers/\n.claude/skills/\n.agents/skills/\n",
                encoding="utf-8",
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
            self.assertEqual(verify.returncode, 0, verify.stderr + verify.stdout)
            installation = json.loads(verify.stdout)["installation"]
            self.assertEqual(
                set(installation),
                {"version", "manifest_sha256", "ledger_sha256", "runtime_sha256"},
            )
            self.assertEqual(
                run_cli(
                    project.runtime,
                    "certify",
                    "--plan",
                    str(plan),
                    "--json",
                    cwd=project.root,
                ).returncode,
                0,
            )

            refresh = run_cli(
                project.runtime,
                "install",
                "--project-root",
                str(project.root),
                "--refresh",
                cwd=project.root,
            )
            self.assertEqual(refresh.returncode, 0, refresh.stderr + refresh.stdout)
            status = run_cli(project.runtime, "status", "--json", cwd=project.root)
            payload = json.loads(status.stdout)
            self.assertEqual(payload["status"], "STALE")
            self.assertIn("installed kit", " ".join(payload["reasons"]).lower())

    def test_failure_timeout_and_placeholder_are_fail_closed(self) -> None:
        cases = [
            (
                "exit",
                [{"id": "fail", "argv": [sys.executable, "-c", "raise SystemExit(7)"], "cwd": ".", "timeout_seconds": 5, "kind": "test"}],
                "verify",
            ),
            (
                "timeout",
                [{"id": "slow", "argv": [sys.executable, "-c", "import time; time.sleep(3)"], "cwd": ".", "timeout_seconds": 1, "kind": "test"}],
                "verify",
            ),
            (
                "spawn",
                [{"id": "missing", "argv": ["ezpowers-command-that-does-not-exist-9f12"], "cwd": ".", "timeout_seconds": 5, "kind": "test"}],
                "verify",
            ),
            (
                "placeholder",
                [{"id": "noop", "argv": ["echo", "ok"], "cwd": ".", "timeout_seconds": 5, "kind": "test"}],
                "validate",
            ),
            (
                "print-only",
                [
                    {
                        "id": "print-only",
                        "argv": [sys.executable, "-c", "print('synthetic pass')"],
                        "cwd": ".",
                        "timeout_seconds": 5,
                        "kind": "test",
                    }
                ],
                "validate",
            ),
        ]
        for label, checks, command in cases:
            with self.subTest(label=label), tempfile.TemporaryDirectory() as temp_dir:
                project = RuntimeProject(pathlib.Path(temp_dir))
                self.assertEqual(project.install().returncode, 0)
                plan = project.write_flow(checks)
                project.commit_all()
                args = [command, "--plan", str(plan)]
                if command == "verify":
                    args.extend(["--all", "--json"])
                proc = run_cli(project.runtime, *args, cwd=project.root)
                self.assertNotEqual(proc.returncode, 0, proc.stderr + proc.stdout)

    def test_path_traversal_and_integration_without_integration_check_fail_validation(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = RuntimeProject(pathlib.Path(temp_dir))
            self.assertEqual(project.install().returncode, 0)
            check = self.passing_check()
            check["cwd"] = "../outside"
            plan = project.write_flow([check], integration=True)
            proc = run_cli(project.runtime, "validate", "--plan", str(plan), "--json", cwd=project.root)
            self.assertNotEqual(proc.returncode, 0)
            errors = " ".join(json.loads(proc.stdout)["errors"]).lower()
            self.assertIn("cwd", errors)
            self.assertIn("integration", errors)

    def test_managed_paths_must_be_project_relative_but_cli_paths_may_be_absolute(self) -> None:
        for label, cwd in (
            ("native-absolute", None),
            ("posix-absolute", "/absolute/path"),
        ):
            with self.subTest(label=label), tempfile.TemporaryDirectory() as temp_dir:
                project = RuntimeProject(pathlib.Path(temp_dir))
                self.assertEqual(project.install().returncode, 0)
                check = self.passing_check()
                check["cwd"] = str(project.root.resolve()) if cwd is None else cwd
                plan = project.write_flow([check])
                proc = run_cli(
                    project.runtime,
                    "validate",
                    "--plan",
                    str(plan.resolve()),
                    "--json",
                    cwd=project.root,
                )
                self.assertNotEqual(proc.returncode, 0, proc.stderr + proc.stdout)
                self.assertIn(
                    "project-relative",
                    " ".join(json.loads(proc.stdout)["errors"]).lower(),
                )

        with tempfile.TemporaryDirectory() as temp_dir:
            project = RuntimeProject(pathlib.Path(temp_dir))
            self.assertEqual(project.install().returncode, 0)
            plan = project.write_flow([self.passing_check()])
            spec_path = (project.root / "docs" / "specs" / "demo.md").resolve()
            text = plan.read_text(encoding="utf-8")
            plan.write_text(
                text.replace('"docs/specs/demo.md"', json.dumps(str(spec_path))),
                encoding="utf-8",
            )
            proc = run_cli(
                project.runtime,
                "validate",
                "--plan",
                str(plan.resolve()),
                "--json",
                cwd=project.root,
            )
            self.assertNotEqual(proc.returncode, 0, proc.stderr + proc.stdout)
            self.assertIn(
                "project-relative spec",
                " ".join(json.loads(proc.stdout)["errors"]).lower(),
            )

    def test_shell_control_operators_fail_validation(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = RuntimeProject(pathlib.Path(temp_dir))
            self.assertEqual(project.install().returncode, 0)
            plan = project.write_flow(
                [
                    {
                        "id": "shell-chain",
                        "argv": [
                            "powershell",
                            "-NoProfile",
                            "-Command",
                            "Write-Output verified; exit 0",
                        ],
                        "cwd": ".",
                        "timeout_seconds": 5,
                        "kind": "test",
                    }
                ]
            )

            proc = run_cli(
                project.runtime,
                "validate",
                "--plan",
                str(plan),
                "--json",
                cwd=project.root,
            )

            self.assertNotEqual(proc.returncode, 0, proc.stderr + proc.stdout)
            self.assertIn("shell control", " ".join(json.loads(proc.stdout)["errors"]).lower())

    def test_opaque_shell_command_forms_fail_validation(self) -> None:
        opaque_argv = (
            ["powershell", "-EncodedCommand", "VwByAGkAdABlAC0ATwB1AHQAcAB1AHQA"],
            ["powershell", "-EncodedArguments", "VwByAGkAdABlAC0ATwB1AHQAcAB1AHQA"],
            ["pwsh", "-CommandWithArgs", "Write-Output", "verified"],
            ["cmd.exe", "/K", "echo", "verified"],
        )
        for argv in opaque_argv:
            with self.subTest(argv=argv), tempfile.TemporaryDirectory() as temp_dir:
                project = RuntimeProject(pathlib.Path(temp_dir))
                self.assertEqual(project.install().returncode, 0)
                plan = project.write_flow(
                    [
                        {
                            "id": "opaque-shell",
                            "argv": argv,
                            "cwd": ".",
                            "timeout_seconds": 5,
                            "kind": "test",
                        }
                    ]
                )

                proc = run_cli(
                    project.runtime,
                    "validate",
                    "--plan",
                    str(plan),
                    "--json",
                    cwd=project.root,
                )

                self.assertNotEqual(proc.returncode, 0, proc.stderr + proc.stdout)
                self.assertIn(
                    "opaque shell",
                    " ".join(json.loads(proc.stdout)["errors"]).lower(),
                )

    def test_literal_pipe_argument_for_direct_process_is_allowed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = RuntimeProject(pathlib.Path(temp_dir))
            self.assertEqual(project.install().returncode, 0)
            plan = project.write_flow(
                [
                    {
                        "id": "literal-pipe",
                        "argv": [
                            sys.executable,
                            "-c",
                            "import sys; assert sys.argv[1] == '|'",
                            "|",
                        ],
                        "cwd": ".",
                        "timeout_seconds": 5,
                        "kind": "test",
                    }
                ]
            )

            proc = run_cli(
                project.runtime,
                "validate",
                "--plan",
                str(plan),
                "--json",
                cwd=project.root,
            )

            self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)

    def test_evidence_tampering_is_detected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = RuntimeProject(pathlib.Path(temp_dir))
            self.assertEqual(project.install().returncode, 0)
            plan = project.write_flow([self.passing_check()])
            project.commit_all()
            verify = run_cli(project.runtime, "verify", "--plan", str(plan), "--all", "--json", cwd=project.root)
            result = json.loads(verify.stdout)
            evidence = project.root / result["evidence_path"]
            evidence.write_text(evidence.read_text(encoding="utf-8") + " ", encoding="utf-8")

            proc = run_cli(project.runtime, "certify", "--plan", str(plan), "--json", cwd=project.root)
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("tamper", " ".join(json.loads(proc.stdout)["reasons"]).lower())

    def test_coherently_rehashed_evidence_cannot_redirect_its_own_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = RuntimeProject(pathlib.Path(temp_dir))
            self.assertEqual(project.install().returncode, 0)
            plan = project.write_flow([self.passing_check()])
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
            result = json.loads(verify.stdout)
            evidence = project.root / result["evidence_path"]
            payload = json.loads(evidence.read_text(encoding="utf-8"))
            payload["evidence_path"] = ".ezpowers/config.json"
            rewritten = (
                json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
            ).encode("utf-8")
            evidence.write_bytes(rewritten)
            digest = hashlib.sha256(rewritten).hexdigest()
            evidence.with_name("result.json.sha256").write_text(
                digest + "\n", encoding="ascii"
            )
            state_path = project.root / ".ezpowers" / "state.json"
            state = json.loads(state_path.read_text(encoding="utf-8"))
            state["latest_evidence"]["all"]["sha256"] = digest
            state_path.write_text(
                json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )

            proc = run_cli(
                project.runtime,
                "certify",
                "--plan",
                str(plan),
                "--json",
                cwd=project.root,
            )
            self.assertNotEqual(proc.returncode, 0, proc.stderr + proc.stdout)
            self.assertIn("self path", " ".join(json.loads(proc.stdout)["reasons"]).lower())
            self.assertFalse((project.root / ".ezpowers" / "certificate.json").exists())

    def test_coherently_rehashed_pass_evidence_must_preserve_recorded_invariants(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = RuntimeProject(pathlib.Path(temp_dir))
            self.assertEqual(project.install().returncode, 0)
            plan = project.write_flow([self.passing_check()])
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
            result = json.loads(verify.stdout)
            evidence = project.root / result["evidence_path"]
            payload = json.loads(evidence.read_text(encoding="utf-8"))
            payload["reasons"] = ["fabricated"]
            payload["workspace_before"] = {}
            payload["installation_before"] = {}
            check = payload["tasks"][0]["checks"][0]
            check["spawn_error"] = "fabricated"
            check["stderr_log"] = check["stdout_log"]
            check["stderr_sha256"] = check["stdout_sha256"]
            rewritten = (
                json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
            ).encode("utf-8")
            evidence.write_bytes(rewritten)
            digest = hashlib.sha256(rewritten).hexdigest()
            evidence.with_name("result.json.sha256").write_text(
                digest + "\n", encoding="ascii"
            )
            state_path = project.root / ".ezpowers" / "state.json"
            state = json.loads(state_path.read_text(encoding="utf-8"))
            state["latest_evidence"]["all"]["sha256"] = digest
            state_path.write_text(
                json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )

            proc = run_cli(
                project.runtime,
                "certify",
                "--plan",
                str(plan),
                "--json",
                cwd=project.root,
            )

            self.assertNotEqual(proc.returncode, 0, proc.stderr + proc.stdout)
            reasons = " ".join(json.loads(proc.stdout)["reasons"]).lower()
            self.assertIn("failure reasons", reasons)
            self.assertIn("workspace changed during recorded verification", reasons)
            self.assertIn("installed kit changed during recorded verification", reasons)
            self.assertIn("not a recorded pass", reasons)
            self.assertIn("duplicate log path", reasons)

    def test_status_rejects_a_noncanonical_certificate_pointer(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = RuntimeProject(pathlib.Path(temp_dir))
            self.assertEqual(project.install().returncode, 0)
            plan = project.write_flow([self.passing_check()])
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
            self.assertEqual(verify.returncode, 0, verify.stderr + verify.stdout)
            certify = run_cli(
                project.runtime,
                "certify",
                "--plan",
                str(plan),
                "--json",
                cwd=project.root,
            )
            self.assertEqual(certify.returncode, 0, certify.stderr + certify.stdout)
            state_path = project.root / ".ezpowers" / "state.json"
            state = json.loads(state_path.read_text(encoding="utf-8"))
            state["latest_certificate"]["path"] = json.loads(verify.stdout)[
                "evidence_path"
            ]
            state_path.write_text(
                json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )

            status = run_cli(project.runtime, "status", "--json", cwd=project.root)

            self.assertEqual(status.returncode, 0, status.stderr + status.stdout)
            payload = json.loads(status.stdout)
            self.assertEqual(payload["status"], "READY")
            self.assertFalse(payload["certified"])
            self.assertIn(
                "certificate pointer is invalid",
                " ".join(payload["reasons"]).lower(),
            )

    def test_state_writers_fail_cleanly_when_the_runtime_lock_is_held(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = RuntimeProject(pathlib.Path(temp_dir))
            self.assertEqual(project.install().returncode, 0)
            plan = project.write_flow([self.passing_check()])
            holder_code = textwrap.dedent(
                """
                import pathlib
                import runpy
                import sys
                import time

                runtime = runpy.run_path(sys.argv[1])
                with runtime["_runtime_lock"](pathlib.Path(sys.argv[2]), timeout_seconds=10):
                    print("locked", flush=True)
                    time.sleep(20)
                """
            )
            holder = subprocess.Popen(
                [sys.executable, "-c", holder_code, str(project.runtime), str(project.root)],
                cwd=project.root,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            try:
                self.assertIsNotNone(holder.stdout)
                self.assertEqual(holder.stdout.readline().strip(), "locked")
                commands = (
                    ("validate", "--plan", str(plan), "--activate", "--json"),
                    ("verify", "--plan", str(plan), "--all", "--json"),
                    ("certify", "--plan", str(plan), "--json"),
                    (
                        "install",
                        "--project-root",
                        str(project.root),
                        "--refresh",
                    ),
                )
                for command in commands:
                    with self.subTest(command=command[0]):
                        blocked = run_cli(project.runtime, *command, cwd=project.root)
                        self.assertNotEqual(
                            blocked.returncode,
                            0,
                            blocked.stderr + blocked.stdout,
                        )
                        self.assertIn(
                            "runtime is busy",
                            (blocked.stderr + blocked.stdout).lower(),
                        )
            finally:
                holder.terminate()
                try:
                    holder.communicate(timeout=10)
                except subprocess.TimeoutExpired:
                    holder.kill()
                    holder.communicate(timeout=10)

    def test_coherently_rehashed_evidence_cannot_omit_a_declared_check(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = RuntimeProject(pathlib.Path(temp_dir))
            self.assertEqual(project.install().returncode, 0)
            plan = project.write_flow([self.passing_check()])
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
            result = json.loads(verify.stdout)
            evidence = project.root / result["evidence_path"]
            payload = json.loads(evidence.read_text(encoding="utf-8"))
            payload["tasks"][0]["checks"] = []
            rewritten = (
                json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
            ).encode("utf-8")
            evidence.write_bytes(rewritten)
            digest = hashlib.sha256(rewritten).hexdigest()
            evidence.with_name("result.json.sha256").write_text(
                digest + "\n", encoding="ascii"
            )
            state_path = project.root / ".ezpowers" / "state.json"
            state = json.loads(state_path.read_text(encoding="utf-8"))
            state["latest_evidence"]["all"]["sha256"] = digest
            state_path.write_text(
                json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )

            proc = run_cli(
                project.runtime,
                "certify",
                "--plan",
                str(plan),
                "--json",
                cwd=project.root,
            )

            self.assertNotEqual(proc.returncode, 0, proc.stderr + proc.stdout)
            self.assertIn(
                "inventory",
                " ".join(json.loads(proc.stdout)["reasons"]).lower(),
            )

    def test_claude_and_codex_hooks_share_the_same_core_verdict(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = RuntimeProject(pathlib.Path(temp_dir))
            self.assertEqual(project.install().returncode, 0)
            plan = project.write_flow([self.passing_check()])
            source = project.root / "source.txt"
            source.write_text("one\n", encoding="utf-8")
            project.commit_all()
            self.assertEqual(
                run_cli(project.runtime, "verify", "--plan", str(plan), "--all", "--json", cwd=project.root).returncode,
                0,
            )

            def hook(host: str) -> dict:
                proc = subprocess.run(
                    [sys.executable, str(project.runtime), "hook", "--host", host],
                    cwd=project.root,
                    input='{"hook_event_name":"Stop"}',
                    text=True,
                    capture_output=True,
                    check=False,
                )
                self.assertEqual(proc.returncode, 0, proc.stderr)
                return json.loads(proc.stdout)

            verify_only_claude = hook("claude")
            verify_only_codex = hook("codex")
            self.assertEqual(verify_only_claude["decision"], "block")
            self.assertEqual(verify_only_codex["decision"], "block")
            self.assertEqual(
                verify_only_claude["reason"], verify_only_codex["reason"]
            )
            self.assertIn("not certified", verify_only_claude["reason"])

            self.assertEqual(
                run_cli(project.runtime, "certify", "--plan", str(plan), "--json", cwd=project.root).returncode,
                0,
            )
            self.assertEqual(hook("claude"), {})
            self.assertEqual(hook("codex"), {})

            source.write_text("changed\n", encoding="utf-8")
            claude_json = hook("claude")
            codex_json = hook("codex")
            self.assertEqual(claude_json["decision"], "block")
            self.assertEqual(codex_json["decision"], "block")
            self.assertEqual(claude_json["reason"], codex_json["reason"])


if __name__ == "__main__":
    unittest.main()
