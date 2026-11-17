"""One entry point for every Franceska tool:  python3 scripts/fr.py <command> ..."""
import argparse
import json
import os
import sys

from . import audit, contrast_check, code_scan, feature_coverage, listing_check, provenance, readiness, review_insights, state, visual_compare
from .core import find_root, wdir, write_text
from .gates import GATES, open_blockers


def build_parser():
    p = argparse.ArgumentParser(prog="fr.py", description="Franceska tools (standard library only)")
    p.add_argument("--project", help="project root (default: nearest folder containing franceska/)")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("init", help="create franceska/state.json")
    for k in ("name", "url", "platform", "slice", "audience"):
        s.add_argument(f"--{k}", default="")
    sub.add_parser("status", help="show the pipeline").add_argument("--json", action="store_true")
    sub.add_parser("next", help="name the next stage and its skill")

    for name in ("start", "gate", "reopen"):
        s = sub.add_parser(name)
        s.add_argument("stage", choices=state.STAGES)
        if name == "start":
            s.add_argument("--force", action="store_true")
            s.add_argument("--reason", default="")
    s = sub.add_parser("skip")
    s.add_argument("stage", choices=state.STAGES)
    s.add_argument("--reason", required=True)
    s = sub.add_parser("override", help="the user accepts a failed gate")
    s.add_argument("stage", choices=state.STAGES)
    s.add_argument("--reason", required=True)
    s = sub.add_parser("approve", help="record the user's go for a stage")
    s.add_argument("stage", choices=state.STAGES)
    s.add_argument("--quote", required=True)

    s = sub.add_parser("source", help="provenance log")
    ss = s.add_subparsers(dest="action", required=True)
    a = ss.add_parser("add")
    a.add_argument("--stage", required=True)
    a.add_argument("--kind", required=True)
    a.add_argument("--ref", required=True)
    a.add_argument("--basis", required=True)
    a.add_argument("--used-for", required=True)
    a.add_argument("--terms-checked", default="n/a")
    a.add_argument("--notes", default="")
    ss.add_parser("list")
    ss.add_parser("check")

    sub.add_parser("audit", help="clean-room audit, writes franceska/review.md")
    sub.add_parser("secrets", help="scan the project for leaked keys")

    s = sub.add_parser("feature_coverage")
    s.add_argument("csv", nargs="?")
    s.add_argument("--visual", nargs="*")
    s.add_argument("--markdown", action="store_true")
    s.add_argument("--json", action="store_true")
    s.add_argument("--blockers", type=int, default=None, help="open S1/S2 bugs (default: read bugs.md)")

    s = sub.add_parser("visual_compare")
    s.add_argument("original")
    s.add_argument("yours")
    s.add_argument("--out")
    s.add_argument("--mode", choices=["layout", "pixel"], default="layout")
    s.add_argument("--json", action="store_true")

    s = sub.add_parser("review_insights")
    s.add_argument("csv", nargs="?")
    s.add_argument("--themes")
    s.add_argument("--out")
    s.add_argument("--json", action="store_true")

    s = sub.add_parser("contrast_check")
    s.add_argument("tokens", nargs="?")
    s.add_argument("--json", action="store_true")

    s = sub.add_parser("code_scan")
    s.add_argument("path", nargs="?", default=None)
    s.add_argument("--avoid")
    s.add_argument("--domains")
    s.add_argument("--colors")
    s.add_argument("--config")
    s.add_argument("--secrets", action="store_true", help="also scan for leaked keys")
    s.add_argument("--json", action="store_true")

    s = sub.add_parser("ready", help="production readiness: check, or init the evidence file")
    s.add_argument("action", nargs="?", choices=["check", "init"], default="check")
    s.add_argument("--area", help="comma list: CI,OBS,REL,SEC,LEG,PERF,COM,OPS")
    s.add_argument("--write", action="store_true", help="also write franceska/readiness.md")
    s.add_argument("--force", action="store_true")
    s.add_argument("--json", action="store_true")

    s = sub.add_parser("listing_check")
    s.add_argument("listing", nargs="?")
    s.add_argument("--config")
    s.add_argument("--json", action="store_true")
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    root = find_root(args.project)
    c = args.cmd

    if c == "init":
        st = state.init(root, {"name": args.name, "url": args.url, "platform": args.platform,
                               "slice": args.slice, "audience": args.audience})
        for d in ("screens", "app-screens", "diffs", "design", "launch"):
            os.makedirs(wdir(root, d), exist_ok=True)
        print(f"initialised {wdir(root)}")
        print("\n".join(state.status_lines(st)))
        return 0
    if c == "status":
        st = state.load(root)
        print(json.dumps(st, indent=2) if args.json else "\n".join(state.status_lines(st)))
        return 0
    if c == "next":
        st = state.load(root)
        n = state.next_stage(st)
        print(f"{n}  ->  /{state.SKILL[n]}" if n else "done: every stage is passed or skipped")
        return 0
    if c == "start":
        st = state.start(root, args.stage, args.force, args.reason)
        print(f"{args.stage}: in progress  ->  /{state.SKILL[args.stage]}")
        return 0
    if c == "gate":
        rep = state.gate(root, args.stage)
        print(f"Gate: {args.stage}")
        print(rep.render())
        print("GATE PASSED" if not rep.failed else "GATE NOT PASSED")
        return 1 if rep.failed else 0
    if c == "reopen":
        stale = state.reopen(root, args.stage)
        print(f"{args.stage} reopened. Stale downstream: {', '.join(stale) or 'none'}")
        return 0
    if c == "skip":
        state.skip(root, args.stage, args.reason)
        print(f"{args.stage} skipped")
        return 0
    if c == "override":
        state.override(root, args.stage, args.reason)
        print(f"{args.stage} passed by override (recorded, and the audit will list it)")
        return 0
    if c == "approve":
        state.approve(root, args.stage, args.quote)
        print(f"recorded the user's go for {args.stage}")
        return 0
    if c == "source":
        if args.action == "add":
            rid = provenance.add(root, args.stage, args.kind, args.ref, args.basis, args.used_for,
                                 args.terms_checked, args.notes)
            print(f"logged {rid}")
            return 0
        if args.action == "list":
            for r in provenance.load(root):
                print(f"{r['id']}  {r['stage']:<12}{r['kind']:<16}{r['basis']:<13}{r['ref']}")
            return 0
        rep = provenance.check(root)
        print(rep.render())
        return 1 if rep.failed else 0
    if c == "audit":
        args.project = args.project
        return audit.run(args)
    if c == "secrets":
        from .code_scan import scan_secrets
        found = scan_secrets(root)
        for rel, n, name in found:
            print(f"{rel}:{n}: SECRET {name}")
        print(f"-> {len(found)} secrets")
        return 1 if found else 0
    if c == "feature_coverage":
        args.csv = args.csv or wdir(root, "features.csv")
        if args.blockers is None:
            args.blockers = open_blockers(root)
        return feature_coverage.run(args)
    if c == "visual_compare":
        return visual_compare.run(args)
    if c == "review_insights":
        args.csv = args.csv or wdir(root, "reviews.csv")
        return review_insights.run(args)
    if c == "contrast_check":
        args.tokens = args.tokens or wdir(root, "design", "tokens.json")
        return contrast_check.run(args)
    if c == "code_scan":
        args.path = args.path or root
        if not args.config and os.path.isfile(wdir(root, "brand.json")) and not (args.avoid or args.domains or args.colors):
            args.config = wdir(root, "brand.json")
        return code_scan.run(args)
    if c == "ready":
        return readiness.run(args, root)
    if c == "listing_check":
        args.listing = args.listing or wdir(root, "launch", "listing.json")
        if not args.config and os.path.isfile(wdir(root, "brand.json")):
            args.config = wdir(root, "brand.json")
        return listing_check.run(args)
    return 2


if __name__ == "__main__":
    sys.exit(main())
