---
name: asc
description: Driving App Store Connect through the official REST API — provisioning profiles, TestFlight (beta groups/testers/builds), in-app purchases, export-compliance, and build-processing waits — in ANY repo. Consult for any task that touches App Store Connect, TestFlight, provisioning profiles, IAP, or export compliance: creating or downloading a provisioning profile, listing bundle IDs, assigning a build to a beta group, adding/removing testers, declaring a build's encryption compliance, polling until a build finishes processing, or reading/creating IAP products. Brevity is not an exemption — even a one-off "just download the provisioning profile" or "is the build done processing yet" routes here.
---

# App Store Connect via the REST API

Use the bundled client at `scripts/asc` for every App Store Connect operation.
It authenticates with an ES256 JWT and calls
`https://api.appstoreconnect.apple.com`. Run `scripts/asc <command> --help` for
flags; run any command with `--dry-run` to print the exact request without
sending it.

## Capability-global, enforcement-project-local

This skill owns the HOW: JWT auth, the endpoint cookbook, the client
subcommands, and the safety rails. It hardcodes NO app-specific identifier.
Each project owns the WHEN: its justfile/specs invoke `asc` with that app's own
IDs (app id, bundle id, group ids). The sanctora consumer that wires these
commands into a release sequence is tracked at
`issues/asc-api-release-tooling-202607.md` (per-project; not part of this skill).

## Credentials

Resolution mirrors `scripts/mas-upload.sh`, so this composes with the existing
upload flow:

- **API key (.p8):** a single `AuthKey_<ID>.p8` under
  `~/.appstoreconnect/private_keys/`. The Key ID is auto-derived from the
  filename. `ASC_API_KEY_ID` overrides; `ASC_API_KEY_FILE` points at an explicit
  path; `ASC_PRIVATE_KEYS_DIR` overrides the directory. Zero or multiple keys is
  an error.
- **Issuer ID:** `ASC_ISSUER_ID` env > `ASC_ISSUER_FILE` env (a path) > a
  gitignored `.asc-issuer-id` sentinel searched from CWD upward. UUID-validated.

**App Manager role** on the key is sufficient for everything here.

When credentials are missing, run `scripts/asc setup`. It reports what resolves
and prints step-by-step instructions to create the key (App Store Connect >
Users and Access > Integrations > Keys > generate an App Manager key > download
the one-time `AuthKey_<ID>.p8` > place it under `~/.appstoreconnect/private_keys/`,
`chmod 600`) and to supply the Issuer ID. Every command that hits unresolvable
credentials points the user back at `asc setup` rather than dumping a trace.
Guide the user through `asc setup` instead of hand-waving.

## Secrets

Never print, echo, log, or paste the private key or the signed JWT. The client
redacts both (dry-run shows `Authorization: Bearer <redacted>`; `asc token`
prints the claims but not the token). Treat the JWT as a secret. When surfacing
a command for a human to run, show the `asc` invocation, never a raw token.

## Subcommand cookbook

Read-only / safe (run freely):

```
asc bundle-ids [--identifier co.example.app]
asc profiles list [--name <name>]
asc profiles download --name "<name>" [--out ~/Downloads/App.provisionprofile]
asc profiles download --id <profileId>
asc groups [--app <appId>]                 # TestFlight beta groups
asc testers list [--group <groupId>] [--email <addr>]
asc builds --app <appId> [--version <v>]   # includes processingState
asc build-wait --build <buildId> [--timeout 1800] [--interval 30]
asc iap list --app <appId>
asc iap status --id <iap> [--locale en-US] # state + completeness of {localization,price,availability,screenshot}
asc iap price-points --id <iap> [--territory USA] [--limit 100]   # pick a --tier for `iap price`
asc compliance --build <buildId> --exempt           # or --uses-encryption
asc token                                  # diagnostic: resolve creds + gen JWT
asc setup                                  # credential walkthrough
```

Create-draft (safe — produces unpublished/draft state):

```
asc profiles create --name "App MAS" --type MAC_APP_STORE \
    --bundle-id <bundleId> --certificate <certId> [--device <deviceId>...] \
    [--out ~/Downloads/App.provisionprofile]      # writes the .provisionprofile
asc iap create --app <appId> --name "Pro" --product-id co.x.pro \
    --type NON_CONSUMABLE [--review-note "..."]
asc iap update --id <iapId> [--name ...] [--review-note ...]
asc iap rename --id <iap> --name "<reference name>"          # internal name
asc iap localize --id <iap> --locale en-US --name "<display>" --description "<desc>"
asc iap price --id <iap> --tier <pricePointId> [--base-territory USA] [--start-date YYYY-MM-DD]
asc iap availability --id <iap> (--territory USA [...] | --all-territories) [--new-territories]
asc iap screenshot --id <iap> --file <path>   # upload the App Review screenshot (3-step reserve/upload/commit)
```

