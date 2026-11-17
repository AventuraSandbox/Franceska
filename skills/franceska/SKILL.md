---
name: franceska
description: >-
  Conductor for the Franceska pipeline, which turns a reference app into a shippable
  product: study it, plan it, design it, build it, add a real backend, test it,
  measure it, learn from users, brand it, review it, launch it and publish it.
  Keeps progress in franceska/state.json, enforces an exit gate at each stage,
  and tracks production readiness. Use when the user says "franceska", "build
  my own version of X", "take this prototype to production", "where are we",
  "what's next", "resume", "status", or starts a stage with no project set up.
---

# franceska: the conductor

Franceska builds a product from a reference app: an existing app to learn from, a
wireframe, a prototype from a builder tool, or a spec. It rebuilds **what a
product does**, never what its owner owns, and it will not call something done
until the evidence says it is. This skill runs the show: it keeps state, runs
gates, picks the next stage and asks the user at the checkpoints. Twelve stage
skills do the work.

## Setup

All tooling is a single standard-library script, `scripts/fr.py`, beside this
file. No installs. From the **user's project folder**:

```bash
FR=<path to this skill>/scripts/fr.py
python3 $FR status
```

In the Claude app, work in the session folder and send finished files to the
user. In Claude Code, work in the repo.

## Opening move

1. If `franceska/state.json` exists, run `python3 $FR status` and pick up from
   there (see "Coming back").
2. Otherwise do intake. Ask only what is not already known, in one
   AskUserQuestion call if you have it:
   - **Reference app**: which app, prototype or spec, its URL or location, and the
     platform (web, iOS, Android, desktop).
   - **Slice**: the single loop worth building first. "A full CRM" is too wide;
     "log a contact and schedule a follow-up" is a slice.
   - **Audience**: who it serves: the user's own company, a niche, or a market.
   - **Account access**: may Claude watch the user walk through their own
     account? "Public sources only" is a fine answer.
3. Initialise, then say in one sentence what happens next:

```bash
python3 $FR init --name "App" --url https://... --platform web --slice "..." --audience "..."
```

## The run

```
explore -> plan -> design -> build -> connect -> test -> compare
      -> validate -> brand -> review -> launch -> publish
```

For each stage: `python3 $FR start <stage>`, load `franceska-<stage>`, do the
work, then `python3 $FR gate <stage>`. Fix every FAIL and re-run. A passing
gate earns a three-line summary to the user and the name of what is next.
`python3 $FR next` names it. The `validate` stage has no prerequisite, so
it can run first as a go / no-go.

Production readiness runs underneath all of it. `python3 $FR ready` lists
every launch-blocking item; early gates only warn about their share of it, and
the publish gate fails on anything open. See `references/pipeline.md`.

Stages and roles:

| stage | role | what it does |
| --- | --- | --- |
| Explore | Product Analyst | study the reference app |
| Plan | Software Architect | stack, schema, API, build order |
| Design | Product Designer | tokens, components, contrast |
| Build | Frontend Engineer | every screen and state |
| Connect | Backend Engineer | accounts, data, payments, security, CI |
| Test | QA Engineer | test plan, e2e, bug log |
| Compare | Product Evaluator | coverage and layout score, verdict |
| Validate | Product Strategist | what users dislike, the angle |
| Brand | Brand Strategist | name, palette, voice, code scan |
| Review | Compliance Reviewer | required originality review, no override |
| Launch | Launch Strategist | landing, pricing, listing, legal outlines |
| Publish | Release Engineer | production, DNS, monitoring; needs your go |

## Where to stop and ask

| before | the question |
| --- | --- |
| design | Is this the right slice and size? |
| build | Stack and order agreed? Building is the costly part. |
| brand | Which positioning angle do you want? |
| launch | Name, palette and code scan are done; ready for launch materials? |
| publish | Show the preflight; get an explicit go; record it with `python3 $FR approve publish --quote "<their words>"`. |

Otherwise keep moving. Nobody wants a question per step.

## When a gate will not pass

If the blocker is a decision for the user (a niche market with few reviews, a
stage that does not apply), ask. Then use one of:

```bash
python3 $FR skip <stage> --reason "static site, no backend"
python3 $FR override <stage> --reason "<their words>"
```

Both are written to the record and surfaced by the audit. Never override on
your own initiative. The audit and deploy gates accept no override.

## Coming back, and changing course

`python3 $FR status` marks stages passed `[x]`, running `[~]`, stale `[!]` or
skipped `[-]`. If an early stage must change, `python3 $FR reopen <stage>`
turns everything after it stale; tell the user what that re-opens.

## Principles for every stage

- Take the behaviour, not the property. No code, logos, icons, illustrations,
  photos, licensed fonts, wording, content or private APIs from anyone else's
  product. Everything is written fresh.
- Use only what the user may use: public pages and their own account. No one
  else's login, no paywall tricks, no crawlers, no bulk pulls.
- Log each source with `python3 $FR source add ...`. The audit reads the log.
- Invent nothing: no reviews, quotes, figures, users or endorsements.
- The user holds the keys. Claude never opens accounts, types passwords or
  card numbers, or pastes live secrets.
- Rebrand before launch; review before publish. Not legal advice.

## Showing the work

Everything lives in `franceska/` in the project. When artifact tools exist,
also publish private artifacts for what the user will read or edit, and hand
over the links: Docs for explore, plan, fixes and brand; Sheets for the feature
and review sheets; a Dashboard for scores and readiness; an HTML artifact for
the landing page. Reference screenshots stay private and never ship.

With Claude in Chrome (or the built-in browser), use it to watch the user's own
account walkthrough, read review pages, click through the build, run store and
DNS consoles. The user signs in and approves anything that spends money.

## Finish

When every stage is passed or skipped, report in one paragraph: live URL,
coverage score, audit result, readiness percent, any overrides, and the three
best next improvements.
