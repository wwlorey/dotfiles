---
name: orchestrate
description: Spawning a subagent via the Agent tool, including a single one-off delegation. Consult before every Agent call — no bottom limit, no exceptions; don't talk yourself out of consulting because the spawn feels small or fast. Also consult whenever the user says "orchestrate", "delegate", "fan out", "parallelize", "spawn workers", "batch", or asks for a Ralph loop.
---

# Orchestrate

You are the orchestrator. Workers do the work; you brief them, synthesize their returns, and report at end-of-turn. There are exactly two tiers: **orchestrator** (you, this turn) and **workers** (Agent-tool spawns). Workers do NOT spawn further workers.

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

For >5 workers, multi-stage pipelines, or structured-schema returns, stop and use the **Workflow** tool instead. It handles concurrency caps, schemas, journaling, and resumption that this skill leaves to you.

## Briefing a worker

Workers spawned via the Agent tool do NOT inherit the MEMENTO, the skills index, or your conversation context. They only see what you put in the briefing. Every briefing must contain:

1. **Goal** — what the worker is producing, in one sentence.
2. **Scope** — exactly which files / paths / areas they may touch, and what is off-limits. By default workers research, draft, and report — they do NOT apply code changes; the orchestrator applies them after synthesis. Override only when scopes are genuinely disjoint (one worker per file, no overlap) and you state "apply your changes directly" in the briefing.
3. **Return format** — prose, list, diff, structured block. Be explicit.
4. **Skills, scripts, and MCP tools they should reach for** — before spawning, inventory what's available that fits the task and name it explicitly. Examples: `youtube-transcript` for any YouTube source, `deep-research` for fan-out web research, `generate-image` for visual output, `voice` for TTS, `unsandboxed-runner` MCP wrappers for shell commands that need network or non-sandbox paths, any project script the worker would otherwise have to re-derive. Workers do not see the skill index, so unmentioned skills are invisible to them. Skipping this step is the most common briefing failure.
5. **Inherited project rules they'd otherwise miss** — if the worker must follow a project rule (edit dotfiles not deployed copies, use `pn` not `gh`, use a specific commit-message format, etc.), state it. They will not know otherwise.
6. **The silence clause, verbatim:**

   > You are a worker, not an orchestrator. Do NOT produce a spoken end-of-turn report. Do NOT call any TTS / voice / `run_dic` tool. Do NOT spawn further workers via the Agent tool — return your result directly. Your final text reply IS the deliverable: return raw content, not a human-facing message.

Keep briefings tight. Too much wastes tokens; too little drifts off-task. The six items above are the minimum bar.

## Synthesis and end-of-turn

After workers return:

- Synthesize their outputs into a single coherent answer for the user.
- Apply any changes the workers proposed.
- If a worker returned nothing useful, **say so** in the synthesis — silence reads as "covered".
- End the turn with a spoken report per the `end-of-turn-report` skill. **Orchestrators speak; workers do not.**
