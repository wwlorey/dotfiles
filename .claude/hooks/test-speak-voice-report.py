#!/usr/bin/env python3
"""Tests for speak-voice-report.py.

Pure-function tests import the hook module and exercise the label/basename
normalization directly. End-to-end tests run the hook as a subprocess with
stub `dic` / `dic-status` binaries (DIC_BIN / DIC_STATUS_BIN seams) so every
branch is covered without real audio.

Run: python3 test-speak-voice-report.py
"""

from __future__ import annotations

import importlib.util
import json
import os
import stat
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
HOOK = os.path.join(HERE, "speak-voice-report.py")

_spec = importlib.util.spec_from_file_location("svr", HOOK)
mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mod)

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


# --------------------------------------------------------------------------
# Pure-function tests: label + basename normalization
# --------------------------------------------------------------------------

SANCT = "/Users/x/sanctora"


def t_canonical() -> None:
    out = mod._spoken_from_text(
        "Summary: Sanctora. Build green, ready to ship.", SANCT
    )
    check(
        "canonical_summary_speaks_remainder_minus_label",
        out == "Sanctora. Build green, ready to ship.",
        repr(out),
    )
    check("canonical_no_summary_word", "summary" not in out.lower(), repr(out))


def t_last_nonempty_line() -> None:
    text = "Here is the report.\nDetails above.\n\nSummary: Sanctora. Done."
    out = mod._spoken_from_text(text, SANCT)
    check("last_nonempty_line_used", out == "Sanctora. Done.", repr(out))


def t_summary_of_changes() -> None:
    out = mod._spoken_from_text("Summary of changes: updated the parser.", SANCT)
    check(
        "summary_of_changes_no_summary_word",
        "summary" not in out.lower(),
        repr(out),
    )
    check(
        "summary_of_changes_prepends_basename",
        out.startswith("Sanctora."),
        repr(out),
    )


def t_bold_summary() -> None:
    out = mod._spoken_from_text("**Summary:** all tests pass", SANCT)
    check("bold_summary_no_summary_word", "summary" not in out.lower(), repr(out))
    check("bold_summary_no_asterisk", "*" not in out, repr(out))


def t_emdash_summary() -> None:
    out = mod._spoken_from_text("Summary — done deal", SANCT)
    check("emdash_summary_no_summary_word", "summary" not in out.lower(), repr(out))
    check("emdash_summary_has_content", "done deal" in out.lower(), repr(out))


def t_prepend_missing_basename() -> None:
    out = mod._spoken_from_text("Build green.", SANCT)
    check("prepend_when_missing", out == "Sanctora. Build green.", repr(out))


def t_no_double_basename_variant() -> None:
    out = mod._spoken_from_text(
        "Summary: Lsr-app. Tests pass.", "/Users/x/lsr-app"
    )
    check("no_double_basename", out == "Lsr-app. Tests pass.", repr(out))
    check(
        "no_double_basename_not_prefixed_twice",
        not out.lower().startswith("lsr app. lsr"),
        repr(out),
    )


def t_basename_speechify() -> None:
    out = mod._spoken_from_text("did it.", "/Users/x/lsr-app")
    check("speechify_hyphen", out == "Lsr App. did it.", repr(out))


def t_markdown_backticks() -> None:
    out = mod._spoken_from_text("`run_dic` invoked cleanly", SANCT)
    check("backticks_stripped", "`" not in out, repr(out))
    check("underscore_identifier_preserved", "run_dic" in out, repr(out))


def t_bullet_stripped() -> None:
    out = mod._spoken_from_text("- Summary: Sanctora. Bulleted line.", SANCT)
    check(
        "leading_bullet_and_label_stripped",
        out == "Sanctora. Bulleted line.",
        repr(out),
    )


def t_long_line_uncapped() -> None:
    body = " ".join(f"word{i}" for i in range(60))
    out = mod._spoken_from_text(body, SANCT)
    check("long_line_spoken_in_full", out.endswith("word59"), repr(out))
    check("long_line_leads_basename", out.startswith("Sanctora."), repr(out))


def t_empty_silent() -> None:
    check("empty_text_silent", mod._spoken_from_text("", SANCT) == "")
    check("whitespace_text_silent", mod._spoken_from_text("   \n  ", SANCT) == "")


