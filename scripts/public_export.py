#!/usr/bin/env python3
"""Deterministic exact-file public source export; no Git history or private state.

Component rights records are supplied by the owning controller, not inferred
from file presence. This utility never creates a repo, publishes or installs.
"""
from __future__ import annotations

import ctypes
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import tarfile
import uuid

try:
    from scripts.create_brain_os import open_directory
except ModuleNotFoundError as error:
    if error.name != "scripts":
        raise
    from create_brain_os import open_directory

FORBIDDEN = {'.git', '.env', 'auth.json', 'sessions', 'memories', 'logs', 'cache',
             '__pycache__', 'node_modules', 'controller-only', '.full-system-proof', '.full-system-fixture'}
CREDENTIAL_PATTERN = re.compile(rb'(?:ghp_[A-Za-z0-9]{36,}|github_pat_[A-Za-z0-9_]{40,}|sk-[A-Za-z0-9_-]{32,}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----)')
PRIVATE_PATH = re.compile(rb'(?:/home/[A-Za-z0-9._-]+/|/srv/[A-Za-z0-9._-]+/|\bt_[0-9a-f]{8}\b)')
MAX_BYTES = 128 * 1024 * 1024


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def valid_path(name: str) -> bool:
    return (isinstance(name, str) and bool(name) and not name.startswith('/') and '\\' not in name
            and not any(ord(char) < 32 for char in name)
            and all(part not in {'', '.', '..'} | FORBIDDEN for part in name.split('/'))
            and not name.endswith(('.db', '.sqlite', '.log', '.pyc', '.bundle')))


def scan(name: str, data: bytes) -> None:
    if (not valid_path(name) or name.endswith(('.gz', '.zip', '.tar', '.tgz', '.7z'))
            or data.startswith((b'\x1f\x8b', b'PK\x03\x04', b'7z\xbc\xaf\x27\x1c'))
            or CREDENTIAL_PATTERN.search(data) or PRIVATE_PATH.search(data)):
        # Never print secret matches or private values.
        raise ValueError('public byte/path privacy rejection')


