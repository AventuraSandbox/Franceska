"""Drive a whole fake project through every gate with the real CLI."""
import contextlib
import io
import json
import os
import tempfile
import unittest

import _load  # noqa: F401
from franceska_core import visual_compare, readiness
from franceska_core.core import read_text, today
from franceska_core.cli import main
from franceska_core.core import wdir, write_csv, write_json, write_text


def fr(*args):
    out = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
        try:
            code = main(list(args))
        except SystemExit as e:
            code = e.code if isinstance(e.code, int) else 1
    return code, out.getvalue()


def png(path, w, h, boxes):
    rows = []
    for y in range(h):
        row = []
        for x in range(w):
            px = (255, 255, 255)
            for x0, y0, x1, y1, c in boxes:
                if x0 <= x < x1 and y0 <= y < y1:
                    px = c
            row.extend(px)
        rows.append(row)
    visual_compare.write_png(path, w, h, rows)


class Pipeline(unittest.TestCase):
    def test_full_run(self):
        d = tempfile.mkdtemp(prefix="fr-pipe-")
        P = ["--project", d]
        run = lambda *a: fr(*P, *a)  # noqa: E731

        self.assertEqual(run("init", "--name", "Slotwise", "--platform", "web", "--slice", "booking links",
                             "--audience", "small teams")[0], 0)
        self.assertEqual(run("next")[1].split()[0], "explore")
        self.assertEqual(run("start", "design")[0], 1)                        # prereqs enforced

        # ---- explore
        run("start", "explore")
        write_text(wdir(d, "explore.md"), "# Recon\n## Screens\nS01 S02 S03\n## Flows\nF01 book\nF02 reschedule\n"
                   "## Components\nbutton\n## Data model\nbooking\n## Out of scope\nmarketplace\n## Size\nM\n")
        feats = [("Guest books a slot", "booking", "must", "yes", "no", "M"),
                 ("Host sets availability", "availability", "must", "yes", "no", "M"),
                 ("Email confirmation", "notify", "should", "yes", "no", "S"),
                 ("Reschedule", "booking", "should", "yes", "no", "S"),
                 ("Embed on a website", "growth", "could", "yes", "no", "M"),
                 ("Partner marketplace", "marketplace", "could", "yes", "skip", "XL")]
        write_csv(wdir(d, "features.csv"), ["feature", "area", "priority", "original", "yours", "effort", "notes"],
                  [dict(zip(["feature", "area", "priority", "original", "yours", "effort"], f), notes="their network"
                        if f[4] == "skip" else "") for f in feats])
        write_text(wdir(d, "original-strings.txt"), "Your meetings, perfectly scheduled every single time\n")
        run("source", "add", "--stage", "explore", "--kind", "help-docs", "--ref", "https://orig.example/help",
            "--basis", "public", "--used-for", "features")
        self.assertEqual(run("gate", "explore")[0], 0, run("gate", "explore")[1])

        # ---- plan
        run("start", "plan")
        write_text(wdir(d, "architecture.md"), "## Stack\nx\n## API and routes\nx\n## The parts that bite\nx\n## Build order\nx\n")
        write_text(wdir(d, "schema.sql"), "create table bookings (id uuid primary key, start_at timestamptz not null);\n")
        self.assertEqual(run("gate", "plan")[0], 0)

        # ---- design
        run("start", "design")
        tokens = {"colors": {"bg": "#ffffff", "surface": "#f4f4f6", "border": "#d0d0d8", "text": "#111111",
                             "text-muted": "#444444", "accent": "#1d4ed8", "on-accent": "#ffffff", "danger": "#b42318"},
                  "colors_dark": {"bg": "#101114", "surface": "#181a1f", "border": "#30333b", "text": "#f5f5f7",
                                  "text-muted": "#b0b3bb", "accent": "#8fa8ff", "on-accent": "#101114", "danger": "#ff9c92"},
                  "pairs": [["text", "bg", 4.5], ["text-muted", "bg", 4.5], ["on-accent", "accent", 4.5], ["danger", "bg", 4.5]]}
        write_json(wdir(d, "design", "tokens.json"), tokens)
        write_text(wdir(d, "design", "components.md"), "Button\n")
        self.assertEqual(run("gate", "design")[0], 0, run("gate", "design")[1])
        self.assertEqual(run("contrast_check")[0], 0)

        # ---- build
        run("start", "build")
        write_text(wdir(d, "build-log.md"), "S01 | home | 2026-11-16 | done\n")
        png(wdir(d, "screens", "S01.png"), 300, 240, [(20, 20, 280, 60, (30, 30, 30)), (20, 90, 280, 200, (80, 80, 80))])
        png(wdir(d, "app-screens", "S01.png"), 300, 240, [(20, 20, 280, 60, (200, 40, 60)), (20, 90, 280, 200, (90, 20, 20))])
        rows = [dict(r) for r in __import__("franceska_core.core", fromlist=["x"]).read_csv(wdir(d, "features.csv"))]
        for r in rows:
            if r["yours"] != "skip":
                r["yours"] = "yes"
        write_csv(wdir(d, "features.csv"), ["feature", "area", "priority", "original", "yours", "effort", "notes"], rows)
        self.assertEqual(run("gate", "build")[0], 0, run("gate", "build")[1])

        # ---- backend
        run("start", "connect")
        write_text(wdir(d, "connect.md"), "- [x] secrets in env\n- [x] webhooks verified\n")
        write_text(os.path.join(d, ".env.example"), "STRIPE_SECRET_KEY=\n")
        write_text(os.path.join(d, ".gitignore"), ".env*\n")
        self.assertEqual(run("gate", "connect")[0], 0, run("gate", "connect")[1])

        # ---- test
        run("start", "test")
        write_text(wdir(d, "test-plan.md"), "F01-H1 a\nF02-H1 b\n")
        write_text(wdir(d, "bugs.md"), "## B-001 [S2] [open] Double booking\n")
        self.assertEqual(run("gate", "test")[0], 1)
        write_text(wdir(d, "bugs.md"), "## B-001 [S2] [fixed] Double booking\n")
        self.assertEqual(run("gate", "test")[0], 0)

        # ---- diff
        run("start", "compare")
        code, out = run("visual_compare", wdir(d, "screens", "S01.png"), wdir(d, "app-screens", "S01.png"), "--json")
        self.assertEqual(code, 0)
        write_text(wdir(d, "diffs", "S01.json"), out)
        code, out = run("feature_coverage", "--markdown")
        self.assertEqual(code, 0, out)
        write_text(wdir(d, "coverage.md"), out)
        self.assertEqual(run("gate", "compare")[0], 0, run("gate", "compare")[1])

        # ---- validate
        run("start", "validate")
        revs = [{"source": s, "url": f"https://{s}.example/{i}", "date": "2026-10-01", "rating": "1",
                 "text": f"Per seat pricing is far too expensive for our small team, review {i}."}
                for i in range(11) for s in ("appstore", "reddit", "g2")]
        write_csv(wdir(d, "reviews.csv"), ["source", "url", "date", "rating", "text"], revs)
        self.assertEqual(run("review_insights", "--out", wdir(d, "feedback.md"))[0], 0)
        write_text(wdir(d, "fixes.md"), "# Fixes\nSample: 33 reviews from 3 sources.\n## What they hate\n"
                   "\"Per seat pricing is far too expensive for our small team, review 4.\"\n"
                   "## What is missing\n## What is unsolved\n## Fix plan\n## Angle\nFor small teams.\n")
        rows = [dict(r) for r in __import__("franceska_core.core", fromlist=["x"]).read_csv(wdir(d, "features.csv"))]
        rows.append({"feature": "Flat pricing", "area": "billing", "priority": "should", "original": "no",
                     "yours": "yes", "effort": "S", "notes": ""})
        write_csv(wdir(d, "features.csv"), ["feature", "area", "priority", "original", "yours", "effort", "notes"], rows)
        self.assertEqual(run("gate", "validate")[0], 0, run("gate", "validate")[1])

        # ---- brand
        run("start", "brand")
        write_json(wdir(d, "brand.json"), {"name": "Slotwise", "avoid": ["Orig Cal"], "domains": ["orig.example"],
                                           "colors": ["#0069ff"], "allow": []})
        write_text(wdir(d, "brand.md"), "# Brand\nName checks: trademark US to run\n")
        write_text(os.path.join(d, "src", "App.tsx"), "<h1>Share a link and get booked</h1>\n")
        self.assertEqual(run("gate", "brand")[0], 0, run("gate", "brand")[1])
        write_text(os.path.join(d, "src", "Bad.tsx"), "import OrigCalEmbed from 'x' // #0069ff\n")
        self.assertEqual(run("gate", "brand")[0], 1)
        self.assertEqual(run("code_scan")[0], 1)
        os.remove(os.path.join(d, "src", "Bad.tsx"))
        self.assertEqual(run("gate", "brand")[0], 0)

        # ---- audit
        run("start", "review")
        self.assertEqual(run("gate", "review")[0], 0, run("gate", "review")[1])
        self.assertTrue(os.path.isfile(wdir(d, "review.md")))

        # ---- launch
        run("start", "launch")
        write_text(wdir(d, "launch", "landing.md"), "# Booking links for small teams\nOne flat price.\n")
        write_text(wdir(d, "launch", "pricing.md"), "Original pricing https://orig.example/pricing read 2026-11-16\n")
        write_text(wdir(d, "launch", "launch-plan.md"), "Waitlist first.\n")
        self.assertEqual(run("gate", "launch")[0], 0, run("gate", "launch")[1])
        write_text(wdir(d, "launch", "landing.md"), "Per seat pricing is far too expensive for our small team, review 4.\n")
        self.assertEqual(run("gate", "launch")[0], 1)                          # reviewer wording on landing page
        write_text(wdir(d, "launch", "landing.md"), "Flat pricing.\n")
        self.assertEqual(run("gate", "launch")[0], 0)

        # ---- deploy needs the user's go and a ready product
        run("start", "publish")
        write_text(wdir(d, "publish.md"), "- [x] tests green\n")
        self.assertEqual(run("gate", "publish")[0], 1)
        self.assertEqual(run("ready", "init")[0], 0)
        self.assertEqual(run("ready")[0], 1)                                     # nothing proven yet
        write_text(os.path.join(d, ".github", "workflows", "ci.yml"), "jobs:\n  verify:\n    steps:\n      - run: npm test\n      - run: npm run build\n")
        write_text(os.path.join(d, "package.json"), "{}")
        write_text(os.path.join(d, "package-lock.json"), "{}")
        write_text(os.path.join(d, "src", "app", "api", "health", "route.ts"), "export const path = '/api/health'\n")
        write_text(os.path.join(d, "next.config.js"), "headers: Content-Security-Policy, Strict-Transport-Security\n")
        write_text(os.path.join(d, "src", "limits.ts"), "import { ratelimit } from 'x'; import { z } from 'zod'\n")
        write_text(os.path.join(d, "src", "app", "privacy", "page.tsx"), "privacy\n")
        write_text(os.path.join(d, "src", "app", "terms", "page.tsx"), "terms\n")
        write_text(os.path.join(d, "src", "account.ts"), "export function deleteAccount() {}\nexport function exportData() {}\n")
        write_text(os.path.join(d, "README.md"), "# App\n## Setup\nrun it\n## Deploy\nship it\n")
        write_text(os.path.join(d, "public", "robots.txt"), "User-agent: *\n")
        write_text(wdir(d, "runbook.md"), "# Runbook\n## Contacts\n## Deploy\n## Rollback\n## Incident\n")
        code, out = run("ready")
        self.assertEqual(code, 1)
        self.assertIn("OBS-1", out)                                              # evidence items still open
        text = read_text(readiness.path(d))
        rows = readiness.parse(text)
        for r in readiness.evaluate(d):
            if not readiness.satisfied(r):
                rows[r["id"]] = {"status": "done", "evidence": "fixture evidence for the test", "date": today()}
        write_text(readiness.path(d), readiness.HEADER + readiness.render_table(rows) + "\n")
        self.assertEqual(run("ready", "--write")[0], 0, run("ready")[1])
        self.assertTrue(os.path.isfile(wdir(d, "readiness.md")))
        self.assertEqual(run("gate", "publish")[0], 1)                            # still no recorded go
        self.assertEqual(run("override", "publish", "--reason", "just do it")[0], 1)
        run("approve", "publish", "--quote", "yes, ship it")
        code, out = run("gate", "publish")
        self.assertEqual(code, 0, out)
        self.assertIn("all stages passed", run("status")[1])

        # ---- changing your mind
        code, out = run("reopen", "design")
        self.assertIn("build", out)
        self.assertIn("[!]", run("status")[1])


if __name__ == "__main__":
    unittest.main()
