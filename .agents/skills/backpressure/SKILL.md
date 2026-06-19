---
name: backpressure
description: Running full backpressure for a project's stack — build, lint, type-check, unit tests, integration tests, format, coverage. Consult before reporting code work complete, before committing, before pushing, before opening a PR, before claiming a feature is ready, and whenever the user asks for a check / verification / lint+test / "is this ready to ship" pass. Also consult as the final step of any procedure that touched code, before the commit lands.
---

# Backpressure

You are about to run full backpressure for the current project. Its purpose is to push back on bad work — formatter residue, lint failures, broken tests, type errors — before the change leaves your hands.

## Procedure

1. **Identify the stack.** Look at the project root for telltale files:
   - `Cargo.toml` → Rust (`references/rust.md`)
   - `package.json` with React / Vite / Tailwind → frontend (`references/frontend.md`)
   - `package.json` plus `src-tauri/` → Tauri (`references/tauri.md`)

   Multiple may apply (a Tauri app has frontend + Rust). Run backpressure for each. If the project's stack is not covered above, name the gap to the user — don't silently improvise.

2. **Read the matching reference file** in this skill's `references/` directory. It lists the canonical commands for that stack, what they do, and which are required vs optional.

3. **Discover the project's actual entry points before running anything.** Commands listed in the references are generic. The project may have wrapped them — e.g. `pnpm run check` that bundles lint+test+typecheck. Look at:
   - `package.json` scripts
   - `justfile` / `Makefile` targets
   - `Cargo.toml` `[workspace.metadata]` aliases
   - The project's `AGENTS.md` / `README.md` for documented dev commands

   If the project has a wrapper, use the wrapper. Otherwise, use the generic commands from the reference.

4. **Run the required gates** for the stack. If any fail, stop and fix before continuing — backpressure has done its job. Report the failure to the user; don't silently move on.

5. **Run the optional gates** when relevant (coverage, integration tests, e2e). Use judgment based on what changed.

6. **Handle formatter residue.** Formatters (`cargo fmt`, `pnpm run format`) reformat files beyond the diff you made. Expected. Commit any formatter residue as a separate formatting-only commit so the substantive change stays reviewable.

## Failure handling

A failing gate is a real failure. Do not:
- Skip a gate because "it's flaky"
- Comment out a test to make backpressure pass
- Report work complete with the failure unmentioned

Do:
- Read the failure
- Fix the underlying issue
- Re-run backpressure until it passes

If a gate is genuinely broken in a way unrelated to your change (a pre-existing failure on the branch), say so explicitly in your report. Don't paper over it.

## Stack reference files

The `references/` directory holds one file per project type. Each lists:
- The required gates (must pass before reporting work complete)
- The optional gates (run when relevant)
- Sandbox / MCP notes (which commands need `unsandboxed-runner` wrappers)
- Stack-specific gotchas

Available references:
- `references/rust.md` — Rust workspace (cargo)
- `references/frontend.md` — TypeScript / React / Vite / Tailwind
- `references/tauri.md` — Tauri desktop apps

## Spec-compliance check

When a code change touches an `implemented`-status spec — either directly editing the spec or modifying code the spec describes — run a spec-compliance check before reporting done. Any `MISSING` finding fails backpressure. This is the structural defense against visually-unimplemented spec items: spec promises a UI element (a control, a label, a section), implementation drops it, no other test catches the gap.

### How to run the check

Read each affected spec at `status: implemented`, drive the surface(s) the spec describes — page, screen, CLI output, TUI panel, or whatever the running app exposes — and report visible promises that don't appear there.

Drive each surface's responsive variants if any (e.g., desktop + mobile for a web page). For surfaces without variants, one drive is enough.

Non-visual specs (library API, server endpoint with no client surface): skip — this check covers visible promises only. For specs that mix visual and non-visual concerns, check only the visible portions.

For each visible thing the spec asserts — a button, control, label, section, layout choice, count, order, sequence — check the running surface. Report gaps as `MISSING: <what the spec says> | observed: <what's actually there>`. Be conservative — don't flag stylistic interpretation differences as MISSING; flag only obvious mismatches.

### Resolution paths when MISSING is found

Decide which is true:

- Implementation is wrong → fix the code in the same commit.
- Spec is stale → fix the spec text in the same commit, and call out the removal in the commit message. Don't silently un-promise content.
- Code is intentionally not there yet → demote the spec from `implemented` to `approved`.

All three resolutions land in the same commit per the specs-alongside-code rule. Don't reflexively change code when the spec is the bug; don't silently delete spec content to pass the check.

### Why this scope

Specs at `status: approved` or `draft` are intentional design-ahead-of-code and are NOT checked. Promoting a spec to `implemented` IS the impl worker's claim that the spec describes shipped reality; backpressure holds them to it. The `audit-specs` skill periodically catches drift that escapes this layer.
