#!/usr/bin/env python3
"""PreToolUse hook on Bash: nudge App Store Connect work through the `asc` skill.

The `asc` skill owns every App Store Connect operation — the JWT-authed REST
client, the endpoint cookbook, the credential resolution, and the safety rails
(destructive-op gating, secret redaction). Its description already fires on any
ASC/TestFlight/provisioning/IAP task, but that rule lives in a skill the main
agent has to *remember* to consult; a quick hand-rolled `curl` to
api.appstoreconnect.apple.com, a raw `xcrun notarytool` call, or invoking the
client without reading its cookbook shortcuts the skill's auth handling and
safety rails.

This hook fires when a Bash command clearly touches App Store Connect and no
`asc` skill was consulted since the last user prompt, and injects a
non-blocking reminder to route through it. It is the ASC-domain sibling of
`route-dev-work.py` / `route-config-work.py`.

Non-blocking by design: injects `additionalContext`, never denies. (The hard
gate for a *destructive* asc operation is `asc-destructive-gate.py`; this is the
softer "did you go through the skill at all" nudge.)

Fires only when ALL hold:
  1. Tool is Bash.
  2. The command matches an unambiguous App Store Connect signal (the `asc`
     client, the ASC API host, or the notarization/upload toolchain).
  3. This is the MAIN session, not a subagent (`/tasks/` transcript path or an
     `agent-setting` entry exempts workers).
  4. No `asc` skill was invoked since the last genuine user prompt.

Fails OPEN on any error — a broken hook must never trap the user.
"""

from __future__ import annotations

import json
import os
import re
import sys

ASC_FAMILY = ("asc",)

# Unambiguous App Store Connect signals in a shell command. Kept deliberately
# tight to avoid nagging on unrelated commands: the ASC API host, the notarize/
# upload toolchain, the credentials dir, and the `asc` client invoked as a
# command (bare, after a separator, after `just`, or as a path tail — never a
# bare substring like "ascii"/"cascade").
ASC_PATTERNS = (
    re.compile(r"appstoreconnect", re.IGNORECASE),
    re.compile(r"\bnotarytool\b", re.IGNORECASE),
    re.compile(r"\baltool\b", re.IGNORECASE),
    re.compile(r"\biTMSTransporter\b", re.IGNORECASE),
    re.compile(r"\bxcrun\s+stapler\b", re.IGNORECASE),
    re.compile(r"\bmas-upload(?:\.sh)?\b"),
    re.compile(r"(?:^|[;&|(]\s*|\bjust\s+|/)asc\b"),
)

CONTEXT = (
    "ASC-routing checkpoint. This command touches App Store Connect, and no `asc` "
    "skill is active since the last user message.\n"
    "\n"
    "Route App Store Connect work through the `asc` skill FIRST. It owns the HOW — "
    "the ES256-JWT-authed REST client at `~/.agents/skills/asc/scripts/asc`, the "
    "endpoint cookbook (profiles, TestFlight groups/builds, IAP create/localize/"
    "price/availability/screenshot, export compliance, build-wait), credential "
    "resolution, secret redaction, and the destructive-op gate. Hand-rolled `curl`/"
    "`xcrun`/JWT calls skip all of that. A project owns only the WHEN: invoke the "
    "skill's client with this app's own IDs; do not re-implement it.\n"
    "\n"
    "Proceed with this command directly ONLY if (a) the `asc` skill is already "
    "active, (b) the user told you to run this exact command, or (c) it isn't "
    "really an ASC operation. Otherwise consult `asc` now.\n"
    "\n"
    "Hook: ~/.claude/hooks/route-asc-work.py"
)

WRAPPER_PREFIXES = (
    "<task-notification",
    "<system-reminder",
    "<local-command-stdout",
    "<local-command-stderr",
    "<local-command-caveat",
    "<command-name",
    "<command-message",
    "<command-args",
)


def _is_wrapper_text(text: str) -> bool:
    stripped = text.lstrip()
    if not stripped:
        return True
    return stripped.startswith(WRAPPER_PREFIXES)


def _is_real_user_prompt(entry: dict) -> bool:
    if entry.get("type") != "user":
        return False
    content = entry.get("message", {}).get("content")
    if isinstance(content, str):
        return not _is_wrapper_text(content)
    if isinstance(content, list):
        has_tool_result = any(
            b.get("type") == "tool_result" for b in content if isinstance(b, dict)
        )
        if has_tool_result:
            return False
        return any(
            b.get("type") == "text" and not _is_wrapper_text(b.get("text", ""))
            for b in content
            if isinstance(b, dict)
        )
    return False


def _invokes_asc_family(entry: dict) -> bool:
    if entry.get("type") != "assistant":
        return False
    content = entry.get("message", {}).get("content")
    if not isinstance(content, list):
        return False
    for block in content:
        if not isinstance(block, dict):
            continue
        if block.get("type") != "tool_use" or block.get("name") != "Skill":
            continue
        inp = block.get("input") or {}
        name = str(inp.get("skill") or inp.get("command") or "").strip()
        name = name.split(":")[-1]
        if name in ASC_FAMILY:
            return True
    return False


def _command_touches_asc(command: str) -> bool:
    return any(p.search(command) for p in ASC_PATTERNS)


def main() -> None:
    data = json.load(sys.stdin)

    if data.get("tool_name", "") != "Bash":
        return

    command = data.get("tool_input", {}).get("command", "")
    if not command or not _command_touches_asc(command):
        return

    transcript_path = data.get("transcript_path")
    if not transcript_path:
        return
    if os.sep + "tasks" + os.sep in transcript_path:
        return

    entries: list[dict] = []
    try:
        with open(transcript_path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    except OSError:
        return

    if any(e.get("type") == "agent-setting" for e in entries):
        return

    last_user = -1
    for idx, entry in enumerate(entries):
        if _is_real_user_prompt(entry):
            last_user = idx

    tail = entries[last_user + 1 :]
    if any(_invokes_asc_family(e) for e in tail):
        return

    output = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "additionalContext": CONTEXT,
        }
    }
    print(json.dumps(output))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        # Fail open: never trap the user behind a broken hook.
        pass
