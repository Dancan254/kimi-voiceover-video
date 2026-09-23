# Scene Blocks

The vocabulary for a voiceover edit. A shot is one `<section class="shot">` plus its timeline
lines. Pick a block for each line of speech, then time it to the word.

---

## Pacing

- **Cut every 1–4 seconds.** A shot held longer than ~5s needs internal motion (a push-in, a
  line drawing, a counter) or the viewer scrolls.
- **Hook in the first 3 seconds.** Shot 01 is the claim plus motion — a slam or the rec-card
  title card, never a slow setup. The best visuals go in the first 60 seconds.
- **Graphics live 1–5 seconds.** A headline, card or image that stays longer is dead weight;
  cut or animate it.
- **Cut on the word, not the sentence.** The shot starts at the first word of its idea.
- **Hits are punctuation.** Use `hit()` / `slam()` on the one word per shot that lands the
  point: a year, a name, a reveal, a punchline. More than ~2 hits per shot reads as noise.
- **Contrast beats intensity.** Slow down for reflective lines (fade entries, no hits, music
  down); speed up for montages (one word per cut).
- **End on a slam, then hold.** The last ~2.5s after the final word is the outro: handle, mascot,
  call to action.

## Transitions (`shot(id, in, out, enter)`)

| enter | Feel | Use for |
|---|---|---|
| *(none)* | hard cut | the default between fast beats |
| `whip` | sideways blur-whip | moving forward in the story |
| `whipUp` | vertical whip | lists, rising energy, "then…" |
| `zoom` | punch in from blur | reveals, new chapter |
| `glitch` | RGB-split jitter | hard topic switches, error beats, meme energy |
| `fade` | soft | reflective lines, setup before a reveal |

---

## Blocks

### Kinetic slam
One huge word crashing in, everything else small around it.
```html
<div class="cx xl" id="s01a" style="top:520px;font-size:340px">JAVA</div>
```
```js
slam("#s01a", 0.44, 1.2);
```

### Code Report hook
Camera-viewfinder title card for shot 01: corner brackets, blinking `● REC`, a running timecode,
then the title word slams. The dot blink and timecode are recomputed every frame, so seeking
stays frame-exact. Pair with a `shutter` cue on the cut.
```html
<section class="shot" id="s01">
  <div class="vf"><i></i><i></i><i></i><i></i></div>
  <div class="rec"><i id="s01rec"></i>REC</div>
  <div class="tc" id="s01tc"></div>
  <div class="cx xl" id="s01a" style="top:700px;font-size:280px">JAVA</div>
</section>
```
```js
shot("s01", 0, 2.4);
SFX.push({t: .05, type: "shutter"});
recDot("#s01rec", 0, 2.4);
timecode("#s01tc", 0);
slam("#s01a", .5, 1.2);
```
For a multi-word title (a slam montage), slam each word in its own ~0.2–0.3s shot and hide
captions across all of them.

### Strike-through
Kill a wrong assumption ("not built for the web").
```html
<span style="position:relative;display:inline-block">the web?<span class="strike" id="s01s"></span></span>
```
```js
tl.fromTo("#s01s",{scaleX:0},{scaleX:1,duration:.25,ease:EX},2.1); hit(2.12,.7);
```

### Highlight box
Marker-pen accent behind the key word.
```html
<span class="hl"><i id="s02hl"></i>DIFFERENT</span>
```
```js
tl.fromTo("#s02hl",{scaleX:0},{scaleX:1,duration:.3,ease:EX},4.58); hit(4.6,.6);
```

### Stacked slams
Each word of a slogan on its own line, one hit each ("WRITE / ONCE. / RUN / ANYWHERE.").
Add a `#pinkflash` burst on the last word. Hide captions.

### Counter
Years, stats, "30+ years later". Ease-out so it settles on the number.
```js
counter("#s03y", 1984, 1991, 6.5, 7.2); hit(7.2,.8);
```

