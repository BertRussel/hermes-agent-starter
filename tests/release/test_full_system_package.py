"""Full-system archive safety; factory fixtures never enter recipient payloads."""
import importlib.util
import ast
import asyncio
import io
import json
import logging
from pathlib import Path
import sys
import tarfile
from types import ModuleType, SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]


def implementation():
    path = ROOT / "scripts/full_system_package.py"
    assert path.is_file(), "full-system exact-completeness builder is missing"
    spec = importlib.util.spec_from_file_location("full_system_package", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_archive_is_deterministic_and_restore_requires_exact_manifest(tmp_path):
    package = implementation()
    source = tmp_path / "source"
    source.mkdir()
    (source / "README.md").write_text("Neutral prepared candidate\n", encoding="utf-8")
    first, second = tmp_path / "one.tar.gz", tmp_path / "two.tar.gz"
    package.build_archive(source, first)
    package.build_archive(source, second)
    assert first.read_bytes() == second.read_bytes()
    restored = package.restore_archive(first, tmp_path / "restore")
    assert (restored / "README.md").read_bytes() == (source / "README.md").read_bytes()
    with tarfile.open(first) as original:
        members = [(member, original.extractfile(member).read()) for member in original]
    altered = tmp_path / "extra.tar.gz"
    with tarfile.open(altered, "w:gz") as output:
        for member, data in members:
            output.addfile(member, io.BytesIO(data))
        extra = tarfile.TarInfo("full-system/extra.txt")
        extra.size = 1
        output.addfile(extra, io.BytesIO(b"x"))
    with pytest.raises(ValueError, match="completeness"):
        package.restore_archive(altered, tmp_path / "bad")


def test_restore_rejects_traversal_before_creating_destination(tmp_path):
    package = implementation()
    archive = tmp_path / "unsafe.tar.gz"
    with tarfile.open(archive, "w:gz") as output:
        member = tarfile.TarInfo("full-system/../escape")
        member.size = 1
        output.addfile(member, io.BytesIO(b"x"))
    destination = tmp_path / "restore"
    with pytest.raises(ValueError, match="completeness"):
        package.restore_archive(archive, destination)
    assert not destination.exists()


def test_public_package_has_no_factory_source_selection_or_bindings():
    package = implementation()
    assert not hasattr(package, "SOURCE_BINDINGS")
    assert not hasattr(package, "read_source_objects")
    assert package.scan_bytes("candidate.txt", b"SOURCE_BINDINGS") == ["private_marker"]


def test_restore_rejects_symlinked_destination_ancestor(tmp_path):
    package = implementation()
    source, real = tmp_path / "source", tmp_path / "real"
    source.mkdir()
    real.mkdir()
    (source / "README.md").write_text("Neutral candidate")
    archive = tmp_path / "source.tar.gz"
    package.build_archive(source, archive)
    linked = tmp_path / "linked"
    linked.symlink_to(real, target_is_directory=True)
    with pytest.raises(ValueError, match="unsafe"):
        package.restore_archive(archive, linked / "restore")
    assert not (real / "restore").exists()


def test_archive_scan_requires_hash_bound_protected_instructions():
    package = implementation()
    assert package.scan_bytes("skills/pdf/SKILL.md", b"public skill") == []
    assert package.scan_bytes("profiles/example/SOUL.md", b"public role") == ["forbidden_path"]


def test_package_entrypoint_accepts_only_explicit_bundle_source():
    body = (ROOT / "scripts/full_system_package.py").read_text(encoding="utf-8")
    assert "def accept_full_system(bundle_source" in body
    assert "bundle_source.resolve()" in body
    assert "private_source\": \"not-read\"" in body


def test_byte_scan_catches_identity_paths_and_actual_secret_shapes():
    package = implementation()
    assert package.scan_bytes("README.md", b"Neutral instructions") == []
    assert package.scan_bytes("source.py", b"/home/ubuntu/private")
    assert package.scan_bytes("source.py", b"skepsy-dev")
    assert package.scan_bytes("source.py", b"ghp_" + b"a" * 36)
    assert package.scan_bytes("source.py", b"-----BEGIN " + b"PRIVATE KEY-----")
    assert package.scan_bytes("state.db", b"neutral")


def test_archive_scan_prevents_indirect_protected_file_creation():
    package = implementation()
    for name in ("SOUL.md", "profiles/owner-agent/AGENTS.md", "skills/example/HERMES.md"):
        assert package.scan_bytes(name, b"") == ["forbidden_path"]


def test_privacy_scan_distinguishes_protocol_nick_from_personal_identity():
    package = implementation()
    assert package.scan_bytes("adapter.py", b'nick = member.get("nick"); command = "NICK"') == []
    assert package.scan_bytes("README.md", b"Ask Nick for creative approval") == ["private_identity_or_path"]


def test_disposable_environment_never_inherits_provider_or_profile_state(tmp_path, monkeypatch):
    package = implementation()
    monkeypatch.setenv("OPENAI_API_KEY", "do-not-inherit")
    monkeypatch.setenv("HERMES_HOME", "/private/live")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "do-not-inherit")
    environment = package.isolated_environment(tmp_path)
    assert "OPENAI_API_KEY" not in environment
    assert "AWS_ACCESS_KEY_ID" not in environment
    assert environment["HOME"] == str(tmp_path / "home")
    assert environment["HERMES_HOME"] == str(tmp_path / "home/.hermes")
    assert environment["AWS_EC2_METADATA_DISABLED"] == "true"


