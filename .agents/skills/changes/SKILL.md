---
name: changes
description: Handling change requests — add a feature, fix a bug, modify behavior — from initial framing through planning, implementation, spec updates, verification, and commit. Consult whenever the user says "I want to add/change/fix X", describes a piece of work conversationally, supplies a bulleted list of changes, hands you a multi-phase plan, or asks for any focused code work that needs discussion before implementation. Size and item count are irrelevant — decomposition is the core job. Do not consult for issue-backlog work (which uses build) — this is for user-described work, not for the issues/ tracker.
---

# Changes

You are about to handle one or more change requests. The pipeline:

**decompose → plan (parallel workers) → user approval per item → implement (serial across items, with sub-worker fan-out within each item) → many small commits → push.**

A single user request often decomposes into many atomic items. Each item may itself land as many small commits via sub-worker fan-out. Atomicity is enforced at the sub-piece (commit) level, not the item level.

This is a pipeline. The conventions below are inlined here, not pulled in by reference.

## Why this shape

- **Decomposition first.** The user's input is raw material — a "fix this bug" can decompose into 8 atomic items. The slate IS the decomposed atomic set, not the user's literal phrasing.
- **Planning in parallel.** Multiple workers investigate, draft plans, and surface clarifying questions concurrently. The user answers interleaved.
- **Serial implementation across items.** Two impl workers editing the codebase simultaneously create merge pain and obscure failures. Serial keeps backpressure runs honest.
- **Sub-worker fan-out within an item.** When an item's implementation is genuinely multi-part, the impl worker spawns sub-workers (3-tier max: orchestrator → impl worker → sub-workers). Sub-workers research/draft; the impl worker applies + verifies + commits each sub-piece as its own atomic commit. This pushes atomicity down to the sub-piece level — even a coarse item lands as many small commits.

## Procedure

### 1. Receive and decompose

**Treat the user's input as raw material, not the final item slate.** Your first job is to convert it into atomic change items. A 5-item user list often becomes a 20-item atomic slate after decomposition. A single conversational "fix this bug" can decompose into 8 items. The split is not optional.

Run two pre-flight passes on the raw input before numbering anything.

**De-duplicate.** If two items describe the same change in different words, collapse them or flag the suspected duplication to the user. Spawning two workers against the same change wastes context and produces conflicting plans.

**Split coarse items.** What you pass to a planning worker must be small and atomic: one fix, one planner, one approved plan. If an item bundles N independently-verifiable fixes — distinct symptoms, distinct files, distinct planning surfaces — break it into N items.

Signs an item should split:
- "Fix these N findings in spec X" → one item per finding.
- "Update A and B in module Y" → split if A and B have independent failure modes.
- A description with multiple `and`-joined action verbs ("rename foo, refactor bar, document baz") → split per verb.
- The item arrived from an external source (audit report, code review, TODO list) rather than a user typing "do these together."

Signs an item is already atomic — leave alone:
- One symptom, one code path, one verifiable behavior change.
- Splitting would force a coordinated revert (the parts only make sense together).
- The user supplied the bundle deliberately and named the grouping.

**When the input is too vague to decompose** (e.g. "add some kind of analytics"), spawn ONE planning worker as a discovery worker. Brief it to investigate and propose a decomposition along with the plan. Relay back to the user for approval of the decomposition AND the plan.

Flag the split decision to the user when ambiguous. Do not silently fan out a dozen workers from a one-line request, and do not silently bundle a dozen findings into one worker.

Once the slate is atomic, number the items (Item 01, Item 02, …) and keep a running table of `(item-id, brief description, status)` throughout the session.

Statuses: `planning`, `waiting-for-approval`, `approved`, `implementing`, `committed`, `blocked`.

### 2. Fan out planning

For each item, spawn one worker via the `orchestrate` skill (Agent-tool spawn). Workers run concurrently. The briefing must be self-contained — workers inherit no skills, no context.

Worker briefing template:

