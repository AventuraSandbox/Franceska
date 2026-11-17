"""Feature coverage score from features.csv (+ optional layout scores)."""
import json
import os
import re

from .core import read_csv

WEIGHT = {"must": 3, "should": 2, "could": 1}
EFFORT = {"s": 0, "m": 1, "l": 2, "xl": 3, "": 1}
DONE = {"yes": 1.0, "partial": 0.5}
VALID_CLONE = {"yes", "partial", "no", "skip"}


def load_features(path):
    rows = read_csv(path)
    for r in rows:
        r["priority"] = r.get("priority", "").lower()
        r["yours"] = r.get("yours", "").lower() or "no"
        r["original"] = r.get("original", "").lower() or "yes"
    return rows


def validate(rows):
    problems = []
    for i, r in enumerate(rows, start=2):
        if r["priority"] not in WEIGHT:
            problems.append(f"row {i} ({r.get('feature','?')}): priority must be must/should/could")
        if r["yours"] not in VALID_CLONE:
            problems.append(f"row {i} ({r.get('feature','?')}): yours must be yes/partial/no/skip")
        if r["yours"] == "skip" and not r.get("notes"):
            problems.append(f"row {i} ({r.get('feature','?')}): skip needs a reason in notes")
        if r["yours"] == "partial" and not r.get("notes"):
            problems.append(f"row {i} ({r.get('feature','?')}): partial needs a note on what is missing")
    return problems


def score(rows, layout_scores=None):
    scored = [r for r in rows if r["yours"] != "skip" and r["original"] != "no" and r["priority"] in WEIGHT]
    extras = [r for r in rows if r["original"] == "no"]
    skipped = [r for r in rows if r["yours"] == "skip"]
    total_w = sum(WEIGHT[r["priority"]] for r in scored)
    got_w = sum(WEIGHT[r["priority"]] * DONE.get(r["yours"], 0.0) for r in scored)
    feature = round(100.0 * got_w / total_w, 1) if total_w else 0.0

    musts = [r for r in scored if r["priority"] == "must"]
    musts_done = [r for r in musts if r["yours"] == "yes"]
    musts_missing = [r for r in musts if r["yours"] != "yes"]

    areas = {}
    for r in scored:
        a = areas.setdefault(r.get("area") or "(none)", [0, 0.0])
        a[0] += WEIGHT[r["priority"]]
        a[1] += WEIGHT[r["priority"]] * DONE.get(r["yours"], 0.0)
    area_rows = sorted(
        ((k, round(100.0 * v[1] / v[0], 1)) for k, v in areas.items() if v[0]),
        key=lambda kv: kv[1],
    )

    missing = [r for r in scored if r["yours"] in ("no", "partial")]
    missing.sort(key=lambda r: (-WEIGHT[r["priority"]], EFFORT.get(r.get("effort", "").lower(), 1), r["yours"] != "partial"))

    layout = None
    if layout_scores:
        layout = round(sum(layout_scores.values()) / len(layout_scores), 1)

    overall = feature if layout is None else round(0.8 * feature + 0.2 * layout, 1)
    return {
        "feature_score": feature,
        "layout_score": layout,
        "overall": overall,
        "musts_total": len(musts),
        "musts_done": len(musts_done),
        "musts_missing": [r["feature"] for r in musts_missing],
        "areas": area_rows,
        "missing": [
            {"feature": r["feature"], "priority": r["priority"], "yours": r["yours"],
             "effort": r.get("effort", ""), "notes": r.get("notes", "")}
            for r in missing
        ],
        "extras": len(extras),
        "skipped": len(skipped),
        "counted": len(scored),
    }


def verdict(result, open_blockers=0):
    if result["musts_missing"] or open_blockers:
        return "not shippable"
    if result["feature_score"] >= 80:
        return "shippable"
    return "not shippable"


def load_layout(paths):
    out = {}
    for p in paths:
        try:
            with open(p, encoding="utf-8") as fh:
                d = json.load(fh)
        except (OSError, json.JSONDecodeError):
            continue
        if "score" in d:
            out[os.path.splitext(os.path.basename(p))[0]] = float(d["score"])
    return out


def render(result, verdict_text, markdown=False):
    h = "## " if markdown else ""
    lines = []
    lines.append(f"{h}Coverage: {result['overall']}  (features {result['feature_score']}"
                 + (f", layout {result['layout_score']}" if result["layout_score"] is not None else "") + ")")
    lines.append(f"Must-haves: {result['musts_done']} of {result['musts_total']} done")
    lines.append(f"Counted {result['counted']} features; {result['extras']} extras you added and "
                 f"{result['skipped']} deliberate skips are not scored")
    lines.append(f"Verdict: {verdict_text}")
    if result["musts_missing"]:
        lines.append("Missing must-haves: " + "; ".join(result["musts_missing"]))
    lines.append("")
    lines.append(f"{h}Areas, weakest first")
    for name, pct in result["areas"]:
        lines.append(f"- {name}: {pct}")
    lines.append("")
    lines.append(f"{h}Missing, in build order")
    for m in result["missing"]:
        tag = "partial" if m["yours"] == "partial" else "no"
        extra = f" ({m['notes']})" if m["notes"] else ""
        lines.append(f"- [{m['priority']}] {m['feature']} - {tag}{extra}")
    if not result["missing"]:
        lines.append("- nothing")
    return "\n".join(lines)


def run(args):
    rows = load_features(args.csv)
    if not rows:
        raise SystemExit(f"error: no rows in {args.csv}")
    problems = validate(rows)
    layout = load_layout(args.visual or [])
    res = score(rows, layout)
    v = verdict(res, args.blockers)
    if args.json:
        print(json.dumps({**res, "verdict": v, "problems": problems}, indent=2))
    else:
        if problems:
            print("Fix the sheet first:")
            for p in problems:
                print("  - " + p)
            print()
        print(render(res, v, markdown=args.markdown))
    return 0 if (v == "shippable" and not problems) else 1
