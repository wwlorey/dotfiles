# Global Instructions

- Use MCP tools (e.g. `run_newsboat`, `run_kw`) instead of running those commands directly via Bash. The MCP wrappers exist to bypass sandbox restrictions reliably.
- Use `create_project` to scaffold new projects (e.g. `pnpm create vite`, `npm create next-app`). Never run scaffold commands via Bash — they are blocked by the sandbox.
