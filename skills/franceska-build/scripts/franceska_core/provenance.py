"""Provenance log: where every fact about the original came from, and on what basis."""
import re

from .core import Report, read_csv, today, wdir, write_csv

FIELDS = ["id", "stage", "kind", "ref", "accessed", "basis", "terms_checked", "used_for", "notes"]
KINDS = {"help-docs", "pricing-page", "changelog", "store-listing", "walkthrough", "marketing-site",
         "own-account", "public-api-docs", "review", "screenshot", "user-supplied", "other"}
BANNED_KINDS = {"network-log", "source-code", "js-bundle", "decompiled", "private-api", "scraped-dump",
                "other-persons-account", "paywall-bypass"}
BASES = {"public", "own-account", "official-api", "user-supplied"}


def path(root):
    return wdir(root, "provenance.csv")


def load(root):
    return read_csv(path(root))


def add(root, stage, kind, ref, basis, used_for, terms_checked="n/a", notes=""):
    rows = load(root)
    n = len(rows) + 1
    rows.append({"id": f"P{n:02d}", "stage": stage, "kind": kind, "ref": ref, "accessed": today(),
                 "basis": basis, "terms_checked": terms_checked, "used_for": used_for, "notes": notes})
    write_csv(path(root), FIELDS, rows)
    return rows[-1]["id"]


def check(root):
    rep = Report("Provenance")
    rows = load(root)
    if not rows:
        rep.fail("provenance.csv is empty or missing: log every source with `source add`")
        return rep
    rep.ok(f"{len(rows)} sources logged")
    for r in rows:
        rid = r.get("id") or "?"
        kind, basis = r.get("kind", "").lower(), r.get("basis", "").lower()
        if kind in BANNED_KINDS:
            rep.fail(f"{rid}: source kind '{kind}' is not allowed (private or protected material)")
        elif kind not in KINDS:
            rep.warn(f"{rid}: unknown kind '{kind}'")
        if basis not in BASES:
            rep.fail(f"{rid}: basis must be one of {', '.join(sorted(BASES))}")
        if not r.get("ref"):
            rep.fail(f"{rid}: no URL or description in ref")
        if basis == "own-account" or kind == "own-account":
            tc = r.get("terms_checked", "").lower()
            if tc == "restricted":
                rep.fail(f"{rid}: the account's terms restrict building a competing product. Use public sources only")
            elif tc != "yes":
                rep.fail(f"{rid}: own-account source needs terms_checked=yes (read the app's terms first)")
        if kind in ("help-docs", "pricing-page", "store-listing", "review", "public-api-docs") and \
                not re.match(r"^https?://", r.get("ref", "")):
            rep.warn(f"{rid}: {kind} should have a URL in ref")
    if not any(r.get("kind", "").lower() != "review" for r in rows):
        rep.warn("only review sources logged; add help docs, pricing or store listing")
    return rep
