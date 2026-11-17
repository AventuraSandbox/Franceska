# Backend record

## Accounts the user created
| service | purpose | variables | mode |
| --- | --- | --- | --- |

## Integrations
| integration | official API | scopes | approval needed | lead time |
| --- | --- | --- | --- | --- |

## Checklist (tick only what is true and tested)
- [ ] secrets live only in environment variables; .env* is git-ignored; nothing in client bundles
- [ ] every write route validates input on the server
- [ ] every read and write checks authorisation, tested with a second user
- [ ] throttling on login, registration and every route that triggers email or SMS
- [ ] webhooks verify signatures and are idempotent
- [ ] uploads limited by size and type and served from a separate origin
- [ ] no personal data in URLs or logs
- [ ] dependency audit has no high or critical findings
- [ ] account deletion removes data; users can export theirs
- [ ] backups on
- [ ] plan limits enforced on the server
- [ ] health endpoint checks the database
- [ ] CI runs lint, types, tests and build on every push
