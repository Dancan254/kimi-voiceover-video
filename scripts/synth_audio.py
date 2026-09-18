#!/usr/bin/env python3
"""Synthesize the sound design for a composition.

  synth_audio.py <cues.json> <duration> <work-dir> [--drop T] [--quiet A:B] [--no-music]

Writes sfx.wav (every cue the timeline pushed) and music.wav (an 88 bpm pad, sub bass and
plucks, drums from --drums-from onward). Everything is generated here, so there is nothing
to license.
"""

import argparse
import json
import sys
import wave
from pathlib import Path

import numpy as np

SR = 48000
rng = np.random.default_rng(7)


def t_axis(seconds):
    return np.arange(int(SR * seconds)) / SR


def smooth(x, width):
    return np.convolve(x, np.ones(width) / width, mode="same")


def envelope(n, attack, release):
    env = np.ones(n)
    a, r = max(1, int(SR * attack)), max(1, int(SR * release))
    env[:a] = np.linspace(0, 1, a)
    env[-r:] *= np.exp(-np.linspace(0, 6, r))
    return env


def note(midi):
    return 440.0 * 2 ** ((midi - 69) / 12)


def place(buffer, sound, at):
    start = int(at * SR)
    if start < 0:
        sound, start = sound[-start:], 0
    if start >= len(buffer):
        return
    end = min(len(buffer), start + len(sound))
    buffer[start:end] += sound[: end - start]


def hit(power):
    t = t_axis(0.9)
    body = np.sin(2 * np.pi * np.cumsum(38 + 90 * np.exp(-t * 28)) / SR) * np.exp(-t * 5.5)
    click = rng.standard_normal(len(t)) * np.exp(-t * 60) * 0.5
    boom = smooth(rng.standard_normal(len(t)), 40) * np.exp(-t * 3) * 0.6
    return (body * 0.9 + click + boom) * 0.55 * power


def whoosh():
    t = t_axis(0.45)
    noise = rng.standard_normal(len(t))
    return (smooth(noise, 6) - smooth(noise, 60)) * np.sin(np.pi * t / t[-1]) ** 2 * 0.35


def riser(duration):
    t = t_axis(duration)
    k = t / duration
    noise = rng.standard_normal(len(t))
    tone = np.sin(2 * np.pi * np.cumsum(180 + 900 * k ** 2) / SR)
    return ((noise - smooth(noise, 45)) * 0.12 + tone * 0.08) * k ** 2


def down(duration):
    t = t_axis(duration)
    k = t / duration
    tone = np.sin(2 * np.pi * np.cumsum(700 * (1 - k) + 60) / SR)
    return tone * 0.12 * (1 - k) * np.sin(np.pi * np.minimum(k * 8, 1) / 2)


