#!/usr/bin/env python3
"""Manage the EZPowers-owned Codex CLI model and usage HUD configuration.

Codex CLI v0.101.0 and newer provides a native TUI status line.  This helper
only manages the smallest global ``[tui]`` fragment needed for the EZPowers
model and usage HUD; it never installs a project harness and never rewrites
unrelated Codex settings.

Writes require ``--approve``.  Existing unowned status-line settings are a
conflict unless ``--replace-existing`` is supplied alongside that approval.
"""

from __future__ import annotations

import argparse
import codecs
import hashlib
import json
import os
import re
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


START_MARKER = "# >>> ezpowers:managed-codex-hud >>>"
END_MARKER = "# <<< ezpowers:managed-codex-hud <<<"
STATUS_LINE = (
    'status_line = ["model-with-reasoning", "five-hour-limit", '
    '"weekly-limit", "context-used"]'
)
USE_COLORS = "status_line_use_colors = true"
MANAGED_FRAGMENT = (START_MARKER, STATUS_LINE, USE_COLORS, END_MARKER)
LEGACY_MANAGED_FRAGMENTS = (
    (
        START_MARKER,
        'status_line = ["five-hour-limit", "weekly-limit", "context-used"]',
        USE_COLORS,
        END_MARKER,
    ),
)
MANAGED_KEYS = ("status_line", "status_line_use_colors")

SECTION_RE = re.compile(r"^\s*\[([^\]]+)\]\s*(?:#.*)?$")
KEY_RE = re.compile(r"^\s*(status_line|status_line_use_colors)\s*=")
ROOT_DOTTED_KEY_RE = re.compile(
    r"^\s*tui\.(status_line|status_line_use_colors)\s*="
)
ROOT_TUI_INLINE_RE = re.compile(r"^\s*tui\s*=")

EXIT_OK = 0
EXIT_APPROVAL_REQUIRED = 2
EXIT_CONFLICT = 3
EXIT_MALFORMED = 4
EXIT_ERROR = 5


class ConfigMalformed(ValueError):
    """The existing file cannot be edited without guessing its structure."""


@dataclass(frozen=True)
class TextFile:
    exists: bool
    lines: tuple[str, ...]
    newline: str
    final_newline: bool
    bom: bool
    raw: bytes


@dataclass(frozen=True)
class Assignment:
    key: str
    start: int
    end: int


@dataclass(frozen=True)
class Analysis:
    status: str
    tui_start: int | None
    tui_end: int | None
    block: tuple[int, int] | None
    assignments: tuple[Assignment, ...]
    conflict_keys: tuple[str, ...]


def _default_config_path() -> Path:
    codex_home = os.environ.get("CODEX_HOME")
    root = Path(codex_home).expanduser() if codex_home else Path.home() / ".codex"
    return root / "config.toml"


def _read_text_file(path: Path) -> TextFile:
    if not path.exists():
        return TextFile(False, (), "\n", True, False, b"")

    raw = path.read_bytes()
    bom = raw.startswith(codecs.BOM_UTF8)
    payload = raw[len(codecs.BOM_UTF8) :] if bom else raw
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ConfigMalformed(f"config is not valid UTF-8: {exc}") from exc

    newline = "\r\n" if "\r\n" in text else "\n"
    final_newline = text.endswith(("\n", "\r"))
    return TextFile(
        True,
        tuple(text.splitlines()),
        newline,
        final_newline,
        bom,
        raw,
    )


def _render_bytes(
    lines: Iterable[str], *, newline: str, final_newline: bool, bom: bool
) -> bytes:
    values = list(lines)
    text = newline.join(values)
    if final_newline and values:
        text += newline
    payload = text.encode("utf-8")
    return (codecs.BOM_UTF8 + payload) if bom else payload


def _section_headers(lines: tuple[str, ...] | list[str]) -> list[tuple[int, str]]:
    headers: list[tuple[int, str]] = []
    for index, line in enumerate(lines):
        match = SECTION_RE.match(line)
        if match:
            headers.append((index, match.group(1).strip()))
    return headers


def _tui_bounds(lines: tuple[str, ...] | list[str]) -> tuple[int | None, int | None]:
    headers = _section_headers(lines)
    tui_headers = [(index, name) for index, name in headers if name == "tui"]
    if len(tui_headers) > 1:
        raise ConfigMalformed("config contains more than one [tui] section")
    if not tui_headers:
        return None, None

    start = tui_headers[0][0]
    end = len(lines)
    for index, _ in headers:
        if index > start:
            end = index
            break
    return start, end


