---
name: specs
description: Tracking design specifications in a per-project markdown library — creating, evolving, validating, and pruning specs. Consult whenever the task involves a spec, design doc, architecture note, RFC, ADR, or anything the user calls "the spec for X", "how X is supposed to work", "design for Y". Also consult when a pipeline (build, change, changes, spec) needs to read or update a spec, when discovering that code drifts from its spec, or when starting design work that should produce a spec before any code.
---

# Specs

Specs are markdown files in `<repo>/specs/`, one file per design unit. Filename stem IS the ID. Git tracks history; the schema is small enough to grep.

## Layout

```
<repo>/specs/
  auth-flow.md
  cookie-handling.md
  billing-refund.md
  validate                     ← helper script (see ./scripts/validate)
```

Flat directory. No subdirectories. Encode logical grouping as a stem prefix: `auth-*`, `billing-*`, etc.

If `<repo>/specs/` doesn't exist when you start, create it. If `<repo>/specs/validate` doesn't exist, copy it from this skill's `scripts/validate`.

## Spec file format

```markdown
---
status: draft
refs: [cookie-handling, billing-flow]
---

# Auth flow

## Overview

What this spec defines, in 1-3 sentences. A reader should know what's in scope after reading this section alone.

## Architecture

The shape of the solution. Components, data flow, key decisions. Diagrams in prose or ASCII if useful.

## Dependencies

Other specs this depends on (named here in prose; cross-link via the `refs:` frontmatter field). External libraries, APIs, services this leans on.

## Error handling

How failure modes are handled. What surfaces to the user. What logs. What retries. What stays inconsistent.

## Testing

How this is verified end-to-end. The CLI invocation or test entry point a build agent would reach for. The shape of the assertions.
```

**Frontmatter — exactly two fields, every spec:**

| Field | Values | Notes |
|---|---|---|
| `status` | `draft` \| `approved` \| `implemented` | see lifecycle below |
| `refs` | YAML list of stems | empty list `[]` if none. inline form: `[a, b]` |

**Body:**
- `# Title` as the first H1.
- Five required H2 sections in this exact order: `## Overview`, `## Architecture`, `## Dependencies`, `## Error handling`, `## Testing`.
- Each section must have substantive content. Empty or placeholder sections cause `validate` to error.

That's the whole schema. No other frontmatter, no other required sections. Add sub-sections (H3 etc.) freely within the required H2s if useful.

## Stem rules

- Lowercase, hyphen-separated, no extension in the stem itself (the file is `<stem>.md`).
- Unique within the project. If you collide, the second spec was probably the same idea — merge, don't disambiguate.
- Prefix with a group name if the spec belongs to a logical area (`auth-`, `billing-`, `infra-`).

## Status lifecycle

| Status | Means | When to advance |
|---|---|---|
| `draft` | being figured out, can change without notice | when the design is settled and you're ready to implement against it |
| `approved` | committed to this design; implementation should match it | once code exists that satisfies the spec end-to-end |
| `implemented` | code now matches the spec | terminal state |

There is no `verified` status. Whether code is *correct* per the spec is a different question (tested, observed, audited) that is not tracked here. If a spec needs to be reopened because the design itself changed, drop back to `draft` and commit with the reason.

## Operations

| Action | How |
|---|---|
| Create | Write the file. Use the format above. |
| Show | `cat specs/<stem>.md` |
| Promote | Edit frontmatter `status` field |
| Add/remove ref | Edit the `refs:` list |
| Search | `grep -r "<pattern>" specs/` |
| List by status | `grep -l "^status: draft$" specs/*.md` |
| Validate the whole library | `specs/validate` |
| History of one spec | `git log --follow specs/<stem>.md` |
| Who/when changed it | `git blame specs/<stem>.md` |

Every state transition is an edit + git commit. The commit message IS the reason for the transition.

## The `validate` script

`specs/validate` walks every `specs/*.md`, parses frontmatter, and reports problems:

1. **Errors** (stderr, exit 1, spec excluded from output): missing/unterminated frontmatter, `refs:` not in inline list form, unknown status value, missing required H2 section, empty required H2 section.
2. **Warnings** (stderr, exit 0): `refs:` entries that don't resolve to an existing spec, cycles in the ref graph.

The stem list of valid specs stays on stdout regardless, so the script is pipe-friendly.

Usage:

```
specs/validate              # validate all specs in the project
specs/validate auth         # only stems starting with "auth-"
```

`validate` runs before each spec-touching commit and as the first step of any spec pipeline. If it errors, fix before continuing.

## Cycle detection

Cycles in the `refs:` graph almost always indicate that two specs are really one spec, or that the dependency direction is wrong. `validate` warns but doesn't error — sometimes you need a temporary cycle while refactoring two specs in tandem. Resolve before merging.

## Cross-link with issues

An issue's `## Doc refs` section can point at `specs/<stem>.md`. No special handling — just the path bullet under the issues skill's `## Doc refs` convention. The reverse direction (a spec naming issues) is not encoded; specs describe the design, not the work backlog.

## When pipelines use this

A pipeline (build, change, changes, spec) needing to read or update specs should:

- Call `specs/validate` to surface structural problems before touching anything
- Read individual specs via `cat specs/<stem>.md` or the Read tool
- Update specs via the Edit tool — change a frontmatter line or a section body, commit
- Cite this skill rather than restating the schema
