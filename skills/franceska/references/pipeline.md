# Pipeline reference

Paths are inside `franceska/` in the project unless noted.

| stage | skill | reads | writes | gate checks |
| --- | --- | --- | --- | --- |
| explore | franceska-explore | public sources, the user's account or prototype | explore.md, features.csv, provenance.csv, original-strings.txt, screens/ | scope, sections, IDs, valid sheet, logged and allowed sources |
| plan | franceska-plan | explore.md, features.csv | architecture.md, schema.sql | stack, API, risks, build order, tables, timestamptz, no floats |
| design | franceska-design | explore.md, screens/ | design/tokens.json, tokens.css, components.md | colour roles, WCAG AA in light and dark, components |
| build | franceska-build | explore, architecture, design | the app, build-log.md, app-screens/, features.csv | log lines, half the must-haves started, screenshots |
| connect | franceska-connect | architecture.md | server code, connect.md, .env.example | checklist ticked, .env.example, no secrets; warns on SEC/REL/LEG readiness |
| test | franceska-test | explore.md flows | test-plan.md, bugs.md, e2e/ | every flow has cases, no open S1/S2; warns on CI/PERF readiness |
| compare | franceska-compare | features.csv, screens/, app-screens/ | coverage.md, diffs/ | all must-haves done, score 80+, no S1/S2 |
| validate | franceska-validate | public review pages | reviews.csv, feedback.md, fixes.md, new rows in features.csv | 30+ linked reviews, 3+ sources, every quote verbatim |
| brand | franceska-brand | fixes.md | brand.md, brand.json, tokens | name, avoid list, clean code scan, contrast |
| review | franceska-review | everything | review.md | provenance, references, copied wording, leftovers, secrets, assets |
| launch | franceska-launch | fixes.md, brand.md | launch/ files, listing | pricing cited, no reviewer wording, listing lint; warns on COM/OPS readiness |
| publish | franceska-publish | everything | publish.md, runbook.md, production-readiness.md | preflight ticked, user's go, audit, shippable, **all readiness items** |

## Production readiness

`python3 $FR ready init` creates `franceska/production-readiness.md`, one row
per item, grouped into CI, OBS, REL, SEC, LEG, PERF, COM and OPS. A row is
satisfied by an automatic check on the project (health endpoint, security
headers, rate limits, CI workflow, lockfile, privacy and terms pages, account
deletion, data export, README, runbook, secrets) or by `done` with evidence
and a date, or `na` with a reason. Stale evidence (over 30 days) is flagged.
`python3 $FR ready --write` writes `readiness.md` with the percent.

Commands: `init status next start gate reopen skip override approve source audit feature_coverage visual_compare review_insights contrast_check code_scan listing_check secrets ready`.