def _managed_block(lines: tuple[str, ...] | list[str]) -> tuple[int, int] | None:
    starts = [index for index, line in enumerate(lines) if line.strip() == START_MARKER]
    ends = [index for index, line in enumerate(lines) if line.strip() == END_MARKER]
    if not starts and not ends:
        return None
    if len(starts) != 1 or len(ends) != 1 or starts[0] >= ends[0]:
        raise ConfigMalformed("Codex HUD ownership markers are incomplete or duplicated")
    return starts[0], ends[0]


def _array_assignment_end(lines: tuple[str, ...] | list[str], start: int, limit: int) -> int:
    first = lines[start].split("=", 1)[1]
    if not first.lstrip().startswith("["):
        return start

    depth = 0
    opened = False
    quote: str | None = None
    escaped = False

    for index in range(start, limit):
        segment = lines[index].split("=", 1)[1] if index == start else lines[index]
        for char in segment:
            if quote is not None:
                if quote == '"' and escaped:
                    escaped = False
                    continue
                if quote == '"' and char == "\\":
                    escaped = True
                    continue
                if char == quote:
                    quote = None
                continue
            if char in ('"', "'"):
                quote = char
                continue
            if char == "#":
                break
            if char == "[":
                opened = True
                depth += 1
            elif char == "]":
                depth -= 1
                if depth < 0:
                    raise ConfigMalformed("status_line has an unmatched closing bracket")
                if opened and depth == 0:
                    return index

    raise ConfigMalformed("status_line array is not closed before the next section")


def _assignments(
    lines: tuple[str, ...] | list[str],
    tui_start: int | None,
    tui_end: int | None,
    block: tuple[int, int] | None,
) -> tuple[Assignment, ...]:
    if tui_start is None or tui_end is None:
        return ()

    found: list[Assignment] = []
    index = tui_start + 1
    while index < tui_end:
        if block and block[0] <= index <= block[1]:
            index = block[1] + 1
            continue
        match = KEY_RE.match(lines[index])
        if not match:
            index += 1
            continue
        key = match.group(1)
        end = _array_assignment_end(lines, index, tui_end) if key == "status_line" else index
        found.append(Assignment(key, index, end))
        index = end + 1
    return tuple(found)


def _root_tui_assignments(
    lines: tuple[str, ...] | list[str],
) -> tuple[Assignment, ...]:
    headers = _section_headers(lines)
    root_end = headers[0][0] if headers else len(lines)
    found: list[Assignment] = []
    index = 0
    while index < root_end:
        if ROOT_TUI_INLINE_RE.match(lines[index]):
            raise ConfigMalformed("root inline 'tui = {...}' cannot be merged safely")
        match = ROOT_DOTTED_KEY_RE.match(lines[index])
        if not match:
            index += 1
            continue
        key = match.group(1)
        end = _array_assignment_end(lines, index, root_end) if key == "status_line" else index
        found.append(Assignment(key, index, end))
        index = end + 1
    return tuple(found)


def _unique_keys(assignments: Iterable[Assignment]) -> tuple[str, ...]:
    seen: set[str] = set()
    result: list[str] = []
    for assignment in assignments:
        if assignment.key not in seen:
            seen.add(assignment.key)
            result.append(assignment.key)
    return tuple(result)


def _analyze(lines: tuple[str, ...] | list[str]) -> Analysis:
    tui_start, tui_end = _tui_bounds(lines)
    block = _managed_block(lines)
    if block:
        if tui_start is None or tui_end is None or not (
            tui_start < block[0] and block[1] < tui_end
        ):
            raise ConfigMalformed("Codex HUD ownership block is outside the [tui] section")

    assignments = (
        *_root_tui_assignments(lines),
        *_assignments(lines, tui_start, tui_end, block),
    )
    conflict_keys = _unique_keys(assignments)

    if block:
        actual = tuple(lines[block[0] : block[1] + 1])
        if actual == MANAGED_FRAGMENT:
            status = "conflict" if assignments else "installed"
        elif actual in LEGACY_MANAGED_FRAGMENTS:
            status = "conflict" if assignments else "outdated"
        else:
            status = "customized"
    elif assignments:
        status = "conflict"
    else:
        status = "absent"

    return Analysis(status, tui_start, tui_end, block, assignments, conflict_keys)


