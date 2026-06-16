#!/bin/bash
# Test suite for block-force-push.py hook
# Usage: bash .claude/hooks/test-block-force-push.sh

set -uo pipefail

HOOK="$(dirname "$0")/block-force-push.py"
PASS=0
FAIL=0

# expected: "deny" | "allow"
run_test() {
  local description="$1"
  local expected="$2"
  local json="$3"
  local env_prefix="${4:-}"

  local output
  output=$(echo "$json" | env -u ALLOW_FORCE_PUSH $env_prefix python3 "$HOOK" 2>/dev/null)

  local actual="allow"
  if echo "$output" | grep -q '"permissionDecision": "deny"'; then
    actual="deny"
  fi

  if [[ "$actual" == "$expected" ]]; then
    echo "  PASS: $description"
    ((PASS++))
  else
    echo "  FAIL: $description (expected $expected, got $actual)"
    echo "    output: $output"
    ((FAIL++))
  fi
}

echo "=== Hard force push variants → deny ==="

run_test "git push --force" deny \
  '{"tool_name":"Bash","tool_input":{"command":"git push --force origin main"}}'

run_test "git push -f" deny \
  '{"tool_name":"Bash","tool_input":{"command":"git push -f origin main"}}'

run_test "git push --force at end of command" deny \
  '{"tool_name":"Bash","tool_input":{"command":"git push origin main --force"}}'

run_test "git push origin +main (plus refspec)" deny \
  '{"tool_name":"Bash","tool_input":{"command":"git push origin +main"}}'

run_test "git  push  --force (extra whitespace)" deny \
  '{"tool_name":"Bash","tool_input":{"command":"git  push  --force"}}'

echo ""
echo "=== --force-with-lease alone → deny (fetch-then-push race) ==="

run_test "git push --force-with-lease (no includes guard)" deny \
  '{"tool_name":"Bash","tool_input":{"command":"git push --force-with-lease origin main"}}'

run_test "git push --force-with-lease=main:abc123 (no includes guard)" deny \
  '{"tool_name":"Bash","tool_input":{"command":"git push --force-with-lease=main:abc123 origin"}}'

echo ""
echo "=== Safe push variants → allow ==="

run_test "git push (no flags)" allow \
  '{"tool_name":"Bash","tool_input":{"command":"git push"}}'

run_test "git push origin main" allow \
  '{"tool_name":"Bash","tool_input":{"command":"git push origin main"}}'

run_test "git push --force-with-lease --force-if-includes" allow \
  '{"tool_name":"Bash","tool_input":{"command":"git push --force-with-lease --force-if-includes origin main"}}'

run_test "git push --force-if-includes --force-with-lease (flags reversed)" allow \
  '{"tool_name":"Bash","tool_input":{"command":"git push --force-if-includes --force-with-lease"}}'

run_test "git push --force-with-lease=main:abc --force-if-includes" allow \
  '{"tool_name":"Bash","tool_input":{"command":"git push --force-with-lease=main:abc --force-if-includes"}}'

run_test "git push --force-if-includes alone (no-op without lease)" allow \
  '{"tool_name":"Bash","tool_input":{"command":"git push --force-if-includes origin main"}}'

run_test "git push -u origin feature" allow \
  '{"tool_name":"Bash","tool_input":{"command":"git push -u origin feature"}}'

run_test "git push --tags" allow \
  '{"tool_name":"Bash","tool_input":{"command":"git push --tags"}}'

echo ""
echo "=== Quoted args (shlex strips quotes) ==="

run_test 'git push "--force"' deny \
  '{"tool_name":"Bash","tool_input":{"command":"git push \"--force\" origin main"}}'

run_test "git push '-f'" deny \
  '{"tool_name":"Bash","tool_input":{"command":"git push '\''-f'\'' origin main"}}'

run_test 'git push "--force-with-lease" (quoted lease alone)' deny \
  '{"tool_name":"Bash","tool_input":{"command":"git push \"--force-with-lease\" origin main"}}'

run_test "Combined short flag -uf" deny \
  '{"tool_name":"Bash","tool_input":{"command":"git push -uf origin feature"}}'

run_test "Combined short flag -fu" deny \
  '{"tool_name":"Bash","tool_input":{"command":"git push -fu origin feature"}}'

echo ""
echo "=== Malformed shell with push → fail closed ==="

run_test "Unclosed quote in push segment → deny" deny \
  '{"tool_name":"Bash","tool_input":{"command":"git push --force \"unclosed"}}'

echo ""
echo "=== Scope discipline (no false positives) ==="

run_test "Safe push then unrelated command with --force literal" allow \
  '{"tool_name":"Bash","tool_input":{"command":"git push origin main && echo --force"}}'

run_test "Safe push then unrelated command with +foo literal" allow \
  '{"tool_name":"Bash","tool_input":{"command":"git push origin main && echo +foo"}}'

run_test "--force in a non-push git command (e.g. checkout)" allow \
  '{"tool_name":"Bash","tool_input":{"command":"git checkout --force main"}}'

run_test "-f in rm (not git push)" allow \
  '{"tool_name":"Bash","tool_input":{"command":"trash -f junk"}}'

run_test "Semicolon inside quoted commit message (regression)" allow \
  '{"tool_name":"Bash","tool_input":{"command":"git commit -m \"foo; push --force in message\""}}'

run_test "Heredoc commit message mentioning force pushes (regression)" allow \
  '{"tool_name":"Bash","tool_input":{"command":"git commit -m \"$(cat <<EOF\nBlock force pushes; mentions --force-with-lease in body\nEOF\n)\""}}'

echo ""
echo "=== Compound commands ==="

run_test "Safe command then force push → deny" deny \
  '{"tool_name":"Bash","tool_input":{"command":"git fetch && git push --force"}}'

run_test "Force push then safe command → deny" deny \
  '{"tool_name":"Bash","tool_input":{"command":"git push -f origin main; echo done"}}'

run_test "Force push behind ||" deny \
  '{"tool_name":"Bash","tool_input":{"command":"true || git push --force"}}'

echo ""
echo "=== Non-Bash tools → allow ==="

run_test "Read tool ignored" allow \
  '{"tool_name":"Read","tool_input":{"file_path":"/tmp/x"}}'

run_test "Edit tool ignored" allow \
  '{"tool_name":"Edit","tool_input":{"file_path":"/tmp/x","old_string":"a","new_string":"b"}}'

echo ""
echo "=== No bypass ==="

run_test "ALLOW_FORCE_PUSH=1 does NOT bypass the block" deny \
  '{"tool_name":"Bash","tool_input":{"command":"git push --force origin main"}}' \
  "ALLOW_FORCE_PUSH=1"

echo ""
echo "================================"
echo "Results: $PASS passed, $FAIL failed"
[[ "$FAIL" -eq 0 ]] && echo "All tests passed!" || exit 1
