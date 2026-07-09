---
name: handoff
description: Producing a self-contained continuation prompt that hands in-flight work to a fresh agent or a new session. Consult whenever the user asks to "hand this off", "write/produce a prompt for the next agent/worker/session", "pick up where I left off", "continue this later", "prep a handoff/continuation prompt", or "brief the next session" — and whenever a session must wrap with work still up in the air (context running low, or a natural stop with pending tasks). This is the WRITTEN next-agent briefing, distinct from end-of-turn-report's spoken user update; reach for it even after a short session, because the in-conversation decisions it captures are lost on compaction otherwise.
---

# Handoff

You are producing a **continuation prompt** for the next agent — a fresh session
that inherits NOTHING: no chat history, no memory of this one. Everything the
next agent needs must be either IN the prompt you produce or in durable state
you point it at precisely.

## The one principle

Two kinds of state exist, and they get opposite treatment:

- **Durable** — git history, the issue backlog, specs, code on disk, open PRs.
  The next agent reads these itself. You **MAP** them (point and orient it to
  what's relevant); you do NOT copy or re-summarize them.
- **Ephemeral** — the decisions, agreements, constraints, and pending tasks that
  live only in this conversation. These EVAPORATE the moment the session
  compacts. Nothing else holds them.

Your PRIMARY job is the ephemeral: capture it, and flush what belongs into
durable form. A handoff that laboriously re-narrates the backlog while dropping
the three verbal decisions the session actually turned on is a failed handoff.

Ground everything in the probe and the durable anchors — NOT in your fading
recollection of the session. Memory drifts; git and the backlog do not.

## Procedure

### 1. Probe the durable-state surface

Run the probe (works from any working directory):

    bash ~/.agents/skills/handoff/scripts/gather-state.sh

It prints a factual digest of what exists here — git HEAD / branch / push-state,
uncommitted or in-flight work, recent commits, and which state anchors are
present (`issues/`, `specs/`, `plans/`, `TODO.md`, GitHub PRs). It adapts: a
rich repo yields issues + specs + git, a plain repo yields git, a bare directory
yields the files on disk. Use whatever it finds; assume no particular anchor
exists. Pass a path argument to probe a directory other than the current one.

Also account for any **in-flight work you spawned this session** that is not yet
reflected on disk — background workers / async jobs still running, or a worker
that died mid-task leaving an uncommitted tree. The probe surfaces an unclean
tree; only you know about still-running spawns. [Harness note: "background
workers I spawned" is a runtime-specific concept; the underlying capability is
"in-flight work not yet on disk." Name it however the current runtime exposes
it, or drop the line on a runtime without async spawns.]

### 2. Inventory the ephemeral

Scan THIS session for everything that lives only in the conversation and is not
yet in durable state:

- **Decisions & agreements** — "we'll do X", "use approach A not B", a chosen
  design the code doesn't yet reflect.
- **Constraints / do-NOT** agreed verbally — the highest-value category:
  irreversible-action guardrails, sign-off gates ("don't ship / don't bump the
  version without my OK"), "don't do X autonomously." These are what stop the
  next agent doing damage.
- **Collaborative protocol** — what the user does vs. what the agent does, when
  the work needs both (the user runs a device step; the agent writes the code).
- **Offers pending the user's word**, stated preferences, and any task discussed
  but not written down anywhere.

### 3. Flush ephemeral → durable

For each ephemeral item that is a real task or decision meant to outlive this
prompt, **make it durable**: file it into the project's tracker (an issue via
the `issues` skill, a `TODO.md` entry — whatever the project uses), so it
survives independently of the prompt. Then the prompt merely points at it. A
genuine pending task must not live ONLY in prose that itself compacts away.
Items that are truly prompt-only (a stated style preference, a who-does-what
note) stay in the prompt. If the project has no tracker at all, say so and keep
those items in the prompt's Next-actions section.

### 4. Write the handoff prompt

Fill this skeleton. Keep the durable sections as pointers; spend your words on
the ephemeral.

- **Mission** — the current objective, 1–2 lines.
- **State snapshot** — HEAD (pushed?), branch, uncommitted / in-flight work,
  running background workers. From the probe.
- **What's done** — brief, with commit SHAs / closed issue slugs, so the next
  agent doesn't redo it. Point, don't narrate.
- **Next actions (ordered)** — the loose ends, ordered, each with the exact
  file / issue-slug / command and its dependency (what unblocks what). The
  ephemeral pending tasks plus the live durable items.
- **Constraints / do-NOT** — the guardrails from step 2. The section everyone
  forgets and the one that prevents the irreversible mistake. Never omit it.
- **Key decisions + rationale** — settled calls, so they are not relitigated.
- **Where to look** — the map: "backlog at `issues/` (live items: …); git from
  `<sha>` is <what>; specs at `specs/`." Pointers, not copies.
- **How to proceed** — which skills to route the work through, and the
  collaborative protocol if the user is a participant.

### 5. Output and self-containedness check

Write the prompt to `HANDOFF.md` in the working directory AND print it in your
reply. If the working directory is a git repo, add `HANDOFF.md` to
`.git/info/exclude` (or `.gitignore`) so session state is never committed.
Surface the file on its own line as `handoff: file://<absolute-path>` per the
file-surfacing rule.

Then re-read the prompt as if you have zero context. Does every SHA, slug, path,
and decision resolve? Would a fresh agent know exactly what to do next AND what
not to do? If not, fix it before returning.

## What this is not

- Not `end-of-turn-report`: that is a SPOKEN update for the USER at every
  turn-end. This is a WRITTEN briefing for the NEXT AGENT, on request.
- Not a status summary: re-summarizing self-serve durable state is wasted words.
  The value is the ephemeral capture plus the flush to durable.

The self-contained-briefing DNA is shared with the `orchestrate` skill (workers
inherit nothing) — this is that principle scaled from a scoped worker up to a
whole next session.
