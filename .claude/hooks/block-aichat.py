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
    "BLOCKED: Claude must never run `aichat` (nor its `ah` alias). It is the "
    "user's HIPAA-compliant Vertex AI chat client, for their own interactive "
    "use only — the agent pointing it (potentially at PHI) at an LLM is "
    "off-limits. There is no override; if aichat needs to run, the user runs "
    "it themselves in their own terminal. Hook: ~/.claude/hooks/block-aichat.py"
)

# aichat as a command word in the malformed-shell fallback: preceded by start,
# a shell separator, a path slash, a quote, or an assignment `=`, and not part
# of a longer identifier (aichat-notes, aichat.py).
RAW_RE = re.compile(r"""(?:^|[\s;&|()`"'=/])aichat(?![\w.\-])""")

# The `ah` alias resolves to the same gated `aichat` function in the user's
# shell, so it's a second name the agent must never run. `ah` is short and
# common as an argument/string (`echo ah`, `-m ah`), so — unlike `aichat`,
# which is blocked in any position — `ah` is blocked ONLY in command position:
# at the start or immediately after a shell control operator.
AH_RE = re.compile(r"""(?:^|[;&|()`])\s*ah(?![\w.\-])""")

# Shell control-operator token (all punctuation): after one, the next token is
# in command position.
_OP_RE = re.compile(r"^[;&|()<>`]+$")

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
    in_cmd_pos = True  # first token is a command word
    for idx, tok in enumerate(tokens):
        base = os.path.basename(tok)
        if base == "aichat":
            return True
        if base == "ah" and in_cmd_pos:
            return True
        # `sh -c '<subcommand>'` — re-tokenize the following argument one level.
        if _C_FLAG.match(tok) and idx + 1 < len(tokens):
            sub = _tokenize(tokens[idx + 1])
            if sub and _has_aichat_token(sub):
                return True
        in_cmd_pos = bool(_OP_RE.match(tok))
    return False


def is_blocked(command: str) -> bool:
    if "aichat" not in command and "ah" not in command:  # cheap pre-filter
        return False
    tokens = _tokenize(command)
    if tokens is None:  # malformed shell → fail closed
        return bool(RAW_RE.search(command)) or bool(AH_RE.search(command))
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
