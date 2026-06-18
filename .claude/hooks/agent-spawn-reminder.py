#!/usr/bin/env python3
"""PreToolUse hook on Agent: inject orchestrate + notification-reading reminders.

Fires before every Agent tool call. Surfaces two rules the orchestrator needs
at the moment of the spawn:

1. Consult the `orchestrate` skill for the briefing checklist.
2. When the spawn's task-notification arrives, `status: completed` is not
   necessarily terminal — interim snapshots fire it too. Verify the artifact,
   not the notification text.
"""

import json
import sys

CONTEXT = (
    "Agent spawn checkpoint. The `orchestrate` skill governs both ends of this spawn — composing the briefing and reading the response. Two rules that bite at this moment:\n"
    "\n"
    "1. **Brief per the orchestrate checklist.** Goal, scope, return format, skills/scripts/MCP tools the worker should reach for, inherited project rules, silence clause. Workers inherit no MEMENTO, no skills index, no conversation context — anything they need has to be named in the prompt. If you haven't consulted `orchestrate` this turn, do so before composing this spawn.\n"
    "\n"
    "2. **Reading the response.** When the task-notification for this spawn arrives, `status: completed` is NOT necessarily terminal — the harness fires that event whenever the worker emits new output. Interim snapshots with sentence-fragment tails ('Let me wait...', 'Good. Let me...', 'File hasn't been written in...') look terminal but aren't. Only a notification whose `result` matches the structured return format you required in the briefing (## Summary, ## Files changed, etc.) is terminal. When unsure, verify the artifact (git log, tree state, file written), not the notification text. Treating an interim snapshot as terminal triggers premature escalation — a real failure mode."
)


def main() -> int:
    sys.stdin.read()  # drain hook input JSON; we don't need it
    output = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "additionalContext": CONTEXT,
        }
    }
    print(json.dumps(output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
