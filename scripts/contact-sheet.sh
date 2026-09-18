#!/usr/bin/env bash
# contact-sheet.sh <stills-dir> <out.jpg> — tile every still, in time order, into one image to review
set -euo pipefail

STILLS="$1"
OUT="$2"
COUNT=$(find "$STILLS" -name 't*.jpg' | wc -l)

if (( COUNT == 0 )); then
  echo "No stills in $STILLS"
  echo "Next: run render.js stills first"
  exit 1
fi

COLUMNS=$(( COUNT < 8 ? COUNT : 8 ))
ROWS=$(( (COUNT + COLUMNS - 1) / COLUMNS ))
ffmpeg -v error -y -pattern_type glob -i "$STILLS/t*.jpg" \
  -vf "scale=270:-1,tile=${COLUMNS}x${ROWS}:padding=6:color=black" -frames:v 1 "$OUT"
echo "$COUNT stills → $OUT (${COLUMNS}x${ROWS}, left-to-right in time order)"
echo "Next: read $OUT and check every shot for clipping and caption collisions"
