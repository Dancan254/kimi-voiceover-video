#!/usr/bin/env bash
# setup-all.sh — one-command setup for the kimi-voiceover-video skill.
# Runs dependency/asset setup, then checks for a brand file and guides next steps.
set -euo pipefail

SCRIPTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(dirname "$SCRIPTS_DIR")"

echo "== Kimi Voiceover Video setup =="

bash "$SCRIPTS_DIR/setup.sh" "$@"

for brand in "./brand.json" "$HOME/.config/kimi-voiceover-video/brand.json" "$SKILL_DIR/brand.example.json"; do
  if [[ -f "$brand" ]]; then
    echo "Brand file found: $brand"
    echo "Setup complete. Start a new conversation and say: make a video out of ~/path/to/audio.m4a"
    exit 0
  fi
done

echo "No brand file found. Create one with:"
echo "  python3 $SCRIPTS_DIR/init_brand.py --handle @yourhandle --preset kimi-violet"
exit 0
