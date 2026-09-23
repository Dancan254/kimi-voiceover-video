---
name: kimi-voiceover-video
description: "A Kimi-built skill for content creators who want pro short-form videos from a voice recording or to-camera take. Turns audio into a fully animated, brand-styled 1080x1920 Short (or 1920x1080 landscape) — local word-level transcription, a timed shot list, kinetic typography, camera moves, real images, synthesized sound design and a voice-ducked music bed. The brand is fully yours to set; Kimi violet is only the default starting point. Use when asked to 'make a video out of this audio', 'animate this voice note', 'turn this narration into a Short', 'edit this like a pro', 'create a video from my voiceover', or 'make a reel from this recording'."
---

# Kimi Voiceover Video Skill

A Kimi model runs this skill for content creators making short-form video. It takes an audio file and
builds a complete edit around it: every shot is an HTML/GSAP scene timed to the exact spoken word,
rendered frame by frame in headless Chromium, then muxed with a mixed soundtrack (voice + synthesized
SFX + ducked music). The judgement — what each line should *look* like — is Kimi's. The scripts handle
transcription, rendering, audio, and encoding.

The brand is fully customizable: handle, colours, fonts, output folder and music are all user-controlled.
The bundled `kimi-violet` preset is just a default; pass your own brand file to replace every visual.

Given a to-camera video instead of audio, the opening line and the sign-off stay on camera as face
shots; everything between them is animated over the voice from the same take.

`SKILL_DIR` = the directory containing this SKILL.md.

**Always load `SKILL_DIR/references/scene-blocks.md` before writing the shot list.** It holds the
block catalogue, the pacing rules, and the sound-cue vocabulary.

---

## Step 0 — Gather inputs

| Field | Required | Example |
|-------|----------|---------|
| `audio` or `video` | Yes | `~/Downloads/voice-note.m4a` · a to-camera recording `~/Movies/take-1.mp4` |
| `script` | No | the script, plain or with `[FACE]` / `[VOICE]` sections; captions are checked against it. Sections start on their own line with exactly `[FACE]` or `[VOICE]` |
| `format` | No | `vertical` 1080x1920 (default) · `landscape` 1920x1080 · `square` 1080x1080 |
| `music` | No | `synth` (default) · path to a royalty-free track · `none` |
| `model` | No | `small` (default) · `base` for clean audio, ~2x faster |
| `vocab` | No | names and terms the speaker uses: `"Kubernetes, Kafka, Jane Doe"` |
| `slug` | No | inferred from the topic, e.g. `java-origin` |

Brand: `./brand.json`, then `~/.config/kimi-voiceover-video/brand.json`, then the bundled
`SKILL_DIR/brand.example.json`. Output goes to `<brand.output.dir>/<slug>/`; work files go to
`<brand.output.dir>/<slug>/work/`. Create it now and set `<work>` to that path for the rest of the
workflow:

```bash
mkdir -p <brand.output.dir>/<slug>/work
work="<brand.output.dir>/<slug>/work"
```

Pick the defaults and proceed. Don't interrogate.

**First run only — no brand file anywhere:** the example brand ships someone else's handle and colours,
so ask before rendering. Four questions, each with its default, answered in one message:

| Ask | Default |
|---|---|
| Handle shown in the corner | required, no default |
| Look: `kimi-violet`, `tiktok-neon`, `youtube-dark`, `minimal-light`, `sports-energy`, `midnight-pink`, `carbon-cyan`, `ink-amber`, `violet-signal`, or their own accent and background | `kimi-violet` |
| Fonts: display and code | `Archivo` / `Geist Mono` |
| Where finished videos go | `~/kimi-voiceover-videos` |

```bash
python3 SKILL_DIR/scripts/init_brand.py --handle @theirhandle [--preset kimi-violet] \
  [--accent '#8b5cf6' --bg '#0f0f1a'] [--heading Archivo --mono 'Geist Mono'] [--output-dir ~/kimi-voiceover-videos]

Presets: `kimi-violet`, `tiktok-neon`, `youtube-dark`, `minimal-light`, `sports-energy`,
`midnight-pink`, `carbon-cyan`, `ink-amber`, `violet-signal`.
```

It derives the surface and border colours, checks the fonts against Google Fonts, and writes
`~/.config/kimi-voiceover-video/brand.json`. Then run Step 1 so the fonts download. Offer a preview: fill the
template and render one still, so they see their look before a full render. If they'd rather skip setup,
say plainly that the video will carry the example brand's `@kimi`.

**First run — brand setup.** If no brand file exists, ask the four questions above, write the brand
with `init_brand.py`, run `setup.sh`, then render one preview still before any full render. The user
can change every part of the look later by editing the brand file or re-running `init_brand.py --force`.

