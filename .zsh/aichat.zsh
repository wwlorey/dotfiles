# HIPAA gate for aichat.
#
# Wrap `aichat` so it never launches unless its LIVE config passes the
# compliance check (Vertex-only, GA models, no disk persistence). The check
# runs on every invocation against the config aichat will actually use, so
# config drift is caught at the moment of use.
#
# Fail-closed via ALLOWLISTS, not denylists (aichat's override surface is too
# large and version-growing to enumerate safely — source-audited at v0.30.0):
#   - ENV: any AICHAT_* or GOOGLE_CLOUD_HIPAA_* var (except the required
#     PROJECT_ID) blocks the launch. This covers AICHAT_PATCH_<client>_<api>,
#     which can rewrite the request URL to ANY host (PHI exfiltration) while the
#     gate still prints ✓, plus model/provider/save/dir overrides.
#   - .env: a sibling config-dir/.env blocks the launch — aichat auto-loads it
#     into the environment before config, re-supplying any refused var.
#   - ARGS: only a small safe set of flags is permitted; -m/--model must name a
#     declared model. -s/--session is permitted so an interactive session can
#     hold multi-turn context (the plain REPL keeps none) — safe because the
#     checker enforces save_session:false, so the session lives only in memory
#     and is never written to disk (so it does not survive exit or resume across
#     invocations). Every other flag (‑a/‑e/‑r/--save-session/--serve/--rag/
#     --macro/--agent …, and clap's attached/stacked short forms) blocks.
# Bypass is possible with `command aichat` / an absolute path — this is a
# guardrail for normal use, not an adversarial control against yourself.
#
# RESIDUAL RISK (launch-time gate cannot close these — source-audited at
# aichat v0.30.0): once the REPL is open, `.model <any-name>` accepts models
# outside config.yaml (aichat synthesizes unknown gemini-*/claude-*/mistral-*
# names and sends them to Vertex), and `.set save true` / `.set save_session
# true` / `.save session` write the transcript to disk despite save:false /
# save_session:false. Don't use those REPL commands — an `-s` session stays in
# memory only as long as save_session:false holds. Also,
# $GOOGLE_CLOUD_HIPAA_PROJECT_ID chooses the GCP project —
# keep it pointed at the BAA-covered project.
aichat() {
  local check="$HOME/.local/bin/aichat-hipaa-check"

  if [[ ! -x "$check" ]]; then
    print -ru2 -- "⛔ aichat blocked: compliance check not found ($check). Deploy dotfiles (save-config)."
    return 1
  fi

  # ENV allowlist: refuse ANY aichat-influencing env var. aichat honors a large,
  # version-growing AICHAT_* surface — model, provider, platform, save/session/
  # history, roles/macros/functions/rags dirs, and critically
  # AICHAT_PATCH_<CLIENT>_<API>, whose JSON value can rewrite the request URL to
  # any host (PHI exfiltration). Enumerating the dangerous ones is a losing game,
  # so block on the whole namespace; keep only the required project id.
  # Also refuse HTTP(S)_PROXY/ALL_PROXY (either case) and CA/cert overrides:
  # aichat's reqwest client honors the system proxy env by default (it never
  # calls .no_proxy()), so a stray proxy var reroutes the Vertex request off
  # "only to Vertex" — and a rogue CA bundle lets a MITM proxy decrypt PHI.
  local v
  for v in ${(Mk)parameters:#(AICHAT_*|GOOGLE_CLOUD_HIPAA_*|HTTP_PROXY|HTTPS_PROXY|ALL_PROXY|http_proxy|https_proxy|all_proxy|SSL_CERT_FILE|SSL_CERT_DIR|REQUESTS_CA_BUNDLE|CURL_CA_BUNDLE)}; do
    [[ $v == GOOGLE_CLOUD_HIPAA_PROJECT_ID ]] && continue
    print -ru2 -- "⛔ aichat blocked: $v is set — it can redirect the model, provider, request URL, or persistence, or route/decrypt PHI traffic through a proxy. Unset it and retry."
    return 1
  done

  # Refuse a sibling .env: aichat auto-loads config_dir/.env into the process
  # environment BEFORE config init (main.rs load_env_file → env::set_var), so
  # any var refused above can be smuggled back in via that file, and neither the
  # wrapper (which reads only the live shell env) nor the checker (which parses
  # only config.yaml) would see it. Block the launch if it exists.
  local envfile="$HOME/Library/Application Support/aichat/.env"
  if [[ -e $envfile ]]; then
    print -ru2 -- "⛔ aichat blocked: $envfile exists — aichat auto-loads it into the environment before config, re-supplying refused overrides. Remove it."
    return 1
  fi

  # ARG allowlist: permit only known-safe flags. Everything else beginning with
  # '-' is blocked — this covers the whole dangerous flag surface
  # (--save-session, --serve, --rag/--rebuild-rag, --macro, -a/--agent,
  # -r/--role, -e/--execute, --sync-models) AND clap's attached (-mVAL), stacked
  # (-Sm VAL), and =forms that plain token-matching misses. A permitted
  # -m/--model value is checked against the declared allowlist (aichat otherwise
  # synthesizes unknown model names and sends them to Vertex). -s/--session is
  # permitted so an interactive session can hold multi-turn context (the plain
  # REPL keeps none); it stays in memory and cannot persist to disk while the
  # checker holds save_session:false. Bare text (the prompt) is always fine.
  local -a allowed
  allowed=(${(f)"$("$check" --list-models 2>/dev/null)"})
  local a m i=1 rest=0
  while (( i <= $# )); do
    a=${@[i]}
    if (( rest )); then (( i++ )); continue; fi   # after `--`, all args are text
    m=""
    case "$a" in
      --) rest=1 ;;
      -m|--model)
        (( i++ )); m=${@[i]:-} ;;
      -m=*|--model=*)
        m=${a#*=} ;;
      -f|--file|--prompt)              # value-taking: consume the value, but ONLY
        [[ ${@[i+1]:-} != -* ]] && (( i++ )) ;;  # if it isn't itself a flag — else
                                       # a swallowed --serve/--rag/--macro would
                                       # slip past the block arm below unseen.
      -f=*|--file=*|--prompt=*)
        ;;
      -s|--session|-s=*|--session=*)   # session: multi-turn context within one
        ;;                             # interactive run. The value is optional
                                       # — a separate name token is harmless
                                       # plain text — and save_session:false
                                       # (checker-enforced) keeps it in memory.
      -S|--no-stream|-c|--code|--dry-run|--info|\
      --list-models|--list-roles|--list-sessions|--list-agents|--list-rags|--list-macros|\
      -h|--help|-V|--version)          # safe booleans / read-only utilities
        ;;
      -*)
        print -ru2 -- "⛔ aichat blocked: flag '$a' is not permitted by the HIPAA gate."
        print -ru2 -- "   Permitted: -m/--model <declared>, -s/--session, -f/--file <path>, --prompt, -S, -c, --dry-run, --list-*, and plain text."
        return 1 ;;
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

# Short alias for interactive use. `ah` expands to `aichat -s`, whose first
# word `aichat` resolves to the gate function above (functions win over the
# binary), so every `ah` launch still runs the compliance check. `-s` makes
# each run hold multi-turn session context; it stays in memory only, since the
# checker enforces save_session:false, so nothing is written to disk. Never
# point the alias at `command aichat` or an absolute path — that skips the gate.
# Interactive-only: non-interactive (agent) shells must not gain an `ah`
# entry point that the block-aichat hook — which matches the `aichat` token —
# would miss.
if [[ -o interactive ]]; then
  alias ah='aichat -s'
fi