> **Goal.** Take this single item through investigation and produce a plan. **Stop before implementing.** Return: (a) the proposed plan, numbered, (b) any clarifying questions for the user, (c) which specs are likely affected, (d) the exit condition (a verifiable command + expected outcome that proves the item is shippable), (e) for bug items, the observed-failure evidence (the concrete error you confirmed fires — not a hypothesis pattern-matched from the symptom; go get the log line, artifact, or reproduction during investigation).
>
> **Item:** \<verbatim decomposed item>
>
> **Scope.** READ-ONLY. You may read any file in the repo to investigate, but do not edit, create, move, or delete any file. Plans only.
>
> **The lifecycle this plan feeds into (so your plan anticipates downstream).** After approval, an implementation worker takes this plan and: writes the code (possibly fanning out sub-workers for multi-part work) → updates affected specs in the same commit as the code → runs a ripple check on neighbor specs → runs full backpressure → runs any caller-required verification gates (`dev` may inject `verify` for UI/IPC-touching items, `code-review` for non-trivial diffs) → logs a closed tracking issue in `<repo>/issues/` → commits and pushes. Many small commits per item is the norm. Your plan should be specific enough that the implementation worker doesn't need to re-design; it should name files to touch, specs to update, and the exit condition that proves the item is done — and if the item touches user-visible UI or the IPC surface, your plan should include a concrete user-flow assertion `verify` can exercise.
>
> **Skills, scripts, and MCP tools to reach for.** `specs` (schema + locations of any spec your plan would touch), `issues` (so you can name related backlog issues in your plan), `backpressure` (so the plan accounts for what verification will run), the `mcp__unsandboxed-runner__*` wrappers (`run_pnpm`, `run_playwright`, `run_tauri_build`, `smoke_test_tauri`, etc.) for any read-only shell command the sandbox blocks during investigation.
>
> **Return format.** Structured:
> ```
> ## Plan
> 1. ...
>
> ## Files to create/modify
> - path: purpose
>
> ## Design decisions
> - ...
>
> ## Specs likely affected
> - specs/<stem>.md: sections that may need updating, or "no update needed" with reasoning
>
> ## Exit condition
> A verifiable command + expected outcome that proves this item is shippable (e.g. `bash e2e/foo.sh exits 0`, `pytest passes`, `grep finds X in path`). If the item claims a guarantee — a refusal, a confirmation or authorization boundary, an invariant, a limit, a durability or integrity claim — the criteria must include at least one check that attempts the forbidden thing and asserts refusal, reached the way someone bypassing the feature would reach it, plus coverage of whichever substrate boundaries the code touches (concurrency, transactions, IPC, filesystem paths, clock / ordering).
>
> ## Evidence (bug items only)
> The concrete observed failure this plan targets — log line, captured artifact, reproduced error — with where it came from. If evidence is unobtainable, the literal label HYPOTHESIS-FIX plus why.
>
> ## Questions for user
> - ... (omit section if no questions)
> ```
>
> You are a worker, not an orchestrator. Return text only. Do NOT produce spoken or audio output of any kind (the orchestrator handles voice). Do NOT spawn further workers via the Agent tool. Your final text reply IS the deliverable: return raw content, not a human-facing message.

When a worker returns:

- Relay any clarifying questions to the user verbatim.
- Once the user responds, send the answers back to the worker via a follow-up spawn so it can refine the plan.

### 2b. Challenge the plan before approval

Every returned plan goes through this gate before you present it to the user — not just refined plans. Walk this checklist; if the worker can't answer, send the plan back for refinement.

