---
name: send-email
description: Sending an email through the local ProtonMail Bridge — a shared primitive consumed by any skill or task that needs to deliver mail (digests, reports, alerts, notifications). Consult whenever you need to send an email from this machine, when another skill (e.g. jms) needs to hand off a rendered message for delivery, or when setting up / rotating the Bridge SMTP credentials.
---

# send-email

Send a message through the local ProtonMail Bridge. This is a reusable
primitive: callers supply the recipient, subject, and body; the script handles
the SMTP connection and credentials.

## How to send

```bash
python3 ~/.agents/skills/send-email/scripts/send-email.py \
  --to someone@example.com --subject "Subject line" --from noreply@lorey.co <<'BODY'
Message body goes here.
BODY
```

- `--to` (required) — recipient; comma-separate for several.
- `--subject` (required).
- `--from` (optional) — defaults to `MAIL_FROM` in the credentials, else the
  SMTP login address. Must be an address your Proton account owns (or a
  catch-all alias), or Proton rejects the send.
- `--reply-to`, `--in-reply-to`, `--references` (optional) — reply-routing and
  threading headers; each is CR/LF-sanitized. `--references` is a space-separated
  list of Message-IDs.
- Body is read from **stdin** (or pass `--body "..."`).

The script connects over implicit TLS (SMTPS) to `127.0.0.1:1025` and decrypts
the connection credentials on demand with `sops`.

## Credentials

Connection credentials are account-level and shared across all senders. They
live sops-encrypted at `~/.config/mail/bridge.env` (override the path with
`$MAIL_BRIDGE_ENV`):

```
MAIL_SMTP_HOST=127.0.0.1
MAIL_SMTP_PORT=1025
MAIL_SMTP_USER=<Bridge login address>
MAIL_SMTP_PASS=<Bridge password>
MAIL_FROM=<optional default From>
```

Create or rotate them by running, in a real terminal:

```bash
bash ~/.agents/skills/send-email/scripts/setup-bridge-creds
```

It prompts (password without echo), encrypts to your age recipient
(`~/.config/sops/age/keys.txt`), and writes the file into the dotfiles repo.
Then `save-config` to deploy. Never commit a decrypted `bridge.env`.

## Files

- `scripts/send-email.py` — the sender (`smtplib` over SMTPS).
- `scripts/setup-bridge-creds` — interactive credential setup/rotation.
