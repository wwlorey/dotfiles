#!/bin/sh
input=$(cat)
cwd=$(echo "$input" | jq -r '.cwd // empty')
pct=$(echo "$input" | jq -r '.context_window.used_percentage // empty')
model=$(echo "$input" | jq -r '.model.display_name // empty')
if dic-status -q; then
  parts="🔇"
else
  parts="🔈"
fi
if [ -n "$cwd" ]; then
  parts="$parts 📍 $(basename "$cwd")"
fi
if [ -n "$pct" ]; then
  parts="$parts 🧠 $(printf '%.0f%%' "$pct")"
fi
if [ -n "$model" ]; then
  parts="$parts · $model"
fi
printf '%s' "$parts"
