# HIPAA gate for aichat.
#
# Wrap `aichat` so it never launches unless its LIVE config passes the
# compliance check (Vertex-only, GA models, no disk persistence). The check
# runs on every invocation against the config aichat will actually use, so
# config drift is caught at the moment of use.
#
# Fail-closed: a missing check, a failing check, a config/model/save env
# override, an undeclared -m/--model value, or a save-to-disk flag all block
# the launch. Bypass is possible with `command aichat` / an absolute path —
# this is a guardrail for normal use, not an adversarial control against
# yourself.
#
# RESIDUAL RISK (launch-time gate cannot close these — source-audited at
# aichat v0.30.0): once the REPL is open, `.model <any-name>` accepts models
# outside config.yaml (aichat synthesizes unknown gemini-*/claude-*/mistral-*
# names and sends them to Vertex), and `.set save true` / `.save session`
# write the transcript to disk despite save:false. Don't use those REPL
# commands. Also, $GOOGLE_CLOUD_HIPAA_PROJECT_ID chooses the GCP project —
# keep it pointed at the BAA-covered project.
aichat() {
  local check="$HOME/.local/bin/aichat-hipaa-check"

  if [[ ! -x "$check" ]]; then
    print -ru2 -- "⛔ aichat blocked: compliance check not found ($check). Deploy dotfiles (save-config)."
    return 1
  fi

  # Refuse env overrides. Config-path vars could point aichat at a different,
  # unvalidated config; AICHAT_MODEL routes to any model name (aichat does not
  # check it against the declared list); the save/messages/sessions vars
  # re-enable or relocate disk persistence; provider/platform/location vars
  # could redirect the client. The gate validates the DEFAULT config, so force
  # aichat to use exactly it.
  local v
  for v in AICHAT_CONFIG_DIR AICHAT_CONFIG_FILE AICHAT_ENV_FILE \
           AICHAT_MODEL AICHAT_SAVE AICHAT_SAVE_SESSION \
           AICHAT_MESSAGES_FILE AICHAT_SESSIONS_DIR \
           AICHAT_PROVIDER AICHAT_PLATFORM GOOGLE_CLOUD_HIPAA_LOCATION; do
    if [[ -n ${(P)v} ]]; then
      print -ru2 -- "⛔ aichat blocked: $v is set — unset it so the validated default config is used."
      return 1
    fi
  done

  # Walk the args: block flags that persist conversation to disk (PHI hygiene)
  # or open a network server, and validate any -m/--model value against the
  # declared allowlist — aichat itself synthesizes undeclared model names and
  # sends them to Vertex instead of rejecting them, so membership is enforced
  # here.
  local -a allowed
  allowed=(${(f)"$("$check" --list-models 2>/dev/null)"})
  local a m i=1
  while (( i <= $# )); do
    a=${@[i]}
    m=""
    case "$a" in
      -s|--session|--save-session)
        print -ru2 -- "⛔ aichat blocked: session/save flags persist PHI to disk — not allowed."
        return 1 ;;
      --serve)
        print -ru2 -- "⛔ aichat blocked: --serve exposes an ungated HTTP endpoint — not allowed."
        return 1 ;;
      -m|--model)
        (( i++ ))
        m=${@[i]:-} ;;
      -m=*|--model=*)
        m=${a#*=} ;;
    esac
    if [[ -n $m ]] && (( ! ${allowed[(Ie)$m]} )); then
      print -ru2 -- "⛔ aichat blocked: model '$m' is not declared in config.yaml."
      print -ru2 -- "   Allowed: ${(j:, :)allowed}"
      return 1
    fi
    (( i++ ))
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

# Short alias for interactive use. `ah` expands to the word `aichat`, which
# resolves to the gate function above (functions win over the binary), so
# every `ah` launch still runs the compliance check. Never point the alias at
# `command aichat` or an absolute path — that would skip the gate.
# Interactive-only: non-interactive (agent) shells must not gain an `ah`
# entry point that the block-aichat hook — which matches the `aichat` token —
# would miss.
if [[ -o interactive ]]; then
  alias ah='aichat'
fi
