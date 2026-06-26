---
name: build
description: Claiming the next-ready issue from the project backlog and implementing it end-to-end, one issue at a time, until none remain or a sane cap is reached. Consult whenever the user says "build the next thing", "claim the next issue", "implement from the backlog", "work through ready issues", or asks the agent to run autonomously against the issue tracker. Also consult when an orchestrator pipeline (changes) needs the implementation step for a known-claimed issue.
---

# Build

You are the orchestrator of a ralph loop that cranks through the backlog at `<repo>/issues/`. On each iteration you claim one ready issue, spawn one focused worker to implement it end-to-end, audit the worker's return, then continue or stop per the conditions below. The loop is sequential — never two iterations in parallel — and runs until the backlog is empty or the iteration cap is reached.

This is a pipeline. The conventions below are inlined here, not pulled in by reference.

## Orchestrator loop

You (the agent running in the main loop, this turn) own the loop. The worker (spawned via the Agent tool) handles exactly one iteration per spawn and returns. Each iteration:

1. Run `./issues/ready` and take the top slug. If empty, stop and emit the on-completion report ("backlog drained" — or "backlog blocked by unresolved deps" if `grep -l '^status: open$' issues/*.md` shows open issues whose deps aren't closed). If `./issues/ready` exits non-zero, report the doctor error verbatim and stop — do not proceed with a corrupted backlog.
2. Re-read `issues/<slug>.md` and confirm `status: open`. If already `in_progress`, do not work it; report the stale claim and stop.
3. Record `HEAD-before-this-iteration` for the post-iteration audit in step 7.
4. Check your invocation context for a caller-supplied `## Per-item gate policy (from dev)` section — its bullets populate the worker briefing's "Required verification gates" section (per the `orchestrate` skill's 7th briefing-checklist item). If absent, omit that section from the briefing.
5. Spawn the iteration worker via a **synchronous** Agent call. Never `run_in_background` — the loop is sequential by definition, and an async spawn whose terminal notification never arrives leaves you silent while the worker is dead. Briefing template below under "## Iteration worker". Substitute the pre-iteration HEAD recorded in step 3 into the briefing's `Pre-iteration HEAD:` field so the worker can scope backpressure per `backpressure`'s "Per-iteration scoping" section.
6. Wait for the worker's structured return.
7. Run the **post-iteration audit** (below). If it fails, PAUSE the loop, recover, resume.
8. Apply **per-finding routing** for any gate output surfaced this iteration (below).
9. Evaluate the **mid-iteration checkpoint** for per-batch gates from `dev`'s policy (below).
10. Check the stop condition: backlog empty OR 100 iterations completed → stop and emit the on-completion report. Otherwise loop back to step 1.

Stop condition (canonical): `./issues/ready` returns no slugs, OR 100 iterations completed.

### Post-iteration audit

After every worker return, before any other check:

- `git log <HEAD-before-this-iteration>..HEAD` must show exactly one `claim <slug>` commit and at least one matching commit that closes the same slug (frontmatter `status: closed`).
- `grep -l '^status: in_progress$' issues/*.md` must return empty — no orphaned claims.
- The worker's return must include `## Exit condition state: met`.

If any check fails, the worker either went dormant mid-implementation OR violated the one-issue-per-spawn scope by trying to run multiple iterations inside one context (claim commits stacking up with no matching closes is the diagnostic signature of both). PAUSE the loop and apply `orchestrate`'s dormant-worker recovery decision tree — inline trivial mechanical remainders, `SendMessage` to resume non-trivial ones, fresh recovery-scoped spawn only as a last resort. Resume the loop only after every orphaned `in_progress` is in a terminal state. Do NOT spawn iteration N+1 on top of an unresolved iteration N.

### Per-finding routing

When firing per-batch or session-close gates, pass the slate's commit range (SHAs covering iterations closed since the build run started) in each gate-worker briefing AND require the worker to tag every finding INTRODUCED-BY-SLATE or PRE-EXISTING with a one-line git-log/git-blame justification.

