"""Production readiness: a catalogue of launch-blocking items, each satisfied by an automatic
check on the project or by dated evidence in franceska/production-readiness.md."""
import glob
import json
import os
import re
from datetime import date, datetime

from .core import Report, read_text, today, walk_text_files, wdir, write_text
from .code_scan import scan_secrets

AREAS = {
    "CI": "Build and CI", "OBS": "Observability", "REL": "Reliability", "SEC": "Security",
    "LEG": "Legal and privacy", "PERF": "Performance", "COM": "Commercial", "OPS": "Handover and growth",
}
ROW = re.compile(r"^\s*\|\s*([A-Z]{2,4}-\d+)\s*\|(.*)$")
STALE_DAYS = 30


# ---------------------------------------------------------------- automatic checks
def _grep(root, pattern, min_hits=1, ext=None):
    rx = re.compile(pattern, re.I)
    hits = []
    for rel, text in walk_text_files(root):
        if ext and os.path.splitext(rel)[1].lower() not in ext:
            continue
        if rx.search(text) or rx.search(rel):
            hits.append(rel)
            if len(hits) >= min_hits:
                break
    return len(hits) >= min_hits, (hits[0] if hits else "")


CODE_EXT = {".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".py", ".rb", ".go", ".java", ".kt", ".php",
            ".cs", ".rs", ".swift", ".vue", ".svelte", ".json", ".toml", ".yaml", ".yml", ".conf", ".mdx", ".html"}


def a_ci(root):
    pats = [".github/workflows/*.yml", ".github/workflows/*.yaml", ".gitlab-ci.yml", ".circleci/config.yml",
            "azure-pipelines.yml", "bitbucket-pipelines.yml", ".buildkite/*.yml"]
    for p in pats:
        for f in glob.glob(os.path.join(root, p)):
            t = read_text(f).lower()
            if "test" in t and "build" in t:
                return True, os.path.relpath(f, root)
    return False, "no CI workflow that runs tests and a build"


def a_lockfile(root):
    has_manifest = any(os.path.isfile(os.path.join(root, m)) for m in
                       ("package.json", "pyproject.toml", "requirements.txt", "Gemfile", "go.mod", "Cargo.toml"))
    if not has_manifest:
        return True, "no dependency manifest"
    locks = ["package-lock.json", "pnpm-lock.yaml", "yarn.lock", "bun.lockb", "bun.lock", "poetry.lock",
             "uv.lock", "Pipfile.lock", "Gemfile.lock", "go.sum", "Cargo.lock"]
    for l in locks:
        if os.path.isfile(os.path.join(root, l)):
            return True, l
    if os.path.isfile(os.path.join(root, "requirements.txt")) and re.search(
            r"==", read_text(os.path.join(root, "requirements.txt"))):
        return True, "requirements.txt (pinned)"
    return False, "dependencies are not locked"


def a_health(root):
    return _grep(root, r"(/api/health|/healthz?\b|/_health|/health['\"`/ )])", ext=CODE_EXT)


def a_headers(root):
    for rel, text in walk_text_files(root):
        if os.path.splitext(rel)[1].lower() not in CODE_EXT:
            continue
        low = text.lower()
        names = sum(1 for h in ("content-security-policy", "strict-transport-security", "x-content-type-options",
                                "x-frame-options", "referrer-policy") if h in low)
        if names >= 2 or "helmet(" in low or "secure_headers" in low or "securityheaders" in low:
            return True, rel
    return False, "no security headers configured"


def a_ratelimit(root):
    return _grep(root, r"(ratelimit|rate[-_ ]limit|ratelimiter|slowapi|express-rate-limit|limiter\b|throttl)",
                 ext=CODE_EXT)


def a_validation(root):
    return _grep(root, r"(\bzod\b|valibot|\byup\b|\bjoi\b|pydantic|class-validator|\bajv\b|marshmallow|express-validator|vine)",
                 ext=CODE_EXT)


def a_privacy(root):
    return (True, "privacy page") if _page_exists(root, "privacy") else (False, "no privacy policy page")


