"""Build the video short-link pages for GitHub Pages from library.json.

Each exercise gets docs/v/<exercise-id>/index.html, which forwards to its video.
The printed QR codes point at these pages, so a dead or replaced video is fixed
here without reprinting any sheets.
"""
import html
import json
import pathlib
import urllib.parse

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"


def target(v):
    # Vetted videos go straight to the video; candidates to a search on the named channel.
    if v.get("status") == "vetted" and v.get("url"):
        return v["url"]
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
        if v.get("status") == "pending":
            body = f"<h1>{name}</h1><p>This video is still being chosen.</p><p><a href=\"{html.escape(target(v))}\">Search YouTube for now</a></p>"
            (out / "index.html").write_text(page(ex["name"], body))
            rows.append(f"<li>{name} <small>(video being chosen)</small></li>")
            continue
        url = html.escape(target(v))
        label = "Watch" if v.get("status") == "vetted" else f"Search {html.escape(v.get('src', ''))}"
        head = f'\n<meta http-equiv="refresh" content="0; url={url}">\n<script>location.replace({json.dumps(target(v))});</script>'
        body = f'<h1>{name}</h1><p><a href="{url}">{label}</a></p>'
        (out / "index.html").write_text(page(ex["name"], body, head))
        note = "" if v.get("status") == "vetted" else " <small>(search until vetted)</small>"
        rows.append(f'<li><a href="v/{ex_id}/">{name}</a>{note}</li>')
    tv = '<p><a href="tv/">Workout TV slideshow</a> <small>(mirror to the Apple TV)</small></p>'
    (DOCS / "index.html").write_text(page("Exercise videos", "<h1>Exercise videos</h1>" + tv + "<ul>\n" + "\n".join(rows) + "\n</ul>"))
    (DOCS / ".nojekyll").write_text("")
    build_tv(lib)


def build_tv(lib, plan_path=ROOT / "plan.json", out=DOCS / "tv"):
    # The slideshow is one page with the plan and exercise text baked in; fonts sit beside it in docs/tv/fonts.
    plan = json.loads(pathlib.Path(plan_path).read_text())
    used = {e["id"] for d in plan["days"].values() for e in d["exercises"]}
    missing = used - lib["exercises"].keys()
    if missing:
        raise SystemExit(f"plan.json uses exercises missing from library.json: {sorted(missing)}")
    keep = ("name", "setup", "cues", "x", "row2", "video")
    data = {"plan": plan, "exercises": {k: {f: v[f] for f in keep if f in v} for k, v in lib["exercises"].items() if k in used}}
    blob = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    out = pathlib.Path(out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "index.html").write_text((ROOT / "scripts" / "tv.html").read_text().replace("__DATA__", blob))

if __name__ == "__main__":
    build()
