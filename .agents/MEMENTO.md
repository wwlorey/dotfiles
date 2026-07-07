## Law

Non-negotiable rules live in `~/.agents/LAW.md`. Read it before authoring
any new skill, script, hook, or prompt.

## Rules

These rules override default behavior. Follow them exactly.

- **Voice output** — a brief spoken update accompanies every hand-back to the user. End-of-turn speech is automatic: end the turn with one self-contained final message (no trailing tool calls) whose literal last line is `Summary: <Dirname>. <phrase>.`; a Stop hook strips the label and speaks the rest after the final text renders. Before any mid-turn pause that waits on user input (AskUserQuestion, plan approval, etc.), speak an alert directly. See the `end-of-turn-report` skill for the procedure and format.
- **Prefer MCP wrappers over Bash** — when an `unsandboxed-runner` tool exists for a task, use it. The wrappers bypass sandbox restrictions and handle env loading. Discover them by looking for `mcp__unsandboxed-runner__*` in the session toolset; each wrapper's schema describes its purpose.
- **Surface produced files as `label: <clickable URL>`** — when a task produces a file the user might want to open, list it on its own line as `label: file:///absolute/path/to/file` (local file) or `label: https://…` (remote). One line per file. URL-encode `:` in paths as `%3A` so timestamps in filenames don't break the link. No markdown image embeds, no relative paths, no bare filenames. The label names the artifact (`overlay`, `composite`, `wav`, `icon`).
- **Post-commit push prompt** — after every commit, check `git remote` and, if any remote is configured, ask the user "Push to origin?" rather than waiting for them to bring it up. Skip the prompt entirely when no remote exists (local-only repo). Do not push without an explicit yes. Exception: skills or pipelines that script the push as part of their procedure (e.g. `build`'s iteration-end push) override this rule for the commits they make.
