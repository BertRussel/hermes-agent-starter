#!/usr/bin/env python3
"""Lifecycle canary runner for Hermes profile release checks.

This module intentionally keeps dependencies to the Python standard library only.
The implementation is deterministic, path-safe, and requires explicit execution to
perform workspace mutation.
"""

from __future__ import annotations

import argparse
import datetime
import gzip
import hashlib
import json
import os
import pathlib
import re
import shutil
import stat
import tarfile
import tempfile
import uuid
import subprocess
import time
import sys
from typing import Any, Dict, Iterable, List, Mapping, MutableMapping, Sequence


class LifecycleCanaryError(RuntimeError):
    """Fatal environment/infrastructure failures."""


class UnsafeInvocationError(ValueError):
    """Unsafe or ambiguous invocation of the script."""


CANDIDATE_PROFILES = ["owner-agent", "art", "recon", "forge", "eve"]

CANARY_LIMITS = {
    "required_hermes_version": "0.20.5",
    "candidate_profile_prefix": "profiles/",
    "schema_version": "1.0.0",
}

_PORTABLE_BACKUP_ROOTS = ("local", "memories")

_EXIT_MAP = {
    "ok": 0,
    "passed": 0,
    "dry_run": 0,
    "assertion_failure": 1,
    "unsafe_invocation": 2,
    "infrastructure_unavailable": 3,
}

_SECRET_ENV_PATTERNS = [
    "token",
    "secret",
    "credential",
    "passwd",
    "password",
    "gateway",
    "provider",
    "api_key",
    "access_key",
    "private_key",
    "auth",
    "aws_",
    "azure_",
    "gcp_",
]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    host_parser = subparsers.add_parser("host")
    host_parser.add_argument("--root", required=True)
    host_parser.add_argument("--candidate-head", required=True)
    host_parser.add_argument("--hermes", required=True)
    host_parser.add_argument("--hermes-python", default="")
    host_parser.add_argument("--hermes-version", default=CANARY_LIMITS["required_hermes_version"])
    host_parser.add_argument("--work-root", required=True)
    host_parser.add_argument("--evidence", required=True)
    _add_execution_mode(host_parser)

    docker_parser = subparsers.add_parser("docker")
    docker_parser.add_argument("--root", required=True)
    docker_parser.add_argument("--candidate-head", required=True)
    docker_parser.add_argument("--image", required=True)
    docker_parser.add_argument("--work-root", required=True)
    docker_parser.add_argument("--host-receipt", required=True)
    docker_parser.add_argument("--host-work-root", required=True)
    docker_parser.add_argument("--host-archives", required=True)
    docker_parser.add_argument("--evidence", required=True)
    docker_parser.add_argument("--hermes-version", default=CANARY_LIMITS["required_hermes_version"])
    _add_execution_mode(docker_parser)

    worker_parser = subparsers.add_parser("_worker")
    worker_parser.add_argument("--mode", required=True)
    worker_parser.add_argument("--root", default="")
    worker_parser.add_argument("--input-receipt", default="")
    worker_parser.add_argument("--host-receipt", default="")
    worker_parser.add_argument("--host-archives", default="")
    worker_parser.add_argument("--candidate-head", default="")
    worker_parser.add_argument("--work-root", default="")
    worker_parser.add_argument("--evidence", default="")
    worker_parser.add_argument("--hermes", default="/usr/local/bin/hermes")
    worker_parser.add_argument("--hermes-version", default=CANARY_LIMITS["required_hermes_version"])
    _add_execution_mode(worker_parser, required=True)

    return parser


def _add_execution_mode(parser: argparse.ArgumentParser, *, required: bool = False) -> None:
    mode_group = parser.add_mutually_exclusive_group(required=required)
    mode_group.add_argument(
        "--dry-run",
        action="store_true",
        help="perform preflight checks only (default)",
    )
    mode_group.add_argument(
        "--execute",
        action="store_true",
        help="perform real host actions",
    )
    parser.set_defaults(dry_run=False, execute=False)


def _is_absolute_path(path: pathlib.Path) -> None:
    if not path.is_absolute():
        raise UnsafeInvocationError(f"path must be absolute: {path}")


def _no_follow_parts(path: pathlib.Path) -> None:
    for part in path.parts:
        if part == "..":
            raise UnsafeInvocationError(f"path traversal component in path: {path}")


def validate_path_no_follow(path: str | os.PathLike[str]) -> pathlib.Path:
    candidate = pathlib.Path(path)
    if not candidate.is_absolute():
        raise UnsafeInvocationError(f"path must be absolute: {candidate}")

    _no_follow_parts(candidate)
    if candidate.exists():
        for parent in [candidate] + list(reversed(candidate.parents)):
            try:
                mode = os.lstat(parent).st_mode
            except FileNotFoundError:
                continue
            if stat.S_ISLNK(mode):
                raise UnsafeInvocationError(f"symlink disallowed: {parent}")

    if candidate.exists() and not (candidate.is_file() or candidate.is_dir()):
        raise UnsafeInvocationError(f"non-regular path unsupported: {candidate}")

    return candidate


def _collect_file_hashes(root: pathlib.Path) -> List[Dict[str, Any]]:
    entries: List[Dict[str, Any]] = []
    seen_inodes: set[tuple[int, int]] = set()
    for entry in sorted(root.rglob("*")):
        relative = entry.relative_to(root).as_posix()
        if ".." in pathlib.Path(relative).parts:
            raise UnsafeInvocationError(f"relative path traversal in inventory: {entry}")

        st = os.lstat(entry)
        if stat.S_ISLNK(st.st_mode):
            raise UnsafeInvocationError(f"symlink payload prohibited: {entry}")

        if stat.S_ISREG(st.st_mode):
            seen_key = (st.st_dev, st.st_ino)
            if seen_key in seen_inodes:
                raise UnsafeInvocationError(f"duplicate regular-file inode detected: {entry}")
            seen_inodes.add(seen_key)

            h = hashlib.sha256()
            with entry.open("rb") as handle:
                for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                    h.update(chunk)
            entries.append(
                {
                    "path": relative,
                    "size": st.st_size,
                    "sha256": h.hexdigest(),
                }
            )
        elif stat.S_ISDIR(st.st_mode):
            continue
        else:
            raise UnsafeInvocationError(f"non-regular payload entry forbidden: {entry}")
    return entries


def validate_no_duplicate_inodes(paths: Iterable[os.PathLike[str] | str]) -> None:
    seen: set[tuple[int, int]] = set()
    for path in paths:
        candidate = pathlib.Path(path)
        st = os.lstat(candidate)
        if not stat.S_ISREG(st.st_mode):
            continue
        key = (st.st_dev, st.st_ino)
        if key in seen:
            raise UnsafeInvocationError(f"duplicate inode detected: {candidate}")
        seen.add(key)


def compute_candidate_inventory(root: str | os.PathLike[str]) -> Dict[str, Any]:
    root_path = validate_path_no_follow(root)
    if not root_path.is_dir():
        raise UnsafeInvocationError(f"candidate inventory root must be a directory: {root_path}")

    entries = _collect_file_hashes(root_path)
    hasher = hashlib.sha256()
    for entry in entries:
        hasher.update(f"{entry['path']}|{entry['size']}|{entry['sha256']}\n".encode())
    return {
        "schema_version": CANARY_LIMITS["schema_version"],
        "root": str(root_path),
        "entry_count": len(entries),
        "entries": entries,
        "tree": hasher.hexdigest(),
    }


def validate_candidate_profiles(profiles: Sequence[str]) -> bool:
    ordered = list(profiles)
    if ordered != CANDIDATE_PROFILES:
        raise UnsafeInvocationError(
            "candidate profile set must be exactly owner-agent, art, recon, forge, eve"
        )
    return True


def _parse_distribution_owned(manifest: pathlib.Path) -> list[str]:
    lines = manifest.read_text(encoding="utf-8").splitlines()
    in_owned_block = False
    owned: list[str] = []
    for line in lines:
        if line.startswith("name:"):
            continue
        if line.startswith("version:"):
            continue
        if line.startswith("distribution_owned:"):
            in_owned_block = True
            continue
        if in_owned_block:
            if line.startswith("  - "):
                owned.append(line[4:].strip())
                continue
            if line and not line.startswith("  "):
                in_owned_block = False
    return owned


def _parse_distribution_version(manifest: pathlib.Path) -> str:
    for line in manifest.read_text(encoding="utf-8").splitlines():
        if line.startswith("version:"):
            value = line.split(":", 1)[1].strip()
            if not value:
                break
            return value
    return ""


_SOURCE_MANIFEST_FIELDS = {"name", "version", "description", "distribution_owned"}
_INSTALLER_MANIFEST_FIELDS = {"source", "installed_at"}
NATIVE_BOOTSTRAP_DIRECTORIES = frozenset(
    {"memories", "sessions", "skills", "skins", "logs", "plans", "workspace", "cron", "home"}
)


def _decode_manifest_scalar(value: str) -> str:
    """Decode the narrow scalar subset emitted by PyYAML for manifest values."""
    if not value or value != value.strip() or any(ord(char) < 32 or ord(char) == 127 for char in value):
        raise UnsafeInvocationError("manifest scalar is malformed")
    if value.startswith("'"):
        if len(value) < 2 or not value.endswith("'"):
            raise UnsafeInvocationError("manifest scalar is malformed")
        interior = value[1:-1]
        decoded: list[str] = []
        index = 0
        while index < len(interior):
            char = interior[index]
            if char == "'":
                if index + 1 >= len(interior) or interior[index + 1] != "'":
                    raise UnsafeInvocationError("manifest scalar is malformed")
                decoded.append("'")
                index += 2
                continue
            decoded.append(char)
            index += 1
        decoded_value = "".join(decoded)
        if "\\" in decoded_value:
            raise UnsafeInvocationError("manifest scalar is malformed")
        return decoded_value
    if "'" in value or '"' in value or value.startswith(("[", "{", "&", "!", "*", "|", ">", "@", "`", ":")) or ": " in value:
        raise UnsafeInvocationError("manifest scalar is malformed")
    return value


def _validate_installed_at(value: Any) -> None:
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\+00:00", value):
        raise UnsafeInvocationError("installed manifest installed_at is invalid")
    try:
        parsed = datetime.datetime.fromisoformat(value)
    except ValueError as error:
        raise UnsafeInvocationError("installed manifest installed_at is invalid") from error
    if parsed.tzinfo is None or parsed.utcoffset() != datetime.timedelta(0):
        raise UnsafeInvocationError("installed manifest installed_at is invalid")


def _parse_distribution_manifest(manifest: pathlib.Path) -> Dict[str, Any]:
    """Parse the deliberately small distribution manifest schema without YAML dependencies."""
    parsed: Dict[str, Any] = {}
    active_list: str | None = None
    for raw_line in manifest.read_text(encoding="utf-8").splitlines():
        if not raw_line or raw_line.lstrip().startswith("#"):
            continue
        if raw_line.startswith(("- ", "  - ")):
            if active_list is None:
                raise UnsafeInvocationError("manifest list item has no declared field")
            value = raw_line[2 if raw_line.startswith("- ") else 4:]
            if not value or value != value.strip() or value.startswith(("[", "{", "&", "!", "*", "|", ">", "@", "`", "'", '"', ":")) or ": " in value:
                raise UnsafeInvocationError("manifest list item is malformed")
            parsed[active_list].append(value)
            continue
        if raw_line.startswith((" ", "\t")) or ":" not in raw_line:
            raise UnsafeInvocationError("manifest syntax is unsupported")
        key, value = raw_line.split(":", 1)
        value = value.strip()
        if key not in (_SOURCE_MANIFEST_FIELDS | _INSTALLER_MANIFEST_FIELDS) or key in parsed:
            raise UnsafeInvocationError("manifest field is empty or duplicated")
        if value:
            parsed[key] = _decode_manifest_scalar(value)
            active_list = None
        else:
            if key != "distribution_owned":
                raise UnsafeInvocationError("manifest scalar field is empty")
            parsed[key] = []
            active_list = key

    if not _SOURCE_MANIFEST_FIELDS.issubset(parsed):
        raise UnsafeInvocationError("manifest lacks required source contract fields")
    if not all(isinstance(parsed[field], str) and parsed[field] for field in ("name", "version", "description")):
        raise UnsafeInvocationError("manifest scalar source contract field is invalid")
    owned = parsed["distribution_owned"]
    if not isinstance(owned, list) or not owned or len(owned) != len(set(owned)):
        raise UnsafeInvocationError("manifest distribution_owned is invalid")
    for path in owned:
        candidate = pathlib.PurePosixPath(path)
        if candidate.is_absolute() or ".." in candidate.parts:
            raise UnsafeInvocationError("manifest distribution-owned path is unsafe")
    return parsed


