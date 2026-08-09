#!/usr/bin/env python3
"""Compare the reviewed DESIGN.md upstream inputs with their current bytes.

This maintainer-only command is deliberately read-only and is not installed in
the project kit. Normal EZPowers operation never requires network access.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


DEFAULT_PROFILE = "google-alpha-0.4.0-ezpowers-1"
DEFAULT_BASE_URL = "https://raw.githubusercontent.com/google-labs-code/design.md/main"


def load_contract(path: pathlib.Path, profile_id: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"cannot read profile contract {path}: {exc}") from exc
    if not isinstance(value, dict) or value.get("schema_version") != 1:
        raise RuntimeError("profile contract schema_version must be 1")
    profiles = value.get("profiles")
    if not isinstance(profiles, dict) or not isinstance(profiles.get(profile_id), dict):
        raise RuntimeError(f"unknown profile: {profile_id}")
    return profiles[profile_id]


def fetch(base_url: str, relative_path: str, timeout: float) -> bytes:
    encoded_path = "/".join(urllib.parse.quote(part) for part in pathlib.PurePosixPath(relative_path).parts)
    url = f"{base_url.rstrip('/')}/{encoded_path}"
    request = urllib.request.Request(url, headers={"User-Agent": "EZPowers-design-md-upstream-check/1"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def check(profile: dict[str, Any], base_url: str, timeout: float) -> tuple[dict[str, Any], int]:
    upstream = profile.get("upstream")
    watched = upstream.get("watched_files") if isinstance(upstream, dict) else None
    if not isinstance(watched, list) or not watched:
        raise RuntimeError("profile upstream.watched_files must be a non-empty array")
    files: list[dict[str, Any]] = []
    unavailable: list[str] = []
    changed: list[str] = []
    for item in watched:
        if not isinstance(item, dict) or not isinstance(item.get("path"), str) or not isinstance(item.get("sha256"), str):
            raise RuntimeError("invalid watched file entry")
        path = item["path"]
        expected = item["sha256"].lower()
        try:
            data = fetch(base_url, path, timeout)
        except (OSError, urllib.error.URLError, TimeoutError) as exc:
            unavailable.append(f"{path}: {exc}")
            files.append({"path": path, "expected_sha256": expected, "status": "UNAVAILABLE"})
            continue
        actual = hashlib.sha256(data).hexdigest()
        status = "CURRENT" if actual == expected else "CHANGED"
        if status == "CHANGED":
            changed.append(path)
        files.append(
            {
                "path": path,
                "expected_sha256": expected,
                "observed_sha256": actual,
                "bytes": len(data),
                "status": status,
            }
        )
    if unavailable:
        status = "UNAVAILABLE"
        code = 2
    elif changed:
        status = "REVIEW_REQUIRED"
        code = 1
    else:
        status = "CURRENT"
        code = 0
    return (
        {
            "schema_version": 1,
            "status": status,
            "base_url": base_url,
            "pinned_commit": upstream.get("commit") if isinstance(upstream, dict) else None,
            "reviewed_at": upstream.get("reviewed_at") if isinstance(upstream, dict) else None,
            "files": files,
            "changed": changed,
            "unavailable": unavailable,
            "writes_performed": False,
        },
        code,
    )


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Check whether reviewed Google DESIGN.md inputs changed upstream")
    parser.add_argument("--profile-contract", type=pathlib.Path, default=pathlib.Path("docs/reference/design-md-profile.json"))
    parser.add_argument("--profile", default=DEFAULT_PROFILE)
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--timeout", type=float, default=15.0)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        profile = load_contract(args.profile_contract.resolve(), args.profile)
        payload, code = check(profile, args.base_url, args.timeout)
    except RuntimeError as exc:
        payload, code = {"schema_version": 1, "status": "UNAVAILABLE", "error": str(exc), "writes_performed": False}, 2
    if args.json:
        print(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True))
    else:
        print(f"[{payload['status']}] Google DESIGN.md upstream review")
        for item in payload.get("files", []):
            print(f"[{item['status']}] {item['path']}")
        if payload.get("error"):
            print(payload["error"], file=sys.stderr)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
