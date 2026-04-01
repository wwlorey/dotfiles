#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "Installing dependencies..."
cd "$SCRIPT_DIR"
pnpm install

echo "Registering MCP server with Claude Code (user scope)..."
claude mcp add --scope user unsandboxed-runner -- \
  npx --prefix "$HOME/.claude/mcp-servers/unsandboxed-runner" \
  tsx "$HOME/.claude/mcp-servers/unsandboxed-runner/src/index.ts"

echo "Done. Restart Claude Code to pick up the new MCP server."
