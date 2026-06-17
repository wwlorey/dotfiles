# Tauri backpressure

For Tauri desktop apps (root has `package.json` plus `src-tauri/Cargo.toml`). A Tauri app is a Rust backend + a frontend bundle, so this is a superset of both stacks.

## Required gates

Run the **frontend** gauntlet (`references/frontend.md`) and the **Rust** gauntlet (`references/rust.md`) for the `src-tauri/` crate, then add the Tauri-specific gates below.

| Gate | Command | Notes |
|---|---|---|
| Smoke test | `mcp__unsandboxed-runner__smoke_test_tauri` with `cwd: "<app-path>"` | validates the app boots without runtime panics; run after backend changes |
| Tauri build | `mcp__unsandboxed-runner__run_tauri_build` with `cwd: "<app-path>"` | full app build; slow, run when behavior may have shifted |

`<app-path>` is the path to the crate containing `src-tauri/`, e.g. `crates/lsr-app`.

## Sandbox / MCP notes

Tauri commands need windowing / GPU access that the sandbox blocks. **Always** use the `unsandboxed-runner` MCP wrappers:

| Bare command | MCP wrapper to use instead |
|---|---|
| `cargo tauri dev` | `smoke_test_tauri` (one-shot boot check) |
| `cargo tauri build` | `run_tauri_build` |
| `pnpm exec playwright` | `run_playwright` |

Bare invocations fail inside the sandbox and tempt `dangerouslyDisableSandbox` retries — don't go that route.

## Build targets

Tauri apps may have multiple build outputs:
- **Tauri desktop:** `run_tauri_build` MCP tool
- **Web build:** `pnpm run build` (also runs as part of the frontend gauntlet)
- **Mobile (Expo):** `pnpm run expo export --platform all` if the project has Expo

Run the targets the change actually affects. Don't gauntlet-build mobile if you only changed desktop UI.

## Order

1. Frontend gauntlet (typecheck, lint, build, unit tests, format)
2. Rust gauntlet for `src-tauri/` (build, test, clippy, fmt)
3. `smoke_test_tauri` to confirm the app boots
4. Optional: `run_tauri_build` for full distributable, `run_playwright` for e2e

## Gotchas

- **App-path matters.** Both MCP wrappers take `cwd` relative to the project root. Pass the directory containing `src-tauri/`, not the workspace root.
- **Long timeouts.** Tauri builds can run >5 minutes. `run_tauri_build` accepts `timeout_secs` up to 600.
- **Smoke ≠ build.** Smoke test boots the dev build to catch panics; full build produces the distributable. Smoke is cheap and frequent; build is expensive and rare.
