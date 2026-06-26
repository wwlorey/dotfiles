#!/usr/bin/env python3
"""jms_chat.py — answer replies to a JMS digest, by email.

Run once per launchd tick (~60s). Single-pass: connect to the ProtonMail Bridge
over IMAP, find replies addressed to `jms+<VIDEOID>.<TOKEN>@lorey.co`, answer the
question about that episode with `claude -p`, and reply in-thread via the
send-email skill. State (daily cap + answered set) lives in one JSON file under a
flock so overlapping ticks no-op.

Security model (see the jms skill's "Chat by email" section):
- The TOKEN in the recipient address is the only real gate; the @lorey.co sender
  check is unauthenticated defense-in-depth; the daily cap is the backstop.
- `claude -p` runs WITHOUT --dangerously-skip-permissions, so the untrusted email
  body / transcript can never make it run a tool — text only.
"""
from __future__ import annotations

import email
import email.utils
import fcntl
import json
import os
import re
import ssl
import subprocess
import sys
import uuid
from datetime import date, datetime, timedelta
from email import policy
from imaplib import IMAP4

HOME = os.path.expanduser("~")
STATE_DIR = os.path.join(HOME, ".local/state/jms-chat")
STATE_JSON = os.path.join(STATE_DIR, "state.json")
TOKEN_FILE = os.path.join(STATE_DIR, "reply-token")
DISABLED = os.path.join(STATE_DIR, "disabled")
LOCK_FILE = os.path.join(STATE_DIR, "lock")
LOG_FILE = os.path.join(STATE_DIR, "jms-chat.log")

BRIDGE_ENV = os.path.join(HOME, ".config/mail/bridge.env")
SEND_EMAIL = os.path.join(HOME, ".agents/skills/send-email/scripts/send-email.py")
FETCH_TRANSCRIPT = os.path.join(HOME, ".agents/skills/jms/scripts/fetch-transcript")

IMAP_HOST = "127.0.0.1"  # loopback-pinned (Bridge); never speak to a remote host
IMAP_PORT = 1143
FOLDER = '"All Mail"'    # self-addressed mail skips INBOX on a same-account setup
DOMAIN = "lorey.co"
BOT = "noreply@lorey.co"
SENDER = "noreply@lorey.co"

DAILY_CAP = 25
SINCE_DAYS = 3
BODY_CAP = 8000
TRANSCRIPT_CAP = 40000
CLAUDE_TIMEOUT = 150
SEND_TIMEOUT = 60

# Proton rewrites Reply-To and won't send as a +tag From, but it PRESERVES a
# custom Message-ID. So the episode id + token ride in the digest's Message-ID
# (`<jms.<VID>.<TOKEN>@lorey.co>`); a reply's In-Reply-To/References carries it.
# Answers add a `.<uniq>` so a reply to the answer still parses (multi-turn).
MID_RE = re.compile(
    r"<jms\.([A-Za-z0-9_-]+)\.([A-Za-z0-9]+)(?:\.[A-Za-z0-9]+)?@lorey\.co>",
    re.IGNORECASE,
)


def log(msg: str) -> None:
    line = f"[{datetime.now().isoformat(timespec='seconds')}] {msg}"
    try:
        fd = os.open(LOG_FILE, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
        os.write(fd, (line + "\n").encode())
        os.close(fd)
    except Exception:
        pass
    print(line, file=sys.stderr)


def load_creds() -> dict[str, str]:
    # launchd's minimal env lacks XDG_CONFIG_HOME, so sops can't locate the age
    # key by default — point it explicitly.
    env = dict(os.environ)
    env.setdefault("SOPS_AGE_KEY_FILE", os.path.expanduser("~/.config/sops/age/keys.txt"))
    out = subprocess.run(
        ["sops", "-d", "--output-type", "dotenv", BRIDGE_ENV],
        capture_output=True, text=True, check=True, env=env,
    ).stdout
    creds = {}
    for ln in out.splitlines():
        ln = ln.strip()
        if ln and not ln.startswith("#") and "=" in ln:
            k, v = ln.split("=", 1)
            creds[k.strip()] = v.strip()
    return creds


def load_state() -> dict:
    try:
        with open(STATE_JSON) as f:
            s = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        s = {}
    today = date.today().isoformat()
    if s.get("day") != today:
        s = {"day": today, "count": 0, "answered": s.get("answered", [])[-500:]}
    s.setdefault("answered", [])
    s.setdefault("count", 0)
    s.setdefault("day", today)
    return s


def save_state(s: dict) -> None:
    s["answered"] = s["answered"][-500:]
    tmp = STATE_JSON + ".tmp"
    with open(tmp, "w") as f:
        json.dump(s, f)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, STATE_JSON)


