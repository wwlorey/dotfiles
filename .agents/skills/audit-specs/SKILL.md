---
name: audit-specs
description: Running a full-library semantic audit comparing every spec at `specs/<stem>.md` against the code it claims. Consult whenever the user says "audit all specs", "audit the spec library", "verify specs against code", "full-coverage spec review", or wants to surface every drift before a release or after a large refactor. For change-time targeted verification (just the specs the current change touched), use the ripple step inside the `changes` skill — do not call this skill from inside `changes`. For purely structural validation (frontmatter, H2s, refs resolving), use `specs/validate` instead — it is faster and free.
---

# Audit Specs

You are about to run the full-library semantic audit. Every spec at `specs/<stem>.md` is compared, in parallel, against the code it claims. The output is a drift report sorted by severity, surfaced to the user for them to decide what to revise. **This is a pure analysis pipeline — no code or spec edits land from this skill.**

## Procedure

### 1. Discover the spec set

List every `specs/*.md` from the project root. If the user supplied stems (e.g. `audit-specs lsr lsr-app`), audit only those. With no args or `--all`, audit every spec.

If `specs/` doesn't exist, the project hasn't adopted the spec library. Stop and tell the user.

Run `specs/validate` first as a cheap pre-flight. Errors there block the audit — the structural failures need fixing before a semantic audit is meaningful.

### 2. Fan out one worker per spec

Use the `orchestrate` skill. Spawn one general-purpose worker per stem in parallel. Each worker:

- Reads `specs/<stem>.md`
- Walks the code paths the spec names (Architecture, Dependencies, Testing sections typically point at concrete files under `crates/`, `src/`, etc.; the worker discovers the rest as it reads)
- For each substantive claim, verifies against current code
- Returns a structured drift report

Inline this briefing template in each worker prompt. Substitute `<STEM>` and any path hints you derived from reading the spec's Architecture section yourself before spawning (e.g. "the spec names `crates/lsr/src/` — start there"). The hint shortens the worker's discovery phase without constraining it.

```
Goal: Audit `<repo>/specs/<STEM>.md` against the actual code under the project. Report inconsistencies so the user can decide which specs to revise.

Scope: READ-ONLY. Read the spec, read the codebase. Do NOT edit any files.

Procedure:
1. Read the spec file.
2. Walk the relevant code paths the spec names (Architecture section, Dependencies, Testing entry points). Path hint: <PATH_HINT>.
3. For each substantive claim — module/file paths exist, types and signatures match, behaviors implemented, deps listed in Cargo.toml / package.json match, tests entry points exist — verify against code.
4. Do NOT fabricate findings. Only report what you can verify is wrong.

Return format (markdown):

SPEC: <STEM>
DRIFT: <high|medium|low|none>

Findings:
- [HIGH|MED|LOW] <section>: <claim> | reality: <what code shows> | <file:line if applicable>

Summary: <one sentence on overall accuracy>

If no findings, return just:
SPEC: <STEM>
DRIFT: none
Summary: Spec matches code.

Severity:
- HIGH: factually wrong (file doesn't exist, type renamed, wrong constant value, behavior changed)
- MED: stale (missing recent additions, signature drift)
- LOW: minor wording inaccuracy or unverifiable claim

You are a worker, not an orchestrator. Do NOT produce a spoken end-of-turn report. Do NOT call any TTS / voice / `run_dic` tool. Do NOT spawn further workers via the Agent tool — return your result directly. Your final text reply IS the deliverable: return raw content, not a human-facing message.
```

### 3. Synthesize the report

Aggregate the workers' findings into a single table sorted by drift level. For each spec:

- Drift level (high/medium/low/none)
- Top 1–3 findings (collapse the rest by count)
- One-line summary

Highlight HIGH-severity findings prominently and any spec that flips from "none" to anything else since the last audit (if a prior audit log exists). Present to the user. **Do not auto-revise.** The user decides which specs to revise; they can hand the findings to `changes` or a per-spec revision pipeline to apply edits.

## When to use

- Before a release
- After a large refactor that touched many crates
- When suspicious that specs and code have diverged
- Periodic maintenance (monthly, post-sprint)

## When NOT to use

- During a single `changes` run — the changes skill's implementation step has a ripple sub-step that scopes verification to the affected neighborhood per sub-piece
- For structural validation — `specs/validate` is faster and free
- When the spec library is empty or doesn't exist
