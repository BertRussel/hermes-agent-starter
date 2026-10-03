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
    with pytest.raises(ValueError, match="unsafe"):
        package.restore_archive(archive, destination)
    assert not destination.exists()


def test_source_rules_exclude_tests_private_fixtures_and_history():
    package = implementation()
    assert package.selected("studio", "src/art_studio/controller.py")
    assert package.selected("vector", "src/art_vector/cli.py")
    for path in ("tests/test_cli.py", "src/art_vector/private_fixture.py", ".git/config", "docs/history.md"):
        assert not package.selected("vector", path)
    assert package.selected("hermes", "tools/kanban.py")
    assert not package.selected("hermes", "tests/tools/test_kanban.py")
    assert not package.selected("hermes", "SOUL.md")


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


def test_source_selection_keeps_runtime_catalogs_but_excludes_protected_instructions():
    package = implementation()
    assert package.selected("hermes", "skills/pdf/SKILL.md")
    assert package.selected("hermes", "optional-mcps/catalog/server.json")
    assert not package.selected("hermes", "plugins/example/SOUL.md")
    assert not package.selected("hermes", "skills/example/AGENTS.md")


def test_exact_object_reader_rejects_unbound_source_before_running_git(monkeypatch):
    package = implementation()
    calls = []
    monkeypatch.setattr("subprocess.run", lambda *args, **kwargs: calls.append(args))
    with pytest.raises(ValueError, match="source binding"):
        package.read_source_objects("hermes", Path("/unapproved"), "0" * 40)
    assert calls == []


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


def test_full_system_acceptance_rejects_output_escape_before_source_reads(tmp_path, monkeypatch):
    package = implementation()
    calls = []
    monkeypatch.setattr(package, "read_source_objects", lambda *args: calls.append(args))
    destination = tmp_path / "outside"
    with pytest.raises(ValueError, match="proof boundary"):
        package.accept_full_system(Path(package.SOURCE_BINDINGS["hermes"][0]), destination, tmp_path / "fixture")
    assert calls == []
    assert not destination.exists()


@pytest.mark.parametrize("recipient_adapted", [False, True], ids=["actual-baseline-stalls", "recipient-fix-resolves"])
def test_actual_discord_callback_resolves_backend_before_stalled_message_edit(monkeypatch, recipient_adapted):
    package = implementation()
    repository, commit = package.SOURCE_BINDINGS["hermes"]
    source_objects = package.read_source_objects("hermes", Path(repository), commit)
    source = source_objects["plugins/platforms/discord/adapter.py"]
    if recipient_adapted:
        source, _ = package.adapt_source("hermes", "plugins/platforms/discord/adapter.py", source)
    tree = ast.parse(source)
    classes = {node.name: node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)}
    selected = ast.Module(body=[ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0),
                                classes["_HermesView"], classes["ClarifyChoiceView"]], type_ignores=[])

    class View:
        def __init__(self, **kwargs):
            self.children = []

        def add_item(self, child):
            self.children.append(child)

    discord = SimpleNamespace(ui=SimpleNamespace(View=View, Button=lambda **kwargs: SimpleNamespace(**kwargs)),
                              ButtonStyle=SimpleNamespace(primary=1, secondary=2),
                              Color=SimpleNamespace(green=lambda: 1))
    namespace = {"discord": discord, "_read_discord_prompt_timeout": lambda: 900,
                 "_component_check_auth": lambda interaction, users, roles: str(interaction.user.id) in users,
                 "logger": logging.getLogger("clarify-factory")}
    exec(compile(ast.fix_missing_locations(selected), "recipient-discord-views", "exec"), namespace)
    # Actual production queue, not a parallel test model; no live auth or transport.
    queue = ModuleType("tools.clarify_gateway")
    monkeypatch.setitem(sys.modules, queue.__name__, queue)
    exec(compile(source_objects["tools/clarify_gateway.py"], "production-clarify-queue", "exec"), queue.__dict__)
    tools = ModuleType("tools")
    setattr(tools, "clarify_gateway", queue)
    monkeypatch.setitem(sys.modules, "tools", tools)

    async def exercise():
        canonical = "Keep the existing owner identity and all customizations"
        entry = queue.register("causal-factory", "isolated-session", "Choose", [canonical])
        entered, release = asyncio.Event(), asyncio.Event()

        async def edit(**kwargs):
            entered.set()
            await release.wait()

        view = namespace["ClarifyChoiceView"](["short display label"], entry.clarify_id, {"42"})
        interaction = SimpleNamespace(user=SimpleNamespace(id="42", display_name="Recipient"), message=None,
                                      response=SimpleNamespace(edit_message=edit))
        task = asyncio.create_task(view._resolve_choice(interaction, 0, "short display label"))
        try:
            await asyncio.wait_for(entered.wait(), 1)
            assert not task.done(), "test did not causally hold the Discord edit"
            assert entry.event.is_set() == recipient_adapted, "causal baseline/fix distinction was lost"
            if recipient_adapted:
                assert entry.response == canonical
                assert not queue.resolve_gateway_clarify(entry.clarify_id, "duplicate")
        finally:
            release.set()
            await task
            queue.clear_session("isolated-session")

    asyncio.run(exercise())


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


