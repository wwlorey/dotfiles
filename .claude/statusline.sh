#!/bin/sh
input=$(cat)
pct=$(echo "$input" | jq -r '.context_window.used_percentage // empty')
if [ -n "$pct" ]; then
  printf "🧠 %.0f%%" "$pct"
fi
