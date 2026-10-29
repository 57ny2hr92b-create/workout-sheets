"""Copy the strength days of a week plan into plan.json for the TV slideshow.

Usage: python3 scripts/export_plan.py /path/to/weekNN.json

Keeps only what the slideshow shows (day titles, warm-ups, exercise order,
sets, reps, rest, finisher). Loads, dates and anything personal stay out,
because this repo is public.
"""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent


def export(week_path):
    week = json.loads(pathlib.Path(week_path).read_text())
    days = {}
    for key, t in week["templates"].items():
        if not t.get("exercises"):
            continue
        days[key] = {
            "title": t["title"],
            "minutes": t.get("minutes"),
            "warmup_min": t.get("warmup_min"),
            "warmup": t.get("warmup", []),
            "exercises": [
                {k: e[k] for k in ("id", "pair", "sets", "reps", "rest", "extra") if k in e}
                for e in t["exercises"]
            ],
            "finisher": {k: v for k, v in t.get("finisher", {}).items() if k in ("text", "detail")},
        }
    plan = {"week": week["week"], "plan": week.get("plan", ""), "days": days}
    (ROOT / "plan.json").write_text(json.dumps(plan, indent=2, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    export(sys.argv[1])
