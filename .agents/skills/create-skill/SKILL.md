---
name: create-skill
description: Creating a new skill or substantially restructuring an existing one. Consult before adding any skill to ~/.agents/skills, when deciding whether something should be a skill at all, or when writing a skill's frontmatter, body, scripts, or references. For routine edits to existing skills, the config skill is enough; use this when designing a skill's shape.
---

# Skill Authoring

Create skills that prime agents deterministically and load only when relevant.
A skill is a directory under `~/.agents/skills/<name>/` containing a `SKILL.md`,
optionally `scripts/` and `references/`. Editing and deploying skills is
governed by the config skill — follow it; this skill governs their design.

System-wide laws in `~/.agents/LAW.md` apply to every skill. Read them
before authoring. The harness-portability law in particular shapes how a
skill names tools and conditions its body.

## Should it be a skill?

A skill holds **procedure**: how a recurring kind of work is done. It is not
the place for state (that lives in repo files like `tasks/` and `specs/`) or
for a one-off instruction (that is just a prompt). Apply the routing test:
"does this tell an agent *how to do a kind of work*?" → skill. "Is this a
fact, a map, or current state?" → MEMENTO.md or a repo file, not a skill.
One skill, one coherent domain; if a skill spans two unrelated jobs, split it.

## How spawning consumes a skill

Two paths, and the design must serve both:
- **Indexed (ad-hoc spawns):** the `## Skills` block in every memento lists
  each skill's `name` and `description`. The agent reads the body only if the
  description triggers. Here the description does all the work.
- **Injected (keyword spawns):** `agent <name>` cats the whole body in. Here
  the body is the assignment and must read as one.

Write every skill to work under both.

## Frontmatter

- Exactly two fields: `name` and `description`, each on a **single line**
  (the index extractor truncates YAML continuations and the spawn fails loudly
  on a missing field).
- Use only these two fields — no agent-specific extensions — so the skill is
  portable across harnesses.
- `name` matches the directory name.

## Writing the description (the highest-leverage line)

- State **when to consult**, never the procedure. A description that
  summarizes the workflow lets an agent conclude it already knows the steps
  and skip the body. List triggering situations, not methods.
