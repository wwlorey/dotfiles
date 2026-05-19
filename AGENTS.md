# Dotfiles Repository

This repo is a mirror of configuration files, scripts, etc. in `$HOME`. Files here are deployed to `~/` via `save-config`.

## Rules

- After adding a new MCP tool, document its use in `~/Repos/springfield/.sgf/MEMENTO.md`


## When editing config files

- **Never edit config files directly in `~/`.** Always make changes in this repository. The user handles deployment.
- To modify a config (e.g. Neovim, tmux, zsh), find and edit the corresponding file in this repo at the same relative path it would have under `~/`.

## MCP server (unsandboxed-runner)

- Located at `.claude/mcp-servers/unsandboxed-runner/`
- Runs via `tsx` directly — no build step needed. Changes to `src/index.ts` take effect on next MCP server restart.

## Commit workflow

1. commit changes
2. push changes
3. run `save-config`
