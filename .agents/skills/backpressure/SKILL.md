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
