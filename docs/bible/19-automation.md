# 19. Scheduling and durable automation

## Actor and authority
The owner authorizes recurring outcome, scope, timing and delivery. Native cron is the scheduler; the task controller remains native Kanban. No second scheduling sidecar is created.

## Prerequisites and version
Use documented native cron/tool schemas from the accepted runtime. Jobs, credentials and platform subscriptions are private owner state and never inherited from the factory.

## Inputs
Approved trigger/timezone, deterministic versus reasoning classification, idempotency key, source authority, output scope, retries/failure brakes, budget and real delivery route.

## Procedure
Preview the schedule with an explicit timezone. For deterministic maintenance prefer a bounded non-agent job when supported; reasoning jobs need native admission and model/resource limits. Give every mutation an idempotent target and durable receipt so retries cannot duplicate sends or edits. Test a harmless local run and intentionally failed route before enabling recurrence. Check task status and source evidence on resumption; a cron tick is not authority to release a worker. Delivery to a local-only CLI output is not remote notification. Verify the exact intended platform route and attachment result. Disable through native owner-approved pause/remove operations rather than deleting scheduler files.

## Expected results
One native schedule has a responsible owner, precise scope, bounded retries, failure brake and tested delivery. Missed notifications or observer outages do not spawn a competing task graph.

## Independent verification
Read back job/schedule, actual run receipt, idempotency result and destination. Conduct a duplicate-trigger test and failure/recovery trial in a disposable environment. This starter does not claim these live gates from packaging tests.

## Failure and recovery
On repeated failure pause the job and preserve receipts. Owner checks expiry/access, timezone and delivery configuration before resume. Do not enlarge scope or reconstruct missing runs.

## Privacy and outputs
Jobs and delivery credentials live only in the private home. Publish procedures, never inherited active automation.

## Sources
[Daily operation](20-daily.md), [official cron](https://hermes-agent.nousresearch.com/docs/user-guide/features/cron), [recovery](23-troubleshooting.md).
