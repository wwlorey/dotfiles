---
name: config
description: Working with system configuration of any kind — dotfiles, ~/.agents, skills, MEMENTO.md, or the agent script. Consult before editing any config file, creating or modifying a skill, changing anything under $HOME mirrored in the dotfiles repo, or even just brainstorming options for such a change — even for one-line tweaks.
---

# Configuration

All system configuration is managed through the dotfiles repository, a mirror
of configuration files, scripts, etc. in `$HOME`. Files there are deployed to
`~/` via the `save-config` script — invoke it through the
`mcp__unsandboxed-runner__save_config` MCP wrapper so rsync can write into
`$HOME` from within the sandbox. A PreToolUse hook denies bare `save-config`
in Bash with the same pointer.

## Security-enforcing config is high-risk — not ordinary config

A change is **security-enforcing** if it is a gate, hook, wrapper, or checker
that upholds a security or compliance invariant — anything touching PHI,
secrets, credentials, network egress, at-rest storage, auth, or sandboxing
(e.g. the `*-hipaa-check` scripts, the `aichat`/`goose` gates, the `block-*`
hooks). The routine wrap-up below (syntax + `agent ls`) is NOT sufficient for
these. Treat them as high-risk code and clear ALL of the following before
saying "done" — never on the strength of reading the code or testing pieces in
isolation:

1. **Execute the composed artifact end-to-end.** Run the real thing against
   adversarial inputs — not `python3 <checker>` (that bypasses the executable
   bit the gate relies on), not a stub function that omits the file's own
   globals. Drive the actual function/hook through every guard path AND the
   happy path. Bugs in a security control live in the seam between components
   and the runtime — a missing `+x`, a variable whose name trips its own
   filter — and only running the whole thing surfaces them. A read-only
   reasoning pass is structurally blind to these.
2. **Keep a committed test that does #1.** Co-locate a `test-<name>` script
   next to the artifact (the repo convention — see `.claude/hooks/test-*` and
   `.zsh/test-*-gate.zsh`), and re-run it after EVERY change to that artifact,
   including fixes — a fix can introduce a fresh regression, so re-verify with
   the full suite, not the same narrow check that already passed. "Verified" is
   unsayable without a green run of this test.
3. **Get an independent security-review.** The author's eyes rationalize the
   author's blind spots. Invoke the `security-review` command, or spawn a
   fresh-context reviewer that never saw the implementation — do not self-audit
   and call it audited.

State in the report that these ran and passed. If one genuinely could not run
(e.g. the artifact needs a binary or credential unavailable in the run
environment), say so plainly and describe the change as "unverified in field,"
never as "verified."

## Editing config files

- **Never edit config files directly in `~/`.** Always make changes in the
  dotfiles repository, then deploy with `mcp__unsandboxed-runner__save_config`.
- To modify a config (e.g. Neovim, tmux, zsh), find and edit the
  corresponding file in the repo at the same relative path it would have
  under `~/`.
- This applies to `~/.agents/` as well: MEMENTO.md, skills, and the `agent`
  script are configuration. Edit their mirror in the dotfiles repo, never the
  deployed copies.
- A PreToolUse hook at `.claude/hooks/redirect-config-edits.py` enforces
  this — Edit/Write on a deployed copy is denied with a pointer to the
  canonical source. If you add a **new fully-managed top-level dir** to the
  dotfiles repo (one where every legitimate child should live in the repo),
  also add its repo-relative prefix to `MIRRORED_PREFIXES` in that hook so
  brand-new files inside it are caught before the first save-config.
  Selectively-managed parents (like `.claude/`, which contains both mirrored
  config and runtime state) are NOT prefixes — they fall back to exact-file
  match only.
- **Mutate config with the Edit/Write tools, never from Bash.** A shell write
  — `>`/`>>` redirect, `tee`, `sed -i`, `cp`/`mv` into the file, a `python3`
  heredoc that opens it — bypasses the redirect hook above *and* trips the
  sandbox's write-deny on these paths, producing a confusing failure instead
  of an edit. Make the change in the repo source with Edit/Write, then deploy.
  A PreToolUse hook at `.claude/hooks/redirect-bash-config-writes.py` denies
  such Bash writes to managed paths with this same pointer; to READ a config
  via Bash is fine, but prefer the Read tool. When you add a new fully-managed
  prefix, mirror it into that hook's `MANAGED_PREFIXES` too (it keeps its own
  list, independent of the Edit-side hook).

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

## Writing prompts

These rules apply to anything that becomes a prompt an agent will read —
skills, MEMENTO.md, CLAUDE.md, slash commands.

- **Each version reads as if it were the first.** Don't reference prior
  tools or earlier wording ("replaces X", "what Y called", "no longer
  does Z"). When iterating, rewrite the affected passage cleanly rather
  than layering negations or parenthetical exclusions on top of the old
  text. The prompt describes its current desired state, not its history.

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
   - Co-dependents: if the edit changes behavior — a function, a loop,
     an output format, a shared file — grep the script *and the wider
     repo* for other code that calls it, iterates the same source, or
     parses the same output. Confirm each still holds. For behavior
     described in docs (README, CLAUDE.md, skill bodies), re-read those
     too.
3. Deploy with `mcp__unsandboxed-runner__save_config`.
4. Confirm post-deployment: run `agent ls` (catches bad frontmatter in the
   now-deployed copies).
5. For skill edits specifically — including routine tweaks — also run the
   ripple check from the `create-skill` skill's "Ripple check" section.
   The ripple is a local-first fan-out: re-read the edited skill, then
   check neighbors that reference it (or that it references) for drift.
   Apply any drift surfaced as follow-up edits before reporting done.
5. Report under a `**Config changes:**` header as a brief bullet list,
   one bullet per wrap-up step that ran. Each bullet is one of these
   strings copied verbatim: `deployed`, `audited`, `committed`, `pushed`.
