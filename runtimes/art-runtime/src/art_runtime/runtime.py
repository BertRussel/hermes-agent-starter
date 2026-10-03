"""Pure stdlib contract validators for the Art runtime."""

from __future__ import annotations

import copy
import json
from collections.abc import Mapping


_ASCII_LOWER_HEX = "0123456789abcdef"
_JOB_REQUIRED_KEYS = {
    "schema_version",
    "run_id",
    "capability",
    "inputs",
    "outputs",
    "limits",
    "external_access",
    "publication_authority",
}
_JOB_ENTRY_REQUIRED_KEYS = {"path", "sha256", "bytes"}
_CANDIDATE_REQUIRED_KEYS = {
    "schema_version",
    "run_id",
    "status",
    "files",
    "source_sha256",
    "privacy",
    "rights",
    "external_access",
    "publication_authority",
    "approval_receipt",
}
_CANDIDATE_ENTRY_REQUIRED_KEYS = {"path", "sha256", "bytes"}
_CANDIDATE_ALLOWED_STATES = {
    "candidate",
    "blocked",
    "rejected",
    "reviewable_awaiting_owner",
}

_MAX_INPUT_BYTES = 1_048_576
_MAX_OUTPUT_BYTES = 16_777_216
_MAX_CYCLES = 3

_ALLOWED_TRANSITIONS = {
    "initialized": {"candidate", "blocked"},
    "candidate": {"rejected", "blocked", "reviewable_awaiting_owner"},
    "rejected": {"candidate", "blocked"},
}


class ContractError(ValueError):
    """Structured validation failure with a stable machine-readable error code."""

    def __init__(self, code: str, message: str | None = None):
        super().__init__(message or code)
        self.code = code


def validate_job_contract(contract: Mapping) -> dict:
    if not isinstance(contract, Mapping):
        raise ContractError("invalid_job_contract")

    keys = set(contract.keys())
    if keys != _JOB_REQUIRED_KEYS:
        if _JOB_REQUIRED_KEYS - keys:
            raise ContractError("missing_job_root_keys")
        raise ContractError("unexpected_job_root_keys")

    schema_version = contract.get("schema_version")
    if not isinstance(schema_version, int) or isinstance(schema_version, bool) or schema_version != 1:
        raise ContractError("invalid_schema_version")

    run_id = contract.get("run_id")
    _validate_run_id(run_id)

    inputs_raw = contract.get("inputs")
    if type(inputs_raw) is not list:
        raise ContractError("invalid_inputs_type")

    outputs_raw = contract.get("outputs")
    if type(outputs_raw) is not list:
        raise ContractError("invalid_outputs_type")

    limits = _validate_limits(contract.get("limits"))

    if contract.get("external_access") is not False:
        raise ContractError("forbidden_authority")
    if contract.get("publication_authority") is not False:
        raise ContractError("forbidden_authority")

    inputs = []
    seen_inputs: set[str] = set()
    total_input_bytes = 0
    for item in inputs_raw:
        if not isinstance(item, Mapping):
            raise ContractError("invalid_input_entry")
        if set(item.keys()) != _JOB_ENTRY_REQUIRED_KEYS:
            raise ContractError("invalid_input_entry")

        path = validate_relative_path(item.get("path"))
        sha256 = validate_sha256(item.get("sha256"))
        bytes_value = item.get("bytes")
        _validate_non_negative_bytes(bytes_value)

        if path in seen_inputs:
            raise ContractError("duplicate_input_path")
        seen_inputs.add(path)
        total_input_bytes += int(bytes_value)

        inputs.append({"path": path, "sha256": sha256, "bytes": int(bytes_value)})

    if total_input_bytes > limits["max_input_bytes"]:
        raise ContractError("input_bytes_exceeded")

    outputs = []
    seen_outputs: set[str] = set()
    for item in outputs_raw:
        if not isinstance(item, str):
            raise ContractError("invalid_output_entry")
        path = validate_relative_path(item)
        if path in seen_outputs:
            raise ContractError("duplicate_output_path")
        seen_outputs.add(path)
        outputs.append(path)

    for path in seen_inputs:
        if path in seen_outputs:
            raise ContractError("input_output_alias")

    normalized = {
        "schema_version": 1,
        "run_id": str(run_id),
        "capability": str(contract.get("capability")),
        "inputs": inputs,
        "outputs": outputs,
        "limits": limits,
        "external_access": False,
        "publication_authority": False,
    }

    return copy.deepcopy(normalized)