def a_terms(root):
    return (True, "terms page") if _page_exists(root, "terms") else (False, "no terms page")


def _page_exists(root, word):
    for rel, _t in walk_text_files(root):
        parts = re.split(r"[\\/]", rel.lower())
        if any(word in p for p in parts[:-1]) or word in os.path.splitext(parts[-1])[0]:
            return True
    return False


def a_delete(root):
    return _grep(root, r"(delete[-_ ]?account|deleteaccount|account/delete|delete_user|deleteuser|/account.{0,20}delete)",
                 ext=CODE_EXT)


def a_export(root):
    return _grep(root, r"(export[-_ ]?(my[-_ ])?data|exportdata|data[-_]export|download[-_ ]your[-_ ]data|/export\b)",
                 ext=CODE_EXT)


def a_readme(root):
    t = read_text(os.path.join(root, "README.md"))
    heads = len(re.findall(r"^#{1,3}\s", t, re.M))
    ok = heads >= 2 and re.search(r"(install|setup|run|deploy)", t, re.I) is not None
    return ok, "README.md" if ok else "README.md missing or has no setup/run/deploy sections"


def a_runbook(root):
    for p in (wdir(root, "runbook.md"), os.path.join(root, "docs", "runbook.md"), os.path.join(root, "RUNBOOK.md")):
        t = read_text(p)
        if t and all(re.search(w, t, re.I) for w in (r"deploy", r"roll\s?back", r"incident|outage", r"contact|on[- ]call")):
            return True, os.path.relpath(p, root)
    return False, "no runbook with deploy, rollback, incident and contact sections"


def a_seo(root):
    if any(os.path.isfile(os.path.join(root, d, f)) for d in ("", "public", "static") for f in ("robots.txt", "sitemap.xml")):
        return True, "robots.txt or sitemap.xml"
    return _grep(root, r"(og:title|openGraph|sitemap)", ext=CODE_EXT)


def a_secrets(root):
    found = scan_secrets(root)
    return not found, "no secrets in code" if not found else f"{len(found)} secrets in code"


# ---------------------------------------------------------------- the catalogue
# (id, text, auto check or None)
ITEMS = [
    ("CI-1", "CI runs tests and a build on every push", a_ci),
    ("CI-2", "Typecheck and lint pass in CI (paste the run)", None),
    ("CI-3", "Dependencies are locked", a_lockfile),
    ("CI-4", "Production build passes from a clean checkout", None),
    ("OBS-1", "Error tracking is live and a test error arrived", None),
    ("OBS-2", "Uptime checks watch the home page and the core API", None),
    ("OBS-3", "Alerts reach a human who will act (tested)", None),
    ("OBS-4", "Logs are kept and hold no personal data or secrets", None),
    ("REL-1", "A health endpoint answers when app and database are up", a_health),
    ("REL-2", "A staging environment separate from production exists", None),
    ("REL-3", "A database restore from backup was rehearsed", None),
    ("REL-4", "Migrations can be rolled back, or the rollback plan is written", None),
    ("REL-5", "A release rollback was tried once", None),
    ("REL-6", "No secrets in the code", a_secrets),
    ("SEC-1", "Dependency audit shows no high or critical issues", None),
    ("SEC-2", "Security headers are set (CSP, HSTS, nosniff, frame, referrer)", a_headers),
    ("SEC-3", "Rate limits cover sign-in, sign-up and anything that sends email or SMS", a_ratelimit),
    ("SEC-4", "A second user cannot read or change the first user's data (tested)", None),
    ("SEC-5", "Server-side input validation on every write route", a_validation),
    ("LEG-1", "Privacy policy page lists every processor", a_privacy),
    ("LEG-2", "Terms of service page", a_terms),
    ("LEG-3", "Cookie consent in place if non-essential cookies are used in the EU or UK", None),
    ("LEG-4", "Account deletion removes the user's data", a_delete),
    ("LEG-5", "A user can export their data", a_export),
    ("LEG-6", "A lawyer reviewed the legal pages, or the owner accepted the risk in writing", None),
    ("PERF-1", "Lighthouse (or equivalent) run on the landing page and core screen, scores recorded", None),
    ("PERF-2", "Slow queries and missing indexes checked on real-sized data", None),
    ("PERF-3", "A basic load test of this app (never the original) is recorded", None),
    ("PERF-4", "Images and fonts are optimised", None),
    ("COM-1", "Sales tax or VAT is handled (tax tool or adviser)", None),
    ("COM-2", "Cancel and refund flow works end to end in live mode", None),
    ("COM-3", "Failed payments are retried and the customer is told", None),
    ("COM-4", "Plan limits are enforced on the server, not only in the UI", None),
    ("COM-5", "A support inbox exists with a stated response time", None),
    ("COM-6", "Receipts or invoices are sent", None),
    ("COM-7", "The payment and business accounts are verified by the owner", None),
    ("OPS-1", "README covers setup, run and deploy", a_readme),
    ("OPS-2", "Runbook covers deploy, rollback, incidents and contacts", a_runbook),
    ("OPS-3", "Status page or incident channel customers can find", None),
    ("OPS-4", "Core funnel events are tracked", None),
    ("OPS-5", "robots, sitemap and share previews (OG tags) are set", a_seo),
]
BY_ID = {i[0]: i for i in ITEMS}


