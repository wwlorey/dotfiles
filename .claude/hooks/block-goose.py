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
  - `uv run goose`, `npx goose`, `watch goose`  (package/exec runners carry
    command position through their subcommand and option flags)
  - `>f goose`   (a leading redirection's target is skipped, not the command)
  - `` `goose …` ``, `$(goose …)`  (command substitution — caught by the regex
    pass, which runs even when tokenizing succeeds)
while leaving harmless mentions as arguments (`grep goose`, `ls .config/goose`,
`echo "run goose yourself"`, `uv pip install goose`) alone. Malformed shell
fails closed via a command-position regex fallback. This is a guardrail against
accidental agent invocation, not an airtight control against a determined
bypass (`g=goose; $g`).
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

# Command-SEPARATOR operator token (`;`, `|`, `&&`, `(`, `)`, backtick): after
# one, the next token is a fresh command word.
_SEP_RE = re.compile(r"^[;&|()`]+$")

# REDIRECTION operator token (`>`, `>>`, `<`, `2>`, `2>>`, `>&`, `2>&1`, …): its
# following token is a filename target, NOT the command — skip the target and
# keep command position, so `>f goose` still resolves goose as the command.
_REDIR_RE = re.compile(r"^[0-9]*[<>]{1,2}&?[0-9]*$")

# A leading VAR=val assignment (`X=1 goose`) — command position carries past it.
_ASSIGN_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")

# Transparent command-runner prefixes: `env X=1 goose`, `sudo goose`,
# `nohup goose`, `command goose` all still run goose, so command position must
# carry through them. (grep/ls are NOT here, so `grep goose` stays a mention.)
_RUNNERS = frozenset({
    "env", "sudo", "doas", "nohup", "nice", "ionice", "time", "stdbuf",
    "setsid", "command", "builtin", "exec", "xargs", "timeout", "caffeinate",
})

# Package/exec runners, in two shapes:
#   EXEC — the launched command comes AFTER an exec subcommand: `uv run goose`,
#     `poetry run goose`, `pnpm dlx goose`. We scan through the runner and its
#     option flags; only at the exec subcommand does the REST of the line become
#     the launched command — checked for goose and "sticky" until a shell
#     separator — so a value-taking flag (`uv run --with X goose`) can't hide
#     goose behind X. A NON-exec subcommand (`uv pip install goose`) launches no
#     inline command, so command position ends there and goose stays an arg.
#   DIRECT — the command follows the runner directly, possibly behind flags:
#     `npx goose`, `watch -n2 goose`. The rest of the line is sticky-checked
#     from the runner on.
_EXEC_RUNNERS = frozenset({
    "uv", "npm", "pnpm", "yarn", "bun", "poetry", "pdm", "pipx", "deno",
    "rye", "hatch",
})
_DIRECT_RUNNERS = frozenset({"npx", "bunx", "watch"})
_RUNNER_SUBCMDS = frozenset({"run", "exec", "x", "tool", "dlx"})

# A bare file-descriptor number prefixing a redirection (`2>err`, `2>&1`) — part
# of the redirect, not a command word or argument.
_FD_RE = re.compile(r"^\d+$")


def _tokenize(command: str) -> Optional[list[str]]:
    lex = shlex.shlex(command, posix=True, punctuation_chars=True)
    lex.whitespace_split = True
    try:
        return list(lex)
    except ValueError:
        return None


def _has_goose_token(tokens: list[str]) -> bool:
    in_cmd_pos = True     # the next non-prefix token is a command word
    runner = None         # None | "prefix" (scanning an exec-runner) | "exec" (past `run`, sticky)
    skip_next = False     # the next token is a redirection target — skip it
    for idx, tok in enumerate(tokens):
        if skip_next:
            skip_next = False
            continue
        base = os.path.basename(tok)
        if in_cmd_pos and base == "goose":
            return True
        # `sh -c '<subcommand>'` — re-tokenize the following argument one level.
        if _C_FLAG.match(tok) and idx + 1 < len(tokens):
            sub = _tokenize(tokens[idx + 1])
            if sub and _has_goose_token(sub):
                return True
        # A bare fd number before a redirection (`2>err`, `2>&1`) is part of the
        # redirect — don't let it flip command position off.
        if _FD_RE.match(tok) and idx + 1 < len(tokens) and _REDIR_RE.match(tokens[idx + 1]):
            continue
        if _SEP_RE.match(tok):
            in_cmd_pos = True                       # after ; | && ( ` etc.
            runner = None
        elif _REDIR_RE.match(tok):
            skip_next = True                        # skip the redirect target; command still follows
        elif runner == "exec":
            pass                                    # sticky: rest of the exec'd command stays checkable
        elif runner == "prefix":
            if tok.startswith("-"):
                pass                                # a runner option flag
            elif base in _RUNNER_SUBCMDS:
                runner = "exec"                     # `run`/`exec`/`dlx` — the command follows
            else:
                in_cmd_pos = False                  # a non-exec subcommand (pip/add/…) — no inline command
                runner = None
        elif in_cmd_pos and base in _DIRECT_RUNNERS:
            runner = "exec"                         # command follows directly — sticky-check the rest
        elif in_cmd_pos and base in _EXEC_RUNNERS:
            runner = "prefix"                       # scan for the exec subcommand
        elif in_cmd_pos and (_ASSIGN_RE.match(tok) or base in _RUNNERS):
            pass                                    # VAR=val / env / sudo / … — carry command position through
        else:
            in_cmd_pos = False
    return False


def is_blocked(command: str) -> bool:
    if "goose" not in command:  # cheap pre-filter
        return False
    # The regex pass catches command-substitution forms (`` `goose` ``,
    # `$(goose …)`) whose backtick/paren the tokenizer swallows, so OR it in even
    # when tokenizing succeeds; it also fails closed on malformed shell.
    if RAW_RE.search(command):
        return True
    tokens = _tokenize(command)
    if tokens is None:  # malformed shell → already handled by RAW_RE above
        return False
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
