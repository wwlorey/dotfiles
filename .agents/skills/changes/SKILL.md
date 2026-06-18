---
name: changes
description: Orchestrating multiple change requests in parallel through their planning phases and serially through their implementation phases. Consult whenever the user supplies multiple distinct items to add/change/fix ("here are 5 things I want done", a bulleted list of changes, a backlog they want worked through). For a single change item, use the change skill instead. Do not consult for issue-backlog work (which uses build) — this is for user-supplied lists of changes, not for the issues/ tracker.
---

# Changes

You are about to orchestrate several independent change requests from a user-supplied list. Each item walks through the same lifecycle as the `change` skill — discuss, plan, get approval, implement, update specs, run backpressure, log issue, commit — but the orchestration interleaves: planning runs in parallel across items, implementation runs serially one item at a time.

This is a pipeline. The conventions below are inlined here, not pulled in by reference.

## Why this shape

- **Planning in parallel** is safe and fast — multiple workers can investigate, draft plans, and surface clarifying questions concurrently. The user can answer questions interleaved.
- **Implementation in serial** keeps the repo state coherent — two workers editing the codebase simultaneously create merge pain and obscure failures. Serial implementation also keeps backpressure runs honest: each commit is verified against a known-clean tree.

## Procedure

### 1. Receive the list

The user gives you a list of items they want done — bullets, numbered list, or a paragraph that names several changes. Number each item internally (Item 01, Item 02, …) and keep a running table of `(item-id, brief description, status)` throughout the session.

Statuses: `planning`, `waiting-for-approval`, `approved`, `implementing`, `committed`, `blocked`.

Before fanning out, run two pre-flight passes on the list.

**De-duplicate.** If two items describe the same change in different words, collapse them or flag the suspected duplication to the user before spawning. Spawning two workers against the same change wastes context and produces conflicting plans.

**Split coarse items.** What you pass to a `change` worker must be small and atomic: one fix, one planner, one commit. If an item bundles N independently-verifiable fixes — distinct symptoms, distinct files, distinct planning surfaces — break it into N items. Bundles cost context (the planner researches more than it needs), cost rework (one shaky finding contaminates the whole plan), and cost bisect (a coarse commit is not a clean revert unit).

Signs an item should split:
- "Fix these N findings in spec X" → one item per finding.
- "Update A and B in module Y" → split if A and B have independent failure modes.
- A description with multiple `and`-joined action verbs ("rename foo, refactor bar, document baz") → split per verb.
- The item arrived from an external source (audit report, code review, TODO list) rather than a user typing "do these together."

Signs an item is already atomic — leave alone:
- One symptom, one code path, one verifiable behavior change.
- Splitting would force a coordinated revert (the parts only make sense together).
- The user supplied the bundle deliberately and named the grouping.

Flag the split decision to the user when ambiguous; do not silently fan out a dozen workers from a one-line request, and do not silently bundle a dozen findings into one worker.

### 2. Fan out planning

For each item, spawn one worker via the `orchestrate` skill (Agent-tool spawn). Workers run concurrently. Each worker's briefing must include the full `change` procedure inlined (workers don't see other skills' bodies).

Worker briefing template (paste the body of the `change` skill into the briefing, then add):

> **Goal.** Take this single item through discussion and produce a plan. **Stop before implementing.** Return: (a) the proposed plan, numbered, (b) any clarifying questions for the user, (c) which specs are likely affected.
>
> **Override on the inlined change body.** The inlined `change` skill body describes the full lifecycle through commit. **Ignore steps 3 onward** of the inlined change body — your job ends at presenting a plan. Do not implement, do not update specs, do not run the step 4.5 ripple check, do not run backpressure, do not log an issue, do not commit. Stop at the plan.
>
> **Item:** <verbatim from user's list>
>
> **Scope.** READ-ONLY. You may read any file in the repo to investigate, but do not edit, create, move, or delete any file. Plans only.
>
> **Skills, scripts, and MCP tools to reach for.** `specs` (schema and locations of any spec your plan would touch), `issues` (so you can name related backlog issues in your plan), the `mcp__unsandboxed-runner__*` wrappers (`run_pnpm`, `run_playwright`, `run_tauri_build`, `smoke_test_tauri`, etc.) for any read-only shell command the sandbox blocks during investigation.
>
> **Return format.** Structured: `## Plan`, `## Questions for user`, `## Specs likely affected`. If no questions, omit the section.
>
> You are a worker, not an orchestrator. Do NOT produce a spoken end-of-turn report. Do NOT call any TTS / voice / `run_dic` tool. Do NOT spawn further workers via the Agent tool — return your result directly. Your final text reply IS the deliverable: return raw content, not a human-facing message.

