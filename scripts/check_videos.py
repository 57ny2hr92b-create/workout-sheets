"""Check that every YouTube video in library.json still exists and can play inside another site.

Usage: python3 scripts/check_videos.py [--report report.md]

YouTube's oEmbed endpoint answers 200 for a playable video, 401 or 403 when the owner turned off
embedding, and 400 or 404 when the video is gone or private. Exits 1 if any video is broken, so the
weekly GitHub Action can open an issue.
"""
import argparse
import json
import pathlib
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
OEMBED = "https://www.youtube.com/oembed?format=json&url="
WHY = {401: "embedding turned off", 403: "embedding turned off", 400: "removed or private", 404: "removed or private"}


def status(video_id, base=OEMBED):
    url = base + urllib.parse.quote(f"https://www.youtube.com/watch?v={video_id}", safe="")
    for attempt in range(3):
        try:
            with urllib.request.urlopen(url, timeout=20) as r:
                return r.status, json.loads(r.read()).get("title", "")
        except urllib.error.HTTPError as e:
            if e.code in WHY:
                return e.code, ""
            err = e
        except (urllib.error.URLError, TimeoutError) as e:
            err = e
        time.sleep(2 * (attempt + 1))
    return None, str(err)


def videos(lib):
    for ex_id, ex in lib["exercises"].items():
        tv = ex.get("video", {}).get("tv") or {}
        for which, clip in (("demo", tv), ("backup", tv.get("backup") or {})):
            if clip.get("youtube_id") and clip.get("status") != "bad":
                yield ex_id, ex["name"], which, clip["youtube_id"]


def main(argv=None, base=OEMBED):
    ap = argparse.ArgumentParser()
    ap.add_argument("--report")
    ap.add_argument("--library", default=str(ROOT / "library.json"))
    args = ap.parse_args(argv)
    lib = json.loads(pathlib.Path(args.library).read_text())
    broken, unsure, ok = [], [], 0
    for ex_id, name, which, vid in videos(lib):
        code, info = status(vid, base)
        if code == 200:
            ok += 1
        elif code in WHY:
            broken.append(f"- **{name}** ({which}, `{vid}`): {WHY[code]}. Swap it on the [review page](https://57ny2hr92b-create.github.io/workout-sheets/tv/review/) or in `library.json` under `{ex_id}`.")
        else:
            unsure.append(f"- {name} ({which}, `{vid}`): couldn't check ({info or code})")
    lines = [f"Checked {ok + len(broken) + len(unsure)} videos: {ok} fine, {len(broken)} broken, {len(unsure)} couldn't be checked."]
    if broken:
        lines += ["", "**Broken.** The TV skips these and falls back to the backup video or the drawing, but they should be replaced:", *broken]
    if unsure:
        lines += ["", "Couldn't check (try again later):", *unsure]
    report = "\n".join(lines)
    print(report)
    if args.report:
        pathlib.Path(args.report).write_text(report + "\n")
    return 1 if broken else 0


if __name__ == "__main__":
    raise SystemExit(main())
