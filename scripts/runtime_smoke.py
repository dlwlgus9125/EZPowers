#!/usr/bin/env python3
"""Exercise the installed EZPowers v5 user flow in a disposable Git project."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import textwrap


REPO_ROOT = Path(__file__).resolve().parents[1]
INSTALLER = REPO_ROOT / "scripts" / "ezpowers.py"


def run(command: list[str], cwd: Path, *, expect: int = 0) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        command,
        cwd=cwd,
        text=True,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        timeout=90,
        check=False,
    )
    if result.returncode != expect:
        raise RuntimeError(
            f"exit {result.returncode}, expected {expect}: {command!r}\n{result.stdout}\n{result.stderr}"
        )
    return result


def block(kind: str, value: dict) -> str:
    return textwrap.dedent(
        f"""
        # Smoke {kind}

        <!-- ezpowers:{kind}:start -->
        ```json
        {json.dumps(value, indent=2)}
        ```
        <!-- ezpowers:{kind}:end -->
        """
    ).strip() + "\n"


def smoke() -> None:
    with tempfile.TemporaryDirectory(prefix="ezpowers-v5-smoke-") as name:
        root = Path(name)
        run(["git", "init", "-q"], root)
        run(["git", "config", "user.email", "smoke@example.com"], root)
        run(["git", "config", "user.name", "EZPowers Smoke"], root)
        run(["git", "config", "core.autocrlf", "false"], root)

        installed = run(
            [sys.executable, str(INSTALLER), "install", "--project-root", str(root)],
            REPO_ROOT,
        )
        if "installed" not in (installed.stdout + installed.stderr).lower():
            raise RuntimeError("installer did not report an installation")
        runtime = root / ".ezpowers" / "ezpowers.py"
        if not runtime.is_file():
            raise RuntimeError("installed runtime is missing")
        for host_root in (root / ".claude" / "skills", root / ".agents" / "skills"):
            if not (host_root / "execute" / "SKILL.md").is_file():
                raise RuntimeError(f"installed execute skill is missing under {host_root}")
        if (root / ".claude" / "skills" / "hud").exists():
            raise RuntimeError("plugin-only HUD was installed into the project kit")

        (root / "smoke_math.py").write_text(
            "def add(left, right):\n    return left + right\n",
            encoding="utf-8",
        )
        tests_root = root / "tests"
        tests_root.mkdir()
        (tests_root / "test_smoke_math.py").write_text(
            "import unittest\n"
            "from smoke_math import add\n\n"
            "class SmokeMathTests(unittest.TestCase):\n"
            "    def test_add(self):\n"
            "        self.assertEqual(add(2, 3), 5)\n",
            encoding="utf-8",
        )

        spec_path = root / "docs" / "specs" / "smoke.md"
        plan_path = root / "docs" / "plans" / "smoke.md"
        spec_path.parent.mkdir(parents=True)
        plan_path.parent.mkdir(parents=True)
        spec_path.write_text(
            block(
                "spec",
                {
                    "schema_version": 1,
                    "criteria": [
                        {
                            "id": "AC-1",
                            "requirement_id": "R1",
                            "claim": "The project's unit test verifies observable behavior.",
                            "verify_type": "cli",
                            "integration": False,
                        }
                    ],
                },
            ),
            encoding="utf-8",
        )
        plan_path.write_text(
            block(
                "plan",
                {
                    "schema_version": 1,
                    "spec": "docs/specs/smoke.md",
                    "tasks": [
                        {
                            "id": "T1",
                            "criteria": ["AC-1"],
                            "checks": [
                                {
                                    "id": "real-unit-test",
                                    "argv": [
                                        sys.executable,
                                        "-m",
                                        "unittest",
                                        "discover",
                                        "-s",
                                        "tests",
                                    ],
                                    "cwd": ".",
                                    "timeout_seconds": 10,
                                    "kind": "test",
                                }
                            ],
                        }
                    ],
                },
            ),
            encoding="utf-8",
        )
        (root / "source.txt").write_text("one\n", encoding="utf-8")
        (root / ".gitignore").write_text(
            "__pycache__/\n*.py[cod]\n",
            encoding="utf-8",
        )
        run(["git", "add", "-A"], root)
        run(["git", "commit", "-qm", "fixture"], root)

        run([sys.executable, str(runtime), "validate", "--plan", str(plan_path)], root)
        verified = run(
            [sys.executable, str(runtime), "verify", "--plan", str(plan_path), "--all", "--json"],
            root,
        )
        evidence = json.loads(verified.stdout)
        if evidence.get("status") != "PASS" or not (root / evidence["evidence_path"]).is_file():
            raise RuntimeError("all-scope verification did not preserve real PASS evidence")
        certified = run(
            [sys.executable, str(runtime), "certify", "--plan", str(plan_path), "--json"],
            root,
        )
        if json.loads(certified.stdout).get("status") != "PASS":
            raise RuntimeError("fresh evidence was not certified")

        (root / "source.txt").write_text("two\n", encoding="utf-8")
        stale = run(
            [sys.executable, str(runtime), "certify", "--plan", str(plan_path), "--json"],
            root,
            expect=1,
        )
        if "workspace" not in " ".join(json.loads(stale.stdout).get("reasons", [])).lower():
            raise RuntimeError("workspace mutation did not invalidate evidence")


def main() -> int:
    try:
        smoke()
    except Exception as exc:
        print(f"[FAIL] EZPowers v5 runtime smoke: {exc}", file=sys.stderr)
        return 1
    print("[PASS] EZPowers v5 install -> validate -> verify -> certify -> stale flow")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