def validate_candidate_manifest(manifest: Mapping) -> dict:
    if not isinstance(manifest, Mapping):
        raise ContractError("invalid_candidate_manifest")

    keys = set(manifest.keys())
    if keys != _CANDIDATE_REQUIRED_KEYS:
        if _CANDIDATE_REQUIRED_KEYS - keys:
            raise ContractError("missing_candidate_root_keys")
        raise ContractError("unexpected_candidate_root_keys")

    schema_version = manifest.get("schema_version")
    if not isinstance(schema_version, int) or isinstance(schema_version, bool) or schema_version != 1:
        raise ContractError("invalid_schema_version")

    run_id = manifest.get("run_id")
    _validate_run_id(run_id)

    status = manifest.get("status")
    if status not in _CANDIDATE_ALLOWED_STATES:
        raise ContractError("invalid_status")

    files_raw = manifest.get("files")
    if type(files_raw) is not list:
        raise ContractError("invalid_files_type")

    source_sha256_raw = manifest.get("source_sha256")
    if type(source_sha256_raw) is not list:
        raise ContractError("invalid_source_sha256_type")

    files = []
    seen_file_paths: set[str] = set()
    for item in files_raw:
        if not isinstance(item, Mapping):
            raise ContractError("invalid_file_entry")
        if set(item.keys()) != _CANDIDATE_ENTRY_REQUIRED_KEYS:
            raise ContractError("invalid_file_entry")

        path = validate_relative_path(item.get("path"))
        sha256 = validate_sha256(item.get("sha256"))
        bytes_value = item.get("bytes")
        _validate_non_negative_bytes(bytes_value)

        if path in seen_file_paths:
            raise ContractError("duplicate_file_path")
        seen_file_paths.add(path)
        files.append({"path": path, "sha256": sha256, "bytes": int(bytes_value)})

    source_sha256 = [_normalize_and_validate_sha256(item) for item in source_sha256_raw]

    privacy = manifest.get("privacy")
    if not isinstance(privacy, Mapping) or set(privacy.keys()) != {"contains_customer_data", "contains_secrets"}:
        raise ContractError("forbidden_privacy")
    if privacy.get("contains_customer_data") is not False or privacy.get("contains_secrets") is not False:
        raise ContractError("forbidden_privacy")

    rights = manifest.get("rights")
    if not isinstance(rights, Mapping) or set(rights.keys()) != {"state", "external_use_allowed"}:
        raise ContractError("forbidden_rights")
    if rights.get("state") != "unknown" or rights.get("external_use_allowed") is not False:
        raise ContractError("forbidden_rights")

    if manifest.get("external_access") is not False:
        raise ContractError("forbidden_authority")
    if manifest.get("publication_authority") is not False:
        raise ContractError("forbidden_authority")
    if manifest.get("approval_receipt") is not None:
        raise ContractError("invalid_approval_receipt")

    normalized = {
        "schema_version": 1,
        "run_id": str(run_id),
        "status": str(status),
        "files": files,
        "source_sha256": source_sha256,
        "privacy": {"contains_customer_data": False, "contains_secrets": False},
        "rights": {"state": "unknown", "external_use_allowed": False},
        "external_access": False,
        "publication_authority": False,
        "approval_receipt": None,
    }

    return copy.deepcopy(normalized)


def validate_relative_path(path: object) -> str:
    if not isinstance(path, str) or not path:
        raise ContractError("invalid_path")
    if path.startswith("/"):
        raise ContractError("invalid_path")
    if "\\" in path or "//" in path:
        raise ContractError("invalid_path")
    if "://" in path:
        raise ContractError("invalid_path")
    if any(ord(ch) < 32 for ch in path):
        raise ContractError("invalid_path")

    parts = path.split("/")
    if any(part == "" for part in parts):
        raise ContractError("invalid_path")
    for part in parts:
        if part in {".", ".."}:
            raise ContractError("invalid_path")
        if not _is_path_segment(part):
            raise ContractError("invalid_path")

    return path


