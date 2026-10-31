"""Build the video short-link pages for GitHub Pages from library.json.

Each exercise gets docs/v/<exercise-id>/index.html, which forwards to its video.
The printed QR codes point at these pages, so a dead or replaced video is fixed
here without reprinting any sheets.
"""
import html
import json
import pathlib
import re
import urllib.parse

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
REPO = "57ny2hr92b-create/workout-sheets"


def target(v):
    # Vetted videos go straight to the video, then a TV clip Keifer marked good (at its start time),
    # otherwise a search on the named channel.
    if v.get("status") == "vetted" and v.get("url"):
        return v["url"]
    tv = v.get("tv") or {}
    for clip in (tv, tv.get("backup") or {}):
        if clip.get("status") == "good" and clip.get("youtube_id"):
            return f"https://www.youtube.com/watch?v={clip['youtube_id']}&t={int(clip.get('start') or 0)}s"
    return "https://www.youtube.com/results?search_query=" + urllib.parse.quote_plus(v["q"])


def page(title, body, head=""):
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex">
<title>{html.escape(title)}</title>{head}
<style>
body {{ font: 18px/1.5 system-ui, sans-serif; max-width: 34rem; margin: 3rem auto; padding: 0 16px; color: #111; background: #fff; }}
a {{ color: #111; }} li {{ margin: .4rem 0; }} small {{ color: #555; }}
</style></head><body>
{body}
</body></html>
"""


def build():
    lib = json.loads((ROOT / "library.json").read_text())
    rows = []
    for ex_id, ex in sorted(lib["exercises"].items(), key=lambda kv: kv[1]["name"]):
        v = ex["video"]
        name = html.escape(ex["name"])
        out = DOCS / "v" / ex_id
        out.mkdir(parents=True, exist_ok=True)
        if v.get("status") == "pending" and target(v).startswith("https://www.youtube.com/results"):
            body = f"<h1>{name}</h1><p>This video is still being chosen.</p><p><a href=\"{html.escape(target(v))}\">Search YouTube for now</a></p>"
            (out / "index.html").write_text(page(ex["name"], body))
            rows.append(f"<li>{name} <small>(video being chosen)</small></li>")
            continue
        url = html.escape(target(v))
        label = "Watch" if not target(v).startswith("https://www.youtube.com/results") else f"Search {html.escape(v.get('src', ''))}"
        head = f'\n<meta http-equiv="refresh" content="0; url={url}">\n<script>location.replace({json.dumps(target(v))});</script>'
        body = f'<h1>{name}</h1><p><a href="{url}">{label}</a></p>'
        (out / "index.html").write_text(page(ex["name"], body, head))
        note = "" if label == "Watch" else " <small>(search until vetted)</small>"
        rows.append(f'<li><a href="v/{ex_id}/">{name}</a>{note}</li>')
    tv = '<p><a href="tv/">Workout TV slideshow</a> <small>(mirror to the Apple TV)</small><br><a href="tv/review/">Review the demo videos</a></p>'
    (DOCS / "index.html").write_text(page("Exercise videos", "<h1>Exercise videos</h1>" + tv + "<ul>\n" + "\n".join(rows) + "\n</ul>"))
    (DOCS / ".nojekyll").write_text("")
    build_tv(lib)


# Drawings built into scripts/tv.html (PICTO). Keep in step when adding one.
PICTOGRAMS = {"squat", "pullup", "bench", "incline", "rdl", "kb-deadlift", "swing", "row", "split-squat", "carry"}
YT_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")


def check_library(lib, plan, docs=DOCS / "tv"):
    """Return (errors, notes) for the exercises the plan uses. Errors stop the build; notes are reminders."""
    errors, notes = [], []
    max_clip = lib.get("tv", {}).get("max_clip_s", 60)
    used = [e["id"] for d in plan["days"].values() for e in d["exercises"]]
    unreviewed = []
    for ex_id in dict.fromkeys(used):
        ex = lib["exercises"].get(ex_id)
        if not ex:
            errors.append(f"{ex_id}: used in plan.json but missing from library.json")
            continue
        tv = ex.get("video", {}).get("tv") or {}
        playable = 0
        for label, clip in (("demo", tv), ("backup", tv.get("backup") or {})):
            vid = clip.get("youtube_id")
            if not vid:
                continue
            if not YT_ID.match(vid):
                errors.append(f"{ex_id}: {label} youtube_id {vid!r} is not an 11-character YouTube ID")
                continue
            start, end = clip.get("start", 0) or 0, clip.get("end")
            if end is not None and end <= start:
                errors.append(f"{ex_id}: {label} clip ends ({end}s) before it starts ({start}s)")
            elif end is not None and end - start > max_clip:
                notes.append(f"{ex_id}: {label} clip is {end - start}s; the TV cuts it to {max_clip}s")
            if clip.get("status") == "bad":
                continue
            playable += 1
            # A backup nobody reviewed doesn't matter once the other clip is marked good.
            if clip.get("status") != "good" and "good" not in (tv.get("status"), (tv.get("backup") or {}).get("status")):
                unreviewed.append(f"{ex_id} {label}" + ("" if end else " (untrimmed)"))
        if tv.get("image") and not (docs / tv["image"]).is_file():
            errors.append(f"{ex_id}: image {tv['image']} not found under docs/tv/")
        if tv.get("pictogram") and tv["pictogram"] not in PICTOGRAMS:
            errors.append(f"{ex_id}: unknown pictogram {tv['pictogram']!r} (have {', '.join(sorted(PICTOGRAMS))})")
        if not playable and not tv.get("image") and not tv.get("pictogram"):
            notes.append(f"{ex_id}: no working video, photo or drawing; the TV shows the steps only")
        elif not playable:
            notes.append(f"{ex_id}: no working video; the TV shows the {'photo' if tv.get('image') else 'drawing'}")
    if unreviewed:
        notes.append(f"{len(unreviewed)} video(s) not reviewed yet; untrimmed ones play their first {max_clip}s: " + ", ".join(unreviewed))
    return errors, notes


def build_tv(lib, plan_path=ROOT / "plan.json", out=DOCS / "tv", quiet=False):
    # The slideshow and review page are single pages with the data baked in; fonts sit beside them in docs/tv/fonts.
    plan = json.loads(pathlib.Path(plan_path).read_text())
    out = pathlib.Path(out)
    errors, notes = check_library(lib, plan, out)
    if errors:
        raise SystemExit("library.json problems:\n  " + "\n  ".join(errors))
    if notes and not quiet:
        print(f"{len(notes)} video note(s):\n  " + "\n  ".join(notes))
    used = {e["id"] for d in plan["days"].values() for e in d["exercises"]}
    keep = ("name", "setup", "cues", "x", "row2", "video")
    settings = lib.get("tv", {})
    data = {"plan": plan, "settings": settings,
            "exercises": {k: {f: v[f] for f in keep if f in v} for k, v in lib["exercises"].items() if k in used}}
    review = {"settings": settings, "repo": REPO,
              "exercises": {k: {f: v[f] for f in ("name", "video") if f in v} for k, v in lib["exercises"].items()}}
    out.mkdir(parents=True, exist_ok=True)
    (out / "index.html").write_text((ROOT / "scripts" / "tv.html").read_text().replace("__DATA__", blob(data)))
    (out / "review").mkdir(exist_ok=True)
    (out / "review" / "index.html").write_text((ROOT / "scripts" / "review.html").read_text().replace("__DATA__", blob(review)))
    return notes


def blob(data):
    return json.dumps(data, ensure_ascii=False).replace("</", "<\\/")


if __name__ == "__main__":
    build()