1. **Trace the full path.** From trigger to symptom (or input to output), end-to-end, naming every file and condition.
2. **Question magic numbers.** If the fix changes thresholds or constants, demand evidence or reasoning for the values chosen. "Lower X" is not a plan.
3. **Enumerate triggers.** Multiple code paths producing this symptom? Confirmed which fires? A user-visible message that funnels several distinct errors into one string is not a diagnosis — the plan must identify the underlying error, not the message.
4. **Demand evidence for bug fixes.** A bug-fix plan must cite the concrete observed failure it targets: a log line, a captured artifact, a reproduced error, or forensic extraction from the failing environment. "Error X matches the symptom" is a hypothesis, not evidence. When evidence is genuinely unobtainable, the plan carries the explicit label `HYPOTHESIS-FIX`, and the label propagates: into the commit message, into the tracking issue, and into an open `<item>-field-verify` tracker that closes only when the original scenario re-runs successfully. A hypothesis fix is never described as "fixed" in issues, commits, or release notes.
5. **Require a reality anchor for external contracts.** When the item touches code that parses or validates artifacts produced by an external system (platform receipts, third-party API responses, file formats owned by someone else), the plan must name at least one captured real artifact used as a test fixture — or state that none exists yet and include obtaining one in the plan. Synthetic fixtures derived from the same spec or understanding the code was written from are self-confirmation, not verification: spec, code, and tests can all agree with each other and still all be wrong about the external system.
6. **Edge cases.** What inputs should STILL trigger the original behavior? Make the worker prove the fix doesn't break those.
7. **Silent failures.** Does the fix add observability so future debugging has breadcrumbs?
8. **Exit condition.** Is it verifiable? If you can't write a check that proves done, the plan isn't ready — send back.
9. **Adversary acceptance criteria.** When the item claims a guarantee — a refusal, a confirmation or authorization boundary, an invariant, a limit, a durability or integrity claim, or any behavior stated with *cannot* / *never* / *always* / *only* — the exit condition must include at least one automated check that *attempts the forbidden thing and asserts it is refused*, reached the way someone bypassing the feature would reach it (scripted call instead of the interactive prompt, the entry point invoked directly, hostile arguments). A plan whose criteria only exercise the guarantee the intended way proves it works when honored, which is not the claim — send it back.
10. **Substrate boundary.** Defects cluster where new code meets concurrency, transactions, IPC boundaries, filesystem paths, and clock / ordering assumptions: two writers racing, a lock already held, a precondition checked against a timestamp instead of a version, a path that escapes its root. Make the plan name which of these its code actually touches and how each is covered.

When the plan survives the checklist, present it to the user for explicit approval before moving the item to `approved`.

### 3. Serial implementation across items, sub-worker fan-out within each

Once an item is `approved`, queue it. **Only one item implements at a time across the slate.** Within an item, the impl worker may fan out sub-workers (one level of nesting; sub-workers do NOT spawn further — 3 tiers max).

Before constructing the impl-worker briefing, check your invocation context for caller-supplied policy (typically supplied by `dev`):

- A `## Per-item gate policy (from dev)` section — its bullets become the contents of the briefing's "Required verification gates" section (per the `orchestrate` skill's "Required verification gates" briefing-checklist item). If absent, omit "Required verification gates" from the briefing and the worker will skip step 5 of the per-sub-piece lifecycle.

For the next-in-queue approved item, spawn an implementation worker:

