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
