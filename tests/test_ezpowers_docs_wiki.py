from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys
import tempfile
import textwrap
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
EZPOWERS = REPO_ROOT / "scripts" / "ezpowers.py"


def run_cli(
    script: pathlib.Path,
    *args: str,
    cwd: pathlib.Path,
    input_text: str | None = None,
) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)
    with tempfile.TemporaryDirectory(prefix="ezpowers-test-hosts-") as host_dir:
        host_root = pathlib.Path(host_dir)
        for host, version in (("claude", "2.1.217"), ("codex", "0.145.0")):
            if os.name == "nt":
                (host_root / f"{host}.cmd").write_text(
                    f"@echo {host}-cli {version}\n",
                    encoding="utf-8",
                )
            else:
                command = host_root / host
                command.write_text(
                    f"#!/bin/sh\nprintf '{host}-cli {version}\\n'\n",
                    encoding="utf-8",
                )
                command.chmod(0o755)
        env["PATH"] = str(host_root) + os.pathsep + env.get("PATH", "")
        return subprocess.run(
            [sys.executable, str(script), *args],
            cwd=cwd,
            input=input_text,
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


class Project:
    def __init__(self, root: pathlib.Path) -> None:
        self.root = root
        subprocess.run(["git", "init", "-q"], cwd=root, check=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root, check=True)
        subprocess.run(["git", "config", "user.name", "EZPowers Test"], cwd=root, check=True)
        subprocess.run(["git", "config", "core.autocrlf", "false"], cwd=root, check=True)

    @property
    def runtime(self) -> pathlib.Path:
        return self.root / ".ezpowers" / "ezpowers.py"

    def install(self, *extra: str) -> subprocess.CompletedProcess[str]:
        return run_cli(
            EZPOWERS,
            "install",
            "--project-root",
            str(self.root),
            *extra,
            cwd=REPO_ROOT,
        )

    def commit_all(self) -> None:
        subprocess.run(["git", "add", "-A"], cwd=self.root, check=True)
        subprocess.run(["git", "commit", "-qm", "fixture"], cwd=self.root, check=True)


def generated_markdown(
    title: str,
    *,
    doc_type: str,
    authority: str,
    body: str,
) -> str:
    return textwrap.dedent(
        f"""\
        ---
        doc_type: "{doc_type}"
        authority: "{authority}"
        status: "active"
        generated_by: "ezpowers"
        ---

        # {title}

        {body}

        ## Evidence

        - Repository sources declared by the bundle.
        """
    )


def write_ready_bundle(project: Project, name: str = "bootstrap") -> pathlib.Path:
    bundle = project.root / ".ezpowers" / "staging" / name
    files = bundle / "files"
    files.mkdir(parents=True)
    (project.root / "package.json").write_text('{"name":"demo"}\n', encoding="utf-8")
    (files / "AGENTS.md").write_text(
        generated_markdown(
            "Demo Agent Guide",
            doc_type="instructions",
            authority="canonical",
            body="Use repository evidence and run the declared checks.",
        ),
        encoding="utf-8",
    )
    (files / "CLAUDE.md").write_text("@AGENTS.md\n", encoding="utf-8")
    (files / "INDEX.md").write_text(
        generated_markdown(
            "Documentation Index",
            doc_type="index",
            authority="supporting",
            body="- [Agent guide](../AGENTS.md)",
        ),
        encoding="utf-8",
    )
    manifest = {
        "schema_version": 1,
        "status": "ready",
        "replace_links": True,
        "documents": [
            {
                "path": "AGENTS.md",
                "source": "files/AGENTS.md",
                "role": "repository-instructions",
                "ownership": "ezpowers",
                "authority": "canonical",
                "status": "active",
                "validator": "markdown",
                "evidence": ["package.json"],
            },
            {
                "path": "CLAUDE.md",
                "source": "files/CLAUDE.md",
                "role": "claude-import",
                "ownership": "ezpowers",
                "authority": "derived",
                "status": "active",
                "validator": "markdown",
                "evidence": ["AGENTS.md"],
            },
            {
                "path": "docs/INDEX.md",
                "source": "files/INDEX.md",
                "role": "documentation-index",
                "ownership": "ezpowers",
                "authority": "supporting",
                "status": "active",
                "validator": "markdown",
                "evidence": ["AGENTS.md"],
            },
        ],
        "links": [
            {"from": "CLAUDE.md", "to": "AGENTS.md", "relation": "imports"},
            {"from": "docs/INDEX.md", "to": "AGENTS.md", "relation": "indexes"},
        ],
    }
    (bundle / "bundle.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return bundle


class DocumentationRuntimeTests(unittest.TestCase):
    def test_root_architecture_document_is_a_safe_managed_graph_target(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Project(pathlib.Path(temp_dir))
            install = project.install()
            self.assertEqual(0, install.returncode, install.stdout + install.stderr)
            bundle = write_ready_bundle(project, "root-architecture")
            files = bundle / "files"
            (files / "ARCHITECTURE.md").write_text(
                "---\n"
                'doc_type: "reference"\n'
                'authority: "canonical"\n'
                'status: "active"\n'
                'generated_by: "ezpowers"\n'
                "---\n\n"
                "# Architecture\n\n"
                "## System Context\n\nThe CLI is the public entry point.\n\n"
                "## Maintenance\n\n"
                "Update this document when a durable boundary changes.\n\n"
                "## Evidence\n\n"
                "- Repository sources declared by the bundle.\n",
                encoding="utf-8",
            )
            index_path = files / "INDEX.md"
            index_path.write_text(
                index_path.read_text(encoding="utf-8")
                + "\n- [Architecture](../ARCHITECTURE.md)\n",
                encoding="utf-8",
            )
            manifest_path = bundle / "bundle.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["documents"].append(
                {
                    "path": "ARCHITECTURE.md",
                    "source": "files/ARCHITECTURE.md",
                    "role": "architecture",
                    "ownership": "ezpowers",
                    "authority": "canonical",
                    "status": "active",
                    "validator": "markdown",
                    "evidence": ["package.json"],
                }
            )
            manifest["links"].append(
                {
                    "from": "docs/INDEX.md",
                    "to": "ARCHITECTURE.md",
                    "relation": "indexes",
                }
            )
            manifest_path.write_text(
                json.dumps(manifest, indent=2) + "\n",
                encoding="utf-8",
            )

            preview = run_cli(
                project.runtime,
                "docs",
                "preview",
                "--bundle",
                str(bundle.relative_to(project.root)),
                "--json",
                cwd=project.root,
            )
            self.assertEqual(0, preview.returncode, preview.stdout + preview.stderr)
            preview_value = json.loads(preview.stdout)
            applied = run_cli(
                project.runtime,
                "docs",
                "apply",
                "--bundle",
                str(bundle.relative_to(project.root)),
                "--preview-sha256",
                preview_value["preview_sha256"],
                "--json",
                cwd=project.root,
            )
            self.assertEqual(0, applied.returncode, applied.stdout + applied.stderr)
            registry = json.loads(
                (project.root / ".ezpowers" / "docs.json").read_text(encoding="utf-8")
            )
            self.assertEqual(
                "architecture",
                registry["documents"]["ARCHITECTURE.md"]["role"],
            )
            lint = run_cli(
                project.runtime,
                "docs",
                "lint",
                "--json",
                cwd=project.root,
            )
            self.assertEqual(0, lint.returncode, lint.stdout + lint.stderr)

    def test_external_spec_remains_user_owned_but_must_keep_its_managed_block(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Project(pathlib.Path(temp_dir))
            self.assertEqual(0, project.install().returncode)
            spec_path = project.root / "docs" / "specs" / "existing.md"
            spec_path.parent.mkdir(parents=True)
            spec_path.write_text("# Existing spec without a block\n", encoding="utf-8")
            bundle = project.root / ".ezpowers" / "staging" / "external-spec"
            bundle.mkdir(parents=True)
            manifest = {
                "schema_version": 1,
                "status": "incomplete",
                "documents": [
                    {
                        "path": "docs/specs/existing.md",
                        "role": "feature-spec",
                        "ownership": "external",
                        "authority": "supporting",
                        "status": "active",
                        "validator": "spec",
                        "evidence": ["user:existing feature contract"],
                    }
                ],
                "links": [],
            }
            (bundle / "bundle.json").write_text(
                json.dumps(manifest, indent=2) + "\n",
                encoding="utf-8",
            )
            invalid = run_cli(
                project.runtime,
                "docs",
                "preview",
                "--bundle",
                ".ezpowers/staging/external-spec",
                "--json",
                cwd=project.root,
            )
            self.assertEqual(2, invalid.returncode, invalid.stdout + invalid.stderr)

            spec_path.write_text(
                managed_block(
                    "spec",
                    {
                        "schema_version": 1,
                        "criteria": [
                            {
                                "id": "AC-1",
                                "requirement_id": "R1",
                                "claim": "The external contract remains structurally valid.",
                                "verify_type": "document",
                                "integration": False,
                            }
                        ],
                    },
                ),
                encoding="utf-8",
            )
            valid = run_cli(
                project.runtime,
                "docs",
                "preview",
                "--bundle",
                ".ezpowers/staging/external-spec",
                "--json",
                cwd=project.root,
            )
            self.assertEqual(0, valid.returncode, valid.stdout + valid.stderr)
            self.assertEqual("external", json.loads(valid.stdout)["actions"][0]["action"])

    def test_ready_bundle_applies_registers_required_lint_and_detects_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Project(pathlib.Path(temp_dir))
            install = project.install()
            self.assertEqual(0, install.returncode, install.stdout + install.stderr)
            bundle = write_ready_bundle(project)

            preview = run_cli(
                project.runtime,
                "docs",
                "preview",
                "--bundle",
                str(bundle.relative_to(project.root)),
                "--json",
                cwd=project.root,
            )
            self.assertEqual(0, preview.returncode, preview.stdout + preview.stderr)
            preview_payload = json.loads(preview.stdout)
            self.assertEqual("READY", preview_payload["status"])
            self.assertEqual(
                {"create"},
                {entry["action"] for entry in preview_payload["actions"]},
            )

            config_path = project.root / ".ezpowers" / "config.json"
            config_before = json.loads(config_path.read_text(encoding="utf-8"))
            config_before["user_note"] = "preserve me"
            config_path.write_text(
                json.dumps(config_before, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            stale = run_cli(
                project.runtime,
                "docs",
                "apply",
                "--bundle",
                str(bundle.relative_to(project.root)),
                "--preview-sha256",
                preview_payload["preview_sha256"],
                "--json",
                cwd=project.root,
            )
            self.assertEqual(3, stale.returncode, stale.stdout + stale.stderr)
            self.assertEqual("CONFLICT", json.loads(stale.stdout)["status"])
            refreshed_preview = run_cli(
                project.runtime,
                "docs",
                "preview",
                "--bundle",
                str(bundle.relative_to(project.root)),
                "--json",
                cwd=project.root,
            )
            self.assertEqual(0, refreshed_preview.returncode)
            preview_payload = json.loads(refreshed_preview.stdout)

            applied = run_cli(
                project.runtime,
                "docs",
                "apply",
                "--bundle",
                str(bundle.relative_to(project.root)),
                "--preview-sha256",
                preview_payload["preview_sha256"],
                "--json",
                cwd=project.root,
            )
            self.assertEqual(0, applied.returncode, applied.stdout + applied.stderr)
            self.assertFalse(bundle.exists())
            self.assertEqual("@AGENTS.md\n", (project.root / "CLAUDE.md").read_text(encoding="utf-8"))

            config = json.loads(
                (project.root / ".ezpowers" / "config.json").read_text(encoding="utf-8")
            )
            self.assertEqual("preserve me", config["user_note"])
            self.assertIn("ezpowers.docs", config["required_checks"])
            self.assertEqual(
                ["docs", "lint", "--json"],
                config["checks"]["ezpowers.docs"]["argv"][-3:],
            )
            lint = run_cli(
                project.runtime,
                "docs",
                "lint",
                "--json",
                cwd=project.root,
            )
            self.assertEqual(0, lint.returncode, lint.stdout + lint.stderr)
            self.assertEqual("PASS", json.loads(lint.stdout)["status"])

            (project.root / "AGENTS.md").write_text("# user drift\n", encoding="utf-8")
            drift = run_cli(
                project.runtime,
                "docs",
                "lint",
                "--json",
                cwd=project.root,
            )
            self.assertEqual(1, drift.returncode, drift.stdout + drift.stderr)
            self.assertIn(
                "hash drift",
                " ".join(json.loads(drift.stdout)["errors"]),
            )

    def test_ready_design_bundle_registers_profile_and_exact_design_check(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Project(pathlib.Path(temp_dir))
            install = project.install()
            self.assertEqual(0, install.returncode, install.stdout + install.stderr)
            bundle = write_ready_bundle(project, "design-bootstrap")
            files = bundle / "files"
            (project.root / "index.html").write_text("<!doctype html>\n", encoding="utf-8")
            design = textwrap.dedent(
                """\
                ---
                version: alpha
                name: Fixture
                omitted: ["typography", "rounded", "spacing", "components"]
                colors:
                  primary: "#315bdc"
                ---
                # Fixture Design System

                ## Overview
                A compact fixture.

                ## Colors
                Primary is used for the main action.
                """
            )
            (files / "DESIGN.md").write_text(design, encoding="utf-8")
            mapping = {
                "schema_version": 1,
                "design_systems": [
                    {
                        "path": "DESIGN.md",
                        "profile": "google-alpha-0.4.0-ezpowers-1",
                        "frontend_roots": ["."],
                        "implementation_paths": ["index.html"],
                    }
                ],
            }
            frontend_body = (
                "## Design system mapping\n\n"
                "<!-- ezpowers:frontend-design:start -->\n```json\n"
                + json.dumps(mapping, indent=2)
                + "\n```\n<!-- ezpowers:frontend-design:end -->"
            )
            (files / "frontend-design.md").write_text(
                "---\n"
                'doc_type: "frontend-design"\n'
                'authority: "supporting"\n'
                'status: "active"\n'
                'generated_by: "ezpowers"\n'
                "---\n\n"
                "# Fixture Frontend Design\n\n"
                + frontend_body
                + "\n\n## Evidence\n\n- Repository sources declared by the bundle.\n",
                encoding="utf-8",
            )
            manifest_path = bundle / "bundle.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["documents"].extend(
                [
                    {
                        "path": "docs/ux/frontend-design.md",
                        "source": "files/frontend-design.md",
                        "role": "frontend-design",
                        "ownership": "ezpowers",
                        "authority": "supporting",
                        "status": "active",
                        "validator": "markdown",
                        "evidence": ["index.html"],
                    },
                    {
                        "path": "DESIGN.md",
                        "source": "files/DESIGN.md",
                        "role": "design-system",
                        "ownership": "ezpowers",
                        "authority": "canonical",
                        "status": "active",
                        "validator": "design-md",
                        "validator_profile": "google-alpha-0.4.0-ezpowers-1",
                        "evidence": ["docs/ux/frontend-design.md", "index.html"],
                    },
                ]
            )
            manifest_path.write_text(
                json.dumps(manifest, indent=2) + "\n",
                encoding="utf-8",
            )

            preview = run_cli(
                project.runtime,
                "docs",
                "preview",
                "--bundle",
                str(bundle.relative_to(project.root)),
                "--json",
                cwd=project.root,
            )
            self.assertEqual(0, preview.returncode, preview.stdout + preview.stderr)
            preview_payload = json.loads(preview.stdout)
            design_action = next(
                item for item in preview_payload["actions"] if item["path"] == "DESIGN.md"
            )
            self.assertEqual("PASS", design_action["design_review"]["status"])
            applied = run_cli(
                project.runtime,
                "docs",
                "apply",
                "--bundle",
                str(bundle.relative_to(project.root)),
                "--preview-sha256",
                preview_payload["preview_sha256"],
                "--json",
                cwd=project.root,
            )
            self.assertEqual(0, applied.returncode, applied.stdout + applied.stderr)
            config = json.loads(
                (project.root / ".ezpowers" / "config.json").read_text(encoding="utf-8")
            )
            self.assertIn("ezpowers.design", config["required_checks"])
            self.assertEqual(
                [
                    ".ezpowers/tools/design-md.py",
                    "check-project",
                    "--project-root",
                    ".",
                    "--frontend-design",
                    "docs/ux/frontend-design.md",
                    "--json",
                ],
                config["checks"]["ezpowers.design"]["argv"][1:],
            )
            registry = json.loads(
                (project.root / ".ezpowers" / "docs.json").read_text(encoding="utf-8")
            )
            self.assertEqual(
                "google-alpha-0.4.0-ezpowers-1",
                registry["documents"]["DESIGN.md"]["validator_profile"],
            )
            lint = run_cli(project.runtime, "docs", "lint", "--json", cwd=project.root)
            self.assertEqual(0, lint.returncode, lint.stdout + lint.stderr)

            update_bundle = project.root / ".ezpowers" / "staging" / "design-update"
            (update_bundle / "files").mkdir(parents=True)
            (update_bundle / "files" / "DESIGN.md").write_text(
                design.replace("#315bdc", "#2143ab"),
                encoding="utf-8",
            )
            (update_bundle / "bundle.json").write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "status": "ready",
                        "documents": [
                            {
                                "path": "DESIGN.md",
                                "source": "files/DESIGN.md",
                                "role": "design-system",
                                "ownership": "ezpowers",
                                "authority": "canonical",
                                "status": "active",
                                "validator": "design-md",
                                "validator_profile": "google-alpha-0.4.0-ezpowers-1",
                                "evidence": ["docs/ux/frontend-design.md", "index.html"],
                            }
                        ],
                        "links": [],
                    },
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            update_preview = run_cli(
                project.runtime,
                "docs",
                "preview",
                "--bundle",
                str(update_bundle.relative_to(project.root)),
                "--json",
                cwd=project.root,
            )
            self.assertEqual(
                0,
                update_preview.returncode,
                update_preview.stdout + update_preview.stderr,
            )
            review = json.loads(update_preview.stdout)["actions"][0]["design_review"]
            self.assertTrue(
                any(item["path"] == "colors.primary" for item in review["tokens"]["modified"])
            )
            config["checks"]["ezpowers.design"]["argv"][0] = "python-other"
            (project.root / ".ezpowers" / "config.json").write_text(
                json.dumps(config, indent=2) + "\n",
                encoding="utf-8",
            )
            drift = run_cli(project.runtime, "docs", "lint", "--json", cwd=project.root)
            self.assertEqual(1, drift.returncode, drift.stdout + drift.stderr)
            self.assertIn(
                "config check ezpowers.design is missing or changed",
                " ".join(json.loads(drift.stdout)["errors"]),
            )

    def test_unmanaged_document_requires_adoption_force_and_creates_backup(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Project(pathlib.Path(temp_dir))
            self.assertEqual(0, project.install().returncode)
            original = b"# User-owned guide\n"
            (project.root / "AGENTS.md").write_bytes(original)
            bundle = project.root / ".ezpowers" / "staging" / "adopt"
            (bundle / "files").mkdir(parents=True)
            (bundle / "files" / "AGENTS.md").write_text(
                generated_markdown(
                    "Adopted Guide",
                    doc_type="instructions",
                    authority="canonical",
                    body="Use the repository checks.",
                ),
                encoding="utf-8",
            )
            manifest = {
                "schema_version": 1,
                "status": "incomplete",
                "documents": [
                    {
                        "path": "AGENTS.md",
                        "source": "files/AGENTS.md",
                        "role": "repository-instructions",
                        "ownership": "ezpowers",
                        "authority": "canonical",
                        "status": "active",
                        "validator": "markdown",
                        "evidence": ["user:approved repository guidance"],
                    }
                ],
                "links": [],
            }
            manifest_path = bundle / "bundle.json"
            manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

            conflict = run_cli(
                project.runtime,
                "docs",
                "preview",
                "--bundle",
                ".ezpowers/staging/adopt",
                "--json",
                cwd=project.root,
            )
            self.assertEqual(3, conflict.returncode)
            conflict_payload = json.loads(conflict.stdout)
            rejected = run_cli(
                project.runtime,
                "docs",
                "apply",
                "--bundle",
                ".ezpowers/staging/adopt",
                "--preview-sha256",
                conflict_payload["preview_sha256"],
                "--force",
                "--json",
                cwd=project.root,
            )
            self.assertEqual(3, rejected.returncode)
            self.assertEqual("CONFLICT", json.loads(rejected.stdout)["status"])
            self.assertEqual(original, (project.root / "AGENTS.md").read_bytes())

            manifest["documents"][0]["adopt"] = True
            manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
            adopt_preview = run_cli(
                project.runtime,
                "docs",
                "preview",
                "--bundle",
                ".ezpowers/staging/adopt",
                "--json",
                cwd=project.root,
            )
            self.assertEqual(3, adopt_preview.returncode)
            adopt_payload = json.loads(adopt_preview.stdout)
            self.assertEqual("adopt", adopt_payload["actions"][0]["action"])

            no_force = run_cli(
                project.runtime,
                "docs",
                "apply",
                "--bundle",
                ".ezpowers/staging/adopt",
                "--preview-sha256",
                adopt_payload["preview_sha256"],
                "--json",
                cwd=project.root,
            )
            self.assertEqual(3, no_force.returncode)
            applied = run_cli(
                project.runtime,
                "docs",
                "apply",
                "--bundle",
                ".ezpowers/staging/adopt",
                "--preview-sha256",
                adopt_payload["preview_sha256"],
                "--force",
                "--json",
                cwd=project.root,
            )
            self.assertEqual(0, applied.returncode, applied.stdout + applied.stderr)
            result = json.loads(applied.stdout)
            backup = project.root / result["backup_path"] / "AGENTS.md"
            self.assertEqual(original, backup.read_bytes())


class WikiRuntimeTests(unittest.TestCase):
    def test_cjk_query_promotion_and_backup_first_prune(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Project(pathlib.Path(temp_dir))
            self.assertEqual(0, project.install().returncode)
            add_payload = {
                "id": "korean-architecture",
                "title": "한글 구조 결정",
                "category": "architecture",
                "tags": ["구조", "문서"],
                "body": "# 한글 구조 결정\n\n구조화된 문서 그래프를 사용한다.",
            }
            added = run_cli(
                project.runtime,
                "wiki",
                "add",
                "--input",
                json.dumps(add_payload, ensure_ascii=False),
                "--json",
                cwd=project.root,
            )
            self.assertEqual(0, added.returncode, added.stdout + added.stderr)
            query = run_cli(
                project.runtime,
                "wiki",
                "query",
                "--input",
                json.dumps({"query": "구조화"}, ensure_ascii=False),
                "--json",
                cwd=project.root,
            )
            self.assertEqual(0, query.returncode, query.stdout + query.stderr)
            self.assertEqual("korean-architecture", json.loads(query.stdout)["pages"][0]["id"])

            target = project.root / "docs" / "reference" / "architecture.md"
            target.parent.mkdir(parents=True)
            target.write_text("# Canonical architecture\n", encoding="utf-8")
            promote_input = json.dumps(
                {"id": "korean-architecture", "target": "docs/reference/architecture.md"}
            )
            preview = run_cli(
                project.runtime,
                "wiki",
                "promote",
                "--input",
                promote_input,
                "--json",
                cwd=project.root,
            )
            self.assertEqual(0, preview.returncode, preview.stdout + preview.stderr)
            preview_payload = json.loads(preview.stdout)
            promoted = run_cli(
                project.runtime,
                "wiki",
                "promote",
                "--input",
                promote_input,
                "--confirm",
                "--preview-sha256",
                preview_payload["preview_sha256"],
                "--json",
                cwd=project.root,
            )
            self.assertEqual(0, promoted.returncode, promoted.stdout + promoted.stderr)
            self.assertEqual("promoted", json.loads(promoted.stdout)["page"]["status"])

            second = {
                "id": "temporary-note",
                "title": "Temporary note",
                "category": "debugging",
                "body": "# Temporary note\n\nDiscard after review.",
            }
            self.assertEqual(
                0,
                run_cli(
                    project.runtime,
                    "wiki",
                    "add",
                    "--input",
                    json.dumps(second),
                    "--json",
                    cwd=project.root,
                ).returncode,
            )
            prune_input = json.dumps({"ids": ["temporary-note"]})
            prune_preview = run_cli(
                project.runtime,
                "wiki",
                "prune",
                "--input",
                prune_input,
                "--json",
                cwd=project.root,
            )
            prune_payload = json.loads(prune_preview.stdout)
            pruned = run_cli(
                project.runtime,
                "wiki",
                "prune",
                "--input",
                prune_input,
                "--confirm",
                "--preview-sha256",
                prune_payload["preview_sha256"],
                "--json",
                cwd=project.root,
            )
            self.assertEqual(0, pruned.returncode, pruned.stdout + pruned.stderr)
            backup = project.root / json.loads(pruned.stdout)["backup_path"]
            self.assertTrue((backup / "temporary-note.md").is_file())
            self.assertTrue((backup / "manifest.json").is_file())
            lint = run_cli(project.runtime, "wiki", "lint", "--json", cwd=project.root)
            self.assertEqual(0, lint.returncode, lint.stdout + lint.stderr)

    def test_session_hooks_are_separate_allowlisted_and_best_effort(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Project(pathlib.Path(temp_dir))
            install = project.install(
                "--enable-hooks",
                "both",
                "--enable-wiki-hooks",
                "both",
            )
            self.assertEqual(0, install.returncode, install.stdout + install.stderr)
            repeated = project.install(
                "--enable-hooks",
                "both",
                "--enable-wiki-hooks",
                "both",
            )
            self.assertEqual(0, repeated.returncode, repeated.stdout + repeated.stderr)
            for host, path in (
                ("claude", project.root / ".claude" / "settings.json"),
                ("codex", project.root / ".codex" / "hooks.json"),
            ):
                hooks = json.loads(path.read_text(encoding="utf-8"))["hooks"]
                self.assertEqual(1, len(hooks["Stop"]))
                self.assertEqual(1, len(hooks["SessionEnd"]))
                session_handler = hooks["SessionEnd"][0]["hooks"][0]
                self.assertEqual(5, session_handler["timeout"])
                serialized = json.dumps(session_handler)
                self.assertIn("wiki", serialized)
                self.assertIn("capture", serialized)
                self.assertIn(host, serialized)

            handler = json.loads(
                (project.root / ".claude" / "settings.json").read_text(encoding="utf-8")
            )["hooks"]["SessionEnd"][0]["hooks"][0]
            secret = "TRANSCRIPT_SECRET_MUST_NOT_PERSIST"
            capture = subprocess.run(
                [handler["command"], *handler["args"]],
                cwd=project.root / ".claude",
                input=json.dumps(
                    {
                        "hook_event_name": "SessionEnd",
                        "session_id": "private-session-id",
                        "cwd": str(project.root),
                        "transcript": secret,
                        "prompt": secret,
                        "tool_output": secret,
                    }
                ),
                text=True,
                capture_output=True,
                timeout=30,
                check=False,
            )
            self.assertEqual(0, capture.returncode, capture.stderr)
            self.assertEqual({}, json.loads(capture.stdout))
            wiki_root = project.root / ".ezpowers" / "wiki"
            self.assertTrue(list((wiki_root / "pages").glob("session-*.md")))
            stored = "\n".join(
                path.read_text(encoding="utf-8")
                for path in wiki_root.rglob("*")
                if path.is_file()
            )
            self.assertNotIn(secret, stored)
            self.assertNotIn("private-session-id", stored)
            self.assertNotIn(str(project.root), stored)

    def test_local_wiki_changes_do_not_stale_completion_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Project(pathlib.Path(temp_dir))
            self.assertEqual(0, project.install().returncode)
            tests_root = project.root / "empty-tests"
            tests_root.mkdir()
            (tests_root / "test_ok.py").write_text(
                "import unittest\n\n"
                "class Smoke(unittest.TestCase):\n"
                "    def test_ok(self):\n"
                "        self.assertTrue(True)\n",
                encoding="utf-8",
            )
            spec_path = project.root / "docs" / "specs" / "demo.md"
            plan_path = project.root / "docs" / "plans" / "demo.md"
            spec_path.parent.mkdir(parents=True)
            plan_path.parent.mkdir(parents=True)
            spec_path.write_text(
                managed_block(
                    "spec",
                    {
                        "schema_version": 1,
                        "criteria": [
                            {
                                "id": "AC-1",
                                "requirement_id": "R1",
                                "claim": "The repository unit test command exits zero.",
                                "verify_type": "cli",
                                "integration": False,
                            }
                        ],
                    },
                ),
                encoding="utf-8",
            )
            plan_path.write_text(
                managed_block(
                    "plan",
                    {
                        "schema_version": 1,
                        "spec": "docs/specs/demo.md",
                        "tasks": [
                            {
                                "id": "T1",
                                "criteria": ["AC-1"],
                                "checks": [
                                    {
                                        "id": "unit",
                                        "argv": [
                                            sys.executable,
                                            "-B",
                                            "-m",
                                            "unittest",
                                            "discover",
                                            "-s",
                                            "empty-tests",
                                        ],
                                        "cwd": ".",
                                        "timeout_seconds": 30,
                                        "kind": "test",
                                    }
                                ],
                            }
                        ],
                    },
                ),
                encoding="utf-8",
            )
            project.commit_all()
            verified = run_cli(
                project.runtime,
                "verify",
                "--plan",
                "docs/plans/demo.md",
                "--all",
                "--json",
                cwd=project.root,
            )
            self.assertEqual(0, verified.returncode, verified.stdout + verified.stderr)
            before = run_cli(project.runtime, "status", "--json", cwd=project.root)
            self.assertEqual("READY", json.loads(before.stdout)["status"])

            added = run_cli(
                project.runtime,
                "wiki",
                "add",
                "--input",
                json.dumps(
                    {
                        "title": "Local note",
                        "category": "reference",
                        "body": "# Local note\n\nLocal supporting knowledge.",
                    }
                ),
                "--json",
                cwd=project.root,
            )
            self.assertEqual(0, added.returncode, added.stdout + added.stderr)
            after = run_cli(project.runtime, "status", "--json", cwd=project.root)
            self.assertEqual(0, after.returncode, after.stdout + after.stderr)
            self.assertEqual("READY", json.loads(after.stdout)["status"])


if __name__ == "__main__":
    unittest.main()
