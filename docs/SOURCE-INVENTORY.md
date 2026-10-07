# Public source inventory

This repository is a browsable source starter, not an installation image or a
private-agent export. The positive inventory is `release-manifest.json`: every
archive member must be an ordinary tracked source file declared there. No file
is public merely because it exists in a checkout.

## Navigation

- [Start here](START-HERE.md) and [overview](OVERVIEW.md) introduce the owner and operator paths.
- [Agent Bible](AGENT-BIBLE.md), the [full-system index](full-system/Component%20Index.md), and
  [worked workflows](WORKED-WORKFLOWS.md) provide operating guidance.
- `brain-os-starter/` is a generic, fictional Knowledge-base starter.
- `profiles/` contains generic role distributions and their readable contracts.
- `runtimes/`, `runtime-bundle/`, `scripts/`, and `tests/` contain the supporting source,
  explicit boundaries, and deterministic checks.
- `templates/` is public input scaffolding. Keep a completed owner intake outside this tree.

## Archive boundary

`scripts/verify_source_archive_parity.py` reads the requested Git commit/tree,
not the local worktree, and writes a deterministic optional archive. It refuses
Git metadata and `docs/internal/controller-only/`. Archive member bytes come
from the exact tree blobs; timestamps and ownership metadata are normalized.
The command reports the exact head, tree, member count, and SHA-256.

The PDF owner-intake template is the sole approved binary source asset. Its
hash is pinned by the release tests; it is not rewritten by the archive tool.

## Exclusions

Do not add completed intake forms, Souls, USER/MEMORY files, credentials,
browser data, logs, databases, controller evidence, generated archives, or
recipient-specific implementation. `docs/internal/controller-only/` remains
ignored, untracked, and outside both the positive inventory and archive.
