#!/usr/bin/env python3
"""PreToolUse hook: redirect Edit/Write to deployed-copy paths back to the dotfiles repo.

Deployed files under $HOME mirrored from ~/Repos/dotfiles/ are stale until
`save-config` runs — edits applied to the deployed copy are silently dropped
on the next deploy. This hook fires on every Edit/Write/NotebookEdit, and if
the target maps to a path the dotfiles repo owns, denies the call with a
message pointing to the canonical source and the `config` skill.

Ownership rule — a path is "owned" by the repo if EITHER:
  1. The corresponding file exists in the repo at the same path relative to
     $HOME (exact match — covers existing mirrored files).
  2. The path falls under one of the MIRRORED_PREFIXES below (fully-managed
     prefix match — covers new files inside an exhaustively-mirrored dir).

MIRRORED_PREFIXES enumerates dirs where every legitimate child belongs in
the repo. Selectively-managed parents (e.g. ~/.claude/, which contains both
mirrored config and runtime state) are NOT listed here — they fall back to
exact-match only.

When adding a new fully-managed top-level dir to the dotfiles repo, extend
MIRRORED_PREFIXES so subsequent new-file edits are caught.
"""

from __future__ import annotations

import json
import os
import sys


DOTFILES_REPO = os.path.realpath(os.path.expanduser("~/Repos/dotfiles"))
HOME = os.path.realpath(os.path.expanduser("~"))

MIRRORED_PREFIXES = (
    ".agents/",
    ".claude/commands/",
    ".claude/hooks/",
    ".claude/mcp-servers/",
)


def repo_owns(target: str) -> tuple[bool, str]:
    """Return (owned, canonical_repo_path)."""
    try:
        rel = os.path.relpath(target, HOME)
    except ValueError:
        return False, ""
    if rel.startswith(".."):
        return False, ""
    candidate = os.path.join(DOTFILES_REPO, rel)
    if os.path.exists(candidate):
        return True, candidate
    rel_with_slash = rel + ("" if rel.endswith("/") else "")
    for prefix in MIRRORED_PREFIXES:
        if rel_with_slash == prefix.rstrip("/") or rel_with_slash.startswith(prefix):
            return True, candidate
    return False, ""


def main() -> None:
    data = json.load(sys.stdin)
    tool = data.get("tool_name", "")
    if tool not in ("Edit", "Write", "NotebookEdit"):
        return
    tool_input = data.get("tool_input", {})
    path = tool_input.get("notebook_path" if tool == "NotebookEdit" else "file_path", "")
    if not path:
        return
    resolved = os.path.realpath(os.path.expanduser(path))
    if resolved == DOTFILES_REPO or resolved.startswith(DOTFILES_REPO + os.sep):
        return
    owned, canonical = repo_owns(resolved)
    if not owned:
        return
    msg = (
        f"DEPLOYED COPY. {resolved} is mirrored from the dotfiles repo. "
        f"Edits here are stale on the next save-config. "
        f"Edit the canonical source at {canonical} instead, then run save-config. "
        f"Consult the `config` skill for the deploy flow."
    )
    out = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": msg,
        }
    }
    print(json.dumps(out))


if __name__ == "__main__":
    main()
