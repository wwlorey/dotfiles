#!/bin/zsh
# End-to-end test for the goose() HIPAA gate (~/.zsh/goose.zsh) + goose-hipaa-check.
# Usage: zsh ~/.zsh/test-goose-gate.zsh   (needs read access to ~/.local/bin)
#
# Stubs the goose binary with a fake on PATH so `command goose` runs the fake,
# which prints the env the gate injected. This exercises the REAL composed
# artifact — the guard/happy paths that isolated component tests miss (a
# non-executable checker, a self-colliding global). Re-run after ANY change to
# goose.zsh, goose-hipaa-check, or the locked config.

emulate -L zsh
setopt no_unset
PASS=0 FAIL=0
ok()   { print "  PASS: $1"; ((PASS++)); }
bad()  { print "  FAIL: $1 — $2"; ((FAIL++)); }

bin="${TMPDIR:-/tmp}/goose-gate-test-bin"; mkdir -p "$bin"
cat > "$bin/goose" <<'FAKE'
#!/bin/sh
echo "FAKE-RAN"
echo "PATHROOT=$GOOSE_PATH_ROOT"
echo "PROJ=$GCP_PROJECT_ID"
echo "TEL=$GOOSE_TELEMETRY_ENABLED"
echo "TELOFF=$GOOSE_TELEMETRY_OFF"
FAKE
chmod +x "$bin/goose"
export PATH="$bin:$PATH"

source "$HOME/.zsh/goose.zsh"
TESTPROJ="test-baa-project-123"

# expect_block: the gate must refuse (⛔) and the fake must NOT run.
expect_block() {  # label ; command-line
  local label=$1 out
  out=$(eval "$2" 2>&1)
  if [[ $out == *"FAKE-RAN"* ]]; then bad "$label" "gate let the binary run"
  elif [[ $out == *"⛔"* ]]; then ok "$label"
  else bad "$label" "no ⛔ and no run: ${out:0:80}"; fi
}

print "=== Guard paths → block (binary must NOT run) ==="
expect_block "missing project id"      "unset GOOGLE_CLOUD_HIPAA_PROJECT_ID; goose session"
expect_block "GOOSE_PROVIDER override" "GOOGLE_CLOUD_HIPAA_PROJECT_ID=$TESTPROJ GOOSE_PROVIDER=openai goose session"
expect_block "XDG_CONFIG_HOME"         "GOOGLE_CLOUD_HIPAA_PROJECT_ID=$TESTPROJ XDG_CONFIG_HOME=/tmp/e goose session"
expect_block "HTTPS_PROXY"             "GOOGLE_CLOUD_HIPAA_PROJECT_ID=$TESTPROJ HTTPS_PROXY=http://e:8080 goose session"
expect_block "SSL_CERT_FILE"           "GOOGLE_CLOUD_HIPAA_PROJECT_ID=$TESTPROJ SSL_CERT_FILE=/tmp/mitm.pem goose session"
expect_block "--with-extension"        "GOOGLE_CLOUD_HIPAA_PROJECT_ID=$TESTPROJ goose --with-extension 'sh -c curl'"
expect_block "--with-remote-extension" "GOOGLE_CLOUD_HIPAA_PROJECT_ID=$TESTPROJ goose --with-remote-extension https://e/mcp"
expect_block "--with-streamable-http-extension" "GOOGLE_CLOUD_HIPAA_PROJECT_ID=$TESTPROJ goose --with-streamable-http-extension https://e/mcp"
expect_block "--with-builtin"          "GOOGLE_CLOUD_HIPAA_PROJECT_ID=$TESTPROJ goose --with-builtin computercontroller"
expect_block "run --provider override" "GOOGLE_CLOUD_HIPAA_PROJECT_ID=$TESTPROJ goose run --provider openai -t hi"
expect_block "run --model override"    "GOOGLE_CLOUD_HIPAA_PROJECT_ID=$TESTPROJ goose run --model gpt-4o -t hi"

# custom-providers guard: a declarative provider def under the pinned root must
# block the launch (it could define an off-Vertex base_url). Create a dummy,
# assert block, always clean up — the trap covers an interrupt mid-test so a
# stray file can't wedge real launches.
cpd="$HOME/.config/goose-hipaa/config/custom_providers"
trap 'rm -f "$cpd/zz-gate-test.json" 2>/dev/null; rmdir "$cpd" 2>/dev/null' EXIT INT TERM
mkdir -p "$cpd"; print '{}' > "$cpd/zz-gate-test.json"
expect_block "custom_providers dir non-empty" "GOOGLE_CLOUD_HIPAA_PROJECT_ID=$TESTPROJ goose session"
rm -f "$cpd/zz-gate-test.json"; rmdir "$cpd" 2>/dev/null; trap - EXIT INT TERM

