#!/usr/bin/env python3
"""PreToolUse Bash gate: deny the AGENT from executing destructive/production
App Store Connect ops. The agent must never self-approve; those ops are run by
the USER (a `!`-prefixed command or a manual run bypasses PreToolUse — the user
running it IS the approval). Fail-open on any parse error; never block non-asc
or safe/read/draft/--dry-run commands.

Deny mechanism: exit 2 with the reason on stderr (Claude Code shows PreToolUse
exit-2 stderr to the agent as the block reason). Keep the destructive-op set in
sync with DESTRUCTIVE_OPS in the asc client (~/.agents/skills/asc/scripts/asc).
"""
import json
import re
import sys

# Kept in sync with DESTRUCTIVE_OPS in the asc client
# (~/.agents/skills/asc/scripts/asc). Two categories:
#   unconditional   — always production; blocked on the bare subcommand token.
#   state-dependent — SAFE to edit on a DRAFT in-app purchase, destructive on a
#                     LIVE/approved one. The client decides per-product and only
#                     attaches --approve-destructive when the product is live, so
#                     this hook must NOT block these on their bare token (that
#                     would wrongly block legitimate draft edits). They are
#                     caught instead by the --approve-destructive rule below,
#                     which fires exactly when the product is live.
DESTRUCTIVE_OPS = {
    "testers-remove":   "unconditional",   # DELETE /v1/betaTesters/{id}
    "build-assign":     "unconditional",   # distributes a build to testers
    "iap-rename":       "state-dependent",  # PATCH name of a live IAP
    "iap-price":        "state-dependent",  # price schedule on a live IAP
    "iap-availability": "state-dependent",  # availability on a live IAP
    "iap-screenshot":   "state-dependent",  # review screenshot on a live IAP
}


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0  # fail-open

    if data.get("tool_name") != "Bash":
        return 0
    cmd = (data.get("tool_input") or {}).get("command", "")
    if not isinstance(cmd, str) or not cmd:
        return 0

    # Only consider invocations of the asc client (bare `asc` or a path ending /asc).
    if not re.search(r"(^|[\s/;&|(])asc(\s|$)", cmd):
        return 0
    # A dry-run is a safe preview.
    if re.search(r"--dry-run\b", cmd):
        return 0

    hit = None
    if re.search(r"--approve-destructive", cmd):
        hit = "an approved destructive op"
    elif re.search(r"\bbuild-assign\b", cmd):
        hit = "build-assign (distributes a build to testers)"
    elif re.search(r"\btesters\s+remove\b", cmd):
        hit = "testers remove (deletes a beta tester)"
    if not hit:
        return 0

    sys.stderr.write(
        "DENIED: this is a destructive/production App Store Connect op "
        f"({hit}). The agent must NOT execute it. Classify it, prepare the exact "
        "`asc ... --approve-destructive=<op>` command, and hand it to the USER to "
        "run (a user-initiated / `!`-prefixed run bypasses this hook and IS the "
        "approval).\n"
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
