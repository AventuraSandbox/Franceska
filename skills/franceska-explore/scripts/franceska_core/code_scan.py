"""Find leftovers of the original app (names, domains, colours) and leaked secrets."""
import fnmatch
import json
import os
import re

from .core import read_json, walk_text_files

SECRET_PATTERNS = [
    ("Stripe live key", re.compile(r"\b(?:sk|rk)_live_[0-9A-Za-z]{10,}")),
    ("AWS access key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("private key block", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    ("Google API key", re.compile(r"\bAIza[0-9A-Za-z_\-]{35}\b")),
    ("GitHub token", re.compile(r"\bgh[pousr]_[0-9A-Za-z]{30,}\b")),
    ("Slack token", re.compile(r"\bxox[abprs]-[0-9A-Za-z-]{10,}")),
]


def term_patterns(term):
    """Regexes that catch a name in prose and inside identifiers (OriginalApp, original_app)."""
    words = [w for w in re.split(r"[\s_\-.]+", term.strip()) if w]
    if not words:
        return []
    joined = "".join(words)
    if len(words) == 1 and len(joined) < 5:
        # short names: only catch standalone or CamelCase starts, not 'cal' in 'calendar'
        forms = {joined.lower(), joined.capitalize(), joined.upper()}
        return [re.compile(r"(?<![A-Za-z])" + re.escape(f) + r"(?![a-z])") for f in forms]
    sep = r"[\s_\-.]*"
    return [re.compile(sep.join(re.escape(w) for w in words), re.I)]


def color_forms(hexval):
    h = hexval.strip().lstrip("#").lower()
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    if len(h) != 6:
        return None
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return [
        re.compile(r"#" + h, re.I),
        re.compile(rf"rgba?\(\s*{r}\s*,\s*{g}\s*,\s*{b}\b", re.I),
        re.compile(rf"rgba?\(\s*{r}\s+{g}\s+{b}\b", re.I),
    ]


def allowed(rel, term, line, allow):
    for a in allow or []:
        if a.get("path") and not fnmatch.fnmatch(rel, a["path"]):
            continue
        if a.get("term") and a["term"].lower() not in term.lower():
            continue
        return a
    return None


def scan(root, avoid=(), domains=(), colors=(), allow=()):
    hits, allowed_hits = [], []
    pats = []
    for t in avoid:
        for p in term_patterns(t):
            pats.append(("name", t, p))
    for d in domains:
        pats.append(("domain", d, re.compile(re.escape(d.strip().lower()), re.I)))
    for c in colors:
        forms = color_forms(c)
        if forms:
            for p in forms:
                pats.append(("colour", c, p))
    for rel, text in walk_text_files(root):
        # file names count too
        for kind, term, p in pats:
            if p.search(rel):
                rec = (rel, 0, kind, term, "(file name)")
                (allowed_hits if allowed(rel, term, "", allow) else hits).append(rec)
        for n, line in enumerate(text.splitlines(), start=1):
            for kind, term, p in pats:
                if p.search(line):
                    rec = (rel, n, kind, term, line.strip()[:120])
                    a = allowed(rel, term, line, allow)
                    (allowed_hits if a else hits).append(rec)
    return hits, allowed_hits


def scan_secrets(root):
    found = []
    for rel, text in walk_text_files(root):
        base = os.path.basename(rel)
        if base in (".env.example", ".env.sample"):
            continue
        for n, line in enumerate(text.splitlines(), start=1):
            for name, p in SECRET_PATTERNS:
                if p.search(line):
                    found.append((rel, n, name))
    return found


def run(args):
    cfg = {}
    if args.config:
        cfg = read_json(args.config) or {}
        if not cfg:
            raise SystemExit(f"error: could not read {args.config}")
    avoid = list(cfg.get("avoid", [])) + [x for x in (args.avoid or "").split(",") if x.strip()]
    domains = list(cfg.get("domains", [])) + [x for x in (args.domains or "").split(",") if x.strip()]
    colors = list(cfg.get("colors", [])) + [x for x in (args.colors or "").split(",") if x.strip()]
    if not (avoid or domains or colors):
        raise SystemExit("error: nothing to search for. Give --avoid / --domains / --colors or --config")
    hits, ok_hits = scan(args.path, avoid, domains, colors, cfg.get("allow", []))
    secrets = scan_secrets(args.path) if args.secrets else []
    if args.json:
        print(json.dumps({"hits": hits, "allowed": ok_hits, "secrets": secrets}, indent=2))
    else:
        for rel, n, kind, term, snip in hits:
            print(f"{rel}:{n}: {kind} '{term}': {snip}")
        for rel, n, name in secrets:
            print(f"{rel}:{n}: SECRET {name}")
        for rel, n, kind, term, snip in ok_hits:
            print(f"(allowed) {rel}:{n}: {kind} '{term}'")
        print(f"-> {len(hits)} leftovers, {len(secrets)} secrets, {len(ok_hits)} allowed mentions")
    return 1 if (hits or secrets) else 0
