#!/usr/bin/env python3
"""Stop hook: speak the end-of-turn report AFTER the turn's final text renders.

The `end-of-turn-report` rule says the main agent delivers a brief spoken
update every time control returns to the user, with a user-ratified ordering:
the turn's final text renders in the terminal FIRST, the speech follows.
Terminal UIs render only the text after the turn's last tool call, so the
agent cannot both end with text and end with a TTS call. This hook closes the
gap from the harness side: it fires on Stop — after the final text has
rendered — and speaks then.

Two sources for the spoken line, in order:

1. **Staged marker (preferred).** During the turn the agent writes the crafted
   line to `/tmp/claude/voice-report-<cwd-slug>.txt`, where cwd-slug is the
   working directory with `/` replaced by `-` (the same encoding the harness
   uses for its per-project tmp dirs, e.g. `-Users-william-Repos-sanctora`).
   Both sides derive it identically: the agent from `$(pwd | tr '/' '-')`,
   this hook from the `cwd` field in its stdin JSON. Concurrent sessions in
   the *same* project directory share a marker — a documented, accepted edge
   on this single-user machine (a session whose marker was eaten degrades to
   source 2). Marker present, non-empty, and younger than 30 minutes: speak
   it. The marker is DELETED before the speaker is spawned, so a re-fired
   Stop can never double-speak; a marker older than the TTL (orphaned by a
   killed session) is deleted unspoken. The agent stages atomically
   (temp-file + `mv`) so a half-written line is never read.
2. **Auto-fallback (safety net — nothing ever blocks).** No marker: derive a
   line as `<cwd basename, capitalized>. ` + a short summary of the turn's
   final assistant message (read from the transcript). The summary comes from
   a detached `claude -p ... --model haiku` call (run with `AGENT_HEADLESS=1`
   per LAW.md — it is a headless pipeline consuming programmatic output);
   if the CLI is missing or errors, the first ~15 words of the final text
   stand in. No final text at all: speak "Done."

The hook itself returns immediately in every case (always allow the stop):
all TTS/summarization work runs in a DETACHED re-invocation of this same
script (`--speak` / `--speak-summary` subcommands; Popen with
start_new_session=True, all stdio to devnull). Mute (`dic-status -q` exit 0)
is honored in the detached child, the same way the run_dic MCP wrapper honors
it. `dic`'s default voice is bf_isabella — the same default run_dic uses; the
text is fed to `dic` via stdin so no argv quoting issues arise.

Only the main agent speaks — workers must NOT ("Orchestrators speak; workers
do not", per the orchestrate skill). Two layers enforce that:

1. Registered under `Stop`, not `SubagentStop`. Classic Agent-tool workers fire
   `SubagentStop`, so they are never reached here.
2. Teammate sessions (spawned under `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS`) are
   full sessions that fire `Stop` like the main agent, so layer 1 does not
   catch them. They are identified by an `{"type": "agent-setting"}` entry in
   their transcript (the recorded subagent type) — a marker the main session's
   transcript never carries. When present, this hook no-ops BEFORE touching
   the staged marker (teammates share the main session's cwd, so consuming it
   would eat the main agent's staged line).

Headless runs are exempt too: `AGENT_HEADLESS=1` (set by the `agent` wrapper's
`-p` mode, and by scripts calling `claude -p` directly — see LAW.md, "Headless
agent calls declare themselves") is inherited by this hook process. Nobody is
at the keyboard to hear a headless session.

Re-entry safety: when another Stop hook blocks, the harness re-enters with
`stop_hook_active: true`. A freshly staged marker still plays then, but the
auto-fallback is skipped — the fallback already spoke on the first attempt,
and double-speaking is worse than silence.

Fails OPEN on any parse error — a broken hook must never delay or trap the
user; on any doubt it allows the stop silently. The detached child never
surfaces errors into the terminal; failures leave a breadcrumb in
/tmp/claude/voice-report.log.

Test seams: `DIC_BIN` / `DIC_STATUS_BIN` / `CLAUDE_BIN` env vars override the
external binaries so every branch can be exercised without audio or API calls.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time

MARKER_DIR = "/tmp/claude"
BREADCRUMB_LOG = "/tmp/claude/voice-report.log"
MARKER_TTL_SECONDS = 30 * 60
SUMMARY_INPUT_CAP = 1500
FALLBACK_WORDS = 15
SUMMARY_PROMPT = (
    "Condense the following assistant message into one short spoken status "
    "phrase, at most 12 words, no preamble, no quotes, plain text only:\n\n"
)


def _dic_bin() -> str:
    return os.environ.get(
        "DIC_BIN", os.path.join(os.path.expanduser("~"), ".local", "bin", "dic")
    )


def _dic_status_bin() -> str:
    return os.environ.get(
        "DIC_STATUS_BIN",
        os.path.join(os.path.expanduser("~"), ".local", "bin", "dic-status"),
    )


def _claude_bin() -> str:
    return os.environ.get(
        "CLAUDE_BIN", shutil.which("claude") or "/opt/homebrew/bin/claude"
    )


def _muted() -> bool:
    try:
        return (
            subprocess.run(
                [_dic_status_bin(), "-q"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=5,
            ).returncode
            == 0
        )
    except (OSError, subprocess.SubprocessError):
        return False


def _speak(text: str) -> None:
    """Blocking dic call (only ever runs in the detached child)."""
    try:
        subprocess.run(
            [_dic_bin()],
            input=text,
            text=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=600,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        _log(f"dic failed: {exc}")


def _summarize(final_text: str) -> str:
    """One-phrase summary via `claude -p`; falls back to the leading words."""
    tail = final_text[-SUMMARY_INPUT_CAP:]
    try:
        env = dict(os.environ, AGENT_HEADLESS="1")
        r = subprocess.run(
            [_claude_bin(), "-p", SUMMARY_PROMPT + tail, "--model", "haiku"],
            capture_output=True,
            text=True,
            timeout=120,
            env=env,
        )
        if r.returncode == 0:
            line = " ".join(r.stdout.split())
            if line:
                return line
        _log(f"claude summarizer exit {r.returncode}; using truncation fallback")
    except (OSError, subprocess.SubprocessError) as exc:
        _log(f"claude summarizer failed: {exc}; using truncation fallback")
    return " ".join(final_text.split()[:FALLBACK_WORDS])


def _spawn_detached(argv: list[str], extra_env: dict[str, str] | None = None) -> None:
    env = dict(os.environ)
    if extra_env:
        env.update(extra_env)
    try:
        subprocess.Popen(
            [sys.executable, os.path.abspath(__file__), *argv],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
            env=env,
        )
    except OSError:
        pass


def _is_teammate(transcript_path: str) -> bool:
    """True if the transcript carries an agent-teams `agent-setting` entry."""
    try:
        with open(transcript_path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if entry.get("type") == "agent-setting":
                    return True
    except OSError:
        pass
    return False


def _final_assistant_text(transcript_path: str) -> str:
    """Concatenated text blocks of the last assistant entry that has any."""
    final = ""
    try:
        with open(transcript_path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if entry.get("type") != "assistant":
                    continue
                content = entry.get("message", {}).get("content")
                if not isinstance(content, list):
                    continue
                texts = [
                    b.get("text", "")
                    for b in content
                    if isinstance(b, dict) and b.get("type") == "text"
                ]
                joined = "\n".join(t for t in texts if t).strip()
                if joined:
                    final = joined
    except OSError:
        pass
    return final


def _log(msg: str) -> None:
    """Best-effort breadcrumb; a detached process must never surface errors."""
    try:
        with open(BREADCRUMB_LOG, "a", encoding="utf-8") as fh:
            fh.write(f"{time.strftime('%Y-%m-%dT%H:%M:%S')} {msg}\n")
    except OSError:
        pass


def _consume_marker(cwd: str) -> str:
    """Read and DELETE the marker (delete-before-speak keeps re-fired Stops
    idempotent), returning '' when absent, unreadable, or older than the TTL
    (a marker orphaned by a killed session must not be spoken later)."""
    marker = os.path.join(MARKER_DIR, f"voice-report-{cwd.replace('/', '-')}.txt")
    try:
        stale = time.time() - os.stat(marker).st_mtime > MARKER_TTL_SECONDS
    except OSError:
        return ""
    text = ""
    if not stale:
        try:
            with open(marker, encoding="utf-8") as fh:
                text = fh.read().strip()
        except OSError:
            text = ""
    try:
        os.unlink(marker)
    except OSError:
        pass
    if stale:
        _log(f"stale marker discarded: {marker}")
    return text


def hook_main() -> None:
    # Headless run (`agent -p`): nobody is listening — never speak.
    if os.environ.get("AGENT_HEADLESS"):
        return

    data = json.load(sys.stdin)

    transcript_path = data.get("transcript_path") or ""

    # Teammate session (agent-teams worker): no-op before touching the marker
    # — teammates share the main session's cwd. Workers do not speak.
    if transcript_path and _is_teammate(transcript_path):
        return

    cwd = data.get("cwd") or os.getcwd()

    staged = _consume_marker(cwd)
    if staged:
        _spawn_detached(["--speak", staged])
        return

    # Re-entry after another Stop hook blocked: the fallback already spoke on
    # the first attempt — don't double-speak.
    if data.get("stop_hook_active"):
        return

    prefix = (os.path.basename(cwd.rstrip("/")) or "Session").capitalize() + "."
    final_text = _final_assistant_text(transcript_path) if transcript_path else ""
    _spawn_detached(["--speak-summary", prefix], {"FINAL_TEXT": final_text})


def child_main(argv: list[str]) -> None:
    if _muted():
        return
    if argv[0] == "--speak" and len(argv) > 1:
        _speak(argv[1])
    elif argv[0] == "--speak-summary" and len(argv) > 1:
        prefix = argv[1]
        final_text = os.environ.get("FINAL_TEXT", "").strip()
        line = _summarize(final_text) if final_text else "Done."
        _speak(f"{prefix} {line}")


if __name__ == "__main__":
    try:
        if len(sys.argv) > 1 and sys.argv[1].startswith("--speak"):
            child_main(sys.argv[1:])
        else:
            hook_main()
    except Exception:
        # Fail open: never delay or trap the user behind a broken hook.
        pass