print "=== Happy path → attest + run + correct injected env ==="
out=$(GOOGLE_CLOUD_HIPAA_PROJECT_ID=$TESTPROJ goose session 2>&1)
[[ $out == *"✓ HIPAA-locked"* ]] && ok "prints ✓ attestation" || bad "attestation" "no ✓: ${out:0:80}"
[[ $out == *"FAKE-RAN"* ]]       && ok "binary actually runs (would fail on self-block/non-exec)" || bad "runs" "binary did not run: ${out:0:120}"
[[ $out == *"PATHROOT=$HOME/.config/goose-hipaa"* ]] && ok "injects GOOSE_PATH_ROOT" || bad "GOOSE_PATH_ROOT" "$out"
[[ $out == *"PROJ=$TESTPROJ"* ]] && ok "injects trusted GCP_PROJECT_ID" || bad "GCP_PROJECT_ID" "$out"
[[ $out == *"TEL=false"* && $out == *"TELOFF=1"* ]] && ok "injects telemetry kill-switch" || bad "telemetry" "$out"

print "=== Injected env must NOT leak into the caller shell ==="
leak=0
for v in GOOSE_PATH_ROOT GCP_PROJECT_ID GOOSE_TELEMETRY_ENABLED GOOSE_TELEMETRY_OFF; do
  [[ -n ${(P)v:-} ]] && { bad "no leak: $v" "leaked=${(P)v}"; leak=1; }
done
(( leak == 0 )) && ok "no injected var leaked"

print "=== Checker rejects non-compliant configs ==="
chk="$HOME/.local/bin/goose-hipaa-check"
t="${TMPDIR:-/tmp}/goose-gate-test-cfg"; mkdir -p "$t"
base='GOOSE_PROVIDER: gcp_vertex_ai\nGOOSE_MODEL: gemini-2.5-pro\nGCP_LOCATION: us-central1\nGOOSE_TELEMETRY_ENABLED: false\nGOOSE_MODE: approve\n'
reject() {  # label ; yaml
  local label=$1; print "$2" > "$t/c.yaml"
  if "$chk" "$t/c.yaml" >/dev/null 2>&1; then bad "reject $label" "checker PASSED a bad config"; else ok "reject $label"; fi
}
reject "AI-Studio provider" 'GOOSE_PROVIDER: google\nGOOSE_MODEL: gemini-2.5-pro\nGCP_LOCATION: us-central1\nGOOSE_TELEMETRY_ENABLED: false\nGOOSE_MODE: approve\n'
reject "preview model"      'GOOSE_PROVIDER: gcp_vertex_ai\nGOOSE_MODEL: gemini-2.5-pro-preview\nGCP_LOCATION: us-central1\nGOOSE_TELEMETRY_ENABLED: false\nGOOSE_MODE: approve\n'
reject "telemetry on"       'GOOSE_PROVIDER: gcp_vertex_ai\nGOOSE_MODEL: gemini-2.5-pro\nGCP_LOCATION: us-central1\nGOOSE_MODE: approve\n'
reject "auto mode"          'GOOSE_PROVIDER: gcp_vertex_ai\nGOOSE_MODEL: gemini-2.5-pro\nGCP_LOCATION: us-central1\nGOOSE_TELEMETRY_ENABLED: false\nGOOSE_MODE: auto\n'
reject "remote extension"   "${base}extensions:\n  x:\n    type: sse\n    uri: https://e/mcp\n"
reject "CA cert config key"  "${base}GOOSE_CA_CERT_PATH: /tmp/mitm.pem\n"
reject "proxy config key"    "${base}HTTPS_PROXY: http://attacker:8080\n"
# sanity: the compliant base must PASS
print "$base" > "$t/c.yaml"
"$chk" "$t/c.yaml" >/dev/null 2>&1 && ok "accepts a compliant config" || bad "accept compliant" "checker rejected a good config"

print ""
print "================================"
print "Results: $PASS passed, $FAIL failed"
(( FAIL == 0 )) && print "All tests passed!" || exit 1
