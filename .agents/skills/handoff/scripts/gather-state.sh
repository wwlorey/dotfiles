#!/usr/bin/env bash
# handoff: probe the durable-state surface of a working directory and print a
# factual digest. Best-effort and degrades gracefully — every probe is guarded,
# so a missing tool or directory just prints "(none)" rather than failing. The
# digest is the MAP material for the handoff prompt; it does NOT replace the next
# agent reading the anchors it points at.
#
# Usage: gather-state.sh [dir]   (defaults to the current working directory)

set -uo pipefail
ROOT="${1:-$PWD}"
cd "$ROOT" 2>/dev/null || { echo "handoff-probe: cannot cd to $ROOT"; exit 0; }

section() { printf '\n=== %s ===\n' "$1"; }

section "WORKING DIRECTORY"
echo "$PWD"

# ---- git ----
if command -v git >/dev/null 2>&1 && git rev-parse --git-dir >/dev/null 2>&1; then
  section "GIT"
  echo "branch:   $(git branch --show-current 2>/dev/null || echo '(detached)')"
  echo "HEAD:     $(git rev-parse HEAD 2>/dev/null)"
  up="$(git rev-parse --abbrev-ref --symbolic-full-name '@{u}' 2>/dev/null || true)"
  if [ -n "$up" ]; then
    counts="$(git rev-list --left-right --count "${up}...HEAD" 2>/dev/null || echo '? ?')"
    echo "upstream: $up  (behind ahead = $counts)"
  else
    echo "upstream: (none tracked — commits may be unpushed)"
  fi

  section "GIT — uncommitted / in-flight work"
  if [ -n "$(git status --porcelain 2>/dev/null)" ]; then
    git status --porcelain 2>/dev/null
    echo "^ IN-FLIGHT: uncommitted changes — a worker may have died mid-task. Investigate before handoff."
  else
    echo "(clean working tree)"
  fi

  stashes="$(git stash list 2>/dev/null || true)"
  [ -n "$stashes" ] && { section "GIT — stashes"; echo "$stashes"; }

  section "GIT — recent commits (last 20)"
  git log --oneline -20 2>/dev/null || echo "(no commits yet)"
else
  section "GIT"
  echo "(not a git repository — fall back to files on disk + the session objective)"
fi

# ---- issue / task / spec anchors (adaptive: use whatever is present) ----
section "STATE ANCHORS PRESENT"
found=0

if [ -d issues ]; then
  found=1
  open_ct=$(grep -rl '^status: *open$' issues/*.md 2>/dev/null | wc -l | tr -d ' ')
  inprog_ct=$(grep -rl '^status: *in_progress$' issues/*.md 2>/dev/null | wc -l | tr -d ' ')
  echo "issues/   — ${open_ct:-0} open, ${inprog_ct:-0} in_progress   (the next agent reads these; MAP them, don't copy)"
  grep -rl '^status: *\(open\|in_progress\)$' issues/*.md 2>/dev/null | while IFS= read -r f; do
    s=$(grep -m1 '^status:' "$f" 2>/dev/null | awk '{print $2}')
    p=$(grep -m1 '^priority:' "$f" 2>/dev/null | awk '{print $2}')
    printf '   [%s%s] %s\n' "$s" "${p:+ $p}" "$(basename "$f" .md)"
  done
fi
[ -d specs ]    && { found=1; echo "specs/    — $(ls specs/*.md 2>/dev/null | wc -l | tr -d ' ') spec(s)   (design source of truth)"; }
[ -d plans ]    && { found=1; echo "plans/    — present"; }
[ -d docs/adr ] && { found=1; echo "docs/adr/ — present"; }
for f in TODO.md TODO TASKS.md ROADMAP.md HANDOFF.md CLAUDE.md AGENTS.md; do
  [ -f "$f" ] && { found=1; echo "$f — present"; }
done
[ "$found" = 0 ] && echo "(no issues/ specs/ plans/ TODO — a bare working dir; use the files on disk + the session objective)"

# ---- github (optional) ----
if command -v gh >/dev/null 2>&1 && git rev-parse --git-dir >/dev/null 2>&1; then
  prs="$(gh pr list --limit 10 2>/dev/null || true)"
  [ -n "$prs" ] && { section "GITHUB — open PRs (gh)"; echo "$prs"; }
fi

section "PROBE COMPLETE"
cat <<'EOF'
This digest is the MAP. The next agent reads the anchors above itself — the
handoff prompt POINTS at them, it does not re-summarize them. Spend the prompt's
words on the EPHEMERAL: the in-conversation decisions, constraints, and pending
tasks that live nowhere but the chat and evaporate on compaction.
EOF
