# HIPAA gate for goose.
#
# Wrap `goose` so it never launches unless its LIVE config passes the compliance
# check (Vertex-only provider, GA model, telemetry off, human-in-the-loop mode,
# no remote extensions). The check runs on every invocation against the config
# goose will actually use, so config drift is caught at the moment of use — the
# same discipline as the aichat gate, widened to cover a tool that also touches
# the filesystem and shell.
#
# PINNED ROOT: the gate injects GOOSE_PATH_ROOT=$GOOSE_HIPAA_ROOT, so goose reads
# its config/data/state under that dedicated dir and the checker validates the
# SAME file — the two can no longer drift to different paths (goose's default
# config location varies by build/platform, and an unvetted file there would
# otherwise be run under a passing ✓). A non-gated entrypoint (bash script,
# cron, the Desktop app) that reads goose's DEFAULT location finds no config
# under this root and fails closed instead of running unlocked.
#
# Fail-closed via ALLOWLISTS, not denylists:
#   - ENV: any GOOSE_*/GCP_*/GOOGLE_*/VERTEX_* var, or XDG_CONFIG_HOME /
#     XDG_DATA_HOME (which relocate the dirs goose resolves config/data from, so
#     a set value would point goose at a file the checker never saw), blocks the
#     launch — except the required PROJECT_ID, which the gate re-injects below
#     from the trusted source.
#   - COMPETING CONFIG: an unvetted config at goose's default XDG/Library
#     location blocks the launch — such a file is what a non-gated entrypoint (or
#     goose's own path precedence) could run instead of the locked one.
#   - .env: a sibling .env in the pinned config dir blocks the launch — goose
#     auto-loads it into the environment, re-supplying any refused var.
#   - ARGS: request-time overrides that bypass the config lock are blocked —
#     ad-hoc MCP extensions (--with-*), provider/model overrides (--provider/
#     --model), and recipe loading (--recipe, whose settings/extensions override
#     the locked config unseen by the checker). Everything else passes.
#
# Bypass is possible with `command goose` / an absolute path — this is a
# guardrail for normal use, not an adversarial control against yourself.
#
# RESIDUAL RISK (a launch-time gate cannot close these): a coding harness runs
# shell commands, so it can exfiltrate PHI over the network (curl/git/scp)
# regardless of where the MODEL endpoint points — GOOSE_MODE:approve (checker-
# enforced) makes every such action require your approval, so nothing leaves
# silently, but you can still approve an egress. The Desktop app, if it has its
# own config at the default path, is outside this gate — do not use it for PHI.
# `goose configure` can rewrite the config to a non-Vertex provider — caught on
# the NEXT gated launch, and save-config overwrites it on the next deploy anyway
# (edit the config in the dotfiles repo, not via configure). Session content
# persists to a local SQLite DB under the pinned root by design — keep the disk
# encrypted (FileVault) and wipe stale sessions when they may hold PHI.
goose() {
  # `root` is a function-local, NOT a global named GOOSE_* — a GOOSE_*-namespaced
  # global would be caught by this gate's own ENV allowlist below and block every
  # launch. Locals named check/root/cfg/… don't match the refused patterns.
  local check="$HOME/.local/bin/goose-hipaa-check"
  local root="$HOME/.config/goose-hipaa"
  local cfg="$root/config/config.yaml"

  if [[ ! -x "$check" ]]; then
    print -ru2 -- "⛔ goose blocked: compliance check not found ($check). Deploy dotfiles (save-config)."
    return 1
  fi

  if [[ -z "${GOOGLE_CLOUD_HIPAA_PROJECT_ID:-}" ]]; then
    print -ru2 -- "⛔ goose blocked: \$GOOGLE_CLOUD_HIPAA_PROJECT_ID is not set — the gate injects it as the BAA Vertex project. Set it in your private dotfiles and retry."
    return 1
  fi

  # ENV allowlist: refuse any goose-/Vertex-influencing env var except the
  # required project id (which the gate re-injects below from the trusted
  # source, so a pre-set value is refused rather than trusted). Also refused:
  #   - XDG_CONFIG_HOME / XDG_DATA_HOME — goose resolves its config/data dirs
  #     through them, so a set value would point goose at a config file the
  #     checker never validated.
  #   - HTTP(S)_PROXY / ALL_PROXY (both cases) — a proxy would route the
  #     PHI-bound Vertex traffic through a third party (observe/redirect, and
  #     with a planted CA, decrypt).
  #   - SSL_CERT_* / REQUESTS_CA_BUNDLE / CURL_CA_BUNDLE / AWS_CA_BUNDLE /
  #     NODE_EXTRA_CA_CERTS — a rogue CA bundle can make a MITM proxy's cert
  #     trusted, enabling PHI decryption in transit.
  #   - Trace/observability exporters that ship LLM prompts and responses (PHI)
  #     to an operator-chosen host, each a distinct channel from the PostHog
  #     usage telemetry that GOOSE_TELEMETRY_* governs:
  #       * OTEL_* — goose's built-in OpenTelemetry/OTLP exporter
  #         (OTEL_EXPORTER_OTLP_ENDPOINT = arbitrary collector). Refused here AND
  #         killed via OTEL_SDK_DISABLED in the injected env below; OTEL_SDK_
  #         DISABLED itself is exempt (it can only turn tracing OFF, and the
  #         injected value overrides any inherited one).
  #       * LANGFUSE_* — goose's Langfuse integration captures full prompt/
  #         completion traces the moment these vars are present, to LANGFUSE_URL/
  #         _BASE_URL (any host). No build flag needed, so refuse them.
  #       * SECURITY_PROMPT_* — the prompt-injection classifier POSTs prompt
  #         content to SECURITY_PROMPT_CLASSIFIER_ENDPOINT for scoring.
  #     Any future goose exporter env is a new hole — add its prefix here.
  # Per-provider host/base-url overrides (OPENAI_HOST, OLLAMA_HOST, …) are NOT
  # refused here: they are inert while GOOSE_PROVIDER is pinned to Vertex, a
  # drifted provider is caught by the checker on this same launch before goose
  # runs, and blocking them by prefix would trip on an unrelated OPENAI_API_KEY.
  # The config-side equivalent (a host/base-url/endpoint key in config.yaml) IS
  # rejected by goose-hipaa-check, which is where such drift actually persists.
  # Fail closed on all of the below.
  local v
  for v in ${(Mk)parameters:#(GOOSE_*|GCP_*|GOOGLE_*|VERTEX_*|OTEL_*|LANGFUSE_*|SECURITY_PROMPT_*|XDG_CONFIG_HOME|XDG_DATA_HOME|HTTP_PROXY|HTTPS_PROXY|ALL_PROXY|http_proxy|https_proxy|all_proxy|SSL_CERT_FILE|SSL_CERT_DIR|REQUESTS_CA_BUNDLE|CURL_CA_BUNDLE|AWS_CA_BUNDLE|NODE_EXTRA_CA_CERTS)}; do
    [[ $v == GOOGLE_CLOUD_HIPAA_PROJECT_ID || $v == OTEL_SDK_DISABLED ]] && continue
    print -ru2 -- "⛔ goose blocked: $v is set — it can redirect the provider, model, endpoint, config location, stream PHI traces to an OTLP collector, or route/decrypt PHI traffic through a proxy. Unset it and retry."
    return 1
  done

  # Competing-config guard: an unvetted config at goose's default XDG/Library
  # location is a file a non-gated entrypoint (or goose's path precedence) could
  # run instead of the locked one. Block until it's removed.
  local d
  for d in "$HOME/.config/goose/config.yaml" \
           "$HOME/Library/Application Support/Block/goose/config.yaml"; do
    if [[ -e $d ]]; then
      print -ru2 -- "⛔ goose blocked: an unvetted goose config exists at $d — a non-gated entrypoint could run it instead of the locked one. Remove it (trash \"$d\") and retry."
      return 1
    fi
  done

  # Refuse a declarative custom-providers dir under the pinned root: goose loads
  # OpenAI/Anthropic/Ollama-compatible providers with an arbitrary base_url from
  # $root/config/custom_providers/*.json. GOOSE_PROVIDER is pinned to
  # gcp_vertex_ai so none would be *selected*, but the checker never scans that
  # dir — refuse it outright so an off-Vertex provider definition can't sit in
  # the locked root at all (defense in depth for endpoint exclusivity).
  if [[ -d "$root/config/custom_providers" ]] && \
     [[ -n "$(ls -A "$root/config/custom_providers" 2>/dev/null)" ]]; then
    print -ru2 -- "⛔ goose blocked: $root/config/custom_providers is non-empty — a declarative provider there can define an off-Vertex base_url. Remove it."
    return 1
  fi

  # Refuse a sibling .env in the pinned config dir: goose auto-loads it into the
  # process environment, re-supplying any var refused above.
  if [[ -e "$root/config/.env" ]]; then
    print -ru2 -- "⛔ goose blocked: $root/config/.env exists — goose auto-loads it into the environment, re-supplying refused overrides. Remove it."
    return 1
  fi

  # ARG guard. Two CLI surfaces bypass the config lock, so both are refused
  # here (an allowlist-of-shape, not a denylist of specific flag names that
  # drifts as goose renames them):
  #   - ANY --with-* flag injects an extension/builtin (--with-extension,
  #     --with-streamable-http-extension, --with-builtin, …) — an outbound
  #     channel the config-level extension check never sees. Declare extensions
  #     in the locked config instead.
  #   - --provider / --model (on `goose run`) override the validated config at
  #     request time and can route PHI to a non-Vertex endpoint or a non-GA
  #     model. Change the model in the locked config, not on the CLI.
  #   - --recipe (on `goose run`) loads a recipe YAML (local file OR GitHub repo)
  #     whose `settings.goose_provider` / `goose_model` and `extensions:` OVERRIDE
  #     the locked config at execution time — the checker only validates
  #     config/config.yaml and never sees the recipe, so a recipe can route PHI
  #     to a non-Vertex provider/host or attach a remote MCP extension while the
  #     gate still prints ✓. Refuse it; put anything a recipe would carry into
  #     the locked config instead.
  local a
  for a in "$@"; do
    case "$a" in
      --with-*)
        print -ru2 -- "⛔ goose blocked: '$a' injects an ad-hoc MCP extension/builtin — an off-BAA egress path. Declare extensions in the locked config instead."
        return 1 ;;
      --provider|--provider=*|--model|--model=*)
        print -ru2 -- "⛔ goose blocked: '$a' overrides the validated provider/model at the CLI, bypassing the config lock (can route PHI off-Vertex or to a non-GA model). Change the locked config instead."
        return 1 ;;
      --recipe|--recipe=*)
        print -ru2 -- "⛔ goose blocked: '$a' loads a recipe whose settings/extensions override the locked config (unvalidated by the checker) — it can route PHI off-Vertex or attach a remote MCP extension. Put it in the locked config instead."
        return 1 ;;
    esac
  done

  # Validate the live config (at the pinned path); block on any violation.
  local report
  if ! report=$("$check" "$cfg" 2>&1); then
    print -ru2 -- "$report"
    print -ru2 -- "⛔ goose blocked: config is not HIPAA-locked (see above). Fix it in the dotfiles repo, deploy, then retry."
    return 1
  fi

  # Surface the ✓ attestation on every launch (stderr) — visible proof the gate
  # ran and passed, never a silent no-op.
  print -ru2 -- "$report"

  # Inject, exec-local: the pinned root (so goose reads the validated config),
  # the BAA project from the trusted source, telemetry-off (both the config flag
  # and the env kill-switch), and the OpenTelemetry kill-switch (goose's OTLP
  # tracer is a SEPARATE channel from PostHog and would otherwise export prompt/
  # response content — PHI — if any OTEL_EXPORTER_OTLP_ENDPOINT default applied).
  GOOSE_PATH_ROOT="$root" \
  GCP_PROJECT_ID="$GOOGLE_CLOUD_HIPAA_PROJECT_ID" \
  GOOSE_TELEMETRY_ENABLED=false \
  GOOSE_TELEMETRY_OFF=1 \
  OTEL_SDK_DISABLED=true \
    command goose "$@"
}
