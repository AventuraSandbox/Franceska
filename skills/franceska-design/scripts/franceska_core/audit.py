"""Clean-room audit: provenance, shipped references, copied copy, leftovers, secrets, asset ledger."""
import os
import re

from . import provenance
from .core import (Report, SKIP_DIRS, find_root, norm_words, read_csv, read_json, read_text,
                   sha256_file, today, walk_text_files, wdir, write_text)
from .code_scan import scan, scan_secrets

UI_EXT = {".tsx", ".jsx", ".ts", ".js", ".mjs", ".vue", ".svelte", ".html", ".htm", ".json", ".md",
          ".swift", ".kt", ".xml", ".strings", ".dart", ".erb", ".py", ".rb", ".php", ".astro", ".mdx"}
IGNORE_NAMES = {"package-lock.json", "yarn.lock", "pnpm-lock.yaml", "tsconfig.json"}
ASSET_EXT = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".ico", ".icns", ".ttf", ".otf", ".woff", ".woff2", ".mp3", ".wav", ".mp4"}


def all_files(root):
    for base, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for f in files:
            yield os.path.join(base, f)


def copy_overlap(root, strings):
    """Original UI strings that appear (normalised) inside your app's source."""
    targets = []
    for rel, text in walk_text_files(root):
        if os.path.splitext(rel)[1].lower() in UI_EXT and os.path.basename(rel) not in IGNORE_NAMES:
            targets.append((rel, " " + " ".join(norm_words(text)) + " "))
    hits = []
    for s in strings:
        words = norm_words(s)
        if len(words) < 3:
            continue
        phrase = " " + " ".join(words) + " "
        windows = [phrase] if len(words) < 8 else \
            [" " + " ".join(words[i:i + 6]) + " " for i in range(len(words) - 5)]
        for rel, blob in targets:
            if any(w in blob for w in windows):
                hits.append((rel, s, len(words)))
    return hits


def run_audit(root, write=True):
    rep = Report("Clean-room audit")
    rep.extend(provenance.check(root))

    # 1. reference screenshots must never ship
    ref_dir = wdir(root, "screens")
    ref_hashes = {}
    if os.path.isdir(ref_dir):
        for f in all_files(ref_dir):
            try:
                ref_hashes[sha256_file(f)] = os.path.relpath(f, ref_dir)
            except OSError:
                pass
    shipped = [(os.path.relpath(p, root), ref_hashes[h]) for p in all_files(root)
               for h in [sha256_file(p)] if h in ref_hashes] if ref_hashes else []
    rep.check(not shipped, f"none of the {len(ref_hashes)} reference screenshots appear in the project",
              "reference screenshots found in the project: " + "; ".join(f"{a} = {b}" for a, b in shipped[:5]))
    refs = [rel for rel, text in walk_text_files(root)
            if re.search(r"franceska/screens", text)]
    rep.check(not refs, "no source file points at the reference screenshots",
              "source references reference screenshots: " + ", ".join(refs[:5]))

    # 2. copied copy
    strings_file = wdir(root, "original-strings.txt")
    strings = [l.strip() for l in read_text(strings_file).splitlines() if l.strip() and not l.startswith("#")]
    if not strings:
        rep.warn("franceska/original-strings.txt is missing or empty, so copied wording could not be checked")
    else:
        hits = copy_overlap(root, strings)
        strict = [h for h in hits if h[2] >= 4]
        soft = [h for h in hits if h[2] == 3]
        rep.check(not strict, f"no wording from {len(strings)} recorded original strings found in the code",
                  "original wording found in the code: " + "; ".join(f"{r}: \"{s[:50]}\"" for r, s, _ in strict[:5]))
        for r, s, _ in soft[:5]:
            rep.warn(f"3-word phrase matches the original (probably generic, check): {r}: \"{s}\"")

    # 3. leftovers of the original brand
    brand = read_json(wdir(root, "brand.json"))
    if not brand:
        rep.warn("franceska/brand.json missing: names, domains and colours were not swept")
    else:
        hits, allowed_hits = scan(root, brand.get("avoid", []), brand.get("domains", []),
                                  brand.get("colors", []), brand.get("allow", []))
        rep.check(not hits, "code scan is clean",
                  f"{len(hits)} leftovers of the original: " + "; ".join(f"{h[0]}:{h[1]}" for h in hits[:5]))
        for rel, n, kind, term, _ in allowed_hits:
            rep.warn(f"allowed mention of '{term}' in {rel} (check the reason in brand.json)")
        for a in brand.get("allow", []):
            if not a.get("reason"):
                rep.fail(f"allow entry for {a.get('path') or a.get('term')} has no reason")

    # 4. secrets
    secrets = scan_secrets(root)
    rep.check(not secrets, "no secrets in the code",
              "secrets in the code: " + "; ".join(f"{r}:{n} {k}" for r, n, k in secrets[:5]))

    # 5. asset ledger
    ledger = {r.get("path", ""): r for r in read_csv(wdir(root, "assets.csv"))}
    assets = [os.path.relpath(p, root) for p in all_files(root)
              if os.path.splitext(p)[1].lower() in ASSET_EXT]
    unlisted = [a for a in assets if a not in ledger]
    if assets:
        if unlisted:
            rep.warn(f"{len(unlisted)} of {len(assets)} image/font/audio files are not in franceska/assets.csv "
                     f"(path, source, license), e.g. {unlisted[0]}")
        else:
            rep.ok(f"all {len(assets)} assets have a source and licence")
        for p, r in ledger.items():
            if not r.get("license"):
                rep.fail(f"asset {p} has no licence in assets.csv")

    # 6. overrides are surfaced, never hidden
    state = read_json(wdir(root, "state.json"), {}) or {}
    for o in state.get("overrides", []):
        rep.warn(f"gate override on '{o['stage']}': {o['reason']} ({o['at']})")

    if write:
        body = (f"# Clean-room audit\n\nRun {today()}. Result: **{'FAIL' if rep.failed else 'PASS'}**\n\n"
                + rep.to_markdown() + "\n\nThis is a screening tool, not legal advice.\n")
        write_text(wdir(root, "review.md"), body)
    return rep


def run(args):
    root = find_root(args.project)
    rep = run_audit(root)
    print(rep.render())
    return 1 if rep.failed else 0
