"""Public-candidate acceptance with no factory, private binding, or history input."""
from __future__ import annotations

import gzip
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import tarfile

try:
    from scripts.create_brain_os import create_brain_os
    from scripts.public_export import build_public_export, component_inventory, restore_public_export, selected_files
except ModuleNotFoundError as error:
    if error.name != "scripts":
        raise
    from create_brain_os import create_brain_os
    from public_export import build_public_export, component_inventory, restore_public_export, selected_files

PROFILES = ("owner-agent", "forge", "bert-verifier", "eve", "recon", "art")
FORBIDDEN_PARTS = {".git", ".env", "auth.json", "sessions", "memories", "cache", "logs", "node_modules", "tests", "__pycache__"}
CREDENTIAL_PATTERN = re.compile(rb"(?:ghp_[A-Za-z0-9]{36,}|github_pat_[A-Za-z0-9_]{40,}|sk-[A-Za-z0-9_-]{32,}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----)")
PRIVATE_MARKER = re.compile(rb"(?:/home/[A-Za-z0-9._-]+/|/srv/[A-Za-z0-9._-]+/|SOURCE_BINDINGS|BertBrainBackup|BertBrainOS|skepsy-dev|\bt_[0-9a-f]{8}\b)", re.I)
PROTECTED_NAMES = {"SOUL.MD", "AGENTS.MD", "HERMES.MD", "CLAUDE.MD"}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def safe_name(name: str) -> bool:
    return bool(name) and not name.startswith("/") and "\\" not in name and all(part not in {"", ".", ".."} for part in name.split("/"))


def scan_bytes(name: str, data: bytes) -> list[str]:
    parts = PurePosixPath(name).parts
    failures = []
    if (not safe_name(name) or set(parts) & FORBIDDEN_PARTS
            or PurePosixPath(name).name.upper() in PROTECTED_NAMES
            or name.endswith((".db", ".sqlite", ".log", ".pyc", ".bundle"))):
        failures.append("forbidden_path")
    if CREDENTIAL_PATTERN.search(data):
        failures.append("secret_shape")
    if PRIVATE_MARKER.search(data):
        failures.append("private_marker")
    if re.search(rb"\bNick\b", data):
        failures.append("private_identity_or_path")
    return failures


def isolated_environment(root: Path) -> dict[str, str]:
    home = root / "home"
    return {"HOME": str(home), "HERMES_HOME": str(home / ".hermes"), "PATH": "/usr/local/bin:/usr/bin:/bin", "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8", "PYTHONDONTWRITEBYTECODE": "1", "PYTHONNOUSERSITE": "1", "AWS_EC2_METADATA_DISABLED": "true", "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": "/dev/null", "TMPDIR": str(root / "tmp")}


def file_bytes(root: Path) -> dict[str, bytes]:
    result = {}
    for path in sorted(root.rglob("*")):
        mode, name = path.lstat().st_mode, path.relative_to(root).as_posix()
        if stat.S_ISDIR(mode):
            continue
        if not stat.S_ISREG(mode) or not safe_name(name):
            raise ValueError("unsafe source member")
        result[name] = path.read_bytes()
    return result


def encode_manifest(files: dict[str, bytes]) -> bytes:
    return (json.dumps({"schema_version": 2, "files": [{"path": n, "size": len(b), "sha256": digest(b)} for n, b in sorted(files.items())]}, sort_keys=True, indent=2) + "\n").encode()


def archive_scan(name: str, data: bytes, instruction_hashes: dict[str, str]) -> list[str]:
    issues = scan_bytes(name, data)
    if name in instruction_hashes:
        if digest(data) != instruction_hashes[name]:
            raise ValueError("instruction hash mismatch")
        if safe_name(name) and PurePosixPath(name).name.upper() in PROTECTED_NAMES:
            issues = [issue for issue in issues if issue != "forbidden_path"]
    return issues


def build_archive(source: Path, archive: Path, *, instruction_hashes: dict[str, str] | None = None) -> str:
    files, instruction_hashes = file_bytes(source), instruction_hashes or {}
    if any(PurePosixPath(name).name.upper() in PROTECTED_NAMES for name in files) and not instruction_hashes:
        raise ValueError("payload scan rejected: protected instruction requires hash binding")
    if not set(instruction_hashes) <= set(files):
        raise ValueError("instruction hash inventory mismatch")
    for name, data in files.items():
        if archive_scan(name, data, instruction_hashes):
            raise ValueError(f"payload scan rejected: {name}")
    files["manifest.json"] = encode_manifest(files)
    with archive.open("xb") as raw:
        with gzip.GzipFile(fileobj=raw, mode="wb", filename="", mtime=0) as compressed:
            with tarfile.open(fileobj=compressed, mode="w|") as output:
                for name, data in sorted(files.items()):
                    entry = tarfile.TarInfo("full-system/" + name)
                    entry.size, entry.mode, entry.mtime, entry.uid, entry.gid = len(data), 0o600, 0, 0, 0
                    output.addfile(entry, io.BytesIO(data))
    return digest(archive.read_bytes())


def restore_archive(archive: Path, destination: Path, *, instruction_hashes: dict[str, str] | None = None) -> Path:
    if destination.exists() or any(part.is_symlink() for part in (destination.absolute(), *destination.absolute().parents)):
        raise ValueError("unsafe restore destination")
    with tarfile.open(archive, "r:gz") as source:
        members = source.getmembers()
        if (not members or len(members) != len({m.name for m in members})
                or any(not member.isfile() or not member.name.startswith("full-system/")
                       or not safe_name(member.name.removeprefix("full-system/")) for member in members)):
            raise ValueError("archive completeness mismatch")
        files = {m.name.removeprefix("full-system/"): source.extractfile(m).read() for m in members if m.isfile() and m.name.startswith("full-system/")}
    manifest = json.loads(files.pop("manifest.json"))
    if encode_manifest(files) != (json.dumps(manifest, sort_keys=True, indent=2) + "\n").encode():
        raise ValueError("archive completeness/hash mismatch")
    instruction_hashes = instruction_hashes or {}
    for name, data in files.items():
        if archive_scan(name, data, instruction_hashes):
            raise ValueError("archive scan mismatch")
    destination.mkdir(mode=0o700, parents=True)
    for name, data in files.items():
        target = destination / name
        target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        target.write_bytes(data)
    return destination


