---
name: orchestrate
description: Decomposing work across multiple subagents — fan-out, parallelization, batched delegation, sweeps over many files or items, and Ralph loops (running a worker repeatedly on the same task until done). Consult whenever the task naturally splits into independent worker units (audit N files, refactor M call sites, research K sources, draft and critique in parallel), whenever the user asks for a Ralph loop, or whenever they say "orchestrate", "delegate", "fan out", "parallelize", "spawn workers", or "batch". Skip for a single one-off delegation — use the Agent tool directly for those.
---

# Orchestrate

You are the orchestrator. Workers do the work in parallel; you brief them, synthesize their returns, and report at end-of-turn. There are exactly two tiers: **orchestrator** (you, this turn) and **workers** (Agent-tool spawns). Workers do NOT spawn further workers.

## When to orchestrate

Orchestrate when the task splits cleanly into 2+ independent units that don't share state during execution:

- Review N files across distinct concerns (one worker per dimension)
- Research M competing approaches and pick (one worker per option)
- Draft and adversarially critique in parallel (writer + critic)
- Sweep K targets for a pattern (one worker per target chunk)
- **Ralph loop** — run a worker repeatedly on the same task until a stop condition is met (build until tests pass, refine a spec until complete, fix until clean). Sequential, not parallel: each iteration's briefing reflects the state the previous worker left behind. Define the stop condition explicitly before the first spawn; cap iterations to avoid runaway loops.

Do NOT orchestrate for:

- A single delegation — call Agent directly
- Work with cross-step state (sequential edits to the same file) — do it yourself
- Trivial tasks where briefing cost ≥ doing it inline

For >5 workers, multi-stage pipelines, or structured-schema returns, stop and use the **Workflow** tool instead. It handles concurrency caps, schemas, journaling, and resumption that this skill leaves to you.

## Briefing a worker

Workers spawned via the Agent tool do NOT inherit the MEMENTO, the skills index, or your conversation context. They only see what you put in the briefing. Every briefing must contain:

1. **Goal** — what the worker is producing, in one sentence.
2. **Scope** — exactly which files / paths / areas they may touch, and what is off-limits.
3. **Return format** — prose, list, diff, structured block. Be explicit.
4. **Inherited rules they'd otherwise miss** — if the worker must follow a project rule (use MCP wrappers over bash, edit dotfiles not deployed copies, use `pn` not `gh`, etc.), state it. They will not know otherwise.
5. **The silence clause, verbatim:**

   > You are a worker, not an orchestrator. Do NOT produce a spoken end-of-turn report. Do NOT call any TTS / voice / `run_dic` tool. Do NOT spawn further workers via the Agent tool — return your result directly. Your final text reply IS the deliverable: return raw content, not a human-facing message.

Keep briefings tight. Too much wastes tokens; too little drifts off-task. The five items above are the minimum bar.

## Spawning

Use the Agent tool. Pick `subagent_type`:

- **`Explore`** — read-only search, locate-this-symbol, where-is-X workers
- **`claude`** — general work (edits, research, mixed)
- **`Plan`** — design / strategy workers
- **`code-reviewer`** or other specialized types when the fit is obvious

Independent workers run in parallel: emit multiple Agent tool calls in a **single message**. They execute concurrently and results come back together.

Dependent workers run sequentially: brief #2 using the output of #1.

By default workers research / draft / report — they do NOT apply code changes. The orchestrator applies them after synthesis. Override only when scopes are genuinely disjoint (one worker per file, no overlap) and you state "apply your changes directly" in the briefing.

## Synthesis and end-of-turn

After workers return:

- Synthesize their outputs into a single coherent answer for the user.
- Apply any changes the workers proposed (per the default above).
- If a worker returned nothing useful, **say so** in the synthesis — silence reads as "covered".
- End the turn with a spoken report per the `end-of-turn-report` skill. **Orchestrators speak; workers do not.**
