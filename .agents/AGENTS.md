# Global Instructions

- Use MCP tools (e.g. `run_newsboat`, `run_kw`) instead of running those commands directly via Bash. The MCP wrappers exist to bypass sandbox restrictions reliably.
- Use `run_playwright` for all Playwright tests — Chromium can't launch from Bash. Pass `config` for non-default configs (e.g. `playwright-visual.config.ts`).
- Use `create_project` to scaffold new projects (e.g. `pnpm create vite`, `npm create next-app`). Never run scaffold commands via Bash — they are blocked by the sandbox.
- Use `run_pnpm` for allowlisted pnpm scripts that need network access outside the sandbox (e.g. `seed`, `push:schema`, `push:perms`). It loads `.env` from the project root and strips proxy env so Node can reach external APIs directly. To add new scripts, update the `ALLOWED_PNPM_SCRIPTS` set in the unsandboxed-runner source.