def thread_token(msg, token: str):
    """Return the VIDEOID (original case) from a jms.<VID>.<TOKEN>[.uniq] id in
    In-Reply-To/References whose token matches, else None."""
    refs = " ".join(msg.get_all("In-Reply-To", []) + msg.get_all("References", []))
    for m in MID_RE.finditer(refs):
        if m.group(2).lower() == token.lower():
            return m.group(1)
    return None


def sender_addr(msg):
    _, addr = email.utils.parseaddr(msg.get("From", ""))
    addr = addr.strip().lower()
    if not addr or "@" not in addr:
        return None
    if addr.rsplit("@", 1)[1] != DOMAIN or addr == BOT.lower():
        return None
    return addr


def is_auto(msg) -> bool:
    v = (msg.get("Auto-Submitted") or "").strip().lower()
    return bool(v) and v != "no"


def extract_question(full_msg) -> str:
    body = full_msg.get_body(preferencelist=("plain", "html"))
    if body is None:
        return ""
    content = body.get_content()
    if body.get_content_subtype() == "html":
        content = re.sub(r"(?is)<(script|style).*?</\1>", " ", content)
        content = re.sub(r"<[^>]+>", " ", content)
    out = []
    for ln in content.splitlines():
        s = ln.strip()
        if re.match(r"^On .*wrote:$", s) or s.startswith("-----Original"):
            break
        if s.startswith(">"):
            continue
        out.append(ln)
    return "\n".join(out).strip()[:BODY_CAP]


def get_transcript(vid: str) -> str:
    cached = os.path.join(STATE_DIR, f"{vid}.txt")
    if os.path.isfile(cached):
        with open(cached, encoding="utf-8", errors="replace") as f:
            return f.read()[:TRANSCRIPT_CAP]
    try:
        out = subprocess.run(
            ["bash", FETCH_TRANSCRIPT, vid],
            capture_output=True, text=True, timeout=120,
        )
        if out.returncode == 0 and out.stdout.strip():
            return out.stdout[:TRANSCRIPT_CAP]
    except subprocess.TimeoutExpired:
        pass
    return ""


