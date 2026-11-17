import json
import os
import tempfile
import unittest

import _load  # noqa: F401
from franceska_core import audit, code_scan, contrast_check, feature_coverage, gates, listing_check, provenance, readiness, review_insights, state, visual_compare
from franceska_core.core import read_csv, read_text, today, wdir, write_csv, write_json, write_text


def write_bytes(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as fh:
        fh.write(data)


def load_themes():
    with open(os.path.join(os.path.dirname(review_insights.__file__), "themes.default.json"), encoding="utf-8") as fh:
        return json.load(fh)


def tmp():
    return tempfile.mkdtemp(prefix="fr-test-")


class ParityTests(unittest.TestCase):
    def rows(self, spec):
        return [{"feature": f"f{i}", "area": a, "priority": p, "original": o, "yours": c, "notes": "n", "effort": ""}
                for i, (a, p, o, c) in enumerate(spec)]

    def test_weights_partial_skip_extras(self):
        rows = self.rows([("a", "must", "yes", "yes"), ("a", "should", "yes", "partial"),
                          ("b", "could", "yes", "no"), ("b", "must", "yes", "skip"), ("c", "must", "no", "yes")])
        r = feature_coverage.score(rows)
        # must 3*1 + should 2*.5 + could 0 = 4 of 6
        self.assertAlmostEqual(r["feature_score"], 66.7, places=1)
        self.assertEqual(r["extras"], 1)
        self.assertEqual(r["skipped"], 1)
        self.assertEqual(r["musts_missing"], [])

    def test_missing_must_blocks(self):
        rows = self.rows([("a", "must", "yes", "no")] + [("a", "should", "yes", "yes")] * 20)
        r = feature_coverage.score(rows)
        self.assertEqual(feature_coverage.verdict(r), "not shippable")

    def test_shippable(self):
        rows = self.rows([("a", "must", "yes", "yes")] * 4 + [("a", "could", "yes", "no")])
        self.assertEqual(feature_coverage.verdict(feature_coverage.score(rows)), "shippable")
        self.assertEqual(feature_coverage.verdict(feature_coverage.score(rows), open_blockers=1), "not shippable")

    def test_validate(self):
        rows = self.rows([("a", "must", "yes", "partial")])
        rows[0]["notes"] = ""
        self.assertTrue(feature_coverage.validate(rows))


class ContrastTests(unittest.TestCase):
    def test_known_ratios(self):
        self.assertAlmostEqual(contrast_check.ratio((0, 0, 0), (255, 255, 255)), 21.0, places=1)
        self.assertAlmostEqual(contrast_check.ratio((119, 119, 119), (255, 255, 255)), 4.48, places=1)

    def test_failures_both_modes(self):
        d = tmp()
        p = os.path.join(d, "t.json")
        write_json(p, {"colors": {"bg": "#fff", "text": "#000"}, "colors_dark": {"bg": "#000", "text": "#111"},
                       "pairs": [["text", "bg", 4.5]]})
        self.assertEqual(contrast_check.failures(p), 1)   # dark mode fails

    def test_hex_forms(self):
        self.assertEqual(contrast_check.parse_hex("#abc"), (170, 187, 204))
        self.assertEqual(contrast_check.parse_hex("00000080", over=(255, 255, 255)), (127, 127, 127))


class SweepTests(unittest.TestCase):
    def test_identifier_and_colour(self):
        d = tmp()
        write_text(os.path.join(d, "src", "a.tsx"), "import OriginalAppEmbed from 'x'\nconst c = '#0069FF'\n")
        write_text(os.path.join(d, "src", "calendar.ts"), "const calendar = 1\n")
        hits, _ = code_scan.scan(d, avoid=["Original App", "Cal"], colors=["#0069ff"])
        kinds = {(h[0], h[2]) for h in hits}
        self.assertIn(("src/a.tsx", "name"), kinds)
        self.assertIn(("src/a.tsx", "colour"), kinds)
        self.assertNotIn("src/calendar.ts", {h[0] for h in hits})   # 'Cal' must not match 'calendar'

    def test_filename_and_allow(self):
        d = tmp()
        write_text(os.path.join(d, "OriginalApp.css"), "x{}")
        write_text(os.path.join(d, "docs", "import.md"), "Import from Original App\n")
        hits, ok = code_scan.scan(d, avoid=["Original App"], allow=[{"path": "docs/*", "reason": "nominative"}])
        self.assertEqual([h[0] for h in hits], ["OriginalApp.css"])
        self.assertEqual(len(ok), 1)

    def test_skips_planning_and_deps(self):
        d = tmp()
        write_text(os.path.join(d, "franceska", "explore.md"), "Original App everywhere")
        write_text(os.path.join(d, "node_modules", "x", "i.js"), "Original App")
        hits, _ = code_scan.scan(d, avoid=["Original App"])
        self.assertEqual(hits, [])

    def test_secrets(self):
        d = tmp()
        write_text(os.path.join(d, "a.js"), "const k = 'sk_live_" + "a" * 24 + "'\n")
        write_text(os.path.join(d, ".env.example"), "STRIPE=sk_live_" + "b" * 24 + "\n")
        found = code_scan.scan_secrets(d)
        self.assertEqual([f[0] for f in found], ["a.js"])


class ListingTests(unittest.TestCase):
    def test_errors_and_warnings(self):
        data = {"avoid": ["Calendly"],
                "app_store": {"name": "Best Scheduler #1 For Teams Everywhere", "subtitle": "Free forever",
                              "promotional_text": "x", "keywords": "booking, meeting,booking,scheduler",
                              "description": "Works like Calendly but better"},
                "google_play": {"title": "Slotwise", "short_description": "Share a link, get booked.",
                                "full_description": "ok"}}
        rep = listing_check.lint(data)
        text = rep.render()
        self.assertTrue(rep.failed)
        self.assertIn("limit 30", text)
        self.assertIn("ranking claim", text)
        self.assertIn("price or promo", text)
        self.assertIn("contains a name from 'avoid'", text)
        self.assertIn("wasted character", text)

    def test_clean(self):
        data = {"avoid": ["Calendly"], "app_store": {"name": "Slotwise", "subtitle": "Booking links, flat price",
                "promotional_text": "x", "keywords": "booking,meeting", "description": "d"}}
        self.assertFalse(listing_check.lint(data).failed)


class ReviewTests(unittest.TestCase):
    def make(self):
        d = tmp()
        rows = [
            {"source": "App Store", "url": "https://a.example/1", "date": "2026-10-01", "rating": "1",
             "text": "Way too expensive per seat. I wish it had text reminders."},
            {"source": "Reddit", "url": "https://r.example/2", "date": "2026-09-20", "rating": "2",
             "text": "Per seat pricing is a rip off, and support never replied."},
            {"source": "G2", "url": "https://g.example/3", "date": "2026-08-01", "rating": "2",
             "text": "Too expensive for a small team."},
            {"source": "G2", "url": "", "date": "2026-08-01", "rating": "1", "text": "no link so dropped"},
            {"source": "G2", "url": "https://g.example/3", "date": "2026-08-01", "rating": "2",
             "text": "Too expensive for a small team."},
        ]
        p = os.path.join(d, "reviews.csv")
        write_csv(p, ["source", "url", "date", "rating", "text"], rows)
        return p

    def test_drops_and_themes(self):
        revs, dropped = review_insights.load_reviews(self.make())
        self.assertEqual(len(revs), 3)
        self.assertEqual(dropped["no link"], 1)
        self.assertEqual(dropped["duplicate"], 1)
        themes = load_themes()
        ranked, _un, reqs = review_insights.analyse(revs, themes)
        price = next(t for t in ranked if t["id"] == "price")
        self.assertEqual(price["count"], 3)
        self.assertFalse(price["thin"])
        corpus = " ".join(r["text"] for r in revs)
        for q in price["quotes"]:
            self.assertIn(q["quote"], corpus)             # quotes are verbatim
        self.assertTrue(any("wish it had text reminders" in s for s, _ in reqs))

    def test_small_sample_flagged(self):
        revs, d = review_insights.load_reviews(self.make())
        themes = load_themes()
        text = review_insights.render(revs, d, *review_insights.analyse(revs, themes))
        self.assertIn("Small sample", text)


class ImgDiffTests(unittest.TestCase):
    def png(self, path, w, h, bg, boxes):
        rows = []
        for y in range(h):
            row = []
            for x in range(w):
                px = bg
                for (x0, y0, x1, y1, c) in boxes:
                    if x0 <= x < x1 and y0 <= y < y1:
                        px = c
                row.extend(px)
            rows.append(row)
        visual_compare.write_png(path, w, h, rows)

    def test_recolour_still_matches_but_moved_layout_differs(self):
        d = tmp()
        a, b, c, e = (os.path.join(d, n) for n in ("a.png", "b.png", "c.png", "e.png"))
        layout = [(20, 20, 280, 60, (30, 30, 30)), (20, 90, 140, 200, (60, 60, 60)), (160, 90, 280, 200, (60, 60, 60))]
        self.png(a, 300, 240, (255, 255, 255), layout)
        # same layout, new palette
        recoloured = [(x0, y0, x1, y1, (200, 40, 60)) for (x0, y0, x1, y1, _c) in layout]
        self.png(b, 300, 240, (250, 245, 235), recoloured)
        # different layout
        self.png(c, 300, 240, (255, 255, 255), [(20, 150, 280, 220, (30, 30, 30)), (100, 20, 200, 120, (60, 60, 60))])
        same = visual_compare.compare(a, b)
        diff = visual_compare.compare(a, c, out=e)
        self.assertGreaterEqual(same["score"], 85)
        self.assertLess(diff["score"], same["score"] - 20)
        self.assertTrue(diff["regions"])
        self.assertTrue(os.path.getsize(e) > 100)
        self.assertEqual(visual_compare.read_png(e)[0], 240 * 3)     # diff image is written and readable

    def test_taller_clone_noted(self):
        d = tmp()
        a, b = os.path.join(d, "a.png"), os.path.join(d, "b.png")
        box = [(10, 10, 90, 30, (0, 0, 0))]
        self.png(a, 100, 100, (255, 255, 255), box)
        self.png(b, 100, 300, (255, 255, 255), box)
        self.assertIn("height_note", visual_compare.compare(a, b))

    def test_not_png(self):
        d = tmp()
        p = os.path.join(d, "x.png")
        write_text(p, "nope")
        with self.assertRaises(visual_compare.PngError):
            visual_compare.read_png(p)


class ProvenanceAuditTests(unittest.TestCase):
    def test_banned_and_terms(self):
        d = tmp()
        os.makedirs(wdir(d))
        provenance.add(d, "explore", "network-log", "devtools", "public", "endpoints")
        provenance.add(d, "explore", "own-account", "my account", "own-account", "states", terms_checked="")
        provenance.add(d, "explore", "help-docs", "https://x.example/help", "public", "features")
        text = provenance.check(d).render()
        self.assertIn("not allowed", text)
        self.assertIn("terms_checked=yes", text)

    def test_audit_catches_copy_ref_and_secret(self):
        d = tmp()
        os.makedirs(wdir(d, "screens"))
        shot = b"\x89PNG-fake-reference"
        write_bytes(wdir(d, "screens", "S01.png"), shot)
        os.makedirs(os.path.join(d, "public"))
        write_bytes(os.path.join(d, "public", "hero.png"), shot)
        write_text(wdir(d, "original-strings.txt"),
                   "# comment\nYour meetings, perfectly scheduled every single time\nSign in\n")
        write_text(os.path.join(d, "src", "App.tsx"),
                   "<h1>Your meetings, perfectly scheduled every single time</h1>\n")
        write_text(os.path.join(d, "src", "k.ts"), "const k='sk_live_" + "z" * 20 + "'")
        provenance.add(d, "explore", "help-docs", "https://x.example", "public", "features")
        rep = audit.run_audit(d, write=False)
        text = rep.render()
        self.assertTrue(rep.failed)
        self.assertIn("reference screenshots found", text)
        self.assertIn("original wording found", text)
        self.assertIn("secrets in the code", text)

    def test_audit_clean(self):
        d = tmp()
        os.makedirs(wdir(d))
        write_text(wdir(d, "original-strings.txt"), "Your meetings, perfectly scheduled every single time\n")
        write_text(os.path.join(d, "src", "App.tsx"), "<h1>Share a link and get booked</h1>\n")
        write_json(wdir(d, "brand.json"), {"name": "Slotwise", "avoid": ["Original App"], "domains": [], "colors": []})
        provenance.add(d, "explore", "help-docs", "https://x.example", "public", "features")
        self.assertFalse(audit.run_audit(d, write=True).failed)
        self.assertTrue(os.path.isfile(wdir(d, "review.md")))


class StateAndGateTests(unittest.TestCase):
    def setUp(self):
        self.d = tmp()
        state.init(self.d, {"name": "Demo", "platform": "web", "slice": "booking", "audience": "me"})

    def test_prereqs_and_next(self):
        st = state.load(self.d)
        self.assertEqual(state.next_stage(st), "explore")
        with self.assertRaises(SystemExit):
            state.start(self.d, "plan")
        state.skip(self.d, "explore", "testing")
        self.assertEqual(state.next_stage(state.load(self.d)), "plan")

    def test_reopen_marks_downstream_stale(self):
        st = state.load(self.d)
        for s in state.STAGES:
            st["stages"][s]["status"] = "passed"
        state.save(self.d, st)
        stale = state.reopen(self.d, "design")
        self.assertIn("build", stale)
        self.assertIn("publish", stale)
        self.assertNotIn("plan", stale)
        self.assertEqual(state.load(self.d)["stages"]["build"]["status"], "stale")

    def test_override_rules(self):
        with self.assertRaises(SystemExit):
            state.override(self.d, "review", "please")
        state.override(self.d, "validate", "tiny niche, 12 reviews")
        st = state.load(self.d)
        self.assertEqual(st["stages"]["validate"]["status"], "passed")
        self.assertEqual(len(st["overrides"]), 1)

    def test_recon_gate_end_to_end(self):
        d = self.d
        write_text(wdir(d, "explore.md"), "\n".join([
            "# Recon", "## Screens", "S01 S02 S03", "## Flows", "F01 book", "## Components", "x",
            "## Inferred data model", "x", "## Out of scope", "x", "## Size", "M"]))
        write_csv(wdir(d, "features.csv"), ["feature", "area", "priority", "original", "yours", "effort", "notes"],
                  [{"feature": f"f{i}", "area": "a", "priority": "must" if i < 2 else "should", "original": "yes",
                    "yours": "no", "effort": "S", "notes": ""} for i in range(6)])
        self.assertTrue(state.gate(d, "explore").failed)          # no provenance yet
        provenance.add(d, "explore", "help-docs", "https://x.example/help", "public", "features")
        rep = state.gate(d, "explore")
        self.assertFalse(rep.failed, rep.render())
        self.assertEqual(state.load(d)["stages"]["explore"]["status"], "passed")

    def test_entrepreneur_gate_catches_fabricated_quote(self):
        d = self.d
        rows = [{"source": s, "url": f"https://{s}.example/{i}", "date": "2026-10-01", "rating": "1",
                 "text": f"Per seat pricing is far too expensive for us number {i}."}
                for i in range(12) for s in ("a", "b", "c")][:36]
        write_csv(wdir(d, "reviews.csv"), ["source", "url", "date", "rating", "text"], rows)
        base = ("# Fixes\n## What they hate\n## What is missing\n## What is unsolved\n## Fix plan\n## Angle\n"
                "Sample: 36 reviews from 3 sources.\n")
        write_text(wdir(d, "fixes.md"), base + '"Per seat pricing is far too expensive for us number 3."\n')
        rep = gates.gate_entrepreneur(d, {})
        self.assertNotIn("not in reviews.csv", rep.render())
        write_text(wdir(d, "fixes.md"), base + '"This product ruined my entire weekend, truly awful."\n')
        self.assertIn("not in reviews.csv", gates.gate_entrepreneur(d, {}).render())

    def test_test_gate_open_blocker_and_flow_coverage(self):
        d = self.d
        write_text(wdir(d, "explore.md"), "F01 book\nF02 reschedule\n")
        write_text(wdir(d, "test-plan.md"), "F01-H1 happy\n")
        write_text(wdir(d, "bugs.md"), "## B-001 [S2] [open] Double booking\n## B-002 [S4] [open] typo\n")
        text = gates.gate_test(d, {}).render()
        self.assertIn("F02", text)
        self.assertIn("B-001", text)
        write_text(wdir(d, "bugs.md"), "## B-001 [S2] [fixed] Double booking\n")
        write_text(wdir(d, "test-plan.md"), "F01-H1 a\nF02-E1 b\n")
        self.assertFalse(gates.gate_test(d, {}).failed)

    def test_deploy_requires_go(self):
        d = self.d
        write_text(wdir(d, "publish.md"), "- [x] done\n")
        self.assertIn("recorded go", gates.gate_deploy(d, state.load(d)).render())
        state.approve(d, "publish", "yes, ship it")
        self.assertNotIn("recorded go", " ".join(m for k, m in gates.gate_deploy(d, state.load(d)).items if k == "fail"))


class ReadinessTests(unittest.TestCase):
    def setUp(self):
        self.d = tmp()
        os.makedirs(wdir(self.d))

    def states(self):
        return {r["id"]: r for r in readiness.evaluate(self.d)}

    def test_catalogue_is_consistent(self):
        ids = [i[0] for i in readiness.ITEMS]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual({readiness.area_of(i) for i in ids}, set(readiness.AREAS))

    def test_auto_checks_detect_files(self):
        write_text(os.path.join(self.d, "src", "h.ts"), "route('/healthz')")
        write_text(os.path.join(self.d, "src", "s.ts"), "helmet()")
        write_text(os.path.join(self.d, "src", "app", "privacy", "page.tsx"), "x")
        s = self.states()
        self.assertEqual(s["REL-1"]["state"], "auto")
        self.assertEqual(s["SEC-2"]["state"], "auto")
        self.assertEqual(s["LEG-1"]["state"], "auto")
        self.assertEqual(s["LEG-2"]["state"], "open")
        self.assertEqual(s["OBS-1"]["state"], "open")

    def test_secret_in_code_fails_rel6(self):
        write_text(os.path.join(self.d, "a.js"), "k='sk_live_" + "q" * 20 + "'")
        self.assertEqual(self.states()["REL-6"]["state"], "open")

    def test_evidence_rules(self):
        readiness.init(self.d)
        rows = readiness.parse(read_text(readiness.path(self.d)))
        rows["OBS-1"] = {"status": "done", "evidence": "tracker event 123", "date": today()}
        rows["OBS-2"] = {"status": "done", "evidence": "short", "date": today()}
        rows["OBS-3"] = {"status": "done", "evidence": "pager test sent and acked", "date": "2999-01-01"}
        rows["OBS-4"] = {"status": "na", "evidence": "no", "date": ""}
        rows["REL-2"] = {"status": "na", "evidence": "single environment by design, small tool", "date": ""}
        rows["REL-3"] = {"status": "done", "evidence": "restore into scratch db, 12 min", "date": "2020-01-01"}
        write_text(readiness.path(self.d), readiness.HEADER + readiness.render_table(rows) + "\n")
        s = self.states()
        self.assertEqual(s["OBS-1"]["state"], "evidence")
        self.assertEqual(s["OBS-2"]["state"], "bad")
        self.assertEqual(s["OBS-3"]["state"], "bad")
        self.assertEqual(s["OBS-4"]["state"], "bad")
        self.assertEqual(s["REL-2"]["state"], "na")
        self.assertTrue(s["REL-3"].get("stale"))

    def test_init_preserves_rows_and_gates_differ_by_strictness(self):
        readiness.init(self.d)
        rows = readiness.parse(read_text(readiness.path(self.d)))
        rows["OBS-1"] = {"status": "done", "evidence": "tracker event 123", "date": today()}
        write_text(readiness.path(self.d), readiness.HEADER + readiness.render_table(rows) + "\n")
        readiness.init(self.d)                               # re-init must not erase evidence
        self.assertEqual(self.states()["OBS-1"]["state"], "evidence")
        self.assertFalse(readiness.report(self.d, {"SEC"}).failed)           # early stages warn
        self.assertTrue(readiness.report(self.d, {"SEC"}, strict=True).failed)  # deploy fails


if __name__ == "__main__":
    unittest.main()
