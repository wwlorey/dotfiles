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
   - Which guarantees are structural and which are trust assumptions (see "Structural guarantees vs conventions" below)
   - Answers to every open question

   Number your questions and present options as numbered lists so the user can reference items precisely. Push back on ambiguity, surface trade-offs, and present pros/cons when proposing alternatives.

3. **Write or update the spec(s).** Follow the `specs` skill for the schema (five required H2 sections: Overview, Architecture, Dependencies, Error handling, Testing). Use the Edit/Write tools directly on `specs/<stem>.md`. Every spec touched in this phase ends with frontmatter `status: draft`.

4. **Build the absolutes register** for every spec you touched — see "The absolutes register" below. Do this while writing, not afterwards: the register is where an overclaimed sentence gets caught, and the draft is the cheapest place to fix it.

5. **Add cross-references** via the `refs:` frontmatter field for any related specs that this one depends on or interacts with.

6. **Run `specs/validate`** to catch structural problems. Fix anything it errors on.

7. **Commit and push.** Commit message names the spec stem(s) and the substance of the change. Then `git push`. If push fails, report and continue — the commit is safe locally.

### Phase 2: Harden

Use this phase to take a `draft` spec through a quality checklist and either approve it or send it back for more refinement.

1. **Read every `draft` spec** in the project. For each, compare against this checklist:

   - **Structural completeness.** All five required sections have substantive content.
   - **Internal consistency.** No contradictions; terminology used consistently throughout. Take each rule the spec states and re-read *the whole spec* hunting for the passage that breaks it — the dangerous pair is a principle in one section and its own concrete application in another. The shape to catch: §A forbids any ordering rule that compares timestamps, §B builds the staleness precondition on a timestamp comparison. An implementer follows whichever half sits nearer the code. When principle and application conflict, which one survives is a design decision — take it to the user (step 3) rather than settling it with a wording tweak.
   - **Testability.** Frontend AND backend can be end-to-end tested from the CLI. Testing approach is concrete, not aspirational.
   - **Cross-spec coherence.** No conflicts with other specs. Cross-references (`refs:`) are correct and complete in both directions where applicable.
   - **Edge cases and error handling.** Failure modes identified. Error behavior specified.
   - **Dependency clarity.** External dependencies named. Integration points defined. API contracts specified.
   - **Scope boundaries.** Clear in/out of scope. No vague "maybe" features.
   - **Implementability.** A build agent could implement this with no additional context beyond the spec and the code it references.
   - **Security.** No obvious holes or risky patterns. Auth, secrets, untrusted input handled.
   - **KISS.** No premature abstraction or over-engineering.
   - **UI completeness.** Every user flow's necessary UI elements are explicitly defined and connected to backend functionality.
   - **Absolutes register.** Walk the register row by row. For each row, confirm the named mechanism genuinely delivers the claim, and that the violation-attempt test is specified concretely enough for a build agent to write. Then re-run the absolutes grep over the current text and confirm every hit is either a register row or rewritten prose — a claim that escaped the register is the one that ships wrong. Any row without a violation-attempt test blocks approval: weaken the claim or specify the test.
   - **Convention vs structure.** For each absolute, ask what stops a caller who is actively trying to violate it. Where the honest answer is "the code is written not to," rewrite the sentence to name the convention and the trust it assumes.
   - **Impossibility reasoning.** Where the spec declares a failure mode unreachable, make its premise explicit and check what that premise actually quantifies over. The failure to catch: reasoning from a property of *committed* state about a failure that arises from *staged* state — plausible, and wrong. If the premise cannot be shown to cover every case that reaches the code, the spec handles the failure instead of declaring it impossible.
   - **Executable claims.** Run them. Every command, path, filename, config key, and file layout the spec names gets executed or resolved during hardening: invoke the build command and inspect what it produced (a config that sets `noEmit` emits nothing, and a spec documenting that command costs the implementer an afternoon), `ls` the paths, open the config and read the key. Finding a command plausible is not checking it. Names drift.

2. **Fix the obvious problems directly.** Where a spec clearly needs a section expanded, terminology aligned, or a missing cross-reference added, just do it.

3. **Surface the harder questions to the user.** For each non-obvious gap or trade-off:
   - Present the situation with 3 recommendations
   - Pros and cons for each
   - Your recommendation
   - Wait for user input before editing

4. **Update specs based on user input.** Apply the answers; re-run `specs/validate`.

5. **Re-run the checklist.** If everything passes, ask the user: "Are these specs fully hardened?" If yes, promote: edit each affected spec's frontmatter from `status: draft` to `status: approved`. Commit, then `git push` so the promoted specs reach the remote. If push fails, report and continue.

6. **If not yet hardened,** loop back to step 1 and re-walk the checklist. Cap at 25 iterations per session; if not converged by then, stop and report which specs remain at issue.

## The absolutes register

Every spec enumerates its own absolute claims in an `### Absolutes register` subsection at the end of its `## Architecture` section. Build it by grepping the draft for the vocabulary of absolutes:

```
grep -nEi '(cannot|can not|never|always|by construction|structurally|guaranteed|impossible|unreachable|exactly one|only|must not|no [a-z]+ can)' specs/<stem>.md
```