def test_instruction_sources_are_never_transformed_by_recipient_adapter():
    package = implementation()
    original = b'retain Nick as the only creative approver'
    for component in ('studio', 'vector'):
        adapted, transformations = package.adapt_source(
            component, 'skills/art-logo-vector-production/SKILL.md', original)
        assert adapted == original
        assert transformations == []


def test_proprietary_runtime_selection_excludes_instruction_skills():
    package = implementation()
    for component in ('studio', 'vector'):
        assert not package.selected(component, 'skills/art-logo-vector-production/SKILL.md')
        assert package.selected(component, 'pyproject.toml')


def test_native_home_canary_proves_supported_schema_migration_and_full_restore(tmp_path):
    import subprocess
    script = ROOT / 'scripts/native_operations_canary.py'
    assert script.is_file(), 'native home migration/backup/restore entrypoint missing'
    package = implementation()
    runtime = tmp_path / 'runtime'
    runtime.mkdir()
    for name in ('home', 'tmp'):
        (runtime / name).mkdir()
    extracted = tmp_path / 'extracted-hermes'
    repository, commit = package.SOURCE_BINDINGS['hermes']
    for name, data in package.read_source_objects('hermes', Path(repository), commit).items():
        target = extracted / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    environment = package.isolated_environment(runtime)
    environment['PYTHONPATH'] = str(extracted)
    result = subprocess.run([sys.executable, '-B', str(script),
                             str(ROOT / 'profiles/forge/SOUL.md')],
                            cwd=runtime, env=environment,
                            capture_output=True, text=True, timeout=90)
    assert result.returncode == 0, result.stdout + result.stderr
    receipt = json.loads(result.stdout.splitlines()[-1])
    assert receipt['schema_migration']['status'] == 'passed'
    assert receipt['schema_migration']['from'] < receipt['schema_migration']['to']
    assert receipt['schema_migration']['deprecated_key_removed'] is True
    assert receipt['full_home_restore'] == 'passed'
    assert receipt['rollback'] == 'passed-pre-migration-backup'
    assert receipt['identity_memory_vault_preserved'] is True
    assert receipt['malformed_config_refused'] is True
    assert receipt['unsupported_schema_refused'] is True
    assert receipt['gateway_lifecycle'] == 'not-invoked'
    assert receipt['external_vault_recovery']['status'] == 'passed-native-member-restore'
    assert receipt['external_vault_recovery']['members'] == 3
    assert receipt['external_vault_recovery']['traversal_refused'] is True
    assert receipt['external_vault_recovery']['symlink_refused'] is True
    assert receipt['external_vault_recovery']['exact_byte_parity'] is True


