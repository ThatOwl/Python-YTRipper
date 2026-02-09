#!/usr/bin/env bash
# execute in parent directory of music directories, will rename directories starting with "2026_02_" to remove the date prefix
prefix="2026_02_"

for d in */; do
  name="${d%/}"

  # Only act on directories starting with the prefix
  [[ "$name" == "$prefix"* ]] || continue

  # If name is exactly the prefix → error case
  if [[ "$name" == "$prefix" ]]; then
    mv -- "$name" "${prefix}MISSING NAME"
  else
    new_name="${name#$prefix}"
    mv -- "$name" "$new_name"
  fi
done
