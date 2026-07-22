import importlib.util
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from datetime import datetime


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
STATUSLINE = REPO_ROOT / "scripts" / "statusline.py"

_spec = importlib.util.spec_from_file_location("ezp_statusline", STATUSLINE)
statusline = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(statusline)

FULL_LINE_RE = re.compile(r"^\d{2}:\d{2} \| 5h:\d+%\(\S+\) wk:\d+%\(\S+\) \| ctx:\d+%$")
TIME_ONLY_RE = re.compile(r"^\d{2}:\d{2}$")

NOW = 1784500000.0
HHMM = time.strftime("%H:%M", time.localtime(NOW))


def _clean_env() -> dict:
    """Environment with PYTHONPATH stripped so the repo's scripts/ cannot leak
    siblings onto sys.path during the isolation proof."""
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)
    return env


def _full_payload(now: float) -> dict:
    return {
        "session_name": "sample",
        "rate_limits": {
            "five_hour": {"used_percentage": 12, "resets_at": now + 2 * 3600 + 10 * 60 + 30},
            "seven_day": {"used_percentage": 26, "resets_at": now + 2 * 86400 + 5 * 3600 + 90},
        },
        "context_window": {"used_percentage": 34},
    }


class BuildLineTests(unittest.TestCase):
    def test_full_payload_renders_all_segments(self):
        line = statusline.build_line(_full_payload(NOW), NOW)
        self.assertEqual(line, f"{HHMM} | 5h:12%(2h10m) wk:26%(2d5h) | ctx:34%")

    def test_missing_rate_limits_degrades_to_time_and_ctx(self):
        payload = _full_payload(NOW)
        del payload["rate_limits"]
        self.assertEqual(statusline.build_line(payload, NOW), f"{HHMM} | ctx:34%")

    def test_empty_payload_renders_time_only(self):
        self.assertEqual(statusline.build_line({}, NOW), HHMM)

    def test_non_dict_payload_renders_time_only(self):
        self.assertEqual(statusline.build_line(["nonsense"], NOW), HHMM)

    def test_missing_resets_at_omits_countdown(self):
        payload = {"rate_limits": {"five_hour": {"used_percentage": 7}}}
        self.assertEqual(statusline.build_line(payload, NOW), f"{HHMM} | 5h:7%")

    def test_iso_resets_at_is_accepted(self):
        iso = datetime.fromtimestamp(NOW + 2 * 3600 + 10 * 60 + 30).isoformat()
        payload = {"rate_limits": {"five_hour": {"used_percentage": 7, "resets_at": iso}}}
        self.assertEqual(statusline.build_line(payload, NOW), f"{HHMM} | 5h:7%(2h10m)")

    def test_past_resets_at_renders_zero_minutes(self):
        payload = {"rate_limits": {"five_hour": {"used_percentage": 99, "resets_at": NOW - 60}}}
        self.assertEqual(statusline.build_line(payload, NOW), f"{HHMM} | 5h:99%(0m)")

    def test_sub_hour_countdown(self):
        payload = {"rate_limits": {"five_hour": {"used_percentage": 1, "resets_at": NOW + 45 * 60}}}
        self.assertEqual(statusline.build_line(payload, NOW), f"{HHMM} | 5h:1%(45m)")

    def test_sub_minute_countdown_rounds_up(self):
        payload = {"rate_limits": {"five_hour": {"used_percentage": 1, "resets_at": NOW + 30}}}
        self.assertEqual(statusline.build_line(payload, NOW), f"{HHMM} | 5h:1%(1m)")

    def test_ctx_computed_from_tokens_when_percentage_missing(self):
        payload = {
            "context_window": {
                "context_window_size": 1000000,
                "current_usage": {
                    "input_tokens": 2,
                    "output_tokens": 4998,
                    "cache_creation_input_tokens": 20000,
                    "cache_read_input_tokens": 45000,
                },
            }
        }
        self.assertEqual(statusline.build_line(payload, NOW), f"{HHMM} | ctx:7%")


class StatuslineProcessTests(unittest.TestCase):
    def _run(self, stdin_bytes: bytes) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(STATUSLINE)],
            input=stdin_bytes,
            capture_output=True,
            cwd=REPO_ROOT,
            check=False,
        )

    def test_full_payload_end_to_end(self):
        proc = self._run(json.dumps(_full_payload(time.time())).encode("utf-8"))
        self.assertEqual(proc.returncode, 0)
        self.assertEqual(proc.stderr, b"")
        line = proc.stdout.decode("utf-8").strip()
        self.assertRegex(line, FULL_LINE_RE)

    def test_non_ascii_payload_survives_windows_pipe_decoding(self):
        """Claude Code pipes raw UTF-8; payloads carry non-ASCII fields such as
        Korean session names. The script must not fall back to time-only just
        because the locale codepage cannot decode the bytes."""
        payload = _full_payload(time.time())
        payload["session_name"] = "CLI 하단 표시줄"
        proc = self._run(json.dumps(payload, ensure_ascii=False).encode("utf-8"))
        self.assertEqual(proc.returncode, 0)
        self.assertRegex(proc.stdout.decode("utf-8").strip(), FULL_LINE_RE)

    def test_bom_prefixed_payload_is_parsed(self):
        payload = _full_payload(time.time())
        proc = self._run(b"\xef\xbb\xbf" + json.dumps(payload).encode("utf-8"))
        self.assertEqual(proc.returncode, 0)
        self.assertRegex(proc.stdout.decode("utf-8").strip(), FULL_LINE_RE)

    def test_malformed_stdin_renders_time_only(self):
        proc = self._run(b"not json")
        self.assertEqual(proc.returncode, 0)
        self.assertEqual(proc.stderr, b"")
        self.assertRegex(proc.stdout.decode("utf-8").strip(), TIME_ONLY_RE)

    def test_empty_stdin_renders_time_only(self):
        proc = self._run(b"")
        self.assertEqual(proc.returncode, 0)
        self.assertRegex(proc.stdout.decode("utf-8").strip(), TIME_ONLY_RE)


class StatuslineSelfContainedTests(unittest.TestCase):
    def test_runs_without_sibling_scripts(self):
        """statusline.py is installed alone into target projects as
        .harness/ezpowers/statusline.py; copying it into an empty directory and
        running it there proves it uses only the standard library."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = pathlib.Path(tmp)
            isolated = tmp_dir / "statusline.py"
            shutil.copy(STATUSLINE, isolated)

            proc = subprocess.run(
                [sys.executable, str(isolated)],
                input=b"{}",
                capture_output=True,
                cwd=tmp,
                env=_clean_env(),
                check=False,
            )

            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertNotIn(b"ImportError", proc.stderr)
            self.assertNotIn(b"ModuleNotFoundError", proc.stderr)
            self.assertRegex(proc.stdout.decode("utf-8").strip(), TIME_ONLY_RE)


if __name__ == "__main__":
    unittest.main()
