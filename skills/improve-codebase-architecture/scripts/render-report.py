#!/usr/bin/env python3
"""Resolve and run the canonical EZPowers architecture report renderer."""

from __future__ import annotations

from pathlib import Path
import runpy


def renderer_path() -> Path:
    skill_root = Path(__file__).resolve().parent.parent
    plugin_renderer = skill_root.parent.parent / "scripts" / "architecture-review-report.py"
    project_renderers = [
        root / ".ezpowers" / "tools" / "architecture-review-report.py"
        for root in (Path.cwd().resolve(), *Path.cwd().resolve().parents)
    ]
    for candidate in (*project_renderers, plugin_renderer):
        if candidate.is_file():
            return candidate
    raise SystemExit(
        "architecture report renderer not found in the installed project kit "
        "or EZPowers plugin distribution"
    )


if __name__ == "__main__":
    runpy.run_path(str(renderer_path()), run_name="__main__")