def _remove_spans(lines: list[str], spans: Iterable[tuple[int, int]]) -> list[str]:
    for start, end in sorted(spans, reverse=True):
        del lines[start : end + 1]
    return lines


def _insert_fragment(lines: list[str]) -> list[str]:
    tui_start, tui_end = _tui_bounds(lines)
    fragment = list(MANAGED_FRAGMENT)
    if tui_start is None or tui_end is None:
        while lines and not lines[-1].strip():
            lines.pop()
        if lines:
            lines.append("")
        lines.extend(["[tui]", *fragment])
        return lines

    insertion = tui_end
    while insertion > tui_start + 1 and not lines[insertion - 1].strip():
        del lines[insertion - 1]
        insertion -= 1
    lines[insertion:insertion] = fragment
    next_section = insertion + len(fragment) < len(lines)
    if next_section:
        lines.insert(insertion + len(fragment), "")
    return lines


def _install_lines(
    source: TextFile, analysis: Analysis, *, replace_existing: bool
) -> tuple[list[str], bool]:
    if analysis.status == "installed":
        return list(source.lines), False
    if analysis.status in {"conflict", "customized"} and not replace_existing:
        return list(source.lines), False

    spans: list[tuple[int, int]] = []
    if analysis.block:
        spans.append(analysis.block)
    spans.extend((item.start, item.end) for item in analysis.assignments)
    lines = _remove_spans(list(source.lines), spans)
    return _insert_fragment(lines), True


def _uninstall_lines(
    source: TextFile, analysis: Analysis, *, replace_existing: bool
) -> tuple[list[str], bool]:
    if analysis.status == "absent":
        return list(source.lines), False
    if analysis.block is None:
        return list(source.lines), False
    if analysis.status == "customized" and not replace_existing:
        return list(source.lines), False

    lines = _remove_spans(list(source.lines), [analysis.block])
    return lines, True


def _atomic_write(path: Path, data: bytes, existing_mode: int | None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=".config.toml.ezpowers-", dir=path.parent)
    temporary_path = Path(temporary)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        if existing_mode is not None:
            os.chmod(temporary_path, existing_mode)
        os.replace(temporary_path, path)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def _digest(data: bytes) -> str | None:
    return hashlib.sha256(data).hexdigest() if data else None


def _result(
    *,
    action: str,
    status: str,
    path: Path,
    changed: bool,
    before: bytes,
    after: bytes,
    conflict_keys: Iterable[str] = (),
    message: str,
) -> dict[str, object]:
    return {
        "action": action,
        "status": status,
        "config_path": str(path),
        "changed": changed,
        "managed_fragment": list(MANAGED_FRAGMENT),
        "conflict_keys": list(conflict_keys),
        "sha256_before": _digest(before),
        "sha256_after": _digest(after),
        "message": message,
    }


