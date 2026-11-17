# Franceska

A set of thirteen Claude skills that take a reference app (a product you want to
learn from, a wireframe, or a prototype from a builder tool) all the way to a
product you can sell: planned, built, hardened, tested, branded, audited,
launched and deployed, with proof at each step instead of a promise.

It uses only the Python standard library. Nothing to install, no API keys, no
accounts to connect. MIT licensed.

## The idea

Most AI-built prototypes stall at "looks done". Franceska adds the missing
discipline:

1. **A conductor.** `/franceska` runs intake, keeps `franceska/state.json`,
   chooses the next stage, resumes after a break, and asks you at five
   checkpoints.
2. **Gates.** Every stage has exit checks a script can verify (files,
   sections, contrast, coverage, bugs, sample sizes). The next stage will not
   start until they pass. Overrides need your words and are recorded; the audit
   and deploy gates accept none.
3. **Production readiness.** Forty-one launch-blocking items in eight areas
   (CI, observability, reliability, security, legal, performance, commercial,
   handover). The tool checks what it can see in the code; everything else needs
   dated evidence. Early stages warn; the publish gate fails on any open item.
4. **An originality audit.** A source log, proof that no reference captures
   shipped, a search for the reference app's recorded wording in your code, a brand
   code scan, a secrets scan and an asset licence ledger.
5. **No invented facts.** Every long quote in the fixes document must exist
   word for word in the review sheet, and a reviewer's sentence on the landing
   page fails the launch gate.
6. **Claude-native output.** Recon and plans as Docs, sheets as Sheets, scores
   as a Dashboard, the landing page as an HTML artifact, all private until you
   share. Claude in Chrome handles walkthroughs of your own account, review
   reading and click-through tests.

## Install

**Claude Code plugin**

```
/plugin marketplace add <your-github-user>/franceska
/plugin install franceska@franceska
```

**Copy the folders** (global or per project):

```bash
cp -r skills/franceska* ~/.claude/skills/
```

**Claude app**: run `python3 scripts/package.py`, then upload the zips from
`dist/` in your Skills settings (start with `franceska.zip`, then add the stage
skills). Each zip carries its own copy of the tools. Claude runs the Python in
its own workspace, so nothing runs on your computer.

## Use it

Say "franceska, build my own version of <thing>" or "franceska, take this
prototype to production", answer the intake, and follow along. You can also run
any stage on its own.

```
explore -> plan -> design -> build -> connect -> test -> compare
      -> validate -> brand -> review -> launch -> publish
```

`validate` needs nothing before it, so run it first when you are only
deciding whether an idea is worth building.

Stages and the role each one plays:

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

| skill | purpose |
| --- | --- |
| `franceska` | intake, state, gates, checkpoints, resuming |
| `franceska-explore` | study the reference app: screens, flows, data, feature sheet, size, sources |
| `franceska-plan` | stack, schema, API, hazards, build order |
| `franceska-design` | tokens in light and dark, contrast, component specs |
| `franceska-build` | shell, thin slice, every screen and state |
| `franceska-connect` | auth, data rules, payments, email, jobs, hardening, CI |
| `franceska-test` | test plan, Playwright, bug log, performance evidence |
| `franceska-compare` | coverage score, layout comparison, verdict |
| `franceska-validate` | what users dislike, ranked and linked; fix plan; angle |
| `franceska-brand` | name and its checks, palette, logo brief, voice, code scan |
| `franceska-review` | the originality audit |
| `franceska-launch` | landing page, pricing, store listing, legal pages, commercial plumbing |
| `franceska-publish` | readiness close-out, production, DNS, monitoring; needs your go |

## The command line

One script, `scripts/fr.py`, inside every skill. Run it from your project.

```bash
python3 fr.py init --name "App" --url https://... --platform web --slice "..." --audience "..."
python3 fr.py status | next | start <stage> | gate <stage> | reopen <stage>
python3 fr.py skip <stage> --reason ... | override <stage> --reason ... | approve publish --quote ...
python3 fr.py source add|list|check          # provenance log
python3 fr.py audit                          # originality audit
python3 fr.py ready [init] [--area SEC,REL] [--write]   # production readiness
python3 fr.py feature_coverage [--visual diffs/*.json] [--markdown]
python3 fr.py visual_compare base.png mine.png --out diff.png [--json]
python3 fr.py review_insights --out franceska/feedback.md
python3 fr.py contrast_check | code_scan | listing_check | secrets
```

Your working files live in `franceska/` in your project. Run the tests with:

```bash
cd tests && python3 -I -m unittest discover -s . -v
```

To change the tools, edit `shared/`, run `python3 scripts/sync_shared.py` to
refresh each skill's copy, and the tests will fail if any copy drifts.

## Limits worth knowing

- It rebuilds **behaviour**, not the owner's code, assets, brand, wording,
  content, network or licences. The review and brand stages exist to enforce
  that, and they reduce risk without removing it.
- The tool can read your project's files, not your live site or accounts.
  Evidence for things like a restore rehearsal or an alert test is recorded by
  you or Claude with a date, and the gate requires it.
- Trademark and legal checks are screening aids, not advice. Have a lawyer
  review names, policies and terms before real money is involved.
- Claude never opens accounts, types passwords or card numbers, or pastes live
  keys. You do the account steps.
- A "perfect copy" is not promised. Explore sizes the work and compare gives a
  number.

## License

MIT. See LICENSE.
