---
name: end-of-turn-report
description: Producing a brief spoken update whenever the agent is handing control back to the user — either ending a turn or pausing mid-turn to ask for input. Consult before ending any turn (even short, blocked, or abandoned ones) and before any call that requests user input mid-turn (AskUserQuestion, plan approval, or any other pause that waits on the user). Mid-turn alerts delegate synthesis to the `voice` skill.
---

# End-of-Turn Report

Speak a brief update whenever control returns to the user — either the turn
ending or the agent pausing mid-turn to wait on input. Delivery is split:

- **End of turn** — a Stop hook speaks after the final text renders. Your job
  is to author one self-contained final message whose LAST line carries the
  spoken summary. You make no voice call.
- **Mid-turn pause** — manual. Speak the alert directly, in the same response
  that issues the pausing call.

## When to trigger

- **End of every turn** — completion, blocker, abandonment. Not only successes.
- **Before requesting user input mid-turn** — AskUserQuestion, ExitPlanMode for
  approval, or any other pause that hands control back to the user. Speak the
  alert in the same response that issues the request, so the user knows to come
  look.

## End of turn: author the `Summary:` last line; the hook speaks it

End every text-terminated final message with a literal last line of the form:

```
Summary: <Dirname>. <phrase>.
```

- `<Dirname>` is the working directory's basename, spoken-friendly and
  capitalized (e.g. `Sanctora`, `Lsr App`, `Dotfiles`).
- `<phrase>` reports the outcome or request — completion, status, blocker,
  abandonment — as a phrase, not a sentence.

Examples of the last line:

- `Summary: Dotfiles. Voice skill added.`
- `Summary: Sanctora. Build green, ready to ship.`
- `Sanctora. Stalled, stopping.` also works — the label is optional (see below).

The Stop hook (`~/.claude/hooks/speak-voice-report.py`) fires after the turn's
final text has rendered, takes the final message's last non-empty line, strips
the `Summary:` label, and speaks the remainder. **This ordering is the point:**
the speech follows the rendered text, and the spoken line is exactly the last
text the user sees. The hook guarantees the spoken line leads with the
directory basename and never contains the word "summary" — but author the line
in the canonical form anyway so the visible last line reads cleanly.

- The `Summary:` label is the END-OF-TURN form only, and it is a main-agent
  convention — workers do not emit it.
- The hook prepends the basename if your phrase omits it, so a bare
  `Summary: Build green.` still speaks `Sanctora. Build green.` — but leading
  with `<Dirname>.` yourself keeps the visible line self-describing.
- Emit the user-facing text — the answer, report, or synthesis — as the turn's
  LAST output, with no tool calls after it. The terminal renders only the text
  after the turn's last tool call.
- A turn that ends on a tool call has no final text; the hook speaks nothing,
  which is correct. Headless (`AGENT_HEADLESS=1`) and teammate/worker sessions
  are exempt: only the main agent's turns speak.
- Do NOTHING voice-related at turn end — no TTS call, no trailing tool call.
  Compose one final message ending in the `Summary:` line and stop.

## Mid-turn pause: speak directly

Hooks fire only on Stop, not on mid-turn input requests, so for AskUserQuestion,
plan approval, or any other pause that waits on the user, speak the alert
directly using the `voice` skill's **speak now** mode: call the
`mcp__unsandboxed-runner__run_dic` MCP tool (an MCP tool, not a Bash command —
pass `text` as a parameter) in the same response that issues the pausing call.

The mid-turn alert has NO `Summary:` label — speak the direct form:

`<WorkingDirName>. <short phrase>.`

- **Start with the working directory's basename** so the user knows which
  project is talking (e.g. `Dotfiles.`, `Hooked.`, `Springfield.`).
- **Then a short phrase** naming the request — the question being asked, the
  approval being awaited. Keep it to a phrase, not a sentence.
- Backgrounded call, no `output` param (so it plays immediately).
- Default voice (`bf_isabella`).
- The pause UI renders through the pausing tool itself, so a preceding tool
  call displaces nothing.

Examples:

- "Dotfiles. Need input on env var name."
- "Dotfiles. Picking between two icon styles."
- "Dotfiles. Plan ready for approval."

Do not block on the audio; the input request is the primary artifact.
