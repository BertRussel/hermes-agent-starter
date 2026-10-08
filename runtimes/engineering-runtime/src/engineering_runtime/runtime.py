"""Pure Python helpers for the engineering runtime contract tests."""

from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any, Dict, Iterable, List, Mapping, Sequence


_ALLOWED_ROLES = {"maker", "reviewer", "researcher"}
_ALLOWED_OUTCOMES = {
    "authorized",
    "started",
    "completed_verified",
    "failed",
    "cancelled",
}
_FORBIDDEN_ENV_FRAGMENTS = (
    "TOKEN",
    "SECRET",
    "PASSWORD",
    "CREDENTIAL",
    "API_KEY",
    "PRIVATE_KEY",
    "ACCESS_KEY",
    "AUTH",
)


def _as_posix_path(path: Any) -> str:
    if not isinstance(path, str):
        raise ValueError("path entries must be strings")
    if not path:
        raise ValueError("path entries must be non-empty")
    if "\\" in path or path.startswith("/"):
        raise ValueError("changed paths must be POSIX relative paths")
    if path in {".", ".."}:
        raise ValueError("invalid path")
    parts = tuple(PurePosixPath(path).parts)
    if ".." in parts or "." in parts:
        raise ValueError("path traversal is not permitted")
    if "" in parts:
        raise ValueError("invalid path")
    return PurePosixPath(path).as_posix()


def _contains_forbidden_env_key(key: Any) -> bool:
    if not isinstance(key, str):
        return False
    upper_key = key.upper()
    return any(fragment in upper_key for fragment in _FORBIDDEN_ENV_FRAGMENTS)


def _normalise_allowed_paths(allowed_paths: Iterable[Any]) -> List[str]:
    normalized: List[str] = []
    for path in allowed_paths:
        if not isinstance(path, str):
            raise ValueError("allowed path entries must be strings")
        if not path:
            raise ValueError("allowed path entries must be non-empty")
        normalized.append(_as_posix_path(path))
    return normalized


def build_profile_launch(
    role: str,
    executable: str,
    profile_root: str,
    home_root: str,
    inherited_env: Mapping[str, str] | None = None,
) -> tuple[list[str], dict[str, str]]:
    """Build a minimal profile launch command for a validated engineering role."""
    if role not in _ALLOWED_ROLES:
        raise ValueError("unsupported role")

    executable_path = Path(executable)
    if not executable_path.is_file():
        raise FileNotFoundError("executable path is not a regular file")

    profile_root_path = Path(profile_root)
    if not profile_root_path.is_dir():
        raise ValueError("profile_root must be a directory")

    home_root_path = Path(home_root)
    if not home_root_path.is_dir():
        raise ValueError("home_root must be a directory")

    role_profile = profile_root_path / role
    if not role_profile.is_dir():
        raise ValueError("role profile directory is missing")

    if inherited_env is not None:
        for key in inherited_env.keys():
            if _contains_forbidden_env_key(key):
                raise ValueError("inherited_env contains forbidden key")

    return [str(executable_path), "--profile", str(role_profile)], {"HOME": str(home_root_path)}


