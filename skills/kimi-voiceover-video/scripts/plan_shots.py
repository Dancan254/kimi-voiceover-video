#!/usr/bin/env python3
"""Draft a shot list from a proofread transcript.

  plan_shots.py <work-dir>

Reads words.json and transcript.txt, segments speech into 1-4 second shot windows,
classifies each window into a scene block, and writes shots.json. The agent reviews
and refines the draft before authoring the composition.
"""

import json
import re
import sys
from pathlib import Path

SHOT_MIN = 1.0
SHOT_MAX = 4.0
SHOT_TARGET = 2.5

BLOCKS = {
    "terminal": ["terminal", "command", "error", "segmentation", "core dumped", "$ ", "git ", "npm ", "docker ", "python ", "make"],
    "counter": ["year", "years", "percent", "%", "million", "billion", "thousand", "downloads", "users"],
    "strike-through": ["wasn't", "not ", "never ", "no ", "wrong", "myth", "not built", "not designed"],
    "montage": ["everywhere", "across", "around the world", "list of", "stack", "layers"],
    "vhs": ["back in", "back then", "199", "198", "197", "retro", "old days", "vintage"],
    "outro": ["follow", "subscribe", "like this", "next time", "in summary", "to sum up", "the bottom line"],
}

TERMINAL_RE = re.compile(r"\$\s|git\s|npm\s|docker\s|python\s|make\s|gcc\s|error|segmentation|core dumped", re.I)
YEAR_RE = re.compile(r"\b19\d{2}\b|\b20\d{2}\b")
NUMBER_RE = re.compile(r"\b\d+%?\b|\b\d+\.\d+\b")


def load_words(work: Path):
    words_path = work / "words.json"
    if not words_path.is_file():
        print(f"No words.json in {work}", file=sys.stderr)
        print("Next: run transcribe.py with --outdir pointing at this directory", file=sys.stderr)
        sys.exit(1)
    return json.loads(words_path.read_text(encoding="utf-8"))


def build_windows(words):
    """Group words into shot windows: target ~2.5s, cut on punctuation or when max is reached."""
    windows, current = [], []
    start = words[0]["s"] if words else 0.0

    def flush():
        nonlocal current, start
        if not current:
            return
        windows.append({
            "words": current,
            "s": start,
            "e": current[-1]["e"],
        })
        current = []
        start = None

    for w in words:
        if start is None:
            start = w["s"]
        current.append(w)
        duration = w["e"] - start
        ends_sentence = w["t"][-1] in ".!?" if w["t"] else False
        ends_phrase = w["t"][-1] in ",;:" if w["t"] else False

        if ends_sentence and duration >= SHOT_MIN:
            flush()
        elif ends_phrase and duration >= SHOT_TARGET:
            flush()
        elif duration >= SHOT_MAX:
            flush()

    flush()
    return windows


def join_line(words):
    return " ".join(w["t"] for w in words)


def has_prominent_noun(words):
    """True if there is a capitalised word that looks like a name/topic (length > 3)."""
    return any(len(w["t"].strip(".,!?;:")) > 3 and w["t"][0].isupper() for w in words if w["t"])


def classify(line_lower: str, words):
    text = line_lower

    # Terminal takes precedence: code/errors are unmistakable visual beats
    if TERMINAL_RE.search(text):
        return "terminal"

    # Historical year
    if any(kw in text for kw in BLOCKS["vhs"]) or YEAR_RE.search(text):
        return "vhs" if ("back in" in text or "back then" in text or "old days" in text) else "counter"

    # Counter keywords without an explicit year
    if any(kw in text for kw in BLOCKS["counter"]):
        return "counter"

    # Strike-through with a clear topic -> slam + strike
    if any(kw in text for kw in BLOCKS["strike-through"]):
        if has_prominent_noun(words):
            return "kinetic-slam + strike-through"
        return "strike-through"

    if any(kw in text for kw in BLOCKS["montage"]):
        return "montage"

    if any(kw in text for kw in BLOCKS["outro"]):
        return "outro"

    # Short, punchy line with one key noun -> kinetic slam; longer explanatory -> highlight-box
    word_count = len(words)
    if word_count <= 6 and has_prominent_noun(words):
        return "kinetic-slam"
    return "highlight-box"