def read_member(root: Path, name: str) -> bytes:
    if not valid_path(name):
        raise ValueError('public path rejection')
    root_fd = open_directory(root)
    fd = root_fd
    try:
        for part in name.split('/')[:-1]:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            if fd != root_fd:
                os.close(fd)
            fd = child
        member_fd = os.open(name.split('/')[-1], os.O_RDONLY | os.O_NOFOLLOW, dir_fd=fd)
        with os.fdopen(member_fd, 'rb') as member:
            info = os.fstat(member.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_BYTES:
                raise ValueError('unsafe public source member')
            data = member.read(MAX_BYTES + 1)
            if len(data) > MAX_BYTES:
                raise ValueError('excessive public source size')
            return data
    finally:
        if fd != root_fd:
            os.close(fd)
        os.close(root_fd)


def selected_files(manifest: dict) -> list[str]:
    if not isinstance(manifest, dict) or manifest.get('schema_version') != 1 or manifest.get('status') != 'public-candidate':
        raise ValueError('public candidate disposition incomplete')
    components = manifest.get('components')
    if not isinstance(components, list) or not components:
        raise ValueError('empty public component inventory')
    names = []
    ids = set()
    for component in components:
        if not isinstance(component, dict) or not isinstance(component.get('id'), str) or component['id'] in ids:
            raise ValueError('invalid/duplicate public component')
        ids.add(component['id'])
        if (component.get('disposition') != 'carry-unchanged'
                or component.get('public_rights') not in {'verified-original', 'verified-upstream'}
                or not isinstance(component.get('license'), str) or not component['license']):
            raise ValueError('public source rights/disposition unresolved')
        files = component.get('files')
        if (not isinstance(files, list) or not files
                or not all(valid_path(name) and not name.endswith(('.gz', '.zip', '.tar', '.tgz', '.7z')) for name in files)):
            raise ValueError('invalid public file allowlist')
        names.extend(files)
    if len(names) != len(set(names)) or 'manifest.json' in names or len(names) > 20000:
        raise ValueError('duplicate/reserved/excessive public file allowlist')
    return sorted(names)


def encoded_inventory(files: dict[str, bytes]) -> bytes:
    return (json.dumps({'schema_version': 1, 'files': [
        {'path': name, 'size': len(data), 'sha256': sha256(data)}
        for name, data in sorted(files.items())]}, sort_keys=True, indent=2) + '\n').encode()


def component_inventory(source: Path, manifest: dict) -> dict:
    """Hash exact declared files even when rights remain blocked; grant no rights."""
    if not isinstance(manifest, dict) or manifest.get('schema_version') != 1:
        raise ValueError('invalid component inventory schema')
    components = manifest.get('components')
    if not isinstance(components, list) or not components:
        raise ValueError('empty component inventory')
    records, ids, paths = [], set(), set()
    for component in components:
        if (not isinstance(component, dict) or not isinstance(component.get('id'), str)
                or not component['id'] or component['id'] in ids):
            raise ValueError('invalid/duplicate component inventory')
        ids.add(component['id'])
        names = component.get('files')
        if not isinstance(names, list) or any(not valid_path(name) for name in names):
            raise ValueError('invalid component file inventory')
        if any(name in paths for name in names) or len(names) != len(set(names)):
            raise ValueError('duplicate component file inventory')
        paths.update(names)
        files, clean = [], True
        for name in sorted(names):
            data = read_member(source, name)
            try:
                scan(name, data)
            except ValueError:
                clean = False
            files.append({'path': name, 'bytes': len(data), 'sha256': sha256(data)})
        rights = (component.get('disposition') == 'carry-unchanged'
                  and component.get('public_rights') in {'verified-original', 'verified-upstream'}
                  and isinstance(component.get('license'), str) and bool(component['license']))
        gate = ('blocked-rights-or-disposition' if not rights else
                'blocked-empty-inventory' if not files else
                'blocked-byte-privacy' if not clean else 'passed-declared-files-only')
        records.append({'id': component['id'], 'disposition': component.get('disposition'),
                        'public_rights': component.get('public_rights'),
                        'license': component.get('license'), 'files': files, 'gate': gate})
    return {'schema_version': 1, 'components': records,
            'export_authorized': manifest.get('status') == 'public-candidate'
            and all(record['gate'] == 'passed-declared-files-only' for record in records),
            'limits': 'declared files only; inventory is not legal review or public-history certification'}


def scan_public_history(repository: Path, expected_head: str) -> dict:
    """Scan every reachable ref's commits, paths and blob bytes; never print matches.

    Run only on an explicitly selected public source repository. This read-only
    scanner does not sanitize private history, authorize export or inspect auth.
    Shallow history and submodules fail closed rather than claiming coverage.
    """
    if not isinstance(expected_head, str) or re.fullmatch('[0-9a-f]{40}', expected_head) is None:
        raise ValueError('exact head required for history scan')
    repository = Path(repository).absolute()
    fd = open_directory(repository)
    os.close(fd)
    environment = {'PATH': '/usr/bin:/bin', 'HOME': '/nonexistent', 'LANG': 'C.UTF-8',
                   'GIT_CONFIG_NOSYSTEM': '1', 'GIT_CONFIG_GLOBAL': '/dev/null',
                   'GIT_TERMINAL_PROMPT': '0', 'GIT_NO_LAZY_FETCH': '1'}

    def git(*arguments: str) -> bytes:
        result = subprocess.run(['git', '--no-replace-objects', '-C', str(repository), *arguments],
                                env=environment, capture_output=True, timeout=60)
        if result.returncode:
            raise ValueError('public history read failed; no partial certification')
        return result.stdout

    if git('rev-parse', 'HEAD').decode().strip() != expected_head:
        raise ValueError('public history head mismatch')
    if git('rev-parse', '--is-shallow-repository').strip() != b'false':
        raise ValueError('complete public history required; shallow clone rejected')
    graft = Path(os.fsdecode(git('rev-parse', '--git-path', 'info/grafts').strip()))
    if not graft.is_absolute():
        graft = repository / graft
    if graft.exists() or graft.is_symlink():
        raise ValueError('grafted history rejected')
    commits = git('rev-list', '--all', expected_head).decode().splitlines()
    blobs, scanned_bytes = {}, 0
    inventory_hash = hashlib.sha256()

    def object_bytes(oid: str, kind: str) -> bytes:
        nonlocal scanned_bytes
        size = int(git('cat-file', '-s', oid))
        scanned_bytes += size
        if size > MAX_BYTES or scanned_bytes > MAX_BYTES * 4:
            raise ValueError('public history scan byte limit; no partial certification')
        data = git('cat-file', kind, oid)
        if len(data) != size:
            raise ValueError('public history object size mismatch')
        return data

    try:
        for commit in commits:
            scan('history/' + commit + '.commit', object_bytes(commit, 'commit'))
            for entry in git('ls-tree', '-r', '-z', commit).split(b'\0'):
                if not entry:
                    continue
                metadata, raw_name = entry.split(b'\t', 1)
                mode, kind, raw_oid = metadata.split()
                name, oid = raw_name.decode('utf-8', errors='strict'), raw_oid.decode('ascii')
                if kind != b'blob' or mode not in {b'100644', b'100755'} or not valid_path(name):
                    raise ValueError('unsafe historical member')
                if oid not in blobs:
                    data = object_bytes(oid, 'blob')
                    # Path-independent checks are repeated below for every alias.
                    scan(name, data)
                    blobs[oid] = data
                    inventory_hash.update((oid + ':' + sha256(data) + '\n').encode())
                scan(name, blobs[oid])
    except (UnicodeError, ValueError) as error:
        raise ValueError('public history privacy/coverage rejection; matches redacted') from None
    if git('rev-parse', 'HEAD').decode().strip() != expected_head:
        raise ValueError('public history head mismatch after scan')
    return {'status': 'passed-all-reachable-bytes', 'expected_head': expected_head,
            'commits': len(commits), 'unique_blobs': len(blobs), 'scanned_bytes': scanned_bytes,
            'blob_inventory_sha256': inventory_hash.hexdigest(),
            'scope': 'all reachable refs; no dangling-object or remote-publication certification'}


def build_public_export(source: Path, manifest: dict, archive: Path) -> str:
    names = selected_files(manifest)  # Rights failure occurs before source reads/writes.
    files = {name: read_member(source, name) for name in names}
    if sum(map(len, files.values())) > MAX_BYTES:
        raise ValueError('excessive public payload size')
    for name, data in files.items():
        scan(name, data)
    files['manifest.json'] = encoded_inventory(files)
    parent_fd = open_directory(archive.absolute().parent)
    try:
        output_fd = os.open(archive.name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                            0o600, dir_fd=parent_fd)
        try:
            with os.fdopen(output_fd, 'wb') as raw:
                with gzip.GzipFile(fileobj=raw, mode='wb', filename='', mtime=0) as compressed:
                    with tarfile.open(fileobj=compressed, mode='w|') as output:
                        for name, data in sorted(files.items()):
                            info = tarfile.TarInfo('public-agent-starter/' + name)
                            info.size, info.mode, info.mtime = len(data), 0o644, 0
                            info.uid = info.gid = 0
                            info.uname = info.gname = ''
                            output.addfile(info, io.BytesIO(data))
        except BaseException:
            os.unlink(archive.name, dir_fd=parent_fd)
            raise
    finally:
        os.close(parent_fd)
    return sha256(read_member(archive.absolute().parent, archive.name))


def restore_public_export(archive: Path, destination: Path, *, expected_sha256: str) -> Path:
    data = read_member(archive.absolute().parent, archive.name)
    if sha256(data) != expected_sha256:
        raise ValueError('public archive hash mismatch')
    with tarfile.open(fileobj=io.BytesIO(data), mode='r:gz') as source:
        members = source.getmembers()
        if len(members) > 20001 or len({m.name for m in members}) != len(members):
            raise ValueError('unsafe public archive inventory')
        if sum(m.size for m in members) > MAX_BYTES:
            raise ValueError('excessive public archive size')
        files = {}
        for member in members:
            if (not member.name.startswith('public-agent-starter/') or not member.isfile()
                    or not valid_path(member.name) or member.size > MAX_BYTES):
                raise ValueError('unsafe public archive member')
            name = member.name.removeprefix('public-agent-starter/')
            stream = source.extractfile(member)
            if stream is None:
                raise ValueError('unreadable public archive member')
            files[name] = stream.read()
    try:
        manifest = json.loads(files.pop('manifest.json'))
        if encoded_inventory(files) != (json.dumps(manifest, sort_keys=True, indent=2) + '\n').encode():
            raise ValueError('public archive completeness/hash mismatch')
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError('public archive completeness/hash mismatch') from error
    for name, content in files.items():
        scan(name, content)
    if not destination.is_absolute() or '..' in destination.parts or destination.name in {'', '.', '..'}:
        raise ValueError('invalid public restore destination')
    parent_fd = open_directory(destination.parent)
    stage = '.public-export-stage-' + uuid.uuid4().hex
    staged = False
    try:
        try:
            os.stat(destination.name, dir_fd=parent_fd, follow_symlinks=False)
        except FileNotFoundError:
            pass
        else:
            raise FileExistsError('public restore destination exists')
        rename = ctypes.CDLL(None, use_errno=True).renameat2
        rename.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
        rename.restype = ctypes.c_int
        os.mkdir(stage, mode=0o700, dir_fd=parent_fd)
        staged = True
        stage_fd = os.open(stage, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent_fd)
        try:
            for name, content in files.items():
                fd = os.dup(stage_fd)
                try:
                    for part in name.split('/')[:-1]:
                        try:
                            os.mkdir(part, mode=0o700, dir_fd=fd)
                        except FileExistsError:
                            pass
                        child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
                        os.close(fd)
                        fd = child
                    output = os.open(name.split('/')[-1], os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                                     0o600, dir_fd=fd)
                    with os.fdopen(output, 'wb') as handle:
                        handle.write(content)
                finally:
                    os.close(fd)
        finally:
            os.close(stage_fd)
        if rename(parent_fd, os.fsencode(stage), parent_fd, os.fsencode(destination.name), 1) != 0:
            raise OSError(ctypes.get_errno(), 'public no-replace promotion failed')
        staged = False
    finally:
        if staged:
            shutil.rmtree(stage, dir_fd=parent_fd)
        os.close(parent_fd)
    return destination
