#!/usr/bin/env python3
"""Promote negative-feedback traces to eval cases.

Scans trace files for entries with user-feedback score == -1,
presents each candidate to the user, and on approval writes a new
eval case YAML file.

Self-contained: requires only stdlib + PyYAML.

Usage:
  python scripts/promote_trace.py --days 7
  python scripts/promote_trace.py --days 1 --trace-dir /path/to/traces
"""

import argparse
import datetime
import json
import os
import pathlib
import re
import sys

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML required. Install with: pip install pyyaml", file=sys.stderr)
    sys.exit(1)


def find_trace_dirs(trace_root: pathlib.Path, days: int) -> list[pathlib.Path]:
    """Find trace directories within the last N days."""
    dirs = []
    today = datetime.date.today()
    for d in range(days):
        date = today - datetime.timedelta(days=d)
        date_dir = trace_root / date.isoformat()
        if date_dir.is_dir():
            dirs.append(date_dir)
    return dirs


def load_traces_with_negative_feedback(trace_dirs: list[pathlib.Path]) -> list[dict]:
    """Load trace entries that have user-feedback score == -1."""
    candidates = []

    for trace_dir in trace_dirs:
        for jsonl_file in sorted(trace_dir.glob("*.jsonl")):
            entries = []
            with open(jsonl_file, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue

            # Only check the LAST entry per session for feedback (avoid re-promoting stale history)
            if not entries:
                continue

            # Find the original user input from the first UserPromptSubmit or session_start
            original_input = ""
            original_command = "unknown"
            for entry in entries:
                evt = entry.get("hook_event_name", "")
                if evt in ("session_start", "UserPromptSubmit"):
                    tool_input = entry.get("tool_input", {})
                    if isinstance(tool_input, dict):
                        original_input = tool_input.get("message", tool_input.get("user_message", ""))
                    elif isinstance(tool_input, str):
                        original_input = tool_input
                if entry.get("ezpowers.command"):
                    original_command = entry["ezpowers.command"]

            last_entry = entries[-1]
            scores = last_entry.get("scores", [])
            for score in scores:
                if (score.get("name") == "user-feedback"
                        and score.get("value") == -1):
                    candidates.append({
                        "file": str(jsonl_file),
                        "session_id": last_entry.get("session_id", "unknown"),
                        "trace_id": last_entry.get("trace_id", "unknown"),
                        "command": original_command,
                        "comment": score.get("comment", ""),
                        "timestamp": last_entry.get("start_time_unix_ns", ""),
                        "original_input": original_input,
                        "hook_event": last_entry.get("hook_event_name", ""),
                    })

    return candidates


def slugify(text: str) -> str:
    """Convert text to a filesystem-safe slug."""
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_]+', '-', text)
    text = re.sub(r'-+', '-', text)
    return text[:50].rstrip('-')


def prompt_user(prompt: str, valid: set[str]) -> str:
    """Prompt user for input, validate against valid set."""
    while True:
        response = input(prompt).strip().lower()
        if response in valid:
            return response
        print(f"  Valid options: {', '.join(sorted(valid))}")


def display_candidate(idx: int, total: int, candidate: dict):
    """Display a candidate trace for user review."""
    print(f"\n{'=' * 60}")
    print(f"Candidate {idx}/{total}")
    print(f"{'=' * 60}")
    print(f"  Session:   {candidate['session_id']}")
    print(f"  Command:   {candidate['command']}")
    print(f"  Comment:   {candidate['comment']}")
    print(f"  File:      {candidate['file']}")
    print(f"  Event:     {candidate['hook_event']}")


def build_case_yaml(candidate: dict, split: str, strata: dict,
                    case_seq: int) -> dict:
    """Build eval case dict from a candidate trace."""
    command = candidate["command"]
    slug = slugify(candidate["comment"]) if candidate["comment"] else f"trace-{candidate['session_id'][:8]}"
    case_id = f"{split}.{slug.replace('-', '_')}.{case_seq:03d}"

    # Use original user input as the eval case input, not the feedback comment
    user_message = candidate.get("original_input", "")
    if not user_message:
        user_message = candidate["comment"] or "See trace for context"

    case = {
        "case_id": case_id,
        "split": split,
        "stratum": {
            "command": command,
            "pattern": "trace_promoted",
            **strata,
        },
        "input": {
            "user_message": user_message,
            "initial_files": [],
            "source_trace": {
                "trace_id": candidate["trace_id"],
                "session_id": candidate["session_id"],
                "file": candidate["file"],
                "feedback_comment": candidate["comment"],
            },
        },
        "graders": [
            {
                "type": "deterministic_tests",
                "commands": [
                    "echo 'TODO: add grader commands for this case'",
                ],
            },
        ],
        "tracked_metrics": {
            "transcript": ["n_turns", "n_toolcalls", "n_total_tokens"],
        },
    }
    return case


