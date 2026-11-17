"""Exit criteria for every stage. A gate passes when it has no FAIL lines."""
import glob
import os
import re

from . import contrast_check, feature_coverage, provenance, readiness
from .audit import run_audit
from .core import Report, norm_space, read_csv, read_json, read_text, wdir
from .listing_check import lint
from .code_scan import scan, scan_secrets

BUG_RE = re.compile(r"^##\s+(B-\d+)\s+\[(S[1-4])\]\s+\[(open|fixed|wontfix|to-check)\]\s*(.*)$", re.M | re.I)
COLOR_ROLES = ["bg", "surface", "border", "text", "text-muted", "accent", "on-accent", "danger"]


def has_heading(text, pattern):
    return re.search(r"^#{1,4}\s.*(" + pattern + ")", text, re.M | re.I) is not None


def need_file(rep, root, rel, label=None):
    p = wdir(root, rel)
    ok = os.path.isfile(p) and os.path.getsize(p) > 0
    rep.check(ok, f"{label or rel} exists", f"{label or rel} is missing or empty (franceska/{rel})")
    return ok


def features(root):
    return feature_coverage.load_features(wdir(root, "features.csv"))


def bugs(root):
    return [(m.group(1), m.group(2).upper(), m.group(3).lower(), m.group(4).strip())
            for m in BUG_RE.finditer(read_text(wdir(root, "bugs.md")))]


# ---------------------------------------------------------------- stages
def gate_recon(root, state):
    rep = Report()
    app = state.get("app", {})
    missing = [k for k in ("name", "platform", "slice", "audience") if not app.get(k)]
    rep.check(not missing, "scope is set (app, platform, slice, audience)",
              "scope incomplete in state: " + ", ".join(missing))
    if need_file(rep, root, "explore.md"):
        t = read_text(wdir(root, "explore.md"))
        for label, pat in [("screen inventory", "screen"), ("flows", "flow"), ("components", "component"),
                           ("data model", "data model"), ("out of scope", "out of scope|cannot be cloned"),
                           ("size", "size")]:
            rep.check(has_heading(t, pat), f"explore.md has a {label} section", f"explore.md has no {label} section")
        n_s = len(set(re.findall(r"\bS\d{2}\b", t)))
        n_f = len(set(re.findall(r"\bF\d{2}\b", t)))
        rep.check(n_s >= 3, f"{n_s} screens with IDs", f"only {n_s} screen IDs (S01...) found, need at least 3")
        rep.check(n_f >= 1, f"{n_f} flows with IDs", "no flow IDs (F01...) found")
    rows = features(root)
    rep.check(len(rows) >= 5, f"features.csv has {len(rows)} rows", "features.csv has fewer than 5 rows")
    probs = feature_coverage.validate(rows)
    rep.check(not probs, "features.csv is valid", "features.csv: " + "; ".join(probs[:3]))
    rep.check(any(r["priority"] == "must" for r in rows), "at least one must-have", "no must-have features marked")
    rep.extend(provenance.check(root))
    if not read_text(wdir(root, "original-strings.txt")).strip():
        rep.warn("original-strings.txt is empty: record the original's UI wording so the audit can check for copying")
    return rep


def gate_architect(root, state):
    rep = Report()
    if need_file(rep, root, "architecture.md"):
        t = read_text(wdir(root, "architecture.md"))
        for label, pat in [("stack", "stack"), ("API or routes", "api|routes"), ("build order", "build order"),
                           ("risks", "risk|bite")]:
            rep.check(has_heading(t, pat), f"architecture.md has {label}", f"architecture.md has no {label} section")
    sql = read_text(wdir(root, "schema.sql"))
    n = len(re.findall(r"create\s+table", sql, re.I))
    rep.check(n >= 1, f"schema.sql defines {n} tables", "schema.sql has no create table statements")
    rep.check(not re.search(r"\btimestamp\b(?!\s*(with|\())", sql, re.I) or "timestamptz" in sql.lower(),
              "times use timestamptz", "schema.sql uses timestamp without time zone; use timestamptz", "warn")
    rep.check(not re.search(r"\b(float|real|double precision)\b", sql, re.I), "no float columns",
              "schema.sql has a float column; money should be integer cents", "warn")
    return rep


