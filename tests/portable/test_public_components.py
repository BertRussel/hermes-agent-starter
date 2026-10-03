"""Credential-free component checks suitable for a neutral public clone.

These tests do not certify the governed runtime, identity, or full product.
"""
import hashlib
import json
from pathlib import Path

import pytest

from scripts.create_brain_os import create_brain_os
from scripts.public_export import build_public_export, restore_public_export, scan

ROOT = Path(__file__).resolve().parents[2]


def manifest():
    return {'schema_version': 1, 'status': 'public-candidate', 'components': [
        {'id': 'fictional-original', 'disposition': 'carry-unchanged',
         'public_rights': 'verified-original', 'license': 'MIT', 'files': ['README.md']}]}


def test_exact_component_archive_roundtrip_and_determinism(tmp_path):
    source = tmp_path / 'source'
    source.mkdir()
    (source / 'README.md').write_text('Fictional source fixture')
    first, second = tmp_path / 'first.tar.gz', tmp_path / 'second.tar.gz'
    checksum = build_public_export(source, manifest(), first)
    assert checksum == build_public_export(source, manifest(), second)
    restored = restore_public_export(first, tmp_path / 'restored', expected_sha256=checksum)
    assert (restored / 'README.md').read_bytes() == (source / 'README.md').read_bytes()
    with pytest.raises(ValueError, match='archive hash'):
        restore_public_export(first, tmp_path / 'bad', expected_sha256='0' * 64)
    assert not (tmp_path / 'bad').exists()


def test_byte_privacy_gate_checks_binary_content_without_decoding():
    scan('image.bin', b'\x00neutral\xff')
    with pytest.raises(ValueError, match='privacy'):
        scan('image.bin', b'\x00' + b'ghp_' + b'a' * 36)
    with pytest.raises(ValueError, match='privacy'):
        scan('.git/history', b'neutral')


def test_create_once_vault_preserves_existing_destination(tmp_path):
    source = tmp_path / 'notes'
    source.mkdir()
    (source / 'Home.md').write_text('Fictional local knowledge hub')
    target = tmp_path / 'vault'
    create_brain_os(source, target)
    before = hashlib.sha256((target / 'Home.md').read_bytes()).hexdigest()
    with pytest.raises(FileExistsError):
        create_brain_os(source, target)
    assert hashlib.sha256((target / 'Home.md').read_bytes()).hexdigest() == before


def test_role_mapping_is_neutral_and_one_to_one():
    mapping = json.loads((ROOT / 'profiles/roles.json').read_text())['native_assignees']
    assert set(mapping) == {'owner-agent', 'implementer', 'verifier', 'reviewer', 'researcher', 'designer'}
    assert len(mapping.values()) == len(set(mapping.values()))
    assert mapping['implementer'] == 'forge'
    assert mapping['verifier'] == 'bert-verifier'
    assert mapping['reviewer'] == 'eve'
