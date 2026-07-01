# HIPAA gate for aichat.
#
# Wrap `aichat` so it never launches unless its LIVE config passes the
# compliance check (Vertex-only, GA models, no disk persistence). The check
# runs on every invocation against the config aichat will actually use, so
# config drift is caught at the moment of use.
#
# Fail-closed: a missing check, a failing check, a config-path override, or a
# save-to-disk flag all block the launch. Bypass is possible with
# `command aichat` / an absolute path — this is a guardrail for normal use, not
# an adversarial control against yourself.
aichat() {
  local check="$HOME/.local/bin/aichat-hipaa-check"

  if [[ ! -x "$check" ]]; then
    print -ru2 -- "⛔ aichat blocked: compliance check not found ($check). Deploy dotfiles (save-config)."
    return 1
  fi

  # Refuse config/env-path overrides — they could point aichat at a different,
  # unvalidated config (any provider), bypassing the whole gate. The gate
  # validates the DEFAULT config, so force aichat to use it.
  local v
  for v in AICHAT_CONFIG_DIR AICHAT_CONFIG_FILE AICHAT_ENV_FILE; do
    if [[ -n ${(P)v} ]]; then
      print -ru2 -- "⛔ aichat blocked: $v is set — unset it so the validated default config is used."
      return 1
    fi
  done

  # Block flags that persist conversation to disk (PHI hygiene) despite
  # save:false in the config.
  local a
  for a in "$@"; do
    case "$a" in
      -s|--session|--save-session)
        print -ru2 -- "⛔ aichat blocked: session/save flags persist PHI to disk — not allowed."
        return 1 ;;
    esac
  done

  # Validate the live (default) config; block on any violation.
  local report
  if ! report=$("$check" 2>&1); then
    print -ru2 -- "$report"
    print -ru2 -- "⛔ aichat blocked: config is not HIPAA-compliant (see above). Fix it, then retry."
    return 1
  fi

  # Surface the ✓ attestation on every launch (stderr, so piping stdout is
  # unaffected) — visible proof the gate ran and passed, never a silent no-op.
  print -ru2 -- "$report"

  command aichat "$@"
}
