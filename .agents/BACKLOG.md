# Config backlog

Deferred config/tooling follow-ups. Lightweight — one `##` heading per item,
newest first. Not deployed anywhere; repo documentation only.

## Non-blocking swallowed-text audio advisory (voice)

**Deferred fast-follow from the 2026-07 voice redesign.**

The end-of-turn voice mechanism now speaks the agent-authored `Summary:` line
(`speak-voice-report.py`, Stop hook). It reads only `last_assistant_message`
— the text after the turn's final tool call — so if an agent emits a
substantive answer or command *before* a closing tool call, that content is
swallowed by the terminal AND invisible to the hook: the user hears the thin
final line (or silence) and never learns something was lost. The `Summary:`
convention is agent discipline, not a code guarantee.

A blocking guard (`check-swallowed-text.py`) was designed and rejected — it
collided with the build-loop cadence and stacked badly with the parallel
`check-orphaned-claims.py` Stop hook.

**Proposed instead:** a *non-blocking* advisory. The speak hook (which already
has `transcript_path`) detects substantive mid-turn text not subsumed by
`last_assistant_message` and, instead of blocking, speaks a short distinct cue
("<Dir>. Heads up — check the terminal, part of the reply may not have
rendered."). Non-blocking → no cadence collision; fail-open → a transcript
parse break just loses the advisory, not the main speech.

**Why deferred:** it reintroduces transcript-parsing (a silent-death surface
the core redesign deliberately removed), and both adversarial reviews rated it
fast-follow, not build-blocking — the terminal (ctrl+o) and git always hold the
real content. Ship the clean core, live with it, add this only if swallowing
recurs in practice.

**Refs:** `.claude/hooks/speak-voice-report.py`,
`.agents/skills/end-of-turn-report/SKILL.md`.
