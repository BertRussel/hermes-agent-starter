"""Full-system packaging primitives used ONLY by canonical acceptance.

Factory configuration, negative fixtures and private receipts are not payload.
All extraction is from the enumerated exact objects, never working trees/history.
"""
from __future__ import annotations

import gzip
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import sys
import platform
import tarfile
import tempfile
import time

SOURCE_BINDINGS = {
    "hermes": ("/home/ubuntu/.hermes/hermes-agent", "3671350025428cde04d9c8852a38e97420c56917"),
    "studio": ("/home/ubuntu/art-studio-tools-trustedfs-reset-v1", "80c1f07e57eeba7e8a19f019f003d5fc0671746b"),
    "vector": ("/home/ubuntu/art-studio-tools-vector-v1", "67b725032c0271fa975c97f31891bd8d3ed308f3"),
    "timing": ("/home/ubuntu/BertBrainBackup", "cd3a6609b67253bbdbf21e4e347de2435302d264"),
}
TIMING_FILES = (
    "hermes/scripts/forge_timing_adapter.py",
    "hermes/scripts/forge_timing_telemetry.py",
    "hermes/scripts/forge_timing_report.py",
)


def read_source_objects(component: str, repository: Path, commit: str) -> dict[str, bytes]:
    """Read only positively selected blobs at an immutable authorized binding."""
    if SOURCE_BINDINGS.get(component) != (str(repository), commit):
        raise ValueError("source binding mismatch")
    environment = {"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8", "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": "/dev/null"}

    def query(*arguments: str) -> bytes:
        return subprocess.run(
            ["git", "-C", str(repository), "--no-replace-objects", *arguments],
            env=environment, stdin=subprocess.DEVNULL, capture_output=True,
            check=True, timeout=60,
        ).stdout

    if component == "timing":
        names = TIMING_FILES
    else:
        names = tuple(name for name in query("ls-tree", "-r", "--name-only", commit).decode().splitlines() if selected(component, name))
    if not names:
        raise ValueError("empty selected source")
    return {name: query("show", f"{commit}:{name}") for name in names}

PROFILES = ("owner-agent", "forge", "bert-verifier", "eve", "recon", "art")
HERMES_PREFIXES = ("agent/", "tools/", "hermes_cli/", "gateway/", "cron/", "acp_adapter/", "providers/", "plugins/", "tui_gateway/", "skills/", "optional-mcps/", "locales/", "assets/", "prompts/", "vendor/")
HERMES_FILES = {"pyproject.toml", "uv.lock", "setup.py", "LICENSE", "README.md", ".python-version"}
PROTECTED_NAMES = {"SOUL.MD", "AGENTS.MD", "HERMES.MD", "CLAUDE.MD", ".CURSORRULES"}
FORBIDDEN_PARTS = {".git", ".env", "auth.json", "sessions", "memories", "cache", "logs", "node_modules", "tests", "__pycache__"}
CREDENTIAL_PATTERN = re.compile(rb"(?:ghp_[A-Za-z0-9]{36,}|github_pat_[A-Za-z0-9_]{40,}|sk-[A-Za-z0-9_-]{32,}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----)")
# Lowercase `nick` and uppercase IRC `NICK` are protocol identifiers, not a
# person's name. Keep owner-name spelling distinct without exempting files.
IDENTITY = re.compile(rb"(?:/home/ubuntu(?:/|\b)|/srv/brainos-files|skepsy-dev|BertBrainOS|BertBrainBackup|(?-i:\bNick\b)|\bKommu\b|\bt_[0-9a-f]{8}\b)", re.I)


def adapt_source(component: str, name: str, data: bytes) -> tuple[bytes, list[str]]:
    """Reviewed recipient-only changes; never modify an installed source tree."""
    if PurePosixPath(name).name.upper() in PROTECTED_NAMES | {"SKILL.MD"}:
        return data, []  # Instruction behavior is never authored by an adapter.
    transformations = []
    replacements = {
        ("hermes", "gateway/config.py"): [(b"t_0f76430f/t_70483f23", b"historical incident records")],
        ("studio", "README.md"): [
            (b"/home/ubuntu/BertBrainOS/02-Development/Projects/Brain OS/Art Specialist Profile/Forge Corrected Completion Contract - ART-VECTOR-001 G3 - 2026-07-18.md", b"docs/full-system/Procedures.md#creative-quality"),
            (b"Bert/Nick review", b"controller/owner review")],
        ("vector", "README.md"): [
            (b"/home/ubuntu/BertBrainOS/02-Development/Projects/Brain OS/Art Specialist Profile/Forge Corrected Completion Contract - ART-VECTOR-001 G3 - 2026-07-18.md", b"docs/full-system/Procedures.md#creative-quality")],

        ("studio", "src/art_studio/artifacts.py"): [(b"external Nick-approval receipt", b"external owner-approval receipt")],
        ("studio", "src/art_studio/cli.py"): [(b'Path("/home/ubuntu/ArtWorkbench/runs")', b'Path.home() / "ArtWorkbench" / "runs"')],
        ("vector", "src/art_vector/hermes_tool.py"): [(b'"BertBrainOS"', b'"owner-vault"')],
        ("timing", "hermes/scripts/forge_timing_adapter.py"): [(b'Path("/home/ubuntu/.hermes/state/forge-supervision/timing-runs")', b'(Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes"))) / "state/forge-supervision/timing-runs")')],
        ("timing", "hermes/scripts/forge_timing_telemetry.py"): [
            (b'Path("/home/ubuntu/worktrees/bertbrainbackup-forge-timing-telemetry")', b'Path.cwd()'),
            (b'Path("/home/ubuntu/.hermes/state/forge-checkpoints")', b'Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes"))) / "state/forge-checkpoints"'),
            (b'Path("/home/ubuntu/.hermes/state/forge-supervision")', b'Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes"))) / "state/forge-supervision"'),
            (b'    Path("/home/ubuntu/BertBrainOS/02-Development/Projects/Brain OS"),\n', b''),
            (b'parsed.path.startswith("/skepsy-dev/BertBrainBackup/")', b'False  # remote artifact access requires a separately reviewed recipient binding')],
    }
    for before, after in replacements.get((component, name), []):
        if data.count(before) != 1:
            raise ValueError(f"recipient adaptation source drift: {component}/{name}")
        data = data.replace(before, after, 1)
        transformations.append("replace exact operational owner/path binding; retain source notices and authorization gates")
    if component == "hermes" and name == "plugins/platforms/discord/adapter.py":
        finish = b'            await self._finish(interaction, discord.Color.green(), f"Answered by {display_name}: {choice}", log_edit_failure=True)\n'
        anchor = b'                logger.error("Discord clarify resolve_gateway_clarify failed (id=%s): %s", self.clarify_id, exc)\n'
        if data.count(finish) != 1 or data.count(anchor) != 1:
            raise ValueError("clarify adaptation source drift")
        data = data.replace(finish, b"            self.resolved = True\n            self._disable_all()\n", 1)
        data = data.replace(anchor, anchor + finish, 1)
        transformations.append("resolve canonical backend choice before awaiting Discord message edit; reserve single-use view first")
    return data, transformations


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def safe_name(name: str) -> bool:
    parts = PurePosixPath(name).parts
    return bool(parts) and not name.startswith("/") and "\\" not in name and all(part not in {".", "..", ""} for part in name.split("/"))