If the audio or video path is missing or not a file, say so and stop. With a `video`, pass the video
file wherever a step below takes `<audio>`; ffmpeg reads the voice from its audio track.

---

## Step 1 — Setup (first run only)

```bash
bash SKILL_DIR/scripts/setup.sh
```

Checks `ffmpeg`, `node`, `faster_whisper` and `numpy`; installs `playwright-core` and its matching
Chromium build; downloads GSAP and the brand's fonts into `SKILL_DIR/assets/`. Prints `ready` or names
the missing piece. Re-running is a no-op unless the brand's fonts changed.

---

## Step 2 — Transcribe

Tell the user the estimate first: roughly **2–3x realtime on CPU** for `small`.

```bash
python3 SKILL_DIR/scripts/transcribe.py <audio> --outdir "$work" --model small --vocab "<vocab>"
```

Writes `words.json` (every word with start/end) and `transcript.txt` — one phrase per line as
`[start] word@time word@time …`. Read `transcript.txt`; the per-word times are what you cut to.

Run it in the background for anything over two minutes. Never wait silently. The first run downloads
the model, so it may sit at low CPU for a few minutes.

---

## Step 3 — Extract the hook (optional, for long recordings)

If the recording is longer than ~90 seconds, find the best segment for a Short before planning shots.

```bash
python3 SKILL_DIR/scripts/extract_hook.py "$work" <audio> --target 60
python3 SKILL_DIR/scripts/extract_segment.py <audio> "$work"
```

`extract_hook.py` writes `hook.json` with the highest-scoring window. `extract_segment.py` extracts
that audio/video segment to `<work>/hook<ext>`. Then transcribe the hook segment instead of the full
file, or let `plan_shots.py` shift the full transcript to the hook window automatically.

Skip this step if the user already provided a Short-length clip.

---

## Step 4 — Proofread the captions

Captions are burned in. Scan `transcript.txt` for misheard words — proper nouns and technical terms
break first (observed: `San Micro Systems` → Sun Microsystems, `Ok` → Oak, `CNC++` → C/C++,
`Right once` → Write once). Write `<work>/fixes.json` mapping the raw token to its fix; an empty string
drops the token:

```json
{ "San": "Sun", "Ok.": "Oak.", "CNC++,": "C/C++,", "alias,": "" }
```

```bash
python3 SKILL_DIR/scripts/build_captions.py "$work"
```

Writes `<work>/words.js`. Never change timestamps. Tell the user about any token you could not
resolve instead of guessing.

Optionally write `<work>/keywords.json` — a JSON array of key nouns (`["Java", "Kubernetes"]`) —
before running the command above; flagged words stay accent-coloured in the captions. One or two
per phrase, never more.

With a `script`, it is the reference for spelling: a token that differs from it goes in `fixes.json`.
Captions follow what was said, so an ad-libbed line stays; tell the user where the take left the script.

---

## Step 5 — Shot list (confirm before building)

First, let the planner draft the list from the transcript:

```bash
python3 SKILL_DIR/scripts/plan_shots.py "$work"
```

Writes `<work>/shots.json` with a heuristic proposal: shot times, block type, hit word, transition,
and an image query. It is a draft — review it.

Then load `references/scene-blocks.md` **and** `references/shot-planning-prompt.md`. Apply the rules
from the prompt to refine the draft, then write the final shot table — one row per shot, cut on word
times:

```
#   in-out        line (spoken)                      block              sound
01  0.00-2.70     Did you know Java wasn't…          slam + strike      hit@0.44 hit@2.12
02  2.70-6.10     a completely different problem     highlight-box      whoosh, hit@4.60
03  6.10-8.30     Back in the early 1990s            vhs + counter      tick, hit@7.20
```

Rules: a new shot every 1–4 seconds; a hit only on a word that deserves it; captions hidden whenever
the spoken word *is* the visual. Shot 01 is the hook — the claim plus motion inside 3 seconds
(a slam or the rec-card title card), never a slow setup; with a `video` the face hook fills this
role. Find images before the table is final (Step 6).

With a `video`, the first and last rows are face shots (*Face hook*, *Face sign-off*). The hook runs
from 0 to the last word of the script's first `[FACE]` section (no script: the first sentence). The
sign-off runs from the first word of the last `[FACE]` section to the end. A series badge goes on shot 02.

Show the table and the image list to the user. Wait for a yes — this is the expensive part to change
later.

---

## Step 6 — Source media

Run the media finder against the queries in `shots.json`:

```bash
python3 SKILL_DIR/scripts/find_media.py "$work" --max-per-query 3
```

It searches Wikimedia Commons and Simple Icons, downloads up to 3 candidates per query into
`<work>/assets/`, and writes `<work>/credits.json` with source, author, and licence for every file.
Alongside `image_query`, a shot row can carry `gif_query`, `clip_query` or `local_media` (a path or
list of paths the user supplied); ad-hoc searches work too:

