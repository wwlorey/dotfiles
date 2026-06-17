---
name: change
description: Taking a single user-described change request — add a feature, fix a bug, modify behavior — from initial discussion through planning, implementation, spec updates, verification, and commit. Consult whenever the user says "I want to add/change/fix X", describes a single piece of work conversationally, or asks for a focused code change with discussion. For multiple change items the user wants run in parallel, use the changes skill instead.
---

# Change

You are about to walk one user-described change request through its full lifecycle: discuss, plan, get explicit plan approval, implement, update specs alongside, verify via backpressure, log a tracking issue, commit. This is a conversational pipeline — it pauses for user input at the plan-approval checkpoint and is allowed to ask clarifying questions throughout.

This is a pipeline. The conventions below are inlined here, not pulled in by reference.

## Procedure

### 1. Discuss

Interview the user about what they want. Ask only questions you can't answer yourself by reading code or specs. As the user describes functionality, read the related specs (the `specs` skill governs the schema; spec files live at `<repo>/specs/<stem>.md`).

Come away from the discussion with:
- The behavior change in concrete terms
- Edge cases and failure modes
- Error-handling expectations
- Scope boundaries — what's in, what's out
- Integration points and dependencies
- How to test end-to-end (CLI invocation, UI flow, or both)
- All required UI components if there's a frontend surface — surface implicit components explicitly

### 2. Plan

Present a change plan. **HARD STOP: present the plan and wait for explicit user approval before writing any code.** Even if the user's message contained a detailed plan, present it back for confirmation. Never auto-implement.

Number each item in the plan so the user can reference specific points. If you have alternatives or trade-offs, present 3 options with pros and cons and your recommendation.

### 3. Implement (after approval)

Once the user approves the plan:

- Write the code per the plan.
- Use the `orchestrate` skill to spawn workers for parallel parts of the work (e.g. distinct files / modules / test suites). Each worker briefing must be self-contained — workers do not see this skill's body.
- Write tests (unit, property-based, or integration — whichever fits).

### 4. Update specs alongside code

**Specs are updated in the same commit as code, not deferred.** Do not log an issue saying "circle back to update the specs." If your change affects a spec, update it now.

For each spec affected:
- Read it at `specs/<stem>.md`.
- Verify each claim in the spec against the new code.
- Update the spec body to match the new behavior. If you're rewriting more than half a section, rewrite the whole section so it reads coherently.
- If the spec was `approved` and code now matches it, set frontmatter `status: implemented`. If the spec was `implemented` and the change is a non-trivial design shift, drop back to `draft` and re-shape it.
- Run `specs/validate` to catch any structural problems you introduced.

If no specs are affected, skip this step — but be honest about whether one *should* be affected. A surface-level "no specs touched" answer when the change crosses a documented boundary is wrong.

### 5. Run backpressure

Consult the `backpressure` skill and run the full gauntlet for the project's stack. Fix every failure before continuing.

### 6. Log the tracking issue

Create an issue in `<repo>/issues/` capturing:
- What was changed (impetus + the actual diff)
- What design decisions were made
- Which specs were updated
- Link the issue's `## Source refs` to the files touched, `## Doc refs` to the updated specs

Set the new issue's `status: closed` immediately. This issue is the changelog entry for the change, not a piece of pending work.

### 7. Commit and push

One commit for the substantive change (code + specs + issue). One separate commit for formatter residue if any. Commit message references the issue slug. Then `git push` so the change reaches the remote. If push fails (no upstream, network, conflict), report the failure to the user and continue — the commits are safe locally.

## When to push back

Discussion is not stenography. If the user's described change has obvious problems — incompatible with existing specs, breaks edge cases, introduces a security hole — surface them in the discussion phase. Don't carry a known-bad design into the plan.

## When to spawn workers

Most changes are too small to spawn for. Spawn workers when:
- The work splits into N independent file-scoped chunks
- A second perspective is genuinely useful (adversarial review of the plan before implementation)
- The change touches enough code that one focused worker would lose context

Follow the `orchestrate` skill's briefing rules. Workers do not see this skill, so any of this body that the worker needs must be inlined into the briefing.
