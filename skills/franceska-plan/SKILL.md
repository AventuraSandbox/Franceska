---
name: franceska-plan
description: >-
  Turns the explore map into a technical plan: stack choices with reasons, a real
  SQL schema with access rules and indexes, the API surface per flow, the
  hazards that usually bite, and a build order that begins with a thin vertical
  slice. Use for requests like "how should we build this", "which stack", "model the
  data", "draft the schema" or "outline the API", or once franceska-explore is done.
---

# franceska-plan

**Stage:** Plan · **Role:** Software Architect.

```bash
FR=<path to this skill>/scripts/fr.py
python3 $FR start plan
```

Inputs: `explore.md`, `features.csv`. Outputs: `architecture.md` (see
`templates/architecture.md`) and `schema.sql`. If there is no explore map,
stop and run that stage before planning anything.

## Choosing the stack

Honour the user's existing stack. Otherwise prefer hosted, well-documented
parts that cost little at zero users, and write one line of reasoning for each:

| layer | default | alternatives |
| --- | --- | --- |
| web | Next.js (App Router), TypeScript | Remix, SvelteKit, Rails |
| styling | Tailwind fed by design tokens | CSS modules |
| mobile | Expo (React Native) | SwiftUI, Kotlin |
| database | Postgres on Supabase or Neon | SQLite on Turso |
| data access | Drizzle or Prisma | plain SQL |
| auth | Supabase Auth or Auth.js | Clerk |
| payments | Stripe Checkout and Billing | Paddle, Lemon Squeezy |
| email | Resend or Postmark | SES |
| background work | Vercel Cron, Inngest, Trigger.dev | a small worker |
| files | Supabase Storage or Cloudflare R2 | S3 |
| hosting | Vercel | Netlify, Fly, Render |

One database, one deployable. Copy the reference app's features, not its
infrastructure. If the user's machine forbids local installs, favour hosted
tooling and cloud dev environments, and say so in the table.

## Designing the schema

Write `schema.sql`. Each table gets a uuid primary key, `created_at` and
`updated_at`, an owner column for anything a user owns, explicit `on delete`
behaviour, an index for every foreign key and every filtered or sorted column,
check constraints on status fields, `timestamptz` for all times, money as
integer minor units plus a currency, and a stated **access rule** (row-level
security, or an authorisation check inside every query).

Then encode the invariants explore found. "Two reservations for one slot" is a
database constraint, not a UI nicety.

## Laying out the API

For each flow, tabulate the method and path, its purpose, who calls it, and its
input and output. Add webhooks (in and out) and scheduled jobs with timing.
Depend only on official, documented APIs and the user's own keys.

## Naming the hazards

One line each, where they apply: time zones and DST, duplicate webhook
delivery, races, rate limits, upload limits, search, realtime, offline, email
deliverability, tenancy, deletion duties (privacy law, store rules). Also name
what production will demand later: a health endpoint, backups, a staging
environment and a rollback path, so the build leaves room for them.

## Ordering the build

1. A rough but complete slice of the core loop, to prove the stack works.
2. Must-haves, grouped by area.
3. Should-haves next, then could-haves.
4. Fixes from the validate stage.
Under each milestone, list its screen IDs, tables and routes.

## Exit gate

```bash
python3 $FR gate plan
```

Needs `architecture.md` with stack, API or routes, risks and build order, and a
`schema.sql` with tables. Warns about naive timestamps and float columns.

## Hand off

One line each on stack, table count, route count and the three riskiest parts.
Ask the user to approve stack and order, then `franceska-design`.
