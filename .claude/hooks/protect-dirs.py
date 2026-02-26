#!/usr/bin/env python3
"""PreToolUse hook: block tool access to directories listed in PROTECTED_DIRS."""

from __future__ import annotations

import json
import os
import sys
from typing import Optional


def canonicalize(path: str) -> str:
    """Expand ~ and env vars, then resolve to a real absolute path."""
    return os.path.realpath(os.path.expanduser(os.path.expandvars(path)))


def is_under(path: str, protected: str) -> bool:
    """Boundary-safe prefix match: /a/b matches /a/b and /a/b/foo but NOT /a/bc."""
    return path == protected or path.startswith(protected + "/")


def check_path(path: str, protected_dirs: list[str]) -> Optional[str]:
    """Check a single resolved path against all protected dirs."""
    resolved = canonicalize(path)
    for d in protected_dirs:
        if is_under(resolved, d):
            return d
    return None


def check_bash(command: str, protected_dirs: list[str]) -> Optional[str]:
    """Substring match against protected dirs after expanding ~ and $HOME."""
    home = os.path.expanduser("~")
    # Build expanded version of the command: replace ~/  $HOME  ${HOME}
    expanded = command.replace("~/", home + "/")
    expanded = expanded.replace("$HOME", home)
    expanded = expanded.replace("${HOME}", home)

    for d in protected_dirs:
        # Check canonical form against expanded command
        if d in expanded:
            return d
        # Also check tilde-relative form against raw command
        if d.startswith(home):
            tilde_form = "~" + d[len(home):]
            if tilde_form in command:
                return d
    return None


def check_glob(tool_input: dict, protected_dirs: list[str]) -> Optional[str]:
    """Check Glob's path and pattern fields with bidirectional prefix matching."""
    # Check the path field (search root)
    path = tool_input.get("path")
    if path:
        hit = check_path(path, protected_dirs)
        if hit:
            return hit

    pattern = tool_input.get("pattern", "")
    if not pattern:
        return None

    # Normalize the pattern: expand ~ and make absolute
    norm = os.path.expanduser(os.path.expandvars(pattern))
    if os.path.isabs(norm):
        # Strip glob wildcards to get the concrete prefix
        concrete = []
        for part in norm.split("/"):
            if any(c in part for c in ("*", "?", "[", "{")):
                break
            concrete.append(part)
        prefix = "/".join(concrete) if concrete else "/"
        prefix = os.path.realpath(prefix)

        for d in protected_dirs:
            # Pattern reaches into protected dir, or protected dir is under pattern root
            if is_under(prefix, d) or is_under(d, prefix):
                return d

    return None


def main() -> None:
    raw = os.environ.get("PROTECTED_DIRS", "").strip()
    if not raw:
        print("ERROR: PROTECTED_DIRS is not set. Refusing all tool use.", file=sys.stderr)
        sys.exit(2)

    protected_dirs = [canonicalize(d) for d in raw.split(":") if d.strip()]
    if not protected_dirs:
        print("ERROR: PROTECTED_DIRS is empty. Refusing all tool use.", file=sys.stderr)
        sys.exit(2)

    data = json.load(sys.stdin)
    tool_name = data.get("tool_name", "")
    tool_input = data.get("tool_input", {})

    hit = None

    if tool_name == "Bash":
        command = tool_input.get("command", "")
        if command:
            hit = check_bash(command, protected_dirs)
    elif tool_name == "Glob":
        hit = check_glob(tool_input, protected_dirs)
    elif tool_name in ("Read", "Write", "Edit"):
        path = tool_input.get("file_path", "")
        if path:
            hit = check_path(path, protected_dirs)
    elif tool_name == "NotebookEdit":
        path = tool_input.get("notebook_path", "")
        if path:
            hit = check_path(path, protected_dirs)
    elif tool_name == "Grep":
        path = tool_input.get("path", "")
        if path:
            hit = check_path(path, protected_dirs)
    else:
        # Fallback: check common path fields
        for field in ("file_path", "notebook_path", "path"):
            path = tool_input.get(field, "")
            if path:
                hit = check_path(path, protected_dirs)
                if hit:
                    break

    if hit:
        target = next(
            (tool_input.get(f, "") for f in ("file_path", "notebook_path", "path", "command", "pattern") if tool_input.get(f)),
            "unknown",
        )
        # Truncate long commands for the message
        if len(target) > 80:
            target = target[:77] + "..."
        print(f"BLOCKED: Access to {target} is forbidden (matches {hit}).", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
