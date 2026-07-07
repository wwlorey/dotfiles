#!/usr/bin/env python3
"""PreToolUse hook on Agent: inject orchestrate + dev-routing reminders.

Fires before every Agent tool call. Emits two `additionalContext` blocks:

1. **Orchestrate briefing reminder (always).** Surfaces the two rules the
   orchestrator needs at the spawn boundary — brief per the `orchestrate`
   checklist, and don't treat an interim `status: completed` snapshot as
   terminal.

2. **Dev-routing nudge (conditional, soft).** The Edit/Write hook
   `route-dev-work.py` catches direct source edits from the main session, but
   the orchestrator itself never edits source — it free-spawns impl workers,
   and the exempted worker never trips that hook either. So development work
   can slip through the Agent boundary entirely un-gated. This block closes
   that gap: when a spawn looks like un-routed implementation work on this
   project, it reminds the orchestrator to route through `dev` first. It fires
   ONLY when BOTH hold:
     (a) No dev-family skill (dev / changes / build / spec / spec-to-issues /
         audit-specs) is active since the last genuine user prompt — so a spawn
         inside a proper lifecycle (planning worker, gate worker, impl worker)
         stays silent.
     (b) The spawn prompt is impl-shaped (imperative implementation verb) AND
         carries a this-repo cue (issue slug, `crates/…` path, repo file
         reference) — so research / planning / config / voice spawns and
         cross-project spawns never trigger it.

Both blocks are advisory `additionalContext` — this hook NEVER denies. It fails
OPEN on any error: a malformed payload still yields the orchestrate reminder,
and any failure computing the dev nudge simply drops that second block.

The transcript-scan helpers (`_is_real_user_prompt`, `_invokes_dev_family`)
mirror `route-dev-work.py` so both hooks classify the user-prompt window
identically; keep them in sync.
"""

from __future__ import annotations

import json
import os
import re
import sys

ORCHESTRATE_CONTEXT = (
    "Agent spawn checkpoint. The `orchestrate` skill governs both ends of this spawn — composing the briefing and reading the response. Two rules that bite at this moment:\n"
    "\n"
    "1. **Brief per the orchestrate checklist.** Goal, scope, return format, skills/scripts/MCP tools the worker should reach for, inherited project rules, silence clause. Workers inherit no MEMENTO, no skills index, no conversation context — anything they need has to be named in the prompt. If you haven't consulted `orchestrate` this turn, do so before composing this spawn.\n"
    "\n"
    "2. **Reading the response.** When the task-notification for this spawn arrives, `status: completed` is NOT necessarily terminal — the harness fires that event whenever the worker emits new output. Interim snapshots with sentence-fragment tails ('Let me wait...', 'Good. Let me...', 'File hasn't been written in...') look terminal but aren't. Only a notification whose `result` matches the structured return format you required in the briefing (## Summary, ## Files changed, etc.) is terminal. When unsure, verify the artifact (git log, tree state, file written), not the notification text. Treating an interim snapshot as terminal triggers premature escalation — a real failure mode."
)

DEV_NUDGE_CONTEXT = (
    "Dev-routing checkpoint. This spawn looks like development work on this project "
    "(code / spec / issue / implementation), and no development lifecycle skill "
    "(`dev` / `changes` / `build` / `spec` / `spec-to-issues` / `audit-specs`) is active "
    "since the last user message.\n"
    "\n"
    "Development work of any shape must route through the `dev` skill FIRST. `dev` "
    "decomposes the request, injects the verification-gate cadence, and delegates the "
    "implementation to a worker; spawning an impl worker directly from here bypasses all "
    "of it. If this spawn is development work, stop and invoke `dev` now. Ignore this only "
    "if you're already inside an approved lifecycle for this work, or the spawn isn't "
    "development work.\n"
    "\n"
    "Hook: ~/.claude/hooks/agent-spawn-reminder.py"
)

DEV_FAMILY = ("dev", "changes", "build", "spec", "spec-to-issues", "audit-specs")

# Imperative implementation verbs that mark a spawn as impl-shaped.
IMPL_VERB_RE = re.compile(
    r"\b(implement|fix|refactor|edit|add|wire|rewrite|migrate|patch)(s|es|ed|ing)?\b",
    re.IGNORECASE,
)

# This-repo cues: an issue slug (word + 6-digit date), a `crates/…` path, or a
# reference to a repo-internal directory / source file.
ISSUE_SLUG_RE = re.compile(r"\b[a-z][a-z0-9]*(?:-[a-z0-9]+)*-\d{6}\b", re.IGNORECASE)
REPO_PATH_RE = re.compile(
    r"(crates/|src-tauri/|\bspecs/|\bissues/)|\b[\w./-]+\.(rs|ts|tsx|toml)\b",
    re.IGNORECASE,
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


def _invokes_dev_family(entry: dict) -> bool:
    """True if this assistant entry calls the Skill tool for a dev-family skill."""
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
        # The Skill tool records the target under `skill`; tolerate `command` too.
        name = str(inp.get("skill") or inp.get("command") or "").strip()
        # Plugin-namespaced skills arrive as `plugin:skill`; match the tail.
        name = name.split(":")[-1]
        if name in DEV_FAMILY:
            return True
    return False


def _spawn_is_unrouted_dev(prompt: str) -> bool:
    """True if the spawn prompt is impl-shaped AND carries a this-repo cue."""
    if not IMPL_VERB_RE.search(prompt):
        return False
    return bool(ISSUE_SLUG_RE.search(prompt) or REPO_PATH_RE.search(prompt))


def _dev_family_active(transcript_path: str) -> bool:
    """True if a dev-family skill was invoked since the last real user prompt.

    Returns True (suppress the nudge) when the window can't be established — a
    missing or unreadable transcript is not grounds to nag.
    """
    if not transcript_path:
        return True
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
        return True

    last_user = -1
    for idx, entry in enumerate(entries):
        if _is_real_user_prompt(entry):
            last_user = idx
    tail = entries[last_user + 1 :]
    return any(_invokes_dev_family(e) for e in tail)


def _dev_nudge(data: dict) -> str | None:
    """Return the dev-routing nudge when this spawn is un-routed dev work, else None."""
    tool_input = data.get("tool_input") or {}
    prompt = str(tool_input.get("prompt") or "")
    if not prompt:
        return None
    if not _spawn_is_unrouted_dev(prompt):
        return None
    if _dev_family_active(data.get("transcript_path", "")):
        return None
    return DEV_NUDGE_CONTEXT


def main() -> int:
    raw = sys.stdin.read()

    context = ORCHESTRATE_CONTEXT
    try:
        data = json.loads(raw) if raw.strip() else {}
        nudge = _dev_nudge(data)
        if nudge:
            context = context + "\n\n---\n\n" + nudge
    except Exception:
        # Fail open: any error computing the dev nudge drops it; the
        # orchestrate reminder still emits.
        pass

    output = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "additionalContext": context,
        }
    }
    print(json.dumps(output))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        # Never trap the user behind a broken hook.
        sys.exit(0)
