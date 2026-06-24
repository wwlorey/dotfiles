#!/usr/bin/env python3
"""PreToolUse hook: deny Bash commands that mutate dotfiles-managed config.

Config files mirrored from ~/Repos/dotfiles must be changed in the repo with
the Edit/Write tools, then deployed via save-config. Mutating them from Bash
(`>` redirects, `sed -i`, `cp`/`mv` into them, a `python3` heredoc that opens
and writes them) bypasses the redirect-config-edits hook AND trips the sandbox
write-deny — exactly the confusing wall that prompted this guard. This hook
turns that into an actionable redirect and closes the loophole for unsandboxed
(`dangerouslyDisableSandbox`) Bash too.

DETECTION (two postures, by command kind):
  * Idiom writes — output redirection (`>`/`>>`/`>|`), `tee`, `truncate`,
    `sed -i`, `dd of=`, and dest-taking copies (`cp`/`mv`/`install`/`ln`/
    `rsync`). The WRITE TARGET token is resolved to an absolute path and
    tested against the managed surface. Precise: `cat ~/.claude/settings.json
    > /tmp/x` is a READ of a managed file into an unmanaged target — allowed.
  * Interpreter writes — `python`/`python3`/`perl`/`ruby`/`node`. The write
    happens inside the program, so there is no target token to resolve;
    instead the raw command is scanned for a managed-path MARKER substring.
    Broad by design (a read-only interpreter touching a managed path is also
    denied), so the message names the Read-tool escape hatch.

Managed surface (matched in BOTH the repo and the deployed ~ copies):
  exact files  .claude/settings.json, .claude/settings.local.json,
               .claude/statusline.sh
  prefixes     .agents/, .claude/hooks/, .claude/commands/, .claude/mcp-servers/

Tokenization mirrors redirect-bash-to-mcp.py (shlex, punctuation_chars=True)
so separators and quoting are honored. Malformed shell falls back to a raw
marker+write-indicator scan and fails closed.
"""

from __future__ import annotations

import json
import os
import re
import shlex
import sys


DOTFILES_REPO = os.path.realpath(os.path.expanduser("~/Repos/dotfiles"))
HOME = os.path.realpath(os.path.expanduser("~"))

# Managed config surface, as paths relative to either the repo root or $HOME.
MANAGED_FILES = (
    ".claude/settings.json",
    ".claude/settings.local.json",
    ".claude/statusline.sh",
)
MANAGED_PREFIXES = (
    ".agents/",
    ".claude/hooks/",
    ".claude/commands/",
    ".claude/mcp-servers/",
)

# Substrings that are invariant tails of any managed path regardless of how
# it is written (relative, ~-prefixed, absolute repo, or absolute home). Used
# for the interpreter raw-scan and the malformed-shell fallback.
MARKERS = MANAGED_FILES + MANAGED_PREFIXES

SEPARATOR_TOKENS = {"&&", "||", ";", "|", "&"}
REDIRECT_OPS = {">", ">>", ">|", "&>", "&>>"}
INTERPRETERS = {"python", "python3", "perl", "ruby", "node"}
FILE_TARGET_CMDS = {"tee", "truncate"}
DEST_CMDS = {"cp", "mv", "install", "ln", "rsync"}

ENV_PREFIX_RE = re.compile(r"^[A-Za-z_]\w*=")
WRITE_INDICATOR_RE = re.compile(r">>?|>\||\btee\b|\bsed\b[^\n]*\s-i|\bdd\b[^\n]*\bof=")


def _tokenize(command: str) -> list[str] | None:
    lex = shlex.shlex(command, posix=True, punctuation_chars=True)
    lex.whitespace_split = True
    try:
        return list(lex)
    except ValueError:
        return None


def resolve(tok: str, cwd: str) -> str:
    """Resolve a path token to an absolute, normalized path (no realpath — the
    target may not exist yet)."""
    p = os.path.expanduser(tok)
    if not os.path.isabs(p):
        p = os.path.join(cwd or HOME, p)
    return os.path.normpath(p)


