"""Pipeline state: which stage is where, what gates passed, who approved what."""
import datetime

from .core import die, read_json, wdir, write_json
from .gates import GATES

STAGES = ["explore", "plan", "design", "build", "connect", "test", "compare",
          "validate", "brand", "review", "launch", "publish"]
PREREQS = {
    "explore": [], "validate": [], "plan": ["explore"], "design": ["plan"],
    "build": ["design"], "connect": ["build"], "test": ["connect"], "compare": ["test"],
    "brand": ["compare", "validate"], "review": ["brand"], "launch": ["review"], "publish": ["launch"],
}
SKILL = {s: f"franceska-{s}" for s in STAGES}
DONE = {"passed", "skipped"}
GO_STAGES = {"publish"}          # stages that need the user's explicit go


def now():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%MZ")


def path(root):
    return wdir(root, "state.json")


def load(root):
    st = read_json(path(root))
    if st is None:
        die("no franceska/state.json here. Run `init` first (or pass --project).")
    return st


def save(root, st):
    st["updated"] = now()
    write_json(path(root), st)


def init(root, app):
    st = read_json(path(root))
    if st:
        st["app"].update({k: v for k, v in app.items() if v})
    else:
        st = {"version": 1, "created": now(), "app": app,
              "stages": {s: {"status": "pending"} for s in STAGES},
              "overrides": [], "approvals": [], "history": []}
    save(root, st)
    return st


def downstream(stage):
    out, frontier = set(), {stage}
    while frontier:
        nxt = {s for s, pre in PREREQS.items() if frontier & set(pre)} - out
        out |= nxt
        frontier = nxt
    return out


def unmet(st, stage):
    return [p for p in PREREQS[stage] if st["stages"][p]["status"] not in DONE]


def next_stage(st):
    for s in STAGES:
        if st["stages"][s]["status"] not in DONE and not unmet(st, s):
            return s
    return None


def log(st, msg):
    st.setdefault("history", []).append({"at": now(), "event": msg})


def start(root, stage, force=False, reason=""):
    st = load(root)
    m = unmet(st, stage)
    if m and not force:
        die(f"{stage} needs {', '.join(m)} to pass first. Run those, or --force --reason \"...\" "
            "(only with the user's say-so).", 1)
    if m and force:
        if not reason:
            die("--force needs --reason")
        st["overrides"].append({"stage": stage, "reason": f"started before {', '.join(m)}: {reason}", "at": now()})
    if st["stages"][stage]["status"] != "passed":
        st["stages"][stage]["status"] = "in_progress"
    log(st, f"start {stage}")
    save(root, st)
    return st


def gate(root, stage):
    st = load(root)
    rep = GATES[stage](root, st)
    s = st["stages"][stage]
    s["gate_checked"] = now()
    if rep.failed:
        if s["status"] in ("passed", "stale"):
            s["status"] = "in_progress"
        s["last_fail"] = [m for k, m in rep.items if k == "fail"][:10]
    else:
        s["status"] = "passed"
        s.pop("last_fail", None)
        log(st, f"gate passed: {stage}")
    save(root, st)
    return rep


def skip(root, stage, reason):
    st = load(root)
    if not reason:
        die("skip needs --reason")
    st["stages"][stage] = {"status": "skipped", "reason": reason}
    log(st, f"skip {stage}: {reason}")
    save(root, st)


def reopen(root, stage):
    st = load(root)
    st["stages"][stage]["status"] = "in_progress"
    stale = []
    for d in downstream(stage):
        if st["stages"][d]["status"] == "passed":
            st["stages"][d]["status"] = "stale"
            stale.append(d)
    log(st, f"reopen {stage}; stale: {', '.join(sorted(stale)) or 'none'}")
    save(root, st)
    return sorted(stale)


def override(root, stage, reason):
    """The user knowingly accepts a failed gate. Recorded and shown by the audit."""
    if stage in ("review", "publish"):
        die("the review and publish gates cannot be overridden. Fix what fails.", 1)
    st = load(root)
    if not reason:
        die("override needs --reason in the user's own words")
    st["stages"][stage]["status"] = "passed"
    st["stages"][stage]["overridden"] = True
    st["overrides"].append({"stage": stage, "reason": reason, "at": now()})
    log(st, f"override {stage}: {reason}")
    save(root, st)


def approve(root, stage, quote):
    st = load(root)
    if not quote:
        die("approve needs --quote: what the user said")
    st.setdefault("approvals", []).append({"stage": stage, "quote": quote, "at": now()})
    log(st, f"approval for {stage}")
    save(root, st)


def status_lines(st):
    nxt = next_stage(st)
    icon = {"passed": "[x]", "skipped": "[-]", "in_progress": "[~]", "pending": "[ ]", "stale": "[!]"}
    out = [f"{st['app'].get('name') or '(unnamed app)'}  -  {st['app'].get('platform', '')}  -  slice: {st['app'].get('slice', '')}"]
    for s in STAGES:
        d = st["stages"][s]
        extra = ""
        if d["status"] == "stale":
            extra = "  (an earlier stage changed, re-run the gate)"
        elif d["status"] == "skipped":
            extra = f"  (skipped: {d.get('reason', '')})"
        elif d.get("overridden"):
            extra = "  (passed by override)"
        elif d.get("last_fail"):
            extra = f"  ({len(d['last_fail'])} gate failures)"
        mark = "  <- next" if s == nxt else ""
        out.append(f"{icon[d['status']]} {s:<13}{SKILL[s]}{extra}{mark}")
    if nxt is None:
        out.append("all stages passed or skipped")
    return out
