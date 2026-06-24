---
name: build
description: Claiming the next-ready issue from the project backlog and implementing it end-to-end, one issue at a time, until none remain or a sane cap is reached. Consult whenever the user says "build the next thing", "claim the next issue", "implement from the backlog", "work through ready issues", or asks the agent to run autonomously against the issue tracker. Also consult when an orchestrator pipeline (changes) needs the implementation step for a known-claimed issue.
---

# Build

You are about to claim and implement issues from `<repo>/issues/` one at a time. Each iteration is its own focused worker that picks the top-ready issue, implements it, runs full backpressure, and closes the issue. The loop continues until the backlog is empty or the iteration cap is reached.

This is a pipeline. The conventions below are inlined here, not pulled in by reference.

## Ralph loop

Stop condition: `issues/ready` returns no slugs **OR** you have completed 30 iterations. If `ready` returns no slugs but `grep -l '^status: open$' issues/*.md` finds open issues, report "backlog blocked by unresolved deps" rather than "backlog drained" in the on-completion summary.

Each iteration is one **sequentially** spawned worker via the `orchestrate` skill (Agent-tool spawn). The loop never runs two iterations in parallel. Fresh context per iteration. The worker's briefing covers exactly one issue.

Before constructing the worker briefing, check your invocation context for caller-supplied policy (typically supplied by `dev`):

- A `## Per-item gate policy (from dev)` section — its bullets become the contents of the briefing's "Required verification gates" section (per the `orchestrate` skill's 7th briefing-checklist item). If absent, omit "Required verification gates" from the briefing and the worker will skip step 9 of the procedure.

Worker briefing template:

