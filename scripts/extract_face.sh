#!/usr/bin/env bash
# extract_face.sh <video> <work-dir> <vertical|landscape> <from> <to> [<from> <to> …]
#
# Writes the camera frames for each face shot to <work-dir>/face/fNNNNN.jpg, numbered by edit frame,
# so frame N of the edit shows frame N of the recording and voice and lips stay in sync.
set -euo pipefail

VIDEO="$1"
WORK="$2"
FORMAT="$3"
shift 3
FPS=30

[[ -f "$VIDEO" ]] || { echo "No such video: $VIDEO"; echo "Next: pass the to-camera recording the audio came from"; exit 1; }
case "$FORMAT" in
  vertical) WIDTH=1080; HEIGHT=1920 ;;
  landscape) WIDTH=1920; HEIGHT=1080 ;;
  *) echo "Unknown format: $FORMAT"; echo "Next: pass vertical or landscape"; exit 1 ;;
esac
if (( $# == 0 || $# % 2 != 0 )); then
  echo "Face ranges come in <from> <to> pairs, got $# value(s)"
  echo "Next: e.g. extract_face.sh take.mp4 work vertical 0 2.4 84.1 87.6"
  exit 1
fi
if ! ffprobe -v error -select_streams v:0 -show_entries stream=codec_type -of csv=p=0 "$VIDEO" | grep -q video; then
  echo "$VIDEO has no video stream"
  echo "Next: record to camera, or run the skill with audio only and no face shots"
  exit 1
fi

LENGTH=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$VIDEO")
labels=()
ranges=()

# Validate every pair before extracting any, so a bad sign-off range doesn't leave a half-written face/
while (( $# >= 2 )); do
  FROM="$1"; TO="$2"; shift 2
  RANGE=$(python3 - "$FROM" "$TO" "$LENGTH" "$FPS" <<'PY'
import math, sys
start, end, length, fps = (float(v) for v in sys.argv[1:])
if not 0 <= start < end:
    sys.exit(f"Face range {start}-{end} is empty or negative")
if end > length:
    sys.exit(f"Face range ends at {end}s but the recording is only {length:.2f}s")
first = math.floor(start * fps)
# renderAt rounds t*30, so the frame just before the shot's out point can be ceil(end*30)
last = min(math.ceil(end * fps), math.ceil(length * fps) - 1)
print(first, last - first + 1, f"{first / fps:.6f}")
PY
  ) || { echo "Next: end the face shot at or before the recording's length"; exit 1; }
  labels+=("${FROM}-${TO}s")
  ranges+=("$RANGE")
done

mkdir -p "$WORK/face"
started=$(date +%s)
expected=0

for i in "${!ranges[@]}"; do
  read -r FIRST COUNT SEEK <<< "${ranges[$i]}"
  ffmpeg -v error -y -ss "$SEEK" -i "$VIDEO" -an \
    -vf "fps=$FPS,scale=$WIDTH:$HEIGHT:force_original_aspect_ratio=increase,crop=$WIDTH:$HEIGHT,setsar=1" \
    -frames:v "$COUNT" -start_number "$FIRST" -q:v 3 "$WORK/face/f%05d.jpg"
  echo "face ${labels[$i]} → frames $FIRST…$(( FIRST + COUNT - 1 ))"
  expected=$(( expected + COUNT ))
done

written=$(find "$WORK/face" -name 'f*.jpg' -newermt "@$started" | wc -l)
echo "$written/$expected face frames → $WORK/face"
if (( written < expected )); then
  echo "Next: the recording ran out early; end the face shot sooner and re-run with the same pairs"
  exit 1
fi
echo "Next: author each face shot with faceCam(id, from, to) using the same times"