def selected(component: str, name: str) -> bool:
    if not safe_name(name) or set(PurePosixPath(name).parts) & FORBIDDEN_PARTS:
        return False
    if "private_fixture" in name or PurePosixPath(name).name.upper() in PROTECTED_NAMES:
        return False
    if component == "hermes":
        return name in HERMES_FILES or ("/" not in name and name.endswith(".py")) or (name.startswith(HERMES_PREFIXES) and name.endswith((".py", ".json", ".yaml", ".yml", ".md", ".txt", ".toml", ".js", ".sh", ".css", ".html")) and "/systemd/" not in name)
    if component in {"studio", "vector"}:
        prefix = "src/art_studio/" if component == "studio" else "src/art_vector/"
        # Private source runtime canaries do not require upstream instruction
        # skills. Never rewrite those skills to satisfy a privacy scan.
        return name in {"pyproject.toml", "README.md"} or name.startswith(prefix) or (name.startswith(("schemas/", "config/", "plugins/")) and name.endswith((".py", ".json", ".yaml", ".md")))
    return False


def scan_bytes(name: str, data: bytes) -> list[str]:
    failures = []
    parts = PurePosixPath(name).parts
    if not safe_name(name) or set(parts) & FORBIDDEN_PARTS or PurePosixPath(name).name.upper() in PROTECTED_NAMES or name.endswith((".db", ".sqlite", ".log", ".pyc", ".bundle")):
        failures.append("forbidden_path")
    if CREDENTIAL_PATTERN.search(data):
        failures.append("secret_shape")
    if IDENTITY.search(data):
        failures.append("private_identity_or_path")
    return failures


def isolated_environment(root: Path) -> dict[str, str]:
    home = root / "home"
    return {"HOME": str(home), "HERMES_HOME": str(home / ".hermes"), "PATH": "/usr/local/bin:/usr/bin:/bin:/snap/bin", "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8", "PYTHONDONTWRITEBYTECODE": "1", "PYTHONNOUSERSITE": "1", "AWS_EC2_METADATA_DISABLED": "true", "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": "/dev/null", "UV_CACHE_DIR": str(root / "uv-cache"), "TMPDIR": str(root / "tmp")}


def profile_resources(root: Path) -> dict[str, bytes]:
    """Ordinary source profile metadata/skills, explicitly NOT installable yet."""
    resources = {}
    for role in PROFILES:
        profile = root / "profiles" / role
        for path in sorted(profile.rglob("*")):
            relative = path.relative_to(profile).as_posix()
            if path.name.upper() in PROTECTED_NAMES:
                continue
            if relative != "distribution.yaml" and not (relative.startswith("skills/") and relative.endswith("/SKILL.md")):
                continue
            if not stat.S_ISREG(path.lstat().st_mode):
                raise ValueError("unsafe profile resource")
            resources[f"profiles/{role}/{relative}"] = path.read_bytes()
    return resources


def installable_profile_resources(root: Path) -> dict[str, bytes]:
    """Read exact candidate distribution bytes for authorized disposable installs.

    No rendering, substitution or transformation is permitted on instructions.
    This inventory is separate from generic source selection, whose default
    scan continues to refuse instruction files from unknown upstream trees.
    """
    resources = {}
    for role in PROFILES:
        profile = root / "profiles" / role
        if profile.is_symlink() or not profile.is_dir():
            raise ValueError("unsafe profile root")
        for name, data in file_bytes(profile).items():
            if name not in {"README.md", "SOUL.md", "config.yaml", "distribution.yaml"} and not name.startswith("skills/"):
                raise ValueError("unexpected distribution member")
            issues = scan_bytes(name, data)
            if name == "SOUL.md":
                issues = [issue for issue in issues if issue != "forbidden_path"]
            if issues:
                raise ValueError("unsafe distribution bytes")
            resources[f"profiles/{role}/{name}"] = data
    return resources


def file_bytes(root: Path) -> dict[str, bytes]:
    files = {}
    for path in sorted(root.rglob("*")):
        mode = path.lstat().st_mode
        name = path.relative_to(root).as_posix()
        if stat.S_ISDIR(mode):
            continue
        if not stat.S_ISREG(mode) or not safe_name(name):
            raise ValueError("unsafe source member")
        files[name] = path.read_bytes()
    return files


def encode_manifest(files: dict[str, bytes]) -> bytes:
    return (json.dumps({"schema_version": 2, "files": [{"path": name, "size": len(data), "sha256": digest(data)} for name, data in sorted(files.items())]}, sort_keys=True, indent=2) + "\n").encode()


