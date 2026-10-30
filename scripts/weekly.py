"""The weekly update for the TV slideshow, in one step.

Usage:
  python3 scripts/weekly.py /path/to/weekNN.json [--review results.txt] [--publish]

1. Copies any new exercise from the generator's library.json (next to the week file) into this
   repo's library.json, keeping only public fields, so a new move never breaks the build.
2. Refreshes plan.json from the week file (no loads, dates or logs; this repo is public).
3. Applies video review results, if given.
4. Rebuilds docs/ and lists any video that still needs a look.
5. Runs the screen-fit check (needs Node and Playwright; skipped if missing).
6. With --publish, commits library.json, plan.json and docs/ and pushes the current branch.
"""
import argparse
import json
import pathlib
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import apply_review  # noqa: E402
import build_site  # noqa: E402
import export_plan  # noqa: E402

PUBLIC = ("name", "pattern", "row1", "row2", "cues", "x", "setup")


def sync_exercises(week_path, lib_path=ROOT / "library.json"):
    """Add exercises the week uses that this repo's library doesn't have yet. Returns their IDs."""
    week = json.loads(pathlib.Path(week_path).read_text())
    used = {e["id"] for t in week["templates"].values() for e in t.get("exercises", [])}
    lib = json.loads(lib_path.read_text())
    missing = sorted(used - lib["exercises"].keys())
    if not missing:
        return []
    gen = pathlib.Path(week_path).resolve().parent / "library.json"
    source = json.loads(gen.read_text())["exercises"] if gen.is_file() else {}
    added = []
    for ex_id in missing:
        if ex_id not in source:
            raise SystemExit(f"{ex_id} is in the week plan but in neither library.json; add it first")
        ex = {k: source[ex_id][k] for k in PUBLIC if k in source[ex_id]}
        v = source[ex_id].get("video", {})
        ex["video"] = {k: v[k] for k in ("q", "src", "len", "status", "url") if k in v}
        tv = v.get("tv", {})
        ex["video"]["tv"] = {k: tv[k] for k in ("youtube_id", "src") if k in tv}
        ex["video"]["tv"]["status"] = "unreviewed"
        lib["exercises"][ex_id] = ex
        added.append(ex_id)
    lib_path.write_text(json.dumps(lib, indent=2, ensure_ascii=False) + "\n")
    return added


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("week")
    ap.add_argument("--review", help="results text from the video review page")
    ap.add_argument("--publish", action="store_true", help="commit and push when everything passes")
    args = ap.parse_args(argv)

    added = sync_exercises(args.week)
    for ex_id in added:
        print(f"New exercise {ex_id}: copied in with no demo video yet; the TV shows its steps. Pick a video and a drawing.")
    export_plan.export(args.week)
    if args.review:
        lib_path = ROOT / "library.json"
        lib = json.loads(lib_path.read_text())
        for c in apply_review.apply(lib, apply_review.parse(pathlib.Path(args.review).read_text())):
            print("Review:", c)
        lib_path.write_text(json.dumps(lib, indent=2, ensure_ascii=False) + "\n")
    build_site.build()

    if shutil.which("node"):
        r = subprocess.run(["node", str(ROOT / "scripts" / "check_tv.js"), str(ROOT / "docs" / "tv" / "index.html")], cwd=ROOT)
        if r.returncode:
            raise SystemExit("Screen-fit check failed; fix the layout before publishing.")
    else:
        print("Node not found: skipped the screen-fit check.")

    git = lambda *a: subprocess.run(["git", *a], cwd=ROOT, capture_output=True, text=True)
    changed = git("status", "--porcelain", "--", "library.json", "plan.json", "docs").stdout.rstrip()
    if not changed:
        print("Nothing changed.")
        return
    print("Changed:\n" + changed)
    if args.publish:
        plan = json.loads((ROOT / "plan.json").read_text())
        git("add", "library.json", "plan.json", "docs")
        r = git("commit", "-m", f"Week {plan['week']} slideshow update")
        print(r.stdout or r.stderr)
        r = git("push", "-u", "origin", "HEAD")
        print(r.stdout or r.stderr)
        if r.returncode:
            raise SystemExit("Push failed.")


if __name__ == "__main__":
    main()