def validate_git_snapshot(snapshot: Mapping[str, Any], expected: Mapping[str, Any]) -> Dict[str, Any]:
    """Validate snapshot metadata against expected snapshot expectations."""
    if not isinstance(snapshot, Mapping):
        raise ValueError("snapshot must be a mapping")
    if not isinstance(expected, Mapping):
        raise ValueError("expected must be a mapping")

    required = {"repo", "remote", "head", "parent", "clean", "changed_paths", "allowed_paths"}
    snapshot_keys = set(snapshot.keys())
    expected_keys = set(expected.keys())
    if snapshot_keys != expected_keys:
        raise ValueError("snapshot and expected keys must match")
    if snapshot_keys != required:
        missing_snapshot = required - snapshot_keys
        missing_expected = required - expected_keys
        if missing_snapshot:
            raise ValueError(f"snapshot missing key {next(iter(missing_snapshot))}")
        if missing_expected:
            raise ValueError(f"expected missing key {next(iter(missing_expected))}")
        raise ValueError("unexpected snapshot keys present")

    for key in ("repo", "remote", "head", "parent"):
        if snapshot[key] != expected[key]:
            raise ValueError(f"snapshot {key} mismatch")

    if snapshot["clean"] is not True or expected["clean"] is not True:
        raise ValueError("snapshot must be clean")

    changed_paths_raw = snapshot["changed_paths"]
    if not isinstance(changed_paths_raw, Sequence) or isinstance(changed_paths_raw, (str, bytes)):
        raise ValueError("changed_paths must be a list")
    changed_paths = [_as_posix_path(path) for path in changed_paths_raw]

    expected_changed_paths_raw = expected["changed_paths"]
    if not isinstance(expected_changed_paths_raw, Sequence) or isinstance(
        expected_changed_paths_raw, (str, bytes)
    ):
        raise ValueError("changed_paths must be a list")
    expected_changed_paths = [_as_posix_path(path) for path in expected_changed_paths_raw]

    if changed_paths != expected_changed_paths:
        raise ValueError("snapshot changed_paths mismatch")

    allowed_paths_raw = expected["allowed_paths"]
    if not isinstance(allowed_paths_raw, Sequence) or isinstance(allowed_paths_raw, (str, bytes)):
        raise ValueError("allowed_paths must be a list")
    allowed_paths = _normalise_allowed_paths(allowed_paths_raw)

    snapshot_allowed_paths_raw = snapshot["allowed_paths"]
    if not isinstance(snapshot_allowed_paths_raw, Sequence) or isinstance(
        snapshot_allowed_paths_raw, (str, bytes)
    ):
        raise ValueError("allowed_paths must be a list")
    snapshot_allowed_paths = _normalise_allowed_paths(snapshot_allowed_paths_raw)
    if allowed_paths != snapshot_allowed_paths:
        raise ValueError("snapshot allowed_paths mismatch")

    allowed_parts = [PurePosixPath(path).parts for path in allowed_paths]
    for path in changed_paths:
        parts = PurePosixPath(path).parts
        matched = any(parts[: len(prefix)] == prefix for prefix in allowed_parts if len(prefix) <= len(parts))
        if not matched:
            raise ValueError(f"path {path!r} outside allowed paths")

    result = dict(snapshot)
    result["changed_paths"] = changed_paths
    result["allowed_paths"] = allowed_paths
    return result


def build_event(
    event_type: str,
    run_id: str,
    phase_id: str,
    outcome: str,
    timestamp: str,
) -> Dict[str, Any]:
    """Create a normalized runtime event dictionary."""
    if not all(isinstance(item, str) for item in (event_type, run_id, phase_id, timestamp)):
        raise TypeError("event_type/run_id/phase_id/timestamp must be strings")
    if not all(item.strip() for item in (event_type, run_id, phase_id, timestamp)):
        raise ValueError("event_type/run_id/phase_id/timestamp must be non-blank")
    if outcome not in _ALLOWED_OUTCOMES:
        raise ValueError("unsupported outcome")

    return {
        "version": 1,
        "event_type": event_type,
        "run_id": run_id,
        "phase_id": phase_id,
        "outcome": outcome,
        "timestamp": timestamp,
    }


def validate_transition(current_state: str, next_state: str) -> str:
    """Validate transition between two phase states."""
    transitions = {
        "authorized": {"started"},
        "started": {"completed_verified", "failed", "cancelled"},
    }

    if current_state not in transitions:
        raise ValueError("invalid current state")
    allowed = transitions[current_state]
    if next_state not in allowed:
        raise ValueError("invalid state transition")
    return next_state


def _extract_tool_name(call: Any) -> str | None:
    if not isinstance(call, Mapping):
        return None
    name = call.get("name")
    if isinstance(name, str):
        return name

    function = call.get("function")
    if isinstance(function, Mapping):
        function_name = function.get("name")
        if isinstance(function_name, str):
            return function_name

    return None


