---
name: audit-specs
description: Running a semantic audit comparing specs at `specs/<stem>.md` against the code they claim. Runs library-wide by default (every spec), scoped to a caller-supplied list of stems (per-batch / per-session-close from `dev`, or per-sub-piece from `changes`'s ripple). Supports an optional `DIFF_CONTEXT` parameter so callers scoping to a recent change get fast targeted verification instead of a full-spec walk. Consult whenever the user says "audit all specs", "audit the spec library", "verify specs against code", "full-coverage spec review", or wants to surface every drift before a release or after a large refactor. Also consult whenever any upstream pipeline (`dev`, `changes`'s ripple sub-step) needs scoped spec verification. For purely structural validation (frontmatter, H2s, refs resolving), use `specs/validate` instead — it is faster and free.
---

# Audit Specs

You are about to run a semantic audit of the project's spec library. By default every spec at `specs/<stem>.md` is compared, in parallel, against the code it claims. When the caller supplies a list of stems (scoped mode), only those specs are audited — this is the shape `dev` invokes for per-batch checks scoped to touched-neighbor specs and for the per-session-close library-wide pass. The output is a drift report sorted by severity, surfaced to the user (or upward to `dev`) for the decision on what to revise. **This is a pure analysis pipeline — no code or spec edits land from this skill.**

## Procedure

### 1. Discover the spec set

Determine the audit scope:

- **Scoped invocation** (caller supplies a stem list, including the `dev`-per-batch case where the list is the union of touched-neighbor specs across the batch): audit exactly those stems. The caller MAY also supply a `DIFF_CONTEXT` parameter (1-3 sentences naming what just changed) — when present, each per-spec worker scopes verification to only claims plausibly affected by that diff; when absent, each worker walks every claim of its assigned spec. `changes`'s ripple sub-step always supplies `DIFF_CONTEXT`; `dev`'s per-batch / per-session-close paths typically omit it.
- **User-supplied stems** (e.g. the user types `audit-specs lsr lsr-app`): audit those stems, no `DIFF_CONTEXT`.
- **No args or `--all`**: audit every `specs/*.md` from the project root (library-wide, the per-session-close case and the default user invocation), no `DIFF_CONTEXT`.

If `specs/` doesn't exist, the project hasn't adopted the spec library. Stop and tell the user.

Run `specs/validate` first as a cheap pre-flight. Errors there block the audit — the structural failures need fixing before a semantic audit is meaningful.

### 2. Fan out one worker per spec

Use the `orchestrate` skill. Spawn one general-purpose worker per stem in parallel. Each worker:

- Reads `specs/<stem>.md`
- Walks the code paths the spec names (Architecture, Dependencies, Testing sections typically point at concrete files under `crates/`, `src/`, etc.; the worker discovers the rest as it reads)
- For each substantive claim, verifies against current code
- Returns a structured drift report

Inline this briefing template in each worker prompt. Substitute three slots per spawn:

- `<STEM>` — the spec stem this worker audits.
- `<PATH_HINT>` — any path hints you derived from reading the spec's Architecture section yourself before spawning (e.g. "the spec names `crates/lsr/src/` — start there"). The hint shortens the worker's discovery phase without constraining it.
- `<DIFF_CONTEXT>` — the consolidation hook for change-time ripple usage. Forward whatever the caller supplied in their invocation (see step 1). When the caller is `changes`'s ripple sub-step (or any other caller that wants to scope verification to a recent diff rather than re-audit the whole spec), this is a 1-3 sentence summary of what just changed and the worker verifies ONLY the claims plausibly affected by that diff. When the caller is the library-wide or per-batch path, leave `<DIFF_CONTEXT>` empty and the worker walks every claim as usual.

```
Goal: Audit `<repo>/specs/<STEM>.md` against the actual code under the project. Report inconsistencies so the caller can decide which specs to revise.

Scope: READ-ONLY. Read the spec, read the codebase. Do NOT edit any files.

Diff context (optional — present only when the caller is scoping to a recent change; omit or empty for a full-spec audit):
<DIFF_CONTEXT>

Procedure:
1. Read the spec file.
2. Walk the relevant code paths the spec names (Architecture section, Dependencies, Testing entry points). Path hint: <PATH_HINT>.
3. For each substantive claim — module/file paths exist, types and signatures match, behaviors implemented, deps listed in Cargo.toml / package.json match, tests entry points exist — verify against code. If `<DIFF_CONTEXT>` is supplied and non-empty, scope verification to ONLY the claims plausibly affected by the diff (touching the same files, the same types, the same behaviors). Pre-existing drift unrelated to the diff is out of scope for this invocation.
4. Do NOT fabricate findings. Only report what you can verify is wrong.

Return format (markdown):

SPEC: <STEM>
DRIFT: <high|medium|low|none>

Findings:
- [HIGH|MED|LOW] <section>: <claim> | reality: <what code shows> | <file:line if applicable>

Summary: <one sentence on overall accuracy>

## New work surfaced
- <one bullet per HIGH-severity finding that warrants a follow-up change> — <one-line description naming the affected file(s) and what would need to change to bring code and spec into alignment>
- ... (omit the bullets and write the literal text "none" under the heading if no HIGH findings, even if MED/LOW findings exist — MED/LOW are surfaced in the drift report only, not as auto-routable work)

If no findings at all, return just:
SPEC: <STEM>
DRIFT: none
Summary: Spec matches code.
## New work surfaced
none

Severity:
- HIGH: factually wrong (file doesn't exist, type renamed, wrong constant value, behavior changed)
- MED: stale (missing recent additions, signature drift)
- LOW: minor wording inaccuracy or unverifiable claim

You are a worker, not an orchestrator. Return text only. Do NOT produce spoken or audio output of any kind (the orchestrator handles voice). Do NOT spawn further workers via the Agent tool. Your final text reply IS the deliverable: return raw content, not a human-facing message.
```

### 3. Synthesize the report

Aggregate the workers' findings into a single table sorted by drift level. For each spec:

- Drift level (high/medium/low/none)
- Top 1–3 findings (collapse the rest by count)
- One-line summary

Highlight HIGH-severity findings prominently and any spec that flips from "none" to anything else since the last audit (if a prior audit log exists). Present to the user (or upward to the caller — e.g. `dev`). **Do not auto-revise.** The decision on revisions lives with the caller; they can hand the findings to `changes` or a per-spec revision pipeline to apply edits.

Also surface a top-level `## New work surfaced` section aggregating every per-spec worker's `## New work surfaced` bullets. Group by stem. If no spec produced HIGH findings, write the literal text `none` under the heading. This is the hook a caller like `dev` uses to auto-route HIGH drift into the changes pipeline (MED/LOW drift stays in the drift-report body for human review).

## When to use

- Before a release
- After a large refactor that touched many crates
- When suspicious that specs and code have diverged
- Periodic maintenance (monthly, post-sprint)

## When NOT to use

- For structural validation — `specs/validate` is faster and free.
- When the spec library is empty or doesn't exist.