def test_canonical_acceptance_uses_full_system_not_historical_git_bundle():
    body = (ROOT / "scripts/acceptance.py").read_text(encoding="utf-8")
    assert "accept_full_system" in body
    assert "scripts/build_handoff.py" not in body


def test_full_system_acceptance_refuses_unattributed_disposable_directory(tmp_path):
    package = implementation()
    destination = tmp_path / "outside"
    destination.mkdir()
    with pytest.raises(ValueError, match="unattributable"):
        package.accept_full_system(ROOT, destination, tmp_path / "fixture")


def test_public_package_receipt_declares_nonperformance_of_external_actions(tmp_path):
    package = implementation()
    receipt = package.accept_full_system(ROOT, tmp_path / "output", tmp_path / "fixture")
    assert receipt["publication"] == "not-performed"
    assert receipt["external_accounts_credentials_production_gateway"] == "not-performed"
    assert receipt["private_source"] == "not-read"


def test_six_role_inventory_is_installable_without_live_exports():
    package = implementation()
    assert set(package.PROFILES) == {"owner-agent", "forge", "bert-verifier", "eve", "recon", "art"}
    for role in package.PROFILES:
        root = ROOT / "profiles" / role
        assert (root / "distribution.yaml").is_file(), role
        assert (root / "SOUL.md").is_file(), role
    assert (ROOT / "docs/full-system/Agent Bible.md").is_file()


def test_profile_resource_selection_does_not_copy_protected_instructions():
    package = implementation()
    resources = package.profile_resources(ROOT)
    for role in package.PROFILES:
        assert resources[f"profiles/{role}/distribution.yaml"] == (ROOT / "profiles" / role / "distribution.yaml").read_bytes()
    assert not any(Path(name).name.upper() in {"SOUL.MD", "AGENTS.MD", "CLAUDE.MD"} for name in resources)
    assert any(name.endswith("/SKILL.md") for name in resources)


def test_instruction_bytes_require_exact_hash_binding():
    package = implementation()
    source = ROOT / "profiles/forge"
    bound = {"SOUL.md": package.digest((source / "SOUL.md").read_bytes())}
    assert package.archive_scan("SOUL.md", (source / "SOUL.md").read_bytes(), bound) == []


def test_package_explicitly_excludes_proprietary_runtime_selection():
    source = (ROOT / "scripts/full_system_package.py").read_text(encoding="utf-8")
    assert "art_studio" not in source and "art_vector" not in source


