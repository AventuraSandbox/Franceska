---
name: franceska-review
description: >-
  Produces the evidence that the product is original: the source log, proof
  that no reference captures shipped, no recorded wording of the reference app in the
  code, a clean brand code scan, no leaked secrets, an asset licence ledger, and a
  list of every skipped or overridden gate. Use when the user says "audit it",
  "is it clean", "did we copy anything", "prove it", before launch, or when
  deploy asks.
---

# franceska-review

**Stage:** Review · **Role:** Compliance Reviewer. Required review: it cannot be overridden.

A screening tool for originality, not legal advice. Run it any time; running it
after the build stage catches problems while they are cheap.

```bash
FR=<path to this skill>/scripts/fr.py
python3 $FR start review
python3 $FR audit        # prints, and writes franceska/review.md
```

## What it examines

| area | fails when |
| --- | --- |
| sources | none logged; a forbidden kind (network log, scripts, decompiled code, private API, scraped dump, another person's account, paywall bypass); a bad basis; an account source whose terms were unchecked or restrict competitors |
| captures | any file in the project is byte-identical to a reference capture, or code points at `franceska/screens` |
| wording | a string from `original-strings.txt` (4+ words, or any 6-word window of a long one) appears in the code; 3-word matches only warn |
| leftovers | their name, domain or colours remain, per `brand.json` |
| secrets | a live key, token or private key sits in the code |
| assets | warns for images, fonts and audio missing from `franceska/assets.csv` (`path,source,license`); fails if a listed asset lacks a licence |
| overrides | every skip and override is listed, so nothing is hidden |

## Using it well

1. Confirm `original-strings.txt` really contains the reference app's wording; an
   empty file makes the copy check meaningless, and the audit says so.
2. List every non-code asset in `assets.csv` with its source and licence
   (starter in `templates/`).
3. Run it and fix each FAIL in the code or docs. Never edit the log to make it
   pass, and never delete a source row.
4. A wording hit means rewrite the string from scratch in the brand voice, not
   tweak a word.
5. A leftover is replaced, or if it is a factual mention (such as an import
   feature) allowed in `brand.json` with a reason.

If an account source turns out `restricted`, stop using it, remove what came
from it, and tell the user.

## Exit gate

```bash
python3 $FR gate review
```

This runs the audit; pass means no FAIL lines. Nothing can override it.

## Hand off

Report pass or fail, the warning count, any allowed mentions and overrides.
Then `franceska-launch`.