> **Goal.** Implement one issue from the project backlog end-to-end.
>
> **Scope.** You may touch any file in the repo required to implement the one issue you claim, including its referenced specs. You may NOT work more than one issue per spawn, absorb unrelated pre-existing failures into your claim (log new issues instead), or push commits if backpressure is failing on your own changes. The issues directory is the project's `<repo>/issues/` backlog — not GitHub Issues.
>
> **Procedure.**
> 1. Run `issues/ready` to list ready slugs. Take the top one. If the list is empty, stop and report "backlog empty." After taking the top slug, re-read `issues/<slug>.md` and confirm its `status:` is still `open`. If the slug's status is already `in_progress`, do not work it — even if the prior claim was you. Report the stale claim and stop.
> 2. Read the issue at `issues/<slug>.md` to understand scope, source refs, doc refs, and prior comments.
> 3. Claim the issue by editing frontmatter `status: open` → `status: in_progress`. Commit with message `claim <slug>`.
> 4. If the issue's `type` is `bug`, follow the bug-fix flow: reproduce, write a failing test that captures the bug, fix, re-run the test. Otherwise implement per the issue body and any referenced specs.
>    - **Tracer bullet first.** Build a tiny end-to-end slice, validate it, then expand. Avoid implementing the whole feature wide before any part of it works narrow.
>    - **No placeholder code.** Real implementations only — no stubs, no `TODO: implement`, no `expect(true).toBe(true)`.
> 5. Read every spec named in `## Doc refs` via `cat specs/<stem>.md`. Implement against those specs. **Specs describe planned design as readily as existing code** — a spec referencing a type, function, or module is not evidence that it exists. Before calling anything the spec names, verify it's already implemented (grep the codebase); otherwise plan to build it as part of this claim.
> 6. **Update specs alongside code.** If your implementation changes the design described in any spec, update the spec in the same commit as the code. Do not defer with "will update later." See the `specs` skill for the schema; transitions like `approved` → `implemented` happen here when applicable. If you discover the existing code already drifts from a spec while implementing your issue, log a separate issue for the drift rather than absorbing it into the current claim — keep the change focused.
> 7. Write tests (unit, property, or integration — pick what fits). No placeholder tests.
> 8. Consult the `backpressure` skill and run full backpressure for the project's stack. When a gate fails, triage:
>    - **You caused it** → fix it. Part of this claim.
>    - **Pre-existing but trivial** (lint warnings, formatter drift, a one-line type-fix) → fix it. Part of this claim.
>    - **Pre-existing and non-trivial** (a real failing test that's not yours, a broken module on a path you didn't touch) → log a new issue under `issues/` capturing what's broken and where, and leave it alone. Do not absorb unrelated work into this claim.
>
>    When in doubt between trivial and non-trivial, classify as non-trivial and log the issue. Trivial means a clear one-line mechanical fix; anything that requires understanding the failing module is non-trivial.
>
>    If the project has build flags that differ by OS (e.g. Metal feature on macOS, CUDA on Linux), ensure the default build still works on the user's OS.
>
>    Re-run backpressure until it passes clean. Don't ship with unaddressed failures from your own changes.
> 9. Run any **caller-required verification gates**. The orchestrator may have included a "Required verification gates" section in this briefing (per the `orchestrate` skill's briefing checklist) — for example, `dev` injects `verify` for issues that touched user-visible UI / IPC, and `code-review` for non-trivial diffs. Run each gate per its trigger condition. Treat a failing gate the same as a failing backpressure check — fix the underlying issue or revert; do not commit with a gate failure unaddressed. **If the fix touches code, re-run full backpressure (step 8) to confirm nothing else broke before proceeding to step 10.** If no "Required verification gates" section is present, skip this step.
> 10. Close the issue: edit frontmatter `status: in_progress` → `status: closed`. Add a `## Comments` entry summarizing what was done.
> 11. Commit the implementation + spec updates + closure as one logical change (formatter residue may be a separate commit). Then `git push` so the iteration's work reaches the remote before the next iteration starts. If push fails (no upstream, network, conflict), report the failure and continue — the commit is safe locally and a later iteration or human can push it.
>
> **Skills to consult.** `issues` (schema and operations), `specs` (schema and updates), `backpressure` (full backpressure), `orchestrate` (you are spawned via it).
>
> **Skills, scripts, and MCP tools to reach for.** `issues/ready` (the doctor + ready-slug script in the project's `issues/` directory), the `mcp__unsandboxed-runner__*` wrappers (`run_pnpm`, `run_playwright`, `run_tauri_build`, `smoke_test_tauri`, etc.) for any shell command the sandbox blocks (network access, non-sandbox paths, long-running builds), and the project's own scripts named in spec or issue refs.
>
> **Return format.** A one-paragraph summary: which slug was implemented, what changed, what the backpressure outcome was. If the backlog was empty or you hit a blocker, say so explicitly. End with a `## New work surfaced` section listing any new issues you logged during the iteration (slug + one-line description per item — pre-existing drift you filed instead of absorbing, sub-tasks you discovered, spec changes that imply downstream work). Write the literal text `none` under the heading if nothing surfaced.
>
> **Inherited rules.**
> - Never reuse a slug.
> - Never claim an issue that's already `in_progress`.
> - Never commit with backpressure failures unaddressed.
> - If `issues/ready` exits non-zero, report the doctor error verbatim and stop — do not proceed with a corrupted backlog.
> - If a failing test for a `bug`-type issue is impossible in isolation (requires live network, real credentials, hardware), document the manual reproduction in `## Comments` and proceed; do not fake a passing test.
> - If your own change creates a backpressure failure you cannot fix this iteration, revert the change, unclaim the issue (`in_progress` → `open`) with a `## Comments` entry explaining the blocker, and report the blocker to the orchestrator. Do not commit the broken state.
> - **Gate output is not your terminal return.** When a verification gate (`code-review`, `audit-specs`, `verify`, etc.) emits findings, that text is the GATE's output — NOT yours. Your iteration is not done. Continue: address any findings, finish the per-iteration lifecycle (implement → backpressure → commit → push → close issue), and only emit the one-paragraph summary + `## New work surfaced` return AFTER the iteration is committed AND pushed. If your last emitted text is a gate's findings (or any non-structured prose) and the artifact is incomplete, you are NOT done — your next action MUST be a tool call, not more prose.
>
> **Long-running commands use MCP wrappers, not raw Bash.** For any cargo command, use `mcp__unsandboxed-runner__run_cargo` — pass argv as a string array (e.g. `args: ["test", "--workspace"]`, `args: ["clippy", "--workspace", "--all-targets", "--", "-D", "warnings"]`). For tauri build, use `mcp__unsandboxed-runner__run_tauri_build`. For pnpm, use `mcp__unsandboxed-runner__run_pnpm`. The wrappers run outside the sandbox and bypass Bash's timeout cap. Raw `cargo` via Bash is blocked by a PreToolUse hook (`redirect-bash-to-mcp.py`). NEVER end your turn while waiting on a backgrounded task — the harness treats final text without a pending tool call as turn-end, the worker goes dormant, and completion notifications don't wake it.
>
> You are a worker, not an orchestrator. Return text only. Do NOT produce spoken or audio output of any kind (the orchestrator handles voice). Do NOT spawn further workers via the Agent tool. Your final text reply IS the deliverable: return raw content, not a human-facing message.

After the worker returns, check the stop condition:
- If the worker reported "backlog empty" → stop.
- If you've spawned 30 workers → stop and report the cap was hit.
- Otherwise, evaluate the **mid-iteration checkpoint** before spawning the next iteration. Look in your invocation context for a `## Per-batch gate policy (from dev)` section — its bullets are the gates and the `Mid-batch checkpoint:` sub-section names the trigger conditions (typically "every 5 iterations since the last per-batch run" and "immediately after any iteration that touched a high-risk surface"). If the conditions are met, fire the gates before spawning the next iteration.

When firing per-batch gates, pass the slate's commit range (SHAs covering iterations closed since the build run started) in each gate-worker briefing AND require the worker to tag every finding INTRODUCED-BY-SLATE or PRE-EXISTING with a one-line git-log/git-blame justification.

**Per-finding routing (per `dev`'s gate-failure recovery + no-loose-ends rule):**
- HIGH severity → auto-spawn a remediation worker (scoped strictly to the failure; do not absorb unrelated work) and continue — surface the failure + fix in the on-completion report.
- MED severity tagged INTRODUCED-BY-SLATE → auto-spawn a remediation worker (slate-introduced regression; same treatment as HIGH).
- MED severity tagged PRE-EXISTING → file as a tracker issue at `<repo>/issues/<slug>.md` (status: open, mirror the project's existing issue format) before spawning the next iteration — do NOT remediate.
- LOW severity (any tag) → file as a tracker issue. Do NOT remediate.

Tracker filings can land in a single batched commit per mid-iteration round (e.g. `chore(issues): file N mid-iteration <round> gate findings`). If no policy section is present, skip the checkpoint and spawn the next iteration as today.

## On completion

When the loop exits (either condition), report to the user:
- How many issues were implemented this run (slugs + one-line summary each)
- Whether the cap was hit, the backlog truly drained, or the backlog is blocked by unresolved deps (open issues exist but none are ready because their deps aren't closed)
- Any failures left unaddressed (e.g. a backpressure failure on the last iteration that the worker couldn't fix)
- **Aggregated new work surfaced.** Collect the `## New work surfaced` block from every iteration's worker return AND every remediation worker's return (remediation workers spawned at mid-iteration / session-close checkpoints are scoped iteration workers and contribute too). Surface the union under a top-level `## New work surfaced` section in your own report — slug + one-line description per item, grouped by which worker surfaced it. This is the hook a caller like `dev` uses to detect whether the build session genuinely drained the queue or merely re-filled it with follow-ups.
- **Session-close gates.** Look in your invocation context for a `## Session-close gate policy (from dev)` section. If present, AND the aggregated `## New work surfaced` section contains nothing that would queue more iterations into the current session, fire those session-close gates now. Surface findings in the report.
  - Pass the slate's full commit range in each gate-worker briefing and require INTRODUCED-BY-SLATE / PRE-EXISTING tagging per the mid-iteration routing rule above.
  - Apply the same routing: HIGH → remediation; MED + INTRODUCED → remediation; MED + PRE-EXISTING → file as tracker; LOW → file as tracker.
  - **No loose ends.** Before declaring the build session complete, every surfaced finding from every gate run this session (per-iteration + mid-iteration + session-close) MUST be in a terminal state: fixed (commit landed), filed as `<repo>/issues/<slug>.md`, or explicitly deferred by the user. "Surfaced in the report as prose only" is NOT a terminal state — findings in chat alone are re-discovered every future gate run. The orchestrator (this skill) files the trackers itself; a single `chore(issues): file N session-close gate followups` commit covers them.

Do not silently move on if any iteration left the tree in a bad state.
