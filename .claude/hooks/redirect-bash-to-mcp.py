#!/usr/bin/env python3
"""PreToolUse hook: redirect Bash invocations of commands that have an MCP wrapper.

Some commands need to run outside the sandbox — file writes into `$HOME`,
network that bypasses the HTTPS proxy, audio output, etc. We provide
`mcp__unsandboxed-runner__*` tools for those. Calling the bare command via
Bash fails inside the sandbox and tempts a `dangerouslyDisableSandbox` retry.
This hook intercepts the Bash call first and points at the wrapper.

REDIRECTS maps bare command name → MCP tool to use instead. Extend it when
adding a new wrapper that should fully supplant the bare Bash call.

Tokenization uses shlex with punctuation_chars=True so shell separators (`;`,
`&&`, `||`, `|`) are respected and quoting is honored (a redirected name
inside a quoted string is NOT a real invocation). Malformed shell falls back
to a regex boundary check on the raw command and fails closed.
"""

from __future__ import annotations

import json
import re
import shlex
import sys


REDIRECTS = {
    "save-config": "mcp__unsandboxed-runner__save_config",
}

SEPARATOR_TOKENS = {"&&", "||", ";", "|", "&"}


def _tokenize(command: str) -> list[str] | None:
    lex = shlex.shlex(command, posix=True, punctuation_chars=True)
    lex.whitespace_split = True
    try:
        return list(lex)
    except ValueError:
        return None


def find_redirect(command: str) -> tuple[str, str] | None:
    """Return (bare_name, wrapper) for the first redirected invocation, or None."""
    # Cheap pre-filter: none of the redirected names appear at all → skip.
    if not any(name in command for name in REDIRECTS):
        return None

    tokens = _tokenize(command)
    if tokens is None:
        # Malformed shell — boundary regex on the raw command, fail closed.
        for name, wrapper in REDIRECTS.items():
            if re.search(rf"(?:^|[;&|]\s*|\s)\s*{re.escape(name)}(?:\s|$|[;&|])", command):
                return name, wrapper
        return None

    # A token is a real invocation iff it sits at a command-start position:
    # index 0, or immediately after a separator token.
    at_start = True
    for tok in tokens:
        if tok in SEPARATOR_TOKENS:
            at_start = True
            continue
        if at_start and tok in REDIRECTS:
            return tok, REDIRECTS[tok]
        at_start = False
    return None


def main() -> None:
    data = json.load(sys.stdin)
    if data.get("tool_name") != "Bash":
        return
    command = data.get("tool_input", {}).get("command", "")
    if not command:
        return
    hit = find_redirect(command)
    if hit is None:
        return
    name, wrapper = hit
    msg = (
        f"`{name}` has an unsandboxed MCP wrapper. Call `{wrapper}` instead — "
        f"it runs outside the sandbox without `dangerouslyDisableSandbox`. "
        f"Hook: ~/.claude/hooks/redirect-bash-to-mcp.py."
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