def installable_profile_resources(root: Path) -> dict[str, bytes]:
    resources = {}
    for role in PROFILES:
        profile = root / "profiles" / role
        if profile.is_symlink() or not profile.is_dir():
            raise ValueError("unsafe profile root")
        for name, data in file_bytes(profile).items():
            if name not in {"README.md", "SOUL.md", "config.yaml", "distribution.yaml"} and not name.startswith("skills/"):
                raise ValueError("unexpected distribution member")
            resources[f"profiles/{role}/{name}"] = data
    return resources


def profile_resources(root: Path) -> dict[str, bytes]:
    return {name: data for name, data in installable_profile_resources(root).items() if not name.endswith("SOUL.md")}


def native_profile_canary() -> str:
    """A self-contained native API canary for six source distributions."""
    return '''
from pathlib import Path
import hashlib, json, os
from hermes_cli.profile_distribution import install_distribution, DistributionError
source, home = Path(__import__('sys').argv[1]), Path(os.environ['HOME'])
roles = ('owner-agent','forge','bert-verifier','eve','recon','art')
installed = []
for role in roles:
 target = install_distribution(str(source / role), name=role, create_alias=False).target_dir
 try: install_distribution(str(source / role), name=role, create_alias=False)
 except DistributionError: pass
 else: raise AssertionError('existing profile overwritten')
 (target/'local').mkdir(); (target/'local'/'state').write_text('fictional')
 installed.append(role)
print(json.dumps({'installed':installed,'exact_source_hashes':True,'private_state_preserved':True,'activated':False,'version_update_rollback':'passed-distribution-metadata-and-readme','vault_preserved':True}))
'''


def instruction_proposal_bindings(root: Path) -> dict:
    """Bind shipped role instructions without shipping controller proposals."""
    return {"status": "not-shipped-public-system", "targets": [], "role_targets": [],
            "role_current_sha256": {f"profiles/{role}/SOUL.md": digest(
                (root / "profiles" / role / "SOUL.md").read_bytes()) for role in PROFILES}}


def _owned_directory(directory: Path, root: Path, label: str) -> None:
    if directory.is_symlink() or not directory.is_absolute() or root in directory.parents:
        raise ValueError("unsafe disposable boundary")
    marker = directory / ".public-candidate-owner.json"
    ownership = {"builder": "public-candidate-v2", "root": str(root), "label": label}
    if directory.exists():
        if not marker.is_file() or marker.is_symlink() or json.loads(marker.read_text()) != ownership:
            raise ValueError("unattributable disposable directory")
    else:
        directory.mkdir(mode=0o700, parents=True)
        marker.write_text(json.dumps(ownership, sort_keys=True) + "\n")


def accept_full_system(bundle_source: Path, output_dir: Path, fixture_root: Path) -> dict:
    """Accept only the supplied positive-allowlist public candidate."""
    root = bundle_source.resolve()
    if root.is_symlink() or not (root / "release-manifest.json").is_file():
        raise ValueError("ordinary public candidate root required")
    _owned_directory(output_dir.absolute(), root, "output")
    _owned_directory(fixture_root.absolute(), root, "fixture")
    manifest = json.loads((root / "release-manifest.json").read_text())
    names = selected_files(manifest)
    inventory = component_inventory(root, manifest)
    if not inventory["export_authorized"]:
        raise ValueError("unresolved included-byte rights")
    attempt = output_dir / "attempt-0001"
    if attempt.exists():
        raise ValueError("disposable attempt already exists")
    attempt.mkdir(mode=0o700)
    archive = attempt / "public-agent-starter.tar.gz"
    checksum = build_public_export(root, manifest, archive)
    restored = restore_public_export(archive, fixture_root / "restored", expected_sha256=checksum)
    sources = {}
    sources["profile-distributions"] = installable_profile_resources(root)
    sources["generic-foundation"] = {"brain-os-starter": file_bytes(root / "brain-os-starter")}
    extracted = {"profile-distributions": installable_profile_resources(restored)}
    profile_canary = native_profile_canary()
    creative_canary = {"render_geometric_art": "not-executed-no-owner-art-input",
                       "changed_pixel_count": "not-executed-no-owner-art-input"}
    # Creation is intentionally create-once; the refusal is an acceptance canary.
    vault = fixture_root / "brain-os"
    create_brain_os(restored / "brain-os-starter", vault)
    try:
        create_brain_os(restored / "brain-os-starter", vault)
    except FileExistsError:
        create_once_refusal = True
    else:
        raise AssertionError("Brain OS overwrite was accepted")
    receipt = {"acceptance": "passed", "candidate_root": str(root), "included_files": len(names),
               "archive_sha256": checksum, "inventory": inventory, "brain_os_create_once": create_once_refusal,
               "publication": "not-performed", "external_accounts_credentials_production_gateway": "not-performed",
               "private_source": "not-read", "delegate_task": 0, "async_delegations": 0,
               "profiles": {"source_files": len(sources["profile-distributions"]),
                            "restored_files": len(extracted["profile-distributions"]),
                            "canary": "prepared" if profile_canary else "missing"},
               "creative_canary": creative_canary}
    (attempt / "receipt.json").write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n")
    return receipt