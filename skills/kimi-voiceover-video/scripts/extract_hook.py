#!/usr/bin/env python3
"""Find the best 30–90 second segment of a recording for a Short.

  extract_hook.py <work-dir> <audio> [--target 60] [--min 30] [--max 90]

Scores overlapping windows by word density, energetic punctuation, proper nouns/numbers,
and optional audio RMS energy, then picks the highest-scoring contiguous segment.
Writes hook.json with start, end, score and reason.
"""

import argparse
import json
import math
import re
import subprocess
import sys
from pathlib import Path

WINDOW = 5.0
YEAR_RE = re.compile(r"\b19\d{2}\b|\b20\d{2}\b")


def load_words(work: Path):
    words_path = work / "words.json"
    if not words_path.is_file():
        print(f"No words.json in {work}", file=sys.stderr)
        print("Next: run transcribe.py first", file=sys.stderr)
        sys.exit(1)
    return json.loads(words_path.read_text(encoding="utf-8"))


def rms_energy(audio: Path, window: float = WINDOW):
    """Return list of (center_time, db) for each window, or None if ffmpeg fails."""
    try:
        out = subprocess.run(
            [
                "ffmpeg", "-y", "-v", "error", "-i", str(audio),
                "-af", f"astats=metadata=1:reset_count=1,ametadata=print:key=lavfi.astats.Overall.RMS_level",
                "-f", "null", "-"
            ],
            capture_output=True, text=True, timeout=120,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None

    values = []
    for line in out.stderr.splitlines():
        if "RMS_level" in line:
            try:
                db = float(line.split("=")[-1].strip().replace(" dB", ""))
                values.append(db)
            except ValueError:
                pass

    if not values:
        return None

    duration = float(subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(audio)],
        capture_output=True, text=True, check=True,
    ).stdout.strip())

    step = duration / len(values)
    return [(i * step + step / 2, db) for i, db in enumerate(values)]


def score_window(words, energy=None):
    """Score a list of words in a single window. Higher is better."""
    if not words:
        return 0.0

    text = " ".join(w["t"] for w in words)
    duration = words[-1]["e"] - words[0]["s"]
    if duration <= 0:
        return 0.0

    word_count = len(words)
    density = word_count / duration

    score = density * 8

    # Energetic punctuation
    score += text.count("!") * 2
    score += text.count("?") * 1.5

    # Proper nouns / numbers / years
    for w in words:
        t = w["t"].strip(".,!?;:")
        if YEAR_RE.match(t):
            score += 3
        elif t and t[0].isupper() and len(t) > 2:
            score += 1.5
        elif t.isdigit():
            score += 1

    # Audio energy boost
    if energy:
        mid = (words[0]["s"] + words[-1]["e"]) / 2
        db = next((db for t, db in energy if t >= mid), energy[-1][1] if energy else -60)
        if db != float("-inf"):
            score += max(0, (db + 40) / 10)

    return round(score, 2)


def find_best_segment(words, target: float, min_len: float, max_len: float, energy=None):
    """Find the contiguous segment of length ~target with the highest average window score."""
    if not words:
        return None

    # Build 5s window scores aligned every 1s
    start_time = words[0]["s"]
    end_time = words[-1]["e"]
    total = end_time - start_time
    if total < min_len:
        return {"start": start_time, "end": end_time, "score": 0, "reason": "recording shorter than min hook length"}

    # Precompute word index lookup by time
    def words_between(t0, t1):
        return [w for w in words if w["s"] >= t0 and w["e"] <= t1]

    # Sliding windows every 1s
    window_scores = []
    t = start_time
    while t + WINDOW <= end_time:
        ws = words_between(t, t + WINDOW)
        window_scores.append((t, score_window(ws, energy)))
        t += 1.0

    if not window_scores:
        return {"start": start_time, "end": min(end_time, start_time + target), "score": 0, "reason": "no windows to score"}

    # Try target, min, max lengths and pick best average score
    best = None
    for length in {target, min_len, max_len, (min_len + max_len) / 2}:
        for start, _ in window_scores:
            if start + length > end_time:
                continue
            included = [(t, s) for t, s in window_scores if start <= t <= start + length - WINDOW]
            if not included:
                continue
            avg = sum(s for _, s in included) / len(included)
            if best is None or avg > best["score"]:
                best = {
                    "start": round(start, 2),
                    "end": round(min(start + length, end_time), 2),
                    "score": round(avg, 2),
                    "length": round(length, 2),
                    "reason": f"highest average window score over {round(length, 0):.0f}s",
                }

    if best is None:
        return {"start": start_time, "end": end_time, "score": 0, "reason": "fallback to full recording"}

    return best


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("work", type=Path)
    parser.add_argument("audio", type=Path)
    parser.add_argument("--target", type=float, default=60.0, help="target hook length in seconds")
    parser.add_argument("--min", dest="min_len", type=float, default=30.0, help="minimum hook length")
    parser.add_argument("--max", dest="max_len", type=float, default=90.0, help="maximum hook length")
    parser.add_argument("--no-energy", action="store_true", help="skip ffmpeg RMS energy scoring")
    args = parser.parse_args()

    if not args.audio.is_file():
        print(f"No such audio file: {args.audio}", file=sys.stderr)
        return 1

    words = load_words(args.work)
    if not words:
        print("0 words — nothing to extract.", file=sys.stderr)
        return 1

    energy = None if args.no_energy else rms_energy(args.audio)

    hook = find_best_segment(words, args.target, args.min_len, args.max_len, energy)
    hook_path = args.work / "hook.json"
    hook_path.write_text(json.dumps(hook, indent=2) + "\n", encoding="utf-8")

    print(f"Hook {hook['start']:.1f}s–{hook['end']:.1f}s · score {hook['score']:.1f} · {hook['reason']} → {hook_path}")
    print("Next: run plan_shots.py, which will plan shots inside the hook window")
    return 0


if __name__ == "__main__":
    sys.exit(main())
