# 11. Native task lifecycle

## Actor and authority
The owner-facing controller admits/releases children. Native Kanban owns dependencies, claims, runs and readiness; the embedded Gateway dispatcher launches workers. Workers never self-release or launch named profiles.

## Prerequisites and version
Governed APIs require the explicitly compatible custom Hermes runtime, installed timing adapter and native admission/evidence tooling. Stock availability must be audited; this candidate has not cleared public rights for every custom extension.

## Inputs
Stable objective key, owning board, exact originating platform/chat/thread/user route, controller workspace, timing run and immutable child packets.

## Procedure
Create exactly one root blocked. Subscribe the actual notify+wake destination and read it back. Start the installed timing run against immutable evidence, then read the report; failure leaves the root blocked. Release only the root after all predicates pass. The root creates each child blocked, links prerequisites→child and child→root before admission, verifies literal assignee/card/workspace/skills, registers the real timing transition, and authenticates admission/release. Never start a standalone dispatcher or wrapper. Park the root with typed dependency blocking, end its run and let native readiness/dispatcher resume it after child completion. Named reviewers are pre-created blocked and linked before packet sealing; release verifier only, then the dependent reviewer after terminal PASS on unchanged bytes.

### Shared pool, not per-role reservations

The configured ceilings are max_in_progress=6 system-wide,
max_in_progress_per_profile=6, and max_spawn=2 new launches per dispatcher tick.
Any eligible profile may occupy all six slots; there are no reserved/fixed per-profile quotas.
These are ceilings, not launch authority: admission, dependencies, review order
and literal task boundaries remain mandatory. Repository/worktree isolation,
heavy-test serialization, resource pressure and contract/policy limits may reduce
practical concurrency. Free slots never authorize overlapping edits or heavy
tests in one worktree. Record active narrower limits before release.

## Expected results
A durable graph survives chat interruption and observer failure. Every launch has prior admission, notification and timing evidence; no process PID or completion message substitutes for native state.

## Independent verification
Read back root/child runs and edge orientation. Confirm no child run precedes release and no reviewer runs on another head. The package's local DB dependency canary supplements, not replaces, real admitted execution/recovery.

## Failure and recovery
Keep malformed admission blocked. Recover through the same native root and exact stop evidence; never rewrite history, reset the graph or clear guards. Only genuine policy/credential/unavailable-capability gates need human routing.

## Privacy and outputs
Task IDs, receipts and notifications are private operational evidence. Public docs carry neutral sequence, not historical board state.

## Sources
[Review](13-review.md), [timing](14-timing.md), [package canary](../../scripts/full_system_package.py), [official Kanban documentation](https://hermes-agent.nousresearch.com/docs/user-guide/features/kanban).
