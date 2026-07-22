#!/usr/bin/env python3
"""EZPowers statusline HUD for Claude Code.

Reads the statusLine JSON payload Claude Code pipes to stdin and prints one
ASCII line for the CLI footer:

    14:32 | 5h:12%(2h10m) wk:26%(2d5h) | ctx:34%

Segments render only when their payload fields are present (API-key sessions
have no rate_limits, so they show time + ctx only). On any parse error the
script prints the local time and exits 0 -- a statusline must never crash or
write stderr. Installed by /setup as `.harness/ezpowers/statusline.py`; that
path substring is the EZPowers ownership marker in settings.json. Standard
library only: this file is copied alone into target projects by harness-kit.
"""

from __future__ import annotations

import json
import sys
import time
from datetime import datetime


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
    pct = _pct(bucket.get("used_percentage"))
    if pct is None:
        return None
    countdown = _fmt_countdown(bucket.get("resets_at"), now)
    if countdown is not None:
        return "%s:%s(%s)" % (label, pct, countdown)
    return "%s:%s" % (label, pct)


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
        segments.append("ctx:%d%%" % ctx)
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
