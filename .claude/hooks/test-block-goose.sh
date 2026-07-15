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

echo "=== Mentions as arguments → allow ==="
run_test "grep goose"            allow "$(bash_json 'grep goose file.txt')"
run_test "ls a goose dir"        allow "$(bash_json 'ls .config/goose')"
run_test "echo mentioning goose" allow "$(bash_json 'echo run goose yourself')"
run_test "goose-hipaa-check"     allow "$(bash_json 'goose-hipaa-check --list-models')"
run_test "install goose-tool"    allow "$(bash_json 'sudo apt install goose-tool')"

echo "=== Non-Bash tools → allow ==="
run_test "Read ignored"          allow '{"tool_name":"Read","tool_input":{"file_path":"/tmp/x"}}'

echo ""
echo "================================"
echo "Results: $PASS passed, $FAIL failed"
[[ "$FAIL" -eq 0 ]] && echo "All tests passed!" || exit 1
