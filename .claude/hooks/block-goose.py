#!/usr/bin/env python3
"""PreToolUse hook: block Claude from ever running `goose`.

`goose` is the user's HIPAA-locked Vertex AI coding harness, for their own
interactive use only. The coding agent must never invoke it — spawning a second
agent that (potentially at PHI) edits files, runs shell commands, and calls an
LLM is off-limits. This hook denies any Bash command that invokes the `goose`
binary.

No env-var bypass. If the user wants to run goose, they run it themselves in
their own terminal.

`goose` is a common English word and a directory-name component (`.config/goose`,
`grep goose`), so — unlike the rare string `aichat`, which its sibling hook
blocks in any position — `goose` is blocked ONLY in COMMAND position: at the
start of the command, or immediately after a shell control operator (`;`, `|`,
`&&`, `(`, backtick, …). This still catches every way to actually run it:
  - `goose …`
  - `foo | goose …`, `x && goose …`
  - `sh -c 'goose …'` / `bash -lc 'goose …'`  (re-tokenizes the -c argument)
  - `/abs/path/to/goose …`   (basename in command position)
  - `env X=1 goose`, `sudo goose`, `nohup goose`, `X=1 goose`  (command
    position carries through leading VAR=val assignments and runner prefixes)
while leaving harmless mentions as arguments (`grep goose`, `ls .config/goose`,
`echo "run goose yourself"`) alone. Malformed shell fails closed via a
command-position regex fallback. This is a guardrail against accidental agent
invocation, not an airtight control against a determined bypass (`g=goose; $g`).
"""

from __future__ import annotations

import json
import os
import re
import shlex
import sys
from typing import Optional


MSG = (
    "BLOCKED: Claude must never run `goose`. It is the user's HIPAA-locked "
    "Vertex AI coding harness, for their own interactive use only — the agent "
    "pointing it (potentially at PHI) at an LLM, the filesystem, and the shell "
    "is off-limits. There is no override; if goose needs to run, the user runs "
    "it themselves in their own terminal. Hook: ~/.claude/hooks/block-goose.py"
)

# `goose` as a command word in the malformed-shell fallback: at start or right
# after a shell control operator, not part of a longer identifier
# (goose-hipaa-check, goose.py, mongoose).
RAW_RE = re.compile(r"""(?:^|[;&|()`])\s*(?:[^\s;&|()`]*/)?goose(?![\w.\-])""")

# -c style shell flags that take a command string: -c, -lc, -ic, -lic, ...
_C_FLAG = re.compile(r"^-[a-z]*c[a-z]*$")

# Shell control-operator token: after one, the next token is a command word.
_OP_RE = re.compile(r"^[;&|()<>`]+$")

# A leading VAR=val assignment (`X=1 goose`) — command position carries past it.
_ASSIGN_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")

# Transparent command-runner prefixes: `env X=1 goose`, `sudo goose`,
# `nohup goose`, `command goose` all still run goose, so command position must
# carry through them. (grep/ls are NOT here, so `grep goose` stays a mention.)
_RUNNERS = frozenset({
    "env", "sudo", "doas", "nohup", "nice", "ionice", "time", "stdbuf",
    "setsid", "command", "builtin", "exec", "xargs", "timeout", "caffeinate",
})


def _tokenize(command: str) -> Optional[list[str]]:
    lex = shlex.shlex(command, posix=True, punctuation_chars=True)
    lex.whitespace_split = True
    try:
        return list(lex)
    except ValueError:
        return None


def _has_goose_token(tokens: list[str]) -> bool:
    in_cmd_pos = True  # first token is a command word
    for idx, tok in enumerate(tokens):
        if in_cmd_pos and os.path.basename(tok) == "goose":
            return True
        # `sh -c '<subcommand>'` — re-tokenize the following argument one level.
        if _C_FLAG.match(tok) and idx + 1 < len(tokens):
            sub = _tokenize(tokens[idx + 1])
            if sub and _has_goose_token(sub):
                return True
        if _OP_RE.match(tok):
            in_cmd_pos = True                       # after ; | && ( etc.
        elif in_cmd_pos and (
            _ASSIGN_RE.match(tok) or os.path.basename(tok) in _RUNNERS
        ):
            in_cmd_pos = True                       # VAR=val / env / sudo / … — carry through
        else:
            in_cmd_pos = False
    return False


def is_blocked(command: str) -> bool:
    if "goose" not in command:  # cheap pre-filter
        return False
    tokens = _tokenize(command)
    if tokens is None:  # malformed shell → fail closed
        return bool(RAW_RE.search(command))
    return _has_goose_token(tokens)


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
