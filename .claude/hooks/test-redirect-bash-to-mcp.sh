#!/usr/bin/env bash
# Regression tests for redirect-bash-to-mcp.py.
#
# Run from this directory or with the absolute path. Exits non-zero if any
# case behaves unexpectedly.

set -euo pipefail

HOOK="$(cd "$(dirname "$0")" && pwd)/redirect-bash-to-mcp.py"

fail=0

check() {
  local expected="$1"; shift
  local cmd="$1"; shift
  local result
  result=$(printf '{"tool_name":"Bash","tool_input":{"command":%s}}' \
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

# Raw redirect-target invocations: DENY
check DENY "cargo --version"
check DENY "cargo test --workspace"
check DENY "cd /repo && cargo test"
check DENY "save-config"

# `git commit` with redirect-target words in the message body: ALLOW
# (the trigger that motivated this hook's tightening).
check ALLOW "git commit -m 'fix cargo bug'"
check ALLOW "git commit -m 'add run_cargo wrapper'"
check ALLOW "git commit -F /tmp/msg.txt"

# `git commit -m '...' && cargo test`: still DENY (cargo is its own segment).
check DENY "git commit -m 'x' && cargo test"

# Env-var-prefixed cargo invocations: still DENY (the prefix doesn't
# disguise the real command name; the redirect check looks past assignment
# tokens).
check DENY "RUST_TEST_THREADS=1 cargo test"
check DENY "RUST_TEST_THREADS=1 cargo test --workspace -- --ignored"
check DENY "RUST_LOG=debug RUST_TEST_THREADS=1 cargo test"
check DENY "cd /repo && RUST_TEST_THREADS=1 cargo test"
check DENY "FOO=bar save-config"

# Env-var prefix on git commit shouldn't unlock the message body either.
check ALLOW "GIT_AUTHOR_NAME='Test' git commit -m 'fix cargo'"

# Innocent uses of the redirect-target word: ALLOW
check ALLOW "echo cargo is fine"
check ALLOW "echo 'run save-config later'"
# Env-var with a redirect-name-as-value: ALLOW (it's a value, not a command).
check ALLOW "echo FOO=cargo"
# Cargo arg containing an `=` (--feature=...) is NOT an env-prefix; still
# DENY because cargo itself is at command-start.
check DENY "cargo build --features=foo"

if [[ $fail -ne 0 ]]; then
  echo
  echo "FAIL: at least one case behaved unexpectedly"
  exit 1
fi

echo
echo "PASS: all cases behaved as expected"
