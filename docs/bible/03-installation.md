# 3. Preflight and safe installation

## Actor and authority
Only the owner/operator installs on a real target. Disposable acceptance installs are explicitly separate and must not activate live profiles, services or aliases.

## Prerequisites and version
Require a reviewed source revision, retained notices, supported Python and a dependency-isolated environment. This candidate currently lacks cleared public sources for all required custom components; do not treat a factory archive as an approved public installer.

## Inputs
Exact release/archive checksums, compatibility manifest, destination home, role mapping, owner backup and platform information.

## Procedure
Verify checksums before extraction. Reject links, traversal, duplicate, extra, missing or modified members. Create a fresh private HOME with a scrubbed environment: do not inherit provider keys, live HERMES_HOME, task bindings or shell initialization. Rebuild dependencies from pinned source rather than copying a virtual environment. Inspect `hermes profile install --help` on the accepted runtime. Install a local extracted distribution with `hermes profile install /absolute/extracted/profiles/forge --name forge`; do not use force, activation or alias creation as bootstrap defaults. Keep personal identity separate until rendered fields are reviewed.

Read the actual dispatcher configuration before enabling work: the configured
shared pool has max_in_progress=6 system-wide, max_in_progress_per_profile=6,
and max_spawn=2 new launches per dispatcher tick. Any eligible profile can use
all six slots; there are no reserved/fixed per-profile quotas. These are ceilings,
not launch authority. Native admission/task boundaries still apply;
repository/worktree isolation, heavy-test serialization, resource pressure and
contract/policy limits may reduce practical concurrency. Do not alter a live
Gateway to match this guide; configuration/lifecycle remain owner-controlled.

## Expected results
The named profile resides in the selected isolated root, its source-owned files match extracted hashes, and no live home, active-profile selector or Gateway changes occur. Native installation rewrites distribution provenance/timestamp metadata; verify payload files separately.

## Independent verification
The six-profile canary in the canonical package builder installs from extracted archives using rebuilt Hermes and verifies exact payload hashes. Independently repeat on the released bytes and check absence of inherited auth.

## Failure and recovery
Refuse existing-profile overwrite. Preserve a failed attempt's logs privately. Remove only attributable disposable output; never clean a directory merely because its pathname resembles a test fixture.

## Privacy and outputs
Homes, logs and backups are private. The archive is source, not credentials or owner acceptance.

## Sources
[Package builder](../../scripts/full_system_package.py), [role tests](../../tests/release/test_generic_roles.py), [updates](22-updates.md), [official docs](https://hermes-agent.nousresearch.com/docs/).
