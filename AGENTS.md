# Dotfiles Repository

This repo is a mirror of configuration files, scripts, etc. in `$HOME`. Files here are deployed to `~/` via `save-config`.

## Rules

- **Never edit config files directly in `~/`.** Always make changes in this repository. The user handles deployment.
- To modify a config (e.g. Neovim, tmux, zsh), find and edit the corresponding file in this repo at the same relative path it would have under `~/`.
- New config files should be placed in this repo at the path where they belong under `~/`.
- Do not run `save-config` — the user will deploy changes themselves.