def ask_claude(transcript: str, question: str, vid: str):
    url = f"https://www.youtube.com/watch?v={vid}"
    prompt = (
        "You are answering a question about one episode of The Jack Mallers Show "
        "(Bitcoin, macro, markets). The episode transcript (auto-captions; "
        "punctuation unreliable) is piped on stdin. Answer ONLY from that "
        "transcript plus general context; be concise, direct, plain text.\n\n"
        f"Episode: {url}\n\nThe user's question:\n{question}\n\n"
        "Write a plain-text email reply. Wrap it between a line containing exactly "
        "<<<REPLY>>> and a line containing exactly <<<END>>>. No preamble."
    )
    # tools off: NO --dangerously-skip-permissions (non-interactive claude -p
    # auto-denies any tool call the untrusted input might attempt).
    try:
        proc = subprocess.run(
            ["claude", "-p", "--output-format", "stream-json", "--verbose", prompt],
            input=transcript, capture_output=True, text=True, timeout=CLAUDE_TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        log("claude timed out")
        return None
    chunks = []
    for ln in proc.stdout.splitlines():
        try:
            obj = json.loads(ln)
        except json.JSONDecodeError:
            continue
        if obj.get("type") == "assistant":
            for b in obj.get("message", {}).get("content", []):
                if isinstance(b, dict) and b.get("type") == "text":
                    chunks.append(b["text"])
    raw = "".join(chunks)
    m = re.search(r"<<<REPLY>>>(.*?)<<<END>>>", raw, re.DOTALL)
    ans = (m.group(1).strip() if m else raw.strip())
    return ans or None


def send_reply(to_addr, subject, vid, in_reply_to, references, token, body) -> bool:
    if not subject.lower().startswith("re:"):
        subject = "Re: " + subject
    # Carry the episode id + token in this reply's Message-ID (with a unique
    # suffix) so a reply to THIS answer is still gated to the episode (multi-turn).
    mid = f"<jms.{vid}.{token}.{uuid.uuid4().hex}@lorey.co>"
    args = ["python3", SEND_EMAIL, "--from", SENDER, "--to", to_addr,
            "--subject", subject, "--message-id", mid]
    if in_reply_to:
        args += ["--in-reply-to", in_reply_to]
    if references:
        args += ["--references", references]
    try:
        proc = subprocess.run(args, input=body, capture_output=True, text=True,
                              timeout=SEND_TIMEOUT)
    except subprocess.TimeoutExpired:
        log("send-email timed out")
        return False
    if proc.returncode != 0:
        log(f"send-email failed rc={proc.returncode}: {proc.stderr.strip()[:200]}")
    return proc.returncode == 0


def main() -> None:
    os.makedirs(STATE_DIR, exist_ok=True)
    if os.path.exists(DISABLED):
        return
    try:
        with open(TOKEN_FILE) as f:
            token = f.read().strip()
    except FileNotFoundError:
        log("no reply-token; run jms-chat-setup")
        return
    if not token:
        return

    lockf = open(LOCK_FILE, "w")
    try:
        fcntl.flock(lockf, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        return  # another tick is running

    state = load_state()
    if state["count"] >= DAILY_CAP:
        log(f"daily cap reached ({state['count']}/{DAILY_CAP})")
        return

    creds = load_creds()
    user, pw = creds["MAIL_SMTP_USER"], creds["MAIL_SMTP_PASS"]
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    M = IMAP4(IMAP_HOST, IMAP_PORT)
    try:
        M.starttls(ssl_context=ctx)  # aborts if STARTTLS unavailable
        M.login(user, pw)
        M.select(FOLDER, readonly=True)
        since = (date.today() - timedelta(days=SINCE_DAYS)).strftime("%d-%b-%Y")
        # Replies to a digest carry the digest's Message-ID in In-Reply-To and/or
        # References; search both, server-side, and union.
        found = set()
        for h in ("In-Reply-To", "References"):
            typ, data = M.search(None, f'(SINCE {since} HEADER {h} "jms.")')
            if typ == "OK" and data and data[0]:
                found.update(data[0].split())
        uids = sorted(found, key=lambda b: int(b))
        for uid in uids:
            if state["count"] >= DAILY_CAP:
                log("daily cap reached mid-run")
                break
            try:
                typ, d = M.fetch(uid, "(BODY.PEEK[HEADER])")
                if typ != "OK" or not d or not d[0]:
                    continue
                hdr = email.message_from_bytes(d[0][1], policy=policy.default)
                msgid = hdr.get("Message-ID")
                if not msgid or msgid in state["answered"]:
                    continue
                if is_auto(hdr):
                    continue
                sender = sender_addr(hdr)
                if not sender:
                    continue
                vid = thread_token(hdr, token)
                if not vid:
                    continue

                log(f"answering {sender} re {vid} (uid {uid.decode()})")
                typ, fd = M.fetch(uid, "(BODY.PEEK[])")
                full = email.message_from_bytes(fd[0][1], policy=policy.default)
                question = extract_question(full)
                transcript = get_transcript(vid)
                if not transcript:
                    answer = ("Sorry — I couldn't pull the transcript for that "
                              "episode yet. Try again a bit later.")
                elif not question:
                    answer = ("I didn't find a question in your reply — what would "
                              "you like to know?")
                else:
                    answer = ask_claude(transcript, question, vid)
                    if answer is None:
                        log("no answer produced; will retry next tick")
                        continue  # transient: not recorded, retried next tick

                refs = (hdr.get("References", "") + " " + msgid).strip()
                if send_reply(sender, hdr.get("Subject", "JMS"), vid, msgid, refs,
                              token, answer):
                    state["answered"].append(msgid)
                    state["count"] += 1
                    save_state(state)
                else:
                    log("send failed; not recorded, will retry next tick")
            except Exception as e:
                # Poison message must not wedge the tick or block newer mail.
                log(f"skip uid {uid.decode()}: {type(e).__name__}: {e}")
                continue
    finally:
        try:
            M.logout()
        except Exception:
            pass


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # never crash-loop the launchd job on one bad message
        log(f"error: {type(e).__name__}: {e}")
