#!/bin/bash

if [[ -z "$AGENT_ACTIVE" ]]; then
  echo "ERROR: Claude Code must be launched via the \`agent\` script. Please end this session and start a new session using the script." >&2
  exit 2
fi
exit 0
