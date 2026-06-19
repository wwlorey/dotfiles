---
name: orchestrate
description: Spawning a subagent via the Agent tool, AND reading task-notifications / worker returns. Consult before every Agent call — no bottom limit, no exceptions; don't talk yourself out of consulting because the spawn feels small or fast. ALSO consult before acting on any task-notification or worker return — `status: completed` events have a failure mode (interim snapshots that look terminal) that mistakes mid-execution for finished work. Also consult whenever the user says "orchestrate", "delegate", "fan out", "parallelize", "spawn workers", "batch", or asks for a Ralph loop.
---

# Orchestrate

You are the orchestrator. Workers do the work; you brief them, synthesize their returns, and report at end-of-turn.

**Tier limit: up to three tiers.** The default call graph is two tiers: **orchestrator** (you, this turn) → **workers** (Agent-tool spawns). A third tier — **sub-workers** spawned BY workers — is permitted ONLY when the caller is a `changes`-skill implementation worker, and only one level deep. Sub-workers MAY NOT spawn further. This keeps depth predictable and prevents recursive runaway. Outside the `changes` impl path, the two-tier rule holds: workers do not spawn workers.

This skill governs **every Agent spawn**, single or multiple. Briefing is the load-bearing step — workers inherit no skills, no MEMENTO, no conversation context, so anything they need has to be named in the prompt.

## Shape of the spawn

Decide how many workers fit the task — the count doesn't change whether you consult this skill, only how you spawn:

- **Single worker** — one **focused** delegation. Brief per the checklist below and call Agent.
- **Parallel fan-out (2+ workers)** — task splits into independent units that don't share state. Emit multiple Agent calls in one message; they run concurrently. Examples: review N files across distinct concerns, research M competing approaches, draft + adversarial critique pair, sweep K targets.
- **Sequential dependency** — worker #2's briefing needs worker #1's output. Brief them one at a time.
- **Ralph loop** — run a worker repeatedly on the same task until a stop condition is met (build until tests pass, refine a spec until complete, fix until clean). Sequential, not parallel: each iteration's briefing reflects the state the previous worker left behind. Define the stop condition explicitly before the first spawn; cap iterations to avoid runaway loops.

Do the work yourself (no spawn) when:

- Cross-step state (sequential edits to the same file) makes splitting harmful.
- Briefing cost ≥ doing it inline (a one-line read, a single grep).

For multi-step procedures that are worth re-running by name, the work belongs in a **pipeline skill**, not in ad-hoc spawns from this skill. Pipeline skills define the procedure as prompt and delegate the iterative or parallel parts back to this skill. This skill governs the spawn; a pipeline governs the procedure. If you find yourself sequencing several spawns to drive a known kind of work, consider authoring a pipeline skill (see `create-skill`).

## Briefing a worker

Workers spawned via the Agent tool do NOT inherit the MEMENTO, the skills index, or your conversation context. They only see what you put in the briefing. Every briefing must contain:

1. **Goal** — what the worker is producing, in one sentence.
2. **Scope** — exactly which files / paths / areas they may touch, and what is off-limits. By default workers research, draft, and report — they do NOT apply code changes; the orchestrator applies them after synthesis. Override only when scopes are genuinely disjoint (one worker per file, no overlap) and you state "apply your changes directly" in the briefing.
3. **Return format** — prose, list, diff, structured block. Be explicit.
4. **Skills, scripts, and MCP tools they should reach for** — before spawning, inventory what's available that fits the task and name it explicitly. Examples: `youtube-transcript` for any YouTube source, `deep-research` for fan-out web research, `generate-image` for visual output, `voice` for TTS, `unsandboxed-runner` MCP wrappers for shell commands that need network or non-sandbox paths, any project script the worker would otherwise have to re-derive. Workers do not see the skill index, so unmentioned skills are invisible to them. Skipping this step is the most common briefing failure.
5. **Inherited project rules they'd otherwise miss** — if the worker must follow a project rule (edit dotfiles not deployed copies, use the project's `issues/` backlog not GitHub issues, use a specific commit-message format, etc.), state it. They will not know otherwise.
6. **The silence clause.** Pick the variant that fits the worker's role:

   - **Default (workers in any context):**
     > You are a worker, not an orchestrator. Return text only. Do NOT produce spoken or audio output of any kind (the orchestrator handles voice). Do NOT spawn further workers via the Agent tool. Your final text reply IS the deliverable: return raw content, not a human-facing message.

   - **`changes`-skill impl worker (mini-orchestrator):**
     > You are a worker (mini-orchestrator). Return text only. Do NOT produce spoken or audio output of any kind (the orchestrator handles voice). You MAY spawn sub-workers (one level only) per the `orchestrate` skill. Sub-workers MAY NOT spawn further. Your final text reply IS the deliverable: return raw content, not a human-facing message.

   - **Sub-worker (spawned by a `changes` impl worker):**
     > You are a sub-worker. Return text only. Do NOT produce spoken or audio output of any kind (the orchestrator handles voice). Do NOT spawn further workers via the Agent tool. Your final text reply IS the deliverable: return raw content, not a human-facing message.

Keep briefings tight. Too much wastes tokens; too little drifts off-task. The six items above are the minimum bar.

## Reading worker responses & notifications

A `task-notification` with `status: completed` is **not** necessarily terminal. The harness fires these events whenever a background worker emits new output; the `status: completed` field reads like a terminal event but actually means "the worker has emitted output, here's the latest snapshot." The same worker can fire multiple notifications over its lifetime, and only the last one carries the worker's structured return.

Distinguish:

- **Interim snapshot.** `result` is a sentence-fragment thought ("Let me wait for…", "Good. Let me…", "File hasn't been written in 12 min…"). The worker is mid-execution. Do nothing; wait for the next notification or verify the artifact before acting.
- **Terminal return.** `result` matches the structured format your briefing asked for (`## Summary`, `## Files changed`, etc.). The worker has finished its iteration.

When uncertain between the two, **verify the artifact** — git log, tree state, file written, whatever output the briefing promised — not the notification text. Treating an interim snapshot as terminal is the most common mistake: it triggers premature escalation (spawning a finish-the-job worker, prescribing a skill fix, debugging a non-failure) while the original worker quietly succeeds in the background.

## Synthesis and end-of-turn

After workers return:

- Synthesize their outputs into a single coherent answer for the user.
- Apply any changes the workers proposed.
- If a worker returned nothing useful, **say so** in the synthesis — silence reads as "covered".
- End the turn with a spoken report per the `end-of-turn-report` skill. **Orchestrators speak; workers do not.**
