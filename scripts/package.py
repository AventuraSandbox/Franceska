#!/usr/bin/env python3
"""Zip every skill for upload to claude.ai (Settings > Capabilities > Skills).

Each zip has the skill folder at its root, SKILL.md inside it, and no caches.
Writes dist/<skill>.zip and dist/franceska-all.zip (all folders, for plugin-style copying).
"""
import os
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILLS = os.path.join(ROOT, "skills")
DIST = os.path.join(ROOT, "dist")


def add_tree(zf, base, arc_root):
    for d, dirs, files in os.walk(base):
        dirs[:] = [x for x in dirs if x != "__pycache__"]
        for f in sorted(files):
            if f.endswith(".pyc"):
                continue
            full = os.path.join(d, f)
            zf.write(full, os.path.join(arc_root, os.path.relpath(full, base)))


def main():
    os.makedirs(DIST, exist_ok=True)
    names = sorted(n for n in os.listdir(SKILLS) if os.path.isfile(os.path.join(SKILLS, n, "SKILL.md")))
    for n in names:
        with zipfile.ZipFile(os.path.join(DIST, f"{n}.zip"), "w", zipfile.ZIP_DEFLATED) as zf:
            add_tree(zf, os.path.join(SKILLS, n), n)
    with zipfile.ZipFile(os.path.join(DIST, "franceska-all.zip"), "w", zipfile.ZIP_DEFLATED) as zf:
        for n in names:
            add_tree(zf, os.path.join(SKILLS, n), os.path.join("franceska", n))
    print(f"wrote {len(names)} skill zips and franceska-all.zip to {DIST}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
