---
name: franceska-publish
description: >-
  Ships the product to production on the user's domain, behind a preflight and a
  production-readiness gate: CI green, staging and rollback proven, backups
  restored once, monitoring and alerts verified, legal and commercial items
  done, then production services, DNS, mobile builds and a first-week watch
  plan. Needs the user's explicit go. Use for requests like "release it",
  "take it live", "point my domain at it", "are we production ready", or once
  franceska-launch is done.
---

# franceska-publish

**Stage:** Publish · **Role:** Release Engineer. It needs the user's explicit go and cannot be overridden.

```bash
FR=<path to this skill>/scripts/fr.py
python3 $FR start publish
python3 $FR ready --write          # percent ready, every open item, writes readiness.md
```

Inputs: everything in `franceska/`. Outputs: `publish.md` (from
`templates/preflight.md`), `runbook.md` (from `templates/runbook.md`) and a
completed `production-readiness.md` (`templates/production-readiness.md` shows the shape; `ready init` generates it).

## Rules

- **No go, no publish.** Show the preflight, ask, and record the words:
  `python3 $FR approve publish --quote "<their words>"`. The gate refuses
  without it.
- **Money and credentials stay with the user.** Claude does not buy domains or
  handle card numbers, passwords or live secrets. It prepares the exact DNS
  records, variable names and commands. With a browser tool it may open a
  console and point at what to click; the user enters credentials and confirms
  payments.
- **Rebranded and audited first.** Neither gate can be overridden.

## 1. Close the readiness list

`python3 $FR ready` must say ready. Work the open items: the tool verifies the
ones it can see in the project; for the rest, the evidence column needs a link,
pasted result or screenshot path and a date. Typical evidence: a green CI run
(CI-2, CI-4); a test error in the tracker and an alert that reached a person
(OBS-1, OBS-3); an uptime monitor on the home page and core API (OBS-2); a
database restored from backup into a scratch instance (REL-3); a staging URL
(REL-2); a release rolled back once (REL-5); an audit result (SEC-1); a second
user denied access (SEC-4). `na` is allowed with a reason and is listed
afterwards. Write `runbook.md` so someone else could run the service (OPS-2).

## 2. Preflight

Run and paste results into `publish.md`:

```bash
python3 $FR audit
python3 $FR code_scan
python3 $FR feature_coverage
python3 $FR listing_check            # if shipping to stores
python3 $FR secrets
python3 $FR ready
npx playwright test && npm run build
```

By hand: no S1 or S2 bugs open, policy pages live, consent banner if needed,
account deletion and export working, favicon, titles and share image your own.
Any failure stops the release; say which and why.

## 3. Production services

Give production its own database, with backups switched on and migrations run
by the release process. Set production variables in the host (names from
`.env.example`); live keys exist only there. Move Stripe to live mode: rebuild
products and prices, register the production webhook and its secret, then buy
something real and refund it. Add the production domain to every OAuth
provider's redirect list; Google scopes that need review must be approved or
only listed testers can log in. Verify the email sending domain.

## 4. Host and domain

Vercel suits Next.js (Netlify, Cloudflare Pages, Fly or Render are
alternatives). Have `main` deploy automatically, give pull requests preview
URLs, and keep a staging environment that mirrors production. Once the user
owns the domain:

| type | name | value |
| --- | --- | --- |
| A | @ | the host's apex address (shown in its domain settings) |
| CNAME | www | the host's target (Vercel: `cname.vercel-dns.com`) |
| TXT | @ or subdomain | the host's verification value, when asked |

For email, add SPF, DKIM and a DMARC record (begin with
`v=DMARC1; p=none; rua=mailto:you@yourdomain` and tighten to `quarantine` when
the reports look clean); without them, mail lands in spam. Pick one canonical
hostname, redirect the other, and confirm HTTPS works.

## 5. Watch the launch

Re-confirm that error tracking, uptime monitors and alerts fire from
production. Complete the core flow on the live site, then have the user repeat
it on a phone. During week one, look daily at errors, sign-ups, payments and
the support inbox, and add lessons to the runbook.

## 6. Mobile, if any

With Expo, `eas build` and `eas submit` reach TestFlight and Play's internal
track. For native projects, archive in Xcode for App Store Connect and build an
app bundle for Play Console. Developer accounts belong to the user (check
current fees). Run a beta first, then submit using the launch stage's listing.

## Exit gate

```bash
python3 $FR gate publish
```

Needs a fully ticked `publish.md`, the recorded go, a passing review, a shippable
coverage verdict and **every readiness item satisfied**.

## Hand off

Give the user the live URL, the DNS records set, the readiness percent and the
first-week watch list. Then `python3 $FR status` and the conductor's closing
summary.