Every hit is either a real absolute — which earns a row — or loose wording, which gets rewritten into what you actually mean. One row per claim, four columns:

| Column | Contents |
|---|---|
| Claim | The sentence, quoted, plus the section it lives in. |
| Kind | `structural` or `convention` — see the next section. |
| Mechanism | The specific thing that enforces it: a type that makes the bad state unrepresentable, a database constraint, a process or privilege boundary, a named runtime check on the far side of that boundary. "The code is written not to" is not a mechanism; it is the definition of `convention`. |
| Violation attempt | The named test that tries to break the claim and asserts the attempt fails — its name and where it lives. |

**A row with no violation-attempt test is not admissible.** Two exits, no third: weaken the sentence until it states only what the mechanism actually delivers, or specify the test concretely enough to implement — its name, its file, and the forbidden action it performs.

The violation-attempt test acts as an adversary holding whatever access a real caller holds: it performs the forbidden operation directly and asserts it is refused. A test that drives the sanctioned path and observes good behavior proves nothing about "cannot." Every test the register names must also be reachable from the spec's `## Testing` section.

### The instrument and the matcher

Any violation attempt that works by *observing* — grepping captured bytes, walking a directory for leaked files, enumerating spawned processes, diffing a tree — has two halves that fail independently:

- the **instrument**, which collects the observations: the network tap, the filesystem walk, the process capture;
- the **matcher**, which decides whether what was collected is bad: the grep, the assertion, the comparison.

**An empty capture and a clean capture are the same bytes.** So a passing assertion over an instrument that collected nothing is indistinguishable from a real defence, and it will stay green forever — through refactors, through the introduction of the exact leak it was written to catch.

Most control arms prove only the matcher, because that is the easy half: seed a known-bad artefact and confirm the assertion fires on it. That establishes the grep works. It says nothing about whether the tap was ever attached to anything.

So every observing row needs **two** arms, and the register should name both:

- *matcher bites* — the assertion fires against a deliberately planted violation;
- *instrument reaches* — the collector demonstrably saw the region where a violation would occur. Assert a floor on what it collected (bytes, files, calls), and place a witness at the far edge of the region it claims to cover rather than somewhere convenient.

Symptoms that the instrument was never proven, worth grepping a suite for: an assertion of `toEqual([])` or `toHaveLength(0)` with no accompanying non-zero floor; a stub or fake that errors on every request, so the code under test aborts before doing the thing being watched; a walk with a file-count or depth cap and no assertion that the cap went unhit; a canary written to whichever directory was easiest rather than the one at risk.

State the scope on the row too. An instrument covers a region, and the row must not claim past it: *"watched `$TMPDIR`, the chart, and `~/Library/Application Support`"* is a defensible claim, where *"the key is never written to disk"* is not, unless the instrument really did watch every disk.

## Structural guarantees vs conventions

Ask of every guarantee in the spec: **what stops a caller who is actively trying to violate it?** Answer for a caller holding what the sanctioned code holds — the same API surface, the same console, the same database handle, the same process.

- **Structural** — something outside the calling code refuses: the bad state is unrepresentable in the type, a constraint rejects the write, the capability is not reachable from that process, a check runs at the boundary the caller must cross.
- **Convention** — the current code happens not to do the forbidden thing. A discipline, an ordering habit, a "we only ever call this from X" arrangement. Real, worth documenting, and breakable by one future edit or one ordinary script.

If the answer is "the code is written not to," it is a convention, and the spec must say so in the sentence itself. The failure to avoid: a spec asserting a boundary "cannot be bypassed" when the true property is "the one file we shipped does not bypass it" — anything else with the same access bypasses it trivially.

Write the honest sentence. An overclaim transfers risk silently to everyone downstream: the implementer builds on a guarantee that isn't there, and QA declines to test what the spec calls impossible. Naming a trust assumption as a trust assumption costs a clause and buys a correct threat model.

Every structural guarantee the register records becomes a target downstream: `dev` fires the `adversarial-verify` gate on the surface it lives on, and the fresh-context adversary is briefed from the register's own words. That is why the register's violation attempt must describe an attack rather than a scenario — it is the test someone will actually run against the shipped code.

## Ralph loop (for the harden phase)

Stop condition: every previously-`draft` spec is now `approved`, **OR** the user says hardening is complete, **OR** 25 iterations elapsed.

Each harden iteration: re-read the draft specs, apply the checklist, present harder questions to the user, edit on their input, validate, commit. Fresh focused effort per iteration; do not carry stale assumptions between iterations.

## Notes

- **No code in this pipeline.** Specs only; no source edits. Code happens in the `build` or `changes` pipelines, against `approved` specs. Running read-only commands to check what a spec claims — the build the spec names, `ls` on a path, opening a config — is part of hardening, not an exception to this.
- **Use Edit/Write directly** on `specs/<stem>.md`. The `specs` skill is the schema, not a wrapper tool.
- **Always run `specs/validate`** before committing to catch structural breakage.
- **No backpressure step.** This pipeline does not touch code, so full backpressure does not apply. The validation here is `specs/validate` plus the harden checklist.
