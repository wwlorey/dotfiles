#!/usr/bin/env python3
"""Tests for agent-spawn-reminder.py.

End-to-end tests run the hook as a subprocess with fabricated stdin JSON and a
fabricated transcript JSONL, asserting on the two `additionalContext` blocks:
the always-on orchestrate briefing reminder and the conditional dev-routing
nudge. Every case also asserts the orchestrate reminder still emits.

Run: python3 test-agent-spawn-reminder.py
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
HOOK = os.path.join(HERE, "agent-spawn-reminder.py")

ORCH_MARK = "Agent spawn checkpoint"
NUDGE_MARK = "Dev-routing checkpoint"

FAILURES: list[str] = []
COUNT = 0


def check(name: str, cond: bool, detail: str = "") -> None:
    global COUNT
    COUNT += 1
    if cond:
        print(f"PASS {name}")
    else:
        print(f"FAIL {name}  {detail}")
        FAILURES.append(name)


# ---- transcript entry builders -------------------------------------------

def user(text: str) -> dict:
    return {"type": "user", "message": {"content": text}}


def skill(name: str) -> dict:
    return {
        "type": "assistant",
        "message": {
            "content": [{"type": "tool_use", "name": "Skill", "input": {"skill": name}}]
        },
    }


TASK_NOTIF = (
    "<task-notification> <task-id>a58b0889324a0bad2</task-id> "
    "<tool-use-id>toolu_01xyz</tool-use-id> <status>completed</status> "
    "</task-notification>"
)

# A genuine implementation spawn: impl verb + issue slug + repo path, no
# read-only cue.
IMPL_PROMPT = (
    "implement issue lsr-widget-202607 end to end in "
    "crates/lsr-app/src/main.rs; wire the handler and add tests."
)

# A read-only gate spawn that ALSO carries an impl verb + repo cue (so it would
# fire without the read-only exclusion).
READONLY_PROMPT = (
    "security review of the pending changes on crates/lsr-app/src/main.rs. "
    "read-only, do not edit. Implement nothing; return findings only."
)


def run(stdin_text: str, transcript_entries: list[dict] | None) -> str:
    """Run the hook with the given stdin; return combined additionalContext."""
    tp = ""
    tmp = None
    if transcript_entries is not None:
        tmp = tempfile.NamedTemporaryFile(
            "w", suffix=".jsonl", delete=False, encoding="utf-8"
        )
        for e in transcript_entries:
            tmp.write(json.dumps(e) + "\n")
        tmp.close()
        tp = tmp.name
    # If caller passed a dict-shaped stdin, splice the transcript path in.
    payload = stdin_text
    if stdin_text.startswith("{DICT}"):
        obj = json.loads(stdin_text[len("{DICT}"):])
        obj["transcript_path"] = tp
        payload = json.dumps(obj)
    try:
        proc = subprocess.run(
            [sys.executable, HOOK],
            input=payload,
            capture_output=True,
            text=True,
            timeout=15,
        )
    finally:
        if tmp is not None:
            os.unlink(tmp.name)
    out = proc.stdout.strip()
    if not out:
        return ""
    data = json.loads(out)
    return data.get("hookSpecificOutput", {}).get("additionalContext", "")


def stdin_for(prompt: str) -> str:
    return "{DICT}" + json.dumps({"tool_name": "Agent", "tool_input": {"prompt": prompt}})


# ---- tests ---------------------------------------------------------------

def t_a_build_active_despite_notifications() -> None:
    """Impl spawn, build invoked then two task-notifications -> SILENT."""
    entries = [
        user("tackle the backlog"),
        skill("build"),
        user(TASK_NOTIF),
        user(TASK_NOTIF),
    ]
    ctx = run(stdin_for(IMPL_PROMPT), entries)
    check("T-A orchestrate emits", ORCH_MARK in ctx)
    check("T-A nudge SILENT (build active past notifications)", NUDGE_MARK not in ctx, ctx[:120])


def t_b_genuine_bypass() -> None:
    """Impl spawn, no dev-family skill since last genuine prompt -> PRESENT."""
    entries = [user("just spawn a worker to do this")]
    ctx = run(stdin_for(IMPL_PROMPT), entries)
    check("T-B orchestrate emits", ORCH_MARK in ctx)
    check("T-B nudge PRESENT (genuine bypass caught)", NUDGE_MARK in ctx, ctx[:120])


def t_c_readonly_review() -> None:
    """Read-only review/audit spawn, no dev-family -> SILENT (Facet 2)."""
    entries = [user("look into the security of this")]
    ctx = run(stdin_for(READONLY_PROMPT), entries)
    check("T-C orchestrate emits", ORCH_MARK in ctx)
    check("T-C nudge SILENT (read-only review)", NUDGE_MARK not in ctx, ctx[:120])


def t_d_notif_most_recent_build_precedes() -> None:
    """task-notification is most recent user entry, build precedes it -> SILENT."""
    entries = [
        user("work through the ready issues"),
        skill("build"),
        user(TASK_NOTIF),
    ]
    ctx = run(stdin_for(IMPL_PROMPT), entries)
    check("T-D orchestrate emits", ORCH_MARK in ctx)
    check("T-D nudge SILENT (build precedes trailing notification)", NUDGE_MARK not in ctx, ctx[:120])


def t_e_malformed_stdin() -> None:
    """Malformed stdin -> fail open, orchestrate reminder still emits."""
    ctx = run("this is not json {{{", None)
    check("T-E orchestrate emits on malformed stdin", ORCH_MARK in ctx)
    check("T-E no nudge on malformed stdin", NUDGE_MARK not in ctx, ctx[:120])


# ---- extra guards --------------------------------------------------------

def t_f_no_transcript_suppresses() -> None:
    """Impl spawn but transcript path empty/unreadable -> SILENT (no nagging)."""
    payload = json.dumps(
        {"tool_name": "Agent", "transcript_path": "", "tool_input": {"prompt": IMPL_PROMPT}}
    )
    ctx = run(payload, None)
    check("T-F orchestrate emits", ORCH_MARK in ctx)
    check("T-F nudge SILENT when window unknowable", NUDGE_MARK not in ctx, ctx[:120])


def t_g_list_content_genuine_prompt() -> None:
    """Genuine prompt as list content with trailing system-reminder still counts."""
    entries = [
        {
            "type": "user",
            "message": {
                "content": [
                    {"type": "text", "text": "tackle the backlog"},
                    {"type": "text", "text": "<system-reminder>ctx</system-reminder>"},
                ]
            },
        },
        skill("build"),
        user(TASK_NOTIF),
    ]
    ctx = run(stdin_for(IMPL_PROMPT), entries)
    check("T-G nudge SILENT (list genuine prompt + build active)", NUDGE_MARK not in ctx, ctx[:120])


def t_h_config_skill_spawn_mentions_sanctora() -> None:
    """Skill-creation spawn targeting ~/.agents that references a sanctora issue
    slug + repo path for context, no dev-family active -> SILENT (Facet 3)."""
    entries = [user("let's build the asc skill")]
    prompt = (
        "Create a new global skill under ~/.agents/skills/asc/. It packages App "
        "Store Connect automation; add the ES256 JWT client. For context, "
        "sanctora already has issues/asc-api-release-tooling-202607.md and "
        "wires it in crates/lsr-app. Do not touch sanctora source."
    )
    ctx = run(stdin_for(prompt), entries)
    check("T-H orchestrate emits", ORCH_MARK in ctx)
    check("T-H nudge SILENT (config/skill target, sanctora only mentioned)", NUDGE_MARK not in ctx, ctx[:120])


def t_i_dotfiles_hook_spawn() -> None:
    """Spawn whose target is a dotfiles/.claude hook -> SILENT (Facet 3)."""
    entries = [user("fix the guard hook")]
    prompt = (
        "In ~/Repos/dotfiles, fix .claude/hooks/route-dev-work.py so it stops "
        "false-firing. Add a regression test. This mirrors sanctora's "
        "crates/lsr-app conventions."
    )
    ctx = run(stdin_for(prompt), entries)
    check("T-I orchestrate emits", ORCH_MARK in ctx)
    check("T-I nudge SILENT (dotfiles hook target)", NUDGE_MARK not in ctx, ctx[:120])


def main() -> int:
    t_a_build_active_despite_notifications()
    t_b_genuine_bypass()
    t_c_readonly_review()
    t_d_notif_most_recent_build_precedes()
    t_e_malformed_stdin()
    t_f_no_transcript_suppresses()
    t_g_list_content_genuine_prompt()
    t_h_config_skill_spawn_mentions_sanctora()
    t_i_dotfiles_hook_spawn()
    print(f"\n{COUNT - len(FAILURES)}/{COUNT} checks passed")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
