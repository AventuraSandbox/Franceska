import hashlib
import json
import os
import re
import unittest

import _load  # noqa: F401
from _load import ROOT

SKILLS = os.path.join(ROOT, "skills")
NAMES = sorted(n for n in os.listdir(SKILLS) if os.path.isfile(os.path.join(SKILLS, n, "SKILL.md")))
EXPECTED = ["franceska", "franceska-brand", "franceska-build", "franceska-compare", "franceska-connect",
            "franceska-design", "franceska-explore", "franceska-launch", "franceska-plan", "franceska-publish",
            "franceska-review", "franceska-test", "franceska-validate"]


def read_bytes(p):
    with open(p, "rb") as fh:
        return fh.read()


def read(p):
    with open(p, encoding="utf-8") as fh:
        return fh.read()


def frontmatter(text):
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    assert m, "no frontmatter"
    body = m.group(1)
    name = re.search(r"^name:\s*(\S+)\s*$", body, re.M).group(1)
    desc = re.search(r"^description:\s*>-?\n((?:[ ]{2}.*\n?)+)", body + "\n", re.M)
    return name, " ".join(l.strip() for l in desc.group(1).splitlines())


def tree_hash(path):
    h = hashlib.sha256()
    for d, dirs, files in sorted(os.walk(path)):
        dirs[:] = sorted(x for x in dirs if x != "__pycache__")
        for f in sorted(files):
            if f.endswith(".pyc"):
                continue
            h.update(os.path.relpath(os.path.join(d, f), path).encode())
            h.update(read_bytes(os.path.join(d, f)))
    return h.hexdigest()


class RepoTests(unittest.TestCase):
    def test_all_skills_present(self):
        self.assertEqual(NAMES, EXPECTED)

    def test_frontmatter(self):
        for n in NAMES:
            name, desc = frontmatter(read(os.path.join(SKILLS, n, "SKILL.md")))
            self.assertEqual(name, n)
            self.assertTrue(40 < len(desc) <= 1024, f"{n}: description length {len(desc)}")
            self.assertNotRegex(desc, r"[<>]")
            self.assertNotIn("claude", n)

    def test_vendored_tools_match_shared(self):
        want = tree_hash(os.path.join(ROOT, "shared", "franceska_core"))
        fr = read_bytes(os.path.join(ROOT, "shared", "fr.py"))
        for n in NAMES:
            self.assertEqual(tree_hash(os.path.join(SKILLS, n, "scripts", "franceska_core")), want,
                             f"{n}: run scripts/sync_shared.py")
            self.assertEqual(read_bytes(os.path.join(SKILLS, n, "scripts", "fr.py")), fr)

    def test_every_command_in_skills_exists(self):
        from franceska_core.cli import build_parser
        cmds = set(build_parser()._subparsers._group_actions[0].choices)
        for n in NAMES:
            text = read(os.path.join(SKILLS, n, "SKILL.md"))
            for m in re.finditer(r"\$FR\s+(?:--project\s+\S+\s+)?([a-z_]+)", text):
                self.assertIn(m.group(1), cmds, f"{n}: unknown command {m.group(1)}")

    def test_cross_references_resolve(self):
        for n in NAMES:
            text = read(os.path.join(SKILLS, n, "SKILL.md"))
            for ref in set(re.findall(r"franceska-[a-z]+", text)):
                self.assertIn(ref, NAMES, f"{n} mentions missing skill {ref}")
            for t in re.findall(r"`(templates/[\w.\-]+)`", text):
                self.assertTrue(os.path.isfile(os.path.join(SKILLS, n, t)), f"{n}: missing {t}")

    def test_every_skill_has_gate_section(self):
        for n in NAMES:
            if n == "franceska":
                continue
            text = read(os.path.join(SKILLS, n, "SKILL.md"))
            self.assertIn("## Exit gate", text, n)
            self.assertIn(f"start {n.split('-', 1)[1]}", text)

    def test_manifests(self):
        for f in ("plugin.json", "marketplace.json"):
            json.loads(read(os.path.join(ROOT, ".claude-plugin", f)))
        self.assertEqual(json.loads(read(os.path.join(ROOT, ".claude-plugin", "plugin.json")))["skills"], "./skills/")

    def test_templates_parse(self):
        json.loads(read(os.path.join(SKILLS, "franceska-design", "templates", "tokens.json")))
        json.loads(read(os.path.join(SKILLS, "franceska-launch", "templates", "listing.example.json")))
        json.loads(read(os.path.join(SKILLS, "franceska-brand", "templates", "brand.json")))
        json.loads(read(os.path.join(SKILLS, "franceska-validate", "templates", "themes.json")))

    def test_no_notice_file(self):
        self.assertFalse(os.path.exists(os.path.join(ROOT, "NOTICE")))

    def test_no_non_stdlib_imports(self):
        import sys
        std = set(sys.stdlib_module_names)
        src = os.path.join(ROOT, "shared", "franceska_core")
        for f in os.listdir(src):
            if f.endswith(".py"):
                for m in re.finditer(r"^(?:import|from)\s+([a-zA-Z_]+)", read(os.path.join(src, f)), re.M):
                    self.assertTrue(m.group(1) in std or m.group(1) == "franceska_core", f"{f}: {m.group(1)}")


if __name__ == "__main__":
    unittest.main()
