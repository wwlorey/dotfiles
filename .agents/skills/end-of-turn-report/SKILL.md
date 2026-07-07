---
name: end-of-turn-report
description: Producing a brief spoken update whenever the agent is handing control back to the user — either ending a turn or pausing mid-turn to ask for input. Consult before ending any turn (even short, blocked, or abandoned ones) and before any call that requests user input mid-turn (AskUserQuestion, plan approval, or any other pause that waits on the user). Mid-turn alerts delegate synthesis to the `voice` skill.
---

# End-of-Turn Report

Speak a brief update whenever control returns to the user — either the turn ending or the agent pausing mid-turn to wait on input. The format is fixed; delivery is split — end-of-turn lines are staged to a marker file that a Stop hook plays after the final text renders, mid-turn alerts go through the `voice` skill directly.

## When to trigger

- **End of every turn** — completion, blocker, abandonment. Not only successes.
- **Before requesting user input mid-turn** — AskUserQuestion, ExitPlanMode for approval, or any other pause that hands control back to the user. Speak the alert in the same response that issues the request, so the user knows to come look.

## Format

`<WorkingDirName>. <short phrase>.`

- **Start with the working directory's basename** so the user knows which project is talking (e.g. `Dotfiles.`, `Hooked.`, `Springfield.`).
- **Then a short phrase** reporting the outcome or the request — completion, status, blocker, abandonment, or the question being asked. Keep it to a phrase, not a sentence.

Examples:

- "Dotfiles. Voice skill added."
- "Hooked. Build green."
- "Dotfiles. Need input on env var name."
- "Dotfiles. Picking between two icon styles."
- "Dotfiles. Plan ready for approval."
- "Dotfiles. Stalled, stopping."

## How to deliver it

Two delivery paths, chosen by what kind of hand-back this is.

### End of turn: stage the line; the Stop hook speaks it

The Stop hook (`~/.claude/hooks/speak-voice-report.py`) fires after the
turn's final text has rendered in the terminal and plays the report then.
**This ordering is the point:** the speech follows the rendered text, and
the final text is never displaced by a trailing tool call — terminal UIs
render only the text after the turn's last tool call as the turn's message.

**Stage the crafted line (recommended).** Write it to the per-project marker
file via Bash, any time during the turn before the final text (temp-file +
`mv` so the hook never reads a half-written line):

```bash
f="/tmp/claude/voice-report-$(pwd | tr '/' '-').txt" && mkdir -p /tmp/claude && printf '%s' "<WorkingDirName>. <short phrase>." > "$f.tmp" && mv "$f.tmp" "$f"
```

- The marker is keyed by working directory — the cwd with `/` replaced by
  `-`, the same encoding the harness uses for its per-project tmp dirs. The
  hook derives the identical key from the `cwd` in its stdin and speaks +
  deletes the marker (detached, via the same TTS the `voice` skill uses,
  default voice `bf_isabella`).
- Stage within the turn you are ending: the hook discards markers older
  than 30 minutes as orphans of a killed session.
- Accepted edge: two concurrent sessions in the *same* project directory
  share a marker key, so one can consume the other's line; the session
  whose marker was eaten degrades gracefully to the hook's auto-summary.
- The staged text is the format above — nothing more.
- Emit the user-facing text — the answer, report, or synthesis — as the
  turn's LAST output, with no tool calls after it.
- A direct speak-now call at turn end would either play before the text
  renders or displace the text entirely — the end-of-turn line goes through
  the marker.

**Safety net — nothing blocks.** When no marker is staged, the hook derives
a line itself: `<cwd basename, capitalized>.` plus a machine summary of the
turn's final message. The staged line is always better — it names the
outcome the way the format above intends — so stage whenever you can.

### Mid-turn pause: speak directly

Hooks fire only on Stop, not on mid-turn input requests, so for
AskUserQuestion, plan approval, or any other pause that waits on the user,
speak the alert directly using the `voice` skill's **speak now** mode: call
the `mcp__unsandboxed-runner__run_dic` MCP tool (an MCP tool, not a Bash
command — pass `text` as a parameter) in the same response that issues the
pausing call.

- Backgrounded call, no `output` param (so it plays immediately).
- Default voice (`bf_isabella`).
- The pause UI renders through the pausing tool itself, so a preceding tool
  call displaces nothing.

Do not block on the audio; the text reply or input request is the primary artifact.