def test_public_profile_canary_is_limited_to_supported_six_role_distribution_api():
    package = implementation()
    canary = package.native_profile_canary()
    assert "install_distribution" in canary
    assert "owner-agent" in canary and "bert-verifier" in canary
    assert "activated':False" in canary
    assert "passed-distribution-metadata-and-readme" in canary


def test_profile_resource_inventory_rejects_unexpected_distribution_content(tmp_path):
    package = implementation()
    root = tmp_path / "candidate"
    for role in package.PROFILES:
        profile = root / "profiles" / role
        profile.mkdir(parents=True)
        (profile / "distribution.yaml").write_text("name: fictional\n")
        (profile / "README.md").write_text("fictional\n")
    (root / "profiles" / "forge" / "private.txt").write_text("not distributable\n")
    with pytest.raises(ValueError, match="unexpected"):
        package.installable_profile_resources(root)


def test_neutral_export_runs_component_ci_without_factory_home(tmp_path):
    import subprocess
    from scripts.public_export import build_public_export, restore_public_export
    files = ['scripts/create_brain_os.py', 'scripts/public_export.py',
             'profiles/roles.json', 'tests/portable/test_public_components.py',
             '.github/workflows/verify.yml']
    assert (ROOT / files[-1]).is_file(), 'neutral component CI missing'
    manifest = {'schema_version': 1, 'status': 'public-candidate', 'components': [
        {'id': 'component-fixture', 'disposition': 'carry-unchanged',
         'public_rights': 'verified-original', 'license': 'MIT', 'files': files}]}
    archive = tmp_path / 'components.tar.gz'
    checksum = build_public_export(ROOT, manifest, archive)
    clone = restore_public_export(archive, tmp_path / 'clone', expected_sha256=checksum)
    runtime = tmp_path / 'runtime'
    runtime.mkdir()
    for name in ('home', 'tmp'):
        (runtime / name).mkdir()
    result = subprocess.run([sys.executable, '-B', '-m', 'pytest', '-q', '-p',
                             'no:cacheprovider', 'tests/portable'], cwd=clone,
                            env=implementation().isolated_environment(runtime),
                            capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stdout + result.stderr
    assert '4 passed' in result.stdout
    assert not (clone / '.git').exists()
    assert not list(clone.rglob('__pycache__'))


def test_real_http_research_alternative_preserves_bytes_and_refuses_redirects():
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    import threading
    spec = importlib.util.spec_from_file_location(
        'supporting', ROOT / 'runtimes/supporting-runtime/src/supporting_runtime/runtime.py')
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert hasattr(module, 'fetch_public_reference'), 'credential-free research HTTP alternative missing'
    body = b'<html><title>Fictional cited fixture</title><p>Actual retrieved source bytes.</p></html>'

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == '/redirect':
                self.send_response(302)
                self.send_header('Location', '/source')
                self.end_headers()
            else:
                assert self.headers.get('Authorization') is None
                assert self.headers.get('Cookie') is None
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.end_headers()
                self.wfile.write(body)

        def log_message(self, format, *args):
            pass

    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        url = f'http://127.0.0.1:{server.server_port}/source'
        report = module.fetch_public_reference(url, allowed_urls=[url])
        assert report['source'] == url
        assert report['status'] == 'retrieved-not-independently-verified'
        assert report['sha256'] == implementation().digest(body)
        assert report['bytes'] == len(body)
        assert report['title'] == 'Fictional cited fixture'
        with pytest.raises(ValueError, match='allowlist'):
            module.fetch_public_reference(url, allowed_urls=[])
        redirect = url.replace('/source', '/redirect')
        with pytest.raises(ValueError, match='redirect'):
            module.fetch_public_reference(redirect, allowed_urls=[redirect])
        with pytest.raises(ValueError, match='credential'):
            module.fetch_public_reference('https://user:pw@example.com/',
                                          allowed_urls=['https://user:pw@example.com/'])
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_public_runtime_acquisition_refuses_ambient_or_unpinned_sources(tmp_path):
    script = ROOT / 'scripts/public_runtime.py'
    assert script.is_file(), 'public exact-commit acquisition route missing'
    spec = importlib.util.spec_from_file_location('public_runtime', script)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    commit = '2237be355906fbe6065ce1815711eee52b2d646e'
    binding = {'url': 'https://github.com/NousResearch/hermes-agent.git', 'commit': commit}
    assert module.validate_binding(binding) == binding
    for invalid in (dict(binding, commit='main'), dict(binding, commit='0' * 39),
                    dict(binding, url='https://user:pw@github.com/NousResearch/hermes-agent.git'),
                    dict(binding, url='file:///private/source'), dict(binding, token='forbidden')):
        with pytest.raises(ValueError):
            module.acquire_public_runtime(invalid, tmp_path / 'invalid')
        assert not (tmp_path / 'invalid').exists()


def test_browser_documentation_covers_secret_and_owner_handoff_boundaries():
    chapter = (ROOT / 'docs/bible/18-integrations.md').read_text()
    recipient = (ROOT / 'docs/full-system/Agent Bible.md').read_text()
    for text in (chapter, recipient):
        for requirement in ('BWS', 'controlled in-memory', 'existing field state',
                            'browser-stored autofill', 'registered-session recovery',
                            'MFA', 'TOTP', 'passkey', 'app approval',
                            'direct page URL', 'site/account label', 'current step',
                            'blocker', 'expected action', 'expiry', 'post-action verification',
                            'not verified in the recipient environment', 'secret-bearing screenshots'):
            assert requirement in text, requirement
    assert 'Browser selection' in chapter
    assert 'not post-login action authority' in chapter


def test_setup_documents_describe_shared_concurrency_pool_without_quota_authority():
    for name in ('docs/bible/11-native-lifecycle.md', 'docs/bible/03-installation.md',
                 'docs/full-system/Agent Bible.md'):
        text = (ROOT / name).read_text()
        for requirement in ('max_in_progress=6', 'max_in_progress_per_profile=6',
                            'max_spawn=2', 'system-wide', 'six slots', 'dispatcher tick',
                            'no reserved/fixed per-profile quotas', 'not launch authority',
                            'worktree isolation', 'heavy-test serialization',
                            'resource pressure', 'contract/policy limits'):
            assert requirement in text, (name, requirement)


def test_public_history_scan_rejects_deleted_binary_secret_and_old_private_path(tmp_path):
    import subprocess
    from scripts import public_export as export
    assert callable(getattr(export, 'scan_public_history', None)), 'all-history byte scanner missing'
    repository = tmp_path / 'neutral-history'
    repository.mkdir()
    environment = implementation().isolated_environment(tmp_path)
    environment.update({'GIT_CONFIG_NOSYSTEM': '1', 'GIT_CONFIG_GLOBAL': '/dev/null',
                        'GIT_AUTHOR_NAME': 'Fictional fixture', 'GIT_AUTHOR_EMAIL': 'fixture@example.invalid',
                        'GIT_COMMITTER_NAME': 'Fictional fixture', 'GIT_COMMITTER_EMAIL': 'fixture@example.invalid'})

    def git(*args):
        return subprocess.run(['git', '--no-replace-objects', '-C', str(repository), *args],
                              env=environment, check=True, capture_output=True).stdout.decode().strip()

    git('init')
    (repository / 'README.md').write_text('Fictional public source')
    git('add', '--', 'README.md')
    git('commit', '-m', 'fixture clean source')
    first = git('rev-parse', 'HEAD')
    receipt = export.scan_public_history(repository, first)
    assert receipt['commits'] == 1 and receipt['unique_blobs'] == 1
    assert receipt['status'] == 'passed-all-reachable-bytes'
    (repository / 'removed.bin').write_bytes(b'\x00' + b'ghp_' + b'a' * 36)
    git('add', '--', 'removed.bin')
    git('commit', '-m', 'fixture hostile historical bytes')
    (repository / 'removed.bin').unlink()
    git('add', '--', 'removed.bin')
    git('commit', '-m', 'fixture delete does not erase history')
    with pytest.raises(ValueError, match='history privacy') as failure:
        export.scan_public_history(repository, git('rev-parse', 'HEAD'))
    assert 'ghp_' not in str(failure.value)
    with pytest.raises(ValueError, match='exact head'):
        export.scan_public_history(repository, 'main')
    with pytest.raises(ValueError, match='head mismatch'):
        export.scan_public_history(repository, first)


def test_component_inventory_reports_exact_hashes_without_granting_rights(tmp_path):
    from scripts import public_export as export
    assert callable(getattr(export, 'component_inventory', None)), 'component/hash disposition inventory missing'
    (tmp_path / 'README.md').write_bytes(b'Fictional original source')
    manifest = {'schema_version': 1, 'status': 'blocked', 'components': [
        {'id': 'original', 'disposition': 'sanitize', 'public_rights': 'review-required',
         'license': 'unresolved', 'files': ['README.md']}]}
    result = export.component_inventory(tmp_path, manifest)
    assert result['export_authorized'] is False
    assert result['components'][0]['files'][0]['sha256'] == implementation().digest(b'Fictional original source')
    assert result['components'][0]['public_rights'] == 'review-required'
    assert result['components'][0]['gate'] == 'blocked-rights-or-disposition'
    with pytest.raises(ValueError, match='duplicate'):
        export.component_inventory(tmp_path, dict(manifest, components=manifest['components'] * 2))


def test_public_acquisition_never_replaces_a_raced_destination(tmp_path, monkeypatch):
    from scripts import public_runtime as runtime
    from types import SimpleNamespace
    commit = '1' * 40
    destination = tmp_path / 'public-runtime'

    def transport(arguments, **kwargs):
        if arguments[2] == 'init':
            source = Path(arguments[3])
            source.mkdir()
            (source / 'LICENSE').write_text('fictional transport fixture; not upstream rights evidence')
        return SimpleNamespace(returncode=0, stderr='', stdout=commit if arguments[-1] == 'HEAD' else '')

    monkeypatch.setattr(runtime.subprocess, 'run', transport)
    original_exists = Path.exists
    checks = 0

    def raced_exists(path):
        nonlocal checks
        if path == destination:
            checks += 1
            if checks == 2:
                destination.mkdir()  # Appears just after the last pre-promotion check.
                return False
        return original_exists(path)

    monkeypatch.setattr(Path, 'exists', raced_exists)
    with pytest.raises(FileExistsError):
        runtime.acquire_public_runtime({'url': runtime.OFFICIAL_URL, 'commit': commit}, destination)
    assert destination.is_dir() and list(destination.iterdir()) == []


def test_public_runtime_binding_is_official_pinned_and_credential_free():
    from scripts import public_runtime as runtime
    binding = {'url': runtime.OFFICIAL_URL,
               'commit': '2237be355906fbe6065ce1815711eee52b2d646e'}
    assert runtime.validate_binding(binding) == binding
    assert runtime.OFFICIAL_URL == 'https://github.com/NousResearch/hermes-agent.git'


def test_public_acquisition_timeout_is_redacted_and_never_uses_private_fallback(tmp_path, monkeypatch):
    import subprocess
    from scripts import public_runtime as runtime

    def timeout(arguments, **kwargs):
        raise subprocess.TimeoutExpired(arguments, 120, stderr=b'fictional sensitive diagnostic')

    monkeypatch.setattr(runtime.subprocess, 'run', timeout)
    with pytest.raises(RuntimeError, match='public-git-timeout') as error:
        runtime.acquire_public_runtime({'url': runtime.OFFICIAL_URL, 'commit': '1' * 40}, tmp_path / 'source')
    assert 'sensitive' not in str(error.value) and 'private fallback' in str(error.value)
    assert not (tmp_path / 'source').exists()


def test_acceptance_receipt_has_no_worker_or_gateway_side_effects(tmp_path):
    package = implementation()
    receipt = package.accept_full_system(ROOT, tmp_path / 'output', tmp_path / 'fixture')
    assert receipt['delegate_task'] == 0
    assert receipt['async_delegations'] == 0
    assert receipt['external_accounts_credentials_production_gateway'] == 'not-performed'


def test_owner_approved_design_reference_is_exact_discoverable_and_allowlisted(tmp_path):
    import hashlib
    from scripts import public_export as export
    root = Path(__file__).resolve().parents[2]
    relative = 'docs/references/design-and-qa-starter-pack.md'
    content = (root / relative).read_bytes()
    assert hashlib.sha256(content).hexdigest() == 'a7df5f0a447b9919b03f90113b6809db27d063f04bc4363bb091dd375cf092f9'
    text = content.decode('utf-8')
    for coverage in ('## 3. Excel', '## 4. PowerPoint', '## 5. Word', '## 6. HTML email',
                     'web/UI', 'social', 'rendered artifact', 'native editability',
                     'Maker', 'Critic', 'controlled learning', 'stop conditions',
                     'Review licenses and code before installing anything'):
        assert coverage in text
    for document in ('docs/AGENT-BIBLE.md', 'docs/full-system/Agent Bible.md',
                     'docs/bible/16-creative.md', 'profiles/art/README.md'):
        assert 'design-and-qa-starter-pack.md' in (root / document).read_text()
    manifest = json.loads((root / 'release-manifest.json').read_text())
    component = next(entry for entry in manifest['components'] if entry['id'] == 'design-qa-reference')
    assert component['files'] == [relative]
    assert component['disposition'] == 'carry-unchanged'
    assert component['public_rights'] == 'verified-upstream'
    reference_manifest = {'schema_version': 1, 'status': 'public-candidate', 'components': [component]}
    assert export.selected_files(reference_manifest) == [relative]
    assert export.read_member(root, relative) == content
    export.scan(relative, content)
    index = json.loads((root / 'release-index.yaml').read_text())
    references = {item['path']: item['sha256'] for item in index['public_references']}
    assert references[relative] == hashlib.sha256(content).hexdigest()


def test_obsidian_pack_is_exact_linked_and_starter_has_real_control_notes():
    import re
    from scripts import public_export as export
    relative = 'docs/references/obsidian-and-brain-os-starter-pack.md'
    content = (ROOT / relative).read_bytes()
    assert export.sha256(content) == 'c64d458461952da762ebaba27315900cfdf9b5da6075ffc699e7beaafddeae07'
    export.scan(relative, content)
    for path in ('docs/AGENT-BIBLE.md', 'docs/bible/07-knowledge.md', 'brain-os-starter/README.md', 'release-index.yaml'):
        assert 'obsidian-and-brain-os-starter-pack.md' in (ROOT / path).read_text()
    for path in ('00-MOC/Agent Profiles MOC.md', '02-Development/Decision-Journal/Decision Journal Index.md',
                 '05-Reference/Procedures/Storage Operations Hub.md', '05-Reference/Procedures/Filing and Maintenance.md',
                 '06-Inbox/README.md'):
        assert (ROOT / 'brain-os-starter' / path).is_file()
    manifest = json.loads((ROOT / 'release-manifest.json').read_text())
    component = next(item for item in manifest['components'] if item['id'] == 'knowledge-organization-reference')
    assert component['files'] == [relative] and component['disposition'] == 'carry-unchanged'
    index = json.loads((ROOT / 'release-index.yaml').read_text())
    references = {item['path']: item['sha256'] for item in index['public_references']}
    assert references[relative] == export.sha256(content)
    for note in (ROOT / 'brain-os-starter').rglob('*.md'):
        assert re.search(rb'\b(?:Grant|Bo|Joy|Erik|Nick|Bert)\b|Par 4|/home/ubuntu/', note.read_bytes()) is None
    index = json.loads((ROOT / 'release-index.yaml').read_text())
    assert set(index['generic_native_profiles']['paths']) == {'profiles/' + role for role in implementation().PROFILES}
    assert references[relative] == export.sha256(content)
