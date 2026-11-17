"""Rank what an app's users hate, from a sheet of real, linked reviews. Never invents anything."""
import json
import os
import re
from datetime import date, datetime

from .core import norm_space, read_csv, read_json

HERE = os.path.dirname(os.path.abspath(__file__))
REQUEST = re.compile(
    r"\b(i wish|wish (it|they|there)|please add|would be (nice|great|amazing)|need(s)? (a|an|to)\b|"
    r"should (have|add|let|allow)|missing|no way to|can'?t (even )?(\w+ )?(export|import|undo|schedule|share|search)|"
    r"why (can'?t|doesn'?t|isn'?t)|feature request|add support)\b",
    re.I,
)
RATING_W = {1: 1.0, 2: 0.8, 3: 0.5, 4: 0.25, 5: 0.1}
MAX_QUOTE_WORDS = 40


def parse_date(s):
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d/%m/%Y", "%m/%d/%Y", "%b %d, %Y", "%B %d, %Y"):
        try:
            return datetime.strptime(s.strip(), fmt).date()
        except ValueError:
            pass
    m = re.match(r"(\d{4}-\d{2}-\d{2})", s.strip())
    return date.fromisoformat(m.group(1)) if m else None


def recency_w(d, today):
    if not d:
        return 0.5
    age = (today - d).days
    return 1.0 if age <= 90 else 0.7 if age <= 365 else 0.4


def load_reviews(path):
    rows = read_csv(path)
    good, dropped, seen = [], {"no link": 0, "no text": 0, "duplicate": 0}, set()
    for r in rows:
        url, text = r.get("url", ""), r.get("text", "")
        if not re.match(r"^https?://", url):
            dropped["no link"] += 1
            continue
        if not text.strip():
            dropped["no text"] += 1
            continue
        key = (url, norm_space(text))
        if key in seen:
            dropped["duplicate"] += 1
            continue
        seen.add(key)
        try:
            rating = int(float(r.get("rating", ""))) if r.get("rating", "") else None
        except ValueError:
            rating = None
        good.append({
            "source": r.get("source", "").strip() or "unknown", "url": url, "text": text.strip(),
            "rating": rating, "date": parse_date(r.get("date", "")),
        })
    return good, dropped


def sentences(text):
    parts = re.split(r"(?<=[.!?])\s+|\n+", text)
    return [p.strip() for p in parts if p.strip()]


def best_quote(text, patterns):
    """A verbatim sentence from the review, preferring one that matches a keyword."""
    sents = sentences(text)
    pick = next((s for s in sents if any(p.search(s) for p in patterns)), sents[0] if sents else text)
    words = pick.split()
    if len(words) > MAX_QUOTE_WORDS:
        pick = " ".join(words[:MAX_QUOTE_WORDS])
        return pick, True
    return pick, False


def compile_theme(t):
    kws = [re.escape(k) for k in t["keywords"]]
    return re.compile(r"(?<![a-z])(" + "|".join(kws) + r")", re.I)


def analyse(reviews, themes, today=None):
    today = today or date.today()
    comp = [(t, compile_theme(t)) for t in themes]
    out = {t["id"]: {"title": t["title"], "kind": t.get("kind", "hate"), "items": []} for t in themes}
    unmatched, requests = [], []
    for r in reviews:
        w = RATING_W.get(r["rating"], 0.5) * recency_w(r["date"], today)
        r["weight"] = w
        hit = False
        for t, rx in comp:
            if rx.search(r["text"]):
                out[t["id"]]["items"].append((r, rx))
                hit = True
        if not hit and (r["rating"] or 3) <= 2:
            unmatched.append(r)
        for s in sentences(r["text"]):
            if REQUEST.search(s):
                requests.append((s, r))
    ranked = []
    for tid, d in out.items():
        items = d["items"]
        if not items:
            continue
        srcs = sorted({r["source"] for r, _ in items})
        score = sum(r["weight"] for r, _ in items)
        top = sorted(items, key=lambda x: -x[0]["weight"])[:2]
        quotes = []
        for r, rx in top:
            q, cut = best_quote(r["text"], [rx])
            quotes.append({"quote": q, "cut": cut, "url": r["url"], "source": r["source"], "rating": r["rating"]})
        ranked.append({
            "id": tid, "title": d["title"], "kind": d["kind"], "count": len(items),
            "sources": srcs, "score": round(score, 2),
            "thin": len(items) < 3 or len(srcs) < 2, "quotes": quotes,
        })
    ranked.sort(key=lambda x: -x["score"])
    return ranked, unmatched, requests


def render(reviews, dropped, ranked, unmatched, requests):
    n = len(reviews)
    srcs = sorted({r["source"] for r in reviews})
    dates = [r["date"] for r in reviews if r["date"]]
    lines = ["# What the users say", ""]
    span = f", {min(dates)} to {max(dates)}" if dates else ""
    lines.append(f"**Sample: {n} linked reviews from {len(srcs)} sources ({', '.join(srcs) or 'none'}){span}.**")
    d = ", ".join(f"{v} {k}" for k, v in dropped.items() if v)
    if d:
        lines.append(f"Dropped rows: {d}.")
    if n < 30 or len(srcs) < 3:
        lines.append("")
        lines.append("> Small sample. Treat every theme below as a lead, not a trend.")
    lines += ["", "## Themes, ranked", ""]
    for t in ranked:
        flag = " (thin)" if t["thin"] else ""
        lines.append(f"### {t['title']}{flag}")
        lines.append(f"{t['count']} reviews across {len(t['sources'])} sources ({', '.join(t['sources'])}); weight {t['score']}")
        for q in t["quotes"]:
            rate = f"{q['rating']} stars, " if q["rating"] else ""
            tail = " [cut]" if q["cut"] else ""
            lines.append(f"- \"{q['quote']}\"{tail} ({rate}{q['source']}) <{q['url']}>")
        lines.append("")
    if not ranked:
        lines += ["No theme matched. Edit themes.json for this app's category.", ""]
    lines += ["## Requests, in the users' words", ""]
    seen = set()
    shown = 0
    for s, r in sorted(requests, key=lambda x: -x[1]["weight"]):
        k = norm_space(s)
        if k in seen:
            continue
        seen.add(k)
        lines.append(f"- \"{s}\" ({r['source']}) <{r['url']}>")
        shown += 1
        if shown >= 15:
            break
    if not shown:
        lines.append("- none found")
    lines += ["", "## Low ratings no theme caught (read these by hand)", ""]
    for r in sorted(unmatched, key=lambda x: -x["weight"])[:15]:
        q, cut = best_quote(r["text"], [])
        lines.append(f"- \"{q}\"{' [cut]' if cut else ''} ({r['rating']} stars, {r['source']}) <{r['url']}>")
    if not unmatched:
        lines.append("- none")
    return "\n".join(lines) + "\n"


def run(args):
    reviews, dropped = load_reviews(args.csv)
    themes_path = args.themes or os.path.join(HERE, "themes.default.json")
    themes = read_json(themes_path)
    if not themes:
        raise SystemExit(f"error: could not read themes from {themes_path}")
    ranked, unmatched, requests = analyse(reviews, themes)
    if args.json:
        print(json.dumps({"reviews": len(reviews), "dropped": dropped, "themes": ranked}, indent=2))
        return 0
    text = render(reviews, dropped, ranked, unmatched, requests)
    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(text)
        print(f"wrote {args.out}: {len(reviews)} reviews, {len(ranked)} themes")
    else:
        print(text)
    return 0