### Typewriter / terminal
Code, commands, errors. The template's `.term` gives the window chrome; `typer()` types plain
text and pushes typing SFX. For mixed colours (red error lines), keep a line array and rebuild
`innerHTML` in the `renderText` loop — see `terminal()` in the template.

### Photo tape-in
A person or artefact. Tilted `.polaroid` with a `.tape` strip, a `.cap` name tag, a slow
push-in (`drift` on scale) and a stamp.
```html
<div class="polaroid" id="s04p" style="left:230px;top:320px;width:620px;transform:rotate(-3deg)">
  <img src="assets/gosling.jpg" alt="">
  <div class="cap">James Gosling, 1995</div>
  <div class="tape" style="left:180px;top:-32px"></div>
</div>
```
```js
rise("#s04p", 3.2, .5); stamp("#s04stamp", 4.2);
drift("#s04p img", 3.2, 6.0, {scale:1},{scale:1.12});
```

### Stamp
Verdicts: `NOT READY`, `CONFIDENTIAL`, `SUN MICROSYSTEMS`.

```html
<div class="cx stamp" id="s04stamp" style="top:840px;color:var(--accent);font-size:120px">CONFIDENTIAL</div>
```
```js
stamp("#s04stamp", 4.2);
```

### Era look
Period-specific texture for historical beats:
- **VHS**: `.scan` overlay, `.vhs` chromatic text, moving `.track` bars, blinking `● SP`, date stamp
- **CRT monitor**: beige bezel `div` around a period screenshot with `.scan` at 40%
- **Dossier**: dark manila card, mono metadata, stamped title

### Diagram
Hub-and-spoke or tree. Draw paths with `strokeDashoffset`, `pop()` the nodes, send `.pkt`
dots along the routes, then turn nodes green with a `ding` per node. Keep diagrams inside
y = 150…1450 on vertical so captions never collide.

### Chart
One SVG path drawn over 2–4s. A crash is a line that climbs then falls; pair it with a `down`
cue and a stamp.

### Montage
One shot per word, 0.8–2s each, a `whip` and a `hit` on each: an icon or logo plus one word.
The emotional "it's everywhere" beat.

### Logo wall
3x3 grid of `.logo` cards. One `stagger()` call pops them all with a `pop` cue each.
```js
stagger(".logo", 4.2, .09);
```

### Face bubble *(video input)*
The speaker as a circular overlay on b-roll — terminal shots, diagrams, screen-style blocks
(Amigoscode / Tech With Tim style). Place it inside the shot's section, bottom corner above the
captions; its in/out must sit inside an `extract_face.sh` range, same as a face shot.
```html
<div class="facebubble" id="s07bub" style="right:60px;top:1120px"><img alt=""></div>
```
```js
faceBubble("#s07bub>img", 12.4, 16.8);
```

### Path / journey
An SVG curve drawing slowly through labelled milestones — for "found its purpose along the way".

### Reflective photo
Full-bleed photo, darkened gradient, slow drift, large sentence fading in. No hits, music ducked.

### Clip b-roll (gif / video)
Moving footage for a beat: a reaction gif, a process clip, ambient motion. `find_media.py` converts
gifs and videos to webm; the template seeks them per frame, so they stay deterministic. Never
embed a `.gif` directly.
```html
<video class="clip" id="s08v" src="assets/reaction_gif1.webm" muted preload="auto"
       style="left:140px;top:400px;width:800px;height:600px"></video>
```
```js
shot("s08", 12.0, 14.2, "whip");
clip("#s08v", 12.0, 14.2);          // optional 4th arg: start offset seconds into the clip
```
The clip loops if the shot outlasts it. Full-bleed or boxed; boxed clips pair with a `pop` or a
tilt. Keep clips inside the shot area (y = 150…1450) unless full-bleed.

### Meme insert
The funny beat: a meme still or clip dropped on the punchline for one beat only (1–2s), full
saturation, hard cut in and out, `hit()` on entry. Use at most once or twice per video — it is a
punchline, not a texture. A meme still is just a `.photo`; a meme gif is the clip block above.

