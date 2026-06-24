#!/usr/bin/env python3
"""Stop hook: enforce the spoken end-of-turn report.

The `end-of-turn-report` rule says the main agent must speak a brief update
every time control returns to the user. That rule lived only in a skill the
agent had to *remember* to follow, so it failed intermittently. This hook
moves enforcement into the harness.

Registered under `Stop` ONLY — never `SubagentStop`. The `Stop` event fires
for the main agent's turn; `SubagentStop` fires for Agent-tool workers. The
orchestrate skill is explicit that workers must NOT speak ("Orchestrators
speak; workers do not"), so leaving `SubagentStop` unregistered means workers
are structurally never gated. No per-skill logic needed.

Logic: since the last genuine user prompt, did the assistant make a *speak-now*
run_dic call (the voice TTS tool, called WITHOUT an `output` param)? A
render-to-file call (with `output`, e.g. the `news` skill assembling a WAV)
does NOT count as a spoken report. If no speak-now call is found, block once
with a reminder.

Loop/outage safety: when the hook has already blocked once this turn, the
harness re-enters with `stop_hook_active: true`. We allow the stop in that
case, so a TTS outage (or a legitimately voiceless context) costs at most one
wasted nudge and can never wedge the session.

Fails OPEN on any parse error — a broken hook must never trap the user.
"""

from __future__ import annotations

import json
import sys

RUN_DIC = "mcp__unsandboxed-runner__run_dic"

REASON = (
    "You haven't spoken the end-of-turn report. Before ending this turn, "
    "produce the spoken update per the `end-of-turn-report` skill: call "
    f"`{RUN_DIC}` in speak-now mode (background, no `output` param) with the "
    "`<WorkingDirName>. <short phrase>.` format. "
    "Hook: ~/.claude/hooks/require-voice-report.py"
)


def _is_real_user_prompt(entry: dict) -> bool:
    """True for a genuine user turn, False for tool_result-only entries."""
    if entry.get("type") != "user":
        return False
    content = entry.get("message", {}).get("content")
    if isinstance(content, str):
        return bool(content.strip())
    if isinstance(content, list):
        has_text = any(b.get("type") == "text" for b in content if isinstance(b, dict))
        has_tool_result = any(
            b.get("type") == "tool_result" for b in content if isinstance(b, dict)
        )
        return has_text and not has_tool_result
    return False


def _is_speak_now_dic(entry: dict) -> bool:
    """True if this assistant entry calls run_dic without an `output` param."""
    if entry.get("type") != "assistant":
        return False
    content = entry.get("message", {}).get("content")
    if not isinstance(content, list):
        return False
    for block in content:
        if not isinstance(block, dict):
            continue
        if block.get("type") == "tool_use" and block.get("name") == RUN_DIC:
            inp = block.get("input") or {}
            if not inp.get("output"):  # absent/empty => speak-now
                return True
    return False


def main() -> None:
    data = json.load(sys.stdin)

    # Already blocked once this turn — allow the stop to avoid wedging on a
    # TTS outage or a voiceless context.
    if data.get("stop_hook_active"):
        return

    transcript_path = data.get("transcript_path")
    if not transcript_path:
        return

    entries: list[dict] = []
    with open(transcript_path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    # Find the most recent genuine user prompt; scan everything after it.
    last_user = -1
    for idx, entry in enumerate(entries):
        if _is_real_user_prompt(entry):
            last_user = idx

    spoke = any(_is_speak_now_dic(e) for e in entries[last_user + 1 :])
    if spoke:
        return

    print(json.dumps({"decision": "block", "reason": REASON}))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        # Fail open: never trap the user behind a broken hook.
        pass
