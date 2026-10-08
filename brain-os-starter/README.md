# Brain OS starter

Architecture source in the source package: [Obsidian and Brain OS Organization Starter Pack](../docs/references/obsidian-and-brain-os-starter-pack.md), preserved unchanged. After vault relocation this package reference remains outside the private vault; record its verified source-package location rather than copying private source material or assuming that sibling path exists.

Adopt in six phases: minimum control notes, filing rules, one real project, one justified operating hub, profile navigation, validation/maintenance with a restore rehearsal. Memory stores compact confirmed facts; skills store reusable execution rules; this vault stores context/navigation; Git stores code; document/file stores own originals; runtime owns operational state; credential systems own secret values.

Create once on supported Linux with `python3 -B scripts/create_brain_os.py /absolute/private/new-vault` from the source clone. The destination parent must exist; the destination must not. No existing vault is overwritten. The tool stages in a real sibling directory and uses descriptor-anchored Linux `renameat2(RENAME_NOREPLACE)`; it has no overwrite fallback on an unsupported system.

Open [Home](00-MOC/Home.md) for Current State, Task List Hub, Project Registry, Research Index, Reference Index and Inbox. The fictional garden is an example, never an owner fact. For an existing vault, the owner maps equivalent hubs explicitly instead of running this create-once tool over it.

Keep secrets in the selected credential route, not notes. Keep originals/editable assets/code outside the vault, with verified source locations linked from the owning project. Native Kanban remains workflow authority; knowledge indexes are human-facing navigation, not another scheduler.

Independent checks in `tests/release/test_generic_knowledge.py` cover existing and raced destinations, symlink traversal, interrupted staging and relative links after relocation. On failure no destination is promoted and only the attributable staging directory is removed. Remove a newly created private vault only through an owner-approved operation after verifying it contains no owner changes; installation does not authorize deletion of existing knowledge.