When a worker returns:

- Relay any clarifying questions to the user verbatim.
- Once the user responds, send the answers back to the worker via a follow-up spawn so it can refine the plan.

### 2b. Challenge the plan before approval

Every returned plan goes through this gate before you present it to the user — not just refined plans. Walk this checklist against the plan; if the worker can't answer, send the plan back for refinement before approval:

1. **Trace the full path.** From trigger to symptom (or input to output), end-to-end, naming every file and condition. If the worker can't trace it, the analysis is incomplete.
2. **Question magic numbers.** If the fix changes thresholds or constants, demand evidence or reasoning for the specific values chosen. "Lower X" is not a plan.
3. **Enumerate triggers.** Are there multiple code paths producing this symptom? Has the worker confirmed which one is actually firing?
4. **Edge cases.** What inputs should STILL trigger the original behavior? Make the worker prove the fix doesn't break those.
5. **Silent failures.** Does the fix add observability (logs / metrics / errors that propagate) so the next person debugging a similar issue has breadcrumbs?

When the plan survives the checklist, present it to the user for explicit approval before moving the item to `approved`.

### 3. Serialize implementation

Once an item is `approved`, queue it for implementation. **Only one item implements at a time.**

For the next-in-queue approved item, spawn a worker with the full `change` skill body inlined plus:

> **Goal.** Implement the approved plan for this item end-to-end: write the code, update specs alongside (no defer), run the step 4.5 ripple check on touched specs, run full backpressure, log the tracking issue, commit, push. Return a one-paragraph summary of what shipped.
>
> **Item:** <description>
> **Approved plan:** <numbered plan from the planning phase>
>
> **Scope.** You may touch any file in the repo required to implement this single approved plan, including the specs the plan named as affected and any neighbors the step 4.5 ripple check surfaces. You may NOT work any other item from the user's list, absorb unrelated pre-existing failures into this commit (log a separate issue instead), or commit with backpressure failures unaddressed.
>
> **Specs alongside code — non-negotiable.** Update every affected spec in the same commit as the code, per the `change` skill's step 4. Do not defer with an issue saying "circle back to update the spec." After step 4, run the step 4.5 ripple check on the touched specs and apply any cascading drift in the same commit.
>
> **Skills, scripts, and MCP tools to reach for.** `specs` (schema, validation, ripple), `issues` (schema and operations for the tracking issue), `backpressure` (full backpressure for the stack), `orchestrate` (you are spawned via it; if step 4.5 ripple surfaces multiple neighbors you may fan out workers per its template), the `mcp__unsandboxed-runner__*` wrappers (`run_pnpm`, `run_playwright`, `run_tauri_build`, `smoke_test_tauri`, etc.) for any shell command the sandbox blocks (network access, non-sandbox paths, long-running builds).
>
> **Inherited rules.**
> - Project commit conventions and issue/spec locations as inlined in the `change` body.
> - Push after the commit. If push fails (no upstream, network, conflict), report the failure and continue — the commit is safe locally.
> - If backpressure fails on your own changes and you cannot fix it this spawn, do not commit broken state; report the blocker.
>
> **Return format.** `## Summary`, `## Files changed`, `## Specs updated`, `## Backpressure outcome`, `## Push outcome`.
>
> You are a worker, not an orchestrator. Do NOT produce a spoken end-of-turn report. Do NOT call any TTS / voice / `run_dic` tool. Do NOT spawn further workers via the Agent tool — return your result directly. Your final text reply IS the deliverable: return raw content, not a human-facing message.

When the worker returns with a commit (and a push attempt — failure is non-blocking), mark the item `committed`, then dequeue the next approved item.

Before dequeueing the next item, **check the tree is clean** (`git status`). If the previous worker died mid-implement and left a dirty tree, do not start the next item — see the edge cases below.

### 4. Throughout: communicate the state

After every meaningful event (plan ready for approval, item implementing, item committed, item blocked), give the user a brief status snapshot — which items are at which status. The user is the loop's referee; they need to see progress to direct it.

### 5. On completion

When all items are `committed` or `blocked`:

- Summarize what landed (committed items, one line each).
- Surface any blocked items with the reason.
- Surface any items whose worker reported push failure (committed locally, not on the remote yet) so the user can push or investigate.
- Do not silently swallow a blocker.

## Hard rules

