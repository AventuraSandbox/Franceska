---
name: franceska-launch
description: >-
  Prepares the go-to-market: a landing page built on the positioning angle,
  pricing benchmarked against the reference app's public prices and its users'
  billing complaints, an App Store and Google Play listing checked against store
  rules, legal pages, the commercial plumbing a paid product needs (tax,
  refunds, support), and a launch plan. Use for requests like "write the
  landing page", "set pricing", "what should I charge", "store listing",
  "privacy policy", "launch plan", "Product Hunt", or once franceska-review
  passes.
---

# franceska-launch

**Stage:** Launch · **Role:** Launch Strategist.

```bash
FR=<path to this skill>/scripts/fr.py
python3 $FR start launch
python3 $FR listing_check                       # lints franceska/launch/listing.json
python3 $FR ready --area COM,LEG,OPS      # what a paid launch still owes
```

Inputs: `fixes.md`, `brand.md`, `brand.json`. Outputs in `franceska/launch/`:
`landing.md`, `pricing.md`, `listing.json` (start from
`templates/listing.example.json`), `launch-plan.md`.

## Rules

- No invented proof: no fake testimonials, user counts, ratings, press logos or
  "trusted by" rows. An empty section beats a false one. Real beta users, with
  permission, are fine.
- The reference app's reviews are research, never testimonials; the gate fails if a
  reviewer's sentence turns up on the landing page.
- The reference app's name stays out of your name, listing, keywords and ads.

## 1. Landing page

Draft `landing.md`, then build it in the project and, if artifact tools exist,
as a private HTML artifact for review. Order: hero (the angle, one line, one
button, a real screenshot); the problem (top two themes, paraphrased); how it
works (three steps); features (lead with the fixes, since coverage is table
stakes); pricing; FAQ with the honest objections; a closing call to action. Use
the brand voice and re-run `python3 $FR contrast_check` after styling.

## 2. Pricing

`pricing.md` compares the reference app's public pricing page and two or three
alternatives, **each with URL and the date you read it**. Add what reviewers say
about price and billing, with counts. Choose the model (free tier or trial; flat or per seat; monthly and
annual), offer no more than three tiers named for their audience, and remove
billing pain in the product itself: single-click cancellation, plain renewal
notices, no surprise seat charges. List the Stripe products and prices the user
needs to set up.

## 3. Store listing

Complete `listing.json` and run the lint. Its limits: App Store name 30,
subtitle 30, promotional text 170, keywords 100, description 4000; Google Play
title 30, short description 80, full description 4000. It rejects ranking and
price claims in short fields, warns about emoji, capitals, keyword characters
wasted on spaces or repeated words, and fails when the reference app's name shows
up. Apple's guideline 4.1 turns away copies and light reskins, so let your
improvements and your brand dominate the screenshots and first lines. Gather as
well: screenshots at the sizes the consoles currently require, privacy labels
and data-safety answers, policy and support links, an age rating, and review
notes with a demo login.

## 4. Legal and compliance pages

Use `templates/legal-outlines.md` to draft a privacy policy that names every
processor (host, database, Stripe, email, analytics, error tracking) and terms
of service, and publish them as pages in the app. These outlines are starting
points, not legal advice: record in LEG-6 either that a lawyer reviewed them or
that the owner accepted the risk, in the owner's words.

## 5. Commercial plumbing

Record evidence in `franceska/production-readiness.md` for tax or VAT handling
(COM-1), a tested cancel and refund path (COM-2), retries and customer notice
for failed payments (COM-3), server-enforced plan limits (COM-4), a support
inbox with a stated response time (COM-5), receipts (COM-6) and the owner's
verified payment and business accounts (COM-7). Decide where customers find
status or incident news (OPS-3) and which funnel events are tracked (OPS-4).

## 6. Launch plan

`launch-plan.md` covers: a waitlist or closed beta before opening, analytics
and error tracking running, the places where the reference app's frustrated users
talk (taken from the research), an announcement that leads with your fix, and
a list of ten early users to speak with one to one.

## Exit gate

```bash
python3 $FR gate launch
```

Needs landing, pricing and plan files, pricing that cites the reference app's page
with a date, no reviewer wording on the page, and a passing listing if one
exists. Warns on proof-style claims and on open COM and OPS readiness items
(they block at publish).

## Hand off

`franceska-publish`.
