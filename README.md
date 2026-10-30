# workout-sheets

Short links for the QR codes on the printed workout sheets. Each code points to `https://57ny2hr92b-create.github.io/workout-sheets/v/<exercise-id>/`, which forwards to that exercise's video. When a video dies or a better one is chosen, change it in `library.json` and rebuild. The printed sheets never change.

This repo is public, so it holds only exercise names and video links, never any workout logs or health data.

## Updating a video
1. In `library.json`, set the exercise's `video.url` and `video.status` to `"vetted"`.
2. Run `python3 scripts/build_site.py`.
3. Commit `library.json` and `docs/`.

Until an exercise is vetted, its link opens a YouTube search on the named channel.

## GitHub Pages
Settings → Pages → Deploy from a branch → `main`, folder `/docs`.

## Workout TV slideshow
`https://57ny2hr92b-create.github.io/workout-sheets/tv/` runs the week's strength days on the TV, one slide at a time. Open it in Safari on an iPhone, turn the phone sideways, and use Screen Mirroring to send it to the Apple TV.

What it does:
- **Home** lists both days with every exercise, sets × reps, time and set count, and marks the day that's **Up next** (the one after the day last finished). If a workout was left halfway (screen locked, page reloaded), a **Pick up** button returns to the same slide with the sets already ticked.
- **Warm-up**: tick moves off as you go. Moves with a time in them ("Row, easy, 3 min", "Dead hang, 20 s") get their own timer, shown big on the right.
- **Exercise slides**: the demo video loops a short clip, with sets, reps and rest, a **Set done** button and set dots, setup, steps and the common mistake. In a superset, Set done jumps straight to the partner exercise; after the last exercise of the pair it starts the rest timer, then brings you back for the next round, or on to the next exercise when all sets are done.
- **Rest timer**: a full-screen countdown with −15 s, +15 s and Go now. It beeps at 3, 2, 1 and at zero (sound button in the header).
- **Finisher**: "6 × (30 s strong / 30 s easy)" becomes an interval timer; "steady 10 min" becomes a countdown.
- **Done** shows minutes and sets ticked, and reminds you to fill in the sheet.
- The header shows the workout clock and one segment per slide; tap a segment to jump there. Arrow keys, space (set done / start timer) and swipes work too.

### Videos, clips and fallbacks
Each exercise's TV media lives in `library.json` under `video.tv`:

```json
"tv": {
  "youtube_id": "9W5KAqHfDe8", "src": "Fit Father Project",
  "start": 12, "end": 41,
  "status": "good",
  "backup": {"youtube_id": "4YVgTSY2E38", "src": "…", "status": "unreviewed"},
  "image": "img/goblet-squat.jpg",
  "pictogram": "squat"
}
```

- `start` and `end` (seconds) trim the clip, which loops between them. No clip ever plays longer than `tv.max_clip_s` at the top of `library.json` (60 s): an untrimmed video plays its first 60 s.
- `status` is `unreviewed`, `good` or `bad`. A bad video is skipped. When a clip is marked good, the printed QR code's short link opens that clip at its start time.
- The slide tries the demo, then the backup, then a photo (`image`, a file under `docs/tv/`), then a built-in drawing (`pictogram`: squat, pullup, bench, incline, rdl, kb-deadlift, swing, row, split-squat, carry). If YouTube refuses to play a video on another site, the slide switches to the next one by itself. Buttons under the video switch by hand.
- To use your own photo instead, put it in `docs/tv/img/` and set `image`.

### Reviewing videos
`https://57ny2hr92b-create.github.io/workout-sheets/tv/review/` lists every exercise's demo and backup. Load a video, tap **Start here** and **End here** to trim it, mark it **Good** or **Bad**, or paste a better link. **Send results** shares a short summary ending in one line of JSON. Apply it with:

```
python3 scripts/apply_review.py results.txt
```

### The weekly update
```
python3 scripts/weekly.py /path/to/generator/weekNN.json [--review results.txt] [--publish]
```
It copies any new exercise from the generator's `library.json` (public fields only), refreshes `plan.json`, applies review results, rebuilds `docs/`, lists videos that still need a look, runs the screen-fit check, and with `--publish` commits and pushes.

### Checks
- `python3 -m unittest discover test` tests the tools.
- `node scripts/check_tv.js docs/tv/index.html[?style=...] [screenshot-dir]` (needs Playwright) clicks through every slide at TV, phone and tablet sizes, opens the rest timer, the warm-up and finisher timers and the drawing, and fails if anything spills. `test/tv_mock_*.json` is a deliberately extreme plan for stress-testing the design.
- GitHub runs both on every push (`.github/workflows/check.yml`), and checks every video each Sunday (`video-check.yml`); broken ones open an issue called "Broken exercise videos".

### Looks
The default is light "paper" colours with a big video and a coaching sidebar. Add `?style=` to try others: `gym` (the original dark look), `print` or `cinema` alone, `scoreboard` (huge sets, reps and rest across the top), or a mix such as `print,scoreboard`. The page design is `scripts/tv.html` and the review page is `scripts/review.html`; the build bakes the data into `docs/tv/`.
