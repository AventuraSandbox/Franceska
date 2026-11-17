# Runbook: {{product}}

## Contacts
| role | name | how to reach | when |
| --- | --- | --- | --- |
| owner / on call | | | always |
| payments contact | | | payment incidents |

## Where things live
| thing | location |
| --- | --- |
| code | |
| hosting | |
| database | |
| DNS | |
| error tracking | |
| uptime monitor | |
| status page | |

## Deploy
1. Merge to main after CI is green.
2. {{how the host deploys; how to watch it}}
3. Check the health endpoint and one core flow.

## Rollback
1. {{how to promote the previous release}}
2. {{migration rollback or forward-fix note}}
3. Confirm health and the core flow, then post in the incident channel.

## Incident
1. Acknowledge the alert; note the time.
2. Decide: roll back, or fix forward.
3. Tell customers where they will look (status page or email) if impact exceeds 15 minutes.
4. After: write what happened, why, and one change that prevents it.

## Backups and restore
- backups: {{schedule, where}}
- last restore rehearsal: {{date, result}}

## Routine
- daily during week one: errors, signups, payments, support mail
- monthly: dependency audit, restore rehearsal, rotate keys that are due