def audit_session(db_path: str, session_id: str) -> Dict[str, int]:
    """Summarize delegate signals for exactly one session."""
    if not isinstance(session_id, str) or not session_id.strip():
        raise ValueError("session_id must be a non-blank string")

    db_file = Path(db_path)
    if not db_file.is_file():
        raise ValueError("db_path must be an existing file")

    db_path_uri = f"file:{db_file.resolve().as_posix()}?mode=ro"
    with sqlite3.connect(db_path_uri, uri=True) as conn:
        rows = conn.execute(
            "SELECT tool_calls FROM messages WHERE session_id = ?",
            (session_id,),
        ).fetchall()
        if len(rows) != 1:
            raise ValueError("expected exactly one messages row")

        payload = rows[0][0]
        try:
            tool_calls = json.loads(payload)
        except json.JSONDecodeError as exc:
            raise ValueError("invalid tool_calls JSON") from exc

        if not isinstance(tool_calls, list):
            raise ValueError("tool_calls must be a list")

        delegate_task_count = 0
        for call in tool_calls:
            if _extract_tool_name(call) == "delegate_task":
                delegate_task_count += 1

        async_delegation_count = conn.execute(
            "SELECT COUNT(*) FROM async_delegations WHERE origin_session = ?",
            (session_id,),
        ).fetchone()[0]

    return {
        "session_id": session_id,
        "delegate_task_count": int(delegate_task_count),
        "async_delegation_count": int(async_delegation_count),
    }


def _parse_event_timestamp(raw: Any) -> datetime:
    if not isinstance(raw, str):
        raise ValueError("timestamp must be an ISO string")
    try:
        return datetime.strptime(raw, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError as exc:
        raise ValueError("timestamp must be ISO 8601 format") from exc


def timing_report(events: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    """Build a timing report from ordered phase events."""
    if not isinstance(events, Sequence) or isinstance(events, (str, bytes)):
        raise ValueError("events must be a sequence")
    if not events:
        raise ValueError("events cannot be empty")

    run_id = None
    started_events: Dict[str, datetime] = {}
    phase_totals: Dict[str, float] = {}
    ordered_phases: List[str] = []
    open_phase: str | None = None
    previous_timestamp: datetime | None = None
    first_started_timestamp: datetime | None = None
    final_terminal_timestamp: datetime | None = None

    for index, event in enumerate(events):
        if not isinstance(event, Mapping):
            raise ValueError("events must contain mappings")

        event_version = event.get("version")
        event_type = event.get("event_type")
        event_run_id = event.get("run_id")
        phase_id = event.get("phase_id")
        outcome = event.get("outcome")
        timestamp_raw = event.get("timestamp")

        if event_version != 1:
            raise ValueError("event version must be 1")
        if event_type != "phase":
            raise ValueError("invalid event_type")
        if not all(isinstance(value, str) and value for value in (event_run_id, phase_id, outcome, timestamp_raw)):
            raise ValueError("invalid event payload")
        if outcome not in _ALLOWED_OUTCOMES:
            raise ValueError("invalid outcome")

        if run_id is None:
            run_id = event_run_id
        elif event_run_id != run_id:
            raise ValueError("all events must share a run_id")

        event_timestamp = _parse_event_timestamp(timestamp_raw)
        if previous_timestamp is not None and event_timestamp < previous_timestamp:
            raise ValueError("events must be ordered")
        previous_timestamp = event_timestamp

        if outcome == "started":
            if phase_id in started_events:
                raise ValueError("duplicate phase start")
            if open_phase is not None:
                raise ValueError("phase overlap is not allowed")
            started_events[phase_id] = event_timestamp
            open_phase = phase_id
            if first_started_timestamp is None:
                first_started_timestamp = event_timestamp
            ordered_phases.append(phase_id)
            continue

        if outcome in {"completed_verified", "failed", "cancelled"}:
            if open_phase != phase_id:
                raise ValueError("phase terminal without matching started")
            started_at = started_events.get(phase_id)
            if started_at is None:
                raise ValueError("terminal without started")
            if phase_id in phase_totals:
                raise ValueError("duplicate phase terminal")
            elapsed = (event_timestamp - started_at).total_seconds()
            if elapsed < 0:
                raise ValueError("negative phase duration")
            phase_totals[phase_id] = elapsed
            open_phase = None
            final_terminal_timestamp = event_timestamp
            continue

        raise ValueError("invalid transition outcome")

    if open_phase is not None:
        raise ValueError("missing terminal outcome for phase")

    if first_started_timestamp is None or final_terminal_timestamp is None:
        raise ValueError("missing phase timing boundaries")

    phase_data = {phase: {"total_seconds": float(total)} for phase, total in phase_totals.items()}
    total_seconds = float((final_terminal_timestamp - first_started_timestamp).total_seconds())
    return {
        "version": 1,
        "phases": phase_data,
        "total_seconds": total_seconds,
    }