def validate_sha256(raw: object) -> str:
    return _normalize_and_validate_sha256(raw)


def canonical_json_bytes(payload: object) -> bytes:
    try:
        text = json.dumps(
            payload,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        )
    except ValueError as exc:
        raise ValueError("payload must be JSON serializable") from exc
    return (text + "\n").encode("utf-8")


def validate_transition(current_state: str, next_state: str) -> str:
    if current_state not in _ALLOWED_TRANSITIONS:
        raise ContractError("invalid_transition")
    if next_state not in _ALLOWED_TRANSITIONS[current_state]:
        raise ContractError("invalid_transition")
    return next_state


def _is_path_segment(part: str) -> bool:
    if not part:
        return False
    if part[0] in "._-" or part[-1] in "._-":
        return False
    saw_dot = False
    for char in part:
        if char == ".":
            if saw_dot:
                return False
            saw_dot = True
            continue
        saw_dot = False
        if char.isalnum():
            continue
        if char in "_-":
            continue
        return False
    return True


def _validate_limits(limits: object) -> dict:
    if not isinstance(limits, Mapping):
        raise ContractError("invalid_limits_type")
    if set(limits.keys()) != {"max_input_bytes", "max_output_bytes", "max_cycles"}:
        raise ContractError("invalid_limits_type")

    max_input_bytes = limits.get("max_input_bytes")
    max_output_bytes = limits.get("max_output_bytes")
    max_cycles = limits.get("max_cycles")

    if not _is_non_bool_int(max_input_bytes) or not _is_non_bool_int(max_output_bytes) or not _is_non_bool_int(max_cycles):
        raise ContractError("invalid_limits_type")

    if not (0 < int(max_input_bytes) <= _MAX_INPUT_BYTES):
        raise ContractError("invalid_limits_values")
    if not (0 < int(max_output_bytes) <= _MAX_OUTPUT_BYTES):
        raise ContractError("invalid_limits_values")
    if not (0 < int(max_cycles) <= _MAX_CYCLES):
        raise ContractError("invalid_limits_values")

    return {
        "max_input_bytes": int(max_input_bytes),
        "max_output_bytes": int(max_output_bytes),
        "max_cycles": int(max_cycles),
    }


def _validate_non_negative_bytes(value: object) -> int:
    if not _is_non_bool_int(value):
        raise ContractError("invalid_bytes")
    if int(value) < 0:
        raise ContractError("invalid_bytes")
    return int(value)


def _validate_run_id(run_id: object) -> str:
    if not isinstance(run_id, str) or not run_id:
        raise ContractError("invalid_run_id")
    if len(run_id) > 63:
        raise ContractError("invalid_run_id")
    if run_id[0] == "-" or run_id[-1] == "-":
        raise ContractError("invalid_run_id")
    for char in run_id:
        if char.isalnum() or char in "_-":
            continue
        raise ContractError("invalid_run_id")
    for char in run_id:
        if char.isdigit() or char.islower() or char in "_-":
            continue
        raise ContractError("invalid_run_id")
    if ".." in run_id:
        raise ContractError("invalid_run_id")
    if "_" in run_id and run_id.endswith("_"):
        raise ContractError("invalid_run_id")
    return run_id


def _normalize_and_validate_sha256(raw: object) -> str:
    if not isinstance(raw, str):
        raise ContractError("invalid_sha256_type")
    if len(raw) != 64:
        raise ContractError("invalid_sha256_format")
    for char in raw:
        if char not in _ASCII_LOWER_HEX:
            raise ContractError("invalid_sha256_format")
    return raw


def _is_non_bool_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


__all__ = [
    "ContractError",
    "canonical_json_bytes",
    "validate_candidate_manifest",
    "validate_job_contract",
    "validate_relative_path",
    "validate_sha256",
    "validate_transition",
]
