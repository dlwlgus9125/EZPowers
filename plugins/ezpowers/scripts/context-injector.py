#!/usr/bin/env python3
"""Build and validate compact EZPowers context injection blocks."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import sys


SENTINEL_RE = re.compile(r"<!--\s*EZP_CONTEXT:([a-zA-Z0-9_.-]+):([a-fA-F0-9]{8,64})\s*-->")


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


def build_block(kind: str, content: str) -> str:
    marker = digest(f"{kind}\0{content}")
    return f"<!-- EZP_CONTEXT:{kind}:{marker} -->\n{content.rstrip()}\n<!-- /EZP_CONTEXT:{kind}:{marker} -->"


def verify_text(text: str, required: list[str]) -> dict:
    seen: dict[tuple[str, str], int] = {}
    for match in SENTINEL_RE.finditer(text):
        key = (match.group(1), match.group(2).lower())
        seen[key] = seen.get(key, 0) + 1

    duplicates = [
        {"kind": kind, "hash": marker, "count": count}
        for (kind, marker), count in seen.items()
        if count > 1
    ]
    missing = [item for item in required if item not in text]
    return {
        "pass": not duplicates and not missing,
        "duplicates": duplicates,
        "missing_required": missing,
        "sentinel_count": sum(seen.values()),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build or verify EZPowers context blocks")
    sub = parser.add_subparsers(dest="command", required=True)

    build = sub.add_parser("build")
    build.add_argument("--kind", required=True)
    build.add_argument("--content", default="")
    build.add_argument("--content-file", type=pathlib.Path)

    verify = sub.add_parser("verify")
    verify.add_argument("--file", required=True, action="append", type=pathlib.Path)
    verify.add_argument("--require", action="append", default=[])
    verify.add_argument("--json", action="store_true")

    args = parser.parse_args()

    if args.command == "build":
        content = args.content
        if args.content_file:
            content = args.content_file.read_text(encoding="utf-8")
        print(build_block(args.kind, content))
        return 0

    combined = "\n".join(path.read_text(encoding="utf-8") for path in args.file)
    result = verify_text(combined, args.require)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print("PASS" if result["pass"] else "FAIL")
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
