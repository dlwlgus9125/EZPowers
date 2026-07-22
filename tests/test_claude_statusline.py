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
STATUSLINE = REPO_ROOT / "scripts" / "claude-statusline.py"

_spec = importlib.util.spec_from_file_location("ezp_claude_statusline", STATUSLINE)
statusline = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(statusline)

FULL_LINE_RE = re.compile(r"^\d{2}:\d{2} \| 5h:\d+%\(\S+\) wk:\d+%\(\S+\) \| ctx:\d+%$")
MODEL_LINE_RE = re.compile(
    r"^\d{2}:\d{2} \| Fable 5 \| 5h:\d+%\(\S+\) wk:\d+%\(\S+\) \| ctx:\d+%$"
)
TIME_ONLY_RE = re.compile(r"^\d{2}:\d{2}$")
ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")

GREEN = "\x1b[32m"
YELLOW = "\x1b[33m"
RED = "\x1b[31m"
CYAN = "\x1b[36m"
RESET = "\x1b[0m"


def _strip_ansi(text: str) -> str:
    return ANSI_RE.sub("", text)


def _green(text: str) -> str:
    return f"{GREEN}{text}{RESET}"


def _cyan(text: str) -> str:
    return f"{CYAN}{text}{RESET}"

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
        self.assertEqual(
            line,
            f"{HHMM} | {_green('5h:12%(2h10m)')} {_green('wk:26%(2d5h)')} | {_green('ctx:34%')}",
        )

    def test_missing_rate_limits_degrades_to_time_and_ctx(self):
        payload = _full_payload(NOW)
        del payload["rate_limits"]
        self.assertEqual(statusline.build_line(payload, NOW), f"{HHMM} | {_green('ctx:34%')}")

    def test_empty_payload_renders_time_only(self):
        self.assertEqual(statusline.build_line({}, NOW), HHMM)

    def test_non_dict_payload_renders_time_only(self):
        self.assertEqual(statusline.build_line(["nonsense"], NOW), HHMM)

    def test_missing_resets_at_omits_countdown(self):
        payload = {"rate_limits": {"five_hour": {"used_percentage": 7}}}
        self.assertEqual(statusline.build_line(payload, NOW), f"{HHMM} | {_green('5h:7%')}")

    def test_iso_resets_at_is_accepted(self):
        iso = datetime.fromtimestamp(NOW + 2 * 3600 + 10 * 60 + 30).isoformat()
        payload = {"rate_limits": {"five_hour": {"used_percentage": 7, "resets_at": iso}}}
        self.assertEqual(statusline.build_line(payload, NOW), f"{HHMM} | {_green('5h:7%(2h10m)')}")

    def test_past_resets_at_renders_zero_minutes(self):
        payload = {"rate_limits": {"five_hour": {"used_percentage": 99, "resets_at": NOW - 60}}}
        self.assertEqual(statusline.build_line(payload, NOW), f"{HHMM} | {RED}5h:99%(0m){RESET}")

    def test_sub_hour_countdown(self):
        payload = {"rate_limits": {"five_hour": {"used_percentage": 1, "resets_at": NOW + 45 * 60}}}
        self.assertEqual(statusline.build_line(payload, NOW), f"{HHMM} | {_green('5h:1%(45m)')}")

    def test_sub_minute_countdown_rounds_up(self):
        payload = {"rate_limits": {"five_hour": {"used_percentage": 1, "resets_at": NOW + 30}}}
        self.assertEqual(statusline.build_line(payload, NOW), f"{HHMM} | {_green('5h:1%(1m)')}")

    def test_threshold_colors(self):
        for pct, color in ((69, GREEN), (70, YELLOW), (89, YELLOW), (90, RED)):
            payload = {"context_window": {"used_percentage": pct}}
            self.assertEqual(
                statusline.build_line(payload, NOW),
                f"{HHMM} | {color}ctx:{pct}%{RESET}",
            )

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
        self.assertEqual(statusline.build_line(payload, NOW), f"{HHMM} | {_green('ctx:7%')}")