def area_of(item_id):
    return item_id.split("-")[0]


# ---------------------------------------------------------------- the evidence file
def path(root):
    return wdir(root, "production-readiness.md")


def parse(text):
    rows = {}
    for line in text.splitlines():
        m = ROW.match(line)
        if not m:
            continue
        cells = [c.strip() for c in m.group(2).split("|")]
        cells = cells[:-1] if cells and cells[-1] == "" else cells
        status = (cells[0] if len(cells) > 0 else "").lower()
        evidence = cells[1] if len(cells) > 1 else ""
        when = cells[2] if len(cells) > 2 else ""
        rows[m.group(1)] = {"status": status, "evidence": evidence, "date": when}
    return rows


def parse_date(s):
    try:
        return datetime.strptime(s.strip(), "%Y-%m-%d").date()
    except ValueError:
        return None


def render_table(rows):
    out = ["| id | status | evidence | date |", "| --- | --- | --- | --- |"]
    cur = None
    for item_id, text, _fn in ITEMS:
        a = area_of(item_id)
        if a != cur:
            cur = a
            out.append(f"| **{a}** | | {AREAS[a]} | |")
        r = rows.get(item_id, {"status": "todo", "evidence": "", "date": ""})
        out.append(f"| {item_id} | {r['status'] or 'todo'} | {r['evidence']} | {r['date']} |")
    return "\n".join(out)


HEADER = """# Production readiness

Every row must end up `done` or `na`. A row is satisfied when its automatic check passes on the
project, or when you mark it `done` with **evidence** (a link, a pasted result, a screenshot path)
and the **date** it was true (YYYY-MM-DD). `na` needs a reason in the evidence column.
Evidence older than 30 days is flagged as stale.

What each row means is in `python3 fr.py ready`. Items with an automatic check show `auto` there.

"""


def init(root, force=False):
    p = path(root)
    existing = parse(read_text(p)) if os.path.isfile(p) and not force else {}
    write_text(p, HEADER + render_table(existing) + "\n")
    return p


