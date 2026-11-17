---
name: franceska-connect
description: >-
  Makes the product real on the server side: authentication, database
  migrations and access rules, Stripe in test mode, email and background jobs,
  official-API integrations, plus the hardening production needs: security
  headers, rate limits, input validation, health endpoint, secrets hygiene,
  account deletion and data export, and CI. Use for requests like "set up accounts",
  "connect a database", "take payments", "harden this", "make it production
  grade", or once franceska-build is done.
---

# franceska-connect

**Stage:** Connect · **Role:** Backend Engineer.

```bash
FR=<path to this skill>/scripts/fr.py
python3 $FR start connect
python3 $FR ready init                  # once: creates the production evidence file
python3 $FR ready --area SEC,REL,LEG    # see what this stage still owes
```

Input: `architecture.md`. Output: server code, migrations, `.env.example` (see
`templates/env.example`), `connect.md` (checklist in `templates/connect.md`),
and a CI workflow (`templates/ci.example.yml`).

## Boundaries

- Only official, documented APIs, with the user's own credentials. Never the
  the reference app's private endpoints or OAuth client.
- Accounts and keys belong to the user, who creates them. Claude does not
  register for services or touch passwords, cards or live keys; it lists
  variable names in `.env.example` and leaves values blank.
- Stay in test mode (Stripe test keys, test cards) until publish.

## Build, in this order

**Identity.** Sign-up with email verification, password reset, optional magic
links, and OAuth through the user's own developer apps. Sessions use secure
http-only cookies with a global sign-out. Where explore found roles or teams,
route every permission question through one function. Include **real account
deletion and a data export for users**, which privacy law and Apple's sign-up
rules both expect.

**Data.** Commit migrations derived from `architecture.md` and run them from a
script. Put access rules on every table and prove them with a second user who
sees nothing of the first. Seed with invented people. Confirm backups are on.

**Money.** Let Stripe Checkout take plan sign-ups and the Customer Portal take
changes and cancellations; do not build card forms. Check webhook signatures,
record event IDs and make handlers safe to repeat. Cover checkout completed,
subscription updated or deleted, and invoice failed (with a retry and a message
to the customer). Keep each customer's plan in your own database, updated only
by webhooks, and enforce plan limits on the server. Cancelling is one click.

**Messages and jobs.** Transactional email from the user's own domain with
fresh templates. Time-based work runs as jobs with retries and a failure log;
store UTC, show local time.

**Integrations.** For each: official API, fewest scopes, review requirements,
rate limits. Google's sensitive scopes need verification that takes weeks; note
the lead time in `connect.md` and start early.

**Hardening.** These are production requirements, not polish.
- Security headers (CSP, HSTS, nosniff, frame and referrer policy): see
  `templates/security-headers.example.js`.
- Rate limiting for login, registration and any route that triggers email or SMS.
- Server-side validation on every write route.
- A health endpoint that checks the database: `templates/health.example.ts`.
- Secrets only in environment variables; `.env*` ignored by git.
- Uploads capped by size and type, served from a separate origin.
- No personal data in URLs or logs.
- Dependency audit clean of high and critical findings; paste the result as
  evidence for SEC-1.
- CI that runs lint, types, tests and a build on every push: copy
  `templates/ci.example.yml` to `.github/workflows/ci.yml` and adapt it.

Tick `connect.md` only for what is true and tested. Record evidence for the
items the tool cannot see in `franceska/production-readiness.md`:

```
| SEC-1 | done | npm audit: 0 high, 0 critical (output in evidence/audit-2026-11-16.txt) | 2026-11-16 |
```

## Exit gate

```bash
python3 $FR gate connect
python3 $FR secrets
```

Needs a fully ticked checklist, `.env.example`, no leaked secrets, and (with
`.env` ignored) a warning only if not. Open SEC, REL and LEG readiness items
show as warnings now and as failures at publish.

## Hand off

`franceska-test`.
