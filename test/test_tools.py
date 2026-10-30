"""Tests for the weekly tools. Run: python3 -m unittest discover test"""
import http.server
import json
import pathlib
import sys
import tempfile
import threading
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import apply_review  # noqa: E402
import build_site  # noqa: E402
import check_videos  # noqa: E402
import weekly  # noqa: E402

LIB = json.loads((ROOT / "library.json").read_text())
PLAN = json.loads((ROOT / "plan.json").read_text())


def lib_copy():
    return json.loads(json.dumps(LIB))


class FakeOEmbed(http.server.BaseHTTPRequestHandler):
    # Video IDs starting with "gone" answer 404, "lock" 401, anything else 200.
    def do_GET(self):
        vid = self.path.rsplit("%3D", 1)[-1]
        code = 404 if vid.startswith("gone") else 401 if vid.startswith("lock") else 200
        self.send_response(code)
        self.end_headers()
        self.wfile.write(json.dumps({"title": vid}).encode() if code == 200 else b"")

    def log_message(self, *a):
        pass


class CheckVideos(unittest.TestCase):
    def setUp(self):
        self.srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), FakeOEmbed)
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()
        self.base = f"http://127.0.0.1:{self.srv.server_port}/oembed?url="

    def tearDown(self):
        self.srv.shutdown()

    def run_check(self, lib):
        with tempfile.TemporaryDirectory() as d:
            p = pathlib.Path(d) / "lib.json"
            p.write_text(json.dumps(lib))
            rep = pathlib.Path(d) / "r.md"
            code = check_videos.main(["--library", str(p), "--report", str(rep)], base=self.base)
            return code, rep.read_text()

    def test_all_fine(self):
        code, rep = self.run_check(LIB)
        self.assertEqual(code, 0)
        self.assertIn("0 broken", rep)

    def test_broken_videos_fail(self):
        lib = lib_copy()
        lib["exercises"]["db-bench"]["video"]["tv"]["youtube_id"] = "gone_123456"
        lib["exercises"]["kb-swing"]["video"]["tv"]["backup"]["youtube_id"] = "lock_123456"
        code, rep = self.run_check(lib)
        self.assertEqual(code, 1)
        self.assertIn("Dumbbell bench press** (demo, `gone_123456`): removed or private", rep)
        self.assertIn("Kettlebell swing** (backup, `lock_123456`): embedding turned off", rep)

    def test_videos_marked_bad_are_skipped(self):
        lib = lib_copy()
        tv = lib["exercises"]["db-bench"]["video"]["tv"]
        tv.update(youtube_id="gone_123456", status="bad")
        self.assertEqual(self.run_check(lib)[0], 0)


class ApplyReview(unittest.TestCase):
    TEXT = """Workout TV video review
Dumbbell bench press (demo): GOOD, clip 0:05–0:40

{"review":1,"clips":{"db-bench":{"demo":{"status":"good","start":5,"end":40}},"kb-swing":{"backup":{"youtube_id":"abcdefghijk","start":3}}}}"""

    def test_applies_status_clip_and_new_video(self):
        lib = lib_copy()
        apply_review.apply(lib, apply_review.parse(self.TEXT))
        demo = lib["exercises"]["db-bench"]["video"]["tv"]
        self.assertEqual((demo["status"], demo["start"], demo["end"]), ("good", 5, 40))
        backup = lib["exercises"]["kb-swing"]["video"]["tv"]["backup"]
        self.assertEqual((backup["youtube_id"], backup["start"], backup["status"]), ("abcdefghijk", 3, "unreviewed"))

    def test_rejects_text_without_results(self):
        with self.assertRaises(SystemExit):
            apply_review.parse("Dumbbell bench press: good")


class Weekly(unittest.TestCase):
    def test_new_exercise_is_copied_without_private_fields(self):
        with tempfile.TemporaryDirectory() as d:
            d = pathlib.Path(d)
            (d / "week09.json").write_text(json.dumps({"week": 9, "templates": {"A": {"exercises": [{"id": "goblet-squat"}, {"id": "plank"}]}}}))
            (d / "library.json").write_text(json.dumps({"exercises": {"plank": {
                "name": "Plank", "cues": ["Squeeze glutes."], "last": "60 s", "loads": [1, 2],
                "video": {"q": "plank", "status": "candidate", "tv": {"youtube_id": "abcdefghijk", "src": "Somebody"}}}}}))
            repo_lib = d / "repo-library.json"
            repo_lib.write_text(json.dumps(LIB))
            self.assertEqual(weekly.sync_exercises(d / "week09.json", repo_lib), ["plank"])
            plank = json.loads(repo_lib.read_text())["exercises"]["plank"]
            self.assertEqual(set(plank), {"name", "cues", "video"})
            self.assertEqual(plank["video"]["tv"], {"youtube_id": "abcdefghijk", "src": "Somebody", "status": "unreviewed"})


class Library(unittest.TestCase):
    def test_current_library_has_no_errors(self):
        errors, _ = build_site.check_library(LIB, PLAN)
        self.assertEqual(errors, [])

    def test_catches_bad_clips_and_pictures(self):
        lib = lib_copy()
        tv = lib["exercises"]["goblet-squat"]["video"]["tv"]
        tv.update(start=40, end=20, pictogram="handstand", image="img/nope.jpg")
        tv["backup"]["youtube_id"] = "short"
        errors, _ = build_site.check_library(lib, PLAN)
        joined = "\n".join(errors)
        for bit in ("ends (20s) before it starts", "not an 11-character", "unknown pictogram", "img/nope.jpg not found"):
            self.assertIn(bit, joined)

    def test_long_clip_is_a_note(self):
        lib = lib_copy()
        lib["exercises"]["goblet-squat"]["video"]["tv"].update(start=0, end=200, status="good")
        _, notes = build_site.check_library(lib, PLAN)
        self.assertTrue(any("200s; the TV cuts it to 60s" in n for n in notes))

    def test_good_clip_becomes_the_short_link(self):
        v = lib_copy()["exercises"]["db-bench"]["video"]
        v["tv"].update(status="good", start=12)
        self.assertEqual(build_site.target(v), f"https://www.youtube.com/watch?v={v['tv']['youtube_id']}&t=12s")

    def test_pictograms_match_the_page(self):
        page = (ROOT / "scripts" / "tv.html").read_text()
        for name in build_site.PICTOGRAMS:
            key = f'"{name}":' if "-" in name else f"{name}:"
            self.assertIn(key, page, name)


if __name__ == "__main__":
    unittest.main()
