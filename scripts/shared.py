"""Shared constants and utilities for EZPowers verification scripts.

Single source of truth for the banned vague expressions. Run directly to scan
files (used by the commit gate scripts/check-repo.ps1):

    python scripts/shared.py <file.md> [<file.md> ...]

Exits non-zero and prints one line per violation when a banned expression is
found. The constants are also consumed by scripts/verify-step.py.
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import pathlib
import re
import sys
import time
from typing import Any

# ---------------------------------------------------------------------------
# Banned expressions (skills/spec/SKILL.md L197-205)
# ---------------------------------------------------------------------------
BANNED_KO = [
    "적절히", "적절하게",
    "필요한 경우", "필요 시",
    "등등", "기타",
    "올바르게", "정상적으로",
    "효율적으로", "최적화하여",
    "가능하면", "가급적",
    "상황에 맞게", "상황에 따라",
]
BANNED_EN_RE = [
    r"\bappropriately\b",
    r"\bif necessary\b", r"\bif needed\b",
    r"\betc\.\b", r"\band so on\b",
    r"\bproperly\b", r"\bcorrectly\b",
    r"\befficiently\b", r"\boptimized\b",
    r"\bif possible\b", r"\bpreferably\b",
    r"\bas appropriate\b", r"\bdepending on\b",
]

# ---------------------------------------------------------------------------
# Timeout / progress utilities
# ---------------------------------------------------------------------------


def parse_timeout(value: str | int | None, default: int, label: str) -> int:
    """Parse a positive timeout value from CLI args or environment."""
    if value is None or value == "":
        return default
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise argparse.ArgumentTypeError(f"{label} must be an integer") from exc
    if parsed < 1:
        raise argparse.ArgumentTypeError(f"{label} must be >= 1")
    return parsed


def env_timeout(name: str, default: int) -> int:
    return parse_timeout(os.environ.get(name), default, name)


def utc_timestamp() -> str:
    return datetime.datetime.now(datetime.UTC).isoformat().replace("+00:00", "Z")


def write_progress(
    progress_file: str | pathlib.Path | None, payload: dict[str, Any]
) -> None:
    if not progress_file:
        return
    path = pathlib.Path(progress_file)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {"timestamp": utc_timestamp(), **payload}
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def remaining_timeout(deadline: float | None, requested: int) -> float:
    if deadline is None:
        return float(requested)
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        return 0.0
    return min(float(requested), remaining)


# ---------------------------------------------------------------------------
# Banned-expression scan (commit gate)
# ---------------------------------------------------------------------------


def scan_banned(text: str) -> list[str]:
    """Return the banned expressions found in text (empty if clean)."""
    hits: list[str] = []
    for term in BANNED_KO:
        if term in text:
            hits.append(term)
    for pattern in BANNED_EN_RE:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            hits.append(match.group(0))
    return hits


def _main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Scan files for banned vague expressions.")
    parser.add_argument("files", nargs="*", help="Files to scan")
    args = parser.parse_args(argv)
    violations = 0
    for name in args.files:
        path = pathlib.Path(name)
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for hit in scan_banned(text):
            print(f"{name}: banned expression: {hit}")
            violations += 1
    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(_main(sys.argv[1:]))
