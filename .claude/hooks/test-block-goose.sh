#!/bin/bash
# Test suite for block-goose.py hook.
# Usage: bash .claude/hooks/test-block-goose.sh
#
# Covers the command-position matcher: every real invocation form (including
# pipe/&&, `sh -c`, path, and the env/sudo/nohup/VAR=val wrapper prefixes that
# once bypassed it) must deny; mere mentions as arguments must allow.

set -uo pipefail

HOOK="$(dirname "$0")/block-goose.py"
PASS=0
FAIL=0

run_test() {  # description  expected(deny|allow)  json
  local description="$1" expected="$2" json="$3"
  local output actual="allow"
  output=$(echo "$json" | python3 "$HOOK" 2>/dev/null)
  echo "$output" | grep -q '"permissionDecision": "deny"' && actual="deny"
  if [[ "$actual" == "$expected" ]]; then
    echo "  PASS: $description"; ((PASS++))
  else
    echo "  FAIL: $description (expected $expected, got $actual)"; ((FAIL++))
  fi
}

bash_json() { printf '{"tool_name":"Bash","tool_input":{"command":"%s"}}' "$1"; }

echo "=== Real invocations → deny ==="
run_test "bare goose"            deny "$(bash_json 'goose session')"
run_test "pipe into goose"       deny "$(bash_json 'foo | goose run')"
run_test "&& goose"              deny "$(bash_json 'x && goose')"
run_test "sh -c goose"           deny "$(bash_json "bash -lc 'goose run'")"
run_test "absolute path goose"   deny "$(bash_json '/opt/bin/goose run')"
run_test "env VAR=v goose"       deny "$(bash_json 'env X=1 goose run')"
run_test "sudo goose"            deny "$(bash_json 'sudo goose')"
run_test "nohup goose"           deny "$(bash_json 'nohup goose')"
run_test "leading assignment"    deny "$(bash_json 'X=1 goose')"
run_test "command goose"         deny "$(bash_json 'command goose')"
run_test "uv run goose"          deny "$(bash_json 'uv run goose session')"
run_test "npx goose"             deny "$(bash_json 'npx goose run')"
run_test "watch goose"           deny "$(bash_json 'watch goose')"
run_test "poetry run goose"      deny "$(bash_json 'poetry run goose')"
run_test "uv run value-flag"     deny "$(bash_json 'uv run --with foo goose')"
run_test "watch value-flag"      deny "$(bash_json 'watch -n 2 goose')"
run_test "leading redirection"   deny "$(bash_json '>f goose')"
run_test "fd-prefixed redirect"  deny "$(bash_json '2>err goose')"
run_test "fd dup redirect"       deny "$(bash_json '2>&1 goose')"
run_test "command subst \$()"    deny "$(bash_json 'echo $(goose run)')"
run_test "command subst backtick" deny "$(bash_json 'echo `goose run`')"

echo "=== Mentions as arguments → allow ==="
run_test "grep goose"            allow "$(bash_json 'grep goose file.txt')"
run_test "ls a goose dir"        allow "$(bash_json 'ls .config/goose')"
run_test "echo mentioning goose" allow "$(bash_json 'echo run goose yourself')"
run_test "goose-hipaa-check"     allow "$(bash_json 'goose-hipaa-check --list-models')"
run_test "install goose-tool"    allow "$(bash_json 'sudo apt install goose-tool')"
run_test "uv pip install goose"  allow "$(bash_json 'uv pip install goose')"
run_test "redirect to file goose" allow "$(bash_json 'echo hi > goose')"

echo "=== Non-Bash tools → allow ==="
run_test "Read ignored"          allow '{"tool_name":"Read","tool_input":{"file_path":"/tmp/x"}}'

echo ""
echo "================================"
echo "Results: $PASS passed, $FAIL failed"
[[ "$FAIL" -eq 0 ]] && echo "All tests passed!" || exit 1