def t_resolve_text_falsy() -> None:
    check("resolve_absent", mod._resolve_text({}) == "")
    check("resolve_null", mod._resolve_text({"last_assistant_message": None}) == "")
    check(
        "resolve_nonstring",
        mod._resolve_text({"last_assistant_message": 123}) == "",
    )
    check(
        "resolve_string",
        mod._resolve_text({"last_assistant_message": "hi"}) == "hi",
    )


def t_resolve_text_transcript_fallback() -> None:
    with tempfile.TemporaryDirectory() as d:
        tp = os.path.join(d, "t.jsonl")
        with open(tp, "w", encoding="utf-8") as fh:
            fh.write(
                json.dumps(
                    {
                        "type": "assistant",
                        "message": {
                            "content": [
                                {"type": "text", "text": "Summary: Sanctora. Fell back."}
                            ]
                        },
                    }
                )
                + "\n"
            )
        # field omitted entirely -> transcript fallback
        out = mod._resolve_text({"transcript_path": tp})
        check("transcript_fallback", out == "Summary: Sanctora. Fell back.", repr(out))


def t_log_size_cap() -> None:
    with tempfile.TemporaryDirectory() as d:
        logpath = os.path.join(d, "voice-report.log")
        old = mod.BREADCRUMB_LOG
        mod.BREADCRUMB_LOG = logpath
        try:
            with open(logpath, "w", encoding="utf-8") as fh:
                fh.write("x" * (mod.LOG_CAP_BYTES + 1000))
            mod._log("after overflow")
            size = os.path.getsize(logpath)
            check("log_rotated_small", size < 1000, f"size={size}")
            check("log_rotation_kept_old", os.path.exists(logpath + ".1"))
        finally:
            mod.BREADCRUMB_LOG = old


# --------------------------------------------------------------------------
# End-to-end tests: subprocess + stub binaries
# --------------------------------------------------------------------------


def _write_exec(path: str, body: str) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(body)
    os.chmod(path, os.stat(path).st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)


def _make_stubs(d: str) -> tuple[str, str]:
    dic = os.path.join(d, "dic")
    _write_exec(
        dic,
        "#!/usr/bin/env python3\n"
        "import os, sys\n"
        "open(os.environ['DIC_OUT'], 'a').write(sys.stdin.read())\n",
    )
    dic_status = os.path.join(d, "dic-status")
    _write_exec(
        dic_status,
        "#!/usr/bin/env python3\n"
        "import os, sys\n"
        "sys.exit(0 if os.environ.get('DIC_MUTED') == '1' else 1)\n",
    )
    return dic, dic_status


def _run_hook(stdin_obj: dict, extra_env: dict, out_path: str, wait_for: bool) -> str | None:
    env = dict(os.environ)
    env.update(extra_env)
    subprocess.run(
        [sys.executable, HOOK],
        input=json.dumps(stdin_obj),
        text=True,
        env=env,
        timeout=30,
    )
    deadline = time.time() + (10.0 if wait_for else 2.5)
    while time.time() < deadline:
        if os.path.exists(out_path) and os.path.getsize(out_path) > 0:
            return open(out_path, encoding="utf-8").read()
        time.sleep(0.1)
    return open(out_path, encoding="utf-8").read() if os.path.exists(out_path) else None


def _base_env(d: str, dic: str, dic_status: str, out_path: str, muted: bool) -> dict:
    env = {
        "DIC_BIN": dic,
        "DIC_STATUS_BIN": dic_status,
        "DIC_OUT": out_path,
        "DIC_MUTED": "1" if muted else "0",
    }
    env.pop("AGENT_HEADLESS", None)
    return env


def t_e2e_speaks_when_unmuted() -> None:
    with tempfile.TemporaryDirectory() as d:
        dic, dic_status = _make_stubs(d)
        out = os.path.join(d, "spoken.txt")
        stdin = {
            "cwd": SANCT,
            "last_assistant_message": "Summary: Sanctora. Build green.",
        }
        env = _base_env(d, dic, dic_status, out, muted=False)
        env["AGENT_HEADLESS"] = ""
        got = _run_hook(stdin, env, out, wait_for=True)
        check(
            "e2e_speaks_unmuted",
            got is not None and got.strip() == "Sanctora. Build green.",
            repr(got),
        )


