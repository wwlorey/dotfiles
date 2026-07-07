#!/usr/bin/env python3
"""PreToolUse hook on Edit/Write/NotebookEdit: nudge dev work through the `dev` skill.

The `dev` skill is the single entry point for development work in a project, and
its description already fires on "development work of any shape." But that rule
lived only in a skill the main agent had to *remember* to consult, so a terse
request ("show headers below the bottom row too") could shortcut straight to
editing source. This hook surfaces the routing reminder at the exact moment the
main agent is about to edit project source without a lifecycle skill active.

Non-blocking by design: it injects `additionalContext`, never denies. A wrong
guess costs at most one extra reminder line; it can never trap a legitimate
edit. (Compare `require-voice-report.py`, which hard-blocks — the voice rule
graduated to a block only after a soft form proved insufficient. This starts
soft.)

Fires only when ALL hold:
  1. Tool is Edit / Write / NotebookEdit.
  2. Target is source inside a project repo under ~/Repos (NOT the dotfiles
     repo — the `config` skill owns that — and NOT a metadata / build dir like
     specs/, issues/, plans/, target/, node_modules/, .git/, .claude/).
  3. This is the MAIN session, not a subagent. In the correct dev -> changes/
     build flow the actual source edits happen inside a spawned worker, which
     legitimately never invokes `dev` itself — nudging it would be noise. Two
     signals exempt workers: a `/tasks/` transcript path (classic Agent-tool
     worker) and an `agent-setting` transcript entry (teammate session).
  4. No dev-family skill (dev / changes / build / spec / spec-to-issues /
     audit-specs) was invoked since the last genuine user prompt.

Fails OPEN on any error — a broken hook must never trap the user.
"""

from __future__ import annotations

import json
import os
import sys

REPOS = os.path.realpath(os.path.expanduser("~/Repos"))
DOTFILES = os.path.realpath(os.path.expanduser("~/Repos/dotfiles"))

# First path segment (relative to the project root) that means "not source the
# dev lifecycle should gate": build output, dependencies, VCS internals, and the
# metadata dirs that lifecycle workers edit directly (specs/issues/plans).
EXEMPT_TOP_DIRS = frozenset(
    {
        ".git",
        ".claude",
        "target",
        "node_modules",
        "dist",
        "build",
        "specs",
        "issues",
        "plans",
    }
)

DEV_FAMILY = ("dev", "changes", "build", "spec", "spec-to-issues", "audit-specs")

CONTEXT = (
    "Dev-routing checkpoint. You're about to edit project source directly, and no "
    "development lifecycle skill is active since the last user message.\n"
    "\n"
    "If this edit is *development work of any shape* — a feature, bug fix, refactor, "
    "or any change to how the code behaves — route it through the `dev` skill FIRST. "
    "`dev` decomposes the request, plans it, injects the verification-gate cadence, "
    "and delegates the actual edit to a worker; editing source straight from the main "
    "session skips all of that. A terse or one-line request is still development work — "
    "brevity is not an exemption.\n"
    "\n"
    "Proceed with the direct edit ONLY if one of these holds: (a) you're already inside "
    "an approved lifecycle for this change, (b) the user explicitly told you to make this "
    "specific edit directly, or (c) this isn't development work (e.g. config via the "
    "`config` skill, scratch notes). Otherwise consult `dev` now.\n"
    "\n"
    "Hook: ~/.claude/hooks/route-dev-work.py"
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


def _target_is_gated_source(path: str) -> bool:
    """True if `path` is project source the dev lifecycle should gate."""
    resolved = os.path.realpath(os.path.expanduser(path))
    # Must live under a project repo in ~/Repos ...
    if resolved != REPOS and not resolved.startswith(REPOS + os.sep):
        return False
    # ... but the dotfiles repo is the `config` skill's domain, not dev's.
    if resolved == DOTFILES or resolved.startswith(DOTFILES + os.sep):
        return False
    rel = os.path.relpath(resolved, REPOS)
    parts = rel.split(os.sep)
    # parts[0] is the project name; need at least project + one file segment.
    if len(parts) < 2:
        return False
    return parts[1] not in EXEMPT_TOP_DIRS


def main() -> None:
    data = json.load(sys.stdin)

    tool = data.get("tool_name", "")
    if tool not in ("Edit", "Write", "NotebookEdit"):
        return

    tool_input = data.get("tool_input", {})
    path = tool_input.get("notebook_path" if tool == "NotebookEdit" else "file_path", "")
    if not path or not _target_is_gated_source(path):
        return

    transcript_path = data.get("transcript_path")
    if not transcript_path:
        return
    # Classic Agent-tool workers run under a tasks/ transcript — never nudge them.
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

    # Teammate (agent-teams) session: full session, but still a worker — exempt.
    if any(e.get("type") == "agent-setting" for e in entries):
        return

    # Scan since the most recent genuine user prompt.
    last_user = -1
    for idx, entry in enumerate(entries):
        if _is_real_user_prompt(entry):
            last_user = idx

    tail = entries[last_user + 1 :]
    if any(_invokes_dev_family(e) for e in tail):
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
