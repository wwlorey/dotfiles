---
name: voice
description: Producing spoken audio — speaking text aloud in real time (realtime voice responses, ad-hoc utterances, the playback half of an end-of-turn report) or rendering text to a WAV/MP3 file for another skill (e.g. news). Consult whenever you need to produce spoken output, save synthesized speech to disk, or another skill (such as `end-of-turn-report` or `news`) needs the synthesis primitive.
---

# Voice

Synthesize speech via the `run_dic` MCP tool (from `unsandboxed-runner`). Two modes, distinguished by whether the caller passes `output`:

- **Speak now** — plays immediately through the speakers. Used for realtime voice responses, ad-hoc spoken output, and the playback half of an end-of-turn report.
- **Render to file** — saves audio to disk, no playback. Used by skills that need to assemble audio (e.g. `news` chunking themes into a daily WAV).

This skill is the synthesis primitive only — format, length, and trigger rules belong to the caller (see the `end-of-turn-report` skill for end-of-turn specifics).

## Speak now

- **Omit `output`.** That tells `run_dic` to play immediately rather than save.
- **Run in background** (`run_in_background: true`) unless the caller specifically needs to wait. The audio is the user-facing artifact; blocking on it stalls the response text.
- **Voice:** `bf_isabella` is the default. Only override if a downstream prompt asks for a different voice.
- **Speed:** the `speed` param is optional; default playback rate is fine for most uses.

## Render to file

- Pass `output: "<absolute path>"` to save instead of play.
- Optional `format`: `wav` or `mp3` (default `wav`).
- Optional `speed` and `voice` overrides.
- Chunking, concatenation, file naming, and playback decisions belong to the caller — this skill only handles the synthesis call.
