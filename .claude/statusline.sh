#!/bin/sh
input=$(cat)
cwd=$(echo "$input" | jq -r '.cwd // empty')
pct=$(echo "$input" | jq -r '.context_window.used_percentage // empty')
parts=""
if [ -n "$cwd" ]; then
  parts="📍 $(basename "$cwd")"
fi
if [ -n "$pct" ]; then
  parts="$parts 🧠 $(printf '%.0f%%' "$pct")"
fi
printf '%s' "$parts"
