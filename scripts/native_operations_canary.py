#!/usr/bin/env python3
"""Exercise native recovery/migration primitives in a NEW scrubbed test home.

Never use this on an installed owner home. Import uses native member primitives,
not run_import: that CLI can revive a Gateway and is outside this test's scope.
External-vault selection is explicit and confined to this disposable HOME.
This is primitive integration evidence, not an owner backup or live CLI import.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import sqlite3
import sys
from types import SimpleNamespace
import zipfile


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def exercise(soul: Path) -> dict:
    root = Path.cwd().resolve()
    home = root / 'home'
    hermes = home / '.hermes'
    if (Path(os.environ.get('HOME', '')).resolve() != home
            or Path(os.environ.get('HERMES_HOME', '')).resolve() != hermes
            or hermes.exists() or hermes.is_symlink()
            or home.is_symlink() or not home.is_dir()
            or any(key in os.environ for key in ('HERMES_KANBAN_TASK', 'HERMES_PROFILE',
                                                  'OPENAI_API_KEY', 'ANTHROPIC_API_KEY'))):
        raise ValueError('new isolated disposable home required')
    if soul.is_symlink() or not soul.is_file() or soul.name != 'SOUL.md':
        raise ValueError('unchanged source Soul required')
    hermes.mkdir(mode=0o700)
    from hermes_cli import backup, config
    import yaml

    baseline = {'_config_version': 32,
                'model': {'default': 'fictional-owner-model'},
                'delegation': {'max_async_children': 5, 'max_concurrent_children': 3},
                'local': {'identity_label': 'Fictional garden assistant'}}
    config_path = hermes / 'config.yaml'
    config_path.write_text(yaml.safe_dump(baseline))
    config_path.chmod(0o600)
    # Authorized byte-identical instruction copy. No substitutions or authoring.
    (hermes / 'SOUL.md').write_bytes(soul.read_bytes())
    assert digest(hermes / 'SOUL.md') == digest(soul)
    data = {'memories/stable.txt': b'Fictional confirmed garden fact',
            'local/vault/Home.md': b'Fictional private knowledge hub',
            'local/vault/Research.md': b'Fictional cited research note',
            'local/preferences.json': b'{"presentation":"short"}'}
    for name, content in data.items():
        path = hermes / name
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        path.write_bytes(content)
        path.chmod(0o600)
    database = hermes / 'fixture.db'
    with sqlite3.connect(database) as connection:
        connection.execute('CREATE TABLE facts (value TEXT)')
        connection.execute('INSERT INTO facts VALUES (?)', ('fictional persistent fact',))
    preserved = {name: digest(hermes / name) for name in data}
    preserved['SOUL.md'] = digest(hermes / 'SOUL.md')
    old_config = config_path.read_bytes()
    archive = root / 'native-home-backup.zip'
    backup.run_backup(SimpleNamespace(output=str(archive)))
    assert archive.is_file()
    with zipfile.ZipFile(archive) as source:
        assert set(preserved) | {'config.yaml', 'fixture.db'} <= set(source.namelist())
        assert not any(name.endswith(('.db-wal', '.db-shm')) for name in source.namelist())

    results = config.migrate_config(interactive=False, quiet=True)
    migrated = yaml.safe_load(config_path.read_text())
    assert migrated['_config_version'] > 32
    assert 'max_async_children' not in migrated['delegation']
    assert migrated['delegation']['max_concurrent_children'] == 5
    assert migrated['model'] == baseline['model']
    assert migrated['local'] == baseline['local']
    assert all(digest(hermes / name) == value for name, value in preserved.items())

    def restore(target: Path) -> None:
        target.mkdir(mode=0o700)
        with zipfile.ZipFile(archive) as source:
            members = source.namelist()
            restored, external, errors, skipped, shrunk = backup._import_members(
                source, members, '', target, len(members))
        assert not errors and not external and not skipped and not shrunk
        assert restored == len(members)
        assert all(digest(target / name) == value for name, value in preserved.items())
        assert (target / 'config.yaml').read_bytes() == old_config
        with sqlite3.connect(target / 'fixture.db') as connection:
            assert connection.execute('PRAGMA integrity_check').fetchone() == ('ok',)
            assert connection.execute('SELECT value FROM facts').fetchall() == [('fictional persistent fact',)]

    restore(root / 'restored-home')
    restore(root / 'rollback-home')
    # An explicit external vault, including its settings and binary attachment.
    # Native full-home discovery does NOT automatically include arbitrary vaults.
    external = home / 'fictional-vault'
    external.mkdir(mode=0o700)
    external_data = {'Home.md': b'Fictional external knowledge hub',
                     '.obsidian/app.json': b'{"fictional":true}',
                     'assets/example.bin': b'\x00fictional attachment\xff'}
    for name, content in external_data.items():
        path = external / name
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        path.write_bytes(content)
    external_hashes = {name: digest(external / name) for name in external_data}
    external_archive = root / 'external-vault-backup.zip'
    failures = []
    entries = [(external / name, Path('_external/fictional-vault') / name)
               for name in sorted(external_data)]
    with zipfile.ZipFile(external_archive, 'x', zipfile.ZIP_DEFLATED) as output:
        backup._write_zip_entries(output, entries, external_archive,
                                  on_db_failure=lambda name: failures.append(str(name)),
                                  on_error=lambda name, error: failures.append(str(name)),
                                  on_progress=lambda count: None, track_bytes=True)
    assert not failures
    for name in external_data:
        (external / name).write_bytes(b'fictional interrupted update')
    with zipfile.ZipFile(external_archive) as source:
        assert set(source.namelist()) == {str(entry[1]) for entry in entries}
        for name, value in external_hashes.items():
            assert hashlib.sha256(source.read('_external/fictional-vault/' + name)).hexdigest() == value
        restored, restored_external, errors, skipped, shrunk = backup._import_members(
            source, source.namelist(), '', hermes, len(entries))
    assert restored == restored_external == len(entries)
    assert not errors and not skipped and not shrunk
    assert all(digest(external / name) == value for name, value in external_hashes.items())
    # Actual native path-traversal and symlink refusal: no publication outside HOME.
    hostile = root / 'hostile-external.zip'
    with zipfile.ZipFile(hostile, 'x') as output:
        output.writestr('_external/../escape.txt', b'fictional hostile input')
        output.writestr('_external/blocked-link/overwrite.txt', b'fictional hostile input')
    outside = root / 'outside-vault'
    outside.mkdir()
    (home / 'blocked-link').symlink_to(outside, target_is_directory=True)
    with zipfile.ZipFile(hostile) as source:
        restored, restored_external, errors, skipped, shrunk = backup._import_members(
            source, source.namelist(), '', hermes, 2)
    assert restored == restored_external == 0 and len(errors) == 2
    assert not (root / 'escape.txt').exists() and not list(outside.iterdir())
    assert all(digest(hermes / name) == value for name, value in preserved.items())
    external_receipt = {'status': 'passed-native-member-restore', 'members': len(entries),
                        'exact_byte_parity': True, 'preserved_sha256': external_hashes,
                        'backup_sha256': digest(external_archive),
                        'traversal_refused': True, 'symlink_refused': True,
                        'selection': 'explicit disposable vault only; not automatic native full-home discovery'}
    # Actual native unsupported-schema and malformed YAML failure routes.
    config_path.write_text('_config_version: 1\nmodel:\n  default: fictional-owner-model\n')
    below_floor = config_path.read_bytes()
    refused = config.migrate_config(interactive=False, quiet=True)
    assert refused['warnings'] and config_path.read_bytes() == below_floor
    config_path.write_text('model: [\n')
    malformed = config_path.read_bytes()
    try:
        config.migrate_config(interactive=False, quiet=True)
    except Exception as error:
        assert 'config' in str(error).lower() or 'yaml' in str(error).lower()
    else:
        raise AssertionError('malformed YAML migration accepted')
    assert config_path.read_bytes() == malformed
    config_path.write_bytes(old_config)
    return {'schema_migration': {'status': 'passed', 'from': 32,
                                'to': migrated['_config_version'],
                                'deprecated_key_removed': True, 'changes': results['config_added']},
            'full_home_restore': 'passed', 'rollback': 'passed-pre-migration-backup',
            'identity_memory_vault_preserved': True, 'preserved_sha256': preserved,
            'backup_sha256': digest(archive), 'malformed_config_refused': True,
            'external_vault_recovery': external_receipt,
            'unsupported_schema_refused': True, 'gateway_lifecycle': 'not-invoked',
            'scope': 'native full-home and explicit external-vault member recovery; supported config schema migration',
            'not_exercised': ['runtime binary version upgrade', 'live credentials', 'owner customization approval', 'off-host recovery']}


if __name__ == '__main__':
    print(json.dumps(exercise(Path(sys.argv[1])), sort_keys=True))
