#!/bin/bash
# Test suite for block-aichat.py hook.
# Usage: bash .claude/hooks/test-block-aichat.sh
#
# `aichat` is blocked in ANY position (rare string); the `ah` alias is blocked
# only in COMMAND position (common word). Quoted mentions and similarly-named
# tools stay allowed.

set -uo pipefail

HOOK="$(dirname "$0")/block-aichat.py"
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

bj() { printf '{"tool_name":"Bash","tool_input":{"command":"%s"}}' "$1"; }

echo "=== aichat (any position) → deny ==="
run_test "bare aichat"        deny "$(bj 'aichat -m x')"
run_test "pipe into aichat"   deny "$(bj 'foo | aichat')"
run_test "absolute path"      deny "$(bj '/opt/homebrew/bin/aichat')"
run_test "sh -c aichat"       deny "$(bj "bash -lc 'aichat hi'")"
run_test "unquoted mention"   deny "$(bj 'echo aichat')"

echo "=== ah alias (command position) → deny ==="
run_test "bare ah"            deny "$(bj 'ah')"
run_test "&& ah"              deny "$(bj 'x && ah')"

echo "=== mentions / lookalikes → allow ==="
run_test "quoted mention"     allow "$(bj 'echo \"run aichat yourself\"')"
run_test "aichat-notes tool"  allow "$(bj 'aichat-notes list')"
run_test "ah as argument"     allow "$(bj 'grep ah notes.txt')"
run_test "ahead (not ah)"     allow "$(bj 'echo ahead')"

echo "=== Non-Bash tools → allow ==="
run_test "Read ignored"       allow '{"tool_name":"Read","tool_input":{"file_path":"/tmp/x"}}'

echo ""
echo "================================"
echo "Results: $PASS passed, $FAIL failed"
[[ "$FAIL" -eq 0 ]] && echo "All tests passed!" || exit 1