def gate_design(root, state):
    rep = Report()
    p = wdir(root, "design", "tokens.json")
    tokens = read_json(p)
    if not rep.check(tokens is not None, "design/tokens.json exists", "design/tokens.json is missing"):
        return rep
    missing = [r for r in COLOR_ROLES if r not in tokens.get("colors", {})]
    rep.check(not missing, "all colour roles present", "missing colour roles: " + ", ".join(missing))
    bad = contrast_check.failures(p)
    if bad is None:
        rep.fail("tokens.json has no 'pairs' to check contrast with")
    else:
        rep.check(bad == 0, "every pair passes WCAG AA", f"{bad} colour pairs fail WCAG AA")
    rep.check("colors_dark" in tokens, "dark mode tokens present", "no colors_dark; dark mode was not checked", "warn")
    need_file(rep, root, "design/components.md", "design/components.md")
    return rep


def gate_build(root, state):
    rep = Report()
    need_file(rep, root, "build-log.md")
    log = [l for l in read_text(wdir(root, "build-log.md")).splitlines() if re.match(r"^\s*[-*|]?\s*S\d{2}", l)]
    rep.check(len(log) >= 1, f"{len(log)} screens in the build log", "build-log.md has no screen lines (S01 ...)")
    rows = features(root)
    musts = [r for r in rows if r["priority"] == "must" and r["yours"] != "skip" and r["original"] != "no"]
    done = [r for r in musts if r["yours"] in ("yes", "partial")]
    rep.check(musts and len(done) * 2 >= len(musts), f"{len(done)} of {len(musts)} must-haves started",
              f"only {len(done)} of {len(musts)} must-haves are yes/partial in features.csv; build more first")
    shots = glob.glob(wdir(root, "app-screens", "*.png"))
    rep.check(len(shots) >= 1, f"{len(shots)} app screenshots saved",
              "no screenshots in franceska/app-screens/ (the visual comparison needs them)")
    return rep


def gate_backend(root, state):
    rep = Report()
    if need_file(rep, root, "connect.md"):
        open_boxes = len(re.findall(r"^\s*- \[ \]", read_text(wdir(root, "connect.md")), re.M))
        rep.check(open_boxes == 0, "security checklist fully ticked", f"{open_boxes} unticked items in connect.md")
    rep.check(os.path.isfile(os.path.join(root, ".env.example")), ".env.example exists", ".env.example is missing")
    gi = read_text(os.path.join(root, ".gitignore"))
    rep.check(".env" in gi, ".gitignore covers .env files", ".gitignore does not mention .env", "warn")
    s = scan_secrets(root)
    rep.check(not s, "no secrets in the code", "secrets in code: " + "; ".join(f"{r}:{n} {k}" for r, n, k in s[:5]))
    rep.extend(readiness.report(root, {"SEC", "REL", "LEG"}))
    return rep


def gate_test(root, state):
    rep = Report()
    plan_ok = need_file(rep, root, "test-plan.md")
    need_file(rep, root, "bugs.md")
    if plan_ok:
        flows = set(re.findall(r"\bF\d{2}\b", read_text(wdir(root, "explore.md"))))
        planned = set(re.findall(r"\b(F\d{2})-[HEN]\d+\b", read_text(wdir(root, "test-plan.md"))))
        gap = sorted(flows - planned)
        rep.check(not gap, f"every one of {len(flows)} flows has test cases",
                  "flows with no test cases: " + ", ".join(gap))
    b = bugs(root)
    blockers = [x for x in b if x[2] == "open" and x[1] in ("S1", "S2")]
    rep.check(not blockers, "no open S1 or S2 bugs",
              "open S1/S2 bugs: " + ", ".join(x[0] for x in blockers))
    s3 = [x for x in b if x[2] == "open" and x[1] == "S3"]
    if s3:
        rep.warn(f"{len(s3)} open S3 bugs")
    specs = glob.glob(os.path.join(root, "e2e", "**", "*.spec.*"), recursive=True)
    rep.check(bool(specs), f"{len(specs)} e2e spec files", "no e2e specs found; flows were manual-only", "warn")
    rep.extend(readiness.report(root, {"CI", "PERF"}))
    return rep


