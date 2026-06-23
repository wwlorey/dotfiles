---
name: dev
description: Single entry point for any code, spec, issue, or verification work in this project. Consult whenever the user asks for development work of any shape — describing a change conversationally, asking to build from the backlog, wanting to spec something out, asking for an audit, or any focused work that needs routing to the right underlying lifecycle (changes / build / spec / spec-to-issues / audit-specs). Owns the verification cadence policy: gates fire at item-close, at mid-batch checkpoints, and at session-close, never per-commit. Also consult whenever the user is AFK and wants the agent to make autonomous decisions through to session-close. Do NOT consult for non-development work (face reading, image generation, news, voice) — those have their own dedicated skills.
---

# Dev

You are about to handle a user request for development work of any kind. Your job: route to the right underlying lifecycle, inject the verification cadence policy into the worker briefings, own AFK decisions through to session-close, and report.

This is a thin orchestrator. The underlying lifecycle skills (`changes`, `build`, `spec`, `spec-to-issues`, `audit-specs`) do the actual work; `dev` decides *which* lifecycle and *which* gates. Stay above the work — do not pre-investigate, do not implement, do not pre-grep the codebase. Delegate.

## Routing

Pick exactly one underlying lifecycle for each user request. When the user describes multiple kinds of work in one message, route the dominant intent and surface the others as follow-up questions.

| User intent | Route to |
|---|---|
| "I want to add / change / fix / refactor X" (conversational change request) | `changes` |
| "Build the next thing" / "claim the next issue" / "work the backlog" | `build` |
| "Let's spec out X" / "harden the spec for Y" / design discussion that should produce a spec | `spec` |
| "Materialize the backlog from spec X" / "spec-to-issues for Y" | `spec-to-issues` |
| "Audit all specs" / "verify specs against code" / pre-release library audit | `audit-specs` (library-wide, standalone) |
| Ambiguous (could be `changes` or `build`) | When AFK, default to `changes`; otherwise ask. |

When the user explicitly invokes an underlying skill by name (e.g. `/changes ...`), they have bypassed `dev`. Respect the bypass — do not wrap it. `dev` is the default surface, not the only surface.

The verification cadence policy below applies ONLY to code-touching lifecycles (`changes`, `build`). Routes to `spec` / `spec-to-issues` / standalone `audit-specs` produce no code commits, so no per-item / per-batch / session-close gates apply — those lifecycles run as-is.

## Verification cadence policy

Three cadences. Gates are conditional on what the work touched.

### Per-item gates (fire when one item closes, before dequeuing the next)

| Condition | Gate |
|---|---|
| Item touched user-visible UI or the IPC / RPC surface | `verify` (launch the real stack and exercise the changed user flow) |
| Item's cumulative diff is non-trivial (rough threshold: > ~200 lines or touches > 5 files) | `code-review` |

Inject these into the impl-worker briefing as a "Required verification gates" section per the `orchestrate` skill's briefing checklist. The worker runs them after `backpressure` passes, before commit.

### Per-batch gates (always run; no skip option)

Fire at the natural batch boundary: end of the `changes` slate, exit of the `build` loop, OR at a mid-batch checkpoint (see below).

| Condition | Gate |
|---|---|
| Any item in the batch touched a high-risk surface | `security-review` (branch-level) |
| Any item in the batch touched code a spec claims behavior about | `audit-specs` in scoped mode (union of touched-neighbor stems across the batch) |
| Any item produced a non-trivial diff (and `code-review` did NOT already fire per-item) | `code-review` |

Per-batch gates run autonomously even when the user is at the keyboard. Do not pause to ask permission. Surface "running per-batch gates now" as a status update.

### Mid-batch forced checkpoint

Fire per-batch gates immediately — without waiting for the slate / loop to finish — when **any of**:

- 5 items have closed since the last per-batch gate run, OR
- The most recent item touched a high-risk surface

