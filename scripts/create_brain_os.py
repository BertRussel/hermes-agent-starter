#!/usr/bin/env python3
"""Create an optional new Brain OS vault on Linux, never replace a destination."""
from __future__ import annotations

import argparse
import ctypes
import errno
import os
from pathlib import Path
import shutil
import stat
import sys
import uuid


def open_directory(path: Path) -> int:
    """Open each component without following symlinks, retaining parent identity."""
    if not path.is_absolute() or ".." in path.parts:
        raise ValueError("absolute non-traversing directory required")
    fd = os.open("/", os.O_RDONLY | os.O_DIRECTORY)
    try:
        for part in path.parts[1:]:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = child
        return fd
    except BaseException:
        os.close(fd)
        raise


def copy_notes(source_fd: int, target_fd: int) -> None:
    """Copy ordinary note bytes through anchored descriptors, rejecting links."""
    for name in sorted(os.listdir(source_fd)):
        if name.upper() in {"SOUL.MD", "AGENTS.MD", "HERMES.MD", "CLAUDE.MD"}:
            raise ValueError("instruction files are not knowledge scaffold")
        mode = os.stat(name, dir_fd=source_fd, follow_symlinks=False).st_mode
        if stat.S_ISDIR(mode):
            source_child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=source_fd)
            try:
                os.mkdir(name, mode=0o700, dir_fd=target_fd)
                target_child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=target_fd)
                try:
                    copy_notes(source_child, target_child)
                finally:
                    os.close(target_child)
            finally:
                os.close(source_child)
        elif stat.S_ISREG(mode) and name.endswith(".md"):
            source_file = os.open(name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=source_fd)
            try:
                if not stat.S_ISREG(os.fstat(source_file).st_mode):
                    raise ValueError("source type changed")
                target_file = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                                      0o600, dir_fd=target_fd)
                with os.fdopen(target_file, "wb") as output:
                    with os.fdopen(source_file, "rb", closefd=False) as source:
                        shutil.copyfileobj(source, output)
                    output.flush()
                    os.fsync(output.fileno())
            finally:
                os.close(source_file)
        else:
            raise ValueError("unsafe or unexpected knowledge member")
    os.fsync(target_fd)


def create_brain_os(source: Path, destination: Path) -> Path:
    """Stage in the destination parent and atomically promote with NOREPLACE."""
    if sys.platform != "linux":
        raise RuntimeError("create-once promotion requires supported Linux renameat2")
    if not destination.is_absolute() or destination.name in {"", ".", ".."} or ".." in destination.parts:
        raise ValueError("absolute non-traversing destination required")
    libc = ctypes.CDLL(None, use_errno=True)
    try:
        rename = libc.renameat2
    except AttributeError as error:
        raise RuntimeError("renameat2 unavailable; no overwrite fallback") from error
    rename.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
    rename.restype = ctypes.c_int
    parent_fd = open_directory(destination.parent)
    stage_name = ".brain-os-stage-" + uuid.uuid4().hex
    staged = False
    try:
        try:
            os.stat(destination.name, dir_fd=parent_fd, follow_symlinks=False)
        except FileNotFoundError:
            pass
        else:
            raise FileExistsError("vault destination already exists")
        source_fd = open_directory(source)
        try:
            os.mkdir(stage_name, mode=0o700, dir_fd=parent_fd)
            staged = True
            stage_fd = os.open(stage_name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent_fd)
            try:
                copy_notes(source_fd, stage_fd)
            finally:
                os.close(stage_fd)
        finally:
            os.close(source_fd)
        if rename(parent_fd, os.fsencode(stage_name), parent_fd, os.fsencode(destination.name), 1) != 0:
            code = ctypes.get_errno()
            if code == errno.EEXIST:
                raise FileExistsError("vault destination appeared during staging")
            raise OSError(code, "no-replace vault promotion failed")
        staged = False
        os.fsync(parent_fd)
    finally:
        if staged:
            # Remove only our unpredictable, descriptor-anchored sibling staging dir.
            shutil.rmtree(stage_name, dir_fd=parent_fd)
        os.close(parent_fd)
    return destination


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path, help="absent absolute private destination")
    args = parser.parse_args()
    try:
        create_brain_os(Path(__file__).resolve().parents[1] / "brain-os-starter", args.destination)
    except (ValueError, OSError, RuntimeError) as error:
        print(str(error), file=sys.stderr)
        return 1
    print("New private vault created; existing vaults were not modified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