def archive_scan(name: str, data: bytes, instruction_hashes: dict[str, str]) -> list[str]:
    issues = scan_bytes(name, data)
    if name in instruction_hashes:
        if digest(data) != instruction_hashes[name]:
            raise ValueError("instruction hash mismatch")
        # Only the exact declared instruction file is exempted, not forbidden
        # directories, state files, secret shapes or personal identifiers.
        if (safe_name(name) and PurePosixPath(name).name.upper() in PROTECTED_NAMES
                and not set(PurePosixPath(name).parts) & FORBIDDEN_PARTS):
            issues = [issue for issue in issues if issue != "forbidden_path"]
    return issues


def build_archive(source: Path, archive: Path, *, instruction_hashes: dict[str, str] | None = None) -> str:
    files = file_bytes(source)
    instruction_hashes = instruction_hashes or {}
    if not set(instruction_hashes) <= set(files):
        raise ValueError("instruction hash inventory mismatch")
    if "manifest.json" in files:
        raise ValueError("manifest is builder-owned")
    for name, data in files.items():
        if archive_scan(name, data, instruction_hashes):
            raise ValueError(f"payload scan rejected: {name}")
    files["manifest.json"] = encode_manifest(files)
    with archive.open("xb") as raw:
        with gzip.GzipFile(fileobj=raw, mode="wb", filename="", mtime=0) as compressed:
            with tarfile.open(fileobj=compressed, mode="w|") as output:
                for name, data in sorted(files.items()):
                    member = tarfile.TarInfo("full-system/" + name)
                    member.size, member.mode, member.mtime = len(data), 0o600, 0
                    member.uid = member.gid = 0
                    member.uname = member.gname = ""
                    output.addfile(member, io.BytesIO(data))
    return digest(archive.read_bytes())


def restore_archive(archive: Path, destination: Path, *, instruction_hashes: dict[str, str] | None = None) -> Path:
    # Validate everything before writing anything. Fixed limits bound decompression.
    absolute = destination.absolute()
    if any(path.is_symlink() for path in (absolute, *absolute.parents)):
        raise ValueError("unsafe symlinked restore destination")
    if destination.exists():
        raise ValueError("restore destination must be absent")
    with tarfile.open(archive, "r:gz") as source:
        members = source.getmembers()
        names = [member.name for member in members]
        if len(names) > 20000 or len(names) != len(set(names)):
            raise ValueError("unsafe duplicate or excessive members")
        if any(not safe_name(member.name) or not member.name.startswith("full-system/") or not member.isfile() or member.size > 32 * 1024 * 1024 for member in members):
            raise ValueError("unsafe archive member")
        if sum(member.size for member in members) > 256 * 1024 * 1024:
            raise ValueError("unsafe archive size")
        files = {}
        for member in members:
            stream = source.extractfile(member)
            if stream is None:
                raise ValueError("unsafe unreadable member")
            files[member.name.removeprefix("full-system/")] = stream.read()
    try:
        manifest = json.loads(files.pop("manifest.json"))
        instruction_hashes = instruction_hashes or {}
        if not set(instruction_hashes) <= set(files):
            raise ValueError("instruction hash inventory mismatch")
        entries = manifest["files"]
        expected = {entry["path"] for entry in entries}
        if manifest["schema_version"] != 2 or len(expected) != len(entries) or expected != set(files):
            raise ValueError("archive completeness mismatch")
        for entry in entries:
            data = files[entry["path"]]
            if entry["size"] != len(data) or entry["sha256"] != digest(data) or archive_scan(entry["path"], data, instruction_hashes):
                raise ValueError("archive completeness/hash/scan mismatch")
    except (KeyError, TypeError, json.JSONDecodeError) as error:
        raise ValueError("archive completeness manifest invalid") from error
    destination.mkdir(mode=0o700, parents=True)
    for name, data in files.items():
        target = destination / name
        target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        with target.open("xb") as output:
            output.write(data)
        target.chmod(0o600)
    (destination / "manifest.json").write_bytes(encode_manifest(files))
    return destination