```bash
python3 SKILL_DIR/scripts/find_media.py "$work" --gif "facepalm" --clip "steam locomotive" --local ~/Memes/stonks.mp4
```

Gifs and videos are converted to muted webm so the renderer can seek them frame-exactly — never
embed a `.gif` directly. Pick the media type by context (see *Choosing media* in
`references/scene-blocks.md`): photos for people/artefacts, clips for process and ambience, memes
for punchlines — one meme beat per video, two at most.

**Look at every file before using it** — search results lie. For clips, also check the first and
last second (`ffmpeg -i file.webm` for length). If you cannot view images, list each candidate with
its source URL and what you expect it to show, and ask the user to confirm before Step 7.

To search manually, use the Commons API or Simple Icons CDN directly:

```bash
curl -s -A "kimi-voiceover-video-skill/1.0" "https://commons.wikimedia.org/w/api.php?action=query&list=search&srnamespace=6&srlimit=10&format=json&srsearch=<query>"
```

---

## Step 7 — Save project state

After the shot list and images are approved, save the project so the user can iterate later without
re-transcribing or re-sourcing images:

```bash
python3 SKILL_DIR/scripts/save_project.py "$work" \
  --source <audio> --brand <brand.json> --format vertical --music synth --approved
```

Writes `<work>/project.json`. To resume later:

```bash
python3 SKILL_DIR/scripts/load_project.py <work>/project.json [new-work-dir]
```

---

## Step 8 — Author the composition

```bash
python3 SKILL_DIR/scripts/fill_template.py "$work" <duration> --format vertical
# or --format landscape for 1920x1080, or --format square for 1080x1080
```

`<duration>` = last word end + ~2.5s for the outro; with a `video`, last word end + 0.5s, and never past
the recording's length. Get the recording length with:

```bash
ffprobe -v error -show_entries format=duration -of csv=p=0 <video>
```

Writes `<work>/index.html` from the template with brand, geometry and duration filled, and links the
vendored assets as `<work>/vendor`.

With a `video`, extract the camera frames for both face shots, using the shot list's in/out times:

```bash
bash SKILL_DIR/scripts/extract_face.sh <video> <work> vertical <hook-in> <hook-out> <signoff-in> <signoff-out>
```

Replace the demo shots between `BEGIN SHOTS` / `END SHOTS` (markup) and `BEGIN TIMELINE` /
`END TIMELINE` (GSAP) with your shot list, using the helpers the template already defines. Keep the
outer `#world` and `#cam` containers intact:
`shot()` (enters: `whip`, `whipUp`, `zoom`, `fade`, `glitch`), `slam()`, `hit()`, `rise()`, `pop()`,
`stagger()`, `drift()`, `typer()`, `counter()`, `terminal()`, `faceCam()`, `faceBubble()`, `clip()`,
`recDot()`, `timecode()`, and the `NOCAP` ranges and `CAP_STYLE` constant. Every helper that makes
noise pushes its own sound cue.

The display style (`.xl`) is uppercase and width-expanded; captions are condensed. Size headlines
for the expanded width — a vertical frame fits ~6 characters at 250px.

---

## Step 9 — QA stills & thumbnail (loop until clean)

Generate one preview still per shot automatically, choosing the hit word when there is one and the
midpoint otherwise:

```bash
python3 SKILL_DIR/scripts/preview_stills.py "$work"
```

This renders the frames and tiles them into `<work>/contact.jpg`. Then measure first — this needs no
eyes and runs in seconds:

```bash
node SKILL_DIR/scripts/render.js check "$work"/index.html ["$work"/check.json]
```

It seeks to each shot's midpoint and reports text past the frame edge, text sitting under the caption
box, shots that render nothing, and `PAGE ERROR` lines. Exit 1 means findings. Fix and re-run until it
is clean; it catches clipped headlines that a full render would waste minutes on.

Then, **if you can view images**, read `contact.jpg` for what measurement cannot judge: crops that cut
off a face or subject, an image that does not match the line, and layouts that fit the frame but read
badly. Fix, re-render only the affected stills, and look again.

If you cannot view images, say so in the report and ask the user to look at `contact.jpg` before
Step 10. Do not start Step 10 with a known defect — a full render costs minutes.

---

## Step 10 — Sound

```bash
node SKILL_DIR/scripts/render.js cues "$work"/index.html "$work"/cues.json
python3 SKILL_DIR/scripts/synth_audio.py "$work"/cues.json <duration> "$work" --drop <time-of-final-slam>
```

Writes `sfx.wav` and `music.wav`. Omit `--drop` if the video has no final slam; otherwise use the time
of the last big hit. Optional pacing flags:

