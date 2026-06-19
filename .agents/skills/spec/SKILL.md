---
name: spec
description: Creating a new spec from a discussion, refining an existing draft spec, or hardening a draft into an approved spec via a quality checklist. Consult whenever the user says "let's spec this out", "write a spec for X", "harden the spec", "the spec for Y needs work", or is in design-discussion territory that should produce a written spec before any code. For reading or applying existing specs from code-implementation work, use the specs skill directly without this pipeline.
---

# Spec

You are about to walk one or more specs from idea through `draft` to `approved`. The pipeline has two phases that may run on the same spec across separate sessions: a conversational **refine and create** phase, and an iterative **harden** phase.

This is a pipeline. The conventions below are inlined here, not pulled in by reference.

## Procedure

### Phase 1: Refine and create

Use this phase when starting a new spec, or substantially restructuring an existing one.

1. **Interview the user** about what they want to build. Ask only questions you can't answer yourself by reading existing specs and code. As topics come up, read the related specs (`specs/<stem>.md`) for context.

2. **Drive to closure on the design.** The conversation should not end until you have all of the following:
   - Edge cases and failure modes
   - Error-handling behavior
   - Interactions with existing specs and code
   - Scope boundaries — what's in, what's out
   - Dependencies and integration points
   - How the change will be tested end-to-end from the CLI (frontend and backend)
   - All required UI components, with implicit components made explicit
   - User flows defined and testable
   - Answers to every open question

   Number your questions and present options as numbered lists so the user can reference items precisely. Push back on ambiguity, surface trade-offs, and present pros/cons when proposing alternatives.

3. **Write or update the spec(s).** Follow the `specs` skill for the schema (five required H2 sections: Overview, Architecture, Dependencies, Error handling, Testing). Use the Edit/Write tools directly on `specs/<stem>.md`. Every spec touched in this phase ends with frontmatter `status: draft`.

4. **Add cross-references** via the `refs:` frontmatter field for any related specs that this one depends on or interacts with.

5. **Run `specs/validate`** to catch structural problems. Fix anything it errors on.

6. **Commit and push.** Commit message names the spec stem(s) and the substance of the change. Then `git push`. If push fails, report and continue — the commit is safe locally.

### Phase 2: Harden

Use this phase to take a `draft` spec through a quality checklist and either approve it or send it back for more refinement.

1. **Read every `draft` spec** in the project. For each, compare against this checklist:

   - **Structural completeness.** All five required sections have substantive content.
   - **Internal consistency.** No contradictions. Terminology used consistently throughout.
   - **Testability.** Frontend AND backend can be end-to-end tested from the CLI. Testing approach is concrete, not aspirational.
   - **Cross-spec coherence.** No conflicts with other specs. Cross-references (`refs:`) are correct and complete in both directions where applicable.
   - **Edge cases and error handling.** Failure modes identified. Error behavior specified.
   - **Dependency clarity.** External dependencies named. Integration points defined. API contracts specified.
   - **Scope boundaries.** Clear in/out of scope. No vague "maybe" features.
   - **Implementability.** A build agent could implement this with no additional context beyond the spec and the code it references.
   - **Security.** No obvious holes or risky patterns. Auth, secrets, untrusted input handled.
   - **KISS.** No premature abstraction or over-engineering.
   - **UI completeness.** Every user flow's necessary UI elements are explicitly defined and connected to backend functionality.

2. **Fix the obvious problems directly.** Where a spec clearly needs a section expanded, terminology aligned, or a missing cross-reference added, just do it.

3. **Surface the harder questions to the user.** For each non-obvious gap or trade-off:
   - Present the situation with 3 recommendations
   - Pros and cons for each
   - Your recommendation
   - Wait for user input before editing

4. **Update specs based on user input.** Apply the answers; re-run `specs/validate`.

5. **Re-run the checklist.** If everything passes, ask the user: "Are these specs fully hardened?" If yes, promote: edit each affected spec's frontmatter from `status: draft` to `status: approved`. Commit, then `git push` so the promoted specs reach the remote. If push fails, report and continue.

6. **If not yet hardened,** loop back to step 1 and re-walk the checklist. Cap at 25 iterations per session; if not converged by then, stop and report which specs remain at issue.

## Ralph loop (for the harden phase)

Stop condition: every previously-`draft` spec is now `approved`, **OR** the user says hardening is complete, **OR** 25 iterations elapsed.

Each harden iteration: re-read the draft specs, apply the checklist, present harder questions to the user, edit on their input, validate, commit. Fresh focused effort per iteration; do not carry stale assumptions between iterations.

## Notes

- **No code in this pipeline.** Specs only. Code happens in the `build` or `changes` pipelines, against `approved` specs.
- **Use Edit/Write directly** on `specs/<stem>.md`. The `specs` skill is the schema, not a wrapper tool.
- **Always run `specs/validate`** before committing to catch structural breakage.
- **No backpressure step.** This pipeline does not touch code, so full backpressure does not apply. The validation here is `specs/validate` plus the harden checklist.