def scan_candidate_profiles(root: str | os.PathLike[str]) -> Dict[str, Dict[str, Any]]:
    root_path = validate_path_no_follow(root)
    if not root_path.exists():
        raise UnsafeInvocationError(f"missing candidate root: {root_path}")

    inventories: Dict[str, Dict[str, Any]] = {}
    for profile in CANDIDATE_PROFILES:
        profile_root = root_path / CANARY_LIMITS["candidate_profile_prefix"] / profile
        if not profile_root.exists() or not profile_root.is_dir():
            raise UnsafeInvocationError(f"missing profile: {profile}")
        profile_root = validate_path_no_follow(profile_root)

        manifest = profile_root / "distribution.yaml"
        if not manifest.is_file():
            raise UnsafeInvocationError(f"missing distribution.yaml for profile {profile}")
        version = _parse_distribution_version(manifest)
        if not version:
            raise UnsafeInvocationError(f"missing distribution version for profile {profile}")

        validate_no_duplicate_inodes([manifest])
        inventory = compute_candidate_inventory(profile_root)
        inventories[profile] = {
            "inventory": inventory,
            "distribution": str(manifest),
            "owned_files": _parse_distribution_owned(manifest),
            "version": version,
            "name": profile,
        }
    return inventories


def validate_candidate_head(candidate_head: str, expected_head: str) -> bool:
    if len(expected_head) != 40 or not re.fullmatch(r"[0-9a-f]{40}", expected_head):
        raise UnsafeInvocationError("expected candidate head must be a 40-char hex sha")
    if candidate_head != expected_head:
        raise UnsafeInvocationError(
            f"candidate head mismatch (got {candidate_head}, expected {expected_head})"
        )
    return True


def validate_work_root(candidate_root: str | os.PathLike[str], work_root: str | os.PathLike[str]) -> pathlib.Path:
    candidate = validate_path_no_follow(candidate_root)
    work = pathlib.Path(work_root)
    if not work.is_absolute():
        raise UnsafeInvocationError(f"work root must be absolute: {work}")
    _no_follow_parts(work)

    work = pathlib.Path(os.path.normpath(str(work))).resolve()
    candidate_norm = pathlib.Path(str(candidate)).resolve()

    if work == candidate_norm:
        raise UnsafeInvocationError("work root may not equal candidate root")
    if str(candidate_norm).startswith(f"{str(work)}/"):
        raise UnsafeInvocationError("candidate root may not be inside work root")
    return work


def validate_receipt_relationships(receipt: Mapping[str, Any]) -> bool:
    if not isinstance(receipt, Mapping):
        raise ValueError("receipt must be a mapping")
    candidate_head = receipt.get("candidate_head")
    if not isinstance(candidate_head, str) or not re.fullmatch(r"[0-9a-f]{40}", candidate_head):
        raise ValueError("invalid candidate head")

    if receipt.get("hermes_version") != CANARY_LIMITS["required_hermes_version"]:
        raise ValueError("hermes version mismatch")

    profiles = receipt.get("profiles")
    if list(profiles or []) != CANDIDATE_PROFILES:
        raise ValueError("receipt profiles mismatch")

    inventories = receipt.get("profile_inventories") or {}
    if sorted(inventories.keys()) != sorted(CANDIDATE_PROFILES):
        raise ValueError("receipt profile inventories mismatch")
    return True


def assert_receipt_relationships(receipt: Mapping[str, Any]) -> bool:
    return validate_receipt_relationships(receipt)


def validate_receipt_coherence(receipt: Mapping[str, Any]) -> bool:
    return validate_receipt_relationships(receipt)


def validate_archive_member(member_name: str) -> str:
    if not member_name:
        raise UnsafeInvocationError("empty archive member")
    if member_name.startswith("/"):
        raise UnsafeInvocationError(f"absolute archive member: {member_name}")
    if ":" in member_name and member_name.count(":") >= 2:
        raise UnsafeInvocationError(f"invalid archive member path: {member_name}")
    if ".." in member_name.split("/"):
        raise UnsafeInvocationError(f"parent traversal disallowed: {member_name}")
    if re.search(r"^[A-Za-z]:[\\/]", member_name):
        raise UnsafeInvocationError(f"windows absolute member disallowed: {member_name}")
    if member_name.startswith("\\\\"):
        raise UnsafeInvocationError(f"UNC path disallowed: {member_name}")
    return member_name


def _path_is_inside(root: pathlib.Path, candidate: pathlib.Path) -> bool:
    try:
        candidate.relative_to(root)
        return True
    except ValueError:
        return False


def _clean_env(env: Mapping[str, str] | None) -> Dict[str, str]:
    allowed = {
        "PATH",
        "HOME",
        "HERMES_HOME",
        "TMPDIR",
        "PYTHONNOUSERSITE",
        "NO_COLOR",
        "PYTHONDONTWRITEBYTECODE",
    }

    source = {key: value for key, value in os.environ.items() if key in allowed or key.startswith("CANARY_")}
    if env:
        source.update({str(k): str(v) for k, v in env.items()})

    lowered_removed = {
        key
        for key in source
        if any(tok in key.lower() for tok in _SECRET_ENV_PATTERNS)
    }
    for key in lowered_removed:
        source.pop(key, None)

    cleaned: Dict[str, str] = {}
    for key, value in source.items():
        if key in allowed or key.startswith("CANARY_"):
            cleaned[key] = value

    if "PATH" not in cleaned:
        cleaned["PATH"] = "/usr/bin:/bin"
    return cleaned


def run_command(
    argv: Sequence[str],
    env: Mapping[str, str] | None = None,
    timeout: int = 60,
    include_output: bool = False,
    cwd: str | os.PathLike[str] | None = None,
) -> Dict[str, Any]:
    if not argv:
        raise UnsafeInvocationError("argv must contain at least one executable")

    start = time.time()
    completed = subprocess.run(
        list(argv),
        env=_clean_env(dict(env) if env is not None else None),
        cwd=None if cwd is None else str(cwd),
        timeout=timeout,
        text=True,
        capture_output=True,
        shell=False,
        check=False,
    )
    elapsed = time.time() - start

    stdout_data = completed.stdout or ""
    stderr_data = completed.stderr or ""
    payload = {
        "command": list(argv),
        "returncode": completed.returncode,
        "stdout_hash": hashlib.sha256(stdout_data.encode()).hexdigest(),
        "stderr_hash": hashlib.sha256(stderr_data.encode()).hexdigest(),
        "elapsed_seconds": elapsed,
        "env": _clean_env(env),
    }
    if include_output:
        payload["stdout"] = stdout_data
        payload["stderr"] = stderr_data
    return payload


def parse_phase_status(phase_event: Mapping[str, Any] | str | int | bool) -> str:
    if isinstance(phase_event, str):
        return phase_event
    if isinstance(phase_event, bool):
        return "ok" if phase_event else "failed"
    if isinstance(phase_event, int):
        return "ok" if phase_event == 0 else "failed"

    if not isinstance(phase_event, Mapping):
        raise UnsafeInvocationError("phase event type unsupported")

    ok = phase_event.get("ok", False)
    returncode = phase_event.get("returncode", 0)
    if bool(ok) and returncode == 0:
        return "ok"
    if returncode == 0 and "stdout_hash" in phase_event:
        return "ok"
    return "failed"


def validate_phase_result(event: Mapping[str, Any]) -> bool:
    returncode = int(event.get("returncode", 1))
    if event.get("ok", False) and returncode == 0:
        return True
    raise ValueError("command phase did not satisfy expected success semantics")


def map_exit_code(status: str) -> int:
    if status not in _EXIT_MAP:
        raise ValueError(f"unknown status: {status}")
    return _EXIT_MAP[status]


def assert_phase_dependency(completed: Sequence[str], phase: str) -> bool:
    dependencies = {
        "host": set(),
        "install": set(),
        "update": {"install"},
        "force": {"update"},
        "export": {"force"},
        "import": {"export"},
        "delete": {"import"},
        "_worker": {"host"},
        "docker": set(),
    }

    completed_set = set(completed)
    if phase in completed_set:
        return True

    phase_order = ["host", "install", "update", "force", "export", "import", "delete", "_worker", "docker"]
    order_index = {name: idx for idx, name in enumerate(phase_order)}
    if phase not in order_index:
        raise ValueError(f"unknown phase: {phase}")

    required = dependencies.get(phase, set())
    phase_idx = order_index[phase]
    for completed_phase in completed_set:
        completed_idx = order_index.get(completed_phase)
        if completed_idx is not None and completed_idx > phase_idx:
            raise ValueError(f"phase {phase} is not reachable from completed history")

    if not required.issubset(completed_set):
        raise ValueError(f"missing dependency for phase {phase}: {sorted(required - completed_set)}")
    return True


def validate_update_preserved_user_data(before: Mapping[str, str], after: Mapping[str, str]) -> bool:
    if not before:
        raise ValueError("before-image cannot be empty")
    if before != after:
        raise ValueError("user owned artifacts changed")
    return True


def validate_force_config_reset(before: str, after: str) -> bool:
    if before != after:
        raise ValueError("forced config reset did not restore candidate config")
    return True


def validate_candidate_payload_restored(before: Mapping[str, Any], drifted: Mapping[str, Any]) -> bool:
    return before == drifted


def build_synthetic_recipient_receipt(
    profile: str,
    candidate_head: str,
    profile_head: str | None = None,
    *,
    recipient: str = "synthetic-recipient",
    ownership_scope: str = "user-owned-local-directory",
    canary_id: str | None = None,
    nonce: str | None = None,
) -> Dict[str, Any]:
    return {
        "schema_version": CANARY_LIMITS["schema_version"],
        "receipt_type": "synthetic_recipient_ownership",
        "synthetic": True,
        "canary_id": canary_id or str(uuid.uuid4()),
        "profile": profile,
        "recipient": recipient,
        "candidate_head": candidate_head,
        "profile_head": profile_head,
        "ownership_scope": ownership_scope,
        "nonce": nonce or str(uuid.uuid4()),
        "created_phase": "post-install",
    }