Completing a MISSING_METADATA in-app purchase so StoreKit will return it takes
four edits — a localization, a price, an availability, and the App Review
screenshot. Discover the state and what's still incomplete with
`asc iap status --id <iap>`; it reads INTO each relationship and reports the
real gap (price `MISSING (empty schedule)` when the schedule has no manual
price, localization `INCOMPLETE` when the locale lacks a name or description,
`screenshot: MISSING` — the usual final READY_TO_SUBMIT blocker), not mere
existence. Pick a price point with `asc iap price-points --id <iap>` (the
point's `id` is the `--tier` value). `iap localize` creates the localization,
or PATCHes the existing one if that locale already has one. `iap price` sets the
base/manual price schedule from a single price point (effective immediately
unless `--start-date` is given). `iap availability` sets the territories; a
single request covers up to 50, and `--all-territories` fetches the full
territory list and adds the rest in chunks. `iap screenshot` uploads the App
Review screenshot via Apple's 3-step reserved-asset flow: it POSTs a reservation
(`inAppPurchaseAppStoreReviewScreenshots`, with `fileName`/`fileSize` related to
the IAP), PUTs the bytes to each returned `uploadOperations` url with its
headers, then PATCHes the reservation with `uploaded: true` and the file's md5
`sourceFileChecksum`. `--dry-run` prints the reservation request without
sending.

`profiles create`/`download` decode the base64 `profileContent` and write a
`.provisionprofile` file (default `~/Downloads/<name>.provisionprofile`).
`profileType` values: `MAC_APP_STORE`, `MAC_APP_DIRECT`, `IOS_APP_STORE`,
`IOS_APP_DEVELOPMENT`, `IOS_APP_ADHOC`, and the rest of Apple's set.
`inAppPurchaseType` values: `CONSUMABLE`, `NON_CONSUMABLE`,
`NON_RENEWING_SUBSCRIPTION`.

Export compliance: `asc compliance --build <id> --exempt` sets
`usesNonExemptEncryption=false` on the build (the common "resolve Missing
Compliance" answer); `--uses-encryption` sets it true. This is SAFE on an
unreleased build.

## Destructive / production ops — HARD gate

Some ops mutate production state or delete data. They are gated in two layers.
Two are **unconditional** — always production:

| op | what it does | why gated |
|----|--------------|-----------|
| `testers-remove` | `DELETE /v1/betaTesters/{id}` | deletes data |
| `build-assign` | assigns a build to beta groups | distributes the build to real testers |

Four are **state-dependent** — SAFE on a draft in-app purchase, destructive on
a live one:

| op | what it does | gated only when |
|----|--------------|-----------------|
| `iap-rename` | PATCH the reference name (`iap rename`, or `iap update --name`) | the IAP is live/approved |
| `iap-price` | set the price schedule (`iap price`) | the IAP is live/approved |
| `iap-availability` | set territory availability (`iap availability`) | the IAP is live/approved |
| `iap-screenshot` | upload the App Review screenshot (`iap screenshot`) | the IAP is live/approved |

An in-app purchase in state `MISSING_METADATA` or `READY_TO_SUBMIT` has never
been approved — it is a **draft**, and editing its name/price/availability or
uploading its review screenshot is safe, so those ops run freely (no flag). Any
other state means the product has
been submitted/approved and changes reach real, possibly paying users; the
client reads the IAP's `state` before each of these ops and, when it is not a
draft (or the state can't be read — fail safe), refuses unless
`--approve-destructive=<op>` names the op. Setting the **localization** (display
name + description) via `iap localize` is a normal metadata edit, not a
price/availability change, and is never gated.

Everything else above is SAFE (all reads/lists including `iap status` and
`iap price-points`, downloading a profile, creating a draft profile/IAP,
localizing an IAP, editing a draft IAP's price/availability, uploading a draft
IAP's review screenshot, declaring export-compliance on an unreleased build).
Beyond this client, treat as
destructive/production anything that deletes or expires a build, removes a
build from a group, deletes a tester or profile, submits a version for review,
or changes the price/availability of a live product.

**Layer 1 — client refusal.** `asc testers remove` / `asc build-assign` exit
non-zero and refuse unless `--approve-destructive=<op>` names the exact op
(e.g. `--approve-destructive=testers-remove`). The state-dependent `iap`
ops refuse the same way, but only after reading the IAP's `state` and finding
it is not a draft. `--dry-run` always previews without the flag.

**Layer 2 — PreToolUse hook (agent hard-block).** A `PreToolUse` Bash hook
denies the AGENT from executing any gated op — the capability provided is
"block a matching agent Bash tool call before it runs" (a vendor primitive;
a port swaps only the hook mechanism). The agent must NEVER self-approve. For a
destructive op the agent: classifies it, prepares the exact `asc ... --approve-destructive=<op>`
command, and hands it to the USER to run. A user-initiated run (a `!`-prefixed
command the user types, or the user running it manually) is not an agent tool
call and bypasses the PreToolUse hook — the user running it IS the approval, and
the `--approve-destructive` flag serves that manual run.

So: only pass `--approve-destructive` after the user has approved that exact
action in their own words — and expect the agent-side execution to be blocked
regardless, by design. Present the command; let the user run it.

## Boundary: creating a new app record is UI-only

Apple's official REST API does NOT expose creating a new app record (the App
Store Connect app "shell"). Do that once in the App Store Connect web UI.
`fastlane spaceship` drives the private/unofficial endpoints that can create an
app record, but it is brittle and deliberately OUT OF SCOPE here. Everything
after the app record exists — profiles, IAP, TestFlight, builds, compliance —
is covered by this client.

## Error handling

The client surfaces Apple's error JSON (`errors[].detail`) with HTTP status,
not a stack trace. On credential failure it points at `asc setup`.
