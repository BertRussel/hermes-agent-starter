#!/usr/bin/env python3
"""Slice 1 release verifier.

Validate release-index plus repository payload hygiene for local pre-release safety.
Only the Python standard library is used.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import re
import stat
import sys
import subprocess
from pathlib import Path
from typing import Mapping


ERROR_ORDER = [
    "provenance_missing",
    "provenance_malformed",
    "provenance_component_missing",
    "provenance_component_duplicate",
    "provenance_component_extra",
    "provenance_component_status",
    "provenance_row_policy",
    "top_level_entry",
    "invalid_index",
    "invalid_schema",
    "component_count",
    "component_name",
    "component_missing",
    "component_path_invalid",
    "component_version_mismatch",
    "component_status_mismatch",
    "component_path_not_found",
    "symlink_found",
    "hardlink_found",
    "owner_payload_mismatch",
    "owner_contract_mismatch",
    "distribution_contract_mismatch",
    "forbidden_filename",
    "forbidden_path",
    "binary_file",
    "publication_ready_blocker_present",
    "publication_ready_blocker_state",
    "publication_ready_blockers",
    "publication_blocker_obsolete",
    "runtime_manifest_key_mismatch",
    "runtime_manifest_value_mismatch",
    "runtime_manifest_syntax",
    "runtime_payload_missing_file",
    "runtime_payload_unowned_file",
    "runtime_payload_hidden_path",
    "runtime_payload_non_regular_file",
    "runtime_payload_symlink",
    "runtime_payload_executable_file",
    "runtime_source_syntax_error",
    "runtime_source_import_violation",
    "runtime_source_call_violation",
    "compatibility_not_ready",
    "release_status_not_ready",
    "component_not_ready",
    "deny_term_file_invalid",
    "deny_term_file_empty",
    "deny_term",
    "secret_detection",
    "receipt_arg_mismatch",
    "compatibility_receipt_invalid_path",
    "compatibility_receipt_read_error",
    "compatibility_receipt_invalid_schema",
    "compatibility_receipt_invalid_type",
    "compatibility_receipt_invalid_mode",
    "compatibility_receipt_invalid_head",
    "compatibility_receipt_invalid_version",
    "compatibility_receipt_invalid_claim",
    "compatibility_receipt_invalid_profile_set",
    "compatibility_receipt_invalid_archive",
    "compatibility_receipt_invalid_member",
    "compatibility_receipt_invalid_image",
    "compatibility_receipt_mismatched_host_hash",
    "compatibility_receipt_mismatched_archive_records",
]


REQUIRED_SCHEMA_VERSION = "1.0.0"
REQUIRED_RELEASE_STATUS = "private_candidate"
REQUIRED_RELEASE_STATUSES = {REQUIRED_RELEASE_STATUS, "development"}
CANDIDATE_PROFILES = {"owner-agent", "art", "recon", "forge", "eve"}
CANDIDATE_HERMES_VERSION = "0.20.5"
CANDIDATE_HEAD_PLACEHOLDER = "0" * 40
COMPATIBILITY_REQUIREMENT_CLAIMS = (
    "archive_safety",
    "candidate_inventory_unchanged",
    "delete_target_only",
    "exact_five_installs",
    "force_config_restore",
    "portable_backup_created",
    "portable_profile_reinstalled",
    "restore_isolated",
    "restore_reinstall_works",
    "restore_uses_native_profile_import",
    "secrets_excluded",
    "update_preserves_user_data",
    "workspaces_isolated",
)

REQUIRED_COMPONENTS = {
    "owner-agent": "profiles/owner-agent",
    "art": "profiles/art",
    "recon": "profiles/recon",
    "forge": "profiles/forge",
    "eve": "profiles/eve",
    "engineering-runtime": "runtimes/engineering-runtime",
    "art-runtime": "runtimes/art-runtime",
}
REQUIRED_RELEASE_COMPONENT_STATE = {
    "development": {
        "engineering-runtime": {
            "path": "runtimes/engineering-runtime",
            "version": "0.1.0-dev",
            "status": "ready",
        },
        "art-runtime": {
            "path": "runtimes/art-runtime",
            "version": "0.1.0-dev",
            "status": "ready",
        },
        "owner-agent": {
            "path": "profiles/owner-agent",
            "version": "0.0.0-dev",
            "status": "development",
        },
        "art": {
            "path": "profiles/art",
            "version": "0.0.0-dev",
            "status": "development",
        },
        "recon": {
            "path": "profiles/recon",
            "version": "0.0.0-dev",
            "status": "development",
        },
        "forge": {
            "path": "profiles/forge",
            "version": "0.0.0-dev",
            "status": "development",
        },
        "eve": {
            "path": "profiles/eve",
            "version": "0.0.0-dev",
            "status": "development",
        },
    },
    "private_candidate": {
        "engineering-runtime": {
            "path": "runtimes/engineering-runtime",
            "version": "0.1.0-dev",
            "status": "ready",
        },
        "art-runtime": {
            "path": "runtimes/art-runtime",
            "version": "0.1.0-dev",
            "status": "ready",
        },
        "owner-agent": {
            "path": "profiles/owner-agent",
            "version": "0.1.0-dev",
            "status": "candidate",
        },
        "art": {
            "path": "profiles/art",
            "version": "0.1.0-dev",
            "status": "candidate",
        },
        "recon": {
            "path": "profiles/recon",
            "version": "0.1.0-dev",
            "status": "candidate",
        },
        "forge": {
            "path": "profiles/forge",
            "version": "0.1.0-dev",
            "status": "candidate",
        },
        "eve": {
            "path": "profiles/eve",
            "version": "0.1.0-dev",
            "status": "candidate",
        },
    },
}
EXPECTED_TOP_LEVEL_ENTRIES = {
    ".github",
    ".gitignore",
    "CONTRIBUTING.md",
    "LICENSE",
    "README.md",
    "SECURITY.md",
    "THIRD_PARTY_NOTICES.md",
    "compatibility.json",
    "examples",
    "release-index.yaml",
    "release-manifest.json",
    "PROVENANCE.md",
    "brain-os-starter",
    "docs",
    "profiles",
    "runtimes",
    "runtime-bundle",
    "scripts",
    "templates",
    "tests",
}
OWNER_FIELDS = (
    "OWNER_OR_COMPANY_NAME",
    "OWNER_FORM_OF_ADDRESS",
    "AGENT_NAME",
    "AGENT_INSPIRATION",
    "AGENT_INSPIRATION_TRAITS",
    "COMMUNICATION_STYLE",
    "OPTIONAL_HELP_AND_PROJECTS",
)
REQUIRED_OWNER_PAYLOAD_FILES = [
    "README.md",
    "SOUL.md",
    "config.yaml",
    "distribution.yaml",
    "skills",
]
REQUIRED_OWNER_PAYLOAD_DIRECTORIES = {
    "",
    "skills",
    "skills/client-agent-operations",
}
REQUIRED_OWNER_SKILL_FILE = "skills/client-agent-operations/SKILL.md"
REQUIRED_PROVENANCE_COMPONENTS = [
    "owner-agent",
    "art",
    "recon",
    "forge",
    "eve",
    "engineering-runtime",
    "art-runtime",
]

_RUNTIME_MANIFEST_EXPECTATIONS = {
    "engineering-runtime": {
        "name": "engineering-runtime",
        "path": "runtimes/engineering-runtime",
        "version": "0.1.0-dev",
        "description": "Core engineering-runtime scaffold for Slice 4B runtime contracts.",
        "stdlib_only": True,
        "dependencies": [],
        "python_requires": ">=3.11",
        "owned_files": [
            "README.md",
            "runtime.yaml",
            "src/engineering_runtime/__init__.py",
            "src/engineering_runtime/runtime.py",
        ],
        "publication_authority": "none",
        "manifest_error_code": "provenance_row_policy",
        "provenance_terms": {
            "newly authored",
            "original",
            "stdlib-only",
            "publication pending",
            "ready",
        },
        "forbidden_terms": {"imported", "vendored", "proprietary", "licensed", "authorized", "publication-authorized"},
        "payload_error_code": {
            "missing": "runtime_payload_missing_file",
            "unowned": "runtime_payload_unowned_file",
            "hidden": "runtime_payload_hidden_path",
            "non_regular": "runtime_payload_non_regular_file",
            "symlink": "runtime_payload_symlink",
            "executable": "runtime_payload_executable_file",
            "syntax": "runtime_source_syntax_error",
            "import": "runtime_source_import_violation",
            "call": "runtime_source_call_violation",
        },
    },
    "art-runtime": {
        "name": "art-runtime",
        "path": "runtimes/art-runtime",
        "version": "0.1.0-dev",
        "description": "Pure-stdlib validator runtime for Art candidate job and manifest contracts.",
        "stdlib_only": True,
        "dependencies": [],
        "python_requires": ">=3.11",
        "owned_files": [
            "README.md",
            "runtime.yaml",
            "src/art_runtime/__init__.py",
            "src/art_runtime/runtime.py",
        ],
        "publication_authority": "none",
        "manifest_error_code": "runtime_manifest_key_mismatch",
        "provenance_terms": {
            "newly authored",
            "original",
            "clean-room",
            "stdlib-only",
            "publication pending",
            "ready",
        },
        "forbidden_terms": {"imported", "vendored", "proprietary", "licensed", "authorized", "publication-authorized"},
        "payload_error_code": {
            "missing": "runtime_payload_missing_file",
            "unowned": "runtime_payload_unowned_file",
            "hidden": "runtime_payload_hidden_path",
            "non_regular": "runtime_payload_non_regular_file",
            "symlink": "runtime_payload_symlink",
            "executable": "runtime_payload_executable_file",
            "syntax": "runtime_source_syntax_error",
            "import": "runtime_source_import_violation",
            "call": "runtime_source_call_violation",
        },
    },
}

_RUNTIME_IMPORT_ALLOWED_ROOTS = {
    "engineering-runtime": {"__future__", "ast", "base64", "contextlib", "functools", "hashlib", "inspect", "json", "math"},
    "art-runtime": {"__future__", "copy", "json", "math", "re", "pathlib", "typing", "collections"},
}

_RUNTIME_IMPORT_FORBIDDEN_ROOTS = {
    "engineering-runtime": {"os", "sys", "requests", "socket", "subprocess", "tempfile", "time", "random"},
    "art-runtime": {"os", "requests", "socket", "subprocess", "tempfile", "time", "random", "urllib", "http", "socketserver", "asyncio", "threading"},
}

_RUNTIME_FORBIDDEN_CALLS = {"eval", "exec", "compile", "__import__"}
SPECIALIST_ROLES = {
    "art": {
        "contract": "creative-production-contract",
        "tools": ["file", "terminal", "todo", "vision", "web"],
        "authority": "cannot publish or claim final acceptance",
        "required_files": [
            "README.md",
            "SOUL.md",
            "config.yaml",
            "distribution.yaml",
            "skills",
        ],
    },
    "recon": {
        "contract": "research-assurance-contract",
        "tools": ["file", "terminal", "todo", "web", "browser", "vision"],
        "authority": "cannot implement or make final decisions",
        "required_files": [
            "README.md",
            "SOUL.md",
            "config.yaml",
            "distribution.yaml",
            "skills",
        ],
    },
    "forge": {
        "contract": "bounded-implementation-contract",
        "tools": ["file", "terminal", "todo"],
        "authority": "cannot approve its own output or act on production",
        "required_files": [
            "README.md",
            "SOUL.md",
            "config.yaml",
            "distribution.yaml",
            "skills",
        ],
    },
    "eve": {
        "contract": "independent-review-contract",
        "tools": ["file", "terminal", "todo"],
        "authority": "cannot implement or make final decisions",
        "required_files": [
            "README.md",
            "SOUL.md",
            "config.yaml",
            "distribution.yaml",
            "skills",
        ],
    },
}
FORBIDDEN_FILENAMES = {
    ".env",
    ".env.local",
    ".env.production",
    ".git-credentials",
    "authorized_keys",
    "credentials",
    "credential",
    "secret",
    "secrets",
    "token",
    "id_rsa",
    "id_ed25519",
    "id_ecdsa",
    "id_dsa",
    "auth.json",
    "session.json",
    "memory.json",
    "state.json",
    "auth",
    "session",
    "memory",
    "state",
    "passwd",
    "shadow",
    "access_keys.json",
}
FORBIDDEN_SUFFIXES = {
    ".pyc",
    ".pyo",
    ".so",
    ".dylib",
    ".dll",
    ".exe",
    ".bin",
    ".zip",
    ".tar",
    ".gz",
    ".bz2",
    ".xz",
    ".7z",
    ".rar",
    ".apk",
    ".jar",
    ".war",
    ".class",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".mp4",
    ".mov",
}
FORBIDDEN_DIRECTORIES = {
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    "dist",
    "build",
    ".cache",
    "venv",
    ".venv",
    "env",
    "node_modules",
    "runtime-private",
    "private",
    "generated",
    "archives",
}

_TOKEN_KEYWORDS = [
    "api[_-]?key",
    "api_secret",
    "client_secret",
    "private_key",
    "access_token",
    "secret",
]


def _build_secret_high_entropy_pattern():
    keyword_expr = "|".join(_TOKEN_KEYWORDS)
    source = [
        r"(?i)",
        r"\b(",
        keyword_expr,
        r")\b[^\n]*[=:][^\n]{12,}",
    ]
    return re.compile("".join(source))


SECRET_PATTERNS = [
    {
        "code": "secret_aws_access_key",
        "pattern": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    },
    {
        "code": "secret_github_pat",
        "pattern": re.compile(r"\bghp_[A-Za-z0-9]{36}\b"),
    },
    {
        "code": "secret_private_key",
        "pattern": re.compile(r"-----BEGIN [A-Z ]+PRIVATE KEY-----"),
    },
    {
        "code": "secret_high_entropy_kv",
        "pattern": _build_secret_high_entropy_pattern(),
    },
]


def add_entry(items, code, message, path, line=None, details=None):
    entry = {"code": code, "message": message}
    if path is not None:
        entry["path"] = path
    if line is not None:
        entry["line"] = line
    if details:
        entry.update(details)
    items.append(entry)


def _coerce_scalar(value):
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
        value = value[1:-1]
    lowered = value.lower()
    if lowered in {"true", "false"}:
        return lowered == "true"
    if value == "[]":
        return []
    if value == "" or value is None:
        return ""
    return value


def _read_text_file(path: Path, errors, code, detail=None):
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        add_entry(
            errors,
            code,
            f"unable to read {path.name}: {exc}",
            str(path.relative_to(path.parent.parent.parent.parent) if path.is_absolute() else path),
            details=detail,
        )
    return None


def _parse_distribution_yaml(text: str):
    data = {}
    current_key = None
    for line in text.splitlines():
        raw = line.rstrip("\n")
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        line_stripped = raw.strip()
        if indent == 0:
            if ":" not in line_stripped:
                continue
            key, _, value = line_stripped.partition(":")
            key = key.strip()
            value = value.strip()
            if value:
                data[key] = _coerce_scalar(value)
                current_key = None
            else:
                data[key] = []
                current_key = key
            continue

        if current_key and indent >= 2 and line_stripped.startswith("-"):
            data[current_key].append(line_stripped[1:].lstrip().strip())
            continue

        current_key = None

    return data


def _parse_nested_yaml(text: str):
    data = {}
    current_key = None
    for line in text.splitlines():
        raw = line.rstrip("\n")
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        line_stripped = raw.strip()
        if indent == 0:
            if ":" not in line_stripped:
                continue
            key, _, value = line_stripped.partition(":")
            key = key.strip()
            value = value.strip()
            current_key = key
            if value:
                data[key] = _coerce_scalar(value)
            else:
                data[key] = {}
            continue

        if current_key and indent >= 2 and isinstance(data.get(current_key), dict):
            if ":" not in line_stripped:
                continue
            child_key, _, child_value = line_stripped.partition(":")
            data[current_key][child_key.strip()] = _coerce_scalar(child_value.strip())

    return data


def _parse_skill_frontmatter(text: str):
    if not text.startswith("---\n"):
        return None, text
    close = text.find("---", 3)
    if close < 0:
        return None, text
    header = text[3:close].strip()
    body = text[close + 3 :].strip()
    parsed = {}
    for line in header.splitlines():
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        parsed[key.strip()] = value.strip()
    return parsed, body


def _normalise_component_key(value: str) -> str:
    return value.strip().lower()


def _parse_provenance_table(text: str):
    rows = []
    headers = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or not line.startswith("|"):
            continue
        if not line.endswith("|"):
            continue
        if re.fullmatch(r"[\s|:-]+", line):
            continue

        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if not cells:
            continue

        if not headers:
            lower = [cell.lower() for cell in cells]
            if any(cell == "component" for cell in lower):
                headers = [cell.strip() for cell in cells]
            continue

        if len(cells) < 2:
            return None, "provenance row malformed"
        rows.append(cells)

    if not headers:
        return None, "provenance table missing header"
    if not rows:
        return None, "provenance table missing rows"

    # Normalize to an ordered dict-style object list with explicit fields.
    result = []
    for cells in rows:
        if len(cells) < len(headers):
            cells += [""] * (len(headers) - len(cells))
        elif len(cells) > len(headers):
            # Preserve trailing provenance fields in the notes column for markdown rows
            # that use a four-column contract but keep additional tags in a fifth/extra
            # source column.
            cells = cells[: len(headers) - 1] + [" ".join(cells[len(headers) - 1 :]).strip()]
        entry = {headers[i].strip().lower().replace(" ", "_"): cells[i].strip() for i in range(len(headers))}
        if not entry.get("component"):
            continue
        result.append(entry)
    return result, ""


def _sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _read_receipt_blob(path: Path, errors, code_base: str) -> bytes | None:
    try:
        st = path.lstat()
    except FileNotFoundError:
        add_entry(errors, f"{code_base}_invalid_path", f"receipt path not found: {path}", "release-index.yaml")
        return None
    except OSError as exc:
        add_entry(
            errors,
            f"{code_base}_read_error",
            f"cannot read receipt path {path}: {exc}",
            "release-index.yaml",
        )
        return None

    if not stat.S_ISREG(st.st_mode):
        add_entry(
            errors,
            f"{code_base}_invalid_path",
            f"receipt path is not regular file: {path}",
            "release-index.yaml",
        )
        return None
    if stat.S_ISLNK(st.st_mode):
        add_entry(
            errors,
            f"{code_base}_invalid_path",
            f"receipt path must not be a symlink: {path}",
            "release-index.yaml",
        )
        return None

    try:
        return path.read_bytes()
    except OSError as exc:
        add_entry(errors, f"{code_base}_read_error", f"unable to read receipt file {path}: {exc}", "release-index.yaml")
        return None


def _normalize_archive_records(records: Mapping[str, Any], code_base: str, errors) -> Dict[str, Dict[str, Any]] | None:
    if not isinstance(records, dict):
        add_entry(
            errors,
            f"{code_base}_invalid_archive",
            "receipt archive record block must be an object",
            "release-index.yaml",
        )
        return None

    normalized: Dict[str, Dict[str, Any]] = {}
    for profile, record in records.items():
        if not isinstance(profile, str):
            add_entry(
                errors,
                f"{code_base}_invalid_profile_set",
                "archive record profile key must be string",
                "release-index.yaml",
                details={"profile": profile},
            )
            return None
        if not isinstance(record, dict):
            add_entry(
                errors,
                f"{code_base}_invalid_archive",
                f"archive record for {profile} must be an object",
                "release-index.yaml",
                details={"profile": profile},
            )
            return None

        filename = record.get("filename")
        if not isinstance(filename, str) or not filename:
            add_entry(
                errors,
                f"{code_base}_invalid_archive",
                f"archive record for {profile} missing or empty filename",
                "release-index.yaml",
                details={"profile": profile, "filename": filename},
            )
            return None

        sha = record.get("sha256")
        if not isinstance(sha, str) or not re.fullmatch(r"[0-9a-fA-F]{64}", sha):
            add_entry(
                errors,
                f"{code_base}_invalid_archive",
                f"archive record for {profile} missing or invalid sha256",
                "release-index.yaml",
                details={"profile": profile, "sha256": sha},
            )
            return None

        members = record.get("members")
        if not isinstance(members, list):
            add_entry(
                errors,
                f"{code_base}_invalid_archive",
                f"archive record for {profile} missing members",
                "release-index.yaml",
                details={"profile": profile},
            )
            return None

        for member in members:
            if not isinstance(member, str):
                add_entry(
                    errors,
                    f"{code_base}_invalid_member",
                    "archive member must be string",
                    "release-index.yaml",
                    details={"profile": profile, "member": member},
                )
                return None
            if not member or member.startswith("/"):
                add_entry(
                    errors,
                    f"{code_base}_invalid_member",
                    "archive member path must be relative",
                    "release-index.yaml",
                    details={"profile": profile, "member": member},
                )
                return None
            if ".." in member.split("/"):
                add_entry(
                    errors,
                    f"{code_base}_invalid_member",
                    "archive member path must not contain traversal",
                    "release-index.yaml",
                    details={"profile": profile, "member": member},
                )
                return None

        member_count = record.get("member_count")
        if not isinstance(member_count, int) or member_count < 0:
            add_entry(
                errors,
                f"{code_base}_invalid_archive",
                f"archive record for {profile} has invalid member_count",
                "release-index.yaml",
                details={"profile": profile, "member_count": member_count},
            )
            return None
        if member_count != len(members):
            add_entry(
                errors,
                f"{code_base}_invalid_archive",
                f"archive record for {profile} member_count mismatch",
                "release-index.yaml",
                details={"profile": profile, "expected": member_count, "actual": len(members)},
            )
            return None

        normalized[profile] = {
            "filename": filename,
            "sha256": sha.lower(),
            "members": list(members),
            "member_count": member_count,
        }

    return normalized


def _validate_profile_archive_records(records: dict, code_base: str, errors):
    return _normalize_archive_records(records, code_base, errors) is not None


def _validate_receipt_claims(payload: dict, required_claims, code_base: str, errors, *, require_all_claims_only: bool = True) -> bool:
    claims = payload.get("claims")
    if not isinstance(claims, dict):
        add_entry(
            errors,
            f"{code_base}_invalid_schema",
            "receipt claims must be an object",
            "release-index.yaml",
        )
        return False

    ok = True
    if claims.get("all_claims") is not True:
        add_entry(
            errors,
            f"{code_base}_invalid_claim",
            "receipt claims must have all_claims=true",
            "release-index.yaml",
        )
        ok = False

    if require_all_claims_only:
        for claim_name in required_claims:
            if claims.get(claim_name) is not True:
                add_entry(
                    errors,
                    f"{code_base}_invalid_claim",
                    f"receipt claim missing or false: {claim_name}",
                    "release-index.yaml",
                    details={"claim": claim_name},
                )
                ok = False

    return ok


def _validate_receipt_paths_and_fields(path_obj: Path, payload: dict, *, expected_mode: str, expected_head: str | None,
                                        code_base: str, errors) -> tuple[bool, dict]:
    if not isinstance(payload, dict):
        add_entry(errors, f"{code_base}_invalid_schema", "receipt payload must be JSON object", "release-index.yaml")
        return False, {}

    if payload.get("schema_version") != "1.0.0":
        add_entry(errors, f"{code_base}_invalid_schema", "receipt schema_version must be 1.0.0", "release-index.yaml")
    if payload.get("receipt_type") != "lifecycle-canary":
        add_entry(errors, f"{code_base}_invalid_schema", "receipt receipt_type must be lifecycle-canary", "release-index.yaml")

    mode = payload.get("mode")
    rtype = payload.get("type")
    if mode != expected_mode or rtype != expected_mode:
        add_entry(
            errors,
            f"{code_base}_invalid_mode",
            "receipt mode/type mismatch",
            "release-index.yaml",
            details={"expected": expected_mode, "mode": mode, "type": rtype},
        )
        return False, {}

    if payload.get("status") != "passed":
        add_entry(errors, f"{code_base}_invalid_schema", "receipt status must be passed", "release-index.yaml")
        return False, {}

    if payload.get("hermes_version") != CANDIDATE_HERMES_VERSION:
        add_entry(
            errors,
            f"{code_base}_invalid_version",
            f"receipt hermes_version must be {CANDIDATE_HERMES_VERSION}",
            "release-index.yaml",
            details={"expected": CANDIDATE_HERMES_VERSION, "actual": payload.get("hermes_version")},
        )
        return False, {}

    candidate_head = payload.get("candidate_head")
    if not isinstance(candidate_head, str) or not re.fullmatch(r"[0-9a-f]{40}", candidate_head):
        add_entry(
            errors,
            f"{code_base}_invalid_head",
            "receipt candidate_head must be a full 40-hex sha",
            "release-index.yaml",
        )
        return False, {}

    if expected_head is not None and candidate_head != expected_head:
        add_entry(
            errors,
            f"{code_base}_invalid_head",
            "receipt candidate_head does not match repository HEAD",
            "release-index.yaml",
            details={"expected": expected_head, "actual": candidate_head},
        )
        return False, {}

    candidates = payload.get("candidate_profiles")
    if not isinstance(candidates, list):
        add_entry(errors, f"{code_base}_invalid_type", "receipt candidate_profiles must be list", "release-index.yaml")
        return False, {}
    if set(candidates) != CANDIDATE_PROFILES:
        add_entry(
            errors,
            f"{code_base}_invalid_profile_set",
            "receipt candidate_profiles mismatch",
            "release-index.yaml",
            details={"expected": sorted(CANDIDATE_PROFILES), "actual": sorted(candidates)},
        )
        return False, {}

    return True, payload


def _validate_host_receipt(path: Path, *, expected_head: str | None, errors):
    blob = _read_receipt_blob(path, errors, "compatibility_receipt")
    if blob is None:
        return False, None, None

    try:
        payload = json.loads(blob.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        add_entry(errors, "compatibility_receipt_invalid_schema", f"host receipt invalid JSON: {exc}", "release-index.yaml")
        return False, None, None

    digest = _sha256_hex(blob)
    ok, parsed = _validate_receipt_paths_and_fields(path, payload, expected_mode="host", expected_head=expected_head,
                                                    code_base="compatibility_receipt", errors=errors)

    claims_ok = ok and _validate_receipt_claims(parsed, COMPATIBILITY_REQUIREMENT_CLAIMS, "compatibility_receipt", errors)

    archive_flags = parsed.get("flags") if isinstance(parsed, dict) else None
    if not isinstance(archive_flags, dict):
        add_entry(errors, "compatibility_receipt_invalid_schema", "host receipt missing flags", "release-index.yaml")
        return False, None, None
    if _normalize_archive_records(archive_flags.get("archive_records", {}), "compatibility_receipt", errors) is None:
        return False, None, None

    return bool(ok and claims_ok), parsed, digest


def _validate_docker_receipt(path: Path, *, host_payload: dict, host_digest: str | None,
                             expected_head: str | None, errors) -> bool:
    blob = _read_receipt_blob(path, errors, "compatibility_receipt")
    if blob is None:
        return False

    try:
        payload = json.loads(blob.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        add_entry(errors, "compatibility_receipt_invalid_schema", f"docker receipt invalid JSON: {exc}", "release-index.yaml")
        return False

    ok, parsed = _validate_receipt_paths_and_fields(
        path, payload,
        expected_mode="docker",
        expected_head=expected_head,
        code_base="compatibility_receipt",
        errors=errors,
    )
    if not ok:
        return False

    if not _validate_receipt_claims(parsed, ("all_claims",), "compatibility_receipt", errors, require_all_claims_only=False):
        ok = False

    archive_flags = parsed.get("flags") if isinstance(parsed, dict) else None
    if not isinstance(archive_flags, dict):
        add_entry(errors, "compatibility_receipt_invalid_schema", "docker receipt missing flags", "release-index.yaml")
        return False

    host_receipt_claims = archive_flags.get("host_receipt_claims")
    if not _validate_receipt_claims(
        {"claims": host_receipt_claims} if isinstance(host_receipt_claims, dict) else {},
        COMPATIBILITY_REQUIREMENT_CLAIMS,
        "compatibility_receipt",
        errors,
    ):
        ok = False

    host_image = archive_flags.get("image_id")
    if not isinstance(host_image, str) or not re.fullmatch(r"sha256:[0-9a-fA-F]{64}", host_image):
        add_entry(
            errors,
            "compatibility_receipt_invalid_image",
            "docker receipt image_id must be immutable sha256:<64hex>",
            "release-index.yaml",
            details={"image_id": host_image},
        )
        ok = False

    if not isinstance(host_payload, dict):
        add_entry(errors, "compatibility_receipt_invalid_mode", "host receipt required for docker validation", "release-index.yaml")
        return False

    if archive_flags.get("host_receipt_mode") != "host":
        add_entry(errors, "compatibility_receipt_invalid_mode", "docker host_receipt_mode must be host", "release-index.yaml")
        ok = False
    if archive_flags.get("host_receipt_status") != "passed":
        add_entry(errors, "compatibility_receipt_invalid_schema", "docker host_receipt_status must be passed", "release-index.yaml")
        ok = False

    if host_digest is not None and archive_flags.get("host_receipt_sha256") != host_digest:
        add_entry(
            errors,
            "compatibility_receipt_mismatched_host_hash",
            "docker receipt host_receipt_sha256 mismatch",
            "release-index.yaml",
            details={"expected": host_digest, "actual": archive_flags.get("host_receipt_sha256")},
        )
        ok = False

    host_records = archive_flags.get("host_archive_hashes")
    docker_records = _normalize_archive_records(host_records, "compatibility_receipt", errors)
    if docker_records is None:
        ok = False

    host_archive_records = host_payload.get("flags", {}) if isinstance(host_payload, dict) else {}
    host_records_normalized = _normalize_archive_records(host_archive_records.get("archive_records", {}), "compatibility_receipt", errors)
    if host_records_normalized is None:
        ok = False

    if host_records_normalized is not None and docker_records is not None:
        if host_records_normalized != docker_records:
            add_entry(
                errors,
                "compatibility_receipt_mismatched_archive_records",
                "docker host_archive_hashes mismatch host archive_records",
                "release-index.yaml",
                details={"expected": host_records_normalized, "actual": docker_records},
            )
            ok = False

    return bool(ok)


def _validate_provenance(root: Path, errors):
    path = root / "PROVENANCE.md"
    text = _read_text_file(path, errors, "provenance_missing")
    if text is None:
        return

    rows, parse_error = _parse_provenance_table(text)
    if rows is None:
        add_entry(errors, "provenance_malformed", parse_error, "PROVENANCE.md")
        return

    if len(rows) != len(REQUIRED_PROVENANCE_COMPONENTS):
        add_entry(
            errors,
            "provenance_component_missing",
            f"expected {len(REQUIRED_PROVENANCE_COMPONENTS)} provenance rows, found {len(rows)}",
            "PROVENANCE.md",
        )

    normalized_rows = {}
    for row in rows:
        component = _normalise_component_key(row.get("component", ""))
        if not component:
            add_entry(errors, "provenance_malformed", "provenance row missing component", "PROVENANCE.md")
            continue
        if component in normalized_rows:
            add_entry(errors, "provenance_component_duplicate", f"duplicate provenance component: {component}", "PROVENANCE.md")
            continue
        normalized_rows[component] = row

    for required in REQUIRED_PROVENANCE_COMPONENTS:
        row = normalized_rows.get(required)
        if row is None:
            continue
        tags = {segment.strip().lower() for segment in row.get("status", "").split("|") if segment.strip()}
        provenance_tags = {segment.strip().lower() for segment in row.get("provenance", "").split("|") if segment.strip()}
        notes = row.get("notes", "").lower()

        if required == "owner-agent":
            owner_terms = {"newly authored", "original", "pending", "publication"}
            owner_text = " ".join([notes, " ".join(sorted(tags)), " ".join(sorted(provenance_tags))]).strip()
            if not all(term in owner_text for term in owner_terms):
                add_entry(
                    errors,
                    "provenance_row_policy",
                    "owner provenance row missing required lifecycle tags",
                    "PROVENANCE.md",
                    details={"component": required},
                )
            continue

        if required in _RUNTIME_MANIFEST_EXPECTATIONS:
            row_text = " ".join([value for value in row.values() if isinstance(value, str)]).lower()
            _validate_runtime_manifest_and_payload(root, required, {required: row_text}, errors)
            continue

        status_text = f" {row.get('status', '').lower()} {row.get('provenance', '').lower()} {notes} "

        if "no-payload" not in status_text and "no payload" not in status_text:
            add_entry(
                errors,
                "provenance_row_policy",
                "provenance row must state no payload",
                "PROVENANCE.md",
                details={"component": required},
            )
        if not any(token in status_text for token in ["blocked", "pending", "unresolved"]):
            add_entry(
                errors,
                "provenance_row_policy",
                "provenance row must indicate blocker/pending/unresolved state",
                "PROVENANCE.md",
                details={"component": required},
            )
        if any(token in status_text for token in ["ready", "authorized", "licensed", "ready_pending", "publication-authorized"]):
            add_entry(
                errors,
                "provenance_component_status",
                "unresolved component marked ready/authorized/licensed",
                "PROVENANCE.md",
                details={"component": required},
            )
        continue

    for required in REQUIRED_PROVENANCE_COMPONENTS:
        if required not in normalized_rows:
            add_entry(errors, "provenance_component_missing", f"missing provenance component: {required}", "PROVENANCE.md")

    for component in normalized_rows:
        if component not in REQUIRED_PROVENANCE_COMPONENTS:
            add_entry(errors, "provenance_component_extra", f"extra provenance component: {component}", "PROVENANCE.md")


def _runtime_has_hidden_part(path: Path) -> bool:
    return any(part.startswith(".") for part in path.parts)


def _runtime_source_check(path: Path, component: str, payload_codes: Mapping[str, str], errors):
    source = path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(source, filename=path.as_posix())
    except SyntaxError as exc:
        add_entry(
            errors,
            payload_codes["syntax"],
            "runtime source file has syntax error",
            path.as_posix(),
            line=exc.lineno,
            details={"component": component},
        )
        return

    if component != "art-runtime":
        return

    allowed_roots = _RUNTIME_IMPORT_ALLOWED_ROOTS.get(component, set())

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".")[0]
                if root in allowed_roots:
                    continue
                if root:
                    add_entry(
                        errors,
                        payload_codes["import"],
                        f"runtime import root not allowed: {root}",
                        path.as_posix(),
                        line=getattr(node, "lineno", None),
                        details={"component": component, "module": root},
                    )
        elif isinstance(node, ast.ImportFrom):
            if node.level > 0:
                continue
            if not node.module:
                continue
            root = node.module.split(".")[0]
            if root in allowed_roots:
                continue
            if root:
                add_entry(
                    errors,
                    payload_codes["import"],
                    f"runtime import root not allowed: {root}",
                    path.as_posix(),
                    line=getattr(node, "lineno", None),
                    details={"component": component, "module": root},
                )

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Name) and func.id in _RUNTIME_FORBIDDEN_CALLS:
            add_entry(
                errors,
                payload_codes["call"],
                f"runtime call not allowed: {func.id}",
                path.as_posix(),
                line=getattr(node, "lineno", None),
                details={"component": component, "call": func.id},
            )
            continue
        if isinstance(func, ast.Attribute) and func.attr in _RUNTIME_FORBIDDEN_CALLS:
            add_entry(
                errors,
                payload_codes["call"],
                f"runtime call not allowed: {func.attr}",
                path.as_posix(),
                line=getattr(node, "lineno", None),
                details={"component": component, "call": func.attr},
            )



def _validate_runtime_payload(root: Path, component: str, rules: Mapping[str, object], errors):
    runtime_dir = root / "runtimes" / component
    if not runtime_dir.is_dir():
        add_entry(
            errors,
            "provenance_component_missing",
            f"runtime directory missing: runtimes/{component}",
            "PROVENANCE.md",
            details={"component": component},
        )
        return

    payload_codes = rules["payload_error_code"]

    def _normalize_owned_path(value: str) -> Path:
        stripped = str(value).strip()
        normalized = stripped
        if normalized.startswith("./"):
            normalized = normalized[2:]
        parts = Path(normalized).parts
        if len(parts) >= 3 and parts[0] == "runtimes" and parts[1] == component:
            normalized = Path(*parts[2:]).as_posix()
        return Path(normalized)

    owned_files = [_normalize_owned_path(path) for path in rules["owned_files"]]
    owned_set = {path for path in owned_files}
    owner_paths = {p.as_posix() for p in owned_set}

    allowed_dir_parts = {Path(".")}
    for owned in owned_files:
        cur = Path(owned).parent
        while cur.as_posix() != ".":
            allowed_dir_parts.add(cur)
            cur = cur.parent

    for item in runtime_dir.rglob("*"):
        rel = item.relative_to(runtime_dir)
        rel_path = rel.as_posix()
        if rel_path == ".":
            continue

        if _runtime_has_hidden_part(rel):
            add_entry(
                errors,
                payload_codes["hidden"],
                "runtime path hidden",
                f"runtimes/{component}/{rel_path}",
                details={"component": component},
            )

        st = item.lstat()
        if stat.S_ISLNK(st.st_mode):
            add_entry(
                errors,
                payload_codes["symlink"],
                "runtime payload symlink found",
                f"runtimes/{component}/{rel_path}",
                details={"component": component},
            )
            continue

        if item.is_dir():
            if rel not in allowed_dir_parts:
                add_entry(
                    errors,
                    payload_codes["unowned"],
                    "runtime contains unexpected directory",
                    f"runtimes/{component}/{rel_path}",
                    details={"component": component},
                )
            continue

        if not item.is_file():
            add_entry(
                errors,
                payload_codes["non_regular"],
                "runtime payload entry not regular file",
                f"runtimes/{component}/{rel_path}",
                details={"component": component},
            )
            continue

        if rel_path not in owner_paths:
            add_entry(
                errors,
                payload_codes["unowned"],
                "runtime contains unowned payload file",
                f"runtimes/{component}/{rel_path}",
                details={"component": component},
            )
            continue

        if st.st_mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH):
            add_entry(
                errors,
                payload_codes["executable"],
                "runtime payload file has executable mode",
                f"runtimes/{component}/{rel_path}",
                details={"component": component},
            )

        if rel.suffix == ".py":
            _runtime_source_check(item, component, payload_codes, errors)

    for owned in owned_files:
        owned_path = runtime_dir / owned
        if not owned_path.exists():
            add_entry(
                errors,
                payload_codes["missing"],
                "runtime owned payload file missing",
                f"runtimes/{component}/{owned}",
                details={"component": component},
            )


def _validate_runtime_manifest_and_payload(root: Path, component: str, rows_by_component: Mapping[str, str], errors):
    rules = _RUNTIME_MANIFEST_EXPECTATIONS.get(component)
    if rules is None:
        return

    row_text = rows_by_component.get(component, "")
    if not row_text:
        add_entry(
            errors,
            "provenance_component_missing",
            f"missing provenance row: {component}",
            "PROVENANCE.md",
            details={"component": component},
        )
        return

    for required in rules["provenance_terms"]:
        if required not in row_text:
            add_entry(
                errors,
                "provenance_row_policy",
                f"{component} provenance row missing required term: {required}",
                "PROVENANCE.md",
                details={"component": component, "missing": required},
            )

    for forbidden in rules["forbidden_terms"]:
        if forbidden in row_text:
            add_entry(
                errors,
                "provenance_component_status",
                f"{component} provenance row contains forbidden term: {forbidden}",
                "PROVENANCE.md",
                details={"component": component, "forbidden": forbidden},
            )

    runtime_manifest = root / "runtimes" / component / "runtime.yaml"
    manifest_text = _read_text_file(runtime_manifest, errors, "provenance_component_missing")
    if manifest_text is None:
        return

    if not manifest_text.strip():
        add_entry(
            errors,
            "runtime_manifest_syntax",
            f"runtime manifest for {component} is empty",
            f"runtimes/{component}/runtime.yaml",
            details={"component": component},
        )
        return

    lines = manifest_text.splitlines()
    for line_no, raw_line in enumerate(lines, start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" in line or line.startswith("-"):
            continue
        add_entry(
            errors,
            "runtime_manifest_syntax",
            f"runtime manifest has malformed line: {line}",
            f"runtimes/{component}/runtime.yaml",
            line=line_no,
            details={"component": component},
        )

    manifest = _parse_distribution_yaml(manifest_text)

    expected = {
        "name": rules["name"],
        "version": rules["version"],
        "description": rules["description"],
        "stdlib_only": rules["stdlib_only"],
        "python_requires": rules["python_requires"],
        "dependencies": rules["dependencies"],
        "publication_authority": rules["publication_authority"],
        "owned_files": rules["owned_files"],
    }

    for key, expected_value in expected.items():
        if key not in manifest:
            add_entry(
                errors,
                rules["manifest_error_code"],
                f"{component} manifest missing required key: {key}",
                f"runtimes/{component}/runtime.yaml",
                details={"component": component, "missing": key},
            )

    for key, expected_value in expected.items():
        if key not in manifest:
            continue
        actual = manifest.get(key)
        if key == "description":
            if not isinstance(actual, str) or not actual.strip():
                add_entry(
                    errors,
                    rules["manifest_error_code"],
                    f"{component} manifest {key} mismatch",
                    f"runtimes/{component}/runtime.yaml",
                    details={"component": component, "expected": expected_value, "actual": actual},
                )
        else:
            if key == "owned_files":
                expected_value = rules["owned_files"]
            if actual != expected_value:
                add_entry(
                    errors,
                    "runtime_manifest_value_mismatch" if component == "art-runtime" else "provenance_row_policy",
                    f"{component} manifest field mismatch: {key}",
                    f"runtimes/{component}/runtime.yaml",
                    details={"component": component, "expected": expected_value, "actual": actual},
                )

    if set(manifest.keys()) != set(expected.keys()):
        add_entry(
            errors,
            rules["manifest_error_code"],
            f"{component} manifest contains unexpected keys",
            f"runtimes/{component}/runtime.yaml",
            details={
                "component": component,
                "expected": sorted(expected.keys()),
                "actual": sorted(manifest.keys()),
            },
        )

    _validate_runtime_payload(root, component, rules, errors)


def _validate_owner_contract(root: Path, errors):
    owner_dir = root / "profiles" / "owner-agent"
    if not owner_dir.is_dir():
        add_entry(errors, "owner_payload_mismatch", "owner payload directory missing", "profiles/owner-agent")
        return

    discovered_files = []
    for path in owner_dir.rglob("*"):
        rel = path.relative_to(owner_dir).as_posix()
        if rel == "":
            continue

        if path.is_symlink():
            add_entry(errors, "owner_payload_mismatch", "symlink inside owner payload", f"profiles/owner-agent/{rel}")
            continue

        if any(part.startswith(".") for part in rel.split("/")):
            add_entry(errors, "owner_payload_mismatch", "hidden path inside owner payload", f"profiles/owner-agent/{rel}")

        if path.is_dir():
            if rel not in REQUIRED_OWNER_PAYLOAD_DIRECTORIES:
                add_entry(errors, "owner_payload_mismatch", "unexpected owner payload directory", f"profiles/owner-agent/{rel}")
            continue

        discovered_files.append(rel)

    required_files = [item for item in REQUIRED_OWNER_PAYLOAD_FILES if item != "skills"] + [REQUIRED_OWNER_SKILL_FILE]
    if sorted(discovered_files) != sorted(required_files):
        add_entry(
            errors,
            "owner_payload_mismatch",
            "owner payload files do not match required recursive contract",
            "profiles/owner-agent",
            details={"actual": sorted(discovered_files), "expected": required_files},
        )
        return

    if not (owner_dir / REQUIRED_OWNER_SKILL_FILE).is_file():
        add_entry(
            errors,
            "owner_payload_mismatch",
            f"required owner skill file missing: {REQUIRED_OWNER_SKILL_FILE}",
            "profiles/owner-agent",
            details={"expected": REQUIRED_OWNER_SKILL_FILE},
        )
        return

    distribution_path = owner_dir / "distribution.yaml"
    distribution_text = _read_text_file(distribution_path, errors, "owner_contract_mismatch")
    if distribution_text is not None:
        manifest = _parse_distribution_yaml(distribution_text)
        required_owned = [
            "README.md",
            "SOUL.md",
            "config.yaml",
            "distribution.yaml",
            "skills",
        ]
        if manifest.get("name") != "owner-agent":
            add_entry(errors, "distribution_contract_mismatch", "distribution name must be owner-agent", "profiles/owner-agent/distribution.yaml")
        if manifest.get("version") != "0.1.0-dev":
            add_entry(errors, "distribution_contract_mismatch", "distribution version must be 0.1.0-dev", "profiles/owner-agent/distribution.yaml")
        if not str(manifest.get("description", "")).strip():
            add_entry(errors, "distribution_contract_mismatch", "distribution description missing", "profiles/owner-agent/distribution.yaml")
        if manifest.get("distribution_owned") != required_owned:
            add_entry(
                errors,
                "distribution_contract_mismatch",
                "distribution_owned must match payload contract",
                "profiles/owner-agent/distribution.yaml",
                details={"actual": manifest.get("distribution_owned"), "expected": required_owned},
            )
        for forbidden in {"author", "license", "source", "installed_at", "hermes_requires", "env_requires"}:
            if forbidden in manifest:
                add_entry(
                    errors,
                    "distribution_contract_mismatch",
                    f"distribution must omit {forbidden}",
                    "profiles/owner-agent/distribution.yaml",
                )

    config_path = owner_dir / "config.yaml"
    config_text = _read_text_file(config_path, errors, "owner_contract_mismatch")
    if config_text is not None:
        config = _parse_nested_yaml(config_text)
        expected_top_level = {"terminal", "memory", "skills"}
        terminal = config.get("terminal") if isinstance(config.get("terminal"), dict) else None
        memory = config.get("memory") if isinstance(config.get("memory"), dict) else None
        skills = config.get("skills") if isinstance(config.get("skills"), dict) else None
        if set(config.keys()) != expected_top_level:
            add_entry(errors, "distribution_contract_mismatch", "config must contain only terminal, memory, skills", "profiles/owner-agent/config.yaml")
        if terminal is None:
            add_entry(errors, "distribution_contract_mismatch", "terminal section missing", "profiles/owner-agent/config.yaml")
        else:
            if terminal.get("home_mode") != "profile" or not terminal.get("auto_source_bashrc") is False or terminal.get("shell_init_files") != []:
                add_entry(errors, "distribution_contract_mismatch", "terminal contract mismatch", "profiles/owner-agent/config.yaml")
        if memory is None:
            add_entry(errors, "distribution_contract_mismatch", "memory section missing", "profiles/owner-agent/config.yaml")
        else:
            if memory.get("memory_enabled") is not False or memory.get("user_profile_enabled") is not False:
                add_entry(errors, "distribution_contract_mismatch", "memory contract mismatch", "profiles/owner-agent/config.yaml")
        if skills is None:
            add_entry(errors, "distribution_contract_mismatch", "skills section missing", "profiles/owner-agent/config.yaml")
        else:
            if skills.get("write_approval") is not True:
                add_entry(errors, "distribution_contract_mismatch", "skills contract mismatch", "profiles/owner-agent/config.yaml")

    soul_text = _read_text_file(owner_dir / "SOUL.md", errors, "owner_contract_mismatch")
    if soul_text is not None:
        required_terms = [f"[{field}]" for field in OWNER_FIELDS]
        for term in required_terms:
            if term not in soul_text:
                add_entry(
                    errors,
                    "owner_contract_mismatch",
                    f"SOUL missing required phrase: {term}",
                    "profiles/owner-agent/SOUL.md",
                )

    skill_text = _read_text_file(owner_dir / "skills" / "client-agent-operations" / "SKILL.md", errors, "owner_contract_mismatch")
    if skill_text is not None:
        if not skill_text.startswith("---\n"):
            add_entry(errors, "owner_contract_mismatch", "skill file must include YAML frontmatter at byte zero", "profiles/owner-agent/skills/client-agent-operations/SKILL.md")
        frontmatter, body = _parse_skill_frontmatter(skill_text)
        if frontmatter is None:
            add_entry(errors, "owner_contract_mismatch", "skill frontmatter malformed", "profiles/owner-agent/skills/client-agent-operations/SKILL.md")
        else:
            if frontmatter.get("name") != "client-agent-operations":
                add_entry(errors, "owner_contract_mismatch", "skill name mismatch", "profiles/owner-agent/skills/client-agent-operations/SKILL.md")
            description = str(frontmatter.get("description", ""))
            if not description.startswith("Use when ") or "client" not in description.lower() or "owner" not in description.lower():
                add_entry(errors, "owner_contract_mismatch", "skill description mismatch", "profiles/owner-agent/skills/client-agent-operations/SKILL.md")
            if str(frontmatter.get("author", "")) != "Hermes Agent Team":
                add_entry(errors, "owner_contract_mismatch", "skill author mismatch", "profiles/owner-agent/skills/client-agent-operations/SKILL.md")
            if str(frontmatter.get("license", "")) != "Pending owner decision":
                add_entry(errors, "owner_contract_mismatch", "skill license mismatch", "profiles/owner-agent/skills/client-agent-operations/SKILL.md")
            if not frontmatter.get("version"):
                add_entry(errors, "owner_contract_mismatch", "skill version missing", "profiles/owner-agent/skills/client-agent-operations/SKILL.md")

        body_text = (body or "").lower()
        for phrase in [
            "status truth",
            "authority boundaries",
            "specialist routing",
            "privacy",
            "authentication",
            "durable knowledge",
            "handoff",
            "access revocation",
        ]:
            if phrase not in body_text:
                add_entry(
                    errors,
                    "owner_contract_mismatch",
                    f"skill body missing phrase: {phrase}",
                    "profiles/owner-agent/skills/client-agent-operations/SKILL.md",
                )



def is_forbidden_path(path: Path) -> bool:
    for part in path.parts:
        if part in FORBIDDEN_DIRECTORIES:
            return True
    return False


def is_forbidden_name(path: Path) -> bool:
    name = path.name.lower()
    if name in FORBIDDEN_FILENAMES:
        return True
    if name.startswith(".") and name.endswith("id_rsa"):
        return True
    lower = path.as_posix().lower()
    if any(token in lower for token in {"/auth/", "/session/", "/memory/", "/state/", "/log/", "/runtime-private/", "/secrets/"}):
        return True
    return False


def is_binary(data: bytes) -> bool:
    if b"\x00" in data:
        return True
    if b"\r" not in data and b"\n" not in data and len(data) > 512:
        printable = sum(32 <= b <= 126 or b in (9, 10, 13) for b in data)
        if printable / max(1, len(data)) < 0.8:
            return True
    return False


def _candidate_head_for_receipts(root: Path) -> str:
    proc = subprocess.run(
        [
            "git",
            "--no-replace-objects",
            "-C",
            str(root.resolve()),
            "rev-parse",
            "HEAD",
        ],
        capture_output=True,
        text=True,
    )

    if proc.returncode != 0:
        return CANDIDATE_HEAD_PLACEHOLDER

    candidate_head = (proc.stdout.splitlines()[:1] or [""])[0].strip()
    if not re.fullmatch(r"[0-9a-f]{40}", candidate_head):
        return CANDIDATE_HEAD_PLACEHOLDER
    return candidate_head


def _validate_compatibility_receipts(
    root: Path,
    errors,
    *,
    candidate_head: str,
    host_receipt: str | None,
    docker_receipt: str | None,
) -> bool:
    if host_receipt is None and docker_receipt is None:
        return False

    if (host_receipt is None) != (docker_receipt is None):
        add_entry(errors, "receipt_arg_mismatch", "--host-receipt and --docker-receipt must be paired", "release-index.yaml")
        return False

    host_path = Path(str(host_receipt))
    docker_path = Path(str(docker_receipt))
    if not host_path.is_absolute():
        host_path = root / host_path
    if not docker_path.is_absolute():
        docker_path = root / docker_path

    host_ok, host_payload, host_digest = _validate_host_receipt(
        host_path,
        expected_head=candidate_head,
        errors=errors,
    )
    docker_ok = _validate_docker_receipt(
        docker_path,
        host_payload=host_payload or {},
        host_digest=host_digest,
        expected_head=candidate_head,
        errors=errors,
    )
    return bool(host_ok and docker_ok)


def _validate_obsolete_publication_blockers(blockers, location: str, errors):
    if blockers is None:
        return
    legacy_blockers = {"art_runtime_payload"}

    if isinstance(blockers, list):
        for blocker in blockers:
            if str(blocker).strip() in legacy_blockers:
                add_entry(
                    errors,
                    "publication_blocker_obsolete",
                    f"obsolete blocker declared in {location}: {blocker}",
                    "release-index.yaml",
                    details={"blocker": blocker, "location": location},
                )
        return

    if isinstance(blockers, dict):
        for blocker in blockers:
            if str(blocker).strip() in legacy_blockers:
                add_entry(
                    errors,
                    "publication_blocker_obsolete",
                    f"obsolete blocker declared in {location}: {blocker}",
                    "release-index.yaml",
                    details={"blocker": blocker, "location": location},
                )
        return

    if blockers is not None:
        add_entry(errors, "invalid_schema", f"{location} must be list or object", "release-index.yaml")


def validate_root(root: Path):
    errors = []
    warnings = []
    release_index = {
        "schema_version": None,
        "release_status": None,
        "components": [],
        "compatibility": {},
        "publication": {},
    }

    index_path = root / "release-index.yaml"
    if not index_path.exists():
        add_entry(errors, "invalid_index", "missing release-index.yaml", str(index_path.relative_to(root)))
        return release_index, errors, warnings

    try:
        raw_index = index_path.read_text(encoding="utf-8")
    except OSError as exc:
        add_entry(
            errors,
            "invalid_index",
            f"unable to read release-index.yaml: {exc}",
            str(index_path.relative_to(root)),
        )
        return release_index, errors, warnings

    try:
        release_index = json.loads(raw_index)
    except json.JSONDecodeError:
        add_entry(errors, "invalid_index", "release-index.yaml is not valid JSON", "release-index.yaml")
        return release_index, errors, warnings

    if not isinstance(release_index, dict):
        add_entry(errors, "invalid_index", "release-index.yaml is not a JSON object", "release-index.yaml")
        return release_index, errors, warnings

    if release_index.get("schema_version") != REQUIRED_SCHEMA_VERSION:
        add_entry(errors, "invalid_schema", "unsupported schema_version", "release-index.yaml")

    release_status = str(release_index.get("release_status", ""))
    if release_status not in REQUIRED_RELEASE_STATUSES:
        add_entry(
            errors,
            "invalid_schema",
            f"release_status must be one of {sorted(REQUIRED_RELEASE_STATUSES)}",
            "release-index.yaml",
        )

    comp_obj = release_index.get("components")
    if not isinstance(comp_obj, list):
        add_entry(errors, "component_count", "components must be a list", "release-index.yaml")
        return release_index, errors, warnings

    if len(comp_obj) != len(REQUIRED_COMPONENTS):
        add_entry(
            errors,
            "component_count",
            f"expected {len(REQUIRED_COMPONENTS)} components, found {len(comp_obj)}",
            "release-index.yaml",
        )

    seen = set()
    names = []
    component_summary = []
    for component in comp_obj if isinstance(comp_obj, list) else []:
        if not isinstance(component, dict):
            add_entry(errors, "component_path_invalid", "component entry must be object", "release-index.yaml")
            continue

        name = component.get("name")
        if not isinstance(name, str) or not name:
            add_entry(errors, "component_name", "component name missing", "release-index.yaml")
            continue
        if name in seen:
            add_entry(errors, "duplicate_component", f"duplicate component: {name}", name)
            continue
        seen.add(name)
        names.append(name)

        path_field = component.get("path")
        if not isinstance(path_field, str) or not path_field.strip():
            add_entry(errors, "component_path_invalid", "component path missing", name)
            continue

        if path_field.startswith("/") or "/../" in path_field or path_field.startswith("../") or path_field == ".." or path_field.startswith("./"):
            add_entry(errors, "component_path_invalid", f"component path traversal/absolute not allowed: {path_field}", name)
            continue

        normalized = os.path.normpath(path_field)
        if normalized.startswith("..") or os.path.isabs(normalized):
            add_entry(errors, "component_path_invalid", f"component path traversal/absolute not allowed: {path_field}", name)
            continue

        comp_path = (root / normalized).resolve()
        root_real = root.resolve()
        try:
            in_root = comp_path == root_real or str(comp_path).startswith(str(root_real) + os.sep)
        except Exception:
            in_root = False
        if not in_root:
            add_entry(errors, "component_path_invalid", f"component outside canonical root: {path_field}", name)
            continue

        if not comp_path.is_dir():
            add_entry(errors, "component_path_not_found", f"component directory missing: {path_field}", name)
            continue

        if name not in REQUIRED_COMPONENTS or normalized != REQUIRED_COMPONENTS[name]:
            if name not in REQUIRED_COMPONENTS:
                add_entry(errors, "component_name", f"unknown component name: {name}", name)
            if normalized != REQUIRED_COMPONENTS.get(name):
                add_entry(errors, "component_path_invalid", f"unexpected path for component {name}: {path_field}", name)
            continue

        expected_component_states = REQUIRED_RELEASE_COMPONENT_STATE.get(
            release_status,
            REQUIRED_RELEASE_COMPONENT_STATE[REQUIRED_RELEASE_STATUS],
        )

        expected = expected_component_states.get(name)
        if expected is not None:
            version = str(component.get("version", ""))
            status = str(component.get("status", ""))
            if version != expected["version"]:
                add_entry(
                    errors,
                    "component_version_mismatch",
                    f"component {name} version mismatch",
                    name,
                    details={"expected": expected["version"], "actual": component.get("version")},
                )
            if status != expected["status"]:
                add_entry(
                    errors,
                    "component_status_mismatch",
                    f"component {name} status mismatch",
                    name,
                    details={"expected": expected["status"], "actual": component.get("status")},
                )

        component_summary.append(
            {
                "name": name,
                "path": normalized,
                "version": str(component.get("version", "")),
                "status": str(component.get("status", "")),
            }
        )

    missing_components = set(REQUIRED_COMPONENTS) - set(names)
    if missing_components:
        add_entry(
            errors,
            "component_count",
            "missing components: " + ", ".join(sorted(missing_components)),
            "release-index.yaml",
        )

    compatibility = release_index.get("compatibility", {})
    if not isinstance(compatibility, dict):
        add_entry(errors, "invalid_schema", "compatibility must be an object", "release-index.yaml")
    else:
        hermes_requirement = compatibility.get("hermes_requirement")
        if str(hermes_requirement).lower() not in {"unresolved", "pending"}:
            add_entry(
                errors,
                "invalid_schema",
                "compatibility.hermes_requirement must be unresolved/pending",
                "release-index.yaml",
            )

    _validate_obsolete_publication_blockers(release_index.get("blockers"), "top-level blockers", errors)

    publication = release_index.get("publication", {})
    if not isinstance(publication, dict):
        add_entry(errors, "invalid_schema", "publication must be an object", "release-index.yaml")
    else:
        publication_status = str(publication.get("status", "")).lower()
        _validate_obsolete_publication_blockers(publication.get("blockers"), "publication.blockers", errors)
        if publication_status == "blocked":
            add_entry(warnings, "publication_blocked", "publication is blocked", "release-index.yaml")
            blockers = publication.get("blockers", [])
            if isinstance(blockers, list):
                for blocker in blockers:
                    add_entry(
                        warnings,
                        "publication_blocker",
                        f"release blocker present: {blocker}",
                        "release-index.yaml",
                        details={"blocker": blocker},
                    )
            elif isinstance(blockers, dict):
                for blocker, state in blockers.items():
                    if state not in {"resolved", "ready"}:
                        add_entry(
                            warnings,
                            "publication_blocker",
                            f"release blocker present: {blocker}",
                            "release-index.yaml",
                            details={"blocker": blocker, "state": state},
                        )
            else:
                add_entry(errors, "invalid_schema", "publication.blockers must be list or object", "release-index.yaml")
        elif publication_status == "ready":
            blockers = publication.get("blockers", {})
            if isinstance(blockers, list):
                if blockers:
                    add_entry(
                        errors,
                        "publication_ready_blocker_present",
                        "publication is marked ready but blockers list is not empty",
                        "release-index.yaml",
                        details={"blockers": blockers},
                    )
            elif isinstance(blockers, dict):
                for blocker, state in blockers.items():
                    if str(state).lower() not in {"resolved", "ready", "complete"}:
                        add_entry(
                            errors,
                            "publication_ready_blocker_state",
                            "publication blocker state must be resolved, ready, or complete",
                            "release-index.yaml",
                            details={"blocker": blocker, "state": state},
                        )
            else:
                add_entry(errors, "invalid_schema", "publication.blockers must be list or object", "release-index.yaml")

            if str(compatibility.get("hermes_requirement", "")).lower() != "ready":
                add_entry(
                    errors,
                    "compatibility_not_ready",
                    "publication can only be ready when compatibility is ready",
                    "release-index.yaml",
                    details={"hermes_requirement": compatibility.get("hermes_requirement")},
                )

            if str(release_index.get("release_status", "")).lower() != "ready":
                add_entry(
                    errors,
                    "release_status_not_ready",
                    "release_status must be ready when publication is ready",
                    "release-index.yaml",
                    details={"release_status": release_index.get("release_status")},
                )

            for component in component_summary:
                if str(component.get("status")) != "ready":
                    add_entry(
                        errors,
                        "component_not_ready",
                        "all components must be ready when publication is ready",
                        component.get("name"),
                        details={"name": component.get("name"), "status": component.get("status")},
                    )
        elif publication_status == "ready_pending":
            pass
        else:
            add_entry(errors, "invalid_schema", "publication.status must be blocked or ready", "release-index.yaml")

    if not errors:
        _validate_provenance(root, errors)
        _validate_owner_contract(root, errors)

    return release_index, errors, warnings



def collect_scans(root: Path, deny_terms, errors):
    findings = []
    root_str = str(root.resolve())

    for raw_path, dirnames, filenames in os.walk(root, topdown=True, followlinks=False):
        current = Path(raw_path)
        rel_root = current.relative_to(root)

        if rel_root == Path(".git"):
            dirnames[:] = []
            continue

        # Skip nested .git metadata trees.
        dirnames[:] = [d for d in dirnames if d != ".git"]

        for dirname in list(dirnames):
            subdir = current / dirname
            rel = subdir.relative_to(root)
            if rel == Path(".git"):
                continue
            stat_res = os.lstat(subdir)
            if stat.S_ISLNK(stat_res.st_mode):
                add_entry(
                    errors,
                    "symlink_found",
                    "symlink encountered",
                    rel.as_posix(),
                )
                continue
            if is_forbidden_path(subdir) or is_forbidden_name(subdir):
                add_entry(
                    errors,
                    "forbidden_path",
                    "forbidden directory encountered",
                    rel.as_posix(),
                )

        for filename in filenames:
            file_path = current / filename
            rel = file_path.relative_to(root)

            st = os.lstat(file_path)
            if stat.S_ISLNK(st.st_mode):
                add_entry(errors, "symlink_found", "symlink encountered", rel.as_posix())
                continue

            if rel.parts and rel.parts[0] == ".git":
                continue

            name_lower = file_path.name.lower()
            if name_lower.endswith(tuple(FORBIDDEN_SUFFIXES)):
                add_entry(errors, "forbidden_filename", "forbidden binary/archive file", rel.as_posix())
                continue

            if is_forbidden_name(file_path):
                add_entry(errors, "forbidden_filename", "forbidden filename encountered", rel.as_posix())
                continue

            if stat.S_ISREG(st.st_mode) and st.st_nlink > 1:
                add_entry(
                    errors,
                    "hardlink_found",
                    "hard-linked file encountered",
                    rel.as_posix(),
                    details={"nlink": st.st_nlink},
                )

            if file_path.suffix.lower() == ".pyc":
                add_entry(errors, "forbidden_filename", "forbidden compiled bytecode file", rel.as_posix())
                continue

            try:
                raw = file_path.read_bytes()
            except OSError as exc:
                add_entry(errors, "binary_file", f"unable to read file: {exc}", rel.as_posix())
                continue

            # The approved intake is the one intentional binary public asset.
            # Its form-field contract is checked by release tests; all other
            # payload files remain text-only for privacy scanning.
            if rel.as_posix() == "templates/OWNER-INTAKE.pdf":
                continue
            if is_binary(raw):
                add_entry(errors, "binary_file", "binary/undecodable file", rel.as_posix())
                continue

            try:
                text = raw.decode("utf-8")
            except UnicodeDecodeError:
                add_entry(errors, "binary_file", "non-utf8 file", rel.as_posix())
                continue

            lower_text = text.lower()
            for term in deny_terms:
                if term in lower_text:
                    for ln, line in enumerate(text.splitlines(), start=1):
                        if term in line.lower():
                            add_entry(
                                findings,
                                "deny_term",
                                "forbidden deny term found",
                                rel.as_posix(),
                                line=ln,
                                details={"rule": "deny_term"},
                            )
                            break

            for pattern_def in SECRET_PATTERNS:
                regex = pattern_def["pattern"]
                if regex.search(text):
                    for ln, line in enumerate(text.splitlines(), start=1):
                        if regex.search(line):
                            add_entry(
                                findings,
                                pattern_def["code"],
                                "high-confidence secret pattern detected",
                                rel.as_posix(),
                                line=ln,
                                details={"rule": pattern_def["code"]},
                            )
                            break

    findings_sorted = sorted(
        findings,
        key=lambda item: (item.get("code", ""), item.get("path", ""), item.get("line", 0)),
    )
    return findings_sorted


def verify_deny_terms(paths):
    terms = []
    errors = []
    for path in paths:
        try:
            raw = Path(path).read_text(encoding="utf-8")
        except FileNotFoundError:
            add_entry(errors, "deny_term_file_invalid", "deny term file missing", path)
            continue
        except OSError:
            add_entry(errors, "deny_term_file_invalid", "unable to read deny term file", path)
            continue

        normalized = [line.strip().lower() for line in raw.splitlines()]
        normalized = [line for line in normalized if line]
        if not normalized:
            add_entry(errors, "deny_term_file_empty", "deny term file is empty", path)
            continue
        terms.extend(normalized)

    return terms, errors


def verify_top_level(root: Path):
    errors = []
    entries = {p.name for p in root.iterdir()}
    allowed = set(EXPECTED_TOP_LEVEL_ENTRIES)
    if (root / ".git").exists():
        allowed.add(".git")

    for name in sorted(entries):
        if name not in allowed:
            add_entry(errors, "top_level_entry", f"unexpected top-level entry: {name}", name)
    return errors


def parse_args(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True, help="repository root")
    parser.add_argument("--host-receipt", help="path to host compatibility receipt")
    parser.add_argument("--docker-receipt", help="path to docker compatibility receipt")
    parser.add_argument("--deny-term", action="append", default=[], help="case-insensitive deny term")
    parser.add_argument("--deny-term-file", action="append", default=[], help="file containing deny terms")
    parser.add_argument("--require-ready", action="store_true", help="require blockers resolved")
    return parser.parse_args(argv)


def sort_findings(items):
    return sorted(
        items,
        key=lambda item: (
            ERROR_ORDER.index(item.get("code")) if item.get("code") in ERROR_ORDER else 999,
            item.get("code", ""),
            item.get("path", ""),
            item.get("line", 0),
            item.get("message", ""),
        ),
    )


def main(argv=None):
    args = parse_args(argv)

    root = Path(args.root).resolve()
    if not root.is_dir():
        payload = {
            "ok": False,
            "release_ready": False,
            "errors": [
                {
                    "code": "invalid_root",
                    "message": "provided root is not a directory",
                    "path": str(root),
                }
            ],
            "warnings": [],
            "components": [],
            "component_summary": [],
        }
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 2

    top_level_errors = verify_top_level(root)

    index, index_errors, warnings = validate_root(root)
    components = []
    if isinstance(index, dict) and isinstance(index.get("components"), list):
        for component in index["components"]:
            if isinstance(component, dict) and isinstance(component.get("name"), str):
                components.append(component.get("name"))

    combined_errors = top_level_errors + index_errors

    direct_terms, term_errors = verify_deny_terms(args.deny_term_file)
    combined_errors.extend(term_errors)

    deny_terms = []
    deny_terms.extend([t.lower() for t in args.deny_term if t.strip()])
    deny_terms.extend([t.lower() for t in direct_terms])

    scan_findings = collect_scans(root, deny_terms, combined_errors)

    combined_errors.extend(scan_findings)

    candidate_head = _candidate_head_for_receipts(root)
    receipts_supplied = args.host_receipt is not None or args.docker_receipt is not None
    compatibility_evidence_ok = (
        _validate_compatibility_receipts(
            root,
            combined_errors,
            candidate_head=candidate_head,
            host_receipt=args.host_receipt,
            docker_receipt=args.docker_receipt,
        )
        if receipts_supplied
        else True
    )

    # Combine component summary deterministically.
    component_summary = []
    if isinstance(index, dict):
        for component in index.get("components", []) if isinstance(index.get("components", []), list) else []:
            if isinstance(component, dict) and "name" in component and "path" in component:
                component_summary.append(
                    {
                        "name": component.get("name"),
                        "path": component.get("path"),
                        "version": component.get("version"),
                        "status": component.get("status"),
                    }
                )

    component_summary = sorted(component_summary, key=lambda item: item.get("name", ""))

    publication = index.get("publication", {}) if isinstance(index, dict) else {}
    publication_status = str(publication.get("status", "")).lower() if isinstance(publication, dict) else ""
    # A local candidate is ready when its repository contract is clean.  Public
    # publication is deliberately separate: it needs owner and external gates
    # that this verifier neither performs nor can truthfully certify.
    publication_ready = publication_status == "ready" and not combined_errors

    verification_fatal_errors = [
        err
        for err in combined_errors
        if err.get("code") != "publication_blocked"
        and err.get("code") != "publication_blocker"
        and not err.get("code", "").startswith("compatibility_")
        and err.get("code") != "receipt_arg_mismatch"
    ]
    verification_ok = len(verification_fatal_errors) == 0
    private_candidate_ready = bool(verification_ok and compatibility_evidence_ok)
    release_ready = private_candidate_ready

    fatal_errors = [err for err in combined_errors if err.get("code") != "publication_blocked"]
    fatal_errors = [err for err in fatal_errors if err.get("code") not in {"publication_blocker"}]
    ok = len(fatal_errors) == 0

    if publication_status != "ready":
        # If not explicitly ready, keep release not ready and keep blocker signal in warnings.
        if not any(err["code"] == "publication_blocked" for err in warnings):
            warnings.append(
                {
                    "code": "publication_blocked",
                    "message": "release is blocked",
                    "path": "release-index.yaml",
                }
            )


    errors_out = sort_findings([err for err in combined_errors if err.get("code") != "publication_blocker"])
    warning_entries = [
        err for err in combined_errors if err.get("code") in {"publication_blocked", "publication_blocker"}
    ]
    warning_entries.extend(warnings)
    deduped_warning_map = {}
    for entry in warning_entries:
        key = json.dumps(entry, sort_keys=True)
        deduped_warning_map[key] = entry
    warnings_out = list(deduped_warning_map.values())
    warnings_out = sort_findings(warnings_out)

    result = {
        "ok": ok,
        "verification_ok": verification_ok,
        "compatibility_evidence_ok": compatibility_evidence_ok,
        "compatibility_evidence": "external-not-performed" if not receipts_supplied else "receipt-validated",
        "private_candidate_ready": private_candidate_ready,
        "publication_ready": publication_ready,
        "release_ready": release_ready,
        "errors": errors_out,
        "warnings": warnings_out,
        "components": sorted(set(components)),
        "component_summary": component_summary,
    }

    print(json.dumps(result, indent=2, sort_keys=True))

    if args.require_ready:
        return 1 if not result["release_ready"] or fatal_errors else 0

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
