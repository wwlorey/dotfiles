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
- **Ralph loop** — run a worker repeatedly on the same task until a stop condition is met (build until tests pass, refine a spec until complete, fix until clean). Sequential, not parallel: each iteration's briefing reflects the state the previous worker left behind. Define the stop condition explicitly before the first spawn; cap iterations to avoid runaway loops. Spawn each iteration **synchronously** — never `run_in_background`. An async ralph iteration whose terminal notification never arrives leaves the orchestrator silent while the worker is stranded, and the next iteration spawns on top of an unresolved one.

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
6. **Required verification gates** — the caller (e.g. the `dev` skill, or any pipeline that injects post-implementation policy) may require the worker to run specific gates after backpressure passes, before committing. Name each required gate explicitly, with the trigger condition if conditional ("if diff touches the IPC surface, run `verify` before commit"). Workers do not infer gates from context; if a gate isn't in the briefing, it doesn't fire. Omit the section if no gates are required.
7. **The silence clause.** Pick the variant that fits the worker's role:

   - **Default (workers in any context):**
     > You are a worker, not an orchestrator. Return text only. Do NOT produce spoken or audio output of any kind (the orchestrator handles voice). Do NOT spawn further workers via the Agent tool. Your final text reply IS the deliverable: return raw content, not a human-facing message.

   - **`changes`-skill impl worker (mini-orchestrator):**
     > You are a worker (mini-orchestrator). Return text only. Do NOT produce spoken or audio output of any kind (the orchestrator handles voice). You MAY spawn sub-workers (one level only) per the `orchestrate` skill. Sub-workers MAY NOT spawn further. Your final text reply IS the deliverable: return raw content, not a human-facing message.

   - **Sub-worker (spawned by a `changes` impl worker):**
     > You are a sub-worker. Return text only. Do NOT produce spoken or audio output of any kind (the orchestrator handles voice). Do NOT spawn further workers via the Agent tool. Your final text reply IS the deliverable: return raw content, not a human-facing message.

Keep briefings tight. Too much wastes tokens; too little drifts off-task. The seven items above are the minimum bar.

## Worker turn lifecycle

A worker's turn ends when it emits text without a pending tool call. The harness has no "wait for event" state outside of tool calls — if a worker emits `"I'll wait for the test to finish via notification"` and then makes no further tool call, the turn ends and the worker goes dormant. A backgrounded task's completion notification may never wake a dormant worker, stranding the work and the tree mid-state.

In every worker briefing, include this rule:

> **Long-running commands use MCP wrappers, not raw Bash.** For any cargo command, use `mcp__unsandboxed-runner__run_cargo` — pass argv as a string array (e.g. `args: ["test", "--workspace"]`, `args: ["clippy", "--workspace", "--all-targets", "--", "-D", "warnings"]`). For tauri build, use `mcp__unsandboxed-runner__run_tauri_build`. For pnpm, use `mcp__unsandboxed-runner__run_pnpm`. The wrappers run outside the sandbox and bypass the in-sandbox Bash timeout entirely. Raw `cargo` via Bash is blocked by a PreToolUse hook (`redirect-bash-to-mcp.py`). NEVER end your turn while waiting on a backgrounded task — the harness treats final text without a pending tool call as turn-end, the worker goes dormant, and completion notifications don't wake it.

## Reading worker responses & notifications

A `task-notification` with `status: completed` is **not** necessarily terminal. The harness fires these events whenever a background worker emits new output; the `status: completed` field reads like a terminal event but actually means "the worker has emitted output, here's the latest snapshot." The same worker can fire multiple notifications over its lifetime, and only the last one carries the worker's structured return.

Distinguish:

- **Interim snapshot.** `result` is a sentence-fragment thought ("Let me wait for…", "Good. Let me…", "File hasn't been written in 12 min…"). The worker is mid-execution. Do nothing; wait for the next notification or verify the artifact before acting.
- **Terminal return.** `result` matches the structured format your briefing asked for (`## Summary`, `## Files changed`, etc.). The worker has finished its iteration.

When uncertain between the two, **verify the artifact** — git log, tree state, file written, whatever output the briefing promised — not the notification text. Treating an interim snapshot as terminal is the most common mistake: it triggers premature escalation (spawning a finish-the-job worker, prescribing a skill fix, debugging a non-failure) while the original worker quietly succeeds in the background.

## Detecting and recovering from dormant workers

A separate failure mode from interim-snapshot confusion: the worker emits text without a pending tool call (often gate output like `/code-review` findings, or a deliberation snippet that *looks* like a conclusion), the harness ends its turn, and the worker goes dormant. Completion notifications don't wake a dormant worker.

Two variants surface this:

- **Bad-format notification.** A `status: completed` notification arrives whose `result` text doesn't match the structured return format you briefed for.
- **Missing notification.** The Agent spawn returned `Async agent launched successfully` (instead of a synchronous structured result) AND no follow-up `task-notification` has arrived within ~5–10 minutes. The orchestrator is now on the hook to receive a terminal notification carrying the worker's structured return — if it never arrives, the worker is a candidate dormancy regardless of how active the artifact looks. Do NOT rationalize a stream of bookkeeping commits (gate-finding backfills, multi-iteration claim chains) as proof of progress — those can keep landing while the worker is stranded mid-iteration without having returned its terminal block. "I haven't heard back from the worker" is itself the trigger, equivalent to a bad-format notification arriving.

**Detection** (either variant):

1. Verify the artifact (git log, tree state, files written) against the plan.
2. If the artifact is complete → the worker actually finished but emitted bad-format text (or the notification got lost in transit). Extract what you need from the artifact and move on.
3. If the artifact is incomplete → stat the worker's JSONL output file. If the mtime is older than ~5 minutes, the worker is dormant. If still growing, it's mid-execution; wait for the next notification, or `SendMessage` to ask for a status update.

**Recovery decision tree (cheapest option first — do not default to the fresh spawn):**

- **Trivial mechanical remainder** (commit a staged file, push, update tracker, format): orchestrator inlines it. Briefing cost exceeds work cost. Surface what was inlined in the end-of-turn report so the audit trail is explicit. Mark the item closed.
- **Non-trivial remainder needing the worker's earned context** (multiple sub-pieces unfinished, design decisions in flight, mid-refactor state): use `SendMessage` with the worker's agentId to resume — the worker continues in its existing context, much cheaper than starting fresh. Brief the continuation prompt with (a) what specifically is left per the plan, (b) the verbatim reminder that gate output is not the terminal return, (c) the structured return format you still expect.
- **Worker's context is poisoned** (wrong direction taken, scope creep, design mismatch, OR repeated dormancy after `SendMessage` resume): only then spawn a fresh `changes`-style finish-the-job worker, scoped strictly to recovery from the current tree state.

The fresh-spawn option is a LAST resort. It discards the worker's hard-won context and costs the most. Try inline and `SendMessage` first.

## Synthesis and end-of-turn

After workers return:

- Synthesize their outputs into a single coherent answer for the user.
- Apply any changes the workers proposed.
- If a worker returned nothing useful, **say so** in the synthesis — silence reads as "covered".
- End the turn with a spoken report per the `end-of-turn-report` skill. **Orchestrators speak; workers do not.**
