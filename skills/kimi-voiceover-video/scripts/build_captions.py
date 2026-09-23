#!/usr/bin/env python3
"""Apply fixes.json to words.json and write words.js for the caption engine.

fixes.json maps a raw transcribed token to its correction; an empty string drops the token.
keywords.json is an optional array of key nouns; matching words are flagged "k":1 so the
caption engine renders them in the brand accent. Timestamps are never touched.
"""

import json
import string
import sys
from pathlib import Path

PHRASE_MAX_WORDS = 5


def bare(token: str) -> str:
    return token.strip(string.punctuation).lower()


def split_phrases(words):
    """Group words into caption phrases. Mirrors transcribe.split_phrases."""
    phrases, current = [], []
    for word in words:
        current.append(word)
        if len(current) >= PHRASE_MAX_WORDS or word["t"][-1] in ".,?!":
            phrases.append(current)
            current = []
    if current:
        phrases.append(current)
    return phrases


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: build_captions.py <work-dir>", file=sys.stderr)
        return 1

    work = Path(sys.argv[1])
    words_path = work / "words.json"
    if not words_path.is_file():
        print(f"No words.json in {work}", file=sys.stderr)
        print("Next: run transcribe.py with --outdir pointing at this directory", file=sys.stderr)
        return 1

    fixes_path = work / "fixes.json"
    if fixes_path.is_file():
        try:
            fixes = json.loads(fixes_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            print(f"{fixes_path} is not valid JSON: {e}", file=sys.stderr)
            print("Next: fix the JSON syntax, then re-run build_captions.py", file=sys.stderr)
            return 1
    else:
        fixes = {}
    words = json.loads(words_path.read_text(encoding="utf-8"))

    applied = 0
    fixed = []
    for word in words:
        replacement = fixes.get(word["t"], word["t"])
        if replacement != word["t"]:
            applied += 1
        if replacement:
            fixed.append({**word, "t": replacement})

    seen = {w["t"] for w in words}
    unused = [token for token in fixes if token not in seen]

    keywords_path = work / "keywords.json"
    keywords = []
    if keywords_path.is_file():
        try:
            keywords = json.loads(keywords_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            print(f"{keywords_path} is not valid JSON: {e}", file=sys.stderr)
            print("Next: fix the JSON syntax, then re-run build_captions.py", file=sys.stderr)
            return 1
        if not isinstance(keywords, list):
            print(f"{keywords_path} must be a JSON array of words, e.g. [\"Java\", \"Kubernetes\"]", file=sys.stderr)
            print("Next: rewrite keywords.json as an array, then re-run build_captions.py", file=sys.stderr)
            return 1
    wanted = {bare(k) for k in keywords if bare(k)}
    marked = 0
    for word in fixed:
        if bare(word["t"]) in wanted:
            word["k"] = 1
            marked += 1
    missed = sorted(k for k in keywords if bare(k) and bare(k) not in {bare(w["t"]) for w in fixed})

    phrases = split_phrases(fixed)
    (work / "words.js").write_text("window.PHRASES=" + json.dumps(phrases) + ";", encoding="utf-8")

    print(f"{len(fixed)} words · {len(phrases)} phrases · {applied} fixes applied · {marked} keywords flagged")
    if unused:
        print(f"  unmatched fixes: {', '.join(unused)} — tokens must match transcript.txt exactly, punctuation included")
    if missed:
        print(f"  unmatched keywords: {', '.join(missed)} — match is case-insensitive, punctuation ignored")
    print(f"Next: write the shot list (load references/scene-blocks.md)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
