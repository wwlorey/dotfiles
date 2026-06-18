---
name: spec-to-issues
description: Materializing an approved spec into the implementation backlog — reading the spec, walking the codebase to find the gap, and authoring `status: open` issues that, once implemented, bring code into alignment with the spec. Consult whenever the user says "spec-to-issues for X", "incarnate this spec", "generate the backlog for Y", "fan out issues from the spec", or has just promoted a spec from draft to approved and now wants the work queued. Also consult when a build run reports "backlog empty" but approved specs exist whose code hasn't been brought into alignment — those specs need to be materialized into issues before build can resume.
---

# Spec to issues

You are about to walk one or more `approved` specs and author the open issues needed to bring code into alignment with each spec. The output is a queue of `status: open` issue files in `<repo>/issues/`. This pipeline does **not** touch code — code happens later, when `build` consumes the queue.

This is a pipeline. The conventions below are inlined here, not pulled in by reference. The pipeline runs in the agent's main loop — you, this turn, are the orchestrator and the iteration worker both. Each ralph-loop iteration is one sequential pass of the steps below performed by you directly. The only Agent-tool spawns are the optional parallel-walking sub-workers inside step 3, and per the two-tier rule in the `orchestrate` skill those sub-workers do not themselves spawn further workers.

## Procedure

### 0. Bootstrap the backlog directory

Before processing any spec, ensure the project has somewhere to write issues:

- If `<repo>/issues/` does not exist, follow the `issues` skill to create it.
- If `<repo>/issues/ready` does not exist, copy it from the issues skill's `scripts/ready` and `chmod +x` it.

The canonical bootstrap prose lives in the `issues` skill; do not duplicate it here.

### 1. Identify the target spec(s)

If the user named a spec, target that one. Otherwise, list every `approved` spec:

```
grep -l "^status: approved$" specs/*.md
```

Ask the user which to fan out into issues. If they say "all," process them one per ralph-loop iteration (see below).

**Idempotency guard.** Before processing a spec, check whether it has already been materialized:

```
grep -l "specs/<stem>.md" issues/*.md
```

If matches exist, the spec was already fanned out. Default behavior: **skip** it and move to the next target. Override only if the user explicitly asks to re-walk a spec (e.g. the spec has substantially evolved since it was last materialized) — in that case, re-read the existing covering issues first so new ones don't collide on slug or duplicate scope, and add issues only for the delta. This guard prevents slug-collision duplicates on re-run.

### 2. Read the spec end-to-end

For the chosen spec, read `specs/<stem>.md` in full. Note:

- **Architecture** — what components exist or must exist
- **Dependencies** — which other specs (and external systems) interact
- **Error handling** — failure modes the implementation must cover
- **Testing** — how the spec says the work is verified end-to-end

Read each spec named in the `refs:` frontmatter for boundary context.

**Thin-spec guard.** If `## Architecture` is one line, `## Testing` is TBD or hand-wavy, or any required H2 section is too thin to drive concrete issues, **STOP** — do not fan out. Route the spec back to the `spec` skill's harden phase before materializing. Thin specs produce thin issues, and the self-check in step 5 will pass vacuously on TBDs.

### 3. Walk the codebase against the spec

For each component the spec describes, find the corresponding code. The point is to surface the **gap**: what does the code already do, what does the spec say it should do, where is the delta?

Categorize what you find:

- **Implementation gaps** — code that doesn't exist yet
- **Implementation drift** — code exists but doesn't match the spec (file a `bug`-type issue)
- **Dead code** — code the spec retired or never described (file a `chore`-type issue)
- **Documentation gaps** — README / module docs / inline docs out of sync
- **Testing gaps** — behaviors the spec calls testable that have no test

When the spec is large enough that one focused agent would lose context, use the `orchestrate` skill to spawn parallel sub-workers — one per component or section of the spec. These sub-workers walk in read-only mode and return structured findings; you (the orchestrator-and-iteration-worker) author the issues in step 4.

