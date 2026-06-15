## Rules

These rules override default behavior. Follow them exactly.

- **Voice output** — end every turn with a brief spoken report. See the `end-of-turn-report` skill for the procedure and format.
- **Prefer MCP wrappers over Bash** — when an `unsandboxed-runner` tool exists for a task, use it. The wrappers bypass sandbox restrictions and handle env loading. Discover them by looking for `mcp__unsandboxed-runner__*` in the session toolset; each wrapper's schema describes its purpose.
