"""Shared helpers: project root, JSON/CSV IO, a small check-report class."""
import csv
import hashlib
import json
import os
import re
import sys
from datetime import date

WORKDIR = "franceska"          # the folder inside the user's project
SKIP_DIRS = {
    "node_modules", ".git", ".next", "dist", "build", "out", ".venv", "venv",
    "__pycache__", ".turbo", ".cache", "coverage", "target", "Pods",
    ".expo", ".gradle", "DerivedData", WORKDIR,
}
TEXT_LIMIT = 2_000_000


def today():
    return date.today().isoformat()


def find_root(explicit=None):
    """Project root = the directory that holds franceska/. Search upward from cwd."""
    if explicit:
        return os.path.abspath(explicit)
    cur = os.path.abspath(os.getcwd())
    while True:
        if os.path.isdir(os.path.join(cur, WORKDIR)):
            return cur
        parent = os.path.dirname(cur)
        if parent == cur:
            return os.path.abspath(os.getcwd())
        cur = parent


def wdir(root, *parts):
    return os.path.join(root, WORKDIR, *parts)


def read_text(path, default=""):
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except OSError:
        return default


def write_text(path, text):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


def read_json(path, default=None):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except FileNotFoundError:
        return default
    except json.JSONDecodeError as exc:
        raise SystemExit(f"error: {path} is not valid JSON ({exc})")


def write_json(path, data):
    write_text(path, json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def read_csv(path):
    """List of dicts with lower-cased, stripped headers. Missing file -> []."""
    try:
        with open(path, newline="", encoding="utf-8-sig") as fh:
            rows = list(csv.DictReader(fh))
    except FileNotFoundError:
        return []
    out = []
    for row in rows:
        out.append({(k or "").strip().lower(): (v or "").strip() for k, v in row.items()})
    return out


def write_csv(path, fieldnames, rows):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)


def walk_text_files(root, extra_skip=()):
    """Yield (relpath, text) for readable text files, skipping build/vendor dirs."""
    skip = SKIP_DIRS | set(extra_skip)
    for base, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in skip]
        for name in files:
            full = os.path.join(base, name)
            try:
                if os.path.getsize(full) > TEXT_LIMIT:
                    continue
                with open(full, "rb") as fh:
                    raw = fh.read()
            except OSError:
                continue
            if b"\0" in raw[:4096]:
                continue
            yield os.path.relpath(full, root), raw.decode("utf-8", errors="replace")


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def norm_words(text):
    return re.findall(r"[a-z0-9']+", text.lower().replace("’", "'"))


def norm_space(text):
    text = text.replace("’", "'").replace("‘", "'")
    text = text.replace("“", '"').replace("”", '"')
    return re.sub(r"\s+", " ", text).strip().lower()


class Report:
    """Ordered list of ok / warn / fail lines. Fails make the exit code 1."""

    ICON = {"ok": "PASS", "warn": "WARN", "fail": "FAIL"}

    def __init__(self, title=""):
        self.title = title
        self.items = []

    def ok(self, msg):
        self.items.append(("ok", msg))

    def warn(self, msg):
        self.items.append(("warn", msg))

    def fail(self, msg):
        self.items.append(("fail", msg))

    def check(self, cond, ok_msg, fail_msg, level="fail"):
        (self.ok if cond else getattr(self, level))(ok_msg if cond else fail_msg)
        return cond

    def extend(self, other):
        self.items.extend(other.items)

    @property
    def failed(self):
        return any(k == "fail" for k, _ in self.items)

    def counts(self):
        return {k: sum(1 for x, _ in self.items if x == k) for k in ("ok", "warn", "fail")}

    def render(self):
        lines = [self.title] if self.title else []
        for kind, msg in self.items:
            lines.append(f"  {self.ICON[kind]}  {msg}")
        c = self.counts()
        lines.append(f"  -> {c['ok']} passed, {c['warn']} warnings, {c['fail']} failed")
        return "\n".join(lines)

    def to_markdown(self):
        out = []
        for kind, msg in self.items:
            mark = {"ok": "[x]", "warn": "[~]", "fail": "[ ]"}[kind]
            out.append(f"- {mark} **{self.ICON[kind]}** {msg}")
        return "\n".join(out)


def die(msg, code=2):
    print(f"error: {msg}", file=sys.stderr)
    raise SystemExit(code)
