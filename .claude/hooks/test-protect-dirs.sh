#!/bin/bash
# Test suite for protect-dirs.py hook
# Usage: bash .claude/hooks/test-protect-dirs.sh

set -uo pipefail

HOOK="$(dirname "$0")/protect-dirs.py"
PASS=0
FAIL=0
HOME_DIR="$(python3 -c 'import os; print(os.path.expanduser("~"))')"

run_test() {
  local description="$1"
  local expected_exit="$2"  # 0=allow, 2=block
  local protected_dirs="$3"
  local json="$4"

  actual_exit=0
  echo "$json" | PROTECTED_DIRS="$protected_dirs" python3 "$HOOK" 2>/dev/null || actual_exit=$?

  if [[ "$actual_exit" -eq "$expected_exit" ]]; then
    echo "  PASS: $description"
    ((PASS++))
  else
    echo "  FAIL: $description (expected exit $expected_exit, got $actual_exit)"
    ((FAIL++))
  fi
}

echo "=== File tools (Read/Write/Edit) ==="

run_test "Read into protected dir → block" 2 \
  "$HOME_DIR/secrets" \
  '{"tool_name":"Read","tool_input":{"file_path":"'"$HOME_DIR"'/secrets/f"}}'

run_test "Read unrelated path → allow" 0 \
  "$HOME_DIR/secrets" \
  '{"tool_name":"Read","tool_input":{"file_path":"'"$HOME_DIR"'/Repos/foo"}}'

run_test "Write into protected dir → block" 2 \
  "$HOME_DIR/secrets" \
  '{"tool_name":"Write","tool_input":{"file_path":"'"$HOME_DIR"'/secrets/new.txt","content":"x"}}'

run_test "Edit into protected dir → block" 2 \
  "$HOME_DIR/secrets" \
  '{"tool_name":"Edit","tool_input":{"file_path":"'"$HOME_DIR"'/secrets/config","old_string":"a","new_string":"b"}}'

echo ""
echo "=== Boundary safety ==="

run_test "Exact match → block" 2 \
  "/a/b" \
  '{"tool_name":"Read","tool_input":{"file_path":"/a/b"}}'

run_test "Child of protected → block" 2 \
  "/a/b" \
  '{"tool_name":"Read","tool_input":{"file_path":"/a/b/foo"}}'

run_test "/a/bc is NOT under /a/b → allow" 0 \
  "/a/b" \
  '{"tool_name":"Read","tool_input":{"file_path":"/a/bc"}}'

run_test "/a/b-other is NOT under /a/b → allow" 0 \
  "/a/b" \
  '{"tool_name":"Read","tool_input":{"file_path":"/a/b-other/file"}}'

echo ""
echo "=== Bash commands ==="

run_test "Bash cat ~/secrets/file → block" 2 \
  "~/secrets" \
  '{"tool_name":"Bash","tool_input":{"command":"cat ~/secrets/file"}}'

run_test 'Bash cat $HOME/secrets/file → block' 2 \
  "~/secrets" \
  '{"tool_name":"Bash","tool_input":{"command":"cat $HOME/secrets/file"}}'

run_test 'Bash cat ${HOME}/secrets/file → block' 2 \
  "~/secrets" \
  '{"tool_name":"Bash","tool_input":{"command":"cat ${HOME}/secrets/file"}}'

run_test "Bash with absolute protected path → block" 2 \
  "$HOME_DIR/secrets" \
  '{"tool_name":"Bash","tool_input":{"command":"cat '"$HOME_DIR"'/secrets/file"}}'

run_test "Bash unrelated command → allow" 0 \
  "$HOME_DIR/secrets" \
  '{"tool_name":"Bash","tool_input":{"command":"ls /tmp"}}'

echo ""
echo "=== Glob ==="

run_test "Glob pattern into protected dir → block" 2 \
  "$HOME_DIR/secrets" \
  '{"tool_name":"Glob","tool_input":{"pattern":"'"$HOME_DIR"'/secrets/**/*.txt"}}'

run_test "Glob with path field into protected dir → block" 2 \
  "$HOME_DIR/secrets" \
  '{"tool_name":"Glob","tool_input":{"path":"'"$HOME_DIR"'/secrets","pattern":"**/*.txt"}}'

run_test "Glob unrelated pattern → allow" 0 \
  "$HOME_DIR/secrets" \
  '{"tool_name":"Glob","tool_input":{"pattern":"'"$HOME_DIR"'/Repos/**/*.txt"}}'

echo ""
echo "=== Grep ==="

run_test "Grep into protected dir → block" 2 \
  "$HOME_DIR/secrets" \
  '{"tool_name":"Grep","tool_input":{"path":"'"$HOME_DIR"'/secrets","pattern":"password"}}'

run_test "Grep unrelated path → allow" 0 \
  "$HOME_DIR/secrets" \
  '{"tool_name":"Grep","tool_input":{"path":"'"$HOME_DIR"'/Repos","pattern":"TODO"}}'

echo ""
echo "=== NotebookEdit ==="

run_test "NotebookEdit into protected dir → block" 2 \
  "$HOME_DIR/secrets" \
  '{"tool_name":"NotebookEdit","tool_input":{"notebook_path":"'"$HOME_DIR"'/secrets/nb.ipynb","new_source":"x"}}'

echo ""
echo "=== Multiple protected dirs ==="

run_test "Second dir in colon-separated list → block" 2 \
  "/safe/dir:$HOME_DIR/secrets" \
  '{"tool_name":"Read","tool_input":{"file_path":"'"$HOME_DIR"'/secrets/f"}}'

run_test "First dir in colon-separated list → block" 2 \
  "$HOME_DIR/secrets:/other/dir" \
  '{"tool_name":"Read","tool_input":{"file_path":"'"$HOME_DIR"'/secrets/f"}}'

echo ""
echo "=== Missing PROTECTED_DIRS ==="

actual_exit=0
echo '{"tool_name":"Read","tool_input":{"file_path":"/tmp/x"}}' | PROTECTED_DIRS="" python3 "$HOOK" 2>/dev/null || actual_exit=$?
if [[ "$actual_exit" -eq 2 ]]; then
  echo "  PASS: Empty PROTECTED_DIRS → block"
  ((PASS++))
else
  echo "  FAIL: Empty PROTECTED_DIRS → block (expected exit 2, got $actual_exit)"
  ((FAIL++))
fi

actual_exit=0
echo '{"tool_name":"Read","tool_input":{"file_path":"/tmp/x"}}' | env -u PROTECTED_DIRS python3 "$HOOK" 2>/dev/null || actual_exit=$?
if [[ "$actual_exit" -eq 2 ]]; then
  echo "  PASS: Unset PROTECTED_DIRS → block"
  ((PASS++))
else
  echo "  FAIL: Unset PROTECTED_DIRS → block (expected exit 2, got $actual_exit)"
  ((FAIL++))
fi

echo ""
echo "=== Unknown tools (fallback) ==="

run_test "Unknown tool with file_path → block" 2 \
  "$HOME_DIR/secrets" \
  '{"tool_name":"SomeTool","tool_input":{"file_path":"'"$HOME_DIR"'/secrets/f"}}'

run_test "Unknown tool with no path fields → allow" 0 \
  "$HOME_DIR/secrets" \
  '{"tool_name":"SomeTool","tool_input":{"data":"hello"}}'

echo ""
echo "================================"
echo "Results: $PASS passed, $FAIL failed"
[[ "$FAIL" -eq 0 ]] && echo "All tests passed!" || exit 1
