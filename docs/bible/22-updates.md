# 22. Updates, backup and restoration

## Actor and authority
The owner authorizes real-home/version changes and rollback. Makers test only isolated homes; source upgrades do not authorize credential migration, Gateway restart or owner identity replacement.

## Prerequisites and version
Retain previous accepted source/locks and a private backup. Native distribution update overwrites distribution-owned SOUL.md and skills; config is preserved by default, while memories/local namespaces remain user-owned. A personalized Soul requires an explicit preservation plan before update.

## Inputs
Current/next accepted version, private identity/config/memory/vault hash inventory, backup destination, supported migration policy and rollback criteria.

## Procedure
Freeze current source and enumerate private state without exposing values. Use native profile export/import for a credential-free private restore drill; secure credentials need a separate owner recovery route. Test restore into an absent home/name and verify every protected/private hash. For unchanged distribution refresh, `hermes profile update forge` follows native source provenance; do not use force-config or apply this command blindly to a personalized owner identity. For a true version update, install the new distribution in a separate disposable home, migrate approved private state through supported guarded routes, run full acceptance and compare private hashes before switching the real owner route. Keep old source and tested private restore available until owner acceptance. No live Gateway switch/restart is implied.

## Expected results
Canaries verify six native installations, same-version refresh, distinct distribution-version metadata/README upgrade and downgrade, and pre-update native backup import. Tested config/local/memory/Soul and a separate fictional vault retain identical hashes. This proves the exercised distribution-content transitions, not runtime/schema migration, preservation of a modified owner Soul against new instructions, full-home backup or credential recovery.

## Independent verification
Rehash restored private files and reopen vault indexes. Exercise an intentional failed update and the real prior-version rollback; confirm no unrelated private files change.

## Failure and recovery
Reject overwrite of an existing restore destination. Stop unsupported migrations before mutation. On any preservation mismatch retain old accepted environment and return a precise owner-controlled recovery operation.

## Privacy and outputs
Backups may contain owner knowledge/identity and must remain private even when credential-free. Never distribute them as release assets.

## Sources
[Native canary](../../scripts/full_system_package.py), [role tests](../../tests/release/test_generic_roles.py), [knowledge](07-knowledge.md).