def open_blockers(root):
    return len([x for x in bugs(root) if x[2] == "open" and x[1] in ("S1", "S2")])


def gate_diff(root, state):
    rep = Report()
    need_file(rep, root, "coverage.md")
    rows = features(root)
    if not rows:
        rep.fail("features.csv missing")
        return rep
    from glob import glob as g
    layout = feature_coverage.load_layout(g(wdir(root, "diffs", "*.json")))
    res = feature_coverage.score(rows, layout)
    v = feature_coverage.verdict(res, open_blockers(root))
    rep.check(not res["musts_missing"], f"all {res['musts_total']} must-haves done",
              "must-haves not done: " + "; ".join(res["musts_missing"][:6]))
    rep.check(res["feature_score"] >= 80, f"feature score {res['feature_score']}",
              f"feature score {res['feature_score']} is under 80")
    rep.check(not open_blockers(root), "no open S1/S2 bugs", "open S1/S2 bugs block shipping")
    if res["layout_score"] is None:
        rep.warn("no layout diffs in franceska/diffs/")
    rep.ok(f"verdict: {v}") if v == "shippable" else rep.warn(f"verdict: {v}")
    return rep


def gate_entrepreneur(root, state):
    rep = Report()
    from .review_insights import load_reviews
    reviews, dropped = load_reviews(wdir(root, "reviews.csv"))
    srcs = {r["source"] for r in reviews}
    rep.check(len(reviews) >= 30 and len(srcs) >= 3,
              f"{len(reviews)} linked reviews from {len(srcs)} sources",
              f"only {len(reviews)} linked reviews from {len(srcs)} sources (need 30 and 3). "
              "Collect more, or the user can accept a thin sample with `override`")
    if need_file(rep, root, "fixes.md"):
        t = read_text(wdir(root, "fixes.md"))
        for label, pat in [("what they hate", "hate"), ("what is missing", "missing"),
                           ("what is unsolved", "unsolved"), ("fix plan", "fix plan"), ("angle", "angle|position")]:
            rep.check(has_heading(t, pat), f"fixes.md has {label}", f"fixes.md has no {label} section")
        rep.check(re.search(r"sample|\b\d+ reviews\b", t, re.I) is not None, "sample size is stated",
                  "fixes.md does not state the sample size")
        # anti-fabrication: every long quote must exist verbatim in reviews.csv
        corpus = " ".join(norm_space(r["text"]) for r in reviews)
        quotes = re.findall(r"[\"“]([^\"”\n]{25,300})[\"”]", t)
        fake = [q for q in quotes if norm_space(q).rstrip(".!?") not in corpus
                and norm_space(q).rstrip(".!?… ") not in corpus]
        rep.check(not fake, f"all {len(quotes)} quotes in fixes.md appear verbatim in reviews.csv",
                  f"{len(fake)} quotes are not in reviews.csv, e.g. \"{fake[0][:60]}\"" if fake else "")
    extra = [r for r in features(root) if r["original"] == "no"]
    rep.check(bool(extra), f"{len(extra)} fix rows added to features.csv", "no fix rows (original=no) in features.csv", "warn")
    return rep


