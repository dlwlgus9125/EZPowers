import copy
import hashlib
import importlib.util
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest

from tests.test_assurance_graph import (
    check_contract,
    configure_required_checks,
    rehash_evidence,
    write_v2_flow,
)
from tests.test_ezpowers_runtime import (
    EZPOWERS,
    RuntimeProject,
    managed_block,
    run_cli,
)


def load_runtime() -> dict:
    """Load the source runtime in-process for pure-function tests."""
    spec = importlib.util.spec_from_file_location(
        "ezpowers_check_reuse_runtime",
        EZPOWERS,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load EZPowers runtime")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return vars(module)


def case_insensitive_filesystem(directory: pathlib.Path) -> bool:
    probe = directory / "CaseProbe.tmp"
    probe.write_text("probe", encoding="utf-8")
    try:
        return (directory / "caseprobe.tmp").exists()
    finally:
        probe.unlink()


# A check that appends one line to a file outside the project every time its
# process really starts. The count is ground truth that does not depend on any
# field the runtime writes about reuse.
COUNTER_SNIPPET = (
    "import pathlib, sys; "
    "handle = pathlib.Path(sys.argv[1]).open('a', encoding='utf-8'); "
    "handle.write('run\\n'); handle.close(); "
    "code = pathlib.Path(sys.argv[2]); "
    "raise SystemExit(int(code.read_text(encoding='utf-8')) if code.exists() else 0)"
)

V1_EVIDENCE_KEYS = {
    "config_sha256",
    "evidence_path",
    "finished_at",
    "installation",
    "installation_before",
    "plan_path",
    "plan_sha256",
    "project_checks",
    "reasons",
    "run_id",
    "schema_version",
    "scope",
    "spec_path",
    "spec_sha256",
    "started_at",
    "status",
    "tasks",
    "workspace",
    "workspace_before",
}
V2_EVIDENCE_KEYS = V1_EVIDENCE_KEYS | {
    "assurance_graph",
    "assurance_graph_sha256",
    "execution",
}
V1_CHECK_KEYS = {
    "argv",
    "cwd",
    "duration_ms",
    "exit_code",
    "id",
    "kind",
    "spawn_error",
    "status",
    "stderr_log",
    "stderr_sha256",
    "stdout_log",
    "stdout_sha256",
    "timed_out",
    "timeout_seconds",
}
V2_CHECK_KEYS = V1_CHECK_KEYS | {"finished_at", "node_id", "started_at"}
V1_CERTIFICATE_KEYS = {
    "certified_at",
    "config_sha256",
    "evidence_path",
    "evidence_sha256",
    "installation",
    "plan_path",
    "plan_sha256",
    "schema_version",
    "spec_path",
    "spec_sha256",
    "status",
    "workspace",
}
V2_CERTIFICATE_KEYS = V1_CERTIFICATE_KEYS | {"assurance_graph_sha256"}
STATE_KEYS = {
    "active_plan",
    "chain_gates",
    "chain_hosts",
    "chain_run",
    "latest_certificate",
    "latest_evidence",
    "schema_version",
    "updated_at",
}
EXECUTION_KEYS = {"max_parallel_checks", "waves"}
WAVE_KEYS = {
    "batch",
    "finished_at",
    "node_ids",
    "parallel",
    "phase",
    "started_at",
    "task_wave",
}


class ReuseFixture:
    """One installed project plus a sibling directory for process counters."""

    def __init__(self, test: unittest.TestCase, temp_dir: str) -> None:
        base = pathlib.Path(temp_dir)
        self.outside = base / "outside"
        self.outside.mkdir()
        root = base / "project"
        root.mkdir()
        self.project = RuntimeProject(root)
        install = self.project.install()
        test.assertEqual(0, install.returncode, install.stdout + install.stderr)
        self.root = root

    def counter(self, name: str) -> pathlib.Path:
        return self.outside / f"{name}.count"

    def exit_code_file(self, name: str) -> pathlib.Path:
        return self.outside / f"{name}.exit"

    def count(self, name: str) -> int:
        path = self.counter(name)
        if not path.exists():
            return 0
        return len(path.read_text(encoding="utf-8").splitlines())

    def check(
        self,
        check_id: str,
        *,
        reuse: dict | None = None,
        safe: bool = False,
        locks: list[str] | None = None,
    ) -> dict:
        value = {
            "id": check_id,
            "argv": [
                sys.executable,
                "-c",
                COUNTER_SNIPPET,
                str(self.counter(check_id)),
                str(self.exit_code_file(check_id)),
            ],
            "cwd": ".",
            "timeout_seconds": 30,
            "kind": "integration",
            "concurrency": {
                "safe": safe,
                "resource_locks": list(locks or []),
            },
        }
        if reuse is not None:
            value["reuse"] = reuse
        return value

    def cli(self, *args: str) -> subprocess.CompletedProcess:
        return run_cli(self.project.runtime, *args, cwd=self.root)

    def verify(
        self,
        plan: pathlib.Path,
        *extra: str,
        scope: tuple[str, ...] = ("--all",),
    ) -> tuple[subprocess.CompletedProcess, dict]:
        result = self.cli("verify", "--plan", str(plan), *scope, *extra, "--json")
        payload = json.loads(result.stdout) if result.stdout.strip() else {}
        return result, payload

    def evidence(self, payload: dict) -> dict:
        return json.loads(
            (self.root / payload["evidence_path"]).read_text(encoding="utf-8")
        )

    def certify(self, plan: pathlib.Path) -> tuple[subprocess.CompletedProcess, dict]:
        result = self.cli("certify", "--plan", str(plan), "--json")
        payload = json.loads(result.stdout) if result.stdout.strip() else {}
        return result, payload

    def certificate(self, payload: dict) -> dict:
        return json.loads(
            (self.root / payload["certificate_path"]).read_text(encoding="utf-8")
        )

    def state(self) -> dict:
        return json.loads(
            (self.root / ".ezpowers" / "state.json").read_text(encoding="utf-8")
        )

    def status(self) -> dict:
        return json.loads(self.cli("status", "--json").stdout)

    def write_source(self, name: str = "src/app.py", text: str = "VALUE = 1\n") -> None:
        path = self.root.joinpath(*name.split("/"))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def write_state(self, state: dict) -> None:
        (self.root / ".ezpowers" / "state.json").write_text(
            json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    def candidates(self) -> dict:
        value = self.state().get("reuse_candidates", {})
        return value if isinstance(value, dict) else {}


def all_checks(evidence: dict) -> list[dict]:
    entries = [
        check for task in evidence.get("tasks", []) for check in task["checks"]
    ]
    entries.extend(evidence.get("project_checks", []))
    return entries


def modes(evidence: dict) -> list[tuple[str, str | None]]:
    return [
        (entry["id"], (entry.get("reuse") or {}).get("mode"))
        for entry in all_checks(evidence)
    ]


def one_task(checks: list, *, task_id: str = "T1", criterion: str = "AC-1") -> dict:
    return {
        "id": task_id,
        "depends_on": [],
        "criteria": [criterion],
        "checks": checks,
    }


class UndeclaredFlowCharacterizationTests(unittest.TestCase):
    """Pin what a project without any reuse declaration records and runs."""

    def test_undeclared_v1_flow_keeps_evidence_certificate_and_state_shapes(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            fixture = ReuseFixture(self, temp_dir)
            plan = fixture.project.write_flow(
                [
                    {
                        "id": "pass",
                        "argv": [
                            sys.executable,
                            "-c",
                            "from pathlib import Path; assert Path('.').is_dir()",
                        ],
                        "cwd": ".",
                        "timeout_seconds": 10,
                        "kind": "test",
                    }
                ]
            )
            fixture.project.commit_all()

            verify, printed = fixture.verify(plan)
            self.assertEqual(0, verify.returncode, verify.stdout + verify.stderr)
            evidence = fixture.evidence(printed)
            self.assertEqual(printed, evidence)
            self.assertEqual(V1_EVIDENCE_KEYS, set(evidence))
            self.assertEqual({"checks", "criteria", "id"}, set(evidence["tasks"][0]))
            for entry in all_checks(evidence):
                self.assertEqual(V1_CHECK_KEYS, set(entry))

            certify, certified = fixture.certify(plan)
            self.assertEqual(0, certify.returncode, certify.stdout + certify.stderr)
            self.assertEqual(
                V1_CERTIFICATE_KEYS,
                set(fixture.certificate(certified)),
            )
            self.assertEqual(STATE_KEYS, set(fixture.state()))
            self.assertEqual("CERTIFIED", fixture.status()["status"])

    def test_undeclared_v2_flow_keeps_evidence_certificate_and_state_shapes(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            fixture = ReuseFixture(self, temp_dir)
            configure_required_checks(
                fixture.project,
                {"required-a": check_contract("required-a", delay=0)},
                ["required-a"],
            )
            plan = write_v2_flow(
                fixture.project,
                [
                    {
                        "id": "T1",
                        "depends_on": [],
                        "criteria": ["AC-1"],
                        "checks": [check_contract("task-a", delay=0)],
                    }
                ],
                slug="undeclared",
            )
            fixture.project.commit_all()

            verify, printed = fixture.verify(plan)
            self.assertEqual(0, verify.returncode, verify.stdout + verify.stderr)
            evidence = fixture.evidence(printed)
            self.assertEqual(printed, evidence)
            self.assertEqual(V2_EVIDENCE_KEYS, set(evidence))
            self.assertEqual(
                {"checks", "criteria", "depends_on", "id"},
                set(evidence["tasks"][0]),
            )
            self.assertEqual(EXECUTION_KEYS, set(evidence["execution"]))
            for wave in evidence["execution"]["waves"]:
                self.assertEqual(WAVE_KEYS, set(wave))
            entries = all_checks(evidence)
            self.assertEqual(2, len(entries))
            for entry in entries:
                self.assertEqual(V2_CHECK_KEYS, set(entry))

            certify, certified = fixture.certify(plan)
            self.assertEqual(0, certify.returncode, certify.stdout + certify.stderr)
            self.assertEqual(
                V2_CERTIFICATE_KEYS,
                set(fixture.certificate(certified)),
            )
            self.assertEqual(STATE_KEYS, set(fixture.state()))
            self.assertEqual("CERTIFIED", fixture.status()["status"])

    def test_undeclared_checks_start_one_process_per_occurrence_on_every_run(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            fixture = ReuseFixture(self, temp_dir)
            configure_required_checks(
                fixture.project,
                {"shared": fixture.check("shared")},
                ["shared"],
            )
            plan = write_v2_flow(
                fixture.project,
                [
                    {
                        "id": "T1",
                        "depends_on": [],
                        "criteria": ["AC-1"],
                        "checks": ["repeated", "repeated", "shared"],
                    }
                ],
                slug="occurrences",
                checks={"repeated": fixture.check("repeated")},
            )
            (fixture.root / "notes.txt").write_text("one\n", encoding="utf-8")
            fixture.project.commit_all()

            first, first_payload = fixture.verify(plan)
            self.assertEqual(0, first.returncode, first.stdout + first.stderr)
            self.assertEqual(2, fixture.count("repeated"))
            self.assertEqual(2, fixture.count("shared"))
            self.assertEqual(4, len(all_checks(first_payload)))

            (fixture.root / "notes.txt").write_text("two\n", encoding="utf-8")
            second, _ = fixture.verify(plan)
            self.assertEqual(0, second.returncode, second.stdout + second.stderr)
            self.assertEqual(4, fixture.count("repeated"))
            self.assertEqual(4, fixture.count("shared"))

            unchanged, _ = fixture.verify(plan)
            self.assertEqual(
                0,
                unchanged.returncode,
                unchanged.stdout + unchanged.stderr,
            )
            self.assertEqual(6, fixture.count("repeated"))
            self.assertEqual(6, fixture.count("shared"))


class ReuseDeclarationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.runtime = load_runtime()

    def declaration_errors(self, raw: object) -> list[str]:
        errors: list[str] = []
        self.runtime["_validate_reuse_declaration"](raw, label="check.reuse", errors=errors)
        return errors

    def test_valid_declarations_normalize_to_both_lists(self) -> None:
        errors: list[str] = []
        normalized = self.runtime["_validate_reuse_declaration"](
            {"paths": ["src/**", "tools/check.py", "**/*.cfg", "a?c/*.py", "**"]},
            label="check.reuse",
            errors=errors,
        )
        self.assertEqual([], errors)
        self.assertEqual(
            {
                "paths": ["src/**", "tools/check.py", "**/*.cfg", "a?c/*.py", "**"],
                "exclude": [],
            },
            normalized,
        )

    def test_malformed_declarations_and_patterns_are_rejected(self) -> None:
        malformed = [
            ["src/**"],
            {},
            {"paths": []},
            {"paths": "src/**"},
            {"paths": ["src/**"], "exclude": "docs/**"},
            {"paths": ["src/**"], "exclude": None},
            {"paths": ["src/**"], "unknown": True},
            {"paths": ["src/**", "src/**"]},
            {"paths": ["src/**"], "exclude": ["src/**"]},
        ]
        for raw in malformed:
            with self.subTest(declaration=raw):
                self.assertTrue(self.declaration_errors(raw))
        bad_patterns = [
            "",
            7,
            "/abs/path",
            "C:/drive/path",
            "c:relative",
            "src\\win",
            "../outside",
            "src/../other",
            "./src",
            "src/./a",
            "src//a",
            "src/",
            ":(glob)src",
            "-option",
            "!negated",
            "src/[ab].py",
            "src/{a,b}.py",
            "src/**.py",
            "src/a**/b",
            ".git/config",
            ".GIT/hooks/**",
            "src/a\tb",
        ]
        for pattern in bad_patterns:
            with self.subTest(pattern=pattern):
                self.assertTrue(self.declaration_errors({"paths": [pattern]}))
                self.assertTrue(
                    self.declaration_errors(
                        {"paths": ["src/**"], "exclude": [pattern]}
                    )
                )

    def test_pattern_matcher_semantics(self) -> None:
        import re

        table = [
            ("src/**", "src/app.py", True),
            ("src/**", "src/api/v1/handler.py", True),
            ("src/**", "src", False),
            ("src/**", "srcs/app.py", False),
            ("src/**", "lib/src/app.py", False),
            ("**", "README.md", True),
            ("**", "a/b/c.txt", True),
            ("**/*.md", "README.md", True),
            ("**/*.md", "docs/guide/intro.md", True),
            ("**/*.md", "docs/guide/intro.mdx", False),
            ("a/**/b", "a/b", True),
            ("a/**/b", "a/x/b", True),
            ("a/**/b", "a/x/y/b", True),
            ("a/**/b", "a/x/bb", False),
            ("*.py", "setup.py", True),
            ("*.py", "src/setup.py", False),
            ("test*", "tests/unit/core.py", False),
            ("test*", "testing", True),
            ("tests/*/unit.py", "tests/api/unit.py", True),
            ("tests/*/unit.py", "tests/api/v1/unit.py", False),
            ("src/a?c.py", "src/abc.py", True),
            ("src/a?c.py", "src/a/c.py", False),
            ("src/App.py", "src/app.py", False),
            ("tools/check.py", "tools/check.py", True),
            ("tools/check.py", "tools/checkxpy", False),
            ("tools/check.py", "tools/check.pyc", False),
            ("docs/v1.2+3/(a)/x^y$.txt", "docs/v1.2+3/(a)/x^y$.txt", True),
        ]
        for pattern, name, expected in table:
            with self.subTest(pattern=pattern, name=name):
                self.assertIsNone(self.runtime["_reuse_pattern_error"](pattern))
                regex = self.runtime["_reuse_pattern_regex"](pattern)
                self.assertEqual(expected, re.fullmatch(regex, name) is not None)
        declaration = {"paths": ["src/**"], "exclude": ["**/*.md"]}
        selects = self.runtime["_reuse_declaration_selects"]
        self.assertTrue(selects(declaration, "src/app.py"))
        self.assertFalse(selects(declaration, "src/notes/readme.md"))
        self.assertFalse(selects(declaration, "tests/test_app.py"))

    def test_schema_one_rejects_reuse_and_declaration_binds_the_graph_hash(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            fixture = ReuseFixture(self, temp_dir)
            fixture.write_source()

            def validate(plan: pathlib.Path) -> dict:
                result = fixture.cli("validate", "--plan", str(plan), "--json")
                payload = json.loads(result.stdout)
                payload["returncode"] = result.returncode
                return payload

            def plan_with(reuse: dict | None) -> pathlib.Path:
                return write_v2_flow(
                    fixture.project,
                    [one_task(["scoped"])],
                    slug="hash",
                    checks={"scoped": fixture.check("scoped", reuse=reuse)},
                )

            undeclared = validate(plan_with(None))
            self.assertEqual("PASS", undeclared["status"], undeclared)
            declared = validate(plan_with({"paths": ["src/**"]}))
            self.assertEqual("PASS", declared["status"], declared)
            self.assertNotEqual(
                undeclared["assurance_graph_sha256"],
                declared["assurance_graph_sha256"],
            )
            explicit_empty = validate(
                plan_with({"paths": ["src/**"], "exclude": []})
            )
            self.assertEqual(
                declared["assurance_graph_sha256"],
                explicit_empty["assurance_graph_sha256"],
            )
            edited = validate(
                plan_with({"paths": ["src/**"], "exclude": ["**/*.md"]})
            )
            self.assertNotEqual(
                declared["assurance_graph_sha256"],
                edited["assurance_graph_sha256"],
            )
            restored = validate(plan_with(None))
            self.assertEqual(
                undeclared["assurance_graph_sha256"],
                restored["assurance_graph_sha256"],
            )
            invalid = validate(plan_with({"paths": ["../outside"]}))
            self.assertNotEqual(0, invalid["returncode"])
            self.assertIn("reuse", " ".join(invalid["errors"]))

            legacy_check = fixture.check("legacy", reuse={"paths": ["src/**"]})
            legacy_check.pop("concurrency")
            plan_v1 = fixture.project.write_flow([legacy_check], slug="legacy")
            rejected = validate(plan_v1)
            self.assertNotEqual(0, rejected["returncode"])
            self.assertIn(
                "reuse requires schema_version 2",
                " ".join(rejected["errors"]),
            )

            config_path = fixture.root / ".ezpowers" / "config.json"
            config_check = dict(legacy_check)
            config_check.pop("id")
            config_path.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "project_name": "legacy",
                        "checks": {"legacy-config": config_check},
                        "required_checks": [],
                    },
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            passing = {
                "id": "pass",
                "argv": [
                    sys.executable,
                    "-c",
                    "from pathlib import Path; assert Path('.').is_dir()",
                ],
                "cwd": ".",
                "timeout_seconds": 10,
                "kind": "test",
            }
            config_rejected = validate(
                fixture.project.write_flow([passing], slug="config-v1")
            )
            self.assertNotEqual(0, config_rejected["returncode"])
            self.assertIn(
                "config.checks.legacy-config.reuse requires schema_version 2",
                " ".join(config_rejected["errors"]),
            )


class ReuseBehaviorTests(unittest.TestCase):
    """Observe real process starts; never trust the reuse fields alone."""

    def test_unchanged_declared_content_carries_a_pass_and_certifies(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            fixture = ReuseFixture(self, temp_dir)
            fixture.write_source()
            fixture.write_source("notes.txt", "one\n")
            configure_required_checks(
                fixture.project,
                {
                    "heavy": fixture.check("heavy", reuse={"paths": ["src/**"]}),
                    "plain": fixture.check("plain"),
                },
                ["heavy", "plain"],
            )
            plan = write_v2_flow(
                fixture.project,
                [one_task(["feature"])],
                slug="carry",
                checks={
                    "feature": fixture.check("feature", reuse={"paths": ["src/**"]})
                },
            )
            fixture.project.commit_all()

            first_run, first = fixture.verify(plan)
            self.assertEqual(0, first_run.returncode, first_run.stdout + first_run.stderr)
            self.assertEqual(
                [("feature", "executed"), ("heavy", "executed"), ("plain", None)],
                modes(first),
            )
            self.assertEqual((1, 1, 1), tuple(map(fixture.count, ("feature", "heavy", "plain"))))
            first_sha256 = hashlib.sha256(
                (fixture.root / first["evidence_path"]).read_bytes()
            ).hexdigest()

            fixture.write_source("notes.txt", "two\n")
            second_run, second = fixture.verify(plan)
            self.assertEqual(0, second_run.returncode, second_run.stdout + second_run.stderr)
            self.assertEqual(
                [("feature", "carried"), ("heavy", "carried"), ("plain", None)],
                modes(second),
            )
            self.assertEqual((1, 1, 2), tuple(map(fixture.count, ("feature", "heavy", "plain"))))
            self.assertEqual(second, fixture.evidence(second))

            first_by_id = {entry["id"]: entry for entry in all_checks(first)}
            run_directory = pathlib.PurePosixPath(second["evidence_path"]).parent
            for entry in all_checks(second)[:2]:
                source = first_by_id[entry["id"]]
                record = entry["reuse"]
                self.assertEqual(first["run_id"], record["source"]["run_id"])
                self.assertEqual(first_sha256, record["source"]["evidence_sha256"])
                self.assertEqual(source["node_id"], record["source"]["node_id"])
                self.assertEqual("all", record["source"]["scope"])
                self.assertEqual(source["finished_at"], record["source"]["finished_at"])
                self.assertEqual(source["reuse"]["key"], record["key"])
                self.assertEqual(1, record["file_count"])
                self.assertEqual(0, entry["duration_ms"])
                for stream in ("stdout", "stderr"):
                    log_name = entry[f"{stream}_log"]
                    self.assertEqual(run_directory, pathlib.PurePosixPath(log_name).parent)
                    self.assertNotEqual(source[f"{stream}_log"], log_name)
                    self.assertEqual(
                        (fixture.root / source[f"{stream}_log"]).read_bytes(),
                        (fixture.root / log_name).read_bytes(),
                    )
            self.assertEqual([], second["reuse"]["executed"])
            self.assertEqual(2, len(second["reuse"]["carried"]))
            self.assertFalse(second["reuse"]["forced_fresh"])
            executed_nodes = [
                node_id
                for wave in second["execution"]["waves"]
                for node_id in wave["node_ids"]
            ]
            self.assertEqual([all_checks(second)[2]["node_id"]], executed_nodes)

            certify, certified = fixture.certify(plan)
            self.assertEqual(0, certify.returncode, certify.stdout + certify.stderr)
            certificate = fixture.certificate(certified)
            self.assertEqual(second["reuse"], certificate["reuse"])
            self.assertEqual(
                {first["run_id"]},
                {item["source_run_id"] for item in certificate["reuse"]["carried"]},
            )
            self.assertEqual("CERTIFIED", fixture.status()["status"])
            self.assertEqual(
                {first["evidence_path"]},
                {item["path"] for item in fixture.candidates().values()},
            )
            self.assertEqual(2, len(fixture.candidates()))

            # The certified result is self-contained: removing the source run
            # must not change the verdict.
            shutil.rmtree((fixture.root / first["evidence_path"]).parent)
            self.assertEqual("CERTIFIED", fixture.status()["status"])

    def test_changed_declared_content_or_contract_always_re_executes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            fixture = ReuseFixture(self, temp_dir)
            fixture.write_source()
            fixture.write_source("src/keep.py", "KEEP = 1\n")

            def write_plan(reuse: dict, timeout: int = 30) -> pathlib.Path:
                check = fixture.check("scoped", reuse=reuse)
                check["timeout_seconds"] = timeout
                return write_v2_flow(
                    fixture.project,
                    [one_task(["scoped"])],
                    slug="changes",
                    checks={"scoped": check},
                )

            declaration = {"paths": ["src/**"], "exclude": ["src/**/*.md"]}
            plan = write_plan(declaration)
            fixture.project.commit_all()

            def expect(count: int, label: str) -> dict:
                result, payload = fixture.verify(plan)
                self.assertEqual(0, result.returncode, label + result.stdout + result.stderr)
                self.assertEqual(count, fixture.count("scoped"), label)
                return payload

            expect(1, "cold")
            expect(1, "unchanged")
            fixture.write_source("src/app.py", "VALUE = 2\n")
            expect(2, "edit a selected file")
            fixture.write_source("src/new.py", "NEW = 1\n")
            expect(3, "add a selected file")
            (fixture.root / "src" / "new.py").unlink()
            expect(4, "remove an untracked selected file")
            (fixture.root / "src" / "app.py").unlink()
            deleted = expect(5, "delete a tracked selected file")
            # Another selected file remains, so this is a key change and not an
            # empty-selection fallback.
            self.assertIsNotNone(all_checks(deleted)[0]["reuse"]["key"])
            self.assertEqual(1, all_checks(deleted)[0]["reuse"]["file_count"])
            fixture.write_source("src/main.py", "VALUE = 2\n")
            expect(6, "rename a selected file")
            fixture.write_source("src/readme.md", "excluded\n")
            carried = expect(6, "edit an excluded file")
            self.assertEqual([("scoped", "carried")], modes(carried))
            fixture.project.commit_all()
            expect(6, "commit unchanged content")
            fixture.write_source("docs/outside.txt", "outside\n")
            expect(6, "edit outside the selection")
            plan = write_plan({"paths": ["src/**"]})
            expect(7, "change the declaration")
            plan = write_plan({"paths": ["src/**"]}, timeout=31)
            expect(8, "change the check contract")
            expect(8, "unchanged after the contract change")

    def test_failed_result_is_never_carried_and_a_failure_revokes_the_pass(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            fixture = ReuseFixture(self, temp_dir)
            fixture.write_source()
            plan = write_v2_flow(
                fixture.project,
                [one_task(["flaky"])],
                slug="failure",
                checks={"flaky": fixture.check("flaky", reuse={"paths": ["src/**"]})},
            )
            fixture.project.commit_all()
            exit_code = fixture.exit_code_file("flaky")

            self.assertEqual(0, fixture.verify(plan)[0].returncode)
            self.assertEqual(0, fixture.verify(plan)[0].returncode)
            self.assertEqual(1, fixture.count("flaky"))
            self.assertEqual(1, len(fixture.candidates()))

            exit_code.write_text("3", encoding="utf-8")
            forced, forced_payload = fixture.verify(plan, "--no-reuse")
            self.assertEqual(1, forced.returncode, forced.stdout + forced.stderr)
            self.assertEqual(2, fixture.count("flaky"))
            self.assertTrue(forced_payload["reuse"]["forced_fresh"])
            self.assertEqual({}, fixture.candidates())

            revoked, revoked_payload = fixture.verify(plan)
            self.assertEqual(1, revoked.returncode, revoked.stdout + revoked.stderr)
            self.assertEqual(3, fixture.count("flaky"))
            self.assertEqual([("flaky", "executed")], modes(revoked_payload))
            again, _ = fixture.verify(plan)
            self.assertEqual(1, again.returncode)
            self.assertEqual(4, fixture.count("flaky"))
            self.assertEqual({}, fixture.candidates())

            exit_code.write_text("0", encoding="utf-8")
            self.assertEqual(0, fixture.verify(plan)[0].returncode)
            self.assertEqual(5, fixture.count("flaky"))
            recovered, recovered_payload = fixture.verify(plan)
            self.assertEqual(0, recovered.returncode)
            self.assertEqual(5, fixture.count("flaky"))
            self.assertEqual([("flaky", "carried")], modes(recovered_payload))

    def test_declared_duplicates_execute_once_and_no_reuse_executes_all(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            fixture = ReuseFixture(self, temp_dir)
            fixture.write_source()
            configure_required_checks(
                fixture.project,
                {"dup": fixture.check("dup", reuse={"paths": ["src/**"]})},
                ["dup"],
            )
            plan = write_v2_flow(
                fixture.project,
                [
                    one_task(["dup"]),
                    {
                        "id": "T2",
                        "depends_on": ["T1"],
                        "criteria": ["AC-2"],
                        "checks": ["dup"],
                    },
                ],
                slug="duplicates",
            )
            fixture.project.commit_all()

            first_run, first = fixture.verify(plan)
            self.assertEqual(0, first_run.returncode, first_run.stdout + first_run.stderr)
            self.assertEqual(1, fixture.count("dup"))
            entries = all_checks(first)
            self.assertEqual(
                [("dup", "executed"), ("dup", "shared"), ("dup", "shared")],
                modes(first),
            )
            self.assertEqual(3, len({entry["node_id"] for entry in entries}))
            logs = {entry[f"{stream}_log"] for entry in entries for stream in ("stdout", "stderr")}
            self.assertEqual(6, len(logs))
            for log_name in logs:
                self.assertTrue((fixture.root / log_name).is_file(), log_name)
            self.assertEqual(
                [[entries[0]["node_id"]]],
                [wave["node_ids"] for wave in first["execution"]["waves"]],
            )
            for entry in entries[1:]:
                self.assertEqual(
                    {"node_id": entries[0]["node_id"]},
                    entry["reuse"]["source"],
                )
            certify, _ = fixture.certify(plan)
            self.assertEqual(0, certify.returncode, certify.stdout + certify.stderr)

            fixture.exit_code_file("dup").write_text("5", encoding="utf-8")
            fixture.write_source("src/app.py", "VALUE = 2\n")
            failed_run, failed = fixture.verify(plan)
            self.assertEqual(1, failed_run.returncode, failed_run.stdout + failed_run.stderr)
            self.assertEqual(2, fixture.count("dup"))
            self.assertEqual(["FAIL", "FAIL", "FAIL"], [entry["status"] for entry in all_checks(failed)])
            self.assertEqual(
                [
                    "task T1 verification failed",
                    "task T2 verification failed",
                    "required project check dup failed",
                ],
                failed["reasons"],
            )

            fixture.exit_code_file("dup").write_text("0", encoding="utf-8")
            forced_run, forced = fixture.verify(plan, "--no-reuse")
            self.assertEqual(0, forced_run.returncode, forced_run.stdout + forced_run.stderr)
            self.assertEqual(5, fixture.count("dup"))
            self.assertTrue(forced["reuse"]["forced_fresh"])
            self.assertEqual(
                [("dup", "executed"), ("dup", "executed"), ("dup", "executed")],
                modes(forced),
            )
            self.assertEqual(3, len(forced["execution"]["waves"]))

            carried_run, carried = fixture.verify(plan)
            self.assertEqual(0, carried_run.returncode, carried_run.stdout + carried_run.stderr)
            self.assertEqual(5, fixture.count("dup"))
            self.assertEqual(
                [("dup", "carried"), ("dup", "carried"), ("dup", "carried")],
                modes(carried),
            )
            self.assertEqual([], carried["execution"]["waves"])
            certify, _ = fixture.certify(plan)
            self.assertEqual(0, certify.returncode, certify.stdout + certify.stderr)

    def test_ineligible_declarations_execute_every_run_with_a_reason(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            fixture = ReuseFixture(self, temp_dir)
            fixture.write_source()
            fixture.write_source("build/output.txt", "ignored\n")
            fixture.write_source(".gitignore", "build/\n")
            checks = {
                "typo": fixture.check("typo", reuse={"paths": ["srcc/**"]}),
                "partial": fixture.check(
                    "partial",
                    reuse={"paths": ["src/**", "missing/config.toml"]},
                ),
                "ignored": fixture.check("ignored", reuse={"paths": ["build/**"]}),
            }
            names = ["typo", "partial", "ignored"]
            link = fixture.root / "links" / "app.py"
            link.parent.mkdir()
            try:
                os.symlink(fixture.root / "src" / "app.py", link)
            except (OSError, NotImplementedError):
                link.parent.rmdir()
            else:
                checks["linked"] = fixture.check("linked", reuse={"paths": ["links/**"]})
                names.append("linked")
            plan = write_v2_flow(
                fixture.project,
                [one_task(names)],
                slug="ineligible",
                checks=checks,
            )
            fixture.project.commit_all()

            for expected_count in (1, 2):
                result, payload = fixture.verify(plan)
                self.assertEqual(0, result.returncode, result.stdout + result.stderr)
                for entry in all_checks(payload):
                    with self.subTest(check=entry["id"], run=expected_count):
                        self.assertEqual(expected_count, fixture.count(entry["id"]))
                        self.assertEqual("executed", entry["reuse"]["mode"])
                        self.assertIsNone(entry["reuse"]["key"])
                        self.assertIsNone(entry["reuse"]["content_sha256"])
                        expected_reason = (
                            "symbolic link"
                            if entry["id"] == "linked"
                            else "selects no file"
                        )
                        self.assertIn(expected_reason, entry["reuse"]["reason"])
            self.assertEqual({}, fixture.candidates())
            certify, _ = fixture.certify(plan)
            self.assertEqual(0, certify.returncode, certify.stdout + certify.stderr)

    def test_task_scope_pass_carries_across_scopes_and_plans_until_refresh(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            fixture = ReuseFixture(self, temp_dir)
            fixture.write_source()
            configure_required_checks(
                fixture.project,
                {"shared": fixture.check("shared", reuse={"paths": ["src/**"]})},
                [],
            )
            first_plan = write_v2_flow(fixture.project, [one_task(["shared"])], slug="first")
            second_plan = write_v2_flow(fixture.project, [one_task(["shared"])], slug="second")
            fixture.project.commit_all()

            task_run, task_payload = fixture.verify(first_plan, scope=("--task", "T1"))
            self.assertEqual(0, task_run.returncode, task_run.stdout + task_run.stderr)
            self.assertEqual(1, fixture.count("shared"))
            self.assertEqual([("shared", "executed")], modes(task_payload))

            all_run, all_payload = fixture.verify(first_plan)
            self.assertEqual(0, all_run.returncode, all_run.stdout + all_run.stderr)
            self.assertEqual(1, fixture.count("shared"))
            record = all_checks(all_payload)[0]["reuse"]
            self.assertEqual("carried", record["mode"])
            self.assertEqual("task:T1", record["source"]["scope"])
            certify, _ = fixture.certify(first_plan)
            self.assertEqual(0, certify.returncode, certify.stdout + certify.stderr)

            other_run, other_payload = fixture.verify(second_plan)
            self.assertEqual(0, other_run.returncode, other_run.stdout + other_run.stderr)
            self.assertEqual(1, fixture.count("shared"))
            self.assertEqual([("shared", "carried")], modes(other_payload))

            refresh = fixture.project.install("--refresh")
            self.assertEqual(0, refresh.returncode, refresh.stdout + refresh.stderr)
            refreshed_run, refreshed_payload = fixture.verify(second_plan)
            self.assertEqual(0, refreshed_run.returncode, refreshed_run.stdout + refreshed_run.stderr)
            self.assertEqual(2, fixture.count("shared"))
            self.assertEqual([("shared", "executed")], modes(refreshed_payload))

            self.assertEqual(1, len(fixture.candidates()))
            switched = fixture.project.install("--project-profile", "planning")
            self.assertEqual(0, switched.returncode, switched.stdout + switched.stderr)
            self.assertNotIn("reuse_candidates", fixture.state())

    def test_invalid_candidate_falls_back_to_execution(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            fixture = ReuseFixture(self, temp_dir)
            fixture.write_source()
            plan = write_v2_flow(
                fixture.project,
                [one_task(["scoped", "plain"])],
                slug="candidate",
                checks={
                    "scoped": fixture.check("scoped", reuse={"paths": ["src/**"]}),
                    "plain": fixture.check("plain"),
                },
            )
            fixture.project.commit_all()

            def run() -> dict:
                result, payload = fixture.verify(plan)
                self.assertEqual(0, result.returncode, result.stdout + result.stderr)
                return payload

            def edit_pointer(**changes: str) -> None:
                state = fixture.state()
                (contract,) = state["reuse_candidates"]
                state["reuse_candidates"][contract].update(changes)
                fixture.write_state(state)

            latest = run()
            self.assertEqual(1, fixture.count("scoped"))
            run()
            self.assertEqual(1, fixture.count("scoped"))
            (source_path,) = {item["path"] for item in fixture.candidates().values()}
            self.assertEqual(latest["evidence_path"], source_path)

            shutil.rmtree((fixture.root / source_path).parent)
            latest = run()
            self.assertEqual(2, fixture.count("scoped"), "deleted source run")

            source = fixture.root / latest["evidence_path"]
            source.write_bytes(source.read_bytes() + b" ")
            latest = run()
            self.assertEqual(3, fixture.count("scoped"), "edited source result")

            log = fixture.root / all_checks(latest)[0]["stdout_log"]
            log.write_bytes(log.read_bytes() + b"tampered")
            latest = run()
            self.assertEqual(4, fixture.count("scoped"), "edited source log")

            edit_pointer(node_id=all_checks(latest)[1]["node_id"])
            latest = run()
            self.assertEqual(5, fixture.count("scoped"), "pointer at an undeclared entry")

            edit_pointer(path="../outside/result.json")
            latest = run()
            self.assertEqual(6, fixture.count("scoped"), "pointer outside the evidence root")

            edit_pointer(sha256="0" * 64)
            latest = run()
            self.assertEqual(7, fixture.count("scoped"), "pointer hash mismatch")

            fixture.write_source("src/app.py", "VALUE = 2\n")
            state = fixture.state()
            (contract,) = state["reuse_candidates"]
            state["reuse_candidates"][contract]["recorded_at"] = "rewritten"
            fixture.write_state(state)
            run()
            self.assertEqual(8, fixture.count("scoped"), "selected content changed")
            run()
            self.assertEqual(8, fixture.count("scoped"), "valid again")

    def test_tampered_reuse_records_and_certificates_are_stale(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            fixture = ReuseFixture(self, temp_dir)
            fixture.write_source()
            fixture.write_source("notes.txt", "one\n")
            configure_required_checks(
                fixture.project,
                {
                    "heavy": fixture.check("heavy", reuse={"paths": ["src/**"]}),
                    "plain": fixture.check("plain"),
                },
                ["heavy", "plain"],
            )
            plan = write_v2_flow(
                fixture.project,
                [one_task(["feature"])],
                slug="tamper",
                checks={
                    "feature": fixture.check("feature", reuse={"paths": ["src/**"]})
                },
            )
            fixture.project.commit_all()
            _, first = fixture.verify(plan)
            fixture.write_source("notes.txt", "two\n")
            run, payload = fixture.verify(plan)
            self.assertEqual(0, run.returncode, run.stdout + run.stderr)
            evidence_path = fixture.root / payload["evidence_path"]
            original = evidence_path.read_bytes()
            self.assertEqual(0, fixture.certify(plan)[0].returncode)

            first_feature_log = all_checks(first)[0]["stdout_log"]

            def flip_mode(value: dict) -> None:
                value["tasks"][0]["checks"][0]["reuse"]["mode"] = "executed"

            def undeclared_record(value: dict) -> None:
                value["project_checks"][1]["reuse"] = copy.deepcopy(
                    value["project_checks"][0]["reuse"]
                )

            def borrow_source_log(value: dict) -> None:
                value["tasks"][0]["checks"][0]["stdout_log"] = first_feature_log

            def empty_summary(value: dict) -> None:
                value["reuse"]["carried"] = []

            def claim_execution(value: dict) -> None:
                value["execution"]["waves"][0]["node_ids"].insert(
                    0,
                    value["tasks"][0]["checks"][0]["node_id"],
                )

            def drop_summary(value: dict) -> None:
                del value["reuse"]

            def bad_source_hash(value: dict) -> None:
                value["tasks"][0]["checks"][0]["reuse"]["source"][
                    "evidence_sha256"
                ] = "not-a-hash"

            def drop_source_field(value: dict) -> None:
                del value["project_checks"][0]["reuse"]["source"]["run_id"]

            def carried_without_key(value: dict) -> None:
                value["project_checks"][0]["reuse"]["key"] = None

            for mutate in (
                flip_mode,
                undeclared_record,
                borrow_source_log,
                empty_summary,
                claim_execution,
                drop_summary,
                bad_source_hash,
                drop_source_field,
                carried_without_key,
            ):
                with self.subTest(mutation=mutate.__name__):
                    value = json.loads(original)
                    mutate(value)
                    evidence_path.write_text(
                        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True)
                        + "\n",
                        encoding="utf-8",
                        newline="\n",
                    )
                    rehash_evidence(fixture.project, evidence_path)
                    certify, certified = fixture.certify(plan)
                    self.assertEqual(1, certify.returncode, certify.stdout + certify.stderr)
                    self.assertTrue(certified["reasons"])
                    self.assertEqual("STALE", fixture.status()["status"])

            evidence_path.write_bytes(original)
            rehash_evidence(fixture.project, evidence_path)
            certify, certified = fixture.certify(plan)
            self.assertEqual(0, certify.returncode, certify.stdout + certify.stderr)
            certificate_path = fixture.root / certified["certificate_path"]
            certificate = json.loads(certificate_path.read_text(encoding="utf-8"))
            certificate["reuse"]["carried"] = []
            certificate_path.write_text(
                json.dumps(certificate, ensure_ascii=False, indent=2, sort_keys=True)
                + "\n",
                encoding="utf-8",
                newline="\n",
            )
            state = fixture.state()
            state["latest_certificate"]["sha256"] = hashlib.sha256(
                certificate_path.read_bytes()
            ).hexdigest()
            fixture.write_state(state)
            status = fixture.status()
            self.assertEqual("READY", status["status"])
            self.assertIn("certificate tamper", " ".join(status["reasons"]))

    def test_unstable_run_records_no_key_and_no_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            fixture = ReuseFixture(self, temp_dir)
            fixture.write_source()
            writer = fixture.check("writer", reuse={"paths": ["src/**"]})
            writer["argv"] = [
                sys.executable,
                "-c",
                "from pathlib import Path; Path('mutation.txt').write_text('x')",
            ]
            plan = write_v2_flow(
                fixture.project,
                [one_task(["writer", "steady"])],
                slug="unstable",
                checks={
                    "writer": writer,
                    "steady": fixture.check("steady", reuse={"paths": ["src/**"]}),
                },
            )
            fixture.project.commit_all()

            result, payload = fixture.verify(plan)
            self.assertEqual(1, result.returncode, result.stdout + result.stderr)
            self.assertIn("workspace changed during verification", payload["reasons"])
            for entry in all_checks(payload):
                self.assertEqual("executed", entry["reuse"]["mode"])
                self.assertIsNone(entry["reuse"]["key"])
            self.assertEqual({}, fixture.candidates())

            (fixture.root / "mutation.txt").unlink()
            fixture.exit_code_file("steady").write_text("0", encoding="utf-8")
            again, _ = fixture.verify(plan)
            self.assertEqual(1, again.returncode)
            self.assertEqual(2, fixture.count("steady"))

    def test_plan_v1_flow_ignores_config_reuse_declarations(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            fixture = ReuseFixture(self, temp_dir)
            fixture.write_source()
            fixture.write_source("notes.txt", "one\n")
            configure_required_checks(
                fixture.project,
                {"legacy": fixture.check("legacy", reuse={"paths": ["src/**"]})},
                ["legacy"],
            )
            plan = fixture.project.write_flow([], slug="v1")
            plan.write_text(
                managed_block(
                    "plan",
                    {
                        "schema_version": 1,
                        "spec": "docs/specs/v1.md",
                        "tasks": [
                            {"id": "T1", "criteria": ["AC-1"], "checks": ["legacy"]}
                        ],
                    },
                ),
                encoding="utf-8",
            )
            fixture.project.commit_all()

            for expected in (2, 4):
                result, payload = fixture.verify(plan)
                self.assertEqual(0, result.returncode, result.stdout + result.stderr)
                self.assertEqual(expected, fixture.count("legacy"))
                self.assertEqual(1, payload["schema_version"])
                self.assertEqual(V1_EVIDENCE_KEYS, set(payload))
                for entry in all_checks(payload):
                    self.assertEqual(V1_CHECK_KEYS, set(entry))
                fixture.write_source("notes.txt", f"run {expected}\n")
            self.assertEqual(STATE_KEYS, set(fixture.state()))

    def test_carried_barrier_lets_safe_neighbours_share_a_wave(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            fixture = ReuseFixture(self, temp_dir)
            fixture.write_source()
            fixture.write_source("notes.txt", "one\n")
            configure_required_checks(fixture.project, {}, [], workers=4)
            plan = write_v2_flow(
                fixture.project,
                [one_task(["safe-a", "barrier", "safe-b"])],
                slug="waves",
                checks={
                    "safe-a": fixture.check("safe-a", safe=True, locks=["a"]),
                    "barrier": fixture.check("barrier", reuse={"paths": ["src/**"]}),
                    "safe-b": fixture.check("safe-b", safe=True, locks=["b"]),
                },
            )
            fixture.project.commit_all()

            _, cold = fixture.verify(plan)
            self.assertEqual(
                [1, 1, 1],
                [len(wave["node_ids"]) for wave in cold["execution"]["waves"]],
            )
            fixture.write_source("notes.txt", "two\n")
            warm_run, warm = fixture.verify(plan)
            self.assertEqual(0, warm_run.returncode, warm_run.stdout + warm_run.stderr)
            self.assertEqual(
                ["safe-a", "barrier", "safe-b"],
                [entry["id"] for entry in all_checks(warm)],
            )
            self.assertEqual(
                [("safe-a", None), ("barrier", "carried"), ("safe-b", None)],
                modes(warm),
            )
            (wave,) = warm["execution"]["waves"]
            self.assertTrue(wave["parallel"])
            self.assertEqual(2, len(wave["node_ids"]))
            self.assertEqual((2, 1, 2), tuple(map(fixture.count, ("safe-a", "barrier", "safe-b"))))
            certify, _ = fixture.certify(plan)
            self.assertEqual(0, certify.returncode, certify.stdout + certify.stderr)

    def test_copied_project_tree_does_not_carry(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            fixture = ReuseFixture(self, temp_dir)
            fixture.write_source()
            plan = write_v2_flow(
                fixture.project,
                [one_task(["scoped"])],
                slug="copy",
                checks={"scoped": fixture.check("scoped", reuse={"paths": ["src/**"]})},
            )
            fixture.project.commit_all()
            self.assertEqual(0, fixture.verify(plan)[0].returncode)
            self.assertEqual(0, fixture.verify(plan)[0].returncode)
            self.assertEqual(1, fixture.count("scoped"))

            copy_root = pathlib.Path(temp_dir) / "copy"
            shutil.copytree(fixture.root, copy_root, symlinks=True)
            copied = run_cli(
                copy_root / ".ezpowers" / "ezpowers.py",
                "verify",
                "--plan",
                str(copy_root / "docs" / "plans" / "copy.md"),
                "--all",
                "--json",
                cwd=copy_root,
            )
            self.assertEqual(0, copied.returncode, copied.stdout + copied.stderr)
            self.assertEqual(2, fixture.count("scoped"))
            self.assertEqual([("scoped", "executed")], modes(json.loads(copied.stdout)))

    @unittest.skipUnless(os.name == "posix", "the execute bit is a POSIX property")
    def test_execute_bit_change_re_executes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            fixture = ReuseFixture(self, temp_dir)
            fixture.write_source("tools/run.sh", "#!/bin/sh\n")
            plan = write_v2_flow(
                fixture.project,
                [one_task(["scoped"])],
                slug="mode",
                checks={"scoped": fixture.check("scoped", reuse={"paths": ["tools/**"]})},
            )
            fixture.project.commit_all()
            self.assertEqual(0, fixture.verify(plan)[0].returncode)
            self.assertEqual(0, fixture.verify(plan)[0].returncode)
            self.assertEqual(1, fixture.count("scoped"))
            script = fixture.root / "tools" / "run.sh"
            script.chmod(script.stat().st_mode | 0o111)
            self.assertEqual(0, fixture.verify(plan)[0].returncode)
            self.assertEqual(2, fixture.count("scoped"))

    def test_case_only_rename_is_not_carried(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            if not case_insensitive_filesystem(pathlib.Path(temp_dir)):
                self.skipTest("requires a case-insensitive filesystem")
            fixture = ReuseFixture(self, temp_dir)
            fixture.write_source("src/Module.py", "VALUE = 1\n")
            plan = write_v2_flow(
                fixture.project,
                [one_task(["scoped"])],
                slug="case",
                checks={"scoped": fixture.check("scoped", reuse={"paths": ["src/**"]})},
            )
            fixture.project.commit_all()
            self.assertEqual(0, fixture.verify(plan)[0].returncode)
            self.assertEqual(0, fixture.verify(plan)[0].returncode)
            self.assertEqual(1, fixture.count("scoped"))

            os.rename(fixture.root / "src" / "Module.py", fixture.root / "src" / "module.py")
            result, payload = fixture.verify(plan)
            self.assertEqual(0, result.returncode, result.stdout + result.stderr)
            self.assertEqual(2, fixture.count("scoped"))
            record = all_checks(payload)[0]["reuse"]
            if record["key"] is None:
                self.assertIn("spelling", record["reason"])

    def test_edit_inside_the_snapshot_window_is_never_carried(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            fixture = ReuseFixture(self, temp_dir)
            fixture.write_source()
            plan = write_v2_flow(
                fixture.project,
                [one_task(["scoped"])],
                slug="window",
                checks={"scoped": fixture.check("scoped", reuse={"paths": ["src/**"]})},
            )
            fixture.project.commit_all()
            self.assertEqual(0, fixture.verify(plan)[0].returncode)
            self.assertEqual(0, fixture.verify(plan)[0].returncode)
            self.assertEqual(1, fixture.count("scoped"))

            racing_runtime = textwrap.dedent(
                """
                import pathlib
                import runpy
                import sys

                runtime = runpy.run_path(sys.argv[1])
                namespace = runtime["main"].__globals__
                original = namespace["_workspace_snapshot"]
                calls = []

                def snapshot_then_edit(root):
                    value = original(root)
                    calls.append(1)
                    if len(calls) == 1:
                        pathlib.Path(sys.argv[2]).write_text(
                            "VALUE = 'edited in the window'\\n",
                            encoding="utf-8",
                        )
                    return value

                namespace["_workspace_snapshot"] = snapshot_then_edit
                raise SystemExit(namespace["main"](sys.argv[3:]))
                """
            )
            raced = subprocess.run(
                [
                    sys.executable,
                    "-c",
                    racing_runtime,
                    str(fixture.project.runtime),
                    str(fixture.root / "src" / "app.py"),
                    "verify",
                    "--plan",
                    str(plan),
                    "--all",
                    "--json",
                ],
                cwd=fixture.root,
                text=True,
                capture_output=True,
                timeout=60,
                check=False,
            )
            self.assertEqual(1, raced.returncode, raced.stdout + raced.stderr)
            payload = json.loads(raced.stdout)
            self.assertIn("workspace changed during verification", payload["reasons"])
            self.assertEqual(2, fixture.count("scoped"))
            self.assertEqual([("scoped", "executed")], modes(payload))
            self.assertEqual({}, fixture.candidates())

    def test_malformed_candidate_map_is_ignored(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            fixture = ReuseFixture(self, temp_dir)
            fixture.write_source()
            plan = write_v2_flow(
                fixture.project,
                [one_task(["scoped"])],
                slug="broken-map",
                checks={"scoped": fixture.check("scoped", reuse={"paths": ["src/**"]})},
            )
            fixture.project.commit_all()
            self.assertEqual(0, fixture.verify(plan)[0].returncode)
            self.assertEqual(0, fixture.certify(plan)[0].returncode)

            for broken in ("broken", ["broken"], {"contract": "not-a-pointer"}):
                with self.subTest(candidates=broken):
                    state = fixture.state()
                    state["reuse_candidates"] = broken
                    fixture.write_state(state)
                    self.assertEqual("CERTIFIED", fixture.status()["status"])
                    hook = subprocess.run(
                        [sys.executable, str(fixture.project.runtime), "hook", "--host", "claude"],
                        cwd=fixture.root,
                        input='{"hook_event_name":"Stop"}',
                        text=True,
                        capture_output=True,
                        timeout=30,
                        check=False,
                    )
                    self.assertEqual(0, hook.returncode, hook.stderr)
                    self.assertEqual({}, json.loads(hook.stdout))
            before = fixture.count("scoped")
            result, payload = fixture.verify(plan)
            self.assertEqual(0, result.returncode, result.stdout + result.stderr)
            self.assertEqual(before + 1, fixture.count("scoped"))
            pointers = [
                item for item in fixture.candidates().values() if isinstance(item, dict)
            ]
            self.assertEqual([payload["evidence_path"]], [item["path"] for item in pointers])
            carried, _ = fixture.verify(plan)
            self.assertEqual(0, carried.returncode, carried.stdout + carried.stderr)
            self.assertEqual(before + 1, fixture.count("scoped"))

    def test_no_reuse_keeps_undeclared_flows_unchanged(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            fixture = ReuseFixture(self, temp_dir)
            plan = write_v2_flow(
                fixture.project,
                [one_task(["repeated", "repeated"])],
                slug="plain-forced",
                checks={"repeated": fixture.check("repeated")},
            )
            fixture.project.commit_all()
            result, payload = fixture.verify(plan, "--no-reuse")
            self.assertEqual(0, result.returncode, result.stdout + result.stderr)
            self.assertEqual(2, fixture.count("repeated"))
            self.assertEqual(V2_EVIDENCE_KEYS, set(payload))
            for entry in all_checks(payload):
                self.assertEqual(V2_CHECK_KEYS, set(entry))
            certify, certified = fixture.certify(plan)
            self.assertEqual(0, certify.returncode, certify.stdout + certify.stderr)
            self.assertEqual(V2_CERTIFICATE_KEYS, set(fixture.certificate(certified)))
            self.assertEqual(STATE_KEYS, set(fixture.state()))


if __name__ == "__main__":
    unittest.main()