def repeated(sound, duration, interval, jitter):
    out = np.zeros(int(SR * duration) + SR // 10)
    position = 0.0
    while position < duration:
        place(out, sound() * (0.6 + 0.4 * rng.random()), position)
        position += interval + jitter * rng.random()
    return out


def key_click():
    t = t_axis(0.03)
    return rng.standard_normal(len(t)) * np.exp(-t * 250) * 0.12


def tick():
    t = t_axis(0.04)
    return np.sin(2 * np.pi * 2400 * t) * np.exp(-t * 120) * 0.08


def pop():
    t = t_axis(0.12)
    return np.sin(2 * np.pi * np.cumsum(500 + 900 * np.exp(-t * 40)) / SR) * np.exp(-t * 35) * 0.12


def ding():
    t = t_axis(0.6)
    return (np.sin(2 * np.pi * 1318 * t) + 0.5 * np.sin(2 * np.pi * 1975 * t)) * np.exp(-t * 8) * 0.07


def stamp():
    t = t_axis(0.35)
    return smooth(rng.standard_normal(len(t)), 25) * np.exp(-t * 18) * 0.9


def error():
    t = t_axis(0.22)
    return np.sign(np.sin(2 * np.pi * 180 * t)) * np.exp(-t * 14) * 0.05


def build_sfx(cues, samples):
    sfx = np.zeros(samples)
    unknown = set()
    for cue in cues:
        kind, at, duration = cue["type"], cue["t"], cue.get("dur", 0)
        if kind == "hit":
            place(sfx, hit(cue.get("power", 1)), at)
        elif kind == "whoosh":
            place(sfx, whoosh(), at)
        elif kind == "riser":
            place(sfx, riser(duration), at)
        elif kind == "down":
            place(sfx, down(duration), at)
        elif kind == "type":
            if duration > 0.05:
                place(sfx, repeated(key_click, duration, 0.055, 0.04), at)
        elif kind == "tick":
            place(sfx, repeated(tick, duration, 0.07, 0), at)
        elif kind == "pop":
            place(sfx, pop(), at)
        elif kind == "ding":
            place(sfx, ding(), at)
        elif kind == "stamp":
            place(sfx, stamp(), at)
        elif kind == "error":
            place(sfx, error(), at)
        else:
            unknown.add(kind)
    return sfx, unknown


def build_music(duration, samples, drums_from, drop, quiet):
    beat = 60 / 88
    bar = beat * 4
    chords = [[57, 60, 64], [53, 57, 60], [48, 52, 55], [55, 59, 62]]
    bass = [45, 41, 36, 43]
    music = np.zeros(samples)
    for b in range(int(duration / bar) + 2):
        start = b * bar
        chord = chords[b % 4]
        pad_t = t_axis(bar + 0.5)
        pad = sum(
            np.sin(2 * np.pi * note(m) * 2 ** (d / 12) * pad_t) + 0.3 * np.sin(4 * np.pi * note(m) * 2 ** (d / 12) * pad_t)
            for m in chord for d in (-0.12, 0.0, 0.12)
        ) / 9
        place(music, pad * envelope(len(pad_t), 0.6, 0.8) * 0.16, start)
        bass_t = t_axis(bar)
        place(music, np.sin(2 * np.pi * note(bass[b % 4]) * bass_t) * envelope(len(bass_t), 0.05, 0.4) * 0.14, start)
        for i in range(8):
            pluck_t = t_axis(0.25)
            place(music, np.sin(2 * np.pi * note(chord[(i * 2) % 3] + 12) * pluck_t) * np.exp(-pluck_t * 14) * 0.05, start + i * beat / 2)
        if drums_from is not None and start >= drums_from:
            for i in range(4):
                kick_t = t_axis(0.3)
                place(music, np.sin(2 * np.pi * np.cumsum(50 + 120 * np.exp(-kick_t * 30)) / SR) * np.exp(-kick_t * 9) * 0.2, start + i * beat)
                hat_t = t_axis(0.05)
                hat = rng.standard_normal(len(hat_t))
                place(music, (hat - smooth(hat, 4)) * np.exp(-hat_t * 90) * 0.03, start + i * beat + beat / 2)

    t = np.arange(samples) / SR
    gain = np.clip(t / 1.5, 0, 1) * np.clip((duration - t) / 1.2, 0, 1)
    for a, b in quiet:
        gain[(t > a) & (t < b)] *= 0.55
    if drop is not None:
        # Silence right before the final slam makes the punchline land harder
        gain[(t > drop - 0.3) & (t < drop)] = 0.0
        gain[t >= drop] *= 1.25
    return music * gain


def write_wav(path, data):
    peak = np.max(np.abs(data)) or 1.0
    pcm = (data / peak * 0.9 * 32767).astype(np.int16)
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(SR)
        handle.writeframes(pcm.tobytes())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("cues", type=Path)
    parser.add_argument("duration", type=float)
    parser.add_argument("work", type=Path)
    parser.add_argument("--drop", type=float, default=None, help="time of the final slam")
    parser.add_argument("--drums-from", type=float, default=None, help="bring drums in at this time")
    parser.add_argument("--quiet", action="append", default=[], help="A:B range where music sits lower")
    parser.add_argument("--no-music", action="store_true")
    args = parser.parse_args()

    if not args.cues.is_file():
        print(f"No such cues file: {args.cues}", file=sys.stderr)
        print("Next: run render.js cues first", file=sys.stderr)
        return 1

    samples = int(SR * args.duration)
    cues = json.loads(args.cues.read_text())
    sfx, unknown = build_sfx(cues, samples)
    write_wav(args.work / "sfx.wav", sfx)
    written = ["sfx.wav"]

    if not args.no_music:
        quiet = []
        for q in args.quiet:
            parts = q.split(":")
            if len(parts) != 2:
                print(f"--quiet must be A:B, got: {q}", file=sys.stderr)
                print("Next: pass a numeric range like --quiet 2.5:4.0", file=sys.stderr)
                return 1
            try:
                a, b = float(parts[0]), float(parts[1])
            except ValueError:
                print(f"--quiet times must be numbers, got: {q}", file=sys.stderr)
                print("Next: pass a numeric range like --quiet 2.5:4.0", file=sys.stderr)
                return 1
            quiet.append((a, b))
        write_wav(args.work / "music.wav", build_music(args.duration, samples, args.drums_from, args.drop, quiet))
        written.append("music.wav")

    print(f"{len(cues)} cues · {args.duration:.1f}s → {' + '.join(written)}")
    if unknown:
        print(f"  ignored unknown cue types: {', '.join(sorted(unknown))}")
    print("Next: run render-frames.sh, then mix-encode.sh")
    return 0


if __name__ == "__main__":
    sys.exit(main())