def write_case_file(case: dict, evals_root: pathlib.Path) -> pathlib.Path:
    """Write case YAML to the appropriate directory."""
    split = case["split"]
    command = case["stratum"].get("command", "unknown")

    out_dir = evals_root / split / command
    out_dir.mkdir(parents=True, exist_ok=True)

    slug = case["case_id"].split(".")[1]
    out_path = out_dir / f"{slug}.yaml"

    # Avoid overwriting
    counter = 1
    while out_path.exists():
        out_path = out_dir / f"{slug}-{counter}.yaml"
        counter += 1

    with open(out_path, "w", encoding="utf-8") as f:
        yaml.dump(case, f, default_flow_style=False, allow_unicode=True,
                  sort_keys=False, width=120)

    return out_path


def main():
    parser = argparse.ArgumentParser(
        description="Promote negative-feedback traces to eval cases."
    )
    parser.add_argument("--days", type=int, default=7,
                        help="Look back N days for traces (default: 7)")
    parser.add_argument("--trace-dir", default=None,
                        help="Trace root directory (default: $CLAUDE_PLUGIN_DATA/traces)")
    parser.add_argument("--evals-root", default="evals",
                        help="Root directory for eval cases (default: evals)")

    args = parser.parse_args()

    # Resolve trace directory
    if args.trace_dir:
        trace_root = pathlib.Path(args.trace_dir)
    else:
        plugin_data = os.environ.get("CLAUDE_PLUGIN_DATA", "")
        if not plugin_data:
            print("ERROR: $CLAUDE_PLUGIN_DATA not set and --trace-dir not provided.",
                  file=sys.stderr)
            sys.exit(1)
        trace_root = pathlib.Path(plugin_data) / "traces"

    if not trace_root.is_dir():
        print(f"ERROR: trace directory not found: {trace_root}", file=sys.stderr)
        sys.exit(1)

    evals_root = pathlib.Path(args.evals_root)

    # Find candidates
    trace_dirs = find_trace_dirs(trace_root, args.days)
    if not trace_dirs:
        print(f"No trace directories found in last {args.days} days.")
        return

    candidates = load_traces_with_negative_feedback(trace_dirs)
    if not candidates:
        print(f"No negative-feedback traces found in last {args.days} days.")
        return

    print(f"Found {len(candidates)} negative-feedback trace(s).\n")

    promoted = 0
    for i, candidate in enumerate(candidates, 1):
        display_candidate(i, len(candidates), candidate)

        choice = prompt_user(
            "  Promote to eval case? [y/n/q(uit)] ",
            {"y", "n", "q"},
        )

        if choice == "q":
            break
        if choice == "n":
            continue

        # Ask for split
        split = prompt_user(
            "  Split [optimization/holdout] (default: optimization): ",
            {"optimization", "holdout", "o", "h", ""},
        )
        split_map = {"o": "optimization", "h": "holdout", "": "optimization"}
        split = split_map.get(split, split)

        # Ask for difficulty stratum
        difficulty = prompt_user(
            "  Difficulty [single_step/multi_step/long_horizon] (default: multi_step): ",
            {"single_step", "multi_step", "long_horizon", "s", "m", "l", ""},
        )
        diff_map = {"s": "single_step", "m": "multi_step", "l": "long_horizon",
                     "": "multi_step"}
        difficulty = diff_map.get(difficulty, difficulty)

        # Ask for language
        language = prompt_user(
            "  Language [ko/en/ko_en_mixed] (default: ko_en_mixed): ",
            {"ko", "en", "ko_en_mixed", ""},
        )
        if not language:
            language = "ko_en_mixed"

        strata = {
            "difficulty": difficulty,
            "model_family": "agnostic",
            "language": language,
        }

        # Find next sequence number
        existing = list(evals_root.rglob("*.yaml"))
        seq = len(existing) + 1

        case = build_case_yaml(candidate, split, strata, seq)
        out_path = write_case_file(case, evals_root)

        print(f"  Written: {out_path}")
        print(f"  Case ID: {case['case_id']}")
        print(f"  -> Edit graders in {out_path} to add actual test commands.")
        promoted += 1

    print(f"\nDone. Promoted {promoted} trace(s) to eval cases.")


if __name__ == "__main__":
    main()