### Choosing media by context
- Person, artefact, era → photo tape-in or era look
- Brand, tool, ecosystem → logo wall or montage
- Punchline, absurd claim → meme insert
- Reaction, emotion, "everyone" → gif clip
- Process, ambience, "how it works" → clip b-roll or terminal

### Outro
Stacked slams for the final line, mascot bouncing in, `follow @handle`. Hold ~2.5s. With a video
input, use *Face sign-off* instead.

### Face hook *(video input)*
The speaker on camera saying the opening line. Always shot 01, ending on the hook's last word.
```html
<section class="shot face" id="s01"><img alt=""></section>
```
```js
faceCam("s01", 0, 2.4);
hit(1.62, .5);
```
One punch-in on the word that lands the claim. Keep captions on: most viewers watch muted. Enter the
next shot with `zoom`. The `faceCam()` in/out times must exactly match the `extract_face.sh` range
for this shot.

### Series badge
Series name and episode, shown and never spoken. Pops on the first animated shot and leaves before
its cut. Place it inside that shot's section, not the face shot.
```html
<div class="cx" style="top:170px;z-index:5"><span class="badge" id="s02badge">SERIES NAME #04</span></div>
```
```js
pop("#s02badge", 2.5); tl.to("#s02badge",{opacity:0,duration:.3,ease:E},4.3);
```

### Face sign-off *(video input)*
The speaker on camera for the closing line. Always the last shot, from its first word to the end of
the composition. `fade` entry, no hits, no mascot.
```html
<section class="shot face" id="s24"><img alt=""></section>
```
```js
faceCam("s24", 84.1, D, "fade");
```
Face shots are full-bleed; check stills for a crop that cuts off the head. The `faceCam()` in/out
times must exactly match the `extract_face.sh` range for this shot.

---

## Captions

Captions are burned in automatically from `words.js`. Two styles, set with `CAP_STYLE` in the
template:

- **`fireship`** (default): mixed case, each word pops in on its own timestamp, the word being
  spoken glows in the brand accent.
- **`classic`**: ALL-CAPS phrase, dimmed until spoken, accent box on the active word.

Flag key nouns (product names, years, terms) by listing them in `<work>/keywords.json`
(`["Java", "Kubernetes"]`) before running `build_captions.py`; flagged words stay accent-coloured.
Use it sparingly — one or two per phrase.

Hide captions whenever the spoken word *is* the visual (a huge headline, a counter, a terminal)
by adding its time range to `NOCAP` in the template:

```js
const NOCAP = [[1.2, 2.4], [4.1, 5.6]];
```

Never cover the element the viewer is meant to read; hide captions instead.

---

## Sound cues

Every helper pushes its own cue into `SFX`; add extras with `SFX.push({t, type, dur?, power?})`.

| type | Sound | Pair with |
|---|---|---|
| `hit` | sub boom + click | `hit()`, `slam()` |
| `whoosh` | filtered noise sweep | transitions (auto from `shot()` enter) |
| `stamp` | dull thud | stamps |
| `pop` | pitched blip | `pop()` |
| `ding` | bell | success ticks |
| `type` (dur) | key clicks | `typer()` |
| `tick` (dur) | fast ticks | `counter()` |
| `riser` (dur) | rising noise + tone | the 1–2s before a big reveal |
| `down` (dur) | falling tone | crashes, failures |
| `error` | square buzz | red error lines |
| `shutter` | camera click | the rec-card cut |

The music bed ducks under the voice automatically at mix time (`mix-encode.sh`). Use `--drop <t>`
in `synth_audio.py` to cut the music just before the final slam — silence before the punchline is
the strongest hit.

---

## Layout safe zones (vertical 1080x1920)

```
y=0      ┌───────────────┐
y=92     │   signature   │
y=150    ├───────────────┤
         │   shot area   │  keep diagrams and cards here
y=1450   ├───────────────┤
y=1500   │   captions    │  70px, up to 3 lines
y=1800   ├───────────────┤
y=1910   └── progress ───┘
```

Full-bleed photos and backgrounds may fill the whole frame; readable elements may not.