- `--drums-from <t>` — bring the drums in at `<t>` seconds.
- `--quiet <a>:<b>` — duck the music between `a` and `b` seconds (repeatable).

With `music` set to a file, pass `--no-music` and give that file to Step 11. With `none`, pass
`--no-music` and nothing else.

You cannot hear the result. Say so in the report and ask the user to listen.

---

## Step 11 — Render frames

```bash
bash SKILL_DIR/scripts/render-frames.sh "$work"/index.html "$work"/frames <duration> [workers] [from_frame to_frame]
```

About 3 minutes for 108s on 10 workers. Run it in the background. The optional frame range re-renders
a single shot after a fix; each bound is its own argument, so it is safe under zsh.

---

## Step 12 — Mix and encode

```bash
out="<brand.output.dir>/<slug>/<slug>.mp4"
bash SKILL_DIR/scripts/mix-encode.sh "$work" <audio> <duration> "$out" [music-file]
```

Normalises the voice, ducks the music under it, lays the SFX on top, pads everything to the full
duration, targets −14 LUFS, and caps the video bitrate at 8M (film grain otherwise balloons the file
past 800 MB).

---

## Step 13 — Verify, then report

Before reporting, extract a frame from the **encoded file** at a shot you changed, read it, and check
the duration and size:

```bash
ffmpeg -v error -y -ss <t> -i <out.mp4> -frames:v 1 -vf scale=360:-1 <work>/verify.jpg
ffprobe -v error -show_entries format=duration,size -of compact <out.mp4>
```

A still rendered from the HTML is not proof the video contains the fix.

Also generate posting thumbnails from the best preview still:

```bash
python3 SKILL_DIR/scripts/make_thumbnail.py "$work"
```

Writes `<work>/thumbnail_vertical.jpg` (1080×1920) and `<work>/thumbnail_square.jpg` (1080×1080).
Pass `--source <still.jpg>` to override the auto-selected shot.

```
<slug>.mp4 · 1080x1920 · 108.2s · 112 MB · -14.7 LUFS

  shots 30 · sound cues 117 · images 4 · captions fixed 6

  credits     James Gosling 2008 (Wikimedia, CC BY-SA) · Solitary oak (geograph, CC BY-SA)
  unverified  music taste — listen before posting · timeline years are stylistic

Next: preview it on a phone, then post it with the credits in the description
```

`mix-encode.sh` prints raw `ffprobe` output; reformat it into the line above for the report.

---

## Non-negotiables

- **Shot list confirmed before authoring.** Rendering is cheap; redesigning thirty shots is not.
- **Every image is looked at before it is used.** Never ship an image you have not seen.
- **Every fix is verified in the encoded file**, not just in a still.
- Transcription is local. Never upload the audio.
- One brand accent. Green only for success states, red only for errors.
- Timelines are deterministic: no `Math.random()`, no `Date.now()`. The grain uses a seeded PRNG.
  Videos are seeked per frame — never embed a `.gif` directly.
- Captions never cover the element the viewer is meant to read; hide them via `NOCAP` instead.
- Report every image credit and every invented detail (dates, labels) that isn't in the audio.
- Never commit rendered files or `work/`.
- `faceCam()` in/out times match the `extract_face.sh` ranges exactly; never re-time a face shot alone.

---

## Failure states

| Symptom | Cause | Fix |
|---|---|---|
| `Executable doesn't exist at …ms-playwright…` | playwright-core updated, its Chromium build isn't installed | re-run `setup.sh` |
| Fix visible in stills but not in the video | frames never re-rendered — a range passed as one quoted string renders zero frames | use `render-frames.sh` with the range as two separate args; check frame mtimes |
| Video shorter than the audio | an audio filter trimmed the stream | `mix-encode.sh` pads and trims to the duration; don't hand-roll the mix |
| Output file is hundreds of MB | film grain defeats compression at constant CRF | keep the `-maxrate` cap in `mix-encode.sh` |
| Wrong or fallback font in stills | fonts not downloaded for this brand | re-run `setup.sh` with the brand file |
| `PAGE ERROR` in render output | a script error in the timeline | fix it; GSAP only warns on missing selectors, so also check each shot visually |
| `clip failed to load …` stops the render | the webm is missing from `assets/` or the browser can't decode it | check the `src` path against `credits.json`; re-run `find_media.py` for that query |
| Whisper sits at low CPU for minutes | model download on first run | expected once; the model is cached afterwards |
| Shot renders blank | `shot()` start ≥ end, or the shot id is misspelled | check the shot row's in/out times |
| `missing face frame …` stops the render | a `faceCam()` range is wider than the extracted one | re-run `extract_face.sh` with that shot's in/out |
| Face shots look grey and washed out | HDR (HLG) phone recording, tone-mapped without metadata | record in SDR (iPhone: Settings › Camera › Formats, HDR Video off) |
