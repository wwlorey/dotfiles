# Config backlog

Deferred config/tooling follow-ups. Lightweight — one `##` heading per item,
newest first. Not deployed anywhere; repo documentation only.

## Global `asc` skill — App Store Connect via the official REST API

**Design-approved in principle (2026-07), gated by the user on "after the
first app publishes"; also awaits a scope/tier decision.**

Packages "how agents drive App Store Connect" as a reusable global skill —
the knowledge is not project-specific (the `.p8` key + issuer live in
`~/.appstoreconnect/`, not any repo). Split: **capability in the skill,
enforcement in each project.** The skill owns the *how* (ES256 JWT from the
`.p8`; thin subcommands for provisioning profiles, TestFlight groups/testers/
builds, IAP, export-compliance declaration, build-processing polling; the
"app-record creation is UI-only" boundary; secret-handling + confirm-before-
destructive rules). Each project's justfile/specs own the *when* (e.g.
sanctora's `mas-postupload` / `mas-release` targets — tracked project-side by
`issues/asc-api-release-tooling-202607.md`).

**Decisions pending from the user before building:**
1. Publish gate — user said hold until the first app is live (0.1.4 not yet up).
2. Automation tier: (1) post-upload only (compliance + TestFlight assign),
   (2) + yearly profile renewal, (3) full one-command `mas-release`.
3. Client language: pure bash+openssl (zero deps) vs small Python + `pyjwt`
   (cleaner; hooks already assume Python).

**Refs:** `~/.appstoreconnect/`, sanctora `scripts/mas-upload.sh` (existing
credential resolution to reuse), `issues/asc-api-release-tooling-202607.md`.

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
