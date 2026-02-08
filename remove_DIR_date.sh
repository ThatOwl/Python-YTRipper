#!/usr/bin/env bash

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
