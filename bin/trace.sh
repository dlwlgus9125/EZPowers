#!/usr/bin/env bash
# EZPowers trace collector — observation-only, append-only JSONL.
# Called by hooks/hooks.json. Must NEVER modify model behavior.
#
# Usage: echo '{"session_id":"...","tool_name":"Edit",...}' | trace.sh <event_type>
#   event_type: session_start | post_tool | stop | session_end
#
# Output: appends one OTel-compatible JSON line per invocation to
#   ${CLAUDE_PLUGIN_DATA}/traces/<YYYY-MM-DD>/<session_id>.jsonl
#
# Exit: always 0 — never blocks Claude Code.

EVENT_TYPE="${1:-unknown}"
HOOK_TIER="${2:-reporting}"
FAIL_CLOSED="${3:-false}"
TRACE_BASE="${CLAUDE_PLUGIN_DATA:-$HOME/.ezpowers-traces}"
TRACE_DIR="$TRACE_BASE/traces"

# Check python3 availability (required for JSON parsing)
if ! command -v python3 &>/dev/null; then
    echo "WARN: python3 not found — trace dropped for event=$EVENT_TYPE" >&2
    exit 0
fi

# Save stdin to a temp file (safe for arbitrary JSON)
TMPFILE="$(mktemp)"
trap 'rm -f "$TMPFILE"' EXIT
cat > "$TMPFILE"

# Extract session_id; fall back to "unknown" if missing
SESSION_ID="$(python3 -c "
import json, sys
try:
    d = json.load(open(sys.argv[1]))
    print(d.get('session_id', d.get('sessionId', 'unknown')))
except Exception:
    print('unknown')
" "$TMPFILE" 2>/dev/null || echo "unknown")"

# Build date-partitioned directory
DATE_DIR="$TRACE_DIR/$(date +%Y-%m-%d)"
mkdir -p "$DATE_DIR"

OUTFILE="$DATE_DIR/${SESSION_ID}.jsonl"

# Build OTel-compatible trace line and append
python3 -c "
import json, time, uuid, re, sys

try:
    hook_input = json.load(open(sys.argv[1]))
except Exception:
    hook_input = {}

event = sys.argv[2]
tier = sys.argv[3]
fail_closed = sys.argv[4].lower() == 'true'
now_ns = int(time.time() * 1_000_000_000)

line = {
    'trace_id': hook_input.get('trace_id', uuid.uuid4().hex[:16]),
    'span_id': uuid.uuid4().hex[:16],
    'session_id': hook_input.get('session_id', hook_input.get('sessionId', 'unknown')),
    'turn_id': hook_input.get('turn_id', hook_input.get('turnId', None)),
    'hook_event_name': event,
    'ezpowers.hook_tier': tier,
    'ezpowers.fail_closed': fail_closed,
    'tool_name': hook_input.get('tool_name', hook_input.get('toolName', None)),
    'tool_input': hook_input.get('tool_input', hook_input.get('toolInput', None)),
    'tool_use_id': hook_input.get('tool_use_id', hook_input.get('toolUseId', None)),
    'gen_ai.system': 'anthropic',
    'gen_ai.request.model': hook_input.get('model', None),
    'gen_ai.usage.input_tokens': hook_input.get('input_tokens', hook_input.get('inputTokens', None)),
    'gen_ai.usage.output_tokens': hook_input.get('output_tokens', hook_input.get('outputTokens', None)),
    'ezpowers.command': hook_input.get('command', None),
    'ezpowers.verdict': None,
    'ezpowers.banned_expression_hits': None,
    'scores': [],
    'labels': [],
    'start_time_unix_ns': now_ns,
    'end_time_unix_ns': now_ns,
    'status': 'OK'
}

# For stop events, attempt to extract verdict from hook input
if event == 'stop':
    verdict = hook_input.get('verdict', hook_input.get('output', ''))
    if isinstance(verdict, str):
        m = re.search(r'## Verdict:\s*(PASS|FAIL)', verdict)
        if m:
            line['ezpowers.verdict'] = m.group(1)

# Strip None values to keep JSONL compact
line = {k: v for k, v in line.items() if v is not None}

print(json.dumps(line, ensure_ascii=False))
" "$TMPFILE" "$EVENT_TYPE" "$HOOK_TIER" "$FAIL_CLOSED" >> "$OUTFILE" 2>/dev/null

exit 0