class ModelSegmentTests(unittest.TestCase):
    def test_display_name_is_preferred_and_cyan(self):
        payload = _full_payload(NOW)
        payload["model"] = {"id": "claude-fable-5", "display_name": "Fable 5"}
        line = statusline.build_line(payload, NOW)
        self.assertEqual(
            line,
            f"{HHMM} | {_cyan('Fable 5')} | "
            f"{_green('5h:12%(2h10m)')} {_green('wk:26%(2d5h)')} | {_green('ctx:34%')}",
        )

    def test_model_only_payload_renders_time_and_model(self):
        payload = {"model": {"display_name": "Opus 4.8"}}
        self.assertEqual(statusline.build_line(payload, NOW), f"{HHMM} | {_cyan('Opus 4.8')}")

    def test_blank_display_name_falls_back_to_id(self):
        payload = {"model": {"id": "claude-opus-4-8", "display_name": "  "}}
        self.assertEqual(statusline.build_line(payload, NOW), f"{HHMM} | {_cyan('Opus 4.8')}")

    def test_id_version_after_family(self):
        self.assertEqual(statusline._model_from_id("claude-opus-4-8"), "Opus 4.8")

    def test_id_version_before_family_legacy(self):
        self.assertEqual(statusline._model_from_id("claude-3-5-sonnet-20241022"), "Sonnet 3.5")

    def test_id_version_ignores_date_suffix(self):
        self.assertEqual(statusline._model_from_id("claude-haiku-4-5-20251001"), "Haiku 4.5")

    def test_id_single_component_version(self):
        self.assertEqual(statusline._model_from_id("claude-fable-5"), "Fable 5")

    def test_unrecognized_id_is_truncated_verbatim(self):
        self.assertEqual(
            statusline._model_from_id("some-experimental-model-id-that-runs-long"),
            "some-experimental-mo",
        )

    def test_missing_or_malformed_model_omits_segment(self):
        for model in (None, "claude-opus-4-8", {}, {"id": 42}, {"display_name": ""}):
            payload = {"context_window": {"used_percentage": 34}}
            if model is not None:
                payload["model"] = model
            self.assertEqual(
                statusline.build_line(payload, NOW),
                f"{HHMM} | {_green('ctx:34%')}",
                model,
            )


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
        self.assertIn(GREEN, line)
        self.assertRegex(_strip_ansi(line), FULL_LINE_RE)

    def test_model_payload_end_to_end(self):
        payload = _full_payload(time.time())
        payload["model"] = {"id": "claude-fable-5", "display_name": "Fable 5"}
        proc = self._run(json.dumps(payload).encode("utf-8"))
        self.assertEqual(proc.returncode, 0)
        self.assertEqual(proc.stderr, b"")
        line = proc.stdout.decode("utf-8").strip()
        self.assertIn(CYAN, line)
        self.assertRegex(_strip_ansi(line), MODEL_LINE_RE)

    def test_non_ascii_payload_survives_windows_pipe_decoding(self):
        """Claude Code pipes raw UTF-8; payloads carry non-ASCII fields such as
        Korean session names. The script must not fall back to time-only just
        because the locale codepage cannot decode the bytes."""
        payload = _full_payload(time.time())
        payload["session_name"] = "CLI 하단 표시줄"
        proc = self._run(json.dumps(payload, ensure_ascii=False).encode("utf-8"))
        self.assertEqual(proc.returncode, 0)
        self.assertRegex(_strip_ansi(proc.stdout.decode("utf-8").strip()), FULL_LINE_RE)

    def test_bom_prefixed_payload_is_parsed(self):
        payload = _full_payload(time.time())
        proc = self._run(b"\xef\xbb\xbf" + json.dumps(payload).encode("utf-8"))
        self.assertEqual(proc.returncode, 0)
        self.assertRegex(_strip_ansi(proc.stdout.decode("utf-8").strip()), FULL_LINE_RE)

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
        """The statusline runs from the installed plugin copy via a user-owned
        launcher; copying it alone into an empty directory and running it there
        proves it depends only on the standard library."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = pathlib.Path(tmp)
            isolated = tmp_dir / "claude-statusline.py"
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