def t_e2e_muted_silent() -> None:
    with tempfile.TemporaryDirectory() as d:
        dic, dic_status = _make_stubs(d)
        out = os.path.join(d, "spoken.txt")
        stdin = {
            "cwd": SANCT,
            "last_assistant_message": "Summary: Sanctora. Build green.",
        }
        env = _base_env(d, dic, dic_status, out, muted=True)
        got = _run_hook(stdin, env, out, wait_for=False)
        check("e2e_muted_silent", not got, repr(got))


def t_e2e_headless_silent() -> None:
    with tempfile.TemporaryDirectory() as d:
        dic, dic_status = _make_stubs(d)
        out = os.path.join(d, "spoken.txt")
        stdin = {
            "cwd": SANCT,
            "last_assistant_message": "Summary: Sanctora. Build green.",
        }
        env = _base_env(d, dic, dic_status, out, muted=False)
        env["AGENT_HEADLESS"] = "1"
        got = _run_hook(stdin, env, out, wait_for=False)
        check("e2e_headless_silent", not got, repr(got))


def t_e2e_stop_hook_active_silent() -> None:
    with tempfile.TemporaryDirectory() as d:
        dic, dic_status = _make_stubs(d)
        out = os.path.join(d, "spoken.txt")
        stdin = {
            "cwd": SANCT,
            "last_assistant_message": "Summary: Sanctora. Build green.",
            "stop_hook_active": True,
        }
        env = _base_env(d, dic, dic_status, out, muted=False)
        got = _run_hook(stdin, env, out, wait_for=False)
        check("e2e_stop_hook_active_silent", not got, repr(got))


def t_e2e_teammate_silent() -> None:
    with tempfile.TemporaryDirectory() as d:
        dic, dic_status = _make_stubs(d)
        out = os.path.join(d, "spoken.txt")
        tp = os.path.join(d, "teammate.jsonl")
        with open(tp, "w", encoding="utf-8") as fh:
            fh.write(json.dumps({"type": "agent-setting", "subagent": "x"}) + "\n")
            fh.write(
                json.dumps(
                    {
                        "type": "assistant",
                        "message": {
                            "content": [
                                {"type": "text", "text": "Summary: Sanctora. Done."}
                            ]
                        },
                    }
                )
                + "\n"
            )
        stdin = {
            "cwd": SANCT,
            "transcript_path": tp,
            "last_assistant_message": "Summary: Sanctora. Done.",
        }
        env = _base_env(d, dic, dic_status, out, muted=False)
        got = _run_hook(stdin, env, out, wait_for=False)
        check("e2e_teammate_silent", not got, repr(got))


def t_e2e_tool_terminated_no_error() -> None:
    with tempfile.TemporaryDirectory() as d:
        dic, dic_status = _make_stubs(d)
        out = os.path.join(d, "spoken.txt")
        stdin = {"cwd": SANCT, "last_assistant_message": ""}
        env = _base_env(d, dic, dic_status, out, muted=False)
        # Should exit 0 and speak nothing.
        r = subprocess.run(
            [sys.executable, HOOK],
            input=json.dumps(stdin),
            text=True,
            env=dict(os.environ, **env),
            timeout=30,
        )
        check("e2e_tool_terminated_exit0", r.returncode == 0, str(r.returncode))
        time.sleep(1.0)
        got = open(out, encoding="utf-8").read() if os.path.exists(out) else None
        check("e2e_tool_terminated_silent", not got, repr(got))


def main() -> None:
    for fn in [
        t_canonical,
        t_last_nonempty_line,
        t_summary_of_changes,
        t_bold_summary,
        t_emdash_summary,
        t_prepend_missing_basename,
        t_no_double_basename_variant,
        t_basename_speechify,
        t_markdown_backticks,
        t_bullet_stripped,
        t_long_line_uncapped,
        t_empty_silent,
        t_resolve_text_falsy,
        t_resolve_text_transcript_fallback,
        t_log_size_cap,
        t_e2e_speaks_when_unmuted,
        t_e2e_muted_silent,
        t_e2e_headless_silent,
        t_e2e_stop_hook_active_silent,
        t_e2e_teammate_silent,
        t_e2e_tool_terminated_no_error,
    ]:
        fn()
    print(f"\n{COUNT} checks, {len(FAILURES)} failed")
    if FAILURES:
        print("FAILED:", ", ".join(FAILURES))
        sys.exit(1)


if __name__ == "__main__":
    main()
