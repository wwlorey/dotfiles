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

### 2. Fan out planning

For each item, spawn one worker via the `orchestrate` skill (Agent-tool spawn). Workers run concurrently. Each worker's briefing must include the full `change` procedure inlined (workers don't see other skills' bodies).

Worker briefing template (paste the body of the `change` skill into the briefing, then add):

> **Goal.** Take this single item through discussion and produce a plan. **Stop before implementing.** Return: (a) the proposed plan, numbered, (b) any clarifying questions for the user, (c) which specs are likely affected.
>
> **Item:** <verbatim from user's list>
>
> **Return format.** Structured: `## Plan`, `## Questions for user`, `## Specs likely affected`. If no questions, omit the section.

When a worker returns:
- Relay any clarifying questions to the user verbatim.
- Once the user responds, send the answers back to the worker via a follow-up spawn so it can refine the plan.
- When the plan is settled, present it to the user for explicit approval before moving the item to `approved`.

### 3. Serialize implementation

Once an item is `approved`, queue it for implementation. **Only one item implements at a time.**

For the next-in-queue approved item, spawn a worker with the full `change` skill body inlined plus:

> **Goal.** Implement the approved plan for this item. Update specs alongside code (do not defer). Run backpressure. Commit. Return a one-paragraph summary of what shipped.
>
> **Item:** <description>
> **Approved plan:** <numbered plan from the planning phase>
>
> **Return format.** `## Summary`, `## Files changed`, `## Specs updated`, `## Backpressure outcome`.

When the worker returns with a commit, mark the item `committed`, then dequeue the next approved item.

### 4. Throughout: communicate the state

After every meaningful event (plan ready for approval, item implementing, item committed, item blocked), give the user a brief status snapshot — which items are at which status. The user is the loop's referee; they need to see progress to direct it.

### 5. On completion

When all items are `committed` or `blocked`:
- Summarize what landed (committed items, one line each).
- Surface any blocked items with the reason.
- Do not silently swallow a blocker.

## Hard rules

- **Never implement two items simultaneously.** Even if they look independent, serialize. Backpressure runs must observe a clean tree.
- **Never send multiple approve-or-resume signals in one turn.** Each implementation worker runs to its commit before the next is unblocked.
- **Always update specs alongside code.** The same rule as `change` — do not defer with an issue.
- **Surface plans before implementing.** Each item must reach explicit user approval before its implementation worker spawns.

## When to push back

If two items in the user's list conflict (one undoes the other, or they touch overlapping code with incompatible designs), surface this immediately. Don't plan both in parallel as if independent. Ask the user to clarify order, priority, or whether one should be dropped.
