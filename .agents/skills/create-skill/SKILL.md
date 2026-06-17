---
name: create-skill
description: Creating a new skill or substantially restructuring an existing one. Consult before adding any skill to ~/.agents/skills, when deciding whether something should be a skill at all, or when writing a skill's frontmatter, body, scripts, or references. For routine edits to existing skills, the config skill is enough; use this when designing a skill's shape.
---

# Skill Authoring

Create skills that prime agents deterministically and load only when relevant.
A skill is a directory under `~/.agents/skills/<name>/` containing a `SKILL.md`,
optionally `scripts/` and `references/`. Editing and deploying skills is
governed by the config skill — follow it; this skill governs their design.

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

## After creating a skill

The skill exists for agents the moment its frontmatter is valid and it is
deployed — no registration step (the index is generated from frontmatter).
Follow the config skill to deploy: verify in the repo, call
`mcp__unsandboxed-runner__save_config`, confirm with `agent ls`. New skill
appears in the listing → done.
