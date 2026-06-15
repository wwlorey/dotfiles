---
name: end-of-turn-report
description: Closing every turn with a brief spoken report of what the agent did — the system expects every turn to end this way. Consult before ending any turn, even short ones, and even when the work was abandoned or blocked rather than completed. Delegates synthesis to the `voice` skill.
---

# End-of-Turn Report

End every turn with a short spoken report of what happened. The format is fixed; the synthesis call is handed off to the `voice` skill.

## Format

`<WorkingDirName>. <short phrase>.`

- **Start with the working directory's basename** so the user knows which project is talking (e.g. `Dotfiles.`, `Hooked.`, `Springfield.`).
- **Then a short phrase** reporting the outcome — completion, status, blocker, or abandonment. Keep it to a phrase, not a sentence.

Examples:

- "Dotfiles. Voice skill added."
- "Hooked. Build green."
- "Dotfiles. Need input on env var name."
- "Dotfiles. Stalled, stopping."

The report covers every outcome — done, blocked, abandoned. Not only successes.

## How to deliver it

Use the `voice` skill's **speak now** mode:

- Backgrounded `run_dic` call, no `output` param (so it plays immediately).
- Default voice (`bf_isabella`).
- The spoken text is the format above — nothing more.

Do not block the turn on the audio; the text reply is the primary artifact.
