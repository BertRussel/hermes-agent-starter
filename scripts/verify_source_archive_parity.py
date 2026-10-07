#!/usr/bin/env python3
"""Build and verify a deterministic archive of one exact visible Git tree.

The archive is intentionally derived from the named commit, not the ambient
worktree.  It contains ordinary tracked source bytes only: no Git metadata,
ignored controller material, local paths, or generated state.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tarfile


def git(root: Path, *args: str) -> bytes:
    result = subprocess.run(
        ["git", "--no-replace-objects", "-C", str(root), *args],
        check=False,
        capture_output=True,
    )
    if result.returncode:
        raise ValueError("unable to read exact source tree")
    return result.stdout


def tree_members(root: Path, source_ref: str) -> tuple[str, str, list[tuple[str, str, bytes]]]:
    head = git(root, "rev-parse", source_ref).decode().strip()
    tree = git(root, "rev-parse", f"{source_ref}^{{tree}}").decode().strip()
    members: list[tuple[str, str, bytes]] = []
    for raw in git(root, "ls-tree", "-r", "-z", source_ref).split(b"\0"):
        if not raw:
            continue
        metadata, raw_path = raw.split(b"\t", 1)
        mode, kind, blob = metadata.split()
        path = raw_path.decode("utf-8")
        if kind != b"blob" or mode not in {b"100644", b"100755"}:
            raise ValueError("source tree has unsupported member")
        if path.startswith("docs/internal/controller-only/") or path.startswith(".git/"):
            raise ValueError("private or metadata path in visible source tree")
        data = git(root, "cat-file", "blob", blob.decode())
        members.append((path, mode.decode(), data))
    if not members:
        raise ValueError("empty visible source tree")
    return head, tree, members


def write_archive(members: list[tuple[str, str, bytes]], output: Path) -> str:
    with output.open("xb") as raw:
        with gzip.GzipFile(fileobj=raw, mode="wb", filename="", mtime=0) as zipped:
            with tarfile.open(fileobj=zipped, mode="w|") as archive:
                for path, mode, data in members:
                    info = tarfile.TarInfo(f"hermes-agent-starter/{path}")
                    info.size = len(data)
                    info.mode = int(mode, 8)
                    info.mtime = 0
                    info.uid = info.gid = 0
                    info.uname = info.gname = ""
                    archive.addfile(info, io.BytesIO(data))
    return hashlib.sha256(output.read_bytes()).hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-ref", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    root = Path.cwd().resolve()
    output = args.output.resolve()
    if output.exists() or output.is_symlink():
        raise ValueError("archive output must not already exist")
    head, tree, members = tree_members(root, args.source_ref)
    digest = write_archive(members, output)
    print(json.dumps({
        "ok": True,
        "source_ref": args.source_ref,
        "expected_head": head,
        "expected_tree": tree,
        "member_count": len(members),
        "archive_sha256": digest,
        "output": str(output),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
