# 7. Brain OS and Obsidian

## Actor and authority
The owner chooses a new private vault or maps an existing structure. Agents maintain discoverable notes within the granted knowledge scope; no vault migration or overwrite is inferred.

## Prerequisites and version
The create-once tool supports Linux with descriptor-anchored renameat2 no-replace. Parent directory must already exist. A cloud/vault pathname is not proof of access or synchronization.

## Inputs
Absent absolute destination, starter notes or explicit existing-hub mapping, source ownership records and owner-approved project facts.

## Procedure

Use the unchanged [Obsidian and Brain OS organization reference](../references/obsidian-and-brain-os-starter-pack.md). The starter provides Home, Current State, one owner-facing Task List, Project Registry, Research Index, Reference Index, Agent/Profile MOC, Decision Journal and temporary Inbox. The storage hub is justified by multiple file/code/credential/runtime routes and their approval boundaries; add other domain hubs only when real routing complexity warrants them. Native tasks own execution state, while the Task List is the single human-facing work view, not a competing scheduler.

Adopt in six phases: minimal control notes; filing rules; first real project with decision/evidence links; first justified operating hub; profile navigation; validation/maintenance and tested recovery. Compact stable facts belong in memory, reusable execution procedures in skills, durable context in Obsidian, code in Git/GitHub, original/editable binaries in file/document stores, operational databases/sessions in runtime state and secret values in credential systems. Promote raw captures to cited synthesis, accepted decisions and proven procedures separately. Use sparse INDEX.md only where navigation demonstrably fails, and controlled type/domain/status/safety tags instead of a second hierarchy. Follow the starter's linked maintenance procedure for index/link health, supersession, Inbox review and sample backup/restore; do not claim cloud sync or off-host recovery from a local fixture.

For a new vault run `python3 -B scripts/create_brain_os.py /absolute/private/new-vault`. Open Home and follow Current State, Task List Hub, Project Registry, Research Index, Reference Index and Inbox. For existing knowledge, inventory equivalent hubs and ask the owner only about material ambiguity; never create a competing second vault. File raw captures in Inbox, accepted cited findings in Research, implementation/decisions under the owning project, reusable proven procedures in Reference. Update topic/project/index links after each durable change. Keep code, cloud originals, editable masters and binary archives outside the knowledge vault, with verified source paths/IDs and access status in project notes. Stable memory is a compact index of confirmed facts, not duplicated project knowledge.

## Expected results
Every durable note is discoverable from an owning index; relative wikilinks still resolve after relocation. Current facts and outstanding tasks remain distinct. Existing vaults and owner modifications survive setup.

## Independent verification
Tests cover existing/raced destinations, source/destination symlinks, interrupted staging and link relocation. An owner separately verifies real Obsidian access, link health and cloud synchronization; local file creation does not prove these routes.

## Failure and recovery
On a raced destination, the owner's existing data wins and only the attributable staging directory is removed. Unsupported promotion fails closed without overwrite fallback. Interrupted source filing requires index reconciliation, not blind folder recreation.

## Privacy and outputs
Vault contents are private and excluded from public export. No secrets or private source backups in notes.

## Sources
[Starter](../../brain-os-starter/README.md), [creator](../../scripts/create_brain_os.py), [tests](../../tests/release/test_generic_knowledge.py).