Routing (per `dev`'s gate-failure recovery + no-loose-ends rule):

- HIGH severity → auto-spawn a remediation worker (scoped strictly to the failure; do not absorb unrelated work) and continue — surface the failure + fix in the on-completion report.
- MED severity tagged INTRODUCED-BY-SLATE → auto-spawn a remediation worker (slate-introduced regression; same treatment as HIGH).
- MED severity tagged PRE-EXISTING → file as a tracker issue at `<repo>/issues/<slug>.md` (status: open) before spawning the next iteration — do NOT remediate.
- LOW severity (any tag) → file as a tracker issue. Do NOT remediate.

**Orchestrator-inline shortcut for trivial pure-doc drift.** When a MED/LOW finding is a trivial pure-doc / spec-text correction — a one-line drift, no recompile, no investigation (e.g. a stale signature in a spec API list, a wrong byte count, a dangling section reference) — the orchestrator MAY fix it inline in the batched gate-followup commit instead of filing a tracker (or, for INTRODUCED drift, instead of a remediation worker). This is the "Fixed" terminal state from `dev`'s no-loose-ends rule, and it is strictly faster than file-then-reclaim-then-spawn-a-worker for a one-line edit. Reserve filing / remediation for findings that need real code work, a recompile-gated change, or investigation. Per `dev`'s introduced/exposed test, prefer inlining INTRODUCED slate drift (you made the mess, fix it now); a PRE-EXISTING trivial doc nit may be inlined too when you are already editing that spec, else file it to avoid scope-creep.

**Mechanical filing from the worker's `## Trackers to file` block.** Gate worker briefings (per `dev`'s gate-policy injection) require workers to emit a `## Trackers to file` section with one ready-to-write blob per MED/LOW finding. The filing step is mechanical: for each `### issues/<slug>.md` header in the block, write the following content to disk verbatim and `git add`. No prose-to-file translation; no fields to invent. Filings land in a single batched commit per mid-iteration round.

### Mid-iteration checkpoint

Look in your invocation context for a `## Per-batch gate policy (from dev)` section — its bullets are the gates and the `Mid-batch checkpoint:` sub-section names the trigger conditions (typically "every 5 iterations since the last per-batch run" and "immediately after any iteration that touched a high-risk surface"). If the conditions are met, fire the gates before spawning the next iteration. Apply per-finding routing (above) to the gate output. Continue the loop after the gates (and any remediation workers) return.

## Iteration worker

Spawn one worker per iteration via the `orchestrate` skill. Each worker handles **exactly one issue** and returns; the orchestrator runs the loop. Briefing template (substitute `<SLUG>` with the slug from orchestrator step 1, and populate "Required verification gates" if the caller supplied a per-item gate policy):

