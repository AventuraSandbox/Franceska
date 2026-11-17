"""Lint an App Store / Google Play listing: limits, claims, wasted keywords, the original's name."""
import json
import re

from .core import Report, read_json

LIMITS = {
    "app_store": {"name": 30, "subtitle": 30, "promotional_text": 170, "keywords": 100, "description": 4000},
    "google_play": {"title": 30, "short_description": 80, "full_description": 4000},
}
SHORT_FIELDS = {"app_store": ("name", "subtitle"), "google_play": ("title", "short_description")}
RANKING = re.compile(r"(#\s?1\b|\bno\.?\s?1\b|number one|\bbest\b|\btop[- ](rated|app|\d+)|\bleading\b|award[- ]winning)", re.I)
PRICE = re.compile(r"(\bfree\b|\bdiscount|\bsale\b|\d+\s?% off|[$€£]\s?\d)", re.I)
EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿⭐⭕]")


def terms_regex(terms):
    parts = []
    for t in terms:
        words = [w for w in re.split(r"[\s_\-.]+", t.strip()) if w]
        if words:
            parts.append(r"[\s_\-.]*".join(re.escape(w) for w in words))
    return re.compile("|".join(parts), re.I) if parts else None


def lint(data):
    rep = Report("Store listing")
    avoid = terms_regex(data.get("avoid", []))
    found_any = False
    for store, limits in LIMITS.items():
        block = data.get(store)
        if not block:
            continue
        found_any = True
        for field, limit in limits.items():
            val = block.get(field, "")
            n = len(val)
            if not val:
                rep.warn(f"{store}.{field} is empty")
                continue
            if n > limit:
                rep.fail(f"{store}.{field} is {n} characters, limit {limit}")
            else:
                rep.ok(f"{store}.{field}: {n}/{limit}")
            if avoid and avoid.search(val):
                rep.fail(f"{store}.{field} contains a name from 'avoid' (the original's brand)")
            if field in SHORT_FIELDS[store]:
                if RANKING.search(val):
                    rep.fail(f"{store}.{field} makes a ranking claim; the stores reject these in titles")
                if PRICE.search(val):
                    rep.fail(f"{store}.{field} makes a price or promo claim; stores reject these in short fields")
                if EMOJI.search(val):
                    rep.warn(f"{store}.{field} contains emoji; both stores discourage it in titles")
                if val.isupper() and len(val) > 3:
                    rep.warn(f"{store}.{field} is ALL CAPS")
        if store == "app_store":
            kw = block.get("keywords", "")
            if ", " in kw or " ," in kw:
                rep.warn("app_store.keywords has spaces around commas; each space is a wasted character")
            words = [w.strip().lower() for w in kw.split(",") if w.strip()]
            dupes = sorted({w for w in words if words.count(w) > 1})
            if dupes:
                rep.warn("app_store.keywords repeats: " + ", ".join(dupes))
            title_words = set(re.findall(r"[a-z0-9]+", (block.get("name", "") + " " + block.get("subtitle", "")).lower()))
            overlap = sorted(w for w in words if w in title_words)
            if overlap:
                rep.warn("app_store.keywords repeats words already in name/subtitle (already indexed): " + ", ".join(overlap))
    if not found_any:
        rep.fail("no app_store or google_play block found")
    if not data.get("avoid"):
        rep.warn("'avoid' is empty, so the original's name was not checked")
    return rep


def run(args):
    data = read_json(args.listing)
    if data is None:
        raise SystemExit(f"error: {args.listing} not found")
    if args.config:
        cfg = read_json(args.config) or {}
        data["avoid"] = list(data.get("avoid", [])) + list(cfg.get("avoid", []))
    rep = lint(data)
    print(json.dumps(rep.counts()) if args.json else rep.render())
    return 1 if rep.failed else 0
