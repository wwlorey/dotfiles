#!/usr/bin/env python3
"""send-email — send a message through the local ProtonMail Bridge (SMTPS).

A reusable sender: callers supply --to / --subject (and optionally --from); the
body is read from stdin (or --body). Connection credentials are decrypted on
demand from a sops dotenv — default ~/.config/mail/bridge.env, override with
$MAIL_BRIDGE_ENV:

    MAIL_SMTP_HOST  (default 127.0.0.1)
    MAIL_SMTP_PORT  (default 1025)
    MAIL_SMTP_USER  Bridge login address (required)
    MAIL_SMTP_PASS  Bridge password (required)
    MAIL_FROM       default From when --from is omitted (optional)

ProtonMail Bridge serves implicit TLS on localhost with its own (non-public) CA,
so certificate verification is disabled — the connection is to 127.0.0.1 only.

Usage:
    send-email.py --to a@b.com --subject "Hi" [--from x@y.com] < body.txt
"""
from __future__ import annotations

import argparse
import os
import smtplib
import ssl
import subprocess
import sys
from email.message import EmailMessage


def load_creds(path: str) -> dict[str, str]:
    if not os.path.isfile(path):
        sys.exit(
            f"send-email: bridge credentials not found at {path} — run the "
            f"send-email skill's setup-bridge-creds (or set $MAIL_BRIDGE_ENV)"
        )
    # Under launchd's minimal env XDG_CONFIG_HOME is unset, so sops can't find the
    # age key by default — point it explicitly.
    env = dict(os.environ)
    env.setdefault("SOPS_AGE_KEY_FILE", os.path.expanduser("~/.config/sops/age/keys.txt"))
    try:
        out = subprocess.run(
            ["sops", "-d", "--output-type", "dotenv", path],
            capture_output=True,
            text=True,
            check=True,
            env=env,
        ).stdout
    except FileNotFoundError:
        sys.exit("send-email: sops not found on PATH")
    except subprocess.CalledProcessError as exc:
        sys.exit(f"send-email: sops decrypt failed: {exc.stderr.strip()}")

    creds: dict[str, str] = {}
    for line in out.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, val = line.split("=", 1)
        creds[key.strip()] = val.strip()
    return creds


def require(creds: dict[str, str], key: str) -> str:
    val = creds.get(key)
    if not val:
        sys.exit(f"send-email: {key} missing from bridge credentials")
    return val


def header(value: str) -> str:
    """Strip CR/LF so an attacker-influenced value (e.g. a video title flowing
    into Subject) cannot inject extra SMTP headers."""
    return value.replace("\r", " ").replace("\n", " ").strip()


LOOPBACK_HOSTS = {"127.0.0.1", "::1", "localhost"}


def main() -> None:
    ap = argparse.ArgumentParser(prog="send-email")
    ap.add_argument("--to", required=True, help="recipient (comma-separated for several)")
    ap.add_argument("--subject", required=True)
    ap.add_argument("--from", dest="sender", default=None)
    ap.add_argument("--message-id", dest="message_id", default=None)
    ap.add_argument("--reply-to", dest="reply_to", default=None)
    ap.add_argument("--in-reply-to", dest="in_reply_to", default=None)
    ap.add_argument("--references", default=None, help="space-separated Message-IDs")
    ap.add_argument("--body", default=None, help="body text; if omitted, read from stdin")
    args = ap.parse_args()

    cred_path = os.environ.get(
        "MAIL_BRIDGE_ENV", os.path.expanduser("~/.config/mail/bridge.env")
    )
    creds = load_creds(cred_path)

    host = creds.get("MAIL_SMTP_HOST", "127.0.0.1")
    port = int(creds.get("MAIL_SMTP_PORT", "1025"))
    user = require(creds, "MAIL_SMTP_USER")
    password = require(creds, "MAIL_SMTP_PASS")
    sender = args.sender or creds.get("MAIL_FROM") or user
    body = args.body if args.body is not None else sys.stdin.read()

    msg = EmailMessage()
    msg["From"] = header(sender)
    msg["To"] = header(args.to)
    msg["Subject"] = header(args.subject)
    # Optional threading / reply-routing headers (each assigned exactly once;
    # EmailMessage raises on a duplicate header). Values are CR/LF-sanitized so an
    # attacker-controlled inbound In-Reply-To/References can't inject headers.
    if args.message_id:
        msg["Message-ID"] = header(args.message_id)
    if args.reply_to:
        msg["Reply-To"] = header(args.reply_to)
    if args.in_reply_to:
        msg["In-Reply-To"] = header(args.in_reply_to)
    if args.references:
        msg["References"] = header(args.references)
    msg.set_content(body)

    ctx = ssl.create_default_context()
    # The ProtonMail Bridge presents a self-signed cert on loopback, so cert
    # verification is disabled there only. Any non-loopback host keeps full
    # verification — never silently send cleartext-equivalent to a remote MTA.
    if host in LOOPBACK_HOSTS:
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

    with smtplib.SMTP_SSL(host, port, timeout=30, context=ctx) as smtp:
        smtp.login(user, password)
        smtp.send_message(msg)

    print(f"send-email: sent '{args.subject}' to {args.to}", file=sys.stderr)


if __name__ == "__main__":
    main()