> **Goal.** Implement exactly one backlog issue end-to-end. The orchestrator handles all other iterations; you handle only this one.
>
> **Slug:** `<SLUG>`
>
> **Pre-iteration HEAD:** `<PRE_ITERATION_HEAD>` (the SHA of HEAD before your claim commit; pass this to `backpressure` as the diff range for per-iteration scoping)
>
> **Git.** Commit DIRECTLY to the branch the loop runs on (the project's working branch — `master`/`main` unless told otherwise). Do NOT create a feature branch, do NOT `git checkout -b`. Run `git branch --show-current` first; if you are not on that branch, switch to it before claiming. The build loop's one-claim-one-close audit and its `git push` to the shared branch assume every iteration lands there — a stray feature branch silently diverges the loop. (This overrides any generic "branch before committing" git etiquette; the loop's model is trunk-based by design.)
>
> **Scope.** You may touch any file in the repo required to implement this single issue, including specs the issue's `## Doc refs` name and any ripple neighbors. **You may NOT claim another issue from `./issues/ready`. You may NOT iterate on a second slug inside this spawn.** You may not absorb unrelated pre-existing failures into your commits — log a separate `<repo>/issues/<slug>.md` for them and continue. You may not commit with backpressure failures unaddressed.
>
> **Exit condition** (verifiable, all three must hold):
> 1. `issues/<SLUG>.md` frontmatter is `status: closed`.
> 2. `git log` shows a commit on HEAD that includes both the implementation and the closure of `<SLUG>`.
> 3. `git push` for that commit succeeded (or you have explicitly logged a push failure in your return).
>
> When all three are true, emit the structured return below and stop. Do NOT run `./issues/ready`. Do NOT begin a second iteration.
>
> **Procedure** (apply each step in sequence; the implementation may land as one commit or several small ones — your call per logical sub-piece):
> 1. Read `issues/<SLUG>.md` to understand description, source refs, doc refs, and prior comments.
> 2. Read every spec named in the issue's `## Doc refs` via `cat specs/<stem>.md`. Specs describe planned design as readily as existing code — verify with grep before calling anything the spec names; if a spec references a type/function that doesn't exist yet, plan to build it as part of this claim.
> 3. Claim: edit frontmatter `status: open` → `status: in_progress`. Commit with message `claim <SLUG>`.
> 4. Implement per the issue body and referenced specs.
>    - If the issue's `type` is `bug`: reproduce → write a failing test that captures the bug → fix → re-run the test until it passes.
>    - Otherwise implement per the issue body.
>    - **Tracer bullet first.** Build a tiny end-to-end slice, validate it, then expand.
>    - **No placeholder code.** Real implementations only — no stubs, no `TODO: implement`, no `expect(true).toBe(true)`.
>    - **Update affected specs alongside code in the same commit.** Specs are SOURCE OF TRUTH at `<repo>/specs/<stem>.md`. Transitions like `approved` → `implemented` happen here when applicable.
>    - If you discover pre-existing spec drift while implementing, log a separate `<repo>/issues/<slug>.md` for it — do not absorb the drift into this claim. Keep the change focused.
> 5. Write tests (unit, property, or integration — pick what fits). No placeholder tests.
> 6. Consult the `backpressure` skill. Pass the `Pre-iteration HEAD` value (above) as the diff range so backpressure runs in per-iteration scoped mode per its "Per-iteration scoping" section. The skill scopes test invocation to the reverse-dep closure of touched crates, runs workspace-cheap gates as-is, and falls back to full-workspace automatically if the diff hits a workspace-trigger file. Fix every failure on your own changes. For pre-existing trivial failures (lint warnings, formatter drift, one-line type-fix), fix and continue. For pre-existing non-trivial failures (a real failing test on code you didn't touch), log a new `<repo>/issues/<slug>.md` and leave alone — do not absorb. Re-run backpressure until clean.
> 7. Run any **Required verification gates** named in the section below (the section is omitted entirely if no caller policy applied). Treat a failing gate the same as a failing backpressure check — fix the underlying issue or revert. If the fix touches code, re-run step 6 before proceeding.
> 8. Close: edit frontmatter `status: in_progress` → `status: closed`. Add a `## Comments` entry summarizing what was done.
> 9. Commit the implementation + spec updates + closure as one logical change (formatter residue may be a separate commit). Push.
> 10. Verify all three exit-condition clauses hold. Emit the structured return. Stop.
>
> **Inherited rules.**
> - Never reuse a slug.
> - Never claim an issue that's already `in_progress`.
> - Never commit with backpressure failures unaddressed.
> - If a failing test for a `bug`-type issue is impossible in isolation (requires live network, real credentials, hardware), document the manual reproduction in `## Comments` and proceed; do not fake a passing test.
> - If your own change creates a backpressure failure you cannot fix this iteration, revert the change, unclaim the issue (`in_progress` → `open`) with a `## Comments` entry explaining the blocker, and report. Do not commit the broken state.
> - **Gate output is not your terminal return.** When `code-review` / `verify` / `audit-specs` emits findings, that text is the GATE's output — NOT yours. Your iteration is not done. Continue: address any findings, finish steps 8 + 9, and only emit the structured return AFTER everything is committed AND pushed. If your last emitted text is a gate's findings (or any non-structured prose) and the exit condition is not met, you are NOT done — your next action MUST be a tool call.
>
> **Skills to consult.** `issues` (schema), `specs` (schema and updates), `backpressure` (full backpressure). Caller-required gates (`verify`, `code-review`, `audit-specs`) are named below when applicable.
>
> **Skills, scripts, and MCP tools to reach for.** The `mcp__unsandboxed-runner__*` wrappers (`run_pnpm`, `run_playwright`, `run_tauri_build`, `run_cargo`, `smoke_test_tauri`, etc.) for any shell command the sandbox blocks (network access, non-sandbox paths, long-running builds), and the project's own scripts named in spec or issue refs. The `just` task runner exposes lint/audit gates (`just lint`, `just audit`).
>
> **Long-running commands use MCP wrappers, not raw Bash.** For any cargo command, use `mcp__unsandboxed-runner__run_cargo` — pass argv as a string array (e.g. `args: ["test", "--workspace"]`, `args: ["clippy", "--workspace", "--all-targets", "--", "-D", "warnings"]`). For tauri build, use `mcp__unsandboxed-runner__run_tauri_build`. For pnpm, use `mcp__unsandboxed-runner__run_pnpm`. The wrappers run outside the sandbox and bypass Bash's timeout cap. Raw `cargo` via Bash is blocked by a PreToolUse hook (`redirect-bash-to-mcp.py`). NEVER end your turn while waiting on a backgrounded task — the harness treats final text without a pending tool call as turn-end, the worker goes dormant, and completion notifications don't wake it.
>
> **Required verification gates.** [The orchestrator populates this section from the caller-supplied `## Per-item gate policy (from dev)` section, or omits it entirely when no caller policy applied.]
>
> **Return format.**
> ```
> ## Slug
> <SLUG>
>
> ## Summary
> <one paragraph: what changed, which files, the backpressure outcome, which gates fired and their outcome>
>
> ## Commits shipped
> - <short-sha> <subject>
>
> ## Specs updated
> - <path>: <one-line nature of change>
> - (or "none" if no specs touched)
>
> ## Exit condition state
> met | not met + reason
>
> ## New work surfaced
> - <slug or one-line description> — <why it surfaced>
> - (omit the bullets and write the literal text "none" if nothing surfaced)
> ```
>
> You are a worker, not an orchestrator. Return text only. Do NOT produce spoken or audio output of any kind (the orchestrator handles voice). Do NOT spawn further workers via the Agent tool. Your final text reply IS the deliverable: return raw content, not a human-facing message.

## On completion

When the loop exits (either condition), report to the user:

- How many issues were implemented this run (slugs + one-line summary each).
- Whether the cap was hit, the backlog truly drained, or the backlog is blocked by unresolved deps (open issues exist but none are ready because their deps aren't closed).
- Any failures left unaddressed (e.g. a backpressure failure on the last iteration that the worker couldn't fix).
- **Aggregated new work surfaced.** Collect the `## New work surfaced` block from every iteration's worker return AND every remediation worker's return (remediation workers spawned at mid-iteration / session-close checkpoints are scoped iteration workers and contribute too). Surface the union under a top-level `## New work surfaced` section in your own report — slug + one-line description per item, grouped by which worker surfaced it. This is the hook a caller like `dev` uses to detect whether the build session genuinely drained the queue or merely re-filled it with follow-ups.
- **Session-close gates.** Look in your invocation context for a `## Session-close gate policy (from dev)` section. If present, AND the aggregated `## New work surfaced` section contains nothing that would queue more iterations into the current session, fire those session-close gates now. Surface findings in the report.
  - Pass the slate's full commit range in each gate-worker briefing and require INTRODUCED-BY-SLATE / PRE-EXISTING tagging per the per-finding routing rule.
  - Apply the same routing: HIGH → remediation; MED + INTRODUCED → remediation; MED + PRE-EXISTING → file as tracker; LOW → file as tracker.
  - **No loose ends.** Before declaring the build session complete, every surfaced finding from every gate run this session (per-iteration + mid-iteration + session-close) MUST be in a terminal state: fixed (commit landed), filed as `<repo>/issues/<slug>.md`, or explicitly deferred by the user. "Surfaced in the report as prose only" is NOT a terminal state — findings in chat alone are re-discovered every future gate run. The orchestrator (this skill) files the trackers itself; a single `chore(issues): file N session-close gate followups` commit covers them.

Do not silently move on if any iteration left the tree in a bad state.
