#!/usr/bin/env python3
"""PreToolUse hook: block Claude from ever running `aichat`.

`aichat` is the user's HIPAA-compliant Vertex AI chat client, for their own
interactive use only. The coding agent must never invoke it — routing it
(potentially at PHI) to an LLM is off-limits. This hook denies any Bash
command that invokes the `aichat` binary.

No env-var bypass. If the user wants to run aichat, they run it themselves in
their own terminal.

Detection blocks a token whose basename is `aichat`, so all of these are caught:
  - `aichat …`
  - `/opt/homebrew/bin/aichat …`   (absolute / relative path)
  - `command aichat`, `env X=1 aichat`, `foo | aichat`
  - `sh -c 'aichat …'` / `bash -lc 'aichat …'`  (re-tokenizes the -c argument)
It does NOT block a harmless quoted mention like `echo "run aichat yourself"`
(the whole quoted string is one token whose basename is not `aichat`), nor a
similarly-named tool like `aichat-notes`. Malformed shell fails closed via a
regex fallback.
"""

from __future__ import annotations

import json
import os
import re
import shlex
import sys
from typing import Optional


MSG = (
    "BLOCKED: Claude must never run `aichat`. It is the user's "
    "HIPAA-compliant Vertex AI chat client, for their own interactive use "
    "only — the agent pointing it (potentially at PHI) at an LLM is "
    "off-limits. There is no override; if aichat needs to run, the user runs "
    "it themselves in their own terminal. Hook: ~/.claude/hooks/block-aichat.py"
)

# aichat as a command word in the malformed-shell fallback: preceded by start,
# a shell separator, a path slash, a quote, or an assignment `=`, and not part
# of a longer identifier (aichat-notes, aichat.py).
RAW_RE = re.compile(r"""(?:^|[\s;&|()`"'=/])aichat(?![\w.\-])""")

# -c style shell flags that take a command string: -c, -lc, -ic, -lic, ...
_C_FLAG = re.compile(r"^-[a-z]*c[a-z]*$")


def _tokenize(command: str) -> Optional[list[str]]:
    lex = shlex.shlex(command, posix=True, punctuation_chars=True)
    lex.whitespace_split = True
    try:
        return list(lex)
    except ValueError:
        return None


def _has_aichat_token(tokens: list[str]) -> bool:
    for idx, tok in enumerate(tokens):
        if os.path.basename(tok) == "aichat":
            return True
        # `sh -c '<subcommand>'` — re-tokenize the following argument one level.
        if _C_FLAG.match(tok) and idx + 1 < len(tokens):
            sub = _tokenize(tokens[idx + 1])
            if sub and any(os.path.basename(t) == "aichat" for t in sub):
                return True
    return False


def is_blocked(command: str) -> bool:
    if "aichat" not in command:  # cheap pre-filter
        return False
    tokens = _tokenize(command)
    if tokens is None:
        return bool(RAW_RE.search(command))  # malformed shell → fail closed
    return _has_aichat_token(tokens)


def main() -> None:
    data = json.load(sys.stdin)
    if data.get("tool_name") != "Bash":
        return
    command = data.get("tool_input", {}).get("command", "")
    if not command or not is_blocked(command):
        return
    out = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": MSG,
        }
    }
    print(json.dumps(out))


if __name__ == "__main__":
    main()
