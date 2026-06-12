#!/bin/bash

if [[ -z "$AGENT_WRAPPER_ACTIVE" ]]; then
  echo "ERROR: Claude Code must be launched via the wrapper script (`agent`). Please end this session and start a new session using the wrapper." >&2
  exit 2
fi
exit 0
