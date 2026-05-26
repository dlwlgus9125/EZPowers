---
description: Attach user scores to session traces
allowed-tools: [Bash, Read, Write, Agent]
---

# /feedback — Attach User Scores to Session Traces

Record user feedback (score + comment) on the current session's trace. Can be invoked independently at any time.
Successful writes finish through the reviewer placement gate.

<HARD-GATE>
Do not record feedback if no trace file exists. Trace collection must be enabled first via `/setup --enable-traces`.
</HARD-GATE>

## Anti-Pattern: "I'll batch feedback later"

Feedback is most accurate immediately after a session. Memory of what worked and what didn't fades over time. Call `/feedback` right at session end.

## Usage

```
/feedback +1                # Attach positive score to last session
/feedback +1 "spec was clear"  # Positive score + comment
/feedback -1 "repeated unnecessary questions"  # Negative score + comment
/feedback last "additional note"      # Comment only, no score
```

## Process Flow

```
Parse arguments (score, comment)
  -> Locate trace directory
  -> Identify latest trace file
  -> Append feedback to last entry's scores array
  -> Save
  -> Report result
```

## 1. Trace File Location

Trace storage: `${CLAUDE_PLUGIN_DATA}/traces/`

Search order:
1. Today's date directory: `traces/$(date +%Y-%m-%d)/`
2. Most recently modified `.jsonl` file in that directory
3. If today's directory is empty, fall back to yesterday
4. If no trace file found:

```
No trace file found.
Enable trace collection with `/setup --enable-traces`, then run a session.
```

## 2. Feedback Recording

### 2-1. Score Format

Compatible with Langfuse `create_score` schema:

```jsonc
{
  "name": "user-feedback",
  "value": 1,          // +1 or -1
  "comment": "spec was clear",
  "source": "user",
  "timestamp": "2026-04-25T14:30:00Z"
}
```

### 2-2. `/feedback +1` or `/feedback -1 "reason"`

Read the **last JSONL entry** of the trace file and append the feedback object to the `scores` array.

Create the `scores` array if it doesn't exist:
```jsonc
// before
{"trace_id": "...", "hook_event_name": "Stop", "scores": []}

// after
{"trace_id": "...", "hook_event_name": "Stop", "scores": [
  {"name": "user-feedback", "value": 1, "comment": "spec was clear", "source": "user", "timestamp": "2026-04-25T14:30:00Z"}
]}
```

### 2-3. `/feedback last "comment"`

Attach comment only, no score. Set `value` to `null`:

```jsonc
{"name": "user-feedback", "value": null, "comment": "additional note", "source": "user", "timestamp": "..."}
```

## 3. Output

Report concisely after recording:

```
Feedback recorded.
  Trace: traces/2026-04-25/session-abc123.jsonl
  Session: abc123
  Score: +1
  Comment: "spec was clear"
```

Omit the comment line if no comment.

## 4. Feedback → Eval Case Promotion

On `-1` feedback, show promotion guidance:

```
To register this failure pattern as an eval case:
  python scripts/promote_trace.py --days 1
```

## Verification

- After `/feedback +1 "test"`, confirm the last trace entry has a score appended
- Running `/feedback +1` with no trace file outputs the guidance message

## Common Rationalizations

| Rationalization | Why It Doesn't Work |
|----------------|---------------------|
| "Can I just record feedback in a separate file without traces?" | Feedback separated from traces cannot be linked to specific interactions. |
| "Binary +1/-1 doesn't capture nuance" | The comment field captures nuance. Score is for filtering. |