- Be pushy: name the edge cases that cause under-triggering (e.g. "even for
  a one-line change", "even if the discovery seems too small to track").
- Keep it to the trigger; the body holds the how.

## Writing the body

- Open with imperative instructions, not reference prose — under keyword
  spawn the body arrives as the agent's marching orders and a literal reader
  must know to act.
- Keep under ~500 lines. Push detail to `references/` and load on demand;
  push deterministic steps to `scripts/` and call them.
- Prefer scripts over prose for anything an agent shouldn't be trusted to
  re-derive (dependency graphs, validation, parsing). Bundle them in
  `scripts/`; tell the agent to run them rather than reason the logic out.
- State paths relative to the skill dir; the keyword spawn passes the source
  path so relative references resolve.

## Pipeline skills

A pipeline skill is a skill that walks an agent through a multi-step
procedure (claim an issue and implement it, take a change request from
discussion to commit, refine and harden a spec). Pipeline skills are
otherwise ordinary skills — same frontmatter, same directory layout, same
deployment. The conventions below get **inlined into the skill body at
authoring time**, not pulled in by reference at runtime, so each pipeline
skill stays a self-contained prompt artifact.

### When to author a skill as a pipeline

The work spans multiple distinct steps, has an explicit end state, and is
worth re-running by name (the user says "build the next issue" or "make
this change" and expects a known procedure to play out). Single-step or
purely informational work is not a pipeline.

### Ralph loop pattern (only when the pipeline iterates)

Some pipelines loop over a working set (claim the next issue from the
backlog until none remain; harden the spec until it passes the quality
checklist). The pattern, inlined as a `## Ralph loop` section:

- Each iteration spawns one fresh focused worker via the `orchestrate`
  skill (Agent-tool spawn). Fresh context per iteration keeps the worker
  from accumulating drift.
- State the **stop condition** explicitly: what makes the loop end?
  Empty backlog? Checklist all green? Max iterations hit?
- State the **iteration cap** — a hard upper bound to prevent runaway.
  Even if the stop condition is "until done," cap at a sane ceiling.
- After each iteration, the orchestrator (the agent running the pipeline)
  checks the stop condition before spawning the next worker.

Non-iterating pipelines omit the section entirely.

### Backpressure-as-final-step (when the pipeline touches code)

Pipelines that produce code changes end by running full backpressure.
Inline as a final step in the body: "After implementing, consult the
`backpressure` skill and run it for this stack. Do not commit or report
work complete until backpressure passes."

Pipelines that don't touch code (a pure analysis pipeline, a reporting
pipeline) omit this.

### Vocabulary

Do not use vendor-specific or legacy-tool vocabulary in pipeline skill
bodies. Names like `pn`, `fm`, `sgf`, `cursus`, `pensa`, `forma` belong
to the prior generation of tooling and have been replaced. Refer to
`issues`, `specs`, `backpressure`, and the surviving pipeline skills
directly.

### Naming

Flat name, no prefix. The skill name is the verb a user would say
(`build`, `change`, `spec`). Discoverability comes from the description
triggers, not the name.

### Inlining vs referencing

The conventions above are baked into each pipeline skill at create time,
not loaded from this skill at runtime. The author of a new pipeline
copies the relevant patterns (ralph loop section, backpressure-as-final
step, etc.) into the new SKILL.md. This keeps every pipeline skill a
clean standalone artifact with no runtime cross-skill dependency.

## After creating or editing a skill

The skill exists for agents the moment its frontmatter is valid and it is
deployed — no registration step (the index is generated from frontmatter).
Follow the config skill to deploy: verify in the repo, call
`mcp__unsandboxed-runner__save_config`, confirm with `agent ls`. Then run
the cohesion ripple below before reporting done.

## Cohesion ripple

After every skill edit — whether new skill, body rewrite, or one-line
tweak — run a local-first fan-out to verify the edit coheres with the
rest of the library. Skills don't have a formal cross-reference graph the
way specs do; the fan-out uses grep to find the neighborhood.

For each edited skill `<edited>`:

1. **Edited file itself.** Re-read the whole SKILL.md you just changed,
   not only the diff. Confirm the edit reads coherently with the rest of
   the body (vocabulary consistent, sections still in order, no leftover
   references to prior phrasing or renamed tools).
2. **Outgoing neighbors.** Skills the edited body references. Grep:
   `` grep -oE '`[a-z][a-z0-9-]*` skill' ~/.agents/skills/<edited>/SKILL.md ``
   plus any bareword skill mentions you can spot by eye. Verify each
   referenced skill still does what the edit assumes it does.
3. **Incoming neighbors.** Skills that mention the edited one. Grep:
   `` grep -l '<edited>' ~/.agents/skills/*/SKILL.md ``
   For each hit, read the mention in context and verify the edit didn't
   invalidate what the neighbor claims about `<edited>` (procedure
   it points at, output format it expects, vocabulary it assumes).

When the neighborhood is small (≤2 neighbors), inspect inline. When
larger or the edit is non-trivial, use the `orchestrate` skill and spawn
one worker per neighbor. Inline this briefing template; substitute
`<EDITED>`, `<NEIGHBOR>`, and `<DIFF_SUMMARY>` (a few sentences naming
what changed: section moved, term renamed, procedure altered, frontmatter
shape changed).

```
Goal: Determine whether a recent change to `~/.agents/skills/<EDITED>/SKILL.md` invalidates anything `~/.agents/skills/<NEIGHBOR>/SKILL.md` says about it. Report any drift.

Scope: READ-ONLY. Read both files. Do NOT edit either.

The change just landed in `<EDITED>`:
<DIFF_SUMMARY>

Procedure:
1. Read `<NEIGHBOR>/SKILL.md`.
2. Find every mention of `<EDITED>` in the neighbor — by name, by procedure pointer, by vocabulary that came from `<EDITED>`.
3. For each mention, check: does the change in `<EDITED>` still make this mention accurate? Does the neighbor still describe `<EDITED>` correctly?
4. Report ONLY drift caused by this change. Pre-existing drift, ignore.

Return format:

SKILL: <NEIGHBOR>
RIPPLE: <yes|no>
Findings:
- <section or quoted line>: <what the neighbor claims> | reality after the change: <what's now true>
Summary: <one sentence>

If no ripple: SKILL: <NEIGHBOR> / RIPPLE: no / Summary: No ripple from this change.

You are a worker, not an orchestrator. Do NOT produce a spoken end-of-turn report. Do NOT call any TTS / voice / `run_dic` tool. Do NOT spawn further workers via the Agent tool — return your result directly. Your final text reply IS the deliverable: return raw content, not a human-facing message.
```

Apply any drift the ripple surfaced as additional skill edits before
reporting the work done. Re-deploy via `save_config` after the follow-up
edits and re-confirm with `agent ls`.

If the edit was a pure rename (vocabulary substitution across the
library, e.g. one term replaced by another), the ripple's job is to
catch the cases the find-and-replace missed — awkward phrasings ("the X
Y" doublings), references in places the grep didn't reach, and cross-
skill mentions that read incoherently with the new wording.
