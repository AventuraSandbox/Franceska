---
name: franceska-explore
description: >-
  Studies a reference app (a competitor's app, a prototype, a wireframe) and writes
  the explore map: screens, flows, components, inferred data model, a weighted
  feature sheet and an honest size estimate, with every source logged. First
  stage of Franceska. Use when the user says "map out X", "reverse engineer X",
  "what screens does X have", "explore this", "take this prototype and plan it",
  or pastes an app URL, store link or repo.
---

# franceska-explore

**Stage:** Explore · **Role:** Product Analyst.

Every later stage leans on this one. If the map is thin, so is the product.

```bash
FR=<path to this skill>/scripts/fr.py     # run from the project folder
python3 $FR start explore
```

Produces, in `franceska/`: `explore.md`, `features.csv`, `provenance.csv`,
`original-strings.txt`, and reference captures in `screens/`. Starter files are
in `templates/`.

## Ground rules

- Use only public material and the user's own account or prototype.
- Browse at human pace: no crawlers, bulk downloads or scripted loops.
- Leave the target's scripts, binaries and network traffic alone; do not mine
  them for endpoints. Documented public APIs are fine.
- Before using an account, read the app's terms. If they bar building a
  competing product, switch to public sources and record `restricted`.
- Captures are reference only. They stay in `franceska/screens/`; the audit
  hashes them against the project to prove none shipped.

## Procedure

**1. Pin the scope.** State already holds app, platform, slice and audience. If
the slice is fuzzy, tighten it. A good slice is a loop someone pays for.

**2. Gather and log sources.** Log each one as you use it:

```bash
python3 $FR source add --stage explore --kind help-docs --ref https://... --basis public --used-for "feature list"
python3 $FR source add --stage explore --kind own-account --ref "walkthrough 2026-11-16" \
  --basis own-account --terms-checked yes --used-for "all states of S03-S09"
```

Productive sources, most useful first: the help centre (the fullest feature
inventory), the pricing page (what is gated shows what matters), the
changelog, the store listing, public videos, the marketing site, public API
docs, and the user's own account.

If the reference app is the user's own prototype or repo, read it directly and log
it as `user-supplied`. Everything below applies, minus the competitor rules.

For an own-account walkthrough in Claude in Chrome, the user must be present
and agree. They sign in; you read each screen and save captures as
`franceska/screens/S01.png` and so on. Do not run scripts in the page, read
bundles or network calls, or click anything that deletes, sends or pays.

**3. Screens.** One row each with a stable ID (S01...), how to reach it, its
purpose, key components and the states you saw: empty, loading, filled, error,
no permission, mobile. A state you skip is a state that will be missing.

**4. Flows.** F01... each a user goal with the screens it crosses and its
edges. Count happy-path clicks; that is the number to beat.

**5. Components.** Every repeated part with variants, states and where used.

**6. Data model.** Entities, fields, relations, each with evidence and a
confidence of high, medium or guess.

**7. Feature sheet.** `franceska/features.csv` with columns
`feature,area,priority,original,yours,effort,notes`. Priority is must, should
or could. `original` is `yes` (`no` is for fixes added later). `yours` starts
`no` and later becomes `yes`, `partial` (say what is missing) or `skip` (say
why). `effort` is S, M, L or XL.

**8. Record the wording.** Put the reference app's UI wording (buttons, empty
states, errors, emails) into `franceska/original-strings.txt`, one per line.
It is reference only and powers the audit's copy check.

**9. Mark what you cannot take.** Add `skip` rows with reasons for licensed
catalogues, a network of users, data the owner holds, partner deals, hardware
and regulated licences.

**10. Size it.** Count screens, flows and entities; name the hard parts
(realtime, sync, payments, integrations, offline). S is a weekend, M a few
weeks, L a quarter, XL means narrow the slice.

Publish `explore.md` (Docs) and `features.csv` (Sheets) as private artifacts when
those tools exist.

## Exit gate

```bash
python3 $FR gate explore
```

Needs: scope fields set; `explore.md` with sections for screens, flows,
components, data model, out of scope and size; 3+ screen IDs and 1+ flow ID; a
valid sheet of 5+ rows with a must; sources logged on allowed bases. Warns if
`original-strings.txt` is empty.

## Hand off

Summarise in five lines (core loop, counts, three hardest parts, exclusions,
size), ask the user to confirm the slice, then `franceska-plan`.
