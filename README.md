# Kimi Voiceover Video

Turn a voice note, narration, podcast clip, or to-camera take into a polished short-form video — locally, with word-level captions, kinetic typography, camera moves, images, and a mixed soundtrack.

Built as a skill for Kimi models, made for content creators who want pro 9:16 (or 16:9) output without touching a timeline.

![Preview frame](docs/preview.jpg)

---

## What it does

- **Transcribes locally** with word-level timing (Whisper / `faster-whisper` on CPU).
- **Cuts shots to the spoken word** using HTML/GSAP scenes rendered frame-by-frame in headless Chromium.
- **Burns in captions** and lets you hide them whenever the visual already shows the word.
- **Adds synthesized sound design** — hits, whooshes, typewriters, risers, ticks — plus a generated, voice-ducked music bed.
- **Supports your own music** by path; ducking keeps the voice on top.
- **Handles to-camera video** by keeping the hook and sign-off as face shots and animating everything between.
- **Renders vertical (1080×1920)** or **landscape (1920×1080)**.

The default look is Kimi violet, but every colour, font, handle, output folder, and music choice is yours.

---

## Install

### 1. System requirements

You need:

- Python 3.10+
- Node.js 18+
- ffmpeg
- `faster-whisper` and `numpy`

**macOS**
```bash
brew install ffmpeg python node
pip install faster-whisper numpy
```

**Ubuntu / Debian**
```bash
sudo apt update
sudo apt install ffmpeg python3 python3-pip nodejs npm
pip install faster-whisper numpy
```

### 2. Clone the skill

```bash
git clone https://github.com/Dancan254/kimi-voiceover-video.git
cd kimi-voiceover-video
```

### 3. Set up your brand

On first run the skill asks four quick questions: handle, colour preset, fonts, and output folder. You can also run the setup script directly:

```bash
python3 scripts/init_brand.py \
  --handle @yourhandle \
  --preset kimi-violet \
  --output-dir ~/kimi-voiceover-videos
```

Presets: `kimi-violet`, `midnight-pink`, `carbon-cyan`, `ink-amber`, `violet-signal`. Pass `--accent '#rrggbb' --bg '#rrggbb'` to roll your own.

### 4. Download assets and browsers

```bash
bash scripts/setup.sh
```

This installs `playwright-core`, downloads the matching headless Chromium, fetches GSAP, and downloads the fonts your brand uses. Re-run it any time you change fonts.

---

## Quickstart

### Make a video from audio

```bash
work=~/kimi-voiceover-videos/my-topic/work
mkdir -p "$work"

python3 scripts/transcribe.py ~/Downloads/my-voice.m4a --outdir "$work" --model small
# Proofread transcript.txt, then write fixes.json if needed
python3 scripts/build_captions.py "$work"

# Author shots in work/index.html, then:
python3 scripts/fill_template.py "$work" 45.0 --format vertical
bash scripts/render-frames.sh "$work"/index.html "$work"/frames 45.0
bash scripts/mix-encode.sh "$work" ~/Downloads/my-voice.m4a 45.0 \
  ~/kimi-voiceover-videos/my-topic/my-topic.mp4
```

### Use your own background music

```bash
python3 scripts/synth_audio.py "$work"/cues.json 45.0 "$work" --drop 42.5
bash scripts/mix-encode.sh "$work" ~/Downloads/my-voice.m4a 45.0 \
  ~/kimi-voiceover-videos/my-topic/my-topic.mp4 \
  ~/Music/my-track.mp3
```

### To-camera take (face hook + animated middle + face sign-off)

Follow the same flow, but run `extract_face.sh` before authoring shots:

```bash
bash scripts/extract_face.sh ~/Movies/take.mp4 "$work" vertical 0 2.4 42.1 45.0
```

Then use `faceCam()` in `work/index.html` for the first and last shots.

---

## How the workflow fits together

```
audio/video
    │
    ▼
transcribe.py ──► words.json + transcript.txt
    │
    ▼
build_captions.py ──► words.js (burned-in captions)
    │
    ▼
author shots in index.html (see references/scene-blocks.md)
    │
    ▼
fill_template.py ──► index.html with brand + geometry
    │
    ▼
render.js check / stills / frames ──► frames/
    │
    ▼
synth_audio.py ──► sfx.wav + music.wav
    │
    ▼
mix-encode.sh ──► final .mp4
```

---

## Customization

| What | Where |
|---|---|
| Handle, colours, fonts, output folder | `~/.config/kimi-voiceover-video/brand.json` or `./brand.json` |
| Caption fixes (misheard words) | `<work>/fixes.json` |
| Shot list + timing | Edit `BEGIN SHOTS` / `END SHOTS` and `BEGIN TIMELINE` / `END TIMELINE` in `<work>/index.html` |
| Music | `music: <file-path>` or `--no-music` |
| Format | `--format vertical` (default) or `--format landscape` |
| Vocab for transcription | `--vocab "Kubernetes, Jane Doe"` |

The full shot vocabulary and pacing rules are in `references/scene-blocks.md` — load it before writing the shot list.

---

## File structure

```
.
├── SKILL.md                    # Full step-by-step skill instructions for Kimi
├── README.md                   # This file
├── brand.example.json          # Default Kimi-violet brand
├── assets/                     # GSAP, fonts, cached CSS
├── references/
│   └── scene-blocks.md         # Block catalogue and sound cues
├── scripts/
│   ├── setup.sh                # One-time dependency/asset setup
│   ├── init_brand.py           # Create a brand file
│   ├── transcribe.py           # Local Whisper transcription
│   ├── build_captions.py       # Apply fixes, write words.js
│   ├── fill_template.py        # Fill composition.html into work dir
│   ├── render.js               # Headless Chromium still/frames/cues/check
│   ├── render-frames.sh        # Parallel frame renderer
│   ├── synth_audio.py          # Generated SFX + music
│   ├── mix-encode.sh           # Final mix and encode
│   ├── extract_face.sh         # Face frames from to-camera video
│   └── contact-sheet.sh        # Tiled stills for review
└── templates/
    └── composition.html        # Base HTML/GSAP composition
```

---

## Tips for the best output

- **Cut every 1–4 seconds.** A shot held longer needs internal motion.
- **Cut on the word, not the sentence.** Use `transcript.txt` times.
- **Hide captions** with `NOCAP` whenever the spoken word is the visual.
- **Use `render.js check`** before the full render — it catches clipped text and caption collisions in seconds.
- **Render stills first** and read the contact sheet before committing to a full render.
- **Record SDR** for to-camera phone footage to avoid grey/washed-out face shots.

---

## Roadmap

- AI shot planner from transcript
- More short-form presets + square format
- BPM-aware cuts for user-provided music
- Hook / best-segment extraction from long recordings
- Auto-image sourcing with credits
- Project save / reload for easy iteration

---

## License

This skill is a toolset for local video production. You are responsible for the content you create, the images you source, and the music you use. The bundled fonts come from Google Fonts; the default look is inspired by Kimi but fully replaceable.
