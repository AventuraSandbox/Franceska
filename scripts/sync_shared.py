#!/usr/bin/env python3
"""Copy shared/franceska_core and shared/fr.py into every skill's scripts/ folder.

Each skill must work on its own when uploaded alone to claude.ai, so the tools are vendored.
Edit shared/, run this, commit the result. tests/test_repo.py fails if a copy has drifted.
"""
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILLS = os.path.join(ROOT, "skills")
SHARED = os.path.join(ROOT, "shared")


def main():
    for name in sorted(os.listdir(SKILLS)):
        sk = os.path.join(SKILLS, name)
        if not os.path.isfile(os.path.join(sk, "SKILL.md")):
            continue
        dest = os.path.join(sk, "scripts")
        if os.path.isdir(dest):
            shutil.rmtree(dest)
        shutil.copytree(os.path.join(SHARED, "franceska_core"), os.path.join(dest, "franceska_core"),
                        ignore=shutil.ignore_patterns("__pycache__"))
        shutil.copy2(os.path.join(SHARED, "fr.py"), os.path.join(dest, "fr.py"))
        print("synced", name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
