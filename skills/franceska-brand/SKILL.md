---
name: franceska-brand
description: >-
  Gives the product an identity of its own: shortlisted names and the
  trademark, domain, app-store and handle lookups to perform, a new palette
  verified for contrast, a logo brief, a voice guide, and a code scan that searches
  the code for any trace of the reference app. Use for requests like "pick a name",
  "give it an identity", "write a logo brief", "set the voice", "look for
  leftovers", or once franceska-validate is done. Always precedes
  franceska-launch.
---

# franceska-brand

**Stage:** Brand · **Role:** Brand Strategist.

Nothing ships wearing someone else's identity.

```bash
FR=<path to this skill>/scripts/fr.py
python3 $FR start brand
python3 $FR code_scan           # uses franceska/brand.json; non-zero means leftovers
```

Outputs `brand.md` and `brand.json` (starters in `templates/`). `brand.json`
holds `avoid` (their names), `domains`, `colors` and `allow`; the code scan,
listing check, review and publish preflight all read it.

## 1. Names

From the angle in `fixes.md`, draft 20 names across styles (descriptive,
compound, invented, metaphor, verb) and cut to five. A name survives only if it
is not confusingly similar to the reference app or any category peer in sound,
appearance or meaning (the test trademark offices apply), avoids puns on their
name, can be spelled after hearing it once, has no bad meaning in major
languages, and fits the angle. The user picks.

## 2. Checks: run them, do not assume them

Give each finalist a row per check, marked "to run" or with the result and the
date it ran. Never write "available" for something nobody looked up.

| check | where |
| --- | --- |
| US trademark | tmsearch.uspto.gov, classes 9 and 42 for software |
| EU and UK | EUIPO eSearch or TMview; UK IPO |
| Canada | the CIPO trademarks database |
| worldwide | WIPO Global Brand Database |
| domain | the registrar's search |
| app stores | search the exact name |
| handles | X, Instagram, TikTok, GitHub |
| the web | name plus category |

With a browser tool, run what you can and date it. This is screening, not
clearance; a trademark lawyer should search before real money goes into a name.

## 3. Palette

Write new values into the existing token roles, picking a hue family clearly
away from the reference app's. Re-run `python3 $FR contrast_check` until both modes pass,
and list the reference app's brand colours in `brand.json` so the code scan can find
survivors.

## 4. Logo brief

A brief, not a logo: the idea in a line; mark type; legibility at 16 px and as a
1024 px app icon; deliverables (SVG, 1024x1024 opaque iOS icon, favicon set,
1200x630 social image); and a clear instruction that it must not echo the
the reference app's mark in shape, colour pairing or letter trick. Compare drafts beside
their logo.

## 5. Voice

Three adjectives, each with what it excludes ("direct, not curt"); five do and
don't pairs; then rewrite the ten most-seen strings (sign-up, empty states,
primary button, confirmation, error) in the new voice, with nothing echoing the
reference app.

## 6. Sweep

Replace placeholders, then run `python3 $FR code_scan`. It searches file contents
and file names for their names (even inside identifiers such as
`TheirNameEmbed`), their domains and their colours as hex or `rgb()`, skipping
dependencies, build output and `franceska/`. Fix until clean, then check by
eye: favicon, page titles, email templates, share image, app icon.

If the product names the reference app factually (an "Import from X" feature), add
an `allow` entry with `path`, `term` and a **reason**. The audit lists every
allowed mention; keep them out of titles, keywords and ads.

## Exit gate

```bash
python3 $FR gate brand
```

Needs `brand.json` (name and avoid list), `brand.md`, a name free of the
the reference app's, a clean code scan and a palette passing contrast. Warns on undated
"available" claims.

## Hand off

`franceska-review`.
