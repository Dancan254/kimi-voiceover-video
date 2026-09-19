#!/usr/bin/env python3
"""Generate vertical and square thumbnail images from the best preview still.

  make_thumbnail.py <work-dir> [--source <jpg>] [--shots shots.json]

If no source is given, it renders the shot with the most words (or the first
shot) and scales/crops it to:
  - thumbnail_vertical.jpg  1080x1920
  - thumbnail_square.jpg    1080x1080

Both are saved in <work-dir>.
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent


def best_shot(shots: list) -> dict:
    """Pick the shot most likely to make a compelling thumbnail."""
    if not shots:
        return {}
    # Prefer shots with more words and a hit; fall back to the first shot
    def score(s):
        line = s.get("line", "")
        word_count = len(line.split()) if line else 0
        has_hit = 1 if s.get("hit_word") else 0
        # Slightly favour earlier shots so the thumbnail matches the hook
        position = shots.index(s)
        return (has_hit, word_count, -position)
    return max(shots, key=score)


def render_source(work: Path, shot: dict, words: list) -> Path:
    """Render a single still for the chosen shot and return its path."""
    hit = shot.get("hit_word", "").strip().rstrip(".,!?;:").lower()
    start = float(shot.get("in", 0))
    end = float(shot.get("out", start + 1))
    t = (start + end) / 2
    if hit and words:
        for w in words:
            if w.get("word", "").strip().rstrip(".,!?;:").lower() == hit:
                wt = float(w.get("start", t))
                if start <= wt <= end:
                    t = wt
                    break

    thumb_dir = work / "thumb_src"
    thumb_dir.mkdir(parents=True, exist_ok=True)
    index_html = work / "index.html"
    result = subprocess.run(
        ["node", str(SCRIPTS_DIR / "render.js"), "stills", str(index_html), str(thumb_dir), f"{t:.3f}"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        print(result.stderr or result.stdout, file=sys.stderr)
        sys.exit(result.returncode)

    files = sorted(thumb_dir.glob("t*.jpg"))
    if not files:
        print("Thumbnail render produced no files", file=sys.stderr)
        sys.exit(1)
    return files[0]


def make_thumbnails(src: Path, work: Path) -> tuple:
    """Create vertical and square thumbnails from a source JPG."""
    vertical = work / "thumbnail_vertical.jpg"
    square = work / "thumbnail_square.jpg"

    # Vertical: scale to fill 1080 width, crop to 1920 height from the centre
    subprocess.run([
        "ffmpeg", "-v", "error", "-y", "-i", str(src),
        "-vf", "scale=1080:-1,crop=1080:1920:(in_w-1080)/2:(in_h-1920)/2",
        "-frames:v", "1", "-q:v", "2", str(vertical),
    ], check=True)

    # Square: scale to cover 1080x1080 from the centre
    subprocess.run([
        "ffmpeg", "-v", "error", "-y", "-i", str(src),
        "-vf", "scale=1080:1080:force_original_aspect_ratio=increase,crop=1080:1080:(in_w-1080)/2:(in_h-1080)/2",
        "-frames:v", "1", "-q:v", "2", str(square),
    ], check=True)

    return vertical, square


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("work", type=Path)
    parser.add_argument("--source", type=Path, default=None, help="use an existing JPG instead of rendering")
    args = parser.parse_args()

    if args.source:
        src = args.source
        if not src.is_file():
            print(f"Source image not found: {src}", file=sys.stderr)
            return 1
    else:
        shots_path = args.work / "shots.json"
        if not shots_path.is_file():
            print(f"No shots.json in {args.work}", file=sys.stderr)
            print("Next: run plan_shots.py first", file=sys.stderr)
            return 1
        shots = json.loads(shots_path.read_text(encoding="utf-8"))
        words_path = args.work / "words.json"
        words = json.loads(words_path.read_text(encoding="utf-8")) if words_path.is_file() else []
        shot = best_shot(shots)
        src = render_source(args.work, shot, words)

    vertical, square = make_thumbnails(src, args.work)
    print(f"Thumbnails → {vertical} · {square}")
    print("Next: review them, or pass a better source still with --source")
    return 0


if __name__ == "__main__":
    sys.exit(main())
