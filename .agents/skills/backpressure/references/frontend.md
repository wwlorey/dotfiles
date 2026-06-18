# Frontend backpressure

For TypeScript / React / Vite projects (root has `package.json`, typically with React, Vite, Tailwind, Vitest, @testing-library/react, Playwright).

## Required gates

| Gate | Command | Notes |
|---|---|---|
| Type check | `pnpm run typecheck` | should run at least `tsc --noEmit`; project may layer more |
| Build | `pnpm run build` | catches type-stripped errors and missing deps |
| Unit tests | `pnpm run test:unit` | Vitest by default |
| Lint | `pnpm run lint` | typically eslint |
| Format | `pnpm run format` | rewrites in place; expect residue |

If a project has a wrapped target (e.g. `pnpm run check` that bundles typecheck + lint + test), use the wrapper instead of running these individually.

## Optional gates

| Gate | Command | When |
|---|---|---|
| Lint with fixes | `pnpm run lint:fix` | iterating, before format |
| Format check | `pnpm run format:check` | CI parity, no rewrite |
| Single unit file | `pnpm run test:unit <path>` | iterating on one failure |
| E2E | `run_playwright` MCP tool | when UI behavior is in scope; see below |
| Storybook build | `pnpm run storybook:build` | when components changed and stories exist |

## E2E tests (Playwright)

Playwright requires Chromium, which is sandbox-blocked. Always use the `mcp__unsandboxed-runner__run_playwright` wrapper, never bare `pnpm exec playwright`.

- All e2e: `run_playwright` with default args
- One file: `run_playwright` with `file: "<path>"` (e.g. `file: "e2e/settings.test.ts"`)

Accepts optional `cwd` (relative to project root) and `timeout_secs` (default 300, max 600).

## Project wrappers

Before running canonical commands, read `package.json` `scripts`. Projects commonly add:
- `pnpm run check` — full backpressure bundle
- `pnpm run ci` — what the CI pipeline runs
- `pnpm run validate` — typecheck + lint + test

Use the project wrapper when present.

## Component stories (Ladle)

Some projects use Ladle for component isolation. Stories live as `*.stories.tsx` next to components.

- Dev: `pnpm run storybook`
- Build (worth running): `pnpm run storybook:build` — catches broken stories

## Gotchas

- **Formatter residue is normal.** Prettier / project formatter may touch files beyond your diff. Commit residue separately.
- **Sandbox blocks Chromium.** Bare `pnpm exec playwright` will fail with permission errors. Always use the MCP wrapper.
- **Workspace projects.** A monorepo with multiple packages may need `-r` (recursive) or a per-package run. Check the root `pnpm-workspace.yaml`.
