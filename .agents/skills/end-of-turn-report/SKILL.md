---
name: end-of-turn-report
description: Producing a brief spoken update whenever the agent is handing control back to the user — either ending a turn or pausing mid-turn to ask for input. Consult before ending any turn (even short, blocked, or abandoned ones) and before any call that requests user input mid-turn (AskUserQuestion, plan approval, or any other pause that waits on the user). Delegates synthesis to the `voice` skill.
---

# End-of-Turn Report

Speak a brief update whenever control returns to the user — either the turn ending or the agent pausing mid-turn to wait on input. The format is fixed; the synthesis call is handed off to the `voice` skill.

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

Use the `voice` skill's **speak now** mode by calling the `mcp__unsandboxed-runner__run_dic` MCP tool directly. This is an MCP tool, not a Bash command — do not pipe via `echo` or run via Bash; pass `text` as a parameter.

- Backgrounded call, no `output` param (so it plays immediately).
- Default voice (`bf_isabella`).
- The spoken text is the format above — nothing more.

Do not block on the audio; the text reply or input request is the primary artifact.
