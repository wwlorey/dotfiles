---
name: spec-to-issues
description: Materializing an approved spec into the implementation backlog — reading the spec, walking the codebase to find the gap, and authoring `status: open` issues that, once implemented, bring code into alignment with the spec. Consult whenever the user says "spec-to-issues for X", "incarnate this spec", "generate the backlog for Y", "fan out issues from the spec", or has just promoted a spec from draft to approved and now wants the work queued. Also consult when a build run reports "backlog empty" but approved specs exist whose code hasn't been brought into alignment — those specs need incarnating before build can resume.
---

# Spec to issues

You are about to walk one or more `approved` specs and author the open issues needed to bring code into alignment with each spec. The output is a queue of `status: open` issue files in `<repo>/issues/`. This pipeline does **not** touch code — code happens later, when `build` consumes the queue.

This is a pipeline. The conventions below are inlined here, not pulled in by reference.

## Procedure

### 1. Identify the target spec(s)

If the user named a spec, target that one. Otherwise, list every `approved` spec:

```
grep -l "^status: approved$" specs/*.md
```

Ask the user which to incarnate. If they say "all," process them one per ralph-loop iteration (see below).

### 2. Read the spec end-to-end

For the chosen spec, read `specs/<stem>.md` in full. Note:

- **Architecture** — what components exist or must exist
- **Dependencies** — which other specs (and external systems) interact
- **Error handling** — failure modes the implementation must cover
- **Testing** — how the spec says the work is verified end-to-end

Read each spec named in the `refs:` frontmatter for boundary context.

### 3. Walk the codebase against the spec

For each component the spec describes, find the corresponding code. The point is to surface the **gap**: what does the code already do, what does the spec say it should do, where is the delta?

Categorize what you find:

- **Implementation gaps** — code that doesn't exist yet
- **Implementation drift** — code exists but doesn't match the spec (file a `bug`-type issue)
- **Dead code** — code the spec retired or never described (file a `chore`-type issue)
- **Documentation gaps** — README / module docs / inline docs out of sync
- **Testing gaps** — behaviors the spec calls testable that have no test

Use the `orchestrate` skill to spawn workers for parallel walking when the spec is large enough that one focused agent would lose context. Each worker briefing must inline the spec content and the issue schema the worker needs (workers don't see other skills' bodies).

### 4. Author the issues

Write one issue file per work item under `<repo>/issues/<slug>.md`, following the schema in the `issues` skill. Each issue:

- `status: open`
- `type` — `task` for new implementation, `bug` for drift fixes, `chore` for dead-code or doc cleanup
- `priority` — pick based on the spec's stated invariants (gating behavior → p1, polish → p3)
- `deps: [...]` — wire dependencies (e.g. the integration test issue depends on the implementation issue)
- `## Doc refs` — link to the spec you're incarnating: `specs/<stem>.md — driving spec`
- `## Source refs` — link to the code files the issue will touch (best guess if not yet written)

Issue body: prose describing the specific scope, the relevant excerpt from the spec, and what "done" looks like. Don't restate the whole spec — link via `## Doc refs` and quote only the section that scopes this one issue.

### 5. Self-check

Re-read the spec and the set of issues you just authored. Confirm:

- Every component named in **Architecture** has at least one issue
- Every external system named in **Dependencies** is referenced
- Every failure mode in **Error handling** has either an issue or is already covered by tested behavior in code
- Every testing approach in **Testing** has at least one issue creating a test

If anything is uncovered, add an issue for it. Don't leave gaps that `build` won't find.

### 6. Run `issues/ready`

Run `issues/ready` from the project root. It doubles as a doctor (see the `issues` skill) and will surface frontmatter mistakes, orphan deps, or block-form `deps:` lists. Fix anything it errors on before committing.

### 7. Commit and push

One commit for the batch of new issue files. Message names the spec stem(s) incarnated and the issue count, e.g. `spec-to-issues(auth-flow): add 7 open issues`. Then `git push`. If push fails (no upstream, network, conflict), report and continue — the commit is safe locally.

## Ralph loop

Stop condition: every targeted `approved` spec has been incarnated **OR** the user named one spec and it's done **OR** 25 iterations elapsed.

Each iteration picks one unwalked target spec and runs steps 1–7 against it. Spawn one fresh worker per iteration via the `orchestrate` skill so context stays focused. Cap iterations at 25.

For the single-spec case the loop runs exactly once.

## What this pipeline does NOT do

- **Does not promote the spec.** Status stays `approved`. Promotion to `implemented` is `build`'s job, after code lands and backpressure passes.
- **Does not touch code.** Issues only.
- **Does not run backpressure.** Nothing to verify yet.

## Style notes for issue authoring

- **One issue per coherent unit of work.** Don't bundle "implement the parser AND write the integration test" into one issue — split, wire `deps`, let `build` walk them in order.
- **Bias toward smaller issues.** If an issue feels like it spans more than a day of focused work, split it. `build` claims one at a time; smaller is faster to verify and easier to rebase.
- **Tracer bullet first.** The first implementation issue for a spec should produce a minimal end-to-end slice. Subsequent issues expand it. Wire `deps` so the slice lands first.
- **Slug discipline.** Lowercase, hyphenated, unique. Prefix with the spec's domain (`auth-add-oauth-callback`, `billing-refund-edge-case`). The prefix lets `issues/ready <prefix>` filter cleanly.

## On completion

Report to the user:

- Which spec(s) were incarnated
- How many issues were created per spec (slugs + one-line description each)
- Any gaps you flagged but did not turn into issues (e.g. spec section was ambiguous and needs the user's input)

Do not silently swallow ambiguity. If the spec didn't give you enough to write an issue, ask.