# ---------------------------------------------------------------- evaluation
def evaluate(root, areas=None):
    rows = parse(read_text(path(root)))
    out = []
    for item_id, text, fn in ITEMS:
        if areas and area_of(item_id) not in areas:
            continue
        auto_ok, auto_detail = (fn(root) if fn else (False, ""))
        r = rows.get(item_id)
        res = {"id": item_id, "area": area_of(item_id), "text": text, "auto": fn is not None,
               "state": "open", "detail": auto_detail if fn else "needs evidence"}
        if r and r["status"] == "na":
            if len(r["evidence"]) >= 10:
                res.update(state="na", detail="n/a: " + r["evidence"])
            else:
                res.update(state="bad", detail="na needs a reason of 10+ characters")
        elif r and r["status"] == "done":
            d = parse_date(r["date"])
            if len(r["evidence"]) < 8:
                res.update(state="bad", detail="done needs evidence")
            elif d is None or d > date.today():
                res.update(state="bad", detail="done needs a valid past date (YYYY-MM-DD)")
            else:
                age = (date.today() - d).days
                res.update(state="evidence", detail=r["evidence"] + (f" (stale: {age} days old)" if age > STALE_DAYS else ""),
                           stale=age > STALE_DAYS)
        elif auto_ok:
            res.update(state="auto", detail=auto_detail)
        if res["state"] == "open" and fn:
            res["detail"] = auto_detail or "automatic check found nothing; add it, or mark done with evidence"
        out.append(res)
    return out


def satisfied(res):
    return res["state"] in ("auto", "evidence", "na")


def summarize(results):
    areas = {}
    for r in results:
        a = areas.setdefault(r["area"], {"total": 0, "ok": 0, "open": []})
        a["total"] += 1
        if satisfied(r):
            a["ok"] += 1
        else:
            a["open"].append(r["id"])
    total = sum(a["total"] for a in areas.values())
    ok = sum(a["ok"] for a in areas.values())
    return areas, (round(100.0 * ok / total) if total else 0)


def report(root, areas=None, strict=False):
    """strict=True makes open items FAIL (deploy). Otherwise they WARN (earlier stages)."""
    results = evaluate(root, areas)
    rep = Report()
    summary, pct = summarize(results)
    for a, s in summary.items():
        if not s["open"]:
            rep.ok(f"{AREAS[a]}: all {s['total']} production items satisfied")
        else:
            msg = f"{AREAS[a]}: {len(s['open'])} of {s['total']} open ({', '.join(s['open'][:8])})"
            (rep.fail if strict else rep.warn)(msg)
    for r in results:
        if r["state"] == "bad":
            (rep.fail if strict else rep.warn)(f"{r['id']}: {r['detail']}")
        if r["state"] == "na":
            rep.warn(f"{r['id']} marked n/a ({r['detail'][5:60]})")
        if r.get("stale"):
            rep.warn(f"{r['id']} evidence is over {STALE_DAYS} days old; re-check it")
    return rep


def render_markdown(results):
    summary, pct = summarize(results)
    lines = [f"# Readiness: {pct}% satisfied", "", f"Generated {today()}", ""]
    for a, s in summary.items():
        lines.append(f"- {AREAS[a]}: {s['ok']} of {s['total']}")
    lines += ["", "| id | item | state | detail |", "| --- | --- | --- | --- |"]
    for r in results:
        lines.append(f"| {r['id']} | {r['text']} | {r['state']}{' (auto)' if r['state'] == 'auto' else ''} | {r['detail'][:80]} |")
    return "\n".join(lines) + "\n"


def run(args, root):
    if args.action == "init":
        p = init(root, args.force)
        print(f"wrote {p}")
        return 0
    results = evaluate(root, set(args.area.split(",")) if args.area else None)
    summary, pct = summarize(results)
    if args.json:
        print(json.dumps({"percent": pct, "areas": summary, "items": results}, indent=2))
    else:
        print(f"Production readiness: {pct}% satisfied")
        for r in results:
            mark = {"auto": "[auto]", "evidence": "[done]", "na": "[n/a ]", "open": "[ ]   ", "bad": "[!]   "}[r["state"]]
            line = f"  {mark} {r['id']:<7}{r['text']}"
            if r["state"] in ("open", "bad"):
                line += f"\n         -> {r['detail']}"
            print(line)
        print("-> " + ("ready to ship" if all(satisfied(r) for r in results) else "not ready: open items above block deploy"))
    if args.write:
        write_text(wdir(root, "readiness.md"), render_markdown(results))
    return 0 if all(satisfied(r) for r in results) else 1
