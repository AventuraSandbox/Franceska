# Deploy record

## Checks (paste results beside each)
- [ ] CI green on main
- [ ] coverage verdict is shippable
- [ ] clean-room audit passes
- [ ] code scan is clean
- [ ] listing lint passes (if shipping to stores)
- [ ] no secrets in the code
- [ ] production readiness is 100% (`python3 fr.py ready`)
- [ ] no open S1 or S2 bugs
- [ ] policy pages live and listing every processor
- [ ] consent banner if non-essential cookies are used in the EU or UK
- [ ] account deletion and data export work
- [ ] favicon, titles and share image are ours

## Production services
- [ ] production has its own database, backups are on, release runs the migrations
- [ ] production variables set from .env.example
- [ ] Stripe live: products, prices, webhook and secret, one real purchase refunded
- [ ] OAuth redirect URIs and origins updated for the production domain
- [ ] email domain verified (SPF, DKIM, DMARC)

## Domain
- [ ] DNS records set, HTTPS works, one canonical host

## After release
- [ ] error tracking, uptime checks and alerts confirmed in production
- [ ] core flow completed on the live site and on a phone

## The user's go
GO: {{their words, and the date}}
