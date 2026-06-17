## Rules

These rules override default behavior. Follow them exactly.

- **Voice output** — end every turn with a brief spoken report. See the `end-of-turn-report` skill for the procedure and format.
- **Prefer MCP wrappers over Bash** — when an `unsandboxed-runner` tool exists for a task, use it. The wrappers bypass sandbox restrictions and handle env loading. Discover them by looking for `mcp__unsandboxed-runner__*` in the session toolset; each wrapper's schema describes its purpose.
- **Surface produced files as `label: <clickable URL>`** — when a task produces a file the user might want to open, list it on its own line as `label: file:///absolute/path/to/file` (local file) or `label: https://…` (remote). One line per file. URL-encode `:` in paths as `%3A` so timestamps in filenames don't break the link. No markdown image embeds, no relative paths, no bare filenames. The label names the artifact (`overlay`, `composite`, `wav`, `icon`).
