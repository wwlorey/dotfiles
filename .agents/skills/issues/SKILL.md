---
name: issues
description: Tracking work items in a per-project markdown backlog — creating, claiming, querying, and closing issues. Consult whenever the task involves an issue, ticket, backlog, work item, bug, TODO, or anything the user calls "what's next", "what's ready", "what's open", "the queue". Also consult when a workflow skill (build, changes, spec) needs to read or update the tracker.
---

# Issues

Issues are markdown files in `<repo>/issues/`, one file per work item. Filename slug IS the ID. Git tracks history; the schema is small enough to grep.

## Layout

```
<repo>/issues/
  fix-login-redirect.md
  auth-add-oauth.md
  billing-refund-edge.md
  ready                        ← helper script (see ./scripts/ready)
```

Flat directory. No subdirectories. Encode logical grouping as a slug prefix: `auth-*`, `billing-*`, etc. The `ready` script takes that prefix as an optional filter.

If `<repo>/issues/` doesn't exist when you start, create it. If `<repo>/issues/ready` doesn't exist, copy it from this skill's `scripts/ready`.

## Issue file format

```markdown
---
status: open
priority: p2
type: task
deps: []
---

# Add OAuth provider for Google sign-in

Users need to sign in with Google. Current flow only supports email/password.

## References

- src/auth/login.ts — current login handler, needs provider dispatch
- docs/auth-flow.md — spec for the OAuth callback contract
```

**Frontmatter — exactly four fields, every issue:**

| Field | Values | Notes |
|---|---|---|
| `status` | `open` \| `in_progress` \| `closed` | underscore, not hyphen |
| `priority` | `p0` \| `p1` \| `p2` \| `p3` | p0 = highest |
| `type` | `bug` \| `task` \| `chore` | |
| `deps` | YAML list of slugs | empty list `[]` if none |

**Body:**
- `# Title` as the first H1.
- Description in prose underneath.
- Optional `## References` section: one bullet per file, format `path — reason`.

That's the whole schema. No other fields. If you find yourself wanting more, push detail into the body instead.

## Slug rules

- Lowercase, hyphen-separated, no extension in the slug itself (the file is `<slug>.md`).
- Unique within the project. If you collide, add a disambiguator (`fix-login-redirect-2.md`) — don't reuse.
- Prefix with a group name if the issue belongs to a logical workstream (`auth-`, `billing-`, `infra-`). The prefix is whatever you want; `ready` filters by string prefix, not a registered enum.

## Operations

| Action | How |
|---|---|
| Create | Write the file. Use the format above. |
| Show | `cat issues/<slug>.md` |
| Claim | Edit frontmatter `status: open` → `in_progress` |
| Close | Edit frontmatter `status: ...` → `closed` |
| Reopen | Edit `status: closed` → `open` |
| Add/remove dep | Edit the `deps:` list |
| Search | `grep -r "<pattern>" issues/` |
| List by status | `grep -l "^status: open$" issues/*.md` |
| Count by status | `grep -c "^status: open$" issues/*.md \| paste -sd+ - \| bc` (or just eyeball) |
| Find what's ready | `issues/ready [prefix]` |
| History of one issue | `git log --follow issues/<slug>.md` |
| Who/when changed it | `git blame issues/<slug>.md` |

Every state transition is an edit + git commit. The commit message IS the close reason / claim note / reopen explanation. Don't track those in frontmatter.

## The `ready` script

`issues/ready` walks every `issues/*.md`, parses frontmatter, and prints slugs that are:

1. `status: open`, AND
2. Every entry in `deps:` resolves to a file with `status: closed`

Sorted by priority (p0 first), then by filename.

Usage:

```
issues/ready              # all ready issues
issues/ready auth         # only slugs starting with "auth-"
```

`ready` doubles as a doctor: it warns on (a) unknown values in the four enum fields, (b) `deps:` entries that don't resolve to an issue file. Warnings go to stderr; the slug list stays on stdout so you can pipe it.

It does NOT detect cycles. At <100 issues per project the cost of manual cycle review on `dep add` is lower than the script complexity. Revisit if you ever build a project where this bites.

## Lifecycle (the path one issue walks)

1. **Create.** Write the file with `status: open`. Add deps if the work depends on other open issues.
2. **Claim.** When you start work, edit `status: open` → `in_progress`. Commit. The commit is your "claimed by" marker.
3. **Work.** Edit code, add commits. If you discover sub-tasks, create more issue files with deps pointing here.
4. **Close.** When done, edit `status: closed`. Commit. The commit message is the close note.
5. **Reopen if needed.** Edit `status: open`. Commit with the reason.

There is no separate "reopened" state — git history shows it was closed and then opened. That's enough.

## When workflow skills use this

A workflow skill (build, changes, spec, cohere) needing to read or update the tracker should:

- Call `issues/ready [spec-prefix]` to get the next-up backlog
- Read individual issues via `cat issues/<slug>.md` or the Read tool
- Update issues via the Edit tool — change a frontmatter line, commit
- Cite this skill rather than restating the schema

