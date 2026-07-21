"""Shared constants and utilities for EZPowers eval/verification scripts.

Single source of truth for banned expressions and common timeout/progress
helpers used by validate.py, verify-step.py, and run_skill_evals.py.
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import pathlib
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