> **Goal.** Implement the approved plan for this item end-to-end. Each logical sub-piece lands as its own atomic commit; many small commits per item is the norm. Stop only when the exit condition is met. Return a summary of what shipped.
>
> **Item:** \<description>
> **Approved plan:** \<numbered plan>
> **Exit condition:** \<verifiable command + expected outcome from the plan>
>
> **Scope.** You may touch any file in the repo required to implement this approved plan, including specs the plan named and any ripple neighbors. You may NOT work any other item from the slate, absorb unrelated pre-existing failures into your commits (log a separate issue instead), or commit with backpressure failures unaddressed.
>
> **Sub-worker fan-out — permitted.** When the work splits into independent sub-pieces (e.g. multiple sources to cache, multiple files to write, multiple specs to update independently), spawn sub-workers per the `orchestrate` skill. Sub-workers research/draft per `orchestrate`'s default — they do NOT apply changes. You apply, verify, and commit each sub-piece separately. **One logical sub-piece = one commit.** Do not bundle unrelated sub-pieces into one commit. Sub-workers may NOT spawn further workers (3-tier max). When briefing a sub-worker, include this verbatim: *"You are a sub-worker. You may NOT spawn further Agent-tool workers. Return raw content for the orchestrator to apply."*
>
> **Per-sub-piece lifecycle** (apply each in sequence; commit at the end of each):
> 1. Implement the sub-piece (write code yourself, or fan out sub-workers for research/draft).
> 2. Update affected specs alongside code in this commit. Specs live at `<repo>/specs/<stem>.md`. Verify each claim against the new code. If you're rewriting more than half a section, rewrite the whole section. If a spec was `approved` and code now matches it, set frontmatter `status: implemented`. Run `specs/validate` to catch structural problems.
> 3. Ripple check the touched specs' neighbors (outgoing `refs:` list + incoming `grep -l "<stem>" specs/*.md`). When the neighborhood is small (≤2), inspect inline. When larger, invoke the `audit-specs` skill in scoped mode — pass the neighbor stems as the scope list and the 1-3 sentence diff summary as `DIFF_CONTEXT` so each worker scopes its claim-verification to only the claims plausibly affected by your change. Apply any HIGH/MED drift in this same commit. (See the audit-specs skill for the per-spec worker briefing template; do not re-author it inline.)
> 4. Run full backpressure for the project's stack. Fix every failure before continuing. If you fan out for parallel checks, inline the `backpressure` skill body into sub-worker briefings.
> 5. Run any **caller-required verification gates** for this sub-piece. The orchestrator may have included a "Required verification gates" section in this briefing (per the `orchestrate` skill's briefing checklist) — for example, `dev` injects `verify` for sub-pieces that touch user-visible UI / IPC, and `code-review` for non-trivial diffs. Run each gate per its trigger condition. Treat a failing gate the same as a failing backpressure check — fix the underlying issue or revert the sub-piece; do not commit a sub-piece with a gate failure unaddressed. **If the fix touches code, re-run full backpressure (step 4) to confirm nothing else broke before proceeding to step 6.** If no "Required verification gates" section is present, skip this step. `adversarial-verify` never appears in this section — it requires an agent that did not write the code, so the orchestrator fires it separately.
> 6. Log a tracking issue at `<repo>/issues/<slug>.md` with `status: closed`, capturing what changed, design decisions, specs updated. Skip if a sub-piece is genuinely part of a larger logical change that warrants one issue at the end — your call per sub-piece, but err toward one issue per commit.
> 7. Commit (code + specs + issue) with an imperative <72-char message. **Name your paths twice — staging and committing:** other agents are working in this same tree right now, and you share one index with them. `git add <path>` each file you changed, by name — never `git add -A`, `git add .`, or `git add -u` — then commit those same paths explicitly with `git commit -F - -- <path> <path>`, message heredoc'd on stdin. A bare `git commit` ships everything currently staged, including files another agent staged and has not committed yet. `git status` will show files you did not touch; leave them alone. Push. If push fails, report and continue — the commit is safe locally.
>
> Loop: pick the next sub-piece from the plan; repeat the lifecycle. Stop when the exit condition is met.
>
> **Inherited rules.**
> - Specs alongside code — non-negotiable. Do not defer with an issue.
> - When the approved plan's exit condition includes adversary criteria (a check that attempts the forbidden thing and asserts refusal), those checks ship in the same commit as the code they guard — the sub-piece is not done without them. Never describe a guarantee as holding, enforced, or safe on the strength of tests you wrote: your suite encodes your own mental model of the code. Report what you implemented and which adversary checks you added; an independent `adversarial-verify` agent, spawned by the orchestrator, decides whether the guarantee survives.
> - Push after each commit. If push fails, report and continue.
> - If backpressure fails on your own changes and you cannot fix it in this iteration, do not commit broken state; report the blocker.
> - If the approved plan carries the `HYPOTHESIS-FIX` label, the label propagates: every commit message and the tracking issue name it, an open `<item>-field-verify` tracker must exist before the item closes, and the change is described as "fix attempted, pending verification" — never "fixed." Same discipline when the item is a field-reported bug whose failing scenario cannot be re-run from here (see the `issues` skill's field-reported closing rule).
> - **Gate output is not your terminal return.** When a verification gate (`code-review`, `audit-specs`, `verify`, etc.) emits findings, that text is the GATE's output — NOT yours. Your turn is not done. Continue: address any findings, complete steps 6 and 7 of the lifecycle for that sub-piece, move to the next sub-piece, and only emit the structured `## Summary / ## Commits shipped / ...` return AFTER every sub-piece is committed AND the exit condition is met. If your last emitted text is a gate's findings (or any non-structured prose) and the artifact is incomplete, you are NOT done — your next action MUST be a tool call, not more prose.
>
> **Long-running commands use MCP wrappers, not raw Bash.** For any cargo command, use `mcp__unsandboxed-runner__run_cargo` — pass argv as a string array (e.g. `args: ["test", "--workspace"]`, `args: ["clippy", "--workspace", "--all-targets", "--", "-D", "warnings"]`). For tauri build, use `mcp__unsandboxed-runner__run_tauri_build`. For pnpm, use `mcp__unsandboxed-runner__run_pnpm`. The wrappers run outside the sandbox and bypass Bash's timeout cap. Raw `cargo` via Bash is blocked by a PreToolUse hook (`redirect-bash-to-mcp.py`). NEVER end your turn while waiting on a backgrounded task — the harness treats final text without a pending tool call as turn-end, the worker goes dormant, and completion notifications don't wake it.
>
> **Return format.**
> ```
> ## Summary
> ## Commits shipped
> - <short-sha> <subject>
> ## Specs updated
> ## Backpressure outcome
> ## Push outcome
> ## Exit condition state
> met | not met + reason
> ## New work surfaced
> - <slug or one-line description> — <why it surfaced (pre-existing drift logged separately, sub-piece that became its own item, spec change that implies downstream work, etc.)>
> - ... (omit the bullets and write the literal text "none" under the heading if nothing surfaced)
> ```
>
> You are a worker (mini-orchestrator). Return text only. Do NOT produce spoken or audio output of any kind (the orchestrator handles voice). You MAY spawn sub-workers (one level only) per the `orchestrate` skill. Sub-workers MAY NOT spawn further. Your final text reply IS the deliverable: return raw content, not a human-facing message.

When the impl worker returns with commits and the exit condition met, mark the item `committed`, then dequeue the next approved item.

Before dequeueing the next item, **check the tree is clean** (`git status`). Worker died mid-implement → see Edge cases.

**Mid-batch checkpoint.** Before dequeueing, check whether per-batch gates should fire now. Look in your invocation context for a `## Per-batch gate policy (from dev)` section — its bullets are the gates and the `Mid-batch checkpoint:` sub-section names the trigger conditions (typically "every 5 items closed since the last per-batch run" and "immediately after any item that touched a high-risk surface"). If the conditions are met, fire the gates before dequeueing the next item.

When firing per-batch gates, pass the slate's commit range (the SHA range covering items closed since the slate started) in each gate-worker briefing AND require the worker to tag every finding INTRODUCED-BY-SLATE or PRE-EXISTING with a one-line git-log/git-blame justification. Findings handled per the routing rule below.

**`adversarial-verify` is a fresh-context spawn.** When a policy bullet names `adversarial-verify`, the gate worker must be a brand-new agent that did not implement any item in the batch — the implementer can never be its own adversary. The bullet carries the guarantee in plain English and the surface it lives on; put both in the briefing along with the commit range. When a spec covers the surface, take the guarantee and its violation attempt verbatim from that spec's `### Absolutes register` rather than restating them — the register is where the claim and the attempt that would disprove it are already written down, and paraphrasing is how an adversary ends up testing something narrower than the claim. Instruct the worker to: attempt the violation from every route the code permits (scripted invocation instead of the interactive path, the CLI / IPC / API entry point called directly, hostile arguments, two callers at once); probe the boundary between the new code and its substrate — the database (concurrent writers, lock contention, transaction scope, preconditions built on clocks instead of versions), IPC, the filesystem, and ordering assumptions; and treat the green suite as its starting position rather than as evidence.

**A remediation goes back through this gate.** When a remediation worker fixes a finding on a guaranteed surface — this gate's finding, a `security-review` HIGH, any other — the fix is new code on that surface verified only by its author, so spawn a fresh adversary over the fix's commit range: an agent that wrote neither the original code nor the remediation. Brief it to open on the sibling operations that reach the same forbidden state (`create` constrained while `update` still gets there; the interactive path guarded while the scripted one is not). The route the report named is the one the fixer had in mind; the adjacent route is the finding.

**Per-finding routing (per `dev`'s gate-failure recovery + no-loose-ends rule):**
- HIGH severity → auto-spawn a remediation worker (scoped strictly to the failure; do not absorb unrelated work) and continue — surface the failure + fix in the on-completion summary.
- MED severity tagged INTRODUCED-BY-SLATE → auto-spawn a remediation worker (slate-introduced regression; same treatment as HIGH).
- MED severity tagged PRE-EXISTING → file as a tracker issue at `<repo>/issues/<slug>.md` (status: open) before dequeueing the next item — do NOT remediate. Surface in the on-completion summary.
- LOW severity (any tag) → file as a tracker issue (same shape as PRE-EXISTING MED). Do NOT remediate. Surface in the on-completion summary.

**Mechanical filing from the worker's `## Trackers to file` block.** Gate worker briefings (per `dev`'s gate-policy injection) require workers to emit a `## Trackers to file` section with one ready-to-write blob per MED/LOW finding. The orchestrator's filing step is mechanical: for each `### issues/<slug>.md` header in the block, write the following content to disk verbatim and `git add`. No prose-to-file translation; no fields to invent. Filings land in a single batched commit per mid-batch round (e.g. `chore(issues): file N mid-batch <round> gate findings`). If no policy section is present, skip the checkpoint and dequeue as today.

### 4. Throughout: communicate the state

After every meaningful event (plan ready for approval, item implementing, commit landed, item committed, item blocked), give the user a brief status snapshot — which items are at which status, commit count per item. The user is the loop's referee.

### 5. On completion

When all items are `committed` or `blocked`:

- Summarize what landed (committed items + commit count + leading sha, one line each).
- Surface any blocked items with the reason.
- Surface any items whose worker reported push failure.
- **Aggregate new work surfaced.** Collect the `## New work surfaced` block from every impl worker's return AND every remediation worker's return (remediation workers spawned at mid-batch / session-close checkpoints are scoped impl workers and contribute too). Surface the union under a top-level `## New work surfaced` section in your own return — slug + one-line description per item, grouped by which worker reported it. This is the hook a caller like `dev` uses to detect "more work has surfaced from this run" for session-close decisions.
- **Session-close gates.** Look in your invocation context for a `## Session-close gate policy (from dev)` section. If present, AND the aggregated `## New work surfaced` section contains nothing that would queue more items into the current session, fire those session-close gates now. Surface findings in the on-completion summary.
  - Pass the slate's full commit range in each gate-worker briefing and require INTRODUCED-BY-SLATE / PRE-EXISTING tagging per the mid-batch routing rule above.
  - Apply the same routing: HIGH → remediation; MED + INTRODUCED → remediation; MED + PRE-EXISTING → file as tracker; LOW → file as tracker.
  - **Nothing guaranteed ships unverified.** Fire `adversarial-verify` (fresh-context spawn, per the mid-batch checkpoint section) for every guaranteed surface this slate touched that has changed since an independent agent last tried to break it — a remediation commit counts as a change. Do not report the slate complete — or describe any guarantee as holding — while one is outstanding.
  - **No loose ends.** Before declaring the slate complete, every surfaced finding from every gate run this session (per-item + mid-batch + session-close) MUST be in a terminal state: fixed (commit landed), filed as `<repo>/issues/<slug>.md` (open or won't-fix), or explicitly deferred by the user. "Surfaced in the report as prose only" is NOT a terminal state — findings in chat alone are re-discovered by every future gate run, burning cycles forever. The orchestrator (this skill) files the trackers itself (not delegated to a worker); a single `chore(issues): file N session-close gate followups` commit covers them.
- Do not silently swallow a blocker.

## Hard rules

- **Decompose before anything else.** The user's input is raw material. Never fan out planning without running the decomposition pass.
- **Never implement two items simultaneously.** Even if they look independent, serialize across items. Within an item, sub-worker fan-out is allowed and encouraged for multi-part work.
- **Atomicity at the sub-piece (commit) level.** Many small commits per item is the norm. One logical sub-piece = one commit. Bundled commits are a bug.
- **Sub-workers may NOT spawn further workers.** 3-tier max: orchestrator → impl worker → sub-workers.
- **Surface plans before implementing.** Each item must reach explicit user approval before its implementation worker spawns.
- **Specs alongside code — non-negotiable.** Every impl-worker briefing must explicitly require this. No "circle back" issues.
- **Every plan names an exit condition.** A verifiable command + expected outcome. If a planner can't write one, the plan isn't ready. When the item claims a guarantee, that condition must include a check that attempts the forbidden thing and asserts refusal — happy-path-only criteria do not accept a guarantee.
- **No agent is the sole verifier of code it wrote.** A guaranteed surface is described as "implemented, not independently verified" until a fresh-context `adversarial-verify` agent has tried to break it and come back clean.
- **If a worker auto-implements** (skips the plan-approval checkpoint and ships code from what was supposed to be a planning spawn), surface this immediately and stop the queue. Do not silently accept the work. Investigate, revert if needed, re-spawn with tighter briefing.

## Stay above the work

You are the top-level orchestrator. Investigation, analysis, implementation, and ripple checks belong to workers (planning) and impl workers + their sub-workers (impl). Default to delegating:

- **Don't go fishing in source.** No exploratory Grep/Glob/Agent sweeps to "understand the codebase" yourself.
- **Don't pre-investigate before briefing.** If you read code first, your briefing biases the worker.
- **Don't implement.** Code changes happen inside the spawned impl worker (and its sub-workers), not in the orchestrator.

Exception: a single targeted `Read` on a known file is fair when a worker asks a one-line clarifying question (e.g. "does file X export function Y?"). Resist scope creep — one file, one check, then back to orchestration.

## When to push back

### When items conflict

Two items conflict when one undoes the other, or they touch overlapping code with incompatible designs. Surface this immediately — do not plan both in parallel as if independent. Ask the user which wins, drop one, or merge into a single redrawn item before fanning out.

### When items have dependencies

Item B depends on Item A when B's plan can only be evaluated against post-A state (B reads a file A creates, B modifies an API A introduces). Dependents are not in conflict — both should ship — but they need sequencing.

Plan both in parallel; the planning workers investigate concurrently. B's worker notes "this plan assumes Item A lands first." Enforce sequencing in the implementation queue: A first, then B. If A's implementation materially changes the surface B planned against, re-spawn B's planner with the post-A state before approval.

If the dependency is one-way and minor (B mentions A but does not require it), queue ordering alone is enough. If tight (B is meaningless without A), make it explicit in the approved plan so the user sees the coupling.

## When NOT to push back

**Size of the work is not a pushback reason.** A multi-day, multi-deliverable plan is exactly what this skill is for. Decomposition is the core job.

**Item count is not a pushback reason.** Single conversational item or 30-item plan — same skill, same flow. The decomposition pass handles the count.

Reserve pushback for genuine skill mismatch — see "Skill fit by shape" below.

## Skill fit by shape (not size)

- "User described change(s) — single conversational or multi-item list or multi-phase plan" → `changes` (this skill). Size and count irrelevant.
- "Approved specs need to become a backlog" → `spec-to-issues`.
- "Claim and ship from an existing backlog" → `build`.

**Worked counter-example.** User hands you a 5-phase, 30-deliverable, ~17-day plan. This is NOT 5 items and NOT "too big for changes." It's ~30 atomic items with sequencing — decompose, fan out planning, serialize implementation. The size of the project is irrelevant to the shape decision.

## Edge cases

- **Worker dies mid-implement.** Before dequeueing the next approved item, check `git status`. A dirty tree is not automatically this worker's: other agents may be live in it, so first narrow the file list to the paths the dead worker's approved plan named and treat everything else as someone else's in-flight work — untouched, uncommitted, unreverted. If the plan's files are staged and the edits look complete (worker hit a timeout late in the run), default to spawning a **finish-the-job worker** scoped strictly to "verify backpressure on the staged work + commit + push those paths by name, no redesign, no new files; apply only mechanical fixes (formatter, snapshot)." When the staged work is genuinely incomplete or wrong, discard only those paths (`git restore --staged --worktree <path>`) and re-spawn from scratch — never `git reset --hard`, which takes the rest of the tree with it. Surface the dirty tree to the user; accept their override before acting.
- **Duplicate items.** De-dupe before fanning out (step 1). When ambiguous, flag both items to the user and ask.
- **Push failure during a commit step.** The impl worker continues — commits are safe locally. Mark the item `committed`, record the push-failure status, surface in the on-completion summary.
- **Blocked-then-unblocked items.** When the user clarifies a blocker, re-queue the item. If the blocker shifted scope, re-enter planning with a fresh spawn against the new state.
- **Sub-worker attempts to spawn another worker.** This violates the 3-tier rule. The impl worker briefs sub-workers explicitly with "you may NOT spawn further Agent-tool workers." If a sub-worker violates anyway, treat its return as a failed iteration — investigate the briefing and re-spawn with tighter constraint.
- **Conversational single-item case.** When the user describes one thing conversationally ("I want to add X"), the flow is the same: decompose (often to N=1 or N=2), spawn one planning worker, get approval, spawn impl worker. The planning worker handles clarifying-question round-trips via the orchestrator relay. Slight overhead vs in-loop conversation; accepted for uniformity + sub-piece atomicity throughout.
