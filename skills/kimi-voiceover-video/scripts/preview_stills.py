#!/usr/bin/env python3
"""Render one representative still per shot and build a contact sheet for review.

  preview_stills.py <work-dir>

Reads shots.json, picks the hit-word moment when available, otherwise the shot
midpoint, renders those frames, and tiles them into a contact sheet. This lets
the user approve the visual direction before the expensive full render.
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent


def pick_timestamp(shot: dict, words: list) -> float:
    """Best preview timestamp for a shot: hit word if we can find it, else midpoint."""
    hit = shot.get("hit_word", "").strip().rstrip(".,!?;:").lower()
    start = float(shot.get("in", 0))
    end = float(shot.get("out", start + 1))
    if hit and words:
        for w in words:
            if w.get("word", "").strip().rstrip(".,!?;:").lower() == hit:
                t = float(w.get("start", (start + end) / 2))
                if start <= t <= end:
                    return t
    return (start + end) / 2


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("work", type=Path)
    args = parser.parse_args()

    shots_path = args.work / "shots.json"
    if not shots_path.is_file():
        print(f"No shots.json in {args.work}", file=sys.stderr)
        print("Next: run plan_shots.py first", file=sys.stderr)
        return 1

    shots = json.loads(shots_path.read_text(encoding="utf-8"))
    if not shots:
        print("shots.json is empty", file=sys.stderr)
        return 1

    words_path = args.work / "words.json"
    words = json.loads(words_path.read_text(encoding="utf-8")) if words_path.is_file() else []

    times = [pick_timestamp(s, words) for s in shots]
    times_str = ",".join(f"{t:.3f}" for t in times)

    stills_dir = args.work / "stills"
    contact_path = args.work / "contact.jpg"
    stills_dir.mkdir(parents=True, exist_ok=True)

    index_html = args.work / "index.html"
    if not index_html.is_file():
        print(f"No index.html in {args.work}", file=sys.stderr)
        print("Next: run fill_template.py first", file=sys.stderr)
        return 1

    result = subprocess.run(
        ["node", str(SCRIPTS_DIR / "render.js"), "stills", str(index_html), str(stills_dir), times_str],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        print(result.stderr or result.stdout, file=sys.stderr)
        return result.returncode

    result = subprocess.run(
        ["bash", str(SCRIPTS_DIR / "contact-sheet.sh"), str(stills_dir), str(contact_path)],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        print(result.stderr or result.stdout, file=sys.stderr)
        return result.returncode

    print(f"{len(shots)} preview stills → {contact_path}")
    print("Next: review contact.jpg, then run render.js check or make_thumbnail.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