def _emit(payload: dict[str, object], *, as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
        return
    print(f"Codex HUD: {payload['status']}")
    print(f"Config: {payload['config_path']}")
    print(str(payload["message"]))
    if payload["action"] == "preview":
        print("Managed fragment:")
        for line in payload["managed_fragment"]:
            print(line)


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Install, inspect, or remove the global native Codex model and usage HUD."
        )
    )
    parser.add_argument("action", choices=("status", "preview", "install", "uninstall"))
    parser.add_argument("--config", type=Path, default=_default_config_path())
    parser.add_argument(
        "--approve",
        action="store_true",
        help="Confirm a requested install or uninstall write.",
    )
    parser.add_argument(
        "--replace-existing",
        action="store_true",
        help="Replace a conflicting status_line only after its exact diff was approved.",
    )
    parser.add_argument("--json", action="store_true", help="Emit one JSON object.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv or sys.argv[1:])
    path = args.config.expanduser().resolve()
    try:
        source = _read_text_file(path)
        analysis = _analyze(source.lines)
    except (OSError, ConfigMalformed) as exc:
        payload = _result(
            action=args.action,
            status="malformed",
            path=path,
            changed=False,
            before=b"",
            after=b"",
            message=str(exc),
        )
        _emit(payload, as_json=args.json)
        return EXIT_MALFORMED

    if args.action == "status":
        message = {
            "installed": "The EZPowers-owned native status line is active in config.",
            "outdated": (
                "An older exact EZPowers-owned status line is active and can be upgraded."
            ),
            "absent": "No EZPowers-owned Codex HUD is installed.",
            "conflict": "Existing unowned Codex TUI status settings were preserved.",
            "customized": "The marked HUD block was edited and is treated as user-owned.",
        }[analysis.status]
        payload = _result(
            action=args.action,
            status=analysis.status,
            path=path,
            changed=False,
            before=source.raw,
            after=source.raw,
            conflict_keys=analysis.conflict_keys,
            message=message,
        )
        _emit(payload, as_json=args.json)
        return EXIT_CONFLICT if analysis.status in {"conflict", "customized"} else EXIT_OK

    if args.action in {"preview", "install"}:
        lines, changed = _install_lines(
            source, analysis, replace_existing=args.replace_existing
        )
        if analysis.status in {"conflict", "customized"} and not args.replace_existing:
            payload = _result(
                action=args.action,
                status=analysis.status,
                path=path,
                changed=False,
                before=source.raw,
                after=source.raw,
                conflict_keys=analysis.conflict_keys,
                message=(
                    "No write performed. Review the existing TUI settings, then use "
                    "--replace-existing only after approving their replacement."
                ),
            )
            _emit(payload, as_json=args.json)
            return EXIT_CONFLICT
        final_newline = source.final_newline if source.exists else True
        after = _render_bytes(
            lines,
            newline=source.newline,
            final_newline=final_newline,
            bom=source.bom,
        )
        if args.action == "preview":
            payload = _result(
                action=args.action,
                status=analysis.status,
                path=path,
                changed=after != source.raw,
                before=source.raw,
                after=after,
                conflict_keys=analysis.conflict_keys,
                message="Preview only; no file was written.",
            )
            _emit(payload, as_json=args.json)
            return EXIT_OK
        if not args.approve:
            payload = _result(
                action=args.action,
                status="approval_required",
                path=path,
                changed=False,
                before=source.raw,
                after=source.raw,
                conflict_keys=analysis.conflict_keys,
                message="No write performed. Re-run install with --approve after reviewing preview.",
            )
            _emit(payload, as_json=args.json)
            return EXIT_APPROVAL_REQUIRED

        if after != source.raw:
            existing_mode = path.stat().st_mode if source.exists else None
            _atomic_write(path, after, existing_mode)
        payload = _result(
            action=args.action,
            status="installed",
            path=path,
            changed=after != source.raw,
            before=source.raw,
            after=after,
            conflict_keys=analysis.conflict_keys,
            message=(
                "EZPowers Codex HUD upgraded. Start a new Codex session to load it."
                if analysis.status == "outdated"
                else "EZPowers Codex HUD installed. Start a new Codex session to load it."
            ),
        )
        _emit(payload, as_json=args.json)
        return EXIT_OK

    lines, changed = _uninstall_lines(
        source, analysis, replace_existing=args.replace_existing
    )
    if analysis.status in {"conflict", "customized"} and not (
        analysis.status == "customized" and args.replace_existing
    ):
        payload = _result(
            action=args.action,
            status=analysis.status,
            path=path,
            changed=False,
            before=source.raw,
            after=source.raw,
            conflict_keys=analysis.conflict_keys,
            message="No write performed; the existing settings are not an exact EZPowers-owned block.",
        )
        _emit(payload, as_json=args.json)
        return EXIT_CONFLICT
    if not changed:
        payload = _result(
            action=args.action,
            status="absent",
            path=path,
            changed=False,
            before=source.raw,
            after=source.raw,
            message="No EZPowers-owned Codex HUD was present.",
        )
        _emit(payload, as_json=args.json)
        return EXIT_OK
    if not args.approve:
        payload = _result(
            action=args.action,
            status="approval_required",
            path=path,
            changed=False,
            before=source.raw,
            after=source.raw,
            message="No write performed. Re-run uninstall with --approve after reviewing the removal.",
        )
        _emit(payload, as_json=args.json)
        return EXIT_APPROVAL_REQUIRED

    after = _render_bytes(
        lines,
        newline=source.newline,
        final_newline=source.final_newline,
        bom=source.bom,
    )
    existing_mode = path.stat().st_mode if source.exists else None
    _atomic_write(path, after, existing_mode)
    payload = _result(
        action=args.action,
        status="absent",
        path=path,
        changed=True,
        before=source.raw,
        after=after,
        message="EZPowers-owned Codex HUD configuration removed.",
    )
    _emit(payload, as_json=args.json)
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
