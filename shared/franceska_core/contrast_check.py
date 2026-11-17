"""WCAG contrast checker for design tokens (light and optional dark mode)."""
import json
import re

from .core import read_json

HEX = re.compile(r"^#?([0-9a-fA-F]{3}|[0-9a-fA-F]{4}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$")


def parse_hex(value, over=None):
    m = HEX.match(value.strip())
    if not m:
        raise ValueError(f"not a hex colour: {value!r}")
    h = m.group(1)
    if len(h) in (3, 4):
        h = "".join(c * 2 for c in h)
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    a = int(h[6:8], 16) / 255 if len(h) == 8 else 1.0
    if a < 1.0 and over:
        orr, og, ob = over
        r, g, b = (round(a * c + (1 - a) * o) for c, o in ((r, orr), (g, og), (b, ob)))
    return r, g, b


def _lin(c):
    c = c / 255
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def luminance(rgb):
    r, g, b = (_lin(x) for x in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def ratio(fg, bg):
    l1, l2 = luminance(fg), luminance(bg)
    hi, lo = max(l1, l2), min(l1, l2)
    return (hi + 0.05) / (lo + 0.05)


def check_mode(colors, pairs, mode):
    results = []
    for p in pairs:
        if isinstance(p, dict):
            fg, bg, need, label = p["fg"], p["bg"], float(p.get("min", 4.5)), p.get("label", "")
        else:
            fg, bg = p[0], p[1]
            need = float(p[2]) if len(p) > 2 else 4.5
            label = p[3] if len(p) > 3 else ""
        if fg not in colors or bg not in colors:
            results.append((mode, fg, bg, need, None, label, f"unknown role {fg if fg not in colors else bg}"))
            continue
        bg_rgb = parse_hex(colors[bg])
        fg_rgb = parse_hex(colors[fg], over=bg_rgb)
        results.append((mode, fg, bg, need, ratio(fg_rgb, bg_rgb), label, ""))
    return results


def run(args):
    tokens = read_json(args.tokens)
    if tokens is None:
        raise SystemExit(f"error: {args.tokens} not found")
    pairs = tokens.get("pairs") or []
    if not pairs:
        raise SystemExit("error: tokens.json has no 'pairs' list (fg, bg, min ratio) - nothing to check")
    modes = {"light": tokens.get("colors", {})}
    if tokens.get("colors_dark"):
        modes["dark"] = tokens["colors_dark"]
    allres = []
    for mode, colors in modes.items():
        allres += check_mode(colors, pairs, mode)
    bad = 0
    rows = []
    for mode, fg, bg, need, got, label, err in allres:
        if got is None:
            bad += 1
            rows.append(f"FAIL  [{mode}] {fg} on {bg}: {err}")
            continue
        ok = got + 1e-9 >= need
        bad += 0 if ok else 1
        rows.append(f"{'PASS' if ok else 'FAIL'}  [{mode}] {fg} on {bg}: {got:.2f}:1 (needs {need:g})"
                    + (f"  {label}" if label else ""))
    if args.json:
        print(json.dumps({"failures": bad, "checked": len(allres)}))
    else:
        print("\n".join(rows))
        print(f"-> {len(allres) - bad} of {len(allres)} pairs pass WCAG AA")
        if "colors_dark" not in tokens:
            print("note: no colors_dark in tokens, dark mode not checked")
    return 1 if bad else 0


def failures(tokens_path):
    """Used by gates: number of failing pairs, or None when it cannot be checked."""
    tokens = read_json(tokens_path)
    if not tokens or not tokens.get("pairs"):
        return None
    modes = {"light": tokens.get("colors", {})}
    if tokens.get("colors_dark"):
        modes["dark"] = tokens["colors_dark"]
    bad = 0
    for mode, colors in modes.items():
        for _m, _f, _b, need, got, _l, _e in check_mode(colors, tokens["pairs"], mode):
            if got is None or got + 1e-9 < need:
                bad += 1
    return bad
