#!/usr/bin/env python3
"""EZPowers statusline HUD for Claude Code.

Reads the statusLine JSON payload Claude Code pipes to stdin and prints one
ASCII line for the CLI footer:

    14:32 | Fable 5 | 5h:12%(2h10m) wk:26%(2d5h) | ctx:34%

The model segment is cyan and prefers the payload's ``model.display_name``,
falling back to an id parse (opus/sonnet/haiku/fable plus a dotted version,
e.g. ``claude-opus-4-8`` -> ``Opus 4.8``). Usage segments are wrapped in ANSI
colors by threshold: green below 70%, yellow from 70%, red from 90%. Claude
Code's TUI renders the escape codes itself, so this works on Windows; the
time and the fallback line stay uncolored. Segments render only when their
payload fields are present (API-key sessions have no rate_limits, so they
show time + model + ctx only). On any parse error the script prints the
local time and exits 0 -- a statusline must never crash or write stderr.

This file ships with the plugin distribution and is meant to be executed
from the installed plugin copy by a user-managed global statusLine command;
it is never copied into a target project's local kit. Standard library only.
"""

from __future__ import annotations

import json
import sys
import time
from datetime import datetime


_GREEN = "\x1b[32m"
_YELLOW = "\x1b[33m"
_RED = "\x1b[31m"
_CYAN = "\x1b[36m"
_RESET = "\x1b[0m"

_MODEL_FAMILIES = ("opus", "sonnet", "haiku", "fable")


def _colorize(text, percent):
    if percent >= 90:
        color = _RED
    elif percent >= 70:
        color = _YELLOW
    else:
        color = _GREEN
    return "%s%s%s" % (color, text, _RESET)


def _fmt_countdown(resets_at, now):
    """Time until reset as '2d5h', '2h10m', or '45m'; None if unparseable.

    Accepts epoch seconds (current payloads) and ISO-8601 strings (tolerated
    in case the payload format drifts across Claude Code versions).
    """
    try:
        if isinstance(resets_at, str):
            target = datetime.fromisoformat(resets_at.replace("Z", "+00:00")).timestamp()
        elif isinstance(resets_at, (int, float)) and not isinstance(resets_at, bool):
            target = float(resets_at)
        else:
            return None
    except (ValueError, OverflowError, OSError):
        return None
    delta = int(target - now)
    if delta <= 0:
        return "0m"
    days, rem = divmod(delta, 86400)
    hours, rem = divmod(rem, 3600)
    minutes = rem // 60
    if days:
        return "%dd%dh" % (days, hours)
    if hours:
        return "%dh%dm" % (hours, minutes)
    return "%dm" % max(minutes, 1)


def _pct(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return "%d%%" % int(value)


def _limit_segment(label, bucket, now):
    if not isinstance(bucket, dict):
        return None
    value = bucket.get("used_percentage")
    pct = _pct(value)
    if pct is None:
        return None
    countdown = _fmt_countdown(bucket.get("resets_at"), now)
    if countdown is not None:
        text = "%s:%s(%s)" % (label, pct, countdown)
    else:
        text = "%s:%s" % (label, pct)
    return _colorize(text, value)


def _version_from_tokens(tokens, family_index):
    """Dotted version from the numeric id tokens around the family name.

    Modern ids put the version after the family (``claude-opus-4-8`` ->
    ``4.8``); legacy ids put it before (``claude-3-5-sonnet-20241022`` ->
    ``3.5``). Date-like long numbers are never part of the version.
    """
    nums = []
    for token in tokens[family_index + 1 :]:
        if token.isdigit() and len(token) < 4:
            nums.append(token)
        else:
            break
    if not nums:
        index = family_index - 1
        while index >= 0 and tokens[index].isdigit() and len(tokens[index]) < 4:
            nums.insert(0, tokens[index])
            index -= 1
    return ".".join(nums[:2])


def _model_from_id(model_id):
    if not isinstance(model_id, str) or not model_id.strip():
        return None
    tokens = model_id.strip().lower().split("-")
    for family in _MODEL_FAMILIES:
        if family in tokens:
            version = _version_from_tokens(tokens, tokens.index(family))
            if version:
                return "%s %s" % (family.capitalize(), version)
            return family.capitalize()
    return model_id.strip()[:20]


def _model_segment(payload):
    model = payload.get("model")
    if not isinstance(model, dict):
        return None
    display = model.get("display_name")
    if isinstance(display, str) and display.strip():
        text = display.strip()[:40]
    else:
        text = _model_from_id(model.get("id"))
    if text is None:
        return None
    return "%s%s%s" % (_CYAN, text, _RESET)


def _context_percent(payload):
    window = payload.get("context_window")
    if not isinstance(window, dict):
        return None
    used = window.get("used_percentage")
    if isinstance(used, (int, float)) and not isinstance(used, bool):
        return int(used)
    usage = window.get("current_usage")
    size = window.get("context_window_size")
    if (
        isinstance(usage, dict)
        and isinstance(size, (int, float))
        and not isinstance(size, bool)
        and size > 0
    ):
        total = 0
        for key in (
            "input_tokens",
            "output_tokens",
            "cache_creation_input_tokens",
            "cache_read_input_tokens",
        ):
            value = usage.get(key)
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                total += value
        return int(total * 100 / size)
    return None


def build_line(payload, now):
    segments = [time.strftime("%H:%M", time.localtime(now))]
    if not isinstance(payload, dict):
        payload = {}
    model = _model_segment(payload)
    if model is not None:
        segments.append(model)
    limits = payload.get("rate_limits")
    if isinstance(limits, dict):
        parts = []
        for label, key in (("5h", "five_hour"), ("wk", "seven_day")):
            segment = _limit_segment(label, limits.get(key), now)
            if segment is not None:
                parts.append(segment)
        if parts:
            segments.append(" ".join(parts))
    ctx = _context_percent(payload)
    if ctx is not None:
        segments.append(_colorize("ctx:%d%%" % ctx, ctx))
    return " | ".join(segments)


def main():
    try:
        reconfigure = getattr(sys.stdout, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(errors="replace")
        try:
            # Claude Code writes raw UTF-8 to the pipe; on Windows sys.stdin
            # would decode it as the locale codepage (cp949) and choke on any
            # non-ASCII payload field, so read bytes and decode explicitly.
            raw = sys.stdin.buffer.read()
            payload = json.loads(raw.decode("utf-8-sig", "replace"))
        except Exception:
            payload = {}
        line = build_line(payload, time.time())
    except Exception:
        line = time.strftime("%H:%M")
    print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