def pick_hit_word(words, block: str, line_lower: str):
    """Pick the one word in the window that deserves a hit."""
    candidates = []
    preceding = ""
    for i, w in enumerate(words):
        t = w["t"].strip(".,!?;:")
        lower = t.lower()
        if not t:
            continue

        score = 0
        if YEAR_RE.match(t):
            score = 12
        elif t[0].isupper() and len(t) > 2:
            # Longer proper nouns score higher; skip sentence-initial short words like "Did"
            score = 7 + min(len(t), 8)
            if preceding in ("know", "is", "was", "built", "designed", "called", "named"):
                score += 4
        elif NUMBER_RE.match(t):
            score = 6
        elif lower in ("never", "wrong", "myth", "finally", "boom", "yes", "no"):
            score = 5

        if score:
            candidates.append((w["s"], t, score))
        preceding = lower

    if candidates:
        return max(candidates, key=lambda x: x[2])[1]

    # Fallback: last content word
    for w in reversed(words):
        t = w["t"].strip(".,!?;:")
        if t and t.lower() not in ("the", "a", "an", "and", "or", "but", "for", "of", "in", "on", "to", "is", "was", "it"):
            return t
    return words[-1]["t"] if words else ""


def pick_transition(prev_block, block, index):
    if index == 0:
        return ""
    if block in ("vhs", "outro"):
        return "zoom"
    if prev_block == block and index % 3 == 0:
        return "whip"
    if block in ("terminal", "counter"):
        return "zoom"
    return "whip"


def image_query(line_lower: str, block: str, hit_word: str):
    if block == "terminal":
        return "computer terminal code screen"
    if block == "counter":
        return f"{hit_word} technology history" if hit_word else "technology history"
    if block == "vhs":
        return "retro computer 1990s technology"
    if block == "outro":
        return ""
    if hit_word and len(hit_word) > 2 and hit_word[0].isupper():
        return hit_word
    # Try to pull the first capitalised noun from the line as a fallback
    for word in line_lower.split():
        t = word.strip(".,!?;:")
        if len(t) > 3 and t[0].isupper():
            return t
    return line_lower.strip(".,!?;:")[:40]


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: plan_shots.py <work-dir>", file=sys.stderr)
        return 1

    work = Path(sys.argv[1])
    words = load_words(work)
    if not words:
        print("0 words — nothing to plan.", file=sys.stderr)
        return 1

    windows = build_windows(words)
    shots = []
    for i, win in enumerate(windows, start=1):
        line = join_line(win["words"])
        line_lower = line.lower()
        block = classify(line_lower, win["words"])
        hit = pick_hit_word(win["words"], block, line_lower)
        transition = pick_transition(shots[-1]["block"] if shots else None, block, i)
        query = image_query(line_lower, block, hit)

        shots.append({
            "id": f"s{i:02d}",
            "in": round(win["s"], 2),
            "out": round(win["e"], 2),
            "line": line,
            "block": block,
            "hit_word": hit,
            "transition": transition,
            "image_query": query,
            "nocap": any(b in block for b in ("kinetic-slam", "strike-through", "counter", "terminal", "stacked-slams", "outro")),
        })

    shots_path = work / "shots.json"
    shots_path.write_text(json.dumps(shots, indent=2) + "\n", encoding="utf-8")

    print(f"Planned {len(shots)} shots from {words[0]['s']:.2f}s to {words[-1]['e']:.2f}s → {shots_path}")
    print("Next: review shots.json, refine the table, then source images")
    return 0


if __name__ == "__main__":
    sys.exit(main())
