#!/usr/bin/env python3
"""PreToolUse hook on Edit/Write/NotebookEdit: nudge config work through the `config` skill.

System configuration — dotfiles, `~/.agents` (skills, MEMENTO, the agent
script), `~/.claude` settings/hooks/commands, the unsandboxed-runner MCP server —
is edited in the dotfiles repo and deployed with save-config, with a ripple
check for skill edits. That workflow lives in the `config` skill, which the main
agent has to *remember* to consult; a quick "just tweak this hook" can shortcut
straight to editing the file and skip the deploy + audit + ripple steps.

This hook surfaces the routing reminder at the exact moment the main agent is
about to edit a config file without a config-family skill active. It is the
config-domain sibling of `route-dev-work.py` (which nudges project source toward
the `dev` skill); the two are mutually exclusive by target — `route-dev-work`
exempts the dotfiles repo, this one fires only on config.

Non-blocking by design: it injects `additionalContext`, never denies. A wrong
guess costs at most one extra reminder line; it can never trap a legitimate
edit. (The hard-deny for editing a *deployed* copy instead of the canonical
source is `redirect-config-edits.py`; this one is a softer process nudge that
also fires when you edit the canonical source itself.)

Fires only when ALL hold:
  1. Tool is Edit / Write / NotebookEdit.
  2. Target is a config file — either inside the dotfiles repo (the canonical
     source) or a deployed path the dotfiles repo owns (exact-match mirror or a
     fully-managed MIRRORED_PREFIXES dir).
  3. This is the MAIN session, not a subagent (a `/tasks/` transcript path or an
     `agent-setting` entry exempts workers).
  4. No config-family skill (config / create-skill / update-config /
     keybindings-help) was invoked since the last genuine user prompt.

Fails OPEN on any error — a broken hook must never trap the user.
"""

from __future__ import annotations

import json
import os
import sys

DOTFILES = os.path.realpath(os.path.expanduser("~/Repos/dotfiles"))
HOME = os.path.realpath(os.path.expanduser("~"))

# Dirs under $HOME where every legitimate child is mirrored from the dotfiles
# repo. Kept in sync with redirect-config-edits.py's MIRRORED_PREFIXES.
MIRRORED_PREFIXES = (
    ".agents/",
    ".claude/commands/",
    ".claude/hooks/",
    ".claude/mcp-servers/",
)

CONFIG_FAMILY = ("config", "create-skill", "update-config", "keybindings-help")

CONTEXT = (
    "Config-routing checkpoint. You're about to edit a configuration file "
    "(dotfiles / ~/.agents / ~/.claude / a skill / the MCP server), and no "
    "config-family skill is active since the last user message.\n"
    "\n"
    "Route this through the `config` skill FIRST. It owns the workflow: edit the "
    "canonical source in the dotfiles repo (never the deployed copy), mutate with "
    "Edit/Write (never a Bash redirect/sed), deploy with "
    "`mcp__unsandboxed-runner__save_config`, then audit — and for skill edits, run "
    "the create-skill ripple check. Editing straight from here skips the deploy and "
    "the drift sweep. For designing or restructuring a skill specifically, `config` "
    "will point you at `create-skill`.\n"
    "\n"
    "Proceed with the direct edit ONLY if (a) a config-family skill is already "
    "active for this change, (b) the user told you to make this specific edit "
    "directly, or (c) this file isn't really config. Otherwise consult `config` now.\n"
    "\n"
    "Hook: ~/.claude/hooks/route-config-work.py"
)

# Leading tags marking a user-role transcript block as harness-injected rather
# than a genuine user directive. Kept in sync with route-dev-work.py /
# agent-spawn-reminder.py.
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


def _invokes_config_family(entry: dict) -> bool:
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
        if name in CONFIG_FAMILY:
            return True
    return False


def _target_is_config(path: str) -> bool:
    """True if `path` is a config file the `config` skill should gate."""
    resolved = os.path.realpath(os.path.expanduser(path))
    # Canonical source: anything inside the dotfiles repo is config.
    if resolved == DOTFILES or resolved.startswith(DOTFILES + os.sep):
        return True
    # Deployed copy the repo owns: exact-match mirror or a fully-managed prefix.
    try:
        rel = os.path.relpath(resolved, HOME)
    except ValueError:
        return False
    if rel.startswith(".."):
        return False
    if os.path.exists(os.path.join(DOTFILES, rel)):
        return True
    for prefix in MIRRORED_PREFIXES:
        if rel == prefix.rstrip("/") or rel.startswith(prefix):
            return True
    return False


def main() -> None:
    data = json.load(sys.stdin)

    tool = data.get("tool_name", "")
    if tool not in ("Edit", "Write", "NotebookEdit"):
        return

    tool_input = data.get("tool_input", {})
    path = tool_input.get("notebook_path" if tool == "NotebookEdit" else "file_path", "")
    if not path or not _target_is_config(path):
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
    if any(_invokes_config_family(e) for e in tail):
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
