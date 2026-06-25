#!/usr/bin/env python3
"""Stop hook: block end-of-turn if there are orphaned `status: in_progress`
issues in <cwd>/issues/ with stale recent activity, unless the orchestrator
has scheduled a wake-up to recover later.

Background: the `orchestrate` skill's "Missing notification" rule says when
an Async-launched Agent spawn never emits a terminal notification, the
orchestrator should re-verify within ~10 minutes. That rule lived in prose
and relied on orchestrator memory — and failed: a worker died after running
backpressure but before closing, and the session sat idle for 11 hours
before recovery.

This hook moves enforcement into the harness. If any `issues/<slug>.md`
file has `status: in_progress` AND the last git commit mentioning that slug
is older than the staleness threshold AND no ScheduleWakeup tool call has
fired in the current turn's transcript, block the Stop with a recovery
prompt.

Conventions inherited from the `issues` skill: per-repo `issues/` dir,
slug = file stem, `status: open|in_progress|closed` in frontmatter.

Loop/outage safety: `stop_hook_active: true` allows the second stop attempt,
so the orchestrator can always bypass with a deliberate second try after
seeing the block message. Fails OPEN on any exception.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import time
from pathlib import Path

# Threshold matching the orchestrate skill's "~5-10 minutes" rule
STALE_SECONDS = 10 * 60


def main() -> None:
    data = json.load(sys.stdin)
    # Already blocked once this turn — allow stop to avoid wedging.
    if data.get("stop_hook_active"):
        return

    cwd = Path.cwd()
    issues_dir = cwd / "issues"
    if not issues_dir.is_dir():
        return  # not an issues/ tracker project

    in_progress = _find_in_progress(issues_dir)
    if not in_progress:
        return  # no orphans

    stale = _find_stale(cwd, in_progress, STALE_SECONDS)
    if not stale:
        return  # all in_progress issues have recent commit activity — workers running

    transcript_path = data.get("transcript_path")
    if transcript_path and _scheduled_wakeup_this_turn(transcript_path):
        return  # orchestrator has scheduled recovery

    summary = "\n".join(f"  - {slug} (last commit on slug: {age})" for slug, age in stale)
    reason = (
        f"BLOCKED: {len(stale)} orphaned in-progress issue(s) with no recent "
        f"activity AND no ScheduleWakeup tool call this turn:\n"
        f"{summary}\n\n"
        f"Per the `orchestrate` skill's Missing-notification rule, do one:\n"
        f"  1. Inline-close — recover staged work (commit, push), edit "
        f"frontmatter `status: in_progress` -> `closed`, add a `## Comments` "
        f"closure entry. The check passes once status flips.\n"
        f"  2. ScheduleWakeup (recommended for non-trivial recovery) — call "
        f"`ScheduleWakeup` (15 min cadence) so the orchestrator re-enters and "
        f"re-checks. The hook allows stop once a ScheduleWakeup is in this "
        f"turn's transcript.\n"
        f"  3. Unclaim — revert frontmatter `in_progress` -> `open` with a "
        f"`## Comments` note explaining; commit + push so a future iteration "
        f"can re-claim cleanly.\n\n"
        f"After acting, try Stop again. If you genuinely want to defer despite "
        f"orphans, the second Stop attempt is allowed (stop_hook_active loop "
        f"guard) — the block message remains in the transcript as the audit "
        f"trail of deferred work.\n\n"
        f"Hook: ~/.claude/hooks/check-orphaned-claims.py"
    )
    print(json.dumps({"decision": "block", "reason": reason}))


def _find_in_progress(issues_dir: Path) -> list[str]:
    """Slugs whose frontmatter has `status: in_progress`."""
    out: list[str] = []
    pat = re.compile(r"^status:\s*in_progress\s*$", re.MULTILINE)
    for f in issues_dir.glob("*.md"):
        try:
            if pat.search(f.read_text(encoding="utf-8")):
                out.append(f.stem)
        except OSError:
            continue
    return out


def _find_stale(cwd: Path, slugs: list[str], threshold_s: int) -> list[tuple[str, str]]:
    """Slugs whose most-recent commit mention is older than threshold."""
    now = int(time.time())
    stale: list[tuple[str, str]] = []
    for slug in slugs:
        try:
            r = subprocess.run(
                ["git", "log", "-1", "--grep", slug, "--format=%ct"],
                cwd=str(cwd),
                capture_output=True,
                text=True,
                timeout=5,
            )
            if r.returncode != 0:
                stale.append((slug, "git error"))
                continue
            stdout = r.stdout.strip()
            if not stdout:
                stale.append((slug, "no commit mentions slug"))
                continue
            commit_unix = int(stdout)
            age_s = now - commit_unix
            if age_s > threshold_s:
                age_min = age_s // 60
                if age_min < 60:
                    age = f"{age_min} min ago"
                elif age_min < 60 * 24:
                    age = f"{age_min // 60}h {age_min % 60}m ago"
                else:
                    age = f"{age_min // (60 * 24)}d ago"
                stale.append((slug, age))
        except (subprocess.SubprocessError, ValueError):
            continue
    return stale


def _scheduled_wakeup_this_turn(transcript_path: str) -> bool:
    """True if a ScheduleWakeup tool_use appears after the last user prompt."""
    try:
        entries: list[dict] = []
        with open(transcript_path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        last_user = -1
        for idx, e in enumerate(entries):
            if e.get("type") != "user":
                continue
            content = e.get("message", {}).get("content")
            if isinstance(content, str) and content.strip():
                last_user = idx
            elif isinstance(content, list):
                has_text = any(b.get("type") == "text" for b in content if isinstance(b, dict))
                has_tool = any(b.get("type") == "tool_result" for b in content if isinstance(b, dict))
                if has_text and not has_tool:
                    last_user = idx
        for e in entries[last_user + 1 :]:
            if e.get("type") != "assistant":
                continue
            content = e.get("message", {}).get("content")
            if not isinstance(content, list):
                continue
            for block in content:
                if (
                    isinstance(block, dict)
                    and block.get("type") == "tool_use"
                    and block.get("name") == "ScheduleWakeup"
                ):
                    return True
    except OSError:
        pass
    return False


if __name__ == "__main__":
    try:
        main()
    except Exception:
        # Fail open: never trap the user behind a broken hook.
        pass