def gate_brand(root, state):
    rep = Report()
    brand = read_json(wdir(root, "brand.json"))
    if not rep.check(brand is not None, "brand.json exists", "brand.json is missing"):
        return rep
    rep.check(bool(brand.get("name")), f"new name: {brand.get('name')}", "brand.json has no name")
    rep.check(bool(brand.get("avoid")), "avoid list set", "brand.json 'avoid' is empty")
    rep.check(bool(brand.get("domains")), "original domains listed", "brand.json 'domains' empty", "warn")
    rep.check(bool(brand.get("colors")), "original colours listed", "brand.json 'colors' empty", "warn")
    from .code_scan import term_patterns
    clash = [t for t in brand.get("avoid", []) for p in term_patterns(t) if brand.get("name") and p.search(brand["name"])]
    rep.check(not clash, "new name does not contain the original's name",
              "new name contains the original's name: " + ", ".join(clash))
    need_file(rep, root, "brand.md")
    bm = read_text(wdir(root, "brand.md"))
    unchecked = [l for l in bm.splitlines() if re.search(r"\bavailable\b", l, re.I)
                 and not re.search(r"\d{4}-\d{2}-\d{2}", l) and "to run" not in l.lower()]
    rep.check(not unchecked, "name checks are dated or marked 'to run'",
              "a check says 'available' with no date: " + unchecked[0].strip()[:70] if unchecked else "", "warn")
    hits, _ = scan(root, brand.get("avoid", []), brand.get("domains", []), brand.get("colors", []), brand.get("allow", []))
    rep.check(not hits, "code scan is clean", f"{len(hits)} leftovers of the original, e.g. {hits[0][0]}:{hits[0][1]}" if hits else "")
    bad = contrast_check.failures(wdir(root, "design", "tokens.json"))
    rep.check(bad == 0, "new palette passes contrast", "new palette fails contrast or tokens.json has no pairs")
    return rep


def gate_audit(root, state):
    return run_audit(root)


def gate_launch(root, state):
    rep = Report()
    for f in ("landing.md", "pricing.md", "launch-plan.md"):
        need_file(rep, root, "launch/" + f)
    pr = read_text(wdir(root, "launch", "pricing.md"))
    rep.check(re.search(r"https?://", pr) is not None and re.search(r"\d{4}-\d{2}-\d{2}", pr) is not None,
              "pricing cites the original's pricing page with a date",
              "pricing.md needs the original's pricing URL and the date it was read")
    landing = read_text(wdir(root, "launch", "landing.md"))
    if re.search(r"trusted by|★{3,}|\b\d[\d,]*\+? (happy )?(users|customers|teams)\b", landing, re.I):
        rep.warn("landing.md has proof-style claims (trusted by / star rows / user counts). Only keep them if real")
    from .review_insights import load_reviews, sentences
    reviews, _ = load_reviews(wdir(root, "reviews.csv"))
    ln = norm_space(landing)
    reused = [s for r in reviews for s in sentences(r["text"]) if len(s.split()) >= 8 and norm_space(s) in ln]
    rep.check(not reused, "no reviewer wording on the landing page",
              "landing.md reuses a reviewer's sentence: \"" + reused[0][:60] + "\"" if reused else "")
    lp = wdir(root, "launch", "listing.json")
    data = read_json(lp)
    if data is not None:
        brand = read_json(wdir(root, "brand.json"), {}) or {}
        data["avoid"] = list(data.get("avoid", [])) + list(brand.get("avoid", []))
        lr = lint(data)
        rep.check(not lr.failed, "store listing passes", "store listing has errors (run the listing check)")
    else:
        rep.warn("no launch/listing.json (fine if you are not shipping to a store)")
    rep.extend(readiness.report(root, {"COM", "OPS"}))
    return rep


def gate_deploy(root, state):
    rep = Report()
    need_file(rep, root, "publish.md")
    open_boxes = len(re.findall(r"^\s*- \[ \]", read_text(wdir(root, "publish.md")), re.M))
    rep.check(open_boxes == 0, "preflight fully ticked", f"{open_boxes} unticked items in publish.md")
    ap = [a for a in state.get("approvals", []) if a["stage"] == "publish"]
    rep.check(bool(ap), "the user's go is recorded", "no recorded go from the user (run `approve publish`)")
    a = run_audit(root, write=False)
    rep.check(not a.failed, "clean-room audit passes", "clean-room audit fails: run `review`")
    rows = features(root)
    res = feature_coverage.score(rows)
    rep.check(feature_coverage.verdict(res, open_blockers(root)) == "shippable", "coverage verdict: shippable",
              "coverage verdict is not shippable")
    rep.extend(readiness.report(root, strict=True))
    return rep


GATES = {
    "explore": gate_recon, "plan": gate_architect, "design": gate_design, "build": gate_build,
    "connect": gate_backend, "test": gate_test, "compare": gate_diff, "validate": gate_entrepreneur,
    "brand": gate_brand, "review": gate_audit, "launch": gate_launch, "publish": gate_deploy,
}
