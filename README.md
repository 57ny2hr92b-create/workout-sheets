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
`https://57ny2hr92b-create.github.io/workout-sheets/tv/` shows the week's strength days one exercise at a time, with a demo video, sets, reps, rest, setup, cues and the common mistake, sized for a TV. Open it in Safari on an iPhone, turn the phone sideways, and use Screen Mirroring to send it to the Apple TV.

- `plan.json` holds the strength days. Refresh it when the plan changes: `python3 scripts/export_plan.py /path/to/weekNN.json`, then `python3 scripts/build_site.py`. It keeps only titles, warm-ups, exercise order, sets, reps, rest and finisher; no loads or logs.
- Each exercise's demo is `video.tv.youtube_id` in `library.json`. Swap an ID and rebuild to change a video.
- Looks: the default is light "paper" colours with a big video and a coaching sidebar. Add `?style=` to try others: `gym` (the original dark look), `print` or `cinema` alone, `scoreboard` (huge sets, reps and rest across the top), or a mix such as `print,scoreboard`.
- The page design is `scripts/tv.html`; the build bakes the data into `docs/tv/index.html`.
- Long names and instructions shrink to fit their box instead of running off the screen. After changing the design or adding long text, run `node scripts/check_tv.js docs/tv/index.html` (needs Playwright). It clicks through every slide at TV, phone and tablet sizes and fails if anything spills. `test/tv_mock_*.json` is a deliberately extreme plan for stress-testing the design.