After the gates run (and any remediation worker completes), resume the slate / loop with a clean per-batch counter.

### Session-close gates (when the queue is empty AND no new work surfaced)

Inject the session-close policy into the underlying lifecycle's invocation context. The pipeline (`changes` or `build`) fires the gates at its own on-completion per the policy you supplied — `dev` does NOT fire them directly. The policy:

- `audit-specs` (library-wide)
- `security-review` (branch-level, full)

These replace what would otherwise be scheduled / cron gates. Session-close is the natural moment to run them because you know the working tree has stabilized. `dev`'s job at this layer is: (a) inject the policy on lifecycle invocation, (b) read the on-completion return to confirm the gates ran, (c) handle any drift findings per the gate-failure recovery shape below.

### Policy injection wire format

The three cadence policies above reach the underlying lifecycle via your invocation prompt — literal markdown text the lifecycle's body reads from its own invocation context. When invoking `changes` or `build`, include a block with these section headings (omit a heading if its policy is empty; omit the whole block if `dev` was bypassed):

```
## Per-item gate policy (from dev)
- <gate> if <condition>

## Per-batch gate policy (from dev)
- <gate> if <condition>
Mid-batch checkpoint:
- <trigger condition>

## Session-close gate policy (from dev)
- <gate>
```

Populate the bullets from the per-item / per-batch / session-close gate tables above. The `Mid-batch checkpoint:` sub-section's triggers come from the "Mid-batch forced checkpoint" section, not from the per-batch table. `changes` / `build` know to look for these three section headings in their invocation context (see their bodies). When the user invokes `/changes` or `/build` directly, no policy block appears — the lifecycle runs without injected gates, exactly as it does pre-`dev`.

## High-risk surfaces

Plain-English concepts. Map to actual paths in the project at hand (a Rust+Tauri app's `src-tauri/src/commands/`; a Python service's `views/` or `api/`; a Node service's `routes/` or middleware — whatever the project's equivalent surface is).

- Authentication, identity, session management
- Cryptography, key derivation, encryption-at-rest
- The IPC / RPC surface between frontend and backend (Tauri commands, HTTP routes, RPC handlers)
- Application startup, initialization, dependency injection
- Process spawning, child management, signal handling
- Anything the project's security spec claims behavior about

When in doubt, classify as high-risk. The cost of an extra security-review is one round-trip; the cost of missing one is a real bug.

## Gate-failure recovery

The shape `dev` defines; the orchestrating pipeline (`changes` or `build`) does the actual spawning. Every gate failure follows the same recovery shape regardless of cadence:

1. **Auto-spawn a remediation worker** scoped strictly to the failure. Do NOT absorb unrelated work into the fix. The briefing names exactly what the gate flagged, the file(s) involved, and the success criterion (the gate passes when re-run). The spawning actor is the active orchestrator (the pipeline that fired the gate — `changes` mid-batch or on-completion, `build` mid-iteration or on-completion). `dev` does not spawn remediation workers directly; it inherits visibility of them via the lifecycle's return.
2. **Continue the lifecycle.** Do not pause for user input. The fix is part of the work.
3. **Record the failure + fix.** In the end-of-turn report (which `dev` owns) and in the close-comment of whatever issue the fix landed against. Explicit audit trail.

Special case for `audit-specs`: HIGH-severity drift findings get remediation workers (auto-routed into `changes`). MED/LOW drift goes into the on-completion report only — surface, don't block.

## AFK / autonomy rules

The user signals AFK with words like "AFK," "standing orders," "make the calls," "I'm going AFK." When AFK:

- Answer every clarifying question yourself using the documented heuristics in this skill or the relevant underlying skill. Don't pause for user input.
- Apply the verification cadence policy at full strength. Per-batch gates still run. Mid-batch checkpoints still fire.
- Surface every autonomous decision in the end-of-turn report (one bullet per non-trivial choice).
- Gate-failure recovery runs auto-spawn-and-continue. Surface the failure + fix in the report.