def native_profile_canary() -> str:
    """Executed with restored Hermes, in a scrubbed disposable test home only.

    Exercise real native distribution install/update/export/import. No model,
    activation, alias creation, Gateway or protected behavior editing occurs.
    """
    return '''
from pathlib import Path
import hashlib, json, os, sys, shutil, yaml
from hermes_cli.profile_distribution import install_distribution, update_distribution, DistributionError
from hermes_cli.profiles import export_profile, import_profile

source = Path(sys.argv[1]).resolve()
home = Path(os.environ['HOME']).resolve()
assert Path(os.environ['HERMES_HOME']).resolve() == home / '.hermes'
assert not any(key in os.environ for key in ('OPENAI_API_KEY', 'ANTHROPIC_API_KEY', 'HERMES_KANBAN_TASK'))
roles = ('owner-agent', 'forge', 'bert-verifier', 'eve', 'recon', 'art')
hash_file = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
installed = []
vault = home / 'fictional-vault'
vault.mkdir()
(vault / 'Home.md').write_text('Fictional garden knowledge; native tasks remain authoritative')
vault_hash = hash_file(vault / 'Home.md')
for role in roles:
    profile_source = source / role
    original = {p.relative_to(profile_source).as_posix(): hash_file(p)
                for p in profile_source.rglob('*') if p.is_file() and p.name not in ('manifest.json', 'distribution.yaml')}
    plan = install_distribution(str(profile_source), name=role, create_alias=False)
    target = plan.target_dir.resolve()
    assert target == home / '.hermes' / 'profiles' / role, target
    assert all(hash_file(target / name) == value for name, value in original.items())
    try:
        install_distribution(str(profile_source), name=role, create_alias=False)
    except DistributionError:
        pass
    else:
        raise AssertionError('existing profile overwritten')
    # Fictional private data, never credentials; SOUL stays byte-identical.
    (target / 'local').mkdir(exist_ok=True)
    (target / 'local' / 'preference.txt').write_text('fictional preference: short summaries')
    (target / 'memories' / 'stable-fact.txt').write_text('fictional confirmed fact: garden project')
    private = ('local/preference.txt', 'memories/stable-fact.txt', 'config.yaml', 'SOUL.md')
    preserved = {name: hash_file(target / name) for name in private}
    backup = Path.cwd() / (role + '-private-backup.tar.gz')
    export_profile(role, str(backup))
    update_distribution(role)
    assert all(hash_file(target / name) == value for name, value in preserved.items())
    restored = import_profile(str(backup), name=role + '-restore')
    assert all(hash_file(restored / name) == value for name, value in preserved.items())
    # Native source update with a real distinct metadata/content version. Never
    # transform protected instructions; the entire SOUL remains exact source.
    baseline_readme = (target / 'README.md').read_bytes()
    metadata = yaml.safe_load((profile_source / 'distribution.yaml').read_text())
    baseline_version = metadata['version']
    metadata['version'] = '0.2.0-canary'
    upgraded = Path.cwd() / (role + '-upgrade-source')
    shutil.copytree(profile_source, upgraded)
    assert hash_file(upgraded / 'SOUL.md') == hash_file(profile_source / 'SOUL.md')
    (upgraded / 'distribution.yaml').write_text(yaml.safe_dump(metadata))
    (upgraded / 'README.md').write_bytes(baseline_readme + b'\x5cnDisposable version upgrade canary\x5cn')
    installed_metadata = yaml.safe_load((target / 'distribution.yaml').read_text())
    installed_metadata['source'] = str(upgraded)
    (target / 'distribution.yaml').write_text(yaml.safe_dump(installed_metadata))
    update_distribution(role)
    assert yaml.safe_load((target / 'distribution.yaml').read_text())['version'] == '0.2.0-canary'
    assert (target / 'README.md').read_bytes() != baseline_readme
    assert all(hash_file(target / name) == value for name, value in preserved.items())
    # Roll back through the real installed distribution updater using the old
    # source, and independently restore the pre-update native backup.
    installed_metadata = yaml.safe_load((target / 'distribution.yaml').read_text())
    installed_metadata['source'] = str(profile_source)
    (target / 'distribution.yaml').write_text(yaml.safe_dump(installed_metadata))
    update_distribution(role)
    assert yaml.safe_load((target / 'distribution.yaml').read_text())['version'] == baseline_version
    assert (target / 'README.md').read_bytes() == baseline_readme
    assert all(hash_file(target / name) == value for name, value in preserved.items())
    rollback = import_profile(str(backup), name=role + '-rollback')
    assert all(hash_file(rollback / name) == value for name, value in preserved.items())
    assert yaml.safe_load((rollback / 'distribution.yaml').read_text())['version'] == baseline_version
    assert hash_file(vault / 'Home.md') == vault_hash
    installed.append(role)
assert not (home / '.hermes' / 'active_profile').exists()
assert not (home / '.local' / 'bin').exists()
print(json.dumps({'installed': installed, 'exact_source_hashes': True,
                  'private_state_preserved': True, 'activated': False,
                  'version_update_rollback': 'passed-distribution-metadata-and-readme',
                  'vault_preserved': True,
                  'update_scope': 'same-version refresh and distinct metadata/README version upgrade and downgrade; no runtime/schema migration',
                  'restore_scope': 'native profile export/import; no credentials or version migration'}))
'''


def instruction_proposal_bindings(root: Path) -> dict:
    """Declare that controller-only instruction proposals are not shipped."""
    roles = {f"profiles/{role}/SOUL.md": digest((root / "profiles" / role / "SOUL.md").read_bytes())
             for role in PROFILES}
    return {"status": "not-shipped-public-system", "targets": [],
            "role_current_sha256": roles, "role_targets": []}


PUBLIC_REFERENCE_FILES = {
    'docs/references/design-and-qa-starter-pack.md':
        'a7df5f0a447b9919b03f90113b6809db27d063f04bc4363bb091dd375cf092f9',
    'docs/references/obsidian-and-brain-os-starter-pack.md':
        'c64d458461952da762ebaba27315900cfdf9b5da6075ffc699e7beaafddeae07',
}


