---
name: franceska-validate
description: >-
  Finds the reason the product should exist: reads real public reviews and
  threads about the reference app, ranks what users dislike, lack or are ignored by,
  and converts it into a fix plan and a positioning angle. Quotes must be real,
  exact and linked, and the gate verifies them. Use for requests like "what annoys
  users of X", "go through the reviews", "where is the gap", "is this worth
  building", "how should I position it", or once franceska-compare is done.
---

# franceska-validate

**Stage:** Validate · **Role:** Product Strategist.

A product that only matches an incumbent gives nobody a reason to switch. This
stage mines the incumbent's own users for that reason.

```bash
FR=<path to this skill>/scripts/fr.py
python3 $FR start validate
python3 $FR review_insights --out franceska/feedback.md      # reads franceska/reviews.csv
```

It needs no earlier stage, so run it first as a go / no-go for an idea, and
again after compare to refresh the fix plan.

## Honesty rules

- **Invent nothing.** No made-up reviews, quotes, ratings, counts or sources.
  If a site is unreachable, say so. If you found 14 reviews, report 14.
- **Exact and linked.** Quotes are copied character for character with the URL
  of the review or thread. The tool drops rows without a link, and the gate
  fails if a long quote in `fixes.md` is not found in `reviews.csv`.
- **Read pages, do not harvest them.** Open review pages as a person would
  (Claude in Chrome works well) and copy rows into the sheet by hand. Skip
  scraping libraries on any site whose terms prohibit them. Public feeds and
  APIs are acceptable within their terms: Apple's customer-review RSS feed, the
  Hacker News search API and Reddit's official API.
- **Never plant reviews**, whether praising your product or attacking theirs.
  The FTC's 2024 rule makes that illegal in the US, and many other
  jurisdictions agree.
- **Reviewers are research, not testimonials.** Their words never go on your
  landing page.

Log each site once with `python3 $FR source add --stage validate --kind review ...`.

## 1. Collect

Target 100 or more reviews from at least three places, newest first: the App
Store and Google Play listings, G2, Capterra and Trustpilot (include the 1 to 3
star reviews), Reddit and Hacker News (try "X alternative", "switched from X",
"X vs"), the reference app's public roadmap or request board with vote counts, and
its changelog (so you avoid fixing what they already fixed). Include the
middle ratings: complaints wrapped in praise often hold the best ideas.

One row per review in `franceska/reviews.csv`: `source,url,date,rating,text`
(starter in `templates/reviews.csv`).

## 2. Rank

`python3 $FR review_insights --out franceska/feedback.md` groups reviews into themes
(edit a copy of `templates/themes.json` for the category and pass `--themes`),
weights low ratings and recent dates, flags a theme as **thin** with fewer than
three reviews or a single source, lists requests in users' words, and surfaces
low ratings that matched no theme. Go through that final list manually.

## 3. Write `fixes.md`

Start from `templates/fixes.md` and state the sample size at the top. Build
three lists: dislikes (complaints about behaviour), gaps (features requested by
name) and neglected needs (jobs or groups the product overlooks). Each entry has
a one-line problem, review and source counts, and one or two exact, linked
quotes. Mark thin themes as thin.

## 4. Plan the fixes

Pick five to eight by evidence against cheapness. For each: what to build, size,
which skill builds it, evidence. Add them to `features.csv` with `original`
set to `no`. Hand pricing and billing complaints to `franceska-launch`.

## 5. Offer angles

Write three, each from a strong theme, as: *For {who} who {pain in plain
words}, {product} {what it does instead}.* with the evidence count. Recommend
one and ask the user to choose. It drives the name, voice and landing page.
Keep the reference app's name out of your product name, ads and listing.

Publish `reviews.csv` (Sheets) and `fixes.md` (Docs) privately if available.

## Exit gate

```bash
python3 $FR gate validate
```

Needs 30+ linked reviews from 3+ sources, `fixes.md` with all five sections and
a stated sample, and every long quote verified against the sheet. If the market
is genuinely small, ask the user; if they accept a thin sample, run
`python3 $FR override validate --reason "..."`.

## Hand off

`franceska-brand`.