def test_native_pipeline_entrypoint_exercises_real_fences_without_launch(tmp_path):
    import subprocess
    script = ROOT / 'scripts/native_pipeline_canary.py'
    assert script.is_file(), 'native primitive pipeline entrypoint missing'
    package = implementation()
    extracted = tmp_path / 'hermes'
    repository, commit = package.SOURCE_BINDINGS['hermes']
    for name, data in package.read_source_objects('hermes', Path(repository), commit).items():
        target = extracted / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    runtime = tmp_path / 'runtime'
    runtime.mkdir()
    for name in ('home', 'tmp'):
        (runtime / name).mkdir()
    environment = package.isolated_environment(runtime)
    environment['PYTHONPATH'] = str(extracted)
    result = subprocess.run([sys.executable, '-B', str(script)], cwd=runtime,
                            env=environment, capture_output=True, text=True, timeout=90)
    assert result.returncode == 0, result.stdout + result.stderr
    receipt = json.loads(result.stdout.splitlines()[-1])
    assert receipt['native_dependencies'] == 'passed'
    assert receipt['notification_readback'] == 'passed-exact-notify+wake'
    assert receipt['unadmitted_release_refused'] is True
    assert receipt['review_dependency_fence'] is True
    assert receipt['dependency_resume'] == 'passed'
    assert receipt['named_worker_launches'] == 0
    assert receipt['governed_end_to_end'] == 'root-owned-pending'


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
    commit = implementation().SOURCE_BINDINGS['hermes'][1]
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


def test_canonical_inventory_binds_every_selected_byte_and_preserves_rights_gates():
    package = implementation()
    assert callable(getattr(package, 'export_disposition_inventory', None)), 'canonical disposition inventory missing'
    source = {name: {'file.txt': b'Fictional selected bytes'} for name in
              ('hermes', 'studio', 'vector', 'timing', 'evidence', 'supporting',
               'profile-distributions', 'knowledge', 'generic-foundation')}
    receipt = package.export_disposition_inventory(source)
    assert receipt['public_export_authorized'] is False
    assert receipt['selected_files'] == 9
    assert set(receipt['components']) == set(source)
    for name in source:
        assert receipt['components'][name]['files'][0]['sha256'] == package.digest(b'Fictional selected bytes')
        assert receipt['components'][name]['public_gate'] != 'passed'
    assert receipt['components']['studio']['public_rights'] == 'private-transfer-not-public-redistribution'
    assert 'geometric' in receipt['components']['supporting']['capability_limits']


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


def test_disposable_timing_runs_real_start_pause_resume_and_failure_closeout(tmp_path):
    package = implementation()
    assert callable(getattr(package, 'timing_primitive_canary', None)), 'executable timing primitive canary missing'
    source = tmp_path / 'timing'
    repository, commit = package.SOURCE_BINDINGS['timing']
    for name, original in package.read_source_objects('timing', Path(repository), commit).items():
        data, _ = package.adapt_source('timing', name, original)
        target = source / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    result = package.timing_primitive_canary(source)
    assert result['status'] == 'passed-native-timing-primitives'
    assert result['premature_success_refused'] is True
    assert result['pause_resume'] == 'passed'
    assert result['terminal'] == 'failed-fixture-not-acceptance'
    assert result['named_worker_launches'] == 0
    assert len(result['journal_sha256']) == 64


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
    package = implementation()
    assert package.PUBLIC_REFERENCE_FILES[relative] == hashlib.sha256(content).hexdigest()


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
    assert implementation().PUBLIC_REFERENCE_FILES[relative] == export.sha256(content)
    for note in (ROOT / 'brain-os-starter').rglob('*.md'):
        assert re.search(rb'\b(?:Grant|Bo|Joy|Erik|Nick|Bert)\b|Par 4|/home/ubuntu/', note.read_bytes()) is None
    index = json.loads((ROOT / 'release-index.yaml').read_text())
    assert set(index['generic_native_profiles']['paths']) == {'profiles/' + role for role in implementation().PROFILES}
    references = {item['path']: item['sha256'] for item in index['public_references']}
    assert references == implementation().PUBLIC_REFERENCE_FILES
