#!/usr/bin/env python3
"""Stop hook: speak the turn's final line AFTER it renders in the terminal.

The `end-of-turn-report` rule says the main agent delivers a brief spoken
update every time control returns to the user, with a user-ratified ordering:
the turn's final text renders in the terminal FIRST, the speech follows.
Terminal UIs render only the text after the turn's last tool call, so the
agent cannot both end with text and end with a TTS call. This hook closes the
gap from the harness side: it fires on Stop — after the final text has
rendered — and speaks then.

Contract with the agent: by the `end-of-turn-report` convention the agent
ends every text-terminated final message with a literal last line of the form
`Summary: <Dirname>. <phrase>.`. This hook takes the final message's last
non-empty line, strips the `Summary:` label, normalizes it, and speaks the
remainder — so the spoken line is exactly the last text the user sees, it
leads with the working directory's basename, and it never contains the word
"summary".

Source of the final message: the `last_assistant_message` field of the Stop
event (coerced to "" when null/absent/non-string). If a harness omits the
field entirely, a minimal transcript parse recovers the last assistant text
block as a fallback. Empty final text (a turn that ends on a tool call) speaks
nothing — silence is correct and fail-safe there.

The hook returns immediately in every case (always allow the stop). The mute
check and the blocking `dic` call run in a DETACHED re-invocation of this same
script (Popen with start_new_session=True, all stdio to devnull), so the hook
never blocks the user. `dic`'s default voice is bf_isabella — the same default
the run_dic MCP wrapper uses; the text is fed to `dic` via stdin so no argv
quoting issues arise. Mute (`dic-status -q` exit 0) is honored in the child,
the same way the run_dic wrapper honors it.

Only the main agent speaks — workers must NOT ("Orchestrators speak; workers
do not", per the orchestrate skill). Three layers enforce that:

1. Registered under `Stop`, not `SubagentStop`. Classic Agent-tool workers fire
   `SubagentStop` (Stop auto-converts), so they are never reached here.
2. Teammate sessions (spawned under `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS`) are
   full sessions that fire `Stop` like the main agent, so layer 1 does not
   catch them. They are identified by an `{"type": "agent-setting"}` entry in
   their transcript (the recorded subagent type) — a marker the main session's
   transcript never carries. When present, this hook no-ops.
3. Headless runs: `AGENT_HEADLESS=1` (set by the `agent` wrapper's `-p` mode,
   and by scripts calling `claude -p` directly — see LAW.md, "Headless agent
   calls declare themselves") is inherited by this hook process. Nobody is at
   the keyboard to hear a headless session.

Re-entry safety: when another Stop hook blocks (Stop hooks run in PARALLEL, so
this hook fires — and speaks — on the same attempt that gets blocked), the
harness re-enters with `stop_hook_active: true`. This hook then stays silent:
the first attempt already spoke, and double-speaking is worse than silence.

Fails OPEN on any parse error — a broken hook must never delay or trap the
user; on any doubt it allows the stop silently. The detached child never
surfaces errors into the terminal; successes and failures leave a breadcrumb
in /tmp/claude/voice-report.log (size-capped, rotated at ~64 KB).

Test seams: `DIC_BIN` / `DIC_STATUS_BIN` env vars override the external
binaries so every branch can be exercised without audio.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time

BREADCRUMB_LOG = "/tmp/claude/voice-report.log"
LOG_CAP_BYTES = 64 * 1024

_SUMMARY_LABEL_RE = re.compile(
    r"^\s*summary\b\s*(?:of\b[^:–—-]*)?[:–—-]\s*(.*)$",
    re.IGNORECASE,
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


def _log(msg: str) -> None:
    """Best-effort, size-capped breadcrumb; never surfaces errors."""
    try:
        os.makedirs(os.path.dirname(BREADCRUMB_LOG), exist_ok=True)
        try:
            if os.path.getsize(BREADCRUMB_LOG) > LOG_CAP_BYTES:
                os.replace(BREADCRUMB_LOG, BREADCRUMB_LOG + ".1")
        except OSError:
            pass
        with open(BREADCRUMB_LOG, "a", encoding="utf-8") as fh:
            fh.write(f"{time.strftime('%Y-%m-%dT%H:%M:%S')} {msg}\n")
    except OSError:
        pass


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
        _log(f"spoke: {text!r}")
    except (OSError, subprocess.SubprocessError) as exc:
        _log(f"dic failed: {exc}")


def _spawn_detached(extra_env: dict[str, str]) -> None:
    env = dict(os.environ)
    env.update(extra_env)
    try:
        subprocess.Popen(
            [sys.executable, os.path.abspath(__file__), "--speak"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
            env=env,
        )
    except OSError as exc:
        _log(f"spawn failed: {exc}")


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
    """Concatenated text blocks of the last assistant entry that has any.

    Fallback source only — used when the Stop event omits
    `last_assistant_message` entirely.
    """
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


def _resolve_text(data: dict) -> str:
    """The turn's final text: `last_assistant_message` (coerced), or a
    transcript fallback only when the field is omitted entirely."""
    if "last_assistant_message" in data and data["last_assistant_message"] is not None:
        raw = data["last_assistant_message"]
        return raw if isinstance(raw, str) else ""
    transcript_path = data.get("transcript_path") or ""
    return _final_assistant_text(transcript_path) if transcript_path else ""


def _strip_md(text: str) -> str:
    """Strip leading bullets/blockquote markers and inline emphasis for speech."""
    text = text.strip()
    text = re.sub(r"^\s*(?:[>\-+*]\s+)+", "", text)
    text = re.sub(r"`+", "", text)
    text = re.sub(r"\*+", "", text)
    text = re.sub(r"(?<!\w)_+|_+(?!\w)", "", text)
    return text.strip()


def _strip_summary_label(line: str) -> str:
    """Remove a leading summary label tolerantly. Runs whether or not the line
    looked canonical, so a summary-*like* line can never speak the word."""
    m = _SUMMARY_LABEL_RE.match(line)
    if m:
        line = m.group(1)
    line = re.sub(
        r"^\s*summary\b[\s:.–—-]*", "", line, count=1, flags=re.IGNORECASE
    )
    return line.strip()


def _speechify(name: str) -> str:
    s = re.sub(r"[-_.]+", " ", name)
    s = re.sub(r"\s+", " ", s).strip()
    return s.title()


def _key(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.lower())


def _spoken_from_text(text: str, cwd: str) -> str:
    """Build the line to speak, or "" when there is nothing to say.

    Guarantees (both the canonical and the fallback path): the result never
    contains the word "summary", and it leads with the cwd basename.
    """
    text = (text or "").strip()
    if not text:
        return ""
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if not lines:
        return ""
    line = _strip_md(lines[-1])
    line = _strip_summary_label(line)
    remainder = _strip_md(line)

    base = _speechify(os.path.basename((cwd or "").rstrip("/"))) or "Session"
    if base and remainder and _key(remainder).startswith(_key(base)):
        spoken = remainder
    else:
        spoken = f"{base}. {remainder}".strip()

    return spoken.strip()


def hook_main() -> None:
    # Headless run (`agent -p`): nobody is listening — never speak.
    if os.environ.get("AGENT_HEADLESS"):
        return

    data = json.load(sys.stdin)

    # Re-entry after another parallel Stop hook blocked: the first attempt
    # already spoke — don't double-speak.
    if data.get("stop_hook_active"):
        return

    transcript_path = data.get("transcript_path") or ""

    # Teammate session (agent-teams worker): workers do not speak.
    if transcript_path and _is_teammate(transcript_path):
        return

    cwd = data.get("cwd") or os.getcwd()
    spoken = _spoken_from_text(_resolve_text(data), cwd)
    if not spoken:
        # Turn ended on a tool call (no final text) — silence is correct.
        return

    _spawn_detached({"SPEAK_TEXT": spoken})


def child_main() -> None:
    if _muted():
        _log("muted; not speaking")
        return
    text = os.environ.get("SPEAK_TEXT", "").strip()
    if text:
        _speak(text)


if __name__ == "__main__":
    try:
        if len(sys.argv) > 1 and sys.argv[1] == "--speak":
            child_main()
        else:
            hook_main()
    except Exception:
        # Fail open: never delay or trap the user behind a broken hook.
        pass
