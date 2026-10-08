"""A public export is exact allowlisted source, never private Git history."""
import importlib.util
import io
import json
from pathlib import Path
import tarfile

import pytest

ROOT = Path(__file__).resolve().parents[2]


def exporter():
    path = ROOT / 'scripts/public_export.py'
    assert path.is_file(), 'deterministic privacy-clean public export tool missing'
    spec = importlib.util.spec_from_file_location('public_export', path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def source_archive_verifier():
    path = ROOT / 'scripts/verify_source_archive_parity.py'
    spec = importlib.util.spec_from_file_location('verify_source_archive_parity', path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_exact_allowlisted_export_is_reproducible_and_history_free(tmp_path):
    module = exporter()
    source = tmp_path / 'source'
    source.mkdir()
    (source / 'README.md').write_text('Original fictional public fixture\n')
    (source / '.git').mkdir()
    (source / '.git/private-history').write_text('must not travel')
    manifest = {'schema_version': 1, 'status': 'public-candidate',
                'components': [{'id': 'original-fixture', 'disposition': 'carry-unchanged',
                                'public_rights': 'verified-original', 'license': 'MIT',
                                'files': ['README.md']}]}
    first = module.build_public_export(source, manifest, tmp_path / 'first.tar.gz')
    second = module.build_public_export(source, manifest, tmp_path / 'second.tar.gz')
    assert first == second
    restored = module.restore_public_export(tmp_path / 'first.tar.gz', tmp_path / 'restored', expected_sha256=first)
    assert (restored / 'README.md').read_bytes() == (source / 'README.md').read_bytes()
    assert not (restored / '.git').exists()


def test_opaque_nested_archives_cannot_hide_private_source(tmp_path):
    import pytest
    module = exporter()
    source = tmp_path / 'source'
    source.mkdir()
    (source / 'hidden.tar.gz').write_bytes(b'opaque compressed history')
    manifest = {'schema_version': 1, 'status': 'public-candidate',
                'components': [{'id': 'fixture', 'disposition': 'carry-unchanged',
                                'public_rights': 'verified-original', 'license': 'MIT',
                                'files': ['hidden.tar.gz']}]}
    with pytest.raises(ValueError, match='allowlist'):
        module.build_public_export(source, manifest, tmp_path / 'bad.tar.gz')
    assert not (tmp_path / 'bad.tar.gz').exists()


def fixture_manifest(name='README.md'):
    return {'schema_version': 1, 'status': 'public-candidate',
            'components': [{'id': 'original-fixture', 'disposition': 'carry-unchanged',
                            'public_rights': 'verified-original', 'license': 'MIT', 'files': [name]}]}


def test_unresolved_manifest_refuses_export_before_source_reads(tmp_path, monkeypatch):
    module = exporter()
    calls = []
    monkeypatch.setattr(module, 'read_member', lambda *args: calls.append(args))
    manifest = fixture_manifest()
    manifest['status'] = 'rights-pending'
    with pytest.raises(ValueError, match='disposition incomplete'):
        module.build_public_export(ROOT, manifest, tmp_path / 'bad.tar.gz')
    assert calls == []
    assert not (tmp_path / 'bad.tar.gz').exists()


def test_accepted_actual_release_manifest_exports(tmp_path):
    module = exporter()
    manifest = json.loads((ROOT / 'release-manifest.json').read_text())
    archive = tmp_path / 'public-starter.tar.gz'
    digest = module.build_public_export(ROOT, manifest, archive)
    assert digest == module.sha256(archive.read_bytes())
    with tarfile.open(archive) as exported:
        assert {member.name for member in exported} >= {
            'public-agent-starter/manifest.json',
            'public-agent-starter/brain-os-starter/README.md',
            'public-agent-starter/profiles/roles.json',
        }


def test_archive_parity_tool_and_inventory_are_browsable_public_source():
    """The committed public tree documents and verifies its own archive boundary."""
    assert (ROOT / 'scripts' / 'verify_source_archive_parity.py').is_file()
    assert (ROOT / 'docs' / 'SOURCE-INVENTORY.md').is_file()
    assert (ROOT / 'source-inventory.json').is_file()
    readme = (ROOT / 'README.md').read_text(encoding='utf-8')
    assert 'docs/SOURCE-INVENTORY.md' in readme


def test_source_inventory_rejects_omitted_and_extra_members():
    module = source_archive_verifier()
    exact = {
        'schema_version': 1,
        'purpose': 'exact-public-source-tree',
        'files': ['README.md', 'source-inventory.json'],
    }
    module.validate_source_inventory(exact, exact['files'])
    with pytest.raises(ValueError, match='source inventory mismatch'):
        module.validate_source_inventory(exact, exact['files'] + ['extra.md'])
    with pytest.raises(ValueError, match='source inventory mismatch'):
        module.validate_source_inventory(
            {**exact, 'files': exact['files'] + ['not-in-tree.md']}, exact['files']
        )


def test_source_inventory_rejects_duplicates_and_private_paths():
    module = source_archive_verifier()
    with pytest.raises(ValueError, match='duplicate source inventory path'):
        module.validate_source_inventory(
            {'schema_version': 1, 'purpose': 'exact-public-source-tree',
             'files': ['source-inventory.json', 'source-inventory.json']},
            ['source-inventory.json'],
        )
    with pytest.raises(ValueError, match='private path in source inventory'):
        module.validate_source_inventory(
            {'schema_version': 1, 'purpose': 'exact-public-source-tree',
             'files': ['source-inventory.json', 'docs/internal/controller-only/secret.json']},
            ['source-inventory.json', 'docs/internal/controller-only/secret.json'],
        )


@pytest.mark.parametrize('name', ['.git/history', 'docs/internal/controller-only/proposal.txt',
                                  '../escape', '/absolute/file', 'auth.json', 'state.db',
                                  '.full-system-proof/receipt.json'])
def test_forbidden_explicit_source_paths_are_rejected(name, tmp_path):
    with pytest.raises(ValueError, match='allowlist'):
        exporter().build_public_export(tmp_path, fixture_manifest(name), tmp_path / 'bad.tar.gz')
    assert not (tmp_path / 'bad.tar.gz').exists()


def test_source_symlink_and_private_bytes_never_reach_archive(tmp_path):
    module = exporter()
    source = tmp_path / 'source'
    source.mkdir()
    external = tmp_path / 'external.md'
    external.write_text('unapproved linked source')
    (source / 'README.md').symlink_to(external)
    with pytest.raises(OSError):
        module.build_public_export(source, fixture_manifest(), tmp_path / 'bad.tar.gz')
    (source / 'README.md').unlink()
    (source / 'README.md').write_bytes(b'ghp_' + b'a' * 36)
    with pytest.raises(ValueError, match='privacy rejection'):
        module.build_public_export(source, fixture_manifest(), tmp_path / 'bad.tar.gz')
    assert not (tmp_path / 'bad.tar.gz').exists()


@pytest.mark.parametrize('attack', ['extra', 'tamper', 'traversal', 'symlink'])
def test_restore_rejects_modified_inventory_before_destination_creation(tmp_path, attack):
    module = exporter()
    source = tmp_path / 'source'
    source.mkdir()
    (source / 'README.md').write_text('Neutral original fixture')
    original = tmp_path / 'original.tar.gz'
    module.build_public_export(source, fixture_manifest(), original)
    with tarfile.open(original) as archive:
        members = [(member, archive.extractfile(member).read()) for member in archive]
    altered = tmp_path / 'altered.tar.gz'
    with tarfile.open(altered, 'w:gz') as archive:
        for member, content in members:
            if attack == 'tamper' and member.name.endswith('/README.md'):
                content = b'changed'
                member.size = len(content)
            archive.addfile(member, io.BytesIO(content))
        if attack != 'tamper':
            name = {'extra': 'public-agent-starter/extra.txt', 'traversal': 'public-agent-starter/../escape',
                    'symlink': 'public-agent-starter/linked'}[attack]
            member = tarfile.TarInfo(name)
            if attack == 'symlink':
                member.type, member.linkname = tarfile.SYMTYPE, 'README.md'
                archive.addfile(member)
            else:
                member.size = 1
                archive.addfile(member, io.BytesIO(b'x'))
    destination = tmp_path / 'restore'
    with pytest.raises(ValueError):
        module.restore_public_export(altered, destination, expected_sha256=module.sha256(altered.read_bytes()))
    assert not destination.exists()


def test_restore_hash_and_existing_destination_are_independent_gates(tmp_path):
    module = exporter()
    source = tmp_path / 'source'
    source.mkdir()
    (source / 'README.md').write_text('Neutral original fixture')
    archive = tmp_path / 'source.tar.gz'
    digest = module.build_public_export(source, fixture_manifest(), archive)
    destination = tmp_path / 'restore'
    with pytest.raises(ValueError, match='archive hash'):
        module.restore_public_export(archive, destination, expected_sha256='0' * 64)
    assert not destination.exists()
    destination.mkdir()
    (destination / 'owner.txt').write_text('private owner data')
    with pytest.raises(FileExistsError):
        module.restore_public_export(archive, destination, expected_sha256=digest)
    assert (destination / 'owner.txt').read_text() == 'private owner data'
