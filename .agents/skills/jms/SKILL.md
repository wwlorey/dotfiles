---
name: jms
description: Producing a summary digest of The Jack Mallers Show (Bitcoin / macro / markets podcast on youtube.com/@thejackmallersshow). Consult whenever the user asks to summarize the latest JMS episode, wants the weekly Jack Mallers Show digest, says "what did Jack Mallers cover this week", or any phrasing that means catch me up on the newest episode. Also consult when the weekly launchd cron (co.lorey.jms-weekly) needs to run the digest unattended.
---

# JMS Digest

Fetch the newest full episode of **The Jack Mallers Show**, summarize it, and
email the digest to `jms@lorey.co` via the local ProtonMail Bridge. The whole
pipeline is one deterministic script — run it and relay the result.

## How to run

- **Manual / interactive (`/jms`):** run

  ```bash
  bash ~/.agents/skills/jms/scripts/jms-digest --force
  ```

  `--force` bypasses the idempotency guard so a manual run always produces a
  fresh digest, prints it to stdout, *and* emails it. Add `--dry-run` to print
  the rendered email without sending. Relay the printed digest to the user.

- **Unattended (cron):** the launchd agent `co.lorey.jms-weekly` runs
  `jms-digest` with no flags every Tuesday 9:01am. The idempotency guard
  (`~/.local/state/jms/last-sent`) ensures an episode is emailed at most once.

## What the script does

1. Finds the newest long-form episode via `yt-dlp`. Episodes land in either the
   `/streams` tab (live-streamed shows) or `/videos` (pre-recorded uploads), so
   it scans **both**, keeps uploads over `MIN_DURATION` (20min, excluding
   Shorts/clips), and picks the newest by upload date. On an unattended (cron)
   run that finds no episode — empty fetch or nothing long-form — it emails a
   `JMS digest alert: no episode found` notice to `jms@lorey.co` and exits.
2. Skips if that episode id was already sent (unless `--force`).
3. Pulls the auto-generated English captions with `yt-dlp` and flattens them to
   plain text.
4. Summarizes the transcript into a two-part digest — a brief in-depth "Gist"
   (TL;DR) and a "Breakdown" that follows the episode's own segment order. The
   model must wrap the digest in `<<<DIGEST>>>`/`<<<END>>>` sentinels; if they're
   absent (an auth error like "Not logged in", a refusal, an empty stream), the
   script refuses to send, emails a `JMS digest alert: summarization failed`
   notice on a cron run, and exits — it never ships the raw error as the digest.
5. Hands the digest to the `send-email` skill, which delivers it through the
   local ProtonMail Bridge (`From: noreply@lorey.co`, `To: jms@lorey.co`).

## Vendor primitive

Step 4 calls the agent CLI in print mode (`claude -p`) — the capability is
*LLM summarization of a transcript*. It is the only harness-specific line in
`scripts/jms-digest`; a port to another runtime rewrites that one call and
nothing else.

## One-time setup

Delivery goes through the `send-email` skill, so the only credentials needed are
the shared ProtonMail Bridge ones. If they aren't set up yet, follow the
`send-email` skill's setup (`scripts/setup-bridge-creds`), then `save-config`.

Load the weekly schedule once:

```bash
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/co.lorey.jms-weekly.plist
```

## Files

- `scripts/jms-digest` — orchestrator (discovery → guard → transcript →
  summarize → send → record state). The sender address (`noreply@lorey.co`) and
  recipient (`jms@lorey.co`) are set at the top of the script.
- Delivery: the `send-email` skill
  (`~/.agents/skills/send-email/scripts/send-email.py`) — `jms-digest` pipes the
  rendered digest to it. Bridge credentials are owned there, not here.
- Schedule: `~/Library/LaunchAgents/co.lorey.jms-weekly.plist`.
- `scripts/fetch-transcript` — `fetch-transcript <video-id|url>` prints a video's
  cleaned auto-caption transcript (shared by `jms-digest` and the chat poller).

## Chat by email

Reply to a digest to ask a question about that episode and get an emailed answer.

Each digest's `Message-ID` is `<jms.<VIDEOID>.<TOKEN>@lorey.co>` (Proton
preserves a custom Message-ID, but rewrites Reply-To and won't send a `+tag`
From — so the Message-ID is the carrier). A reply's `In-Reply-To`/`References`
preserves it; a launchd job (`co.lorey.jms-chat`, polls ~60s) finds those
replies, verifies the token, answers from the episode transcript via `claude -p`,
and replies in-thread — its own Message-ID also carries `jms.<VIDEOID>.<TOKEN>` so
a reply to the answer keeps working (multi-turn). Because the bot
(`noreply@lorey.co`) and you share one Proton account, mail lands in **All Mail**
(not INBOX) and each message also leaves a Sent copy — the poller searches All
Mail and dedupes by Message-ID.

**Security:** the token is the only real gate (an outsider who emails the address
without it is ignored); the `@lorey.co` sender check is unauthenticated
defense-in-depth; a hard daily cap bounds spend; `claude -p` runs with no tool
access (untrusted input can't make it act).

**Setup / control:**
- One-time: `bash ~/.agents/skills/jms/scripts/jms-chat-setup` (generates the
  reply token), `save-config`, then load the poll:
  `launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/co.lorey.jms-chat.plist`.
- Rotate token (replies to already-sent digests stop being answered):
  `bash ~/.agents/skills/jms/scripts/jms-chat-setup --rotate`.
- Pause: `touch ~/.local/state/jms-chat/disabled`; resume:
  `trash ~/.local/state/jms-chat/disabled`.
- State + log: `~/.local/state/jms-chat/` (`state.json`, `jms-chat.log`).

## Notes

- Auto-captions can lag a freshly-published episode by an hour or two; if the
  transcript is missing the script exits without sending and the next run
  retries.
