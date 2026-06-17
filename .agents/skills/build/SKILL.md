---
name: build
description: Claiming the next-ready issue from the project backlog and implementing it end-to-end, one issue at a time, until none remain or a sane cap is reached. Consult whenever the user says "build the next thing", "claim the next issue", "implement from the backlog", "work through ready issues", or asks the agent to run autonomously against the issue tracker. Also consult when an orchestrator pipeline (changes) needs the implementation step for a known-claimed issue.
---

# Build

You are about to claim and implement issues from `<repo>/issues/` one at a time. Each iteration is its own focused worker that picks the top-ready issue, implements it, runs the verification gauntlet, and closes the issue. The loop continues until the backlog is empty or the iteration cap is reached.

This is a pipeline. The conventions below are inlined here, not pulled in by reference.

## Ralph loop

Stop condition: `issues/ready` returns no slugs **OR** you have completed 30 iterations.

Each iteration is one spawned worker via the `orchestrate` skill (Agent-tool spawn). Fresh context per iteration. The worker's briefing covers exactly one issue.

Worker briefing template:

> **Goal.** Implement one issue from the project backlog end-to-end.
>
> **Procedure.**
> 1. Run `issues/ready` to list ready slugs. Take the top one. If the list is empty, stop and report "backlog empty."
> 2. Read the issue at `issues/<slug>.md` to understand scope, source refs, doc refs, and prior comments.
> 3. Claim the issue by editing frontmatter `status: open` → `status: in_progress`. Commit with message `claim <slug>`.
> 4. If the issue's `type` is `bug`, follow the bug-fix flow: reproduce, write a failing test that captures the bug, fix, re-run the test. Otherwise implement per the issue body and any referenced specs.
> 5. Read every spec named in `## Doc refs` via `cat specs/<stem>.md`. Implement against those specs.
> 6. **Update specs alongside code.** If your implementation changes the design described in any spec, update the spec in the same commit as the code. Do not defer with "will update later." See the `specs` skill for the schema; transitions like `approved` → `implemented` happen here when applicable.
> 7. Write tests (unit, property, or integration — pick what fits). No placeholder tests, no `expect(true).toBe(true)`.
> 8. Consult the `backpressure` skill and run the full gauntlet for the project's stack. If anything fails, fix and re-run until clean.
> 9. Close the issue: edit frontmatter `status: in_progress` → `status: closed`. Add a `## Comments` entry summarizing what was done.
> 10. Commit the implementation + spec updates + closure as one logical change (formatter residue may be a separate commit). Then `git push` so the iteration's work reaches the remote before the next iteration starts. If push fails (no upstream, network, conflict), report the failure and continue — the commit is safe locally and a later iteration or human can push it.
>
> **Skills to consult.** `issues` (schema and operations), `specs` (schema and updates), `backpressure` (verification gauntlet), `orchestrate` (you are spawned via it).
>
> **Return format.** A one-paragraph summary: which slug was implemented, what changed, what the backpressure outcome was. If the backlog was empty or you hit a blocker, say so explicitly.
>
> **Inherited rules.** Never reuse a slug. Never claim an issue that's already `in_progress`. Never commit with backpressure failures unaddressed.

After the worker returns, check the stop condition:
- If the worker reported "backlog empty" → stop.
- If you've spawned 30 workers → stop and report the cap was hit.
- Otherwise, spawn the next iteration.

## Refusing to claim already-claimed work

If `issues/ready` somehow returns a slug whose current status is `in_progress`, do not work it — even if the prior `in_progress` was you. Stale claims are a doctor issue (see the `issues` skill for `ready`'s warnings); re-running the loop without resolving the stale claim risks duplicate work or conflicts.

## Style notes for implementation work

- **Tracer bullet first.** Build a tiny end-to-end slice, validate it, then expand. Avoid implementing the whole feature wide before any part of it works narrow.
- **No placeholder code.** Real implementations only.
- **OS defaults.** If the project has build flags that differ by OS (e.g. Metal feature on macOS, CUDA on Linux), ensure the default build still works on the user's OS.
- **Spec drift discovery.** If you discover the existing code already drifts from a spec while implementing your issue, log a separate issue for the drift rather than absorbing it into the current claim. Keep the change focused.

## On completion

When the loop exits (either condition), report to the user:
- How many issues were implemented this run (slugs + one-line summary each)
- Whether the cap was hit or the backlog truly drained
- Any failures left unaddressed (e.g. a backpressure failure on the last iteration that the worker couldn't fix)

Do not silently move on if any iteration left the tree in a bad state.