- **Keep what reaches `change` small and atomic.** Run the split pass in step 1 before fanout, and again before any late-arriving item enters the queue. One fix, one planner, one commit.
- **Never implement two items simultaneously.** Even if they look independent, serialize. Backpressure runs must observe a clean tree.
- **Never send multiple approve-or-resume signals in one turn.** Each implementation worker runs to its commit before the next is unblocked.
- **Every implementation briefing must explicitly require specs-alongside-code** (no defer with an issue). This is the `change` skill's rule; the orchestrator's job is to make sure each implementation worker carries it forward.
- **Surface plans before implementing.** Each item must reach explicit user approval before its implementation worker spawns.
- **If a worker auto-implements** (skips the plan-approval checkpoint and ships code in what was supposed to be a planning spawn), surface this to the user immediately and stop the queue — do not silently accept the work. Investigate whether to revert, re-spawn against a tighter briefing, or accept on explicit user override. A worker that ignored the "stop before implementing" override on the planning briefing is a briefing failure to diagnose, not a free implementation to bank.

## Stay above the work

You are the orchestrator. Investigation, analysis, and implementation belong to workers; your job is to brief, relay, and synthesize. Default to delegating:

- **Don't go fishing in source.** No exploratory Grep/Glob/Agent sweeps to "understand the codebase" yourself — that's a worker task.
- **Don't pre-investigate before briefing.** If you read code first, your briefing biases the worker. Frame the goal, let the worker investigate.
- **Don't implement.** Code changes happen inside the spawned implementation worker, not in the orchestrator.

Exception: a single targeted `Read` on a known file is fair when a worker asks a one-line clarifying question and a spawn would be obvious overkill (e.g. "does file X export function Y?"). Resist scope creep — one file, one check, then back to orchestration.

## When to push back

### When items conflict

Two items conflict when one undoes the other, or they touch overlapping code with incompatible designs. Surface this immediately — do not plan both in parallel as if independent, and do not let the user discover the collision at implementation time. Ask the user to clarify which one wins, drop one, or merge the two into a single redrawn item before fanning out.

### When items have dependencies

Item B depends on Item A when B's plan can only be evaluated against the post-A state of the codebase (B reads a file A creates, B modifies an API A introduces, B's tests rely on A's behavior). Dependent items are not in conflict — both should ship — but they need sequencing.

Plan both in parallel: the planning workers can investigate concurrently against the current tree, and B's worker can note its assumption "this plan assumes Item A lands first." Then enforce the sequencing in the implementation queue: A implements first, then B. If A's implementation materially changes the surface B planned against, re-spawn B's planner with the post-A state before approval.

If the dependency is one-way and minor (B mentions A but does not require it), the queue ordering alone is enough. If the dependency is tight (B is meaningless without A), make it explicit in the approved plan so the user sees the coupling.

## Edge cases

- **Worker dies mid-implement.** Before dequeueing the next approved item, check `git status`. If the tree is dirty (uncommitted changes from the failed worker), do not start the next item — starting a new worker on a dirty tree compounds the failure. Inspect the staged work: if the file list matches the approved plan and the substantive edits look complete (the worker hit something like a timeout, a hung Monitor loop, or a confused tail message late in the run), default to spawning a **finish-the-job worker** scoped strictly to "verify backpressure on the staged work + commit + push, no redesign, no new files; apply only mechanical fixes (formatter, snapshot) along the way." This preserves the ~10–30 min of work already done and is the right call most of the time. Fall back to `git reset --hard HEAD` + re-spawn from scratch only when the staged work is genuinely incomplete or wrong. Surface the dirty tree to the user with the failing item's id and the recommended option (almost always finish-the-job); accept their override before acting.
- **Duplicate items in the user's list.** De-dupe before fanning out (see step 1). If two items look similar but you're not sure they're duplicates, flag both to the user and ask before spawning. Two planning workers against the same change waste context and surface conflicting plans for the user to reconcile.
- **Push failure during implementation worker's commit step.** The worker reports the push failure and continues per the `change` skill — the commit is safe locally. Mark the item `committed` (the substantive work shipped), but record the push-failure status separately and surface it in the on-completion summary so the user can push or investigate. Do not block the queue on a push failure; the next approved item can still proceed against the locally-committed tree.
- **Blocked-then-unblocked items.** When the user later clarifies a blocker (answers a question, resolves a conflict, drops the competing item), re-queue the previously-blocked item. If the blocker shifted the item's scope (the user changed what they want, or the conflicting item landed and altered the surface), re-enter planning and spawn a fresh planning worker against the new state. If the blocker was purely external (waiting on a decision that's now made and the scope is unchanged), jump back into the approved queue directly. Do not lose the item silently between turns — keep it in the status table until it reaches `committed` or the user explicitly drops it.