def write_json_receipt_atomically(path: str | os.PathLike[str], payload: Mapping[str, Any]) -> None:
    destination = pathlib.Path(path)
    if destination.is_absolute() is False:
        raise UnsafeInvocationError("receipt path must be absolute")
    parent = destination.parent
    validate_path_no_follow(str(parent))
    if destination.exists():
        if destination.is_symlink():
            raise UnsafeInvocationError("receipt destination may not be symlink")

    content = json.dumps(payload, sort_keys=True, indent=2, ensure_ascii=False) + "\n"
    temp = parent / f".{destination.name}.{uuid.uuid4().hex}.tmp"

    flags = os.O_CREAT | os.O_TRUNC | os.O_WRONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW

    fd = os.open(temp, flags, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
    finally:
        try:
            os.close(fd)
        except OSError:
            pass

    os.replace(temp, destination)


def _hash_phase_history(phase_history: Sequence[Mapping[str, Any]]) -> str:
    hasher = hashlib.sha256()
    for phase in phase_history:
        hasher.update(json.dumps(phase, sort_keys=True).encode())
    return hasher.hexdigest()


def build_receipt(
    *,
    mode: str,
    status: str,
    candidate_head: str,
    root: str,
    hermes_version: str,
    work_root: str,
    phase_history: Sequence[Mapping[str, Any]] | None = None,
    canary_id: str | None = None,
    inventory_before: Mapping[str, Any] | None = None,
    inventory_after: Mapping[str, Any] | None = None,
    candidate_profiles: Sequence[str] | None = None,
    evidence_root: str | None = None,
    flags: Mapping[str, Any] | None = None,
    claims: Mapping[str, bool] | None = None,
    changed_paths: Sequence[str] | None = None,
) -> Dict[str, Any]:
    return {
        "schema_version": CANARY_LIMITS["schema_version"],
        "receipt_type": "lifecycle-canary",
        "type": mode,
        "mode": mode,
        "status": status,
        "canary_id": canary_id or str(uuid.uuid4()),
        "candidate_head": candidate_head,
        "candidate_root": root,
        "hermes_version": hermes_version,
        "work_root": work_root,
        "candidate_profiles": list(candidate_profiles) if candidate_profiles else list(CANDIDATE_PROFILES),
        "phase_status_hash": _hash_phase_history(phase_history or []),
        "phase_history": list(phase_history or []),
        "inventory_before": dict(inventory_before or {}),
        "inventory_after": dict(inventory_after or {}),
        "evidence_root": evidence_root,
        "flags": dict(flags or {}),
        "claims": dict(claims or {}),
        "changed_paths": list(changed_paths or []),
    }


def _build_claim_map() -> Dict[str, bool]:
    return {
        "all_claims": False,
        "exact_five_installs": False,
        "update_preserves_user_data": False,
        "force_config_restore": False,
        "portable_backup_created": False,
        "portable_profile_reinstalled": False,
        "archive_safety": False,
        "restore_uses_native_profile_import": False,
        "restore_reinstall_works": False,
        "restore_isolated": False,
        "delete_target_only": False,
        "candidate_inventory_unchanged": False,
        "secrets_excluded": False,
        "workspaces_isolated": False,
    }


def _build_profile_command(action: str, profile: str, hermes: str, extra_args: Sequence[str] | None = None) -> List[str]:
    if action not in {"install", "update", "delete", "export", "info", "import", "force"}:
        raise UnsafeInvocationError(f"unsupported profile action: {action}")
    command = [str(hermes), "profile", action, profile]
    if action in {"export", "force"}:
        command = [str(hermes), "profile", "update", profile]
        if action == "force":
            command.extend(["--force-config", "--yes"])
        else:
            command.append("--yes")
    elif action == "install":
        command.extend(["--yes"])
    elif action == "update":
        command.extend(["--yes"])
    elif action == "delete":
        command.extend(["--yes"])
    if extra_args:
        command.extend(extra_args)
    return command


def build_profile_command(action: str, profile: str, hermes: str, extra_args: Sequence[str] | None = None) -> List[str]:
    if action not in {"install", "update", "delete", "export", "import", "info"}:
        raise ValueError(f"unsupported profile action: {action}")
    command = [str(hermes), "profile", action, profile]
    if extra_args:
        command.extend(extra_args)
    return command


def validate_docker_image_reference(image: str) -> str:
    image = image.strip()
    if image.startswith("sha256:"):
        if not re.fullmatch(r"sha256:[0-9a-fA-F]{64}", image):
            raise ValueError("invalid local image id")
        return image

    if "@" not in image:
        raise ValueError("immutable image reference required")

    digest = image.rsplit("@", 1)[1]
    if not re.fullmatch(r"sha256:[0-9a-fA-F]+", digest):
        raise ValueError("unsupported image digest format")
    return image


def build_docker_run_args(
    *,
    image: str,
    network: str = "none",
    read_only: bool = True,
    no_new_privileges: bool = True,
    cap_drop: Sequence[str] | None = None,
    volumes: Sequence[tuple[str, str]] | None = None,
    env: Mapping[str, str] | None = None,
    tmpfs: str | None = "/tmp:rw,noexec,nosuid,nodev,size=64m",
    pids_limit: int = 64,
    memory_limit: str = "768m",
    cpus: str = "1.0",
    user: str | None = None,
) -> List[str]:
    validated = [
        "docker",
        "run",
        "--rm",
        "--network",
        network,
    ]
    if read_only:
        validated.extend(["--read-only"])
    if no_new_privileges:
        validated.extend(["--security-opt", "no-new-privileges"])
    for cap in cap_drop or ["ALL"]:
        validated.extend(["--cap-drop", cap])
    if tmpfs:
        validated.extend(["--tmpfs", tmpfs])
    validated.extend(["--pids-limit", str(pids_limit)])
    validated.extend(["--memory", memory_limit])
    validated.extend(["--cpus", cpus])
    if volumes:
        for host_path, container_path in volumes:
            validated.extend(["-v", f"{host_path}:{container_path}"])
    if env:
        for key, value in env.items():
            validated.extend(["-e", f"{key}={value}"])
    if user:
        validated.extend(["--user", user])
    validated.extend(["--entrypoint", "", image])
    return validated


def validate_export_archive(archive: str | os.PathLike[str], *, expected_profile: str | None = None) -> List[str]:
    return _validate_export_archive(archive, expected_profile=expected_profile)


def validate_import_restore(archive: str | os.PathLike[str], restore_home: str | os.PathLike[str]) -> bool:
    archive_path = validate_path_no_follow(archive)
    restore = pathlib.Path(restore_home)
    if not archive_path.exists():
        raise ValueError("missing archive")
    if restore.exists():
        validate_work_root(str(archive_path.parent), str(restore))
    else:
        validate_path_no_follow(str(restore))
    validate_export_archive(archive_path)
    return True


def validate_uninstall_targets(current: Iterable[str], intended: Iterable[str]) -> set[str] | list[str] | tuple[str, ...]:
    current_set = set(current)
    intended_set = set(intended)
    remaining = sorted(current_set - intended_set)
    return set(remaining)


def validate_publication_readiness(claims: Mapping[str, Any]) -> bool:
    forbidden = {"arbitrary_version_rollback_supported", "all_secrets_excluded", "publication_ready"}
    for key in forbidden:
        if claims.get(key) is True:
            raise ValueError(f"false claim emitted: {key}")
    return True


def assert_no_false_claims(claims: Mapping[str, Any]) -> bool:
    return validate_publication_readiness(claims)


def validate_claims(claims: Mapping[str, Any]) -> bool:
    return validate_publication_readiness(claims)


def _observe_head(candidate_root: pathlib.Path) -> str:
    proc = subprocess.run(
        ["git", "-C", str(candidate_root), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=False,
        env={"PATH": _clean_env({}).get("PATH", "/usr/bin:/bin")},
    )
    if proc.returncode != 0:
        raise LifecycleCanaryError("failed to read candidate head")
    head = (proc.stdout or "").strip()
    if not re.fullmatch(r"[0-9a-f]{40}", head):
        raise LifecycleCanaryError("invalid observed head")
    return head


def _observe_hermes_version(hermes_binary: pathlib.Path) -> str:
    proc = subprocess.run(
        [str(hermes_binary), "--version"],
        capture_output=True,
        text=True,
        check=False,
        env=_clean_env({"PATH": os.environ.get("PATH", "/usr/bin:/bin")}),
    )
    if proc.returncode != 0:
        raise LifecycleCanaryError("hermes --version command failed")

    observed = (proc.stdout or "") + "\n" + (proc.stderr or "")
    match = re.search(r"(\d+\.\d+\.\d+)", observed)
    if not match:
        raise LifecycleCanaryError("could not parse hermes version")
    return match.group(1)


def _observe_clean_status(candidate_root: pathlib.Path) -> str:
    proc = subprocess.run(
        ["git", "-C", str(candidate_root), "status", "--porcelain=v1", "--untracked-files=all"],
        capture_output=True,
        text=True,
        check=False,
        env={"PATH": _clean_env({}).get("PATH", "/usr/bin:/bin")},
    )
    if proc.returncode != 0:
        raise LifecycleCanaryError("failed to observe git clean status")
    return (proc.stdout or "").strip()


def _snapshot_file_hashes(root: pathlib.Path, paths: Iterable[str]) -> Dict[str, str]:
    snapshot: Dict[str, str] = {}
    for path in paths:
        absolute = root / path
        if not absolute.exists() or not absolute.is_file():
            continue
        h = hashlib.sha256()
        with absolute.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                h.update(chunk)
        snapshot[path] = h.hexdigest()
    return snapshot


def _prepare_isolated_home(root: pathlib.Path, name: str) -> pathlib.Path:
    candidate = root / name
    candidate.mkdir(parents=True, exist_ok=True)
    os.chmod(candidate, 0o700)
    return candidate


def _build_sandbox(root: pathlib.Path) -> Dict[str, pathlib.Path]:
    home = _prepare_isolated_home(root, "home")
    hermes_home = _prepare_isolated_home(root, "hermes-home")
    restore_home = _prepare_isolated_home(root, "restore-home")
    tmpdir = _prepare_isolated_home(root, "tmp")
    archives = _prepare_isolated_home(root, "archives")
    sentinels = {
        "work_root": root / ".lifecycle-work-sentinel",
        "work_parent": root.parent / ".lifecycle-parent-sentinel",
        "work_sibling": root / ".lifecycle-sibling-sentinel",
    }

    sentinels["work_root"].touch()
    sentinels["work_root"].chmod(0o600)
    sentinels["work_parent"].touch()
    sentinels["work_parent"].chmod(0o600)
    sentinels["work_sibling"].touch()
    sentinels["work_sibling"].chmod(0o600)

    return {
        "home": home,
        "hermes_home": hermes_home,
        "restore_home": restore_home,
        "tmpdir": tmpdir,
        "archives": archives,
        "sentinel": sentinels,
    }


def _isolate_env(home: pathlib.Path, hermes_home: pathlib.Path, tmpdir: pathlib.Path, *, base: Mapping[str, str] | None = None) -> Dict[str, str]:
    env = _clean_env(base)
    env["HOME"] = str(home)
    env["HERMES_HOME"] = str(hermes_home)
    env["TMPDIR"] = str(tmpdir)
    return env


def _run_and_record_phase(
    action: str,
    result_tag: str,
    command: Sequence[str],
    env: Mapping[str, str],
    required: bool,
    phase_history: List[Dict[str, Any]],
) -> Dict[str, Any]:
    start = time.time()
    result = run_command(command, env=env)
    status = parse_phase_status(result)
    record = {
        "phase": action,
        "tag": result_tag,
        "status": status,
        "returncode": result["returncode"],
        "command_hash": result["stdout_hash"],
        "env": result.get("env", {}),
        "elapsed_seconds": result.get("elapsed_seconds", time.time() - start),
    }
    phase_history.append(record)
    if status != "ok":
        if required:
            raise LifecycleCanaryError(f"command failed for phase={action}:{result_tag}")
        raise LifecycleCanaryError(f"command optional phase failed for {action}:{result_tag}")
    return result


def _seed_update_drift(profile_root: pathlib.Path, source_profile: pathlib.Path) -> None:
    """Seed a controlled precondition; Hermes must produce every later effect."""
    _inject_drift(profile_root, source_profile)


def _snapshot_user_owned_state(profile_root: pathlib.Path) -> Dict[str, str]:
    """Return a byte-level snapshot of all declared user-owned artifacts."""
    owned = (
        "local", "memories", "sessions", "auth.json", ".env", "owner-config.yaml", "state.db",
        "logs", "cache", "gateway-state.json", "alias-map.json", "service-state.yaml",
        "unknown-root-artifact.txt",
    )
    snapshot: Dict[str, str] = {}
    for name in owned:
        item = profile_root / name
        if item.is_file():
            snapshot[name] = hashlib.sha256(item.read_bytes()).hexdigest()
        elif item.is_dir():
            for entry in sorted(item.rglob("*")):
                if entry.is_file():
                    relative = entry.relative_to(profile_root).as_posix()
                    snapshot[relative] = hashlib.sha256(entry.read_bytes()).hexdigest()
    if not snapshot:
        raise UnsafeInvocationError("controlled user-owned state is missing")
    return snapshot


def _seed_controlled_user_state(profile_root: pathlib.Path, profile: str) -> None:
    """Create deterministic owner fixtures only after observing a native install."""
    owned = (
        "local", "memories", "sessions", "auth.json", ".env", "owner-config.yaml", "state.db",
        "logs", "cache", "gateway-state.json", "alias-map.json", "service-state.yaml",
        "unknown-root-artifact.txt",
    )
    unexpected_user_state = [
        name for name in owned
        if (profile_root / name).exists()
        and not (
            name in NATIVE_BOOTSTRAP_DIRECTORIES
            and (profile_root / name).is_dir()
            and not (profile_root / name).is_symlink()
            and not any((profile_root / name).iterdir())
        )
    ]
    if unexpected_user_state:
        raise UnsafeInvocationError("install unexpectedly created declared user-owned state")
    fixtures = {
        "local/canary-state.json": f'{{"fixture":"portable-local","profile":"{profile}"}}\n',
        "memories/canary-note.txt": f"portable memory fixture for {profile}\n",
        "sessions/runtime-state.json": f'{{"fixture":"runtime","profile":"{profile}"}}\n',
        "auth.json": '{"identity":"synthetic-canary"}\n',
        ".env": "CANARY_FIXTURE=synthetic\n",
        "owner-config.yaml": "owner_override: synthetic-canary\n",
        "state.db": "synthetic database fixture\n",
        "logs/run.log": "synthetic log fixture\n",
        "cache/item.txt": "synthetic cache fixture\n",
        "gateway-state.json": "synthetic gateway fixture\n",
        "alias-map.json": "synthetic alias fixture\n",
        "service-state.yaml": "state: synthetic\n",
        "unknown-root-artifact.txt": "synthetic unknown root fixture\n",
    }
    for relative, content in fixtures.items():
        path = profile_root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    (profile_root / "portable-link-escape").symlink_to(profile_root.parent)


def _snapshot_portable_state(profile_root: pathlib.Path) -> Dict[str, str]:
    return _snapshot_file_hashes(profile_root, ("config.yaml", "local/canary-state.json", "memories/canary-note.txt"))


def _snapshot_portable_payload_state(profile_root: pathlib.Path) -> Dict[str, str]:
    snapshot: Dict[str, str] = {}
    for root in _PORTABLE_BACKUP_ROOTS:
        root_path = profile_root / root
        if not root_path.is_dir() or root_path.is_symlink():
            raise UnsafeInvocationError(f"portable backup root missing or unsafe: {root}")

        for entry in sorted(root_path.rglob("*")):
            if entry.is_symlink():
                rel = entry.relative_to(profile_root).as_posix()
                raise UnsafeInvocationError(f"portable backup contains unsafe symlink: {rel}")
            if not (entry.is_file() or entry.is_dir()):
                rel = entry.relative_to(profile_root).as_posix()
                raise UnsafeInvocationError(f"portable backup contains unsafe entry: {rel}")
            if entry.is_dir():
                continue
            rel = entry.relative_to(profile_root).as_posix()
            snapshot[rel] = hashlib.sha256(entry.read_bytes()).hexdigest()
    return snapshot


def _snapshot_portable_payload_from_archive(archive_path: pathlib.Path, profile: str) -> Dict[str, str]:
    snapshot: Dict[str, str] = {}
    profile_prefix = f"{profile}/"
    found_roots = set()

    with tarfile.open(archive_path, mode="r:*") as tar:
        for member in tar:
            name = validate_archive_member(member.name)
            if name == profile:
                continue
            if not name.startswith(profile_prefix):
                raise UnsafeInvocationError(f"archive member outside profile scope: {name}")
            relative = name[len(profile_prefix):]
            if not relative:
                continue
            root, _, _ = relative.partition("/")
            if root not in _PORTABLE_BACKUP_ROOTS:
                continue

            if not (member.isdir() or member.isfile()):
                raise UnsafeInvocationError(f"portable backup contains unsupported member type: {name}")
            if member.issym() or member.islnk():
                raise UnsafeInvocationError(f"portable backup contains link entry: {name}")

            found_roots.add(root)
            if not member.isfile():
                continue

            file_obj = tar.extractfile(member)
            if file_obj is None:
                raise UnsafeInvocationError(f"portable backup member read failed: {name}")
            digest = hashlib.sha256()
            while True:
                chunk = file_obj.read(65536)
                if not chunk:
                    break
                digest.update(chunk)
            file_obj.close()
            snapshot[relative] = digest.hexdigest()

    for required in _PORTABLE_BACKUP_ROOTS:
        if required not in found_roots:
            raise UnsafeInvocationError(f"portable backup missing expected root: {required}")
    return snapshot


def _snapshot_owned_payload(root: pathlib.Path, paths: Iterable[str]) -> Dict[str, str]:
    """Capture declared owned files and directories, requiring every declaration to exist."""
    snapshot: Dict[str, str] = {}
    for relative in paths:
        absolute = root / relative
        if not absolute.exists() or absolute.is_symlink():
            raise UnsafeInvocationError(f"declared distribution payload is missing or unsafe: {relative}")
        if absolute.is_file():
            snapshot[relative] = hashlib.sha256(absolute.read_bytes()).hexdigest()
            continue
        if not absolute.is_dir():
            raise UnsafeInvocationError(f"declared distribution payload is not regular: {relative}")
        snapshot[f"{relative.rstrip('/')}/"] = "directory"
        for entry in sorted(absolute.rglob("*")):
            entry_relative = entry.relative_to(root).as_posix()
            if entry.is_symlink() or not (entry.is_file() or entry.is_dir()):
                raise UnsafeInvocationError(f"declared distribution payload contains unsafe entry: {entry_relative}")
            if entry.is_dir():
                snapshot[f"{entry_relative}/"] = "directory"
            else:
                snapshot[entry_relative] = hashlib.sha256(entry.read_bytes()).hexdigest()
    return snapshot


def _assert_distribution_payload_matches(
    profile_root: pathlib.Path,
    source_profile: pathlib.Path,
    *,
    allowed_payload_extras: tuple[str, ...] = (),
) -> Dict[str, str]:
    source_manifest = _parse_distribution_manifest(source_profile / "distribution.yaml")
    installed_manifest = _parse_distribution_manifest(profile_root / "distribution.yaml")
    if set(source_manifest) != _SOURCE_MANIFEST_FIELDS:
        raise UnsafeInvocationError("source manifest has unauthorized fields")
    if set(installed_manifest) - (_SOURCE_MANIFEST_FIELDS | _INSTALLER_MANIFEST_FIELDS):
        raise UnsafeInvocationError("installed manifest has unauthorized fields")
    if not _INSTALLER_MANIFEST_FIELDS.issubset(installed_manifest):
        raise UnsafeInvocationError("installed manifest lacks required installer fields")
    _validate_installed_at(installed_manifest["installed_at"])
    for field in _SOURCE_MANIFEST_FIELDS:
        if installed_manifest[field] != source_manifest[field]:
            raise UnsafeInvocationError(f"installed manifest {field} does not match source contract")
    installed_source = pathlib.Path(str(installed_manifest.get("source", "")))
    if not installed_source.is_absolute() or installed_source.resolve() != source_profile.resolve():
        raise UnsafeInvocationError("installed manifest source does not identify the intended profile")

    owned = source_manifest["distribution_owned"]
    ordinary_owned = [path for path in owned if path != "distribution.yaml"]
    source = _snapshot_owned_payload(source_profile, ordinary_owned)
    installed = _snapshot_owned_payload(profile_root, ordinary_owned)
    if source != installed:
        raise UnsafeInvocationError("install distribution-owned payload does not match source")

    source_entries = {entry.relative_to(source_profile).as_posix() for entry in source_profile.rglob("*")}
    installed_entries = {entry.relative_to(profile_root).as_posix() for entry in profile_root.rglob("*")}
    source_owned_directories = {
        pathlib.PurePosixPath(path).parts[0]
        for path in ordinary_owned
        if (source_profile / pathlib.PurePosixPath(path).parts[0]).is_dir()
    }
    for name in NATIVE_BOOTSTRAP_DIRECTORIES:
        candidate = profile_root / name
        try:
            mode = os.lstat(candidate).st_mode
        except FileNotFoundError as error:
            raise UnsafeInvocationError("install is missing a native bootstrap directory") from error
        if stat.S_ISLNK(mode) or not stat.S_ISDIR(mode):
            raise UnsafeInvocationError("install bootstrap directory is not a real directory")
        if name in allowed_payload_extras:
            continue
        if name not in source_owned_directories and any(candidate.iterdir()):
            raise UnsafeInvocationError("install bootstrap directory is not empty")

    allowed = {
        *NATIVE_BOOTSTRAP_DIRECTORIES,
        *allowed_payload_extras,
    }

    def _is_allowed_payload(path: str) -> bool:
        if path in allowed:
            return True
        return any(path.startswith(f"{root}/") for root in allowed_payload_extras)

    extras = installed_entries - source_entries
    if any(not _is_allowed_payload(path) for path in extras):
        raise UnsafeInvocationError("install introduced unauthorized payload")
    for directory in extras:
        if any(directory == allowed or directory.startswith(f"{allowed}/") for allowed in allowed_payload_extras):
            if directory in allowed_payload_extras:
                mode = os.lstat(profile_root / directory).st_mode
                if stat.S_ISLNK(mode) or not stat.S_ISDIR(mode):
                    raise UnsafeInvocationError("install extra payload directory is invalid")
            continue
    for directory in extras & NATIVE_BOOTSTRAP_DIRECTORIES:
        if directory in allowed_payload_extras:
            continue
        candidate = profile_root / directory
        mode = os.lstat(candidate).st_mode
        if stat.S_ISLNK(mode) or not stat.S_ISDIR(mode) or any(candidate.iterdir()):
            raise UnsafeInvocationError("install bootstrap directory is not empty")
    return {**installed, "distribution.yaml": hashlib.sha256((profile_root / "distribution.yaml").read_bytes()).hexdigest()}


def _assert_excluded_state_absent(profile_root: pathlib.Path) -> None:
    excluded = (
        "sessions", "auth.json", ".env", "owner-config.yaml", "state.db", "logs", "cache",
        "gateway-state.json", "alias-map.json", "service-state.yaml", "unknown-root-artifact.txt",
        "portable-link-escape",
    )
    present: list[str] = []
    for name in excluded:
        candidate = profile_root / name
        if candidate.is_symlink():
            present.append(name)
            continue
        if not candidate.exists():
            continue
        if candidate.is_dir() and any(candidate.iterdir()):
            present.append(name)
        if candidate.is_file():
            present.append(name)
    if present:
        raise UnsafeInvocationError(f"restore includes excluded owner state: {present}")


def _stale_profile_files(profile_root: pathlib.Path) -> None:
    stale_dir = profile_root / "skills"
    stale_dir.mkdir(parents=True, exist_ok=True)
    (stale_dir / "stale-skill.md").write_text("stale", encoding="utf-8")


def _inject_drift(profile_root: pathlib.Path, source_profile: pathlib.Path) -> None:
    config = profile_root / "config.yaml"
    if config.exists():
        config.write_text((config.read_text(encoding="utf-8") + "\n# drift\n"), encoding="utf-8")
    else:
        source_config = source_profile / "config.yaml"
        if source_config.exists():
            config.write_text((source_config.read_text(encoding="utf-8") + "\n# drift\n"), encoding="utf-8")

    candidate_home = profile_root / "candidate-owned"
    candidate_home.mkdir(parents=True, exist_ok=True)
    (candidate_home / "ownership.hash").write_text(
        hashlib.sha256(b"drift").hexdigest(),
        encoding="utf-8",
    )
    _stale_profile_files(profile_root)


SENSITIVE_NAME_TOKENS = (
    "auth", "se" "cret", "token", "pass" "word", "pass" "wd",
    "credential", "api" "_key", "access" "_key", "private" "_key",
    "provider", "aws", "azure", "gcp", "cloud", ".env",
    "gateway", "alias", "service",
)
SECRET_CONTENT_FIELD_TOKENS = SENSITIVE_NAME_TOKENS[:-3]


def _verify_no_secret_names(profile_root: pathlib.Path) -> bool:
    fields = tuple(re.escape(value) for value in SECRET_CONTENT_FIELD_TOKENS if value != ".env")
    expression = r"(?im)^\s*(?:" + "|".join(fields) + r")(?:[_-][A-Z0-9_-]+)?\s*[:=]"
    for path in profile_root.rglob("*"):
        if not path.is_file():
            continue
        lowered = [part.lower() for part in path.parts]
        if any(token in part for part in lowered for token in SENSITIVE_NAME_TOKENS):
            return False
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if re.search(expression, text):
            return False
    return True


def _assert_secret_exclusion_in_tar(member_names: Iterable[str]) -> bool:
    for member in member_names:
        lower = member.lower()
        if any(token in part for token in SENSITIVE_NAME_TOKENS for part in pathlib.PurePosixPath(lower).parts):
            return False
    return True


_PORTABLE_BACKUP_ROOTS = ("local", "memories")


def _collect_portable_members(profile_root: pathlib.Path) -> list[tuple[pathlib.Path, str, bool]]:
    members: list[tuple[pathlib.Path, str, bool]] = [(profile_root, "", True)]
    seen_inodes: set[tuple[int, int]] = set()

    for root_name in _PORTABLE_BACKUP_ROOTS:
        root = profile_root / root_name
        if not root.exists():
            raise UnsafeInvocationError(f"portable backup root missing: {root_name}")
        mode = os.lstat(root)
        if stat.S_ISLNK(mode.st_mode):
            raise UnsafeInvocationError(f"portable backup root is symlink: {root_name}")
        if not stat.S_ISDIR(mode.st_mode):
            raise UnsafeInvocationError(f"portable backup root is not a directory: {root_name}")
        members.append((root, f"{root_name}", True))
        for source in sorted(root.rglob("*"), key=lambda item: item.as_posix()):
            stat_result = os.lstat(source)
            if stat.S_ISLNK(stat_result.st_mode):
                raise UnsafeInvocationError(f"portable backup entry is symlink: {source}")
            if not (stat.S_ISREG(stat_result.st_mode) or stat.S_ISDIR(stat_result.st_mode)):
                raise UnsafeInvocationError(f"portable backup entry has unsupported type: {source}")
            if stat_result.st_nlink > 1:
                raise UnsafeInvocationError(f"portable backup entry is hard-linked: {source}")
            entry_key = (stat_result.st_dev, stat_result.st_ino)
            if stat.S_ISREG(stat_result.st_mode):
                if entry_key in seen_inodes:
                    raise UnsafeInvocationError(f"portable backup entry has duplicate inode: {source}")
                seen_inodes.add(entry_key)
            relative = source.relative_to(profile_root).as_posix()
            members.append((source, f"{relative}", stat.S_ISDIR(stat_result.st_mode)))
    ordered: list[tuple[pathlib.Path, str, bool]] = []
    for source, arcname, is_dir in sorted(members, key=lambda item: item[1]):
        ordered.append((source, arcname, is_dir))
    return ordered


def _create_profile_archive(profile_root: pathlib.Path, destination: pathlib.Path, *, profile: str) -> list[str]:
    destination = validate_path_no_follow(destination)
    members = _collect_portable_members(profile_root)
    destination.parent.mkdir(parents=True, exist_ok=True)

    def _safe_tarinfo(path: pathlib.Path, arcname: str, *, is_dir: bool) -> tarfile.TarInfo:
        info = tarfile.TarInfo(arcname)
        info.uid = 0
        info.gid = 0
        info.uname = ""
        info.gname = ""
        info.mtime = 0
        if is_dir:
            info.type = tarfile.DIRTYPE
            info.mode = 0o755
            info.size = 0
            return info
        info.type = tarfile.REGTYPE
        info.mode = 0o644
        info.size = path.stat().st_size
        return info

    member_names: list[str] = [f"{profile}" if arcname == "" else f"{profile}/{arcname}" for _, arcname, _ in members]
    with destination.open("wb") as output:
        with gzip.GzipFile(fileobj=output, mode="wb", compresslevel=9, mtime=0) as gz:
            with tarfile.open(fileobj=gz, mode="w|") as tar:
                for source, arcname, is_dir in members:
                    target_name = f"{profile}" if arcname == "" else f"{profile}/{arcname}"
                    tarinfo = _safe_tarinfo(source, target_name, is_dir=is_dir)
                    if is_dir:
                        tar.addfile(tarinfo)
                        continue
                    with source.open("rb") as handle:
                        tar.addfile(tarinfo, handle)
    return member_names


def _validate_export_archive(
    archive: str | os.PathLike[str],
    *,
    expected_profile: str | None = None,
) -> List[str]:
    archive_path = validate_path_no_follow(archive)
    if not archive_path.is_file():
        raise ValueError("archive path not a file")

    members: List[str] = []
    seen: set[str] = set()
    try:
        with tarfile.open(archive_path, mode="r:*") as tar:
            for item in tar:
                validate_archive_member(item.name)
                if item.name in seen:
                    raise ValueError(f"duplicate archive member: {item.name}")
                seen.add(item.name)
                if item.issym() or item.islnk() or item.isdev() or item.ischr() or item.isblk() or item.isfifo():
                    raise ValueError("unsupported archive member type")
                if not (item.isfile() or item.isdir()):
                    raise ValueError("unsupported archive member type")
                members.append(item.name)
    except (tarfile.TarError, OSError, ValueError) as exc:
        if isinstance(exc, ValueError):
            raise
        raise ValueError("archive unreadable") from exc

    if expected_profile is not None:
        if expected_profile not in members:
            raise ValueError("archive does not include expected profile root")
        if any(
            "/" not in name and name != expected_profile
            for name in members
        ):
            raise ValueError("archive contains members outside expected profile root")
        required = {f"{expected_profile}/local", f"{expected_profile}/memories"}
        if not required.issubset(set(members)):
            raise ValueError(f"portable archive for {expected_profile} missing required portable roots: {sorted(required)}")

    return members


def run_host_canary(*, root: str, candidate_head: str, hermes: str, work_root: str, evidence: str,
                   hermes_version: str = CANARY_LIMITS["required_hermes_version"],
                   hermes_python: str = "",
                   dry_run: bool = False,
                   execute: bool = False,
                   ) -> Dict[str, Any]:
    root_path = validate_path_no_follow(root)
    hermes_path = validate_path_no_follow(hermes)
    hermes_py_path = pathlib.Path(hermes_python) if hermes_python else None
    observed_hermes_version = _observe_hermes_version(hermes_path)
    if observed_hermes_version != CANARY_LIMITS["required_hermes_version"]:
        raise UnsafeInvocationError(
            f"hermes version mismatch (observed={observed_hermes_version}, expected={CANARY_LIMITS['required_hermes_version']})"
        )
    if hermes_version != observed_hermes_version:
        raise UnsafeInvocationError("hermes version argument is inconsistent with observed version")

    observed_head = _observe_head(root_path)
    validate_candidate_head(observed_head, candidate_head)
    work_tree = validate_work_root(str(root_path), work_root)

    if _observe_clean_status(root_path) != "":
        raise UnsafeInvocationError("candidate workspace is not clean")

    candidate_profile_map = scan_candidate_profiles(root_path)
    validate_candidate_profiles(list(candidate_profile_map.keys()))

    inventory_before = compute_candidate_inventory(root_path)

    if dry_run and not execute:
        phase_history: List[Dict[str, Any]] = [
            {
                "phase": "preflight",
                "status": "ok",
                "reason": "dry-run mode selected",
            }
        ]
        claims = _build_claim_map()
        claims["all_claims"] = False
        receipt = build_receipt(
            mode="host",
            status="dry_run",
            candidate_head=candidate_head,
            root=str(root_path),
            hermes_version=observed_hermes_version,
            work_root=str(work_tree),
            phase_history=phase_history,
            inventory_before=inventory_before,
            inventory_after=inventory_before,
            candidate_profiles=CANDIDATE_PROFILES,
            flags={
                "execution_mode": "dry-run",
                "observed_head": observed_head,
            },
            claims=claims,
            changed_paths=[],
        )
        receipt = tokenize_receipt_paths(receipt, candidate_root=str(root_path), work_root=str(work_tree))
        write_json_receipt_atomically(evidence, receipt)
        return receipt

    sandbox = _build_sandbox(work_tree)
    phase_history = []
    claims = _build_claim_map()
    changed_paths: list[str] = []
    primary_error: Exception | None = None
    cleanup_errors: list[str] = []
    installed_profiles: Dict[str, pathlib.Path] = {}
    profile_payload_trees: Dict[str, str] = {}
    archive_members: Dict[str, List[str]] = {}
    archive_records: Dict[str, Dict[str, Any]] = {}
    archive_portable_hashes: Dict[str, Dict[str, str]] = {}
    env: Dict[str, str] = {}

    try:
        claim_ok = True

        env = _isolate_env(
            sandbox["home"],
            sandbox["hermes_home"],
            sandbox["tmpdir"],
            base={"CANARY_WORK_ROOT": str(work_tree), "CANARY_ROOT": str(root_path)},
        )
        claims["workspaces_isolated"] = True

        user_snapshots: Dict[str, Dict[str, str]] = {}

        # Exact five native local-directory installs, no alias or shell indirection.
        for profile in CANDIDATE_PROFILES:
            source_profile = root_path / CANARY_LIMITS["candidate_profile_prefix"] / profile
            command = build_profile_command("install", str(source_profile), str(hermes_path), ["--yes"])
            profile_root = sandbox["hermes_home"] / "profiles" / profile
            installed_profiles[profile] = profile_root
            _run_and_record_phase("install", profile, command, env, True, phase_history)
            if not profile_root.is_dir():
                raise UnsafeInvocationError("install command reported success without creating profile")
            distribution_payload = _assert_distribution_payload_matches(profile_root, source_profile)
            _seed_controlled_user_state(profile_root, profile)
            user_snapshots[profile] = _snapshot_user_owned_state(profile_root)
            profile_payload_trees[profile] = hashlib.sha256(
                json.dumps(distribution_payload, sort_keys=True).encode()
            ).hexdigest()
            changed_paths.append(profile_root.relative_to(work_tree).as_posix())
        claims["exact_five_installs"] = True

        # baseline + drift + update/f-config for each profile
        for profile in CANDIDATE_PROFILES:
            source_profile = root_path / CANARY_LIMITS["candidate_profile_prefix"] / profile
            profile_root = installed_profiles[profile]
            source_data = source_profile

            _seed_update_drift(profile_root, source_data)
            _run_and_record_phase(
                "update",
                profile,
                build_profile_command("update", profile, str(hermes_path), ["--yes"]),
                env,
                True,
                phase_history,
            )
            before_user = user_snapshots[profile]
            after_user = _snapshot_user_owned_state(profile_root)
            if before_user != after_user:
                claim_ok = False
                raise UnsafeInvocationError("user-owned state changed during ordinary update")
            if (profile_root / "skills" / "stale-skill.md").exists():
                claim_ok = False
                raise UnsafeInvocationError("stale candidate skill survived update")

            _seed_update_drift(profile_root, source_data)
            _run_and_record_phase(
                "force",
                profile,
                build_profile_command("update", profile, str(hermes_path), ["--force-config", "--yes"]),
                env,
                True,
                phase_history,
            )
            candidate_config = (source_profile / "config.yaml").read_text(encoding="utf-8") if (source_profile / "config.yaml").exists() else ""
            live_config = (profile_root / "config.yaml").read_text(encoding="utf-8") if (profile_root / "config.yaml").exists() else ""
            if candidate_config != live_config:
                claim_ok = False
                raise UnsafeInvocationError("force-config update did not restore candidate config")
            after_user_after_force = _snapshot_user_owned_state(profile_root)
            if before_user != after_user_after_force:
                claim_ok = False
                raise UnsafeInvocationError("user-owned data changed during force-config update")
        claims["update_preserves_user_data"] = True
        claims["force_config_restore"] = True

        claims["archive_safety"] = True

        archive_paths: List[pathlib.Path] = []
        for profile in CANDIDATE_PROFILES:
            profile_root = installed_profiles[profile]
            archive_path = sandbox["archives"] / f"{profile}.tar.gz"
            members = _create_profile_archive(profile_root, archive_path, profile=profile)
            if not archive_path.is_file():
                raise UnsafeInvocationError("portable archive build failed")

            members = validate_export_archive(archive_path, expected_profile=profile)
            phase_history.append(
                {
                    "phase": "archive",
                    "tag": profile,
                    "status": "ok",
                    "returncode": 0,
                    "command_hash": hashlib.sha256(archive_path.read_bytes()).hexdigest(),
                    "env": {},
                    "elapsed_seconds": 0.0,
                }
            )
            if not _assert_secret_exclusion_in_tar(members):
                raise UnsafeInvocationError("archive secret/member exclusion failed")
            archive_portable_hashes[profile] = _snapshot_portable_payload_from_archive(archive_path, profile)
            archive_members[profile] = members
            archive_paths.append(archive_path)
            changed_paths.append(str(archive_path))
            record_digest = hashlib.sha256(archive_path.read_bytes()).hexdigest()
            archive_records[profile] = {
                "filename": archive_path.name,
                "sha256": record_digest,
                "members": members,
                "member_count": len(members),
            }
            claims["portable_backup_created"] = True

        restore_env = _isolate_env(
            sandbox["home"],
            sandbox["restore_home"],
            sandbox["tmpdir"],
            base={"CANARY_WORK_ROOT": str(work_tree), "CANARY_ROOT": str(root_path)},
        )
        if hermes_py_path and not hermes_py_path.is_file():
            raise UnsafeInvocationError("provided Hermes Python is not a regular file")

        for profile, archive_path in zip(CANDIDATE_PROFILES, archive_paths):
            command = build_profile_command(
                "import", str(archive_path), str(hermes_path), ["--name", profile]
            )
            _run_and_record_phase("import", profile, command, restore_env, True, phase_history)

        claims["restore_uses_native_profile_import"] = True

        for profile in CANDIDATE_PROFILES:
            restore_profile_root = sandbox["restore_home"] / "profiles" / profile
            if not restore_profile_root.exists():
                raise UnsafeInvocationError("import command reported success without restored profile")

            command = [
                str(hermes_path),
                "profile",
                "install",
                str(root_path / CANARY_LIMITS["candidate_profile_prefix"] / profile),
                "--name",
                profile,
                "--force",
                "--yes",
            ]
            _run_and_record_phase("reinstall", profile, command, restore_env, True, phase_history)

            if not restore_profile_root.exists():
                raise UnsafeInvocationError("install reconstruction reported success without restored profile")
            source_profile = root_path / CANARY_LIMITS["candidate_profile_prefix"] / profile
            _assert_distribution_payload_matches(
                restore_profile_root,
                source_profile,
                allowed_payload_extras=("local", "memories"),
            )

        for profile in CANDIDATE_PROFILES:
            source_profile = root_path / CANARY_LIMITS["candidate_profile_prefix"] / profile
            restore_profile_root = sandbox["restore_home"] / "profiles" / profile
            if not _verify_no_secret_names(restore_profile_root):
                raise UnsafeInvocationError("restore introduced secret-like or forbidden artifacts")
            for required in ["local", "memories"]:
                required_path = restore_profile_root / required
                if not required_path.exists():
                    raise UnsafeInvocationError(f"restore missing {required} for {profile}")
            _assert_excluded_state_absent(restore_profile_root)
            if _snapshot_portable_payload_state(restore_profile_root) != archive_portable_hashes[profile]:
                raise UnsafeInvocationError(f"restored portable bytes mismatch for {profile}")
            if (source_profile / "config.yaml").exists():
                candidate_config = (source_profile / "config.yaml").read_text(encoding="utf-8")
                restored_config = (restore_profile_root / "config.yaml").read_text(encoding="utf-8") if (restore_profile_root / "config.yaml").exists() else ""
                if candidate_config != restored_config:
                    raise UnsafeInvocationError(f"restored config mismatch for {profile}")

        claims["portable_profile_reinstalled"] = True
        claims["restore_reinstall_works"] = True

        claims["restore_isolated"] = True

        for profile in CANDIDATE_PROFILES:
            command = build_profile_command("delete", profile, str(hermes_path), ["--yes"])
            _run_and_record_phase("delete", profile, command, env, True, phase_history)
            target = sandbox["hermes_home"] / "profiles" / profile
            if target.exists():
                raise UnsafeInvocationError("delete command reported success without removing profile")

        installed_profiles_set = set(item.name for item in (sandbox["hermes_home"] / "profiles").iterdir() if item.is_dir())
        remaining = validate_uninstall_targets(installed_profiles_set, CANDIDATE_PROFILES)
        if remaining:
            raise UnsafeInvocationError(f"unexpected profiles remain after delete: {sorted(remaining)}")
        claims["delete_target_only"] = True

        inventory_after = compute_candidate_inventory(root_path)
        if inventory_before["tree"] != inventory_after["tree"]:
            raise UnsafeInvocationError("candidate source inventory changed")
        claims["candidate_inventory_unchanged"] = True

        # ensure export artifacts remain after delete
        for path in [sandbox["archives"], *sandbox["sentinel"].values(), sandbox["home"], sandbox["restore_home"]]:
            if not path.exists():
                raise LifecycleCanaryError("work-root artifacts missing after run")

        changed_paths.extend(str(path) for path in sandbox["sentinel"].values())
        claim_ok = True

        if claim_ok:
            claims["secrets_excluded"] = True
            claims["all_claims"] = True

    except Exception as exc:
        primary_error = exc
        claims["all_claims"] = False
        raise
    finally:
        if primary_error is not None:
            for profile, target in installed_profiles.items():
                if not target.exists():
                    continue
                command = build_profile_command("delete", profile, str(hermes_path), ["--yes"])
                try:
                    result = run_command(command, env=env)
                    phase_history.append(
                        {
                            "phase": "cleanup-delete",
                            "tag": profile,
                            "status": parse_phase_status(result),
                            "returncode": result["returncode"],
                            "command_hash": result["stdout_hash"],
                            "env": result.get("env", {}),
                            "elapsed_seconds": result.get("elapsed_seconds", 0),
                        }
                    )
                    if result["returncode"] != 0 or target.exists():
                        cleanup_errors.append(f"cleanup delete failed for {profile}")
                except Exception as cleanup_exc:
                    cleanup_errors.append(f"cleanup delete error for {profile}: {type(cleanup_exc).__name__}")
            for sentinel in sandbox["sentinel"].values():
                if not sentinel.exists():
                    cleanup_errors.append("outside-isolation sentinel missing")
            failure_receipt = build_receipt(
                mode="host",
                status="failed",
                candidate_head=candidate_head,
                root=str(root_path),
                hermes_version=observed_hermes_version,
                work_root=str(work_tree),
                phase_history=phase_history,
                inventory_before=inventory_before,
                inventory_after=compute_candidate_inventory(root_path),
                candidate_profiles=CANDIDATE_PROFILES,
                flags={
                    "execution_mode": "execute",
                    "primary_error": type(primary_error).__name__,
                    "cleanup_errors": cleanup_errors,
                    "archive_records": archive_records,
                },
                claims=claims,
                changed_paths=changed_paths,
            )
            try:
                write_json_receipt_atomically(
                    evidence,
                    tokenize_receipt_paths(
                        failure_receipt,
                        candidate_root=str(root_path),
                        work_root=str(work_tree),
                        hermes_home=str(sandbox["hermes_home"]),
                        home=str(sandbox["home"]),
                    ),
                )
            except Exception as receipt_exc:
                cleanup_errors.append(f"failure receipt error: {type(receipt_exc).__name__}")

    receipt = build_receipt(
        mode="host",
        status="passed" if claims["all_claims"] else "failed",
        candidate_head=candidate_head,
        root=str(root_path),
        hermes_version=observed_hermes_version,
        work_root=str(work_tree),
        phase_history=phase_history,
        inventory_before=inventory_before,
        inventory_after=compute_candidate_inventory(root_path),
        candidate_profiles=CANDIDATE_PROFILES,
        flags={
            "observed_head": observed_head,
            "profile_payload_trees": profile_payload_trees,
            "archive_members": archive_members,
            "archive_records": archive_records,
            "execution_mode": "execute",
        },
        claims=claims,
        changed_paths=changed_paths,
    )
    receipt = tokenize_receipt_paths(
        receipt,
        candidate_root=str(root_path),
        work_root=str(work_tree),
        hermes_home=str(sandbox["hermes_home"]),
        home=str(sandbox["home"]),
    )
    write_json_receipt_atomically(evidence, receipt)
    return receipt


def _read_json_payload(path: str | os.PathLike[str]) -> Dict[str, Any]:
    payload_path = validate_path_no_follow(str(path))
    try:
        data = json.loads(payload_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise LifecycleCanaryError(f"receipt file invalid: {type(exc).__name__}") from exc
    if not isinstance(data, dict):
        raise ValueError("receipt payload must be a JSON object")
    return data


def _validate_host_receipt_for_docker(*, payload: Mapping[str, Any], candidate_head: str) -> Mapping[str, Any]:
    if payload.get("mode") != "host":
        raise ValueError("host receipt mode mismatch")
    if payload.get("status") != "passed":
        raise ValueError("host receipt status must be passed")
    if payload.get("candidate_head") != candidate_head:
        raise ValueError("host receipt candidate head mismatch")
    if payload.get("hermes_version") != CANARY_LIMITS["required_hermes_version"]:
        raise ValueError("host receipt hermes version mismatch")

    claims = payload.get("claims")
    if not isinstance(claims, Mapping):
        raise ValueError("host receipt claims missing")
    if claims.get("all_claims") is not True:
        raise ValueError("host receipt must be all_claims=true")
    if claims.get("secrets_excluded") is not True:
        raise ValueError("host receipt must prove secrets excluded")

    flags = payload.get("flags")
    if not isinstance(flags, Mapping):
        raise ValueError("host receipt flags missing")

    archive_records = flags.get("archive_records")
    if not isinstance(archive_records, Mapping):
        raise ValueError("host receipt archive index missing")

    archive_keys = set(archive_records.keys())
    if archive_keys != set(CANDIDATE_PROFILES):
        raise ValueError("host receipt archive profile key set mismatch")

    normalized_records: Dict[str, Dict[str, Any]] = {}
    for profile in CANDIDATE_PROFILES:
        raw = archive_records.get(profile)
        if not isinstance(raw, Mapping):
            raise ValueError(f"host receipt missing archive record for {profile}")
        filename = raw.get("filename")
        digest = raw.get("sha256")
        members = raw.get("members")
        member_count = raw.get("member_count")
        if not isinstance(filename, str) or not filename:
            raise ValueError(f"host receipt archive filename missing for {profile}")
        if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise ValueError(f"host receipt archive digest missing for {profile}")
        if not isinstance(member_count, int) or member_count < 0:
            raise ValueError(f"host receipt archive member_count missing/invalid for {profile}")
        if not isinstance(members, list) or not all(isinstance(item, str) for item in members):
            raise ValueError(f"host receipt archive member list invalid for {profile}")
        if member_count != len(members):
            raise ValueError(f"host receipt archive member_count mismatch for {profile}")
        normalized_records[profile] = {
            "filename": filename,
            "sha256": digest,
            "member_count": member_count,
            "members": list(members),
        }

    inventory_before = payload.get("inventory_before")
    if not isinstance(inventory_before, Mapping):
        raise ValueError("host receipt inventory_before missing")
    normalized_inventory_before = _canonicalize_inventory_for_docker(inventory_before)

    inventory_after = payload.get("inventory_after")
    if not isinstance(inventory_after, Mapping):
        raise ValueError("host receipt inventory_after missing")
    normalized_inventory_after = _canonicalize_inventory_for_docker(inventory_after)

    return {
        "archive_records": normalized_records,
        "status": payload.get("status"),
        "mode": payload.get("mode"),
        "candidate_head": payload.get("candidate_head"),
        "claims": dict(claims),
        "inventory_before": normalized_inventory_before,
        "inventory_after": normalized_inventory_after,
    }


def _copy_and_validate_host_archives(*, source_root: pathlib.Path, destination_root: pathlib.Path,
                                   archive_records: Mapping[str, Mapping[str, Any]]) -> tuple[
                                       Dict[str, str],
                                       Dict[str, List[str]],
                                       Dict[str, Dict[str, str]],
                                       List[str],
                                   ]:
    destination_root.mkdir(parents=True, exist_ok=True)
    copied_hashes: Dict[str, str] = {}
    copied_members: Dict[str, List[str]] = {}
    copied_portable_hashes: Dict[str, Dict[str, str]] = {}
    copied_paths: List[str] = []

    for profile in CANDIDATE_PROFILES:
        record = archive_records.get(profile, {})
        filename = record.get("filename")
        expected_hash = record.get("sha256")
        expected_members = record.get("members", [])
        source_path = source_root / str(filename)
        if not source_path.is_file():
            raise UnsafeInvocationError(f"missing host archive {source_path}")

        destination_path = destination_root / str(filename)
        shutil.copy2(source_path, destination_path)
        digest = hashlib.sha256(destination_path.read_bytes()).hexdigest()
        if digest != expected_hash:
            raise UnsafeInvocationError(f"host archive checksum mismatch for {profile}")

        members = validate_export_archive(destination_path, expected_profile=profile)
        if sorted(members) != sorted(expected_members):
            raise UnsafeInvocationError(f"host archive members mismatch for {profile}")
        if not _assert_secret_exclusion_in_tar(members):
            raise UnsafeInvocationError(f"host archive contains forbidden artifact names for {profile}")

        copied_portable_hashes[profile] = _snapshot_portable_payload_from_archive(destination_path, profile)

        copied_hashes[profile] = digest
        copied_members[profile] = members
        copied_paths.append(str(destination_path))

    return (
        copied_hashes,
        {k: v[:] for k, v in copied_members.items()},
        {k: dict(v) for k, v in copied_portable_hashes.items()},
        copied_paths,
    )


def _path_owner_identity(path: os.PathLike[str] | str) -> tuple[int, int]:
    st = os.lstat(pathlib.Path(path))
    return (st.st_uid, st.st_gid)


def _canonicalize_inventory_for_docker(inventory: Mapping[str, Any]) -> Dict[str, Any]:
    if not isinstance(inventory.get("root"), str):
        raise ValueError("inventory root missing")
    if not isinstance(inventory.get("tree"), str):
        raise ValueError("inventory tree missing")

    entry_count = inventory.get("entry_count")
    if not isinstance(entry_count, int):
        raise ValueError("inventory entry_count invalid")

    raw_entries = inventory.get("entries")
    if not isinstance(raw_entries, list):
        raise ValueError("inventory entries missing")

    normalized_entries: List[Dict[str, Any]] = []
    for entry in raw_entries:
        if not isinstance(entry, Mapping):
            raise ValueError("invalid inventory entry")
        path = entry.get("path")
        size = entry.get("size")
        digest = entry.get("sha256")
        if not isinstance(path, str):
            raise ValueError("inventory entry path invalid")
        if not isinstance(size, int):
            raise ValueError("inventory entry size invalid")
        if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise ValueError("inventory entry hash invalid")
        normalized_entries.append({"path": path, "size": size, "sha256": digest})

    normalized_entries.sort(key=lambda item: (item["path"], item["size"], item["sha256"]))

    if entry_count != len(normalized_entries):
        raise ValueError("inventory entry_count mismatch")

    normalized: Dict[str, Any] = dict(inventory)
    normalized["root"] = "<candidate_root>"
    normalized["entries"] = normalized_entries
    normalized["entry_count"] = entry_count
    return normalized


def run_docker_canary(*, root: str, candidate_head: str, image: str, work_root: str,
                    host_work_root: str, host_receipt: str, host_archives: str, evidence: str,
                    hermes_version: str = CANARY_LIMITS["required_hermes_version"],
                    dry_run: bool = False,
                    execute: bool = False) -> Dict[str, Any]:
    root_path = validate_path_no_follow(root)
    work_tree = validate_work_root(str(root_path), work_root)
    host_receipt_path = validate_path_no_follow(host_receipt)
    host_work_root_path = validate_path_no_follow(host_work_root)
    host_archive_root = validate_path_no_follow(host_archives)
    evidence_path = validate_path_no_follow(evidence)

    if hermes_version != CANARY_LIMITS["required_hermes_version"]:
        raise UnsafeInvocationError("hermes version argument is inconsistent with required version")

    validated_image = validate_docker_image_reference(image)
    observed_head = _observe_head(root_path)
    validate_candidate_head(observed_head, candidate_head)
    if _observe_clean_status(root_path) != "":
        raise UnsafeInvocationError("candidate workspace is not clean")

    host_payload = _read_json_payload(host_receipt_path)
    normalized_host = _validate_host_receipt_for_docker(
        payload=host_payload,
        candidate_head=candidate_head,
    )
    host_receipt_sha256 = hashlib.sha256(host_receipt_path.read_bytes()).hexdigest()

    if dry_run:
        receipt = build_receipt(
            mode="docker",
            status="dry_run",
            candidate_head=candidate_head,
            root=str(root_path),
            hermes_version=CANARY_LIMITS["required_hermes_version"],
            work_root=str(work_tree),
            phase_history=[{"phase": "preflight", "status": "ok", "tag": "controller"}],
            flags={
                "reason": "dry-run mode selected",
                "image": validated_image,
                "host_receipt_sha256": host_receipt_sha256,
                "host_receipt_path": str(host_receipt_path),
                "host_work_root": str(host_work_root_path),
                "host_archives": str(host_archive_root),
                "execution_mode": "dry-run",
            },
            claims=_build_claim_map(),
            changed_paths=[str(host_receipt_path)],
        )
        receipt = tokenize_receipt_paths(
            receipt,
            candidate_root=str(root_path),
            work_root=str(work_tree),
            hermes_home=str(host_work_root_path),
            home=str(host_work_root_path),
        )
        write_json_receipt_atomically(evidence, receipt)
        return receipt

    if not execute:
        raise UnsafeInvocationError("execution requested flag missing")

    host_receipt_owner = _path_owner_identity(host_receipt_path)
    if evidence_path.exists():
        evidence_owner = _path_owner_identity(evidence_path)
        if evidence_owner != host_receipt_owner:
            raise UnsafeInvocationError("host evidence owner mismatch")

    host_archive_owner = _path_owner_identity(host_archive_root)
    host_work_root_owner = _path_owner_identity(host_work_root_path)
    if host_receipt_owner != host_archive_owner or host_receipt_owner != host_work_root_owner:
        raise UnsafeInvocationError("host archive/work root owner mismatch")

    if not host_work_root_path.is_dir():
        raise UnsafeInvocationError("host work root must be a directory")
    if not host_archive_root.is_dir():
        raise UnsafeInvocationError("host archive directory must be a directory")

    user = f"{host_receipt_owner[0]}:{host_receipt_owner[1]}"

    worker_receipt_path = pathlib.Path(work_tree) / "docker-worker-receipt.json"

    command = build_docker_run_args(
        image=validated_image,
        network="none",
        read_only=True,
        no_new_privileges=True,
        cap_drop=["ALL"],
        volumes=[
            (str(root_path), "/candidate:ro"),
            (str(host_receipt_path), "/candidate-host/receipt.json:ro"),
            (str(host_archive_root), "/candidate-host/archives:ro"),
            (str(work_tree), "/tmp/candidate-work:rw"),
        ],
        env={
            "PATH": "/usr/bin:/bin",
            "HOME": "/tmp/home",
            "TMPDIR": "/tmp",
        },
        tmpfs="/tmp:rw,noexec,nosuid,nodev,size=64m",
        pids_limit=128,
        memory_limit="768m",
        cpus="1.0",
        user=user,
    )

    command.extend([
        "/usr/local/bin/python",
        "/candidate/scripts/lifecycle_canary.py",
        "_worker",
        "--mode",
        "docker",
        "--root",
        "/candidate",
        "--candidate-head",
        candidate_head,
        "--input-receipt",
        "/candidate-host/receipt.json",
        "--host-archives",
        "/candidate-host/archives",
        "--work-root",
        "/tmp/candidate-work",
        "--evidence",
        "/tmp/candidate-work/docker-worker-receipt.json",
        "--hermes-version",
        CANARY_LIMITS["required_hermes_version"],
        "--hermes",
        "/usr/local/bin/hermes",
        "--execute",
    ])

    phase_history = [{"phase": "docker-controller", "status": "ok", "tag": validated_image}]
    container_result = run_command(command)
    phase_history.append({
        "phase": "docker-controller",
        "status": parse_phase_status(container_result),
        "returncode": container_result["returncode"],
        "command_hash": container_result["stdout_hash"],
        "env": container_result.get("env", {}),
        "elapsed_seconds": container_result.get("elapsed_seconds", 0),
    })
    if container_result["returncode"] != 0:
        raise LifecycleCanaryError("docker container execution failed")

    if not worker_receipt_path.is_file():
        raise LifecycleCanaryError("worker receipt missing")

    worker_payload = _read_json_payload(worker_receipt_path)
    if worker_payload.get("mode") != "docker":
        raise LifecycleCanaryError("worker receipt mode mismatch")
    if worker_payload.get("status") != "passed":
        raise LifecycleCanaryError("worker receipt did not pass")
    worker_claims = worker_payload.get("claims")
    if not isinstance(worker_claims, Mapping) or worker_claims.get("all_claims") is not True:
        raise LifecycleCanaryError("worker receipt all_claims is false")

    flags = worker_payload.get("flags", {})
    if not isinstance(flags, Mapping):
        flags = {}
    phase_history.extend(worker_payload.get("phase_history", []))

    receipt_flags: Dict[str, Any] = {
        "image_id": validated_image,
        "host_receipt_sha256": host_receipt_sha256,
        "host_receipt_mode": normalized_host["mode"],
        "host_receipt_status": normalized_host["status"],
        "host_archive_hashes": dict(normalized_host["archive_records"]),
        "host_receipt_claims": normalized_host["claims"],
        "worker_receipt_hash": hashlib.sha256(worker_receipt_path.read_bytes()).hexdigest(),
        "execution_mode": "execute",
    }
    receipt = build_receipt(
        mode="docker",
        status="passed",
        candidate_head=candidate_head,
        root=str(root_path),
        hermes_version=CANARY_LIMITS["required_hermes_version"],
        work_root=str(work_tree),
        phase_history=phase_history,
        inventory_before=compute_candidate_inventory(root_path),
        inventory_after=compute_candidate_inventory(root_path),
        candidate_profiles=CANDIDATE_PROFILES,
        flags=receipt_flags,
        claims=dict(worker_claims),
        changed_paths=[str(host_receipt_path), str(worker_receipt_path)],
    )
    receipt = tokenize_receipt_paths(
        receipt,
        candidate_root=str(root_path),
        work_root=str(work_tree),
    )
    write_json_receipt_atomically(evidence, receipt)
    return receipt


def run_worker_phase(
    *,
    mode: str,
    root: str | os.PathLike[str] = "",
    input_receipt: str | os.PathLike[str] = "",
    candidate_head: str = "",
    work_root: str | os.PathLike[str] = "",
    host_receipt: str = "",
    host_archives: str = "",
    hermes: str = "/usr/local/bin/hermes",
    hermes_version: str = CANARY_LIMITS["required_hermes_version"],
    execute: bool = False,
    dry_run: bool = False,
) -> Dict[str, Any]:
    if mode != "docker":
        raise LifecycleCanaryError("unsupported worker mode")
    if not root or not work_root or not host_archives:
        raise ValueError("worker invocation must include --root, --input-receipt, --work-root, and --host-receipt")

    if execute and dry_run:
        raise ValueError("worker invocation cannot set both --execute and --dry-run")
    if not execute and not dry_run:
        raise ValueError("worker invocation must include --execute or --dry-run")

    if input_receipt == "" and host_receipt == "":
        raise ValueError("worker invocation must include --input-receipt or --host-receipt")
    if input_receipt == "":
        input_receipt = host_receipt

    root_path = validate_path_no_follow(root)
    work_tree = validate_work_root(str(root_path), work_root)
    work_tree_path = pathlib.Path(work_tree)
    archive_work_root = work_tree_path / "archives"
    received_receipt = _read_json_payload(input_receipt)

    if received_receipt.get("candidate_head") != candidate_head:
        raise ValueError("candidate head mismatch")

    if received_receipt.get("hermes_version") != hermes_version:
        raise ValueError("worker received unsupported hermes version")

    normalized_host = _validate_host_receipt_for_docker(payload=received_receipt, candidate_head=candidate_head)
    source_receipt_hash = hashlib.sha256(pathlib.Path(input_receipt).read_bytes()).hexdigest()

    candidate_inventory_before = compute_candidate_inventory(root_path)
    canonical_inventory_before = _canonicalize_inventory_for_docker(candidate_inventory_before)
    if canonical_inventory_before != normalized_host["inventory_before"]:
        raise ValueError("candidate inventory mismatch before execution")

    if dry_run:
        candidate_inventory_after = compute_candidate_inventory(root_path)
        canonical_inventory_after = _canonicalize_inventory_for_docker(candidate_inventory_after)
        if canonical_inventory_after != normalized_host["inventory_after"]:
            raise ValueError("candidate inventory mismatch after execution")

        tokenized_inventory_before = tokenize_receipt_paths(
            candidate_inventory_before,
            candidate_root=str(root_path),
            work_root=str(work_tree),
        )
        tokenized_inventory_after = tokenize_receipt_paths(
            candidate_inventory_after,
            candidate_root=str(root_path),
            work_root=str(work_tree),
        )

        receipt = build_receipt(
            mode="docker",
            status="dry_run",
            candidate_head=candidate_head,
            root=str(root_path),
            hermes_version=CANARY_LIMITS["required_hermes_version"],
            work_root=str(work_tree),
            phase_history=[{"phase": "preflight", "status": "ok", "tag": "worker-preflight"}],
            inventory_before=tokenized_inventory_before,
            inventory_after=tokenized_inventory_after,
            candidate_profiles=CANDIDATE_PROFILES,
            flags={
                "execution_mode": "dry-run",
                "source_receipt_hash": source_receipt_hash,
                "host_archive_records": normalized_host["archive_records"],
            },
            claims=_build_claim_map(),
            changed_paths=[str(input_receipt)],
        )
        receipt = tokenize_receipt_paths(
            receipt,
            candidate_root=str(root_path),
            work_root=str(work_tree),
        )
        return receipt

    candidate_profiles = scan_candidate_profiles(root_path)
    validate_candidate_profiles(list(candidate_profiles.keys()))

    inventory_before = candidate_inventory_before
    inventory_after: Dict[str, Any] | None = None
    sandbox = _build_sandbox(work_tree_path)
    phase_history: List[Dict[str, Any]] = []
    changed_paths: List[str] = []
    claims = _build_claim_map()
    cleanup_errors: List[str] = []
    env = _isolate_env(
        sandbox["home"],
        sandbox["restore_home"],
        sandbox["tmpdir"],
        base={
            "CANARY_WORK_ROOT": str(work_tree_path),
            "CANARY_ROOT": str(root_path),
            "CANARY_SOURCE_RECEIPT": str(input_receipt),
            "CANARY_SOURCE_RECEIPT_SHA256": source_receipt_hash,
        },
    )
    claims["workspaces_isolated"] = True

    host_archive_root = validate_path_no_follow(host_archives)
    if not host_archive_root.is_dir():
        raise ValueError("host archive input must be a directory")

    copied_hashes, copied_members, copied_portable_hashes, copied_paths = _copy_and_validate_host_archives(
        source_root=host_archive_root,
        destination_root=archive_work_root,
        archive_records=normalized_host["archive_records"],
    )
    changed_paths.extend(copied_paths)
    claims["archive_safety"] = True

    primary_error: Exception | None = None
    hermes_path = validate_path_no_follow(hermes)
    observed_hermes_version = _observe_hermes_version(hermes_path)
    if observed_hermes_version != hermes_version:
        raise UnsafeInvocationError(
            f"hermes version mismatch (observed={observed_hermes_version}, expected={hermes_version})"
        )

    try:
        for profile in CANDIDATE_PROFILES:
            command = build_profile_command(
                "import",
                str(archive_work_root / normalized_host["archive_records"][profile]["filename"]),
                str(hermes_path),
                ["--name", profile],
            )
            _run_and_record_phase("import", profile, command, env, True, phase_history)

        for profile in CANDIDATE_PROFILES:
            source_profile = root_path / CANARY_LIMITS["candidate_profile_prefix"] / profile
            restore_profile_root = sandbox["restore_home"] / "profiles" / profile
            if not restore_profile_root.is_dir():
                raise UnsafeInvocationError("import command reported success without restored profile")

            _run_and_record_phase(
                "reinstall",
                profile,
                [
                    str(hermes_path),
                    "profile",
                    "install",
                    str(source_profile),
                    "--name",
                    profile,
                    "--force",
                    "--yes",
                ],
                env,
                True,
                phase_history,
            )

            _assert_distribution_payload_matches(
                restore_profile_root,
                source_profile,
                allowed_payload_extras=("local", "memories"),
            )

            if not _verify_no_secret_names(restore_profile_root):
                raise UnsafeInvocationError("restore introduced forbidden artifacts")

            for required in ("local", "memories"):
                if not (restore_profile_root / required).exists():
                    raise UnsafeInvocationError(f"restore missing {required} for {profile}")

            _assert_excluded_state_absent(restore_profile_root)
            if _snapshot_portable_payload_state(restore_profile_root) != copied_portable_hashes[profile]:
                raise UnsafeInvocationError(f"portable bytes mismatch for {profile}")

            if (source_profile / "config.yaml").exists():
                source_config = (source_profile / "config.yaml").read_text(encoding="utf-8")
                restore_config = (restore_profile_root / "config.yaml").read_text(encoding="utf-8")
                if source_config != restore_config:
                    raise UnsafeInvocationError(f"config mismatch for {profile}")

        claims["restore_uses_native_profile_import"] = True
        claims["portable_profile_reinstalled"] = True
        claims["restore_reinstall_works"] = True
        claims["portable_backup_created"] = True
        claims["restore_isolated"] = True
        claims["secrets_excluded"] = True

        for profile in CANDIDATE_PROFILES:
            command = build_profile_command("delete", profile, str(hermes_path), ["--yes"])
            _run_and_record_phase("delete", profile, command, env, True, phase_history)
            target = sandbox["restore_home"] / "profiles" / profile
            if target.exists():
                raise UnsafeInvocationError("delete command did not remove restored profile")

        claims["delete_target_only"] = True
        inventory_after = compute_candidate_inventory(root_path)
        canonical_inventory_after = _canonicalize_inventory_for_docker(inventory_after)
        if canonical_inventory_after != normalized_host["inventory_after"]:
            raise ValueError("candidate inventory mismatch after execution")
        claims["candidate_inventory_unchanged"] = inventory_after["tree"] == inventory_before["tree"]
        claims["workspaces_isolated"] = True
        claims["all_claims"] = all(
            claims[claim]
            for claim in [
                "archive_safety",
                "restore_uses_native_profile_import",
                "portable_profile_reinstalled",
                "restore_reinstall_works",
                "restore_isolated",
                "secrets_excluded",
                "delete_target_only",
                "candidate_inventory_unchanged",
            ]
        )
    except Exception as exc:  # noqa: BLE001
        primary_error = exc
        claims["all_claims"] = False
        raise
    finally:
        if primary_error is not None:
            for profile in CANDIDATE_PROFILES:
                target = sandbox["restore_home"] / "profiles" / profile
                if not target.exists():
                    continue
                cleanup_command = build_profile_command("delete", profile, str(hermes_path), ["--yes"])
                try:
                    result = run_command(cleanup_command, env=env)
                    phase_history.append(
                        {
                            "phase": "cleanup-delete",
                            "tag": profile,
                            "status": parse_phase_status(result),
                            "returncode": result["returncode"],
                            "command_hash": result["stdout_hash"],
                            "env": result.get("env", {}),
                            "elapsed_seconds": result.get("elapsed_seconds", 0),
                        }
                    )
                except Exception as cleanup_exc:
                    cleanup_errors.append(f"cleanup failed for {profile}: {type(cleanup_exc).__name__}")

            final_inventory_after = inventory_after if inventory_after is not None else compute_candidate_inventory(root_path)
            failure_receipt = build_receipt(
                mode="docker",
                status="failed",
                candidate_head=candidate_head,
                root=str(root_path),
                hermes_version=CANARY_LIMITS["required_hermes_version"],
                work_root=str(work_tree),
                phase_history=phase_history,
                inventory_before=inventory_before,
                inventory_after=final_inventory_after,
                candidate_profiles=CANDIDATE_PROFILES,
                flags={
                    "primary_error": type(primary_error).__name__ if primary_error else "",
                    "source_receipt_hash": source_receipt_hash,
                    "copied_hashes": copied_hashes,
                    "copied_members": copied_members,
                    "cleanup_errors": cleanup_errors,
                },
                claims=claims,
                changed_paths=changed_paths,
            )
            write_json_receipt_atomically(
                str(pathlib.Path(work_tree) / "docker-worker-receipt.json"),
                tokenize_receipt_paths(
                    failure_receipt,
                    candidate_root=str(root_path),
                    work_root=str(work_tree),
                    hermes_home=str(sandbox["hermes_home"]),
                    home=str(sandbox["home"]),
                ),
            )

    final_inventory_after = inventory_after if inventory_after is not None else compute_candidate_inventory(root_path)
    receipt = build_receipt(
        mode="docker",
        status="passed" if claims.get("all_claims") else "failed",
        candidate_head=candidate_head,
        root=str(root_path),
        hermes_version=CANARY_LIMITS["required_hermes_version"],
        work_root=str(work_tree),
        phase_history=phase_history,
        inventory_before=inventory_before,
        inventory_after=final_inventory_after,
        candidate_profiles=CANDIDATE_PROFILES,
        flags={
            "source_receipt_hash": source_receipt_hash,
            "host_archive_hashes": copied_hashes,
            "host_archive_members": copied_members,
            "execution_mode": "execute",
        },
        claims=claims,
        changed_paths=changed_paths,
    )
    write_json_receipt_atomically(
        str(pathlib.Path(work_tree) / "docker-worker-receipt.json"),
        tokenize_receipt_paths(
            receipt,
            candidate_root=str(root_path),
            work_root=str(work_tree),
            hermes_home=str(sandbox["hermes_home"]),
            home=str(sandbox["home"]),
        ),
    )
    return receipt


def tokenize_receipt_paths(payload: Any, *, candidate_root: str | None = None, work_root: str | None = None,
                        hermes_home: str | None = None, home: str | None = None) -> Any:
    replacements: List[tuple[str, str]] = []
    if candidate_root:
        replacements.append((str(pathlib.Path(candidate_root)), "<candidate_root>"))
    if work_root:
        replacements.append((str(pathlib.Path(work_root)), "<work_root>"))
    if hermes_home:
        replacements.append((str(pathlib.Path(hermes_home)), "<hermes_home>"))
    if home:
        replacements.append((str(pathlib.Path(home)), "<home>"))

    roots = [path for path in (candidate_root, work_root, hermes_home, home) if path]
    if not roots:
        discovered: List[str] = []

        def _collect(value: Any) -> None:
            if isinstance(value, dict):
                for item in value.values():
                    _collect(item)
            elif isinstance(value, (list, tuple)):
                for item in value:
                    _collect(item)
            elif isinstance(value, str):
                if value.startswith("/") and "/" in value and not value.startswith(("/bin", "/usr", "/tmp", "/var", "/proc", "/dev")):
                    discovered.append(value)

        _collect(payload)
        roots = [path for path in discovered if "/" in path]

    if len(roots) >= 2:
        common = os.path.commonpath([str(pathlib.Path(root)) for root in roots])
        if common and common.startswith("/"):
            replacements.append((common, "<repo_root>"))

    common_replacements = [item for item in replacements if item[1] == "<repo_root>"]
    direct_replacements = [item for item in replacements if item[1] != "<repo_root>"]
    direct_replacements.sort(key=lambda item: len(item[0]), reverse=True)
    replacements = common_replacements + direct_replacements

    def _scrub(value: Any) -> Any:
        if isinstance(value, dict):
            return {key: _scrub(val) for key, val in value.items()}
        if isinstance(value, list):
            return [_scrub(item) for item in value]
        if isinstance(value, tuple):
            return tuple(_scrub(item) for item in value)
        if isinstance(value, str):
            scrubbed = value
            for source, token in replacements:
                if not source:
                    continue
                if scrubbed == source:
                    scrubbed = token
                elif scrubbed.startswith(f"{source}/"):
                    scrubbed = scrubbed.replace(source, token, 1)
            return scrubbed
        return value

    return _scrub(payload)


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    execute_requested = False
    dry_run_requested = False
    if hasattr(args, "execute"):
        if args.execute and args.dry_run:
            raise UnsafeInvocationError("execution flags conflict: --execute and --dry-run")
        execute_requested = bool(args.execute)
        dry_run_requested = bool(args.dry_run) or not execute_requested

    try:
        if args.command == "host":
            if not args.dry_run and not args.execute:
                args.dry_run = True
            if args.execute and args.dry_run:
                raise UnsafeInvocationError("execution flags conflict: --execute and --dry-run")
            if args.hermes_python and pathlib.Path(args.hermes_python).is_relative_to(pathlib.Path("/")):
                pass
            run_host_canary(
                root=args.root,
                candidate_head=args.candidate_head,
                hermes=args.hermes,
                work_root=args.work_root,
                evidence=args.evidence,
                hermes_version=args.hermes_version,
                hermes_python=args.hermes_python,
                dry_run=bool(args.dry_run and not args.execute),
                execute=bool(args.execute),
            )
            if dry_run_requested:
                return map_exit_code("dry_run")
            return map_exit_code("passed")
        if args.command == "docker":
            run_docker_canary(
                root=args.root,
                candidate_head=args.candidate_head,
                image=args.image,
                work_root=args.work_root,
                host_work_root=args.host_work_root,
                host_receipt=args.host_receipt,
                host_archives=args.host_archives,
                evidence=args.evidence,
                hermes_version=args.hermes_version,
                dry_run=bool(args.dry_run and not args.execute),
                execute=bool(args.execute),
            )
            return map_exit_code("ok")
        if args.command == "_worker":
            run_worker_phase(
                mode=args.mode,
                root=args.root,
                input_receipt=args.input_receipt,
                host_receipt=args.host_receipt,
                work_root=args.work_root,
                host_archives=args.host_archives,
                hermes=args.hermes,
                hermes_version=args.hermes_version,
                candidate_head=args.candidate_head,
                execute=bool(args.execute),
                dry_run=bool(args.dry_run),
            )
            return map_exit_code("ok")
        raise UnsafeInvocationError(f"unsupported command: {args.command}")
    except UnsafeInvocationError as exc:
        print(json.dumps({"status": "error", "reason": str(exc), "level": "unsafe"}, sort_keys=True))
        return map_exit_code("unsafe_invocation")
    except LifecycleCanaryError as exc:
        print(json.dumps({"status": "error", "reason": str(exc), "level": "infrastructure"}, sort_keys=True))
        return map_exit_code("infrastructure_unavailable")
    except ValueError as exc:
        print(json.dumps({"status": "error", "reason": str(exc), "level": "assertion"}, sort_keys=True))
        return map_exit_code("assertion_failure")


if __name__ == "__main__":
    raise SystemExit(main())
