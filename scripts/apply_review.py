"""Apply the results Keifer sends from the video review page to library.json, then rebuild.

Usage: python3 scripts/apply_review.py results.txt   (or paste the results on stdin)

The review page ends its results with one line of JSON: {"review": 1, "clips": {...}}.
Each clip can carry status (good or bad), start and end in seconds, and a new youtube_id.
"""
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import build_site  # noqa: E402


def parse(text):
    for line in reversed(text.strip().splitlines()):
        line = line.strip().strip("`")
        if line.startswith("{") and '"review"' in line:
            return json.loads(line)["clips"]
    raise SystemExit("No review results found. Paste everything the review page sent, including the last line.")


def apply(lib, clips):
    changes = []
    for ex_id, parts in clips.items():
        ex = lib["exercises"].get(ex_id)
        if not ex:
            changes.append(f"skipped {ex_id}: not in library.json")
            continue
        tv = ex["video"].setdefault("tv", {})
        for which, m in parts.items():
            clip = tv if which == "demo" else tv.setdefault("backup", {})
            if m.get("youtube_id") and m["youtube_id"] != clip.get("youtube_id"):
                if not build_site.YT_ID.match(m["youtube_id"]):
                    raise SystemExit(f"{ex_id} {which}: {m['youtube_id']!r} is not a YouTube ID")
                clip.update(youtube_id=m["youtube_id"], src="Keifer's pick", status="unreviewed")
                clip.pop("start", None)
                clip.pop("end", None)
            for f in ("start", "end"):
                if f in m:
                    clip[f] = int(m[f])
            if m.get("status") in ("good", "bad"):
                clip["status"] = m["status"]
            changes.append(f"{ex['name']} ({which}): " + ", ".join(f"{k} {v}" for k, v in m.items()))
    return changes


if __name__ == "__main__":
    text = pathlib.Path(sys.argv[1]).read_text() if len(sys.argv) > 1 else sys.stdin.read()
    path = ROOT / "library.json"
    lib = json.loads(path.read_text())
    for c in apply(lib, parse(text)):
        print(c)
    path.write_text(json.dumps(lib, indent=2, ensure_ascii=False) + "\n")
    build_site.build()
