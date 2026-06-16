#!/usr/bin/env python3
"""PreToolUse hook: block git force pushes that could clobber remote refs.

Denied unconditionally:
  - --force, -f, +<refspec>, combined short flags containing -f
  - --force-with-lease alone (the lease compares to your remote-tracking ref,
    which becomes stale-fresh after a `git fetch` and lets you clobber commits
    you fetched but didn't build on)

Allowed:
  - --force-with-lease paired with --force-if-includes — the pair refuses to
    clobber unseen upstream commits AND refuses to clobber commits you fetched
    but didn't build on.

No env-var bypass. If a hard push is truly needed, the user runs it themselves.

Tokenization uses shlex with punctuation_chars=True, which respects quoting
when splitting shell separators (`;`, `&&`, `||`, `|`). A `;` inside a quoted
string (e.g. a commit message) is NOT treated as a command boundary, so the
hook doesn't false-positive on `git commit -m "...;..."`. Malformed shell
that contains an unquoted `git push` substring fails closed.
"""

from __future__ import annotations

import json
import re
import shlex
import sys
from typing import Optional


SEPARATOR_TOKENS = {"&&", "||", ";", "|"}
COMBINED_SHORT_F = re.compile(r"^-[a-zA-Z]*f[a-zA-Z]*$")


HARD_MSG = (
    "BLOCKED: git force push would overwrite remote history. "
    "Use --force-with-lease --force-if-includes together if a rewrite is "
    "truly needed — the pair refuses to clobber unseen upstream commits and "
    "refuses to clobber commits you fetched but didn't build on. "
    "There is no override; if a hard push is truly needed, the user must "
    "run it themselves. "
    "Hook: ~/.claude/hooks/block-force-push.py"
)

LEASE_ONLY_MSG = (
    "BLOCKED: --force-with-lease alone clobbers commits you fetched between "
    "rebase and push — the lease compares to your now-fresh remote-tracking "
    "ref. Add --force-if-includes to also require that your new commits were "
    "built on top of what you fetched. "
    "Hook: ~/.claude/hooks/block-force-push.py"
)


def _is_hard_force(tok: str) -> bool:
    if tok in ("--force", "-f"):
        return True
    # +<refspec> — leading-+ ref is equivalent to --force.
    if tok.startswith("+") and len(tok) > 1 and (tok[1].isalpha() or tok[1] in "_/"):
        return True
    # Combined short flags like -fu, -uf. Excludes --foo (different dash count).
    if not tok.startswith("--") and COMBINED_SHORT_F.match(tok):
        return True
    return False


def _is_lease(tok: str) -> bool:
    return tok == "--force-with-lease" or tok.startswith("--force-with-lease=")


def _tokenize(command: str) -> Optional[list[str]]:
    lex = shlex.shlex(command, posix=True, punctuation_chars=True)
    lex.whitespace_split = True
    try:
        return list(lex)
    except ValueError:
        return None


def find_block_reason(command: str) -> Optional[str]:
    # Cheap pre-filter: no `push` substring → can't be a push.
    if "push" not in command:
        return None
    tokens = _tokenize(command)
    if tokens is None:
        # Malformed shell. Fail closed only if `git push` appears unquoted
        # in the raw command — the regex below is the same boundary check
        # the loop would have used.
        if re.search(r"\bgit\s+push\b", command):
            return HARD_MSG
        return None

    i = 0
    while i < len(tokens) - 1:
        if tokens[i] != "git" or tokens[i + 1] != "push":
            i += 1
            continue
        saw_lease = False
        saw_includes = False
        j = i + 2
        while j < len(tokens) and tokens[j] not in SEPARATOR_TOKENS:
            tok = tokens[j]
            if _is_hard_force(tok):
                return HARD_MSG
            if _is_lease(tok):
                saw_lease = True
            elif tok == "--force-if-includes":
                saw_includes = True
            j += 1
        if saw_lease and not saw_includes:
            return LEASE_ONLY_MSG
        i = j + 1
    return None


def main() -> None:
    data = json.load(sys.stdin)
    if data.get("tool_name") != "Bash":
        return
    command = data.get("tool_input", {}).get("command", "")
    if not command:
        return
    reason = find_block_reason(command)
    if not reason:
        return
    out = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }
    print(json.dumps(out))


if __name__ == "__main__":
    main()
