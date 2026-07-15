#!/bin/zsh
# End-to-end test for the aichat() HIPAA gate (~/.zsh/aichat.zsh) + aichat-hipaa-check.
# Usage: zsh ~/.zsh/test-aichat-gate.zsh   (needs read access to ~/.local/bin)
#
# Stubs the aichat binary with a fake on PATH so `command aichat` runs the fake.
# Exercises the REAL gate: env allowlist, arg allowlist (declared-model check),
# happy path, and the checker's reject matrix. Re-run after ANY change to
# aichat.zsh, aichat-hipaa-check, or the locked aichat config.

emulate -L zsh
PASS=0 FAIL=0
ok()  { print "  PASS: $1"; ((PASS++)); }
bad() { print "  FAIL: $1 — $2"; ((FAIL++)); }

bin="${TMPDIR:-/tmp}/aichat-gate-test-bin"; mkdir -p "$bin"
print '#!/bin/sh\necho "FAKE-RAN args=[$*]"' > "$bin/aichat"; chmod +x "$bin/aichat"
export PATH="$bin:$PATH"
source "$HOME/.zsh/aichat.zsh"
chk="$HOME/.local/bin/aichat-hipaa-check"
dm=$("$chk" --list-models 2>/dev/null | head -1)   # a declared model id

expect_block() {  # label ; command-line
  local label=$1 out; out=$(eval "$2" 2>&1)
  if [[ $out == *"FAKE-RAN"* ]]; then bad "$label" "gate let the binary run"
  elif [[ $out == *"⛔"* ]]; then ok "$label"
  else bad "$label" "no ⛔ and no run: ${out:0:80}"; fi
}
expect_run() {  # label ; command-line
  local label=$1 out; out=$(eval "$2" 2>&1)
  [[ $out == *"FAKE-RAN"* ]] && ok "$label" || bad "$label" "binary did not run: ${out:0:100}"
}

print "=== Guard paths → block ==="
expect_block "AICHAT_* env override"          "AICHAT_MODEL=x aichat hi"
expect_block "GOOGLE_CLOUD_HIPAA_* override"   "GOOGLE_CLOUD_HIPAA_REGION=x aichat hi"
expect_block "HTTPS_PROXY env"                "HTTPS_PROXY=http://e:8080 aichat hi"
expect_block "disallowed flag --serve"        "aichat --serve"
expect_block "-f swallowing --serve"          "aichat -f --serve"
expect_block "undeclared -m model"            "aichat -m nope:nope hi"

print "=== Allowed paths → run (binary must execute) ==="
expect_run "plain text prompt"                "aichat hello world"
expect_run "-s session"                       "aichat -s mysession"
if [[ -n $dm ]]; then
  expect_run "declared -m model ($dm)"        "aichat -m $dm hi"
else
  bad "declared -m model" "checker --list-models returned nothing"
fi

print "=== Checker rejects non-compliant aichat configs ==="
t="${TMPDIR:-/tmp}/aichat-gate-test-cfg"; mkdir -p "$t"
good='model: google_cloud_hipaa:gemini-2.5-flash-lite\nsave: false\nsave_session: false\nsave_shell_history: false\nclients:\n  - type: vertexai\n    name: google_cloud_hipaa\n    models:\n      - name: gemini-2.5-flash-lite\n'
reject() { local label=$1; print "$2" > "$t/c.yaml"
  if "$chk" "$t/c.yaml" >/dev/null 2>&1; then bad "reject $label" "checker PASSED a bad config"; else ok "reject $label"; fi }
reject "gemini (AI-Studio) client" 'model: g:m\nsave: false\nsave_session: false\nsave_shell_history: false\nclients:\n  - type: gemini\n    name: g\n    models:\n      - name: gemini-2.5-flash\n'
reject "save: true"                'model: google_cloud_hipaa:gemini-2.5-flash-lite\nsave: true\nsave_session: false\nsave_shell_history: false\nclients:\n  - type: vertexai\n    name: google_cloud_hipaa\n    models:\n      - name: gemini-2.5-flash-lite\n'
reject "preview model"             'model: google_cloud_hipaa:gemini-2.5-flash-preview\nsave: false\nsave_session: false\nsave_shell_history: false\nclients:\n  - type: vertexai\n    name: google_cloud_hipaa\n    models:\n      - name: gemini-2.5-flash-preview\n'
reject "save key omitted (aichat defaults to persist)" 'model: google_cloud_hipaa:gemini-2.5-flash-lite\nsave_session: false\nsave_shell_history: false\nclients:\n  - type: vertexai\n    name: google_cloud_hipaa\n    models:\n      - name: gemini-2.5-flash-lite\n'
print "$good" > "$t/c.yaml"
"$chk" "$t/c.yaml" >/dev/null 2>&1 && ok "accepts a compliant config" || bad "accept compliant" "checker rejected a good config"

print ""
print "================================"
print "Results: $PASS passed, $FAIL failed"
(( FAIL == 0 )) && print "All tests passed!" || exit 1