def timing_primitive_canary(source: Path) -> dict:
    """Exercise actual observer CLI in disposable state, never a governed launch."""
    adapter = source / 'hermes/scripts/forge_timing_adapter.py'
    if not adapter.is_file() or adapter.is_symlink():
        raise ValueError('extracted timing adapter required')
    # The supported adapter explicitly allows only its /tmp-prefixed test root.
    with tempfile.TemporaryDirectory(prefix='forge-timing-telemetry-', dir='/tmp') as temporary:
        root = Path(temporary)
        environment = isolated_environment(root)
        for name in ('home', 'tmp', 'worktree'):
            (root / name).mkdir(mode=0o700)
        environment.update({'GIT_CONFIG_NOSYSTEM': '1', 'GIT_CONFIG_GLOBAL': '/dev/null',
                            'GIT_AUTHOR_NAME': 'Fictional timing fixture',
                            'GIT_AUTHOR_EMAIL': 'fixture@example.invalid',
                            'GIT_COMMITTER_NAME': 'Fictional timing fixture',
                            'GIT_COMMITTER_EMAIL': 'fixture@example.invalid'})
        worktree = root / 'worktree'
        (worktree / 'README.md').write_text('Fictional immutable timing fixture\n')

        def run(arguments: list[str]) -> subprocess.CompletedProcess:
            return subprocess.run(arguments, cwd=worktree, env=environment,
                                  stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=60)

        for arguments in (['init', '-b', 'fixture'], ['add', '--', 'README.md'],
                          ['commit', '-m', 'fixture source']):
            result = run(['git', '--no-replace-objects', *arguments])
            if result.returncode:
                raise ValueError('disposable timing Git prerequisite failed')
        prefix = [sys.executable, '-B', str(adapter), '--state-root', str(root)]
        commands = []
        last_second = 0

        def timing(*arguments: str, expected: int = 0) -> dict:
            nonlocal last_second
            # This source's observer clock truncates to seconds. Wait on that
            # exact prerequisite instead of inventing timestamps or retrying a
            # rejected mutation. Reports need no new timestamp boundary.
            if arguments[0] != 'report':
                while int(time.time()) <= last_second:
                    time.sleep(max(0.01, last_second + 1 - time.time()))
                last_second = int(time.time())
            result = run(prefix + list(arguments))
            if arguments[0] != 'report':
                last_second = int(time.time())
            commands.append({'operation': arguments[0], 'exit_code': result.returncode})
            if result.returncode != expected:
                raise ValueError('disposable timing primitive failed: ' + arguments[0] + ': ' + result.stderr.strip())
            return json.loads(result.stdout) if result.returncode == 0 else {}

        timing('start-run', '--run-id', 'fictional-canary', '--project-id', 'fictional-project',
               '--repo', 'fictional/repository', '--branch', 'fixture', '--worktree', str(worktree),
               '--task-class', 'feature', '--complexity', 'medium', '--unfamiliar-code', 'false',
               '--external-system', 'false', '--test-surface', 'full', '--review-surface', 'independent',
               '--dependency-count', '0', '--human-gate-count', '0',
               '--estimate-p50-seconds', '120', '--estimate-p80-seconds', '240',
               '--phase-id', 'fixture-implementation', '--phase-type', 'implementation', '--phase-origin', 'planned')
        timing('report', '--run-id', 'fictional-canary')
        timing('pause', '--run-id', 'fictional-canary', '--kind', 'blocked', '--reason-code', 'fixture_dependency')
        timing('resume', '--run-id', 'fictional-canary')
        timing('transition-phase', '--run-id', 'fictional-canary', '--phase-id', 'fixture-smoke',
               '--phase-type', 'smoke_test', '--phase-origin', 'planned',
               '--outcome', 'success', '--evidence-type', 'commit')
        # Never synthesize Verifier/Reviewer PASS to make a successful timing run.
        timing('finish-run', '--run-id', 'fictional-canary', '--outcome', 'success', expected=3)
        timing('abort-run', '--run-id', 'fictional-canary', '--outcome', 'failed', '--reason-code', 'fixture_failure')
        report = timing('report', '--run-id', 'fictional-canary')
        journal = (root / 'fictional-canary/events.jsonl').read_bytes()
        return {'status': 'passed-native-timing-primitives', 'pause_resume': 'passed',
                'premature_success_refused': True, 'terminal': 'failed-fixture-not-acceptance',
                'journal_sha256': digest(journal), 'report': report, 'commands': commands,
                'named_worker_launches': 0, 'scope': 'disposable observer CLI only; live root timing/reviews remain pending'}


def export_disposition_inventory(sources: dict[str, dict[str, bytes]]) -> dict:
    """Exact private evidence inventory; possession never invents public rights."""
    rights = {
        'hermes': ('MIT-upstream-notice', 'public-compatible-revision-acquisition-pending',
                   'native compatible extensions require separate public binding'),
        'studio': ('Proprietary', 'private-transfer-not-public-redistribution',
                   'private factory canary only; no public replacement equivalence'),
        'vector': ('Proprietary', 'private-transfer-not-public-redistribution',
                   'private Inkscape QA only; public source rights unresolved'),
        'timing': ('unresolved', 'source-rights-verification-required',
                   'source adapter is not installed governed timing acceptance'),
        'evidence': ('unresolved', 'controller-snapshot-rights-verification-required',
                     'snapshot has no verified upstream public source/license'),
        'supporting': ('original-source-review-required', 'original-source-review-required',
                       'geometric SVG/PNG only, local documents/media and bounded public text; not a full design suite or authenticated browser'),
        'profile-distributions': ('original-source-review-required', 'original-source-review-required',
                                 'unchanged Souls; final operational instruction review deferred'),
        'knowledge': ('original-source-review-required', 'recipient-only-content-needs-public-sanitization',
                      'recipient-specific guide is not a generic public export'),
        'generic-foundation': ('original-source-review-required', 'original-source-review-required',
                              'final Soul/seed and clean-public-onboarding review deferred'),
    }
    if set(sources) != set(rights):
        raise ValueError('incomplete/unknown canonical component inventory')
    records = {}
    for component, files in sorted(sources.items()):
        license_label, public_rights, limits = rights[component]
        records[component] = {
            'license': license_label, 'public_rights': public_rights,
            'public_gate': 'blocked', 'capability_limits': limits,
            'files': [{'path': name, 'bytes': len(data), 'sha256': digest(data)}
                      for name, data in sorted(files.items())]}
    return {'schema_version': 1, 'public_export_authorized': False,
            'selected_files': sum(len(files) for files in sources.values()),
            'components': records, 'scope': 'exact selected factory bytes; not full public history or legal clearance'}