Sub-worker briefing template (inline; substitute the bracketed slots):

> **Goal.** Walk one component of an approved spec against the codebase and return a structured gap report. You are not authoring issues — you are surfacing the deltas the orchestrator will turn into issues.
>
> **Scope.** Read-only. You may read `specs/<STEM>.md`, the spec's named `refs:`, and any code files relevant to the assigned component: [SECTION-OR-COMPONENT]. Do NOT edit any file. Do NOT write to `issues/`.
>
> **Procedure.**
> 1. Read `specs/<STEM>.md` in full to ground the spec's claims.
> 2. Focus on the assigned scope: [SECTION-OR-COMPONENT]. Find the corresponding code via `grep -r`, `find`, or whatever locator fits the project.
> 3. For each finding, classify as one of: implementation gap, implementation drift, dead code, documentation gap, testing gap.
> 4. For each finding, suggest a slug stem (lowercase, hyphenated, prefixed with the spec's domain — e.g. `auth-add-oauth-callback`) and one-line scope.
>
> **Return format.** A structured block, no prose preamble:
>
> ```
> Component: [SECTION-OR-COMPONENT]
>
> Findings:
> - category: <gap|drift|dead-code|doc|test>
>   suggested-slug: <prefix-verb-noun>
>   scope: <one line>
>   source-refs: <paths>
>   doc-refs: <paths>
>   notes: <anything the orchestrator needs to know>
> - ...
>
> Open questions: <any ambiguity in the spec the orchestrator must resolve>
> ```
>
> **Skills, scripts, and MCP tools to reach for.** `specs` skill (schema you're reading), `issues` skill (schema the orchestrator will use — quote suggested slugs and refs in its vocabulary), the project's own search tools (`grep`, `rg`, `find`), and any project script named in the spec's `## Testing` section.
>
> **Inherited rules.** The issues directory is the project's `<repo>/issues/` backlog — not GitHub Issues. Slugs are lowercase, hyphenated, unique, prefixed with the spec's domain.
>
> You are a worker, not an orchestrator. Do NOT produce a spoken end-of-turn report. Do NOT call any TTS / voice / `run_dic` tool. Do NOT spawn further workers via the Agent tool — return your result directly. Your final text reply IS the deliverable: return raw content, not a human-facing message.

After the sub-workers return, synthesize their findings into a single deduplicated list before proceeding to step 4.

### 4. Author the issues

Write one issue file per work item under `<repo>/issues/<slug>.md`, following the schema in the `issues` skill. Each issue:

- `status: open`
- `type` — `task` for new implementation, `bug` for drift fixes, `chore` for dead-code or doc cleanup
- `priority` — pick based on the spec's stated invariants (gating behavior → p1, polish → p3)
- `deps: [...]` — wire dependencies (e.g. the integration test issue depends on the implementation issue)
- `## Doc refs` — link to the spec you're materializing: `specs/<stem>.md — driving spec`
- `## Source refs` — link to the code files the issue will touch (best guess if not yet written)

Issue body: prose describing the specific scope, the relevant excerpt from the spec, and what "done" looks like. Don't restate the whole spec — link via `## Doc refs` and quote only the section that scopes this one issue.

**The first implementation issue for a spec must be a tracer bullet** — a minimal end-to-end slice that exercises the spec's primary user flow. Subsequent issues expand from it. Wire `deps:` so the tracer-bullet issue lands first and every other issue for the spec lists it (directly or transitively) as a dependency. This is not optional and not a discovery to make post-hoc; it shapes the first authored issue.

### 5. Self-check

Re-read the spec and the set of issues you just authored. Confirm:

- Every component named in **Architecture** has at least one issue
- Every external system named in **Dependencies** is referenced
- Every failure mode in **Error handling** has either an issue or is already covered by tested behavior in code
- Every testing approach in **Testing** has at least one issue creating a test

If anything is uncovered, add an issue for it. Don't leave gaps that `build` won't find.

### 6. Cross-library final pass

Run this step **once per pipeline run** — not per spec. It is the last iteration of the ralph loop (or a single trailing pass after the per-spec iterations finish). It exists because the per-spec self-check in step 5 only sees one spec's neighborhood; gaps that cross spec boundaries slip past it.

Procedure:

1. Re-read every `approved` spec in `specs/`.
2. Re-read every file in `issues/` (the whole directory, not just what you just wrote).
3. Walk each spec's `## Dependencies` section. For each reference into another spec's behavior, confirm at least one open or closed issue covers the seam. A `refs: [other-spec]` link in spec A that depends on behavior in spec B with no covering issue is a backlog gap; author the issue now.
4. Pay explicit attention to root-level shared docs (`README.md`, top-level `CONTRIBUTING.md`, module-overview docs) that cross spec boundaries. If they have drifted from the union of `approved` specs, author a `chore`-type issue for the doc cleanup.

If sub-workers help here, brief them with the same template as step 3 but scoped to a spec-pair or a shared-doc area rather than a single component.

### 7. Run `issues/ready`

Run `issues/ready` from the project root. It doubles as a doctor (see the `issues` skill) and will surface frontmatter mistakes, orphan deps, or block-form `deps:` lists.

Fix anything `ready` prints to stderr — warnings and errors both — before committing. `ready` exits 0 on warnings (unknown enum values, orphan deps) and exits non-zero on structural errors (broken frontmatter, block-form `deps:`). Treat both as work to do before commit; warnings on freshly authored issues mean you typoed an enum value or wired a dep that doesn't resolve, both of which will hurt `build` later.

### 8. Commit and push

One commit for the batch of new issue files. Use an imperative, sentence-case message naming the spec stem(s) materialized and the issue count, e.g. `Add 7 open issues materializing the auth-flow spec`. Then `git push`. If push fails (no upstream, network, conflict), report and continue — the commit is safe locally.

## Ralph loop

Stop condition: every targeted `approved` spec has been materialized **AND** the cross-library final pass (step 6) has run **OR** the user named one spec and it's done (with step 6 then run as a single trailing pass) **OR** 50 iterations elapsed.

Each iteration is one sequential pass of steps 1–5 and 7–8 against one unwalked target spec, performed by the agent's main loop (you, this turn). Iterations do not run in parallel; the next iteration begins only after the previous iteration's commit lands. Step 6 — the cross-library final pass — runs once at the end of the loop and produces its own commit.

The 50-iteration cap accommodates projects with up to ~50 approved specs queued at once; raise it if your library grows beyond that.

For the single-spec case the per-spec loop runs exactly once and step 6 follows as a single trailing pass.

## What this pipeline does NOT do

- **Does not promote the spec.** Status stays `approved`. Promotion to `implemented` is `build`'s job, after code lands and backpressure passes.
- **Does not touch code.** Issues only.
- **Does not run backpressure.** Nothing to verify yet.

## Style notes for issue authoring

- **One issue per coherent unit of work.** Don't bundle "implement the parser AND write the integration test" into one issue — split, wire `deps`, let `build` walk them in order.
- **Bias toward smaller issues.** If an issue feels like it spans more than a day of focused work, split it. `build` claims one at a time; smaller is faster to verify and easier to rebase.
- **Slug discipline.** Lowercase, hyphenated, unique. Prefix with the spec's domain (`auth-add-oauth-callback`, `billing-refund-edge-case`). The prefix lets `issues/ready <prefix>` filter cleanly.

(The tracer-bullet rule lives in step 4 above — it shapes the first authored issue, not a post-hoc style polish.)

## On completion

Report to the user:

- Which spec(s) were materialized
- How many issues were created per spec (slugs + one-line description each)
- What the cross-library final pass (step 6) added or flagged
- Any gaps you flagged but did not turn into issues (e.g. spec section was ambiguous and needs the user's input)

Do not silently swallow ambiguity. If the spec didn't give you enough to write an issue, ask.
