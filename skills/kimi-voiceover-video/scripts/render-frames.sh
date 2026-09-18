#!/usr/bin/env bash
# render-frames.sh <index.html> <frames-dir> <duration-seconds> [workers] [from-frame to-frame]
#
# Renders frames in parallel. Pass a frame range to re-render one shot after a fix.
set -euo pipefail

HTML="$1"
OUT="$2"
DURATION="$3"
WORKERS="${4:-10}"
FPS=30
SCRIPTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if ! [[ "$WORKERS" =~ ^[1-9][0-9]*$ ]]; then
  echo "workers must be a positive integer, got: $WORKERS"
  echo "Next: pass a positive integer like 8 or 10"
  exit 1
fi

TOTAL=$(python3 -c "import math; print(math.ceil($DURATION * $FPS))")
FROM="${5:-0}"
TO="${6:-$TOTAL}"

if ! [[ "$FROM" =~ ^[0-9]+$ ]] || ! [[ "$TO" =~ ^[0-9]+$ ]]; then
  echo "frame range must be non-negative integers, got: $FROM $TO"
  echo "Next: pass the range as two integer frame numbers"
  exit 1
fi
if (( FROM >= TO )); then
  echo "frame range must satisfy from < to, got: $FROM $TO"
  echo "Next: pass a valid range, or omit the range to render all frames"
  exit 1
fi

SPAN=$(( TO - FROM ))
STEP=$(( (SPAN + WORKERS - 1) / WORKERS ))

mkdir -p "$OUT"
started=$(date +%s)
pids=()
for (( i = 0; i < WORKERS; i++ )); do
  start=$(( FROM + i * STEP ))
  end=$(( start + STEP < TO ? start + STEP : TO ))
  (( start >= end )) && break
  # Bounds are separate arguments on purpose: a single quoted "a b" renders zero frames silently
  node "$SCRIPTS_DIR/render.js" frames "$HTML" "$OUT" "$start" "$end" &
  pids+=($!)
done

failed=0
for pid in "${pids[@]}"; do wait "$pid" || failed=$(( failed + 1 )); done

rendered=$(find "$OUT" -name 'f*.jpg' -newermt "@$started" | wc -l)
echo "$rendered/$SPAN frames rendered in $(( $(date +%s) - started ))s · $failed worker(s) failed"
if (( rendered < SPAN || failed > 0 )); then
  echo "Next: fix the first error printed above (PAGE ERROR = composition bug, Executable doesn't exist = run setup.sh), then re-run with the same range"
  exit 1
fi
echo "Next: run mix-encode.sh"