def accept_full_system(bundle_source: Path, output_dir: Path, fixture_root: Path) -> dict:
    """Canonical factory gate. Failed or unexercised gates never become acceptance."""
    root = Path(__file__).resolve().parents[1]
    if (output_dir.absolute() != root / ".full-system-proof"
            or fixture_root.absolute() != root / ".full-system-fixture"
            or output_dir.is_symlink() or fixture_root.is_symlink()):
        raise ValueError("proof boundary mismatch")
    if str(bundle_source) != SOURCE_BINDINGS["hermes"][0]:
        raise ValueError("source binding mismatch")
    output_dir = output_dir.absolute()
    fixture_root = fixture_root.absolute()
    # Never remove a previous directory on the strength of a pathname alone.
    ownership = {"builder": "canonical-full-system-v1", "root": str(root)}
    for directory in (output_dir, fixture_root):
        if directory.exists():
            marker = directory / "factory-owner.json"
            if not marker.is_file() or marker.is_symlink() or json.loads(marker.read_bytes()) != ownership:
                raise ValueError("unattributable previous proof output")
        else:
            directory.mkdir(mode=0o700)
            (directory / "factory-owner.json").write_text(json.dumps(ownership, sort_keys=True) + "\n")
    # Append-only attempts retain failed gate evidence, without broad cleanup.
    attempt = next(index for index in range(1, 10000) if not (output_dir / f"attempt-{index:04d}").exists())
    proof = output_dir / f"attempt-{attempt:04d}"
    proof.mkdir(mode=0o700)
    proposal_binding = instruction_proposal_bindings(root)
    (proof / "instruction-proposal-bindings.json").write_text(json.dumps(proposal_binding, sort_keys=True, indent=2) + "\n")
    failures = []
    sources = {}
    ledger = []
    for component, (repository, commit) in SOURCE_BINDINGS.items():
        original = read_source_objects(component, Path(repository), commit)
        sources[component] = {}
        for name, data in original.items():
            adapted, transformations = adapt_source(component, name, data)
            sources[component][name] = adapted
            issues = scan_bytes(name, adapted)
            if issues:
                failures.append({"component": component, "path": name, "codes": issues})
            ledger.append({"component": component, "commit": commit, "path": name,
                           "original_sha256": digest(data), "adapted_sha256": digest(adapted), "transformations": transformations})
    snapshot = Path("/home/ubuntu/.hermes/artifacts/grant-full-handoff-20261001/controller-source/brainos-kanban-git-evidence.py").read_bytes()
    if digest(snapshot) != "fd22017fec89e96279eb6ccbff37891d03adb3372830ace8de4363f578a4bb33":
        raise ValueError("stateless evidence snapshot hash mismatch")
    sources["evidence"] = {"brainos-kanban-git-evidence.py": snapshot}
    sources["supporting"] = file_bytes(root / "runtimes/supporting-runtime")
    sources["profile-distributions"] = installable_profile_resources(root)
    instruction_hashes = {name: digest(data) for name, data in sources["profile-distributions"].items()
                          if PurePosixPath(name).name.upper() in PROTECTED_NAMES}
    sources["knowledge"] = {"docs/full-system/" + name: data for name, data in file_bytes(root / "docs/full-system").items()}
    sources["knowledge"]["THIRD_PARTY_NOTICES.md"] = (root / "THIRD_PARTY_NOTICES.md").read_bytes()
    sources["generic-foundation"] = {}
    for directory in ("templates", "examples", "brain-os-starter", "docs/bible"):
        for name, data in file_bytes(root / directory).items():
            sources["generic-foundation"][directory + "/" + name] = data
    for name in ("README.md", "CONTRIBUTING.md", "compatibility.json", "release-index.yaml", "release-manifest.json", "profiles/roles.json",
                 "scripts/validate_customization.py", "scripts/create_brain_os.py", "scripts/public_export.py", "scripts/public_runtime.py", "scripts/native_operations_canary.py", "scripts/native_pipeline_canary.py",
                 "docs/AGENT-BIBLE.md", "docs/START-HERE.md", "docs/CAPABILITY-STATUS.md", "docs/WORKED-WORKFLOWS.md", "docs/COMMAND-MATRIX.md"):
        sources["generic-foundation"][name] = (root / name).read_bytes()
    for name, expected_hash in PUBLIC_REFERENCE_FILES.items():
        data = (root / name).read_bytes()
        if digest(data) != expected_hash:
            raise ValueError('unchanged public reference hash mismatch')
        sources['generic-foundation'][name] = data
    for component in ("supporting", "profile-distributions", "knowledge", "generic-foundation"):
        for name, data in sources[component].items():
            issues = archive_scan(name, data, instruction_hashes if component == "profile-distributions" else {})
            if issues:
                failures.append({"component": component, "path": name, "codes": issues})
            ledger.append({"component": component, "provenance": "admitted candidate source; exact Git binding required at frozen handoff",
                           "path": name, "original_sha256": digest(data), "adapted_sha256": digest(data), "transformations": []})
    for name, data in sources["evidence"].items():
        if scan_bytes(name, data):
            failures.append({"component": "evidence", "path": name, "codes": scan_bytes(name, data)})
        ledger.append({"component": "evidence", "provenance": "controller-supplied installed-source snapshot; upstream Git unknown",
                       "path": name, "original_sha256": digest(data), "adapted_sha256": digest(data), "transformations": []})
    (proof / "source-ledger.json").write_text(json.dumps(ledger, sort_keys=True, indent=2) + "\n")
    export_inventory = export_disposition_inventory(sources)
    (proof / 'component-export-inventory.json').write_text(json.dumps(export_inventory, sort_keys=True, indent=2) + '\n')
    receipt = {"schema_version": 1, "acceptance": "blocked", "profiles": list(PROFILES),
               "host": {"architecture": platform.machine(), "python": platform.python_version(), "platform": platform.platform()},
               "source_files": len(ledger), "privacy_failures": failures, "artifacts": [],
               "pending_gates": ["recipient adaptation and full-byte privacy", "host dependency rebuild",
                                 "creative render and QA", "coding machinery canary", "exact extracted-byte native install",
                                 "backup/restore/update/rollback", "isolated real inference credentials",
                                 "browser/media/external research runtime coverage", "public source rights clearance",
                                 "independent exact-head reviews", "target installation and owner acceptance"]}
    receipt["generic_public_release"] = "not-accepted"
    receipt['component_export_inventory'] = {
        'path': 'component-export-inventory.json',
        'sha256': digest((proof / 'component-export-inventory.json').read_bytes()),
        'selected_files': export_inventory['selected_files'], 'public_export_authorized': False}
    receipt["generic_pending_gates"] = json.loads((root / "release-manifest.json").read_bytes())["remaining_gates"]
    # Source bytes are staged only after all byte-level privacy gates pass.
    if not failures:
        extracted = {}
        for component, files in sources.items():
            stage = proof / "source" / component
            stage.mkdir(mode=0o700, parents=True)
            for name, data in files.items():
                path = stage / name
                path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
                path.write_bytes(data)
                path.chmod(0o600)
            archive = proof / f"{component}-source.tar.gz"
            bound_instructions = instruction_hashes if component == "profile-distributions" else {}
            archive_hash = build_archive(stage, archive, instruction_hashes=bound_instructions)
            receipt["artifacts"].append({"path": archive.name, "sha256": archive_hash})
            # All runtime validation operates on restored bytes, never source stage.
            extracted[component] = restore_archive(archive, fixture_root / proof.name / component,
                                                   instruction_hashes=bound_instructions)
            again = proof / f"{component}-reproducibility.tar.gz"
            if build_archive(stage, again, instruction_hashes=bound_instructions) != archive_hash:
                raise ValueError("non-deterministic source archive")
            for name, data in files.items():
                if name.endswith(".py"):
                    compile(data, f"{component}/{name}", "exec")
        receipt["source_restore_and_determinism"] = "passed"
        receipt['timing_primitive_canary'] = timing_primitive_canary(extracted['timing'])
        receipt["pending_gates"].remove("recipient adaptation and full-byte privacy")
        runtime = fixture_root / proof.name / "runtime"
        runtime.mkdir(mode=0o700)
        environment = isolated_environment(runtime)
        for name in ("home", "tmp", "uv-cache"):
            (runtime / name).mkdir(mode=0o700)
        commands = []
        rebuilt = []

        def run(arguments: list[str], *, cwd: Path = runtime, timeout: int = 600) -> bool:
            result = subprocess.run(arguments, cwd=cwd, env=environment, stdin=subprocess.DEVNULL,
                                    capture_output=True, text=True, timeout=timeout)
            index = len(commands) + 1
            (proof / f"runtime-command-{index:02d}.log").write_text(result.stdout + result.stderr)
            commands.append({"argv": arguments, "exit_code": result.returncode,
                             "log": f"runtime-command-{index:02d}.log"})
            return result.returncode == 0

        # A private source binding is never substituted for a failed official
        # public fetch. This separate gate does not authorize a runtime fork.
        public_ok = run([sys.executable, "-B",
                         str(extracted["generic-foundation"] / "scripts/public_runtime.py"),
                         "--commit", SOURCE_BINDINGS["hermes"][1],
                         "--destination", str(runtime / "official-public-hermes")], timeout=180)
        receipt["public_runtime_acquisition"] = {
            "status": "acquired-not-compatibility-certified" if public_ok else "blocked",
            "revision": SOURCE_BINDINGS["hermes"][1], "log": commands[-1]["log"],
            "private_fallback": False,
            "remaining": ["public compatible native extension and license binding", "isolated public install"]}

        # Distinct venvs avoid overlapping Art distribution/package names.
        for component in ("studio", "vector", "hermes"):
            venv = runtime / (component + "-venv")
            if not run([sys.executable, "-B", "-m", "venv", str(venv)]):
                break
            python = str(venv / "bin/python")
            if not run([python, "-B", "-m", "pip", "--isolated", "install", "--disable-pip-version-check",
                        "--no-cache-dir", "-e", str(extracted[component])]):
                receipt["runtime_failure"] = component + " extracted-source editable dependency rebuild"
                break
            if not run([python, "-B", "-m", "pip", "check"]):
                receipt["runtime_failure"] = component + " dependency consistency"
                break
            run([python, "-B", "-m", "pip", "freeze", "--all"])
            # Capture resolver output as data, removing editable VCS/local locators.
            freeze = (proof / commands[-1]["log"]).read_text()
            pins = [line for line in freeze.splitlines() if re.fullmatch(r"[A-Za-z0-9_.-]+==[A-Za-z0-9_.+!-]+", line)]
            (proof / f"{component}-host-dependencies.txt").write_text("\n".join(sorted(pins)) + "\n")
            rebuilt.append(component)
            if component == "studio":
                if not run([python, "-B", "-m", "art_studio.cli", "doctor"], cwd=extracted[component]):
                    receipt["runtime_failure"] = "Studio doctor"
                    break
            if component == "vector":
                # Factory geometry is original harmless test data, never payload.
                source = runtime / "canary.svg"
                source.write_text('<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 32 32"><path id="mark" fill="#000000" d="M 2 2 L 30 2 L 30 30 L 2 30 Z"/></svg>')
                canary = (
                    "from pathlib import Path; from art_vector.inkscape import InkscapeAdapter; "
                    "from art_vector.svg_document import validate_svg; from art_vector.metrics import compare_png; "
                    "import json; p=Path('canary.svg'); validate_svg(p.read_bytes()); "
                    "r=InkscapeAdapter().render_png(p,Path('canary.png'),width=32,height=32); "
                    "b=Path('canary.png').read_bytes(); qa=compare_png(b,b); "
                    "assert qa['after_alpha_bounds']==[2,2,29,29]; "
                    "p.write_bytes(p.read_bytes().replace(b'L 30 2 L 30 30',b'L 22 2 L 22 30')); "
                    "validate_svg(p.read_bytes()); "
                    "InkscapeAdapter().render_png(p,Path('changed.png'),width=32,height=32); "
                    "changed=compare_png(b,Path('changed.png').read_bytes()); "
                    "assert changed['changed_pixel_count']==28*8; "
                    "assert changed['changed_pixel_bounds']==[22,2,29,29]; "
                    "print(json.dumps({'render':r,'qa':qa,'changed_qa':changed}))"
                )
                if not run([python, "-B", "-c", canary]):
                    receipt["runtime_failure"] = "actual Vector Inkscape render/PNG QA"
                    break
                receipt["creative_render_and_qa"] = "passed"
                receipt["pending_gates"].remove("creative render and QA")
                browser = (
                    "from pathlib import Path\nfrom art_vector.chromium import ChromiumAdapter\n"
                    "from art_vector.inkscape import BackendError\nimport json\n"
                    "try:\n ChromiumAdapter().render_png(Path('canary.svg'),Path('browser.png'),width=32,height=32)\n"
                    "except BackendError as error:\n print(json.dumps({'browser_canary':'blocked','backend_failure':str(error)}))\n"
                )
                if run([python, "-B", "-c", browser]):
                    receipt["browser_readiness"] = json.loads((proof / commands[-1]["log"]).read_text())
            if component == "hermes":
                if not run([python, "-B", "-m", "hermes_cli.main", "--help"], cwd=extracted[component]):
                    receipt["runtime_failure"] = "extracted Hermes CLI import/asset closure"
                    break
                if run([python, "-B", "-c", native_profile_canary(),
                        str(extracted["profile-distributions"] / "profiles")]):
                    receipt["native_profile_install_restore"] = json.loads((proof / commands[-1]["log"]).read_text())
                    receipt["pending_gates"].remove("exact extracted-byte native install")
                    # Same-version update/restore is measured, not version migration
                    # or full-home/vault backup and rollback acceptance.
                else:
                    receipt["runtime_failure"] = "extracted six-profile native install/restore"
                    break
                recovery = runtime / "native-home-canary"
                recovery.mkdir(mode=0o700)
                for directory in ("home", "tmp"):
                    (recovery / directory).mkdir(mode=0o700)
                recovery_env = isolated_environment(recovery)
                recovery_env["PYTHONPATH"] = str(extracted["hermes"])
                operation = subprocess.run(
                    [python, "-B", str(extracted["generic-foundation"] / "scripts/native_operations_canary.py"),
                     str(extracted["profile-distributions"] / "profiles/forge/SOUL.md")],
                    cwd=recovery, env=recovery_env, stdin=subprocess.DEVNULL,
                    capture_output=True, text=True, timeout=120)
                (proof / "native-home-canary.log").write_text(operation.stdout + operation.stderr)
                receipt["native_home_canary_exit_code"] = operation.returncode
                if operation.returncode == 0:
                    receipt["native_home_recovery"] = json.loads(operation.stdout.splitlines()[-1])
                    receipt["config_schema_migration"] = "passed; native schema migration with pre-migration rollback"
                    # Runtime binary upgrade and external vault remain separate gates.
                else:
                    receipt["runtime_failure"] = "actual native home/schema recovery canary"
                    break
                if run([python, "-B", str(extracted["generic-foundation"] / "scripts/native_pipeline_canary.py")]):
                    receipt["native_pipeline_primitives"] = json.loads((proof / commands[-1]["log"]).read_text().splitlines()[-1])
                    receipt["coding_machinery_canary"] = "passed native primitives; governed execution remains root-owned pending"
                else:
                    receipt["runtime_failure"] = "extracted native pipeline primitives"
        if rebuilt == ["studio", "vector", "hermes"] and "runtime_failure" not in receipt:
            receipt["host_dependency_rebuild"] = "passed; pinned direct dependencies plus captured resolved host set"
            receipt["pending_gates"].remove("host dependency rebuild")
        receipt["runtime_commands"] = commands
        if "runtime_failure" not in receipt:
            support_venv = runtime / "supporting-venv"
            python = str(support_venv / "bin/python")
            if (run([sys.executable, "-B", "-m", "venv", str(support_venv)])
                    and run([python, "-B", "-m", "pip", "--isolated", "install", "--disable-pip-version-check",
                             "--no-cache-dir", "-r", str(extracted["supporting"] / "requirements-host.txt")])
                    and run([python, "-B", "-m", "pip", "--isolated", "install", "--disable-pip-version-check",
                             "--no-cache-dir", "-e", str(extracted["supporting"])])
                    and run([python, "-B", "-m", "pip", "check"])):
                run([python, "-B", "-m", "pip", "freeze", "--all"])
                pins = (proof / commands[-1]["log"]).read_text()
                pins = [line for line in pins.splitlines() if re.fullmatch(r"[A-Za-z0-9_.-]+==[A-Za-z0-9_.+!-]+", line)]
                (proof / "supporting-host-dependencies.txt").write_text("\n".join(sorted(pins)) + "\n")
                # No source working tree imports: actual restored supporting API.
                code = ("import json; from pathlib import Path; "
                        "from supporting_runtime.runtime import local_canary; "
                        "print(json.dumps(local_canary(Path('supporting-output')),sort_keys=True))")
                if run([python, "-B", "-c", code]):
                    receipt["supporting_canaries"] = "passed; real local DOCX/XLSX/PDF/raster and local RSS only"
                    reference = "https://hermes-agent.nousresearch.com/docs/"
                    research = (
                        "import json; from supporting_runtime.runtime import fetch_public_reference; "
                        f"print(json.dumps(fetch_public_reference({reference!r}, allowed_urls=[{reference!r}]),sort_keys=True))")
                    if run([python, "-B", "-c", research], timeout=45):
                        receipt["public_research_alternative"] = json.loads((proof / commands[-1]["log"]).read_text())
                    else:
                        receipt["public_research_alternative"] = {"status": "blocked", "log": commands[-1]["log"],
                                                                   "browser_javascript": "not-exercised"}
                    original_art = (
                        "import json; from pathlib import Path; from PIL import Image, ImageChops; "
                        "from supporting_runtime.runtime import render_geometric_art; "
                        "design={'width':32,'height':32,'rectangles':[{'x':2,'y':2,'width':28,'height':28,'fill':'#123456'}]}; "
                        "a=render_geometric_art(design,Path('original-art')); "
                        "design['rectangles'][0]['width']=20; "
                        "b=render_geometric_art(design,Path('revised-art')); "
                        "left=Image.open('original-art/render.png'); right=Image.open('revised-art/render.png'); "
                        "assert left.size==right.size==(32,32); "
                        "assert ImageChops.difference(left,right).getbbox()==(22,2,30,30); "
                        "count=sum(left.getpixel((x,y))!=right.getpixel((x,y)) for x in range(32) for y in range(32)); "
                        "assert count==224; "
                        "print(json.dumps({'original':a,'revised':b,'changed_pixel_count':count,'scope':'original-geometric-SVG-PNG-only'}))"
                    )
                    if run([python, "-B", "-c", original_art]):
                        receipt["original_creative_canary"] = json.loads((proof / commands[-1]["log"]).read_text())
                    else:
                        receipt["runtime_failure"] = "original geometric render and changed-pixel QA"
                    media = ("import json; from pathlib import Path; "
                             "from supporting_runtime.runtime import media_canary; "
                             "print(json.dumps(media_canary(Path('media-output')),sort_keys=True))")
                    if run([python, "-B", "-c", media]):
                        receipt["media_canary"] = json.loads((proof / commands[-1]["log"]).read_text())
                    else:
                        receipt["runtime_failure"] = "actual media workflow"
                else:
                    receipt["runtime_failure"] = "supporting workflow canary"
            else:
                receipt["runtime_failure"] = "supporting dependency rebuild"
    (proof / "receipt.json").write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n")
    return receipt
