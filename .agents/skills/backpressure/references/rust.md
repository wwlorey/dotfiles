# Rust backpressure

For a Rust workspace (root has `Cargo.toml` with `[workspace]`). Single-crate projects use the same commands without `--workspace`.

## Required gates

| Gate | Command | Notes |
|---|---|---|
| Build | `cargo build --workspace` | catches type errors and missing features |
| Test | `cargo test --workspace` | runs all unit + integration tests, skips `#[ignore]` |
| Lint | `cargo clippy --workspace -- -D warnings` | warnings as errors |
| Format | `cargo fmt --all` | rewrites in place; expect residue if you touched code |

Single-crate variants: drop `--workspace` and use `-p <crate>` to target one crate.

## Optional gates

| Gate | Command | When |
|---|---|---|
| Code coverage | `cargo llvm-cov --workspace` | when coverage signal matters; slow |
| Long-running tests | `cargo test --workspace -- --ignored` | for tests gated behind `#[ignore]` (slow / expensive) |
| Single test | `cargo test -p <crate> <test_name>` | iterating on one failure |

## Project wrappers

Before running the canonical commands, check `justfile` / `Makefile` for project-wrapped targets — projects often expose `just test`, `just check`, `just ci` that bundle backpressure. Use the wrapper if it exists.

## CLI E2E tests (Tuistory)

Some Rust crates run terminal-level e2e tests via [Tuistory](https://github.com/remorses/tuistory). Look for a `tests/cli_e2e.rs` file in the crate.

- All: `cargo test -p <crate> --test cli_e2e`
- One: `cargo test -p <crate> --test cli_e2e <test_name>`

## Gotchas

- **Default target.** Some crates have build flags that differ by OS (e.g. `metal` feature on macOS). Confirm the default build still works on the user's OS before claiming backpressure passed.
- **Newly authored slow tests.** If a new test is unreasonably slow, gate it behind `#[ignore]` and run via `cargo test -- --ignored` in a separate optional pass. Don't slow default backpressure.
- **Formatter residue is normal.** `cargo fmt` may touch files beyond your diff. Commit the residue separately so review stays clean.
