#!/usr/bin/env python3
"""PostToolUse hook: remind to run the ripple check after a skill SKILL.md is edited.

Fires after Edit/Write/NotebookEdit. If the target path is a SKILL.md under
either the deployed `.agents/skills/` tree or its dotfiles-repo mirror, inject
a system-reminder pointing at the create-skill skill's "Ripple check" section.

The failure mode this prevents: rationalizing past the ripple step on
"routine" or "internal-only" edits, where contract drift can still leak into
neighbor skills through vocabulary or assumed procedure.
"""

from __future__ import annotations

import json
import sys


REMINDER = (
    "RIPPLE CHECK REQUIRED: a skill SKILL.md was just edited. "
    "Before reporting this skill change done, run the ripple check from "
    "~/.agents/skills/create-skill/SKILL.md §Ripple check — re-read the "
    "edited skill end-to-end, then check incoming and outgoing skill neighbors "
    "for drift. Do not skip even for routine internal tweaks (frontmatter "
    "unchanged, snippet hardening, internal scripts) — that is exactly the "
    "failure mode this reminder prevents."
)


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except json.JSONDecodeError:
        return
    tool = data.get("tool_name", "")
    if tool not in ("Edit", "Write", "NotebookEdit"):
        return
    tool_input = data.get("tool_input", {})
    path = tool_input.get(
        "notebook_path" if tool == "NotebookEdit" else "file_path", ""
    )
    if not path:
        path = data.get("tool_response", {}).get("filePath", "")
    if "/.agents/skills/" not in path or not path.endswith("/SKILL.md"):
        return
    out = {
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": REMINDER,
        }
    }
    print(json.dumps(out))


if __name__ == "__main__":
    main()
