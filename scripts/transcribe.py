#!/usr/bin/env python3
"""Transcribe a voice recording locally with word-level timestamps.

Writes words.json (every word with start/end) and transcript.txt, one phrase per line as
`[start] word@time word@time …` — the per-word times are what shots are cut to.
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")


PHRASE_MAX_WORDS = 5


def probe_duration(audio: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(audio)],
        capture_output=True, text=True, check=True,
    )
    return float(out.stdout.strip())


def split_phrases(words):
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
    parser = argparse.ArgumentParser(description="Word-level transcription with faster-whisper (CPU).")
    parser.add_argument("audio", type=Path)
    parser.add_argument("--outdir", type=Path, required=True)
    parser.add_argument("--model", default="small", choices=["tiny", "base", "small", "medium"])
    parser.add_argument("--threads", type=int, default=8)
    parser.add_argument("--vocab", default="", help="comma-separated names and terms the speaker uses, to bias recognition")
    args = parser.parse_args()

    if not args.audio.is_file():
        print(f"No such audio file: {args.audio}", file=sys.stderr)
        print("Next: pass a path to an existing audio or video file", file=sys.stderr)
        return 1

    args.outdir.mkdir(parents=True, exist_ok=True)
    duration = probe_duration(args.audio)

    from faster_whisper import WhisperModel

    started = time.time()
    with tempfile.TemporaryDirectory() as tmp:
        wav = Path(tmp) / "audio.wav"
        subprocess.run(
            ["ffmpeg", "-y", "-v", "error", "-i", str(args.audio), "-vn", "-ac", "1", "-ar", "16000", str(wav)],
            check=True,
        )
        model = WhisperModel(args.model, device="cpu", compute_type="int8", cpu_threads=args.threads)
        segments, info = model.transcribe(
            str(wav), beam_size=5, word_timestamps=True, vad_filter=False,
            initial_prompt=args.vocab or None,
        )
        words = [
            {"t": w.word.strip(), "s": round(w.start, 2), "e": round(w.end, 2)}
            for segment in segments for w in (segment.words or []) if w.word.strip()
        ]
    elapsed = time.time() - started

    if not words:
        print("0 words — no speech detected.", file=sys.stderr)
        print(f"Next: check the audio with `ffplay {args.audio}`", file=sys.stderr)
        return 1

    words_path = args.outdir / "words.json"
    transcript_path = args.outdir / "transcript.txt"
    words_path.write_text(json.dumps(words), encoding="utf-8")
    phrases = split_phrases(words)
    with transcript_path.open("w", encoding="utf-8") as handle:
        for phrase in phrases:
            handle.write(f"[{phrase[0]['s']:.2f}] " + " ".join(f"{w['t']}@{w['s']:.2f}" for w in phrase) + "\n")

    print(
        f"Transcribed {duration:.1f}s → {len(words)} words · {len(phrases)} phrases · "
        f"lang={info.language} · {elapsed:.0f}s elapsed ({duration / elapsed:.1f}x realtime)"
    )
    print(f"  {words_path}")
    print(f"  {transcript_path}")
    print(f"Next: proofread {transcript_path.name}, write fixes.json, run build_captions.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
