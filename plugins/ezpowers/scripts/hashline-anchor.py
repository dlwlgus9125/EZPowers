#!/usr/bin/env python3
"""Create and verify sidecar line anchors for generated harness step files."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys
from datetime import datetime, timezone
from typing import Any


SCHEMA_VERSION = 1


def read_lines(path: pathlib.Path) -> list[str]:
    return path.read_text(encoding="utf-8").splitlines()


def line_hash(line_number: int, text: str) -> str:
    normalized = text.rstrip("\r")
    seed = f"{line_number}\0{normalized}".encode("utf-8")
    return hashlib.sha256(seed).hexdigest()[:10]


def build_anchor(source: pathlib.Path) -> dict[str, Any]:
    lines = read_lines(source)
    return {
        "schema_version": SCHEMA_VERSION,
        "source": source.name,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "line_count": len(lines),
        "lines": [
            {"line": index + 1, "hash": line_hash(index + 1, line)}
            for index, line in enumerate(lines)
        ],
    }


def verify_anchor(source: pathlib.Path, anchor_path: pathlib.Path) -> dict[str, Any]:
    current = build_anchor(source)
    expected = json.loads(anchor_path.read_text(encoding="utf-8"))
    expected_lines = expected.get("lines", []) if isinstance(expected, dict) else []
    current_lines = current["lines"]
    mismatches = []

    max_len = max(len(expected_lines), len(current_lines))
    for index in range(max_len):
        expected_item = expected_lines[index] if index < len(expected_lines) else None
        current_item = current_lines[index] if index < len(current_lines) else None
        if expected_item != current_item:
            mismatches.append(
                {
                    "line": index + 1,
                    "expected": expected_item,
                    "actual": current_item,
                }
            )

    return {
        "pass": len(mismatches) == 0,
        "source": str(source),
        "anchor": str(anchor_path),
        "expected_line_count": len(expected_lines),
        "actual_line_count": len(current_lines),
        "mismatches": mismatches[:20],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Stamp or verify hashline anchors")
    sub = parser.add_subparsers(dest="command", required=True)

    stamp = sub.add_parser("stamp")
    stamp.add_argument("--source", required=True, type=pathlib.Path)
    stamp.add_argument("--anchor", required=True, type=pathlib.Path)

    verify = sub.add_parser("verify")
    verify.add_argument("--source", required=True, type=pathlib.Path)
    verify.add_argument("--anchor", required=True, type=pathlib.Path)
    verify.add_argument("--json", action="store_true")

    show = sub.add_parser("print")
    show.add_argument("--source", required=True, type=pathlib.Path)

    args = parser.parse_args()

    if args.command == "stamp":
        anchor = build_anchor(args.source)
        args.anchor.parent.mkdir(parents=True, exist_ok=True)
        args.anchor.write_text(json.dumps(anchor, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"stamped {args.anchor}")
        return 0

    if args.command == "verify":
        if not args.anchor.exists():
            result = {
                "pass": False,
                "source": str(args.source),
                "anchor": str(args.anchor),
                "error": "anchor sidecar missing",
            }
        else:
            result = verify_anchor(args.source, args.anchor)
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print("PASS" if result["pass"] else "FAIL")
        return 0 if result["pass"] else 1

    anchor = build_anchor(args.source)
    print(json.dumps(anchor, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
