# Architecture: {{product}}

## Stack
| layer | choice | reason |
| --- | --- | --- |
| web | | |
| database | | |
| auth | | |
| payments | | |
| email | | |
| background work | | |
| hosting | | |

## Data
Schema in schema.sql. Access rule: {{row-level security | check inside every query}}.
Invariants enforced by the database: {{}}

## API
| method and path | purpose | caller | input | output | flow |
| --- | --- | --- | --- | --- | --- |

Inbound webhooks: {{}} | Outbound webhooks: {{}} | Scheduled jobs: {{name and timing}}

## Hazards
- time zones and DST:
- duplicate webhook delivery:
- concurrent writes:
- {{limits, search, realtime, offline, deliverability, tenancy, deletion duties}}

## Production hooks to leave room for
health endpoint | staging environment | backups and restore | rollback path

## Build order
1. Thin slice: {{core loop; screens, tables, routes}}
2. Must-haves, by area:
3. Should-haves next, then could-haves:
4. Fixes from the validate stage:
