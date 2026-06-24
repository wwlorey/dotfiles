#!/usr/bin/env bash
# Regression tests for redirect-bash-config-writes.py.
#
# Run from this directory or with the absolute path. Exits non-zero if any
# case behaves unexpectedly. The `cwd` in each payload is the dotfiles repo so
# relative path tokens (e.g. .claude/settings.json) resolve like a real run.

set -euo pipefail

HOOK="$(cd "$(dirname "$0")" && pwd)/redirect-bash-config-writes.py"
CWD="$HOME/Repos/dotfiles"

fail=0

check() {
  local expected="$1"; shift
  local cmd="$1"; shift
  local result
  result=$(printf '{"tool_name":"Bash","cwd":%s,"tool_input":{"command":%s}}' \
    "$(printf '%s' "$CWD" | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))')" \
    "$(printf '%s' "$cmd" | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))')" \
    | python3 "$HOOK" 2>&1)
  local actual="ALLOW"
  if [[ -n "$result" ]]; then actual="DENY"; fi
  if [[ "$actual" == "$expected" ]]; then
    printf '  OK  | %s | %s\n' "$expected" "$cmd"
  else
    printf 'FAIL  | want=%s got=%s | %s\n' "$expected" "$actual" "$cmd"
    fail=1
  fi
}

# --- Idiom writes targeting managed config: DENY ---
check DENY "echo x >> .claude/settings.json"
check DENY "echo '{}' > ~/.claude/settings.json"
check DENY "cat foo > .claude/settings.local.json"
check DENY "sed -i '' s/a/b/ .claude/hooks/foo.py"
check DENY "sed -i s/a/b/ ~/.claude/hooks/foo.py"
check DENY "cp /tmp/new .agents/skills/x/SKILL.md"
check DENY "mv /tmp/x ~/.agents/MEMENTO.md"
check DENY "tee .claude/commands/foo.md < /tmp/x"
check DENY "dd of=.claude/mcp-servers/x conv=notrunc"
check DENY "truncate -s 0 .claude/statusline.sh"
# absolute repo path
check DENY "echo x > $HOME/Repos/dotfiles/.claude/settings.json"

# --- Interpreter writes touching managed config: DENY ---
check DENY "python3 - <<'PY'
open('.claude/settings.json','w').write('x')
PY"
check DENY "python3 -c \"open('.claude/settings.json','w')\""
check DENY "python3 edit.py ~/.claude/settings.json"
check DENY "node script.js .agents/skills/x/SKILL.md"
check DENY "ruby -e \"File.write('.claude/hooks/foo.py','x')\""

# --- Reads of managed config (no managed write target): ALLOW ---
check ALLOW "cat ~/.claude/settings.json"
check ALLOW "grep token .claude/hooks/foo.py"
check ALLOW "cat .claude/settings.json > /tmp/x"
check ALLOW "diff .claude/settings.json /tmp/other"
check ALLOW "jq . ~/.claude/settings.json"

# --- Writes to unmanaged paths: ALLOW ---
check ALLOW "echo x > /tmp/scratch"
check ALLOW "echo x >> ~/notes.txt"
check ALLOW "sed -i '' s/a/b/ README.md"
check ALLOW "cp /tmp/a /tmp/b"
check ALLOW "python3 build.py /tmp/out.json"
# A managed-looking name outside the managed tree (Repos/other) is fine.
check ALLOW "echo x > $HOME/Repos/other/.claude/settings.json"

# --- Innocent mentions: ALLOW ---
check ALLOW "echo 'edit .claude/settings.json by hand'"
check ALLOW "git commit -m 'update .agents/ skills'"
check ALLOW "ls .claude/hooks/"

if [[ $fail -ne 0 ]]; then
  echo
  echo "FAIL: at least one case behaved unexpectedly"
  exit 1
fi

echo
echo "PASS: all cases behaved as expected"