When NOT AFK:

- Clarifying questions get asked once per item before planning workers fan out.
- Per-batch gates still run autonomously — these are not optional and not blocked on user input.
- Surface routing decisions ("routing this to `changes`") and mid-batch checkpoint firings as status updates so the user can interrupt if needed.

The AFK / non-AFK distinction is small. Only clarifying questions about design choices differ. Gates fire identically.

## Session-close detection

A session is "closed" when ALL of:

1. The most recent underlying-lifecycle invocation has returned (changes slate done, build loop exited, spec hardened, etc.).
2. The aggregated `## New work surfaced` section from that return is empty (or contains only items the user has explicitly deferred). This section is produced by the underlying lifecycle per its on-completion return format — every impl worker contributes one and the lifecycle's orchestrator aggregates upward.
3. No new user message has queued work.
4. Session-close gates (if any) have run AND any remediation workers they spawned have themselves returned with empty `## New work surfaced`.

The fourth condition can loop: a remediation worker's findings may queue more work, which may surface more findings. Continue until the loop stabilizes (no new surfaced work for one full iteration). Cap at 5 loop iterations to prevent runaway; report `session-close did not stabilize` if hit.

Once stabilized, emit the end-of-turn report (per the `end-of-turn-report` skill — orchestrators speak; workers do not).

## Communicating with the user

Throughout a session, surface state at every meaningful event. Most events happen inside the lifecycle (`changes` / `build`); `dev`'s job is to relay them from the lifecycle's progress updates / on-completion return.

- Routing decision (which lifecycle was chosen and why) — surfaced by `dev` directly, at routing time.
- Each item moving through the lifecycle (planning → approved → implementing → committed) — relayed from the lifecycle's per-item status snapshots.
- Per-batch gates starting / passing / firing remediation workers — relayed from the lifecycle's mid-batch checkpoint or on-completion output.
- Mid-batch checkpoint firing — relayed from the lifecycle.
- Session-close gates starting — relayed from the lifecycle's on-completion path.

Keep status updates brief — one or two sentences, factual. The end-of-turn report is the comprehensive summary; mid-session updates exist to let the user interrupt cheaply.

## Hard rules

- **Route deterministically.** One user request → one lifecycle. Do not split a single request across `changes` and `build` simultaneously.
- **Inject gate policy into worker briefings — don't try to wedge it in after the worker returns.** The `orchestrate` skill's briefing checklist includes "Required verification gates" exactly for this. Populate that section per the policy above when spawning the impl worker.
- **Per-batch and session-close gates run autonomously.** Never pause for permission. They are part of the work, not a checkpoint.
- **Gate failures auto-spawn remediation workers at the lifecycle layer.** The actor is the active orchestrator (`changes` or `build`), not `dev`. Never silently swallow a gate failure. Never block the lifecycle on one.
- **Do not pre-investigate.** Routing decisions come from the user's words, not from grep sweeps. If the user is ambiguous, ask once — do not investigate to disambiguate.
- **Do not implement.** Implementation happens inside the underlying lifecycle's impl worker (and its sub-workers). `dev` is the orchestrator of orchestrators.

## Skills, scripts, and MCP tools to reach for

- `orchestrate` — every spawn into an underlying lifecycle goes through orchestrate's briefing checklist. The 7th item ("Required verification gates") is the policy-injection hook.
- `changes`, `build`, `spec`, `spec-to-issues`, `audit-specs` — the underlying lifecycles. Each consumes the gate policy via the orchestrate hook.
- `backpressure` — runs inside the impl-worker lifecycle as the mechanical pre-commit gate; not directly invoked by `dev`.
- `end-of-turn-report` — produces the spoken end-of-session summary.
- For any project-specific scripts and `mcp__unsandboxed-runner__*` MCP wrappers — these belong to the project, not to `dev`; the underlying lifecycle skills name them as needed.
