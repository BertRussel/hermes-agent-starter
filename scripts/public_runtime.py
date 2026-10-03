#!/usr/bin/env python3
"""Acquire an explicitly approved official public revision in disposable state.

No installation, dispatch, credential use or implicit local source fallback.
A binding is input, not a claim that its commit is publicly available/licensed.
"""
from __future__ import annotations

import json
import ctypes
import errno
import os
from pathlib import Path
import re
import subprocess
import tempfile
import sys

try:
    from scripts.create_brain_os import open_directory
except ModuleNotFoundError as error:
    if error.name != 'scripts':
        raise
    from create_brain_os import open_directory

OFFICIAL_URL = 'https://github.com/NousResearch/hermes-agent.git'


def validate_binding(binding: dict) -> dict:
    if (not isinstance(binding, dict) or set(binding) != {'url', 'commit'}
            or binding['url'] != OFFICIAL_URL
            or not isinstance(binding['commit'], str)
            or re.fullmatch('[0-9a-f]{40}', binding['commit']) is None):
        raise ValueError('exact official public credential-free binding required')
    return dict(binding)


def acquire_public_runtime(binding: dict, destination: Path) -> dict:
    binding = validate_binding(binding)
    destination = Path(destination).absolute()
    if destination.exists() or destination.is_symlink():
        raise FileExistsError('runtime destination exists')
    if not destination.parent.is_dir() or destination.parent.is_symlink():
        raise ValueError('existing ordinary destination parent required')
    with tempfile.TemporaryDirectory(prefix='public-runtime-', dir=destination.parent) as scratch:
        home = Path(scratch) / 'home'
        home.mkdir()
        env = {'PATH': '/usr/bin:/bin', 'HOME': str(home), 'LANG': 'C.UTF-8',
               'GIT_CONFIG_NOSYSTEM': '1', 'GIT_CONFIG_GLOBAL': '/dev/null',
               'GIT_TERMINAL_PROMPT': '0', 'GIT_ASKPASS': '/bin/false'}
        stage = Path(scratch) / 'source'

        def git(*args):
            try:
                result = subprocess.run(['git', '--no-replace-objects', *args], env=env,
                                        capture_output=True, text=True, timeout=120)
            except subprocess.TimeoutExpired:
                raise RuntimeError('official public revision acquisition failed: public-git-timeout; no private fallback') from None
            if result.returncode:
                # Record a bounded diagnosis, never ambient credentials or raw
                # stderr. This command's remote and commit are fixed validated data.
                reason = ('revision-not-publicly-available'
                          if any(marker in result.stderr.lower() for marker in
                                 ('not our ref', 'unadvertised object', "couldn't find remote ref"))
                          else 'public-git-route-failed')
                raise RuntimeError(f'official public revision acquisition failed: {reason}; no private fallback')
            return result.stdout.strip()

        git('init', str(stage))
        git('-C', str(stage), 'remote', 'add', 'origin', binding['url'])
        git('-C', str(stage), '-c', 'credential.helper=', 'fetch', '--depth=1',
            'origin', binding['commit'])
        git('-C', str(stage), 'checkout', '--detach', binding['commit'])
        head = git('-C', str(stage), 'rev-parse', 'HEAD')
        if head != binding['commit'] or git('-C', str(stage), 'status', '--porcelain'):
            raise ValueError('public revision identity/cleanliness mismatch')
        if not (stage / 'LICENSE').is_file():
            raise ValueError('upstream license missing; public rights unresolved')
        # No installation follows from a successful acquisition. Extension and
        # license compatibility remain independently reviewed gates.
        if destination.exists() or destination.is_symlink():
            raise FileExistsError('runtime destination appeared')
        if sys.platform != 'linux':
            raise RuntimeError('public acquisition requires Linux no-replace promotion')
        rename = ctypes.CDLL(None, use_errno=True).renameat2
        rename.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
        rename.restype = ctypes.c_int
        source_fd = open_directory(stage.parent)
        try:
            parent_fd = open_directory(destination.parent)
            try:
                if rename(source_fd, os.fsencode(stage.name), parent_fd,
                          os.fsencode(destination.name), 1) != 0:
                    code = ctypes.get_errno()
                    if code in {errno.EEXIST, errno.ENOTEMPTY}:
                        raise FileExistsError('runtime destination appeared during acquisition')
                    raise OSError(code, 'public no-replace promotion failed')
                os.fsync(parent_fd)
            finally:
                os.close(parent_fd)
        finally:
            os.close(source_fd)
    return {'source': binding['url'], 'commit': head, 'destination': str(destination),
            'installed': False, 'rights': 'upstream-license-present-not-reviewed',
            'extension_compatibility': 'not-certified'}


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--commit', required=True)
    parser.add_argument('--destination', required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(acquire_public_runtime({'url': OFFICIAL_URL, 'commit': args.commit},
                                           args.destination), sort_keys=True))
