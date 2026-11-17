---
name: franceska-test
description: >-
  Proves the product works: a test plan derived from the explore flows, Playwright
  specs with accessibility scans, a manual pass for what cannot be automated,
  a severity-ranked bug log with a fix loop, and the performance evidence
  production needs (Lighthouse, query and load checks on this app). Use when the
  user says "test it", "QA this", "find bugs", "write e2e tests", "is it fast
  enough", or after franceska-connect.
---

# franceska-test

**Stage:** Test · **Role:** QA Engineer.

```bash
FR=<path to this skill>/scripts/fr.py
python3 $FR start test
python3 $FR ready --area CI,PERF        # evidence this stage owes
```

Inputs: flows in `explore.md`. Outputs: `test-plan.md`, `bugs.md`, specs in
`e2e/`. Starters in `templates/`: `test-plan.md`, `bug-report.md`,
`e2e.example.spec.ts`, `load-test.example.js`.

## One firm rule

Aim every test at **your own** product. Do not load, fuzz or script the
the reference app's servers. Using the reference app manually, as a customer, is fine.

## 1. Plan from the flows

For every flow, describe the happy path and what the user ends up seeing. Then
probe it with these variations: blank fields, oversized input, emoji and
accented text, two tabs open, a double-clicked submit, going back or reloading
mid-flow, a slow or dropped connection, an expired session, **someone else's
records (which must never appear)**, other time zones and DST changes, small
screens, keyboard-only use, and screen-reader labels. Add failure cases such as
a wrong password, a declined card (Stripe's test number 4000 0000 0000 0002), a
forbidden action and a deleted record. Number cases `F01-H1`, `F01-E3`,
`F01-N2`; the gate needs at least one case for every explore flow.

## 2. Automate

Write one Playwright spec per flow and run it against the dev server with seed
data. Locate elements by role and label rather than CSS class. Make each spec
fail on console errors, on any 5xx response and on an axe accessibility scan:

```bash
npm i -D @playwright/test @axe-core/playwright && npx playwright install chromium
npx playwright test
```

If the user's machine cannot install software, run it in a cloud dev
environment or the Claude workspace, and say so. Wire it into CI
(`franceska-connect` supplies the workflow) so it runs on every push.

## 3. Walk what remains

Emails arriving, real OAuth, end-to-end payments and visual glitches need a
manual pass. With Claude in Chrome or the built-in browser, drive the local
build and screenshot each step. Without one, hand the user a checklist.

## 4. Performance evidence

Record results in `franceska/production-readiness.md` with dates:
- **PERF-1** Lighthouse (or PageSpeed) on the landing page and the core
  screen; write the scores, and aim for 80+ on performance and 90+ on
  accessibility.
- **PERF-2** Query review on realistic row counts: check the slowest queries
  with `EXPLAIN` and add missing indexes.
- **PERF-3** A short load test of this app only (`templates/load-test.example.js`
  for k6), against staging, with the numbers noted.
- **PERF-4** Images and fonts compressed and sized.
- **CI-2 and CI-4** Link a green CI run covering lint, types and the build.

## 5. Bugs

Log each in `bugs.md` as a heading the gate reads:

```
## B-007 [S2] [open] Reminder sent twice
```

S1: data loss, a security hole, a wrong charge, or a blocked core flow. S2: a
broken feature with no way around it. S3: breakage with a workaround, or
something visibly wrong. S4: cosmetic. Status is open, fixed, wontfix or to-check. Log only what you
reproduced. Fix S1 and S2 first: failing test, fix, green test, keep the test,
re-run everything, note the commit.

## Exit gate

```bash
python3 $FR gate test
```

Needs a plan covering every flow, `bugs.md`, and no open S1 or S2. Warns on
open S3, on manual-only coverage, and on open CI and PERF readiness items
(these block at publish).

## Hand off

Report cases run, passed, failed and bugs by severity. Next
`franceska-compare`.
