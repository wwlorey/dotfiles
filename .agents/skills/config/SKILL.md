---
name: config
description: Updating system configuration of any kind — dotfiles, ~/.agents, skills, MEMENTO.md, or the agent script. Consult before editing any config file, creating or modifying a skill, or changing anything under $HOME that is mirrored in the dotfiles repo, even for one-line tweaks.
---

# Configuration

All system configuration is managed through the dotfiles repository, a mirror
of configuration files, scripts, etc. in `$HOME`. Files there are deployed to
`~/` via `save-config`.

## Editing config files

- **Never edit config files directly in `~/`.** Always make changes in the
  dotfiles repository, then deploy with `save-config`.
- To modify a config (e.g. Neovim, tmux, zsh), find and edit the
  corresponding file in the repo at the same relative path it would have
  under `~/`.
- This applies to `~/.agents/` as well: MEMENTO.md, skills, and the `agent`
  script are configuration. Edit their mirror in the dotfiles repo, never the
  deployed copies.

## Editing skills

- Frontmatter must have `name` and `description`, each on a **single line**
  (the index extractor truncates YAML continuations; the spawn fails loudly
  on missing fields).
- Descriptions state *when to consult*, never the procedure — a description
  that summarizes the workflow causes agents to skip reading the body. Be
  pushy about triggering contexts.
- Open every skill body with imperative instructions, not reference prose.
- Keep bodies under ~500 lines; move detail to `references/`, deterministic
  steps to `scripts/`.
- MEMENTO.md is a map: pointers only, no procedures. Procedures belong in
  skills.
- Never hand-edit generated content (the `## Skills` index is built from
  frontmatter at spawn time; changing frontmatter is the only way to change
  it).

## MCP server (unsandboxed-runner)

- Located at `.claude/mcp-servers/unsandboxed-runner/` in the dotfiles repo.
- Runs via `tsx` directly — no build step. Changes to `src/index.ts` take
  effect on next MCP server restart.

## After any change

1. Verify the edited files **in the repo** (deployed copies are stale until
   `save-config` runs):
   - Skills: confirm frontmatter has single-line `name:` and `description:`
     (`grep -c '^name: .' <file>` and same for description — both must be 1).
   - Scripts: `bash -n <file>`.
2. Sweep for inconsistency. Re-read the edit against itself and the rest
   of the system:
   - Stale references: every backticked command, script, skill name, or
     path resolves to something that exists.
   - Description vs body: triggers in the description still match the
     procedure in the body.
   - Cross-skill drift: claims here don't contradict another skill or
     MEMENTO.md — overlapping advice diverges over time.
   - Renamed or removed things: nothing references work the system no
     longer does.
3. Deploy with `save-config`.
4. Confirm post-deployment: run `agent ls` (catches bad frontmatter in the
   now-deployed copies).
5. Report what changed **and** list every shell command that ran. Format:
   - **Changed:** one-line summary of the substantive edits.
   - **Commands:** every command this session ran that touched the
     system — `save-config`, `agent ls`, deletions (`trash`/`rm`), git ops
     (`git commit`, `git push`), and anything else with side effects.
     One short note per command so the user can audit the deployment chain
     after the fact without re-reading the transcript.
