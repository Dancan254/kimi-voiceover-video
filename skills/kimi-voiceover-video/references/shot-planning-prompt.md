> Load this prompt before reviewing the draft shot list.

You are editing a short-form video. The transcript has already been proofread and the captions have
been built. `plan_shots.py` has produced a draft `shots.json` covering the whole recording.

Your job:

1. Read `shots.json`.
2. Load `references/scene-blocks.md` for the block catalogue, pacing rules, and sound cues.
3. Adjust any shot that breaks the rules below.
4. Show the user a clean shot table plus the image search list.
5. Wait for approval before authoring `index.html`.

---

## Review rules

- **One shot every 1–4 seconds.** Merge shots that are too short; split shots that are too long.
- **Cut on the word, not the sentence.** Each shot starts at the first word of its idea.
- **One hit per shot, on the word that lands the point** — a name, year, number, reveal, or punchline.
  Remove extra hits.
- **Hide captions** (`nocap: true`) whenever the spoken word is already the visual: huge headlines,
  counters, terminals, or stacked slams.
- **Match the block to the line.** A definition or key noun → `kinetic-slam`; a wrong assumption →
  `strike-through`; a year/number → `counter`; code/error → `terminal`; historical line → `vhs`;
  list of items → `montage` or `logo-wall`; final line → `outro`.
- **Match the media to the line.** Person/artefact → `image_query`; reaction/emotion → `gif_query`;
  process/ambience → `clip_query`; a joke the user would get → their own file via `local_media`.
  At most one or two meme beats per video.
- **Transitions:** use `whip` to move the story forward, `zoom` for reveals/new chapters, `glitch`
  for hard topic switches or error beats, `fade` for reflective beats, hard cut for fast
  back-to-back shots.
- **Media queries** should be concrete enough to search (person name, product name, logo, era). Drop
  the query if the shot is pure typography.

---

## Output table

Show the user this exact format:

```
#   in-out        line (spoken)                      block              sound
01  0.00-2.70     Did you know Java wasn't…          slam + strike      hit@0.44 hit@2.12
02  2.70-6.10     a completely different problem     highlight-box      whoosh, hit@4.60
03  6.10-8.30     Back in the early 1990s            vhs + counter      tick, hit@7.20
```

Then list every media query (`image_query`, `gif_query`, `clip_query`, `local_media`) with its
source plan (e.g., Wikimedia Commons search term).

Do not start `fill_template.py` or rendering until the user says yes.