def is_managed(abs_path: str) -> bool:
    """True if abs_path is a managed config file in the repo or its ~ mirror."""
    for root in (DOTFILES_REPO, HOME):
        rel = os.path.relpath(abs_path, root)
        if rel.startswith(".."):
            continue
        rel = rel.replace(os.sep, "/")
        if rel in MANAGED_FILES:
            return True
        if any(rel == p.rstrip("/") or rel.startswith(p) for p in MANAGED_PREFIXES):
            return True
    return False


def _is_inplace(flag: str) -> bool:
    # GNU `-i`, `--in-place`, BSD `-i ''`/`-i.bak`, combined `-ie`.
    return flag == "--in-place" or (flag.startswith("-i") and not flag.startswith("--"))


def _segments(tokens: list[str]):
    seg: list[str] = []
    for tok in tokens:
        if tok in SEPARATOR_TOKENS:
            if seg:
                yield seg
            seg = []
        else:
            seg.append(tok)
    if seg:
        yield seg


def _write_targets(seg: list[str]) -> tuple[str | None, list[str]]:
    """Return (command_basename, write-target tokens) for one pipeline segment."""
    targets: list[str] = []
    # Redirect targets: the token after any redirect operator, anywhere.
    for idx, tok in enumerate(seg):
        if tok in REDIRECT_OPS and idx + 1 < len(seg):
            targets.append(seg[idx + 1])

    # Command word: first token past leading env-var assignments.
    i = 0
    while i < len(seg) and ENV_PREFIX_RE.match(seg[i]):
        i += 1
    if i >= len(seg):
        return None, targets
    cmd = os.path.basename(seg[i])
    args = seg[i + 1:]

    # Positional args (drop flags and redirect op/operand pairs).
    positionals: list[str] = []
    a = 0
    while a < len(args):
        t = args[a]
        if t in REDIRECT_OPS:
            a += 2
            continue
        if t.startswith("-"):
            a += 1
            continue
        positionals.append(t)
        a += 1

    if cmd in FILE_TARGET_CMDS:
        targets.extend(positionals)
    elif cmd in DEST_CMDS:
        targets.extend(positionals)  # liberal: any managed path as src or dest
    elif cmd == "dd":
        targets.extend(t[3:] for t in args if t.startswith("of="))
    elif cmd == "sed" and any(_is_inplace(t) for t in args):
        targets.extend(positionals)
    return cmd, targets


def find_violation(command: str, cwd: str) -> str | None:
    """Return the offending managed path (display form), or None."""
    tokens = _tokenize(command)
    if tokens is None:
        # Malformed shell: deny only if a marker AND a write indicator coexist.
        if any(m in command for m in MARKERS) and WRITE_INDICATOR_RE.search(command):
            return next(m for m in MARKERS if m in command)
        return None

    for seg in _segments(tokens):
        cmd, targets = _write_targets(seg)
        for t in targets:
            if is_managed(resolve(t, cwd)):
                return t
        if cmd in INTERPRETERS:
            hit = next((m for m in MARKERS if m in " ".join(seg)), None)
            if hit:
                return hit
    return None


def main() -> None:
    data = json.load(sys.stdin)
    if data.get("tool_name") != "Bash":
        return
    command = data.get("tool_input", {}).get("command", "")
    if not command:
        return
    cwd = data.get("cwd", "") or os.getcwd()
    hit = find_violation(command, cwd)
    if hit is None:
        return
    msg = (
        f"`{hit}` is a dotfiles-managed config path. Don't mutate it from Bash — "
        f"Bash writes bypass the config redirect hook and the sandbox blocks them. "
        f"Edit the canonical source under ~/Repos/dotfiles with the Edit/Write tool, "
        f"then deploy with `mcp__unsandboxed-runner__save_config`. "
        f"If you only need to READ it, use the Read tool. "
        f"Consult the `config` skill. Hook: ~/.claude/hooks/redirect-bash-config-writes.py."
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
