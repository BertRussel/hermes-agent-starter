import importlib.util
import json
import sqlite3
import tempfile
import unittest.mock
from datetime import datetime
from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[2]
RUNTIME_PATH = (
    REPO_ROOT
    / "runtimes"
    / "engineering-runtime"
    / "src"
    / "engineering_runtime"
    / "runtime.py"
)


def _ts(seconds: int) -> str:
    return f"2026-01-01T12:00:{seconds:02d}Z"


class EngineeringRuntimeContractTests(unittest.TestCase):
    def _load_runtime(self):
        self.assertTrue(
            RUNTIME_PATH.is_file(),
            f"Expected placeholder module missing at {RUNTIME_PATH}",
        )
        spec = importlib.util.spec_from_file_location("engineering_runtime.runtime", str(RUNTIME_PATH))
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)  # type: ignore[union-attr]
        return module

    def test_build_profile_launch(self):
        runtime = self._load_runtime()
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            profile_root = tmp / "profiles"
            home_root = tmp / "home"
            home_root.mkdir()
            for role in ("maker", "reviewer", "researcher"):
                (profile_root / role).mkdir(parents=True)

            executable = tmp / "bin" / "agent"
            executable.parent.mkdir(parents=True)
            executable.write_text("#!/usr/bin/env python3\n")

            inherited_env = {
                "HOME": "bad-home",
                "PATH": "/usr/bin",
            }

            for role in ("maker", "reviewer", "researcher"):
                command, env = runtime.build_profile_launch(
                    role=role,
                    executable=str(executable),
                    profile_root=profile_root,
                    home_root=home_root,
                    inherited_env=inherited_env,
                )
                self.assertEqual(command[0], str(executable))
                self.assertEqual(env.get("HOME"), str(home_root))
                self.assertNotIn("AWS_SECRET_ACCESS_KEY", env)
                self.assertNotIn("HERMES_API_TOKEN", env)
                self.assertEqual(set(env), {"HOME"})
                self.assertIn(str(profile_root / role), " ".join(command))

            bad_forbidden_env = {
                "HERMES_API_TOKEN": "forbidden",
            }
            with self.assertRaises(ValueError):
                runtime.build_profile_launch(
                    role="maker",
                    executable=str(executable),
                    profile_root=profile_root,
                    home_root=home_root,
                    inherited_env=bad_forbidden_env,
                )

            bad_calls = [
                ("", ""),
                (str(tmp / "missing"), str(profile_root)),
            ]
            for exe, pr in bad_calls:
                with self.assertRaises((ValueError, FileNotFoundError, OSError)):
                    runtime.build_profile_launch("maker", exe, profile_root if exe else Path(pr), home_root)
            with self.assertRaises((ValueError, KeyError)):
                runtime.build_profile_launch("invalid", str(executable), profile_root, home_root)

    def test_validate_git_snapshot(self):
        runtime = self._load_runtime()
        actual = {
            "repo": str(REPO_ROOT),
            "remote": "file:///tmp/origin",
            "head": "a" * 40,
            "parent": "b" * 40,
            "clean": True,
            "changed_paths": ["runtimes/engineering-runtime/README.md"],
            "allowed_paths": ["runtimes/engineering-runtime", "tests/runtime"],
        }
        expected = dict(actual)
        mismatched = dict(actual)
        mismatched["head"] = "c" * 40

        self.assertEqual(runtime.validate_git_snapshot(actual, expected), actual)
        with self.assertRaises(ValueError):
            runtime.validate_git_snapshot({**actual, "clean": False}, expected)
        with self.assertRaises(ValueError):
            runtime.validate_git_snapshot({**actual, "changed_paths": ["../outside/path.py"]}, expected)
        with self.assertRaises(ValueError):
            runtime.validate_git_snapshot({**actual, "allowed_paths": []}, expected)
        with self.assertRaises(ValueError):
            runtime.validate_git_snapshot({**actual, "mismatch": True}, expected)
        with self.assertRaises(ValueError):
            runtime.validate_git_snapshot(actual, {**expected, "extra": 1})
        with self.assertRaises(ValueError):
            runtime.validate_git_snapshot({"changed_paths": ["runtimes/engineering-runtime/README.md"]}, expected)
        with self.assertRaises(ValueError):
            runtime.validate_git_snapshot(actual, mismatched)

    def test_build_event(self):
        runtime = self._load_runtime()
        event = runtime.build_event(
            event_type="phase",
            run_id="run-1",
            phase_id="build",
            outcome="started",
            timestamp=_ts(1),
        )
        self.assertEqual(event["version"], 1)
        self.assertEqual(event["outcome"], "started")
        with self.assertRaises(ValueError):
            runtime.build_event("phase", "run-1", "build", "done", _ts(2))
        with self.assertRaises(ValueError):
            runtime.build_event("phase", "run-1", "build", 7, _ts(2))
        with self.assertRaises(TypeError):
            runtime.build_event("phase", "run-1", "build", "started", _ts(2), payload={"x": 1})

    def test_validate_transition(self):
        runtime = self._load_runtime()
        self.assertEqual(runtime.validate_transition("authorized", "started"), "started")
        self.assertEqual(runtime.validate_transition("started", "completed_verified"), "completed_verified")
        self.assertEqual(runtime.validate_transition("started", "failed"), "failed")
        self.assertEqual(runtime.validate_transition("started", "cancelled"), "cancelled")
        for nxt in ("authorized", "started", "unknown"):
            with self.assertRaises(ValueError):
                runtime.validate_transition("completed_verified", nxt)

    def test_audit_session(self):
        runtime = self._load_runtime()
        with tempfile.TemporaryDirectory() as td:
            db_path = Path(td) / "session.db"
            with sqlite3.connect(db_path) as conn:
                conn.execute("CREATE TABLE messages (session_id TEXT NOT NULL, tool_calls TEXT NOT NULL)")
                conn.execute("CREATE TABLE async_delegations (origin_session TEXT NOT NULL, session_id TEXT NOT NULL)")
                conn.execute(
                    "INSERT INTO messages VALUES (?, ?)",
                    (
                        "session-alpha",
                        json.dumps([{"name": "delegate_task"}, {"name": "read_file"}, {"name": "delegate_task"}]),
                    ),
                )
                conn.execute(
                    "INSERT INTO async_delegations VALUES (?, ?)",
                    ("session-alpha", "async-1"),
                )

            report = runtime.audit_session(str(db_path), "session-alpha")
            self.assertEqual(report["session_id"], "session-alpha")
            self.assertEqual(report["delegate_task_count"], 2)
            self.assertEqual(report["async_delegation_count"], 1)

            with self.assertRaises(ValueError):
                runtime.audit_session(str(db_path), "")
            with self.assertRaises(ValueError):
                runtime.audit_session(str(db_path), "missing")
            with sqlite3.connect(db_path) as conn:
                conn.execute(
                    "INSERT INTO messages VALUES (?, ?)",
                    ("session-alpha", json.dumps([{"name": "delegate_task"}])),
                )
            with self.assertRaises(ValueError):
                runtime.audit_session(str(db_path), "session-alpha")

    def test_audit_session_readonly_uri(self):
        runtime = self._load_runtime()
        with tempfile.TemporaryDirectory() as td:
            db_path = Path(td) / "session.db"
            with sqlite3.connect(db_path) as conn:
                conn.execute("CREATE TABLE messages (session_id TEXT NOT NULL, tool_calls TEXT NOT NULL)")
                conn.execute("CREATE TABLE async_delegations (origin_session TEXT NOT NULL, session_id TEXT NOT NULL)")
                conn.execute(
                    "INSERT INTO messages VALUES (?, ?)",
                    ("session-beta", json.dumps([{"name": "delegate_task"}])),
                )

            expected_uri = f"file:{db_path.resolve().as_posix()}?mode=ro"
            original_connect = runtime.sqlite3.connect

            def capture_connect(database, *args, **kwargs):
                self.assertEqual(database, expected_uri)
                self.assertTrue(kwargs.get("uri", False))
                return original_connect(database, *args, **kwargs)

            with unittest.mock.patch.object(runtime.sqlite3, "connect", side_effect=capture_connect):
                runtime.audit_session(str(db_path), "session-beta")
            with sqlite3.connect(db_path) as conn:
                self.assertEqual(
                    conn.execute("SELECT count(*) FROM async_delegations WHERE origin_session = ?", ("session-beta",)).fetchone()[0],
                    0,
                )

    def test_timing_report(self):
        runtime = self._load_runtime()
        events = [
            runtime.build_event("phase", "run-1", "build", "started", _ts(0)),
            runtime.build_event("phase", "run-1", "build", "completed_verified", _ts(5)),
            runtime.build_event("phase", "run-1", "review", "started", _ts(6)),
            runtime.build_event("phase", "run-1", "review", "completed_verified", _ts(11)),
        ]
        report = runtime.timing_report(events)
        self.assertEqual(report["version"], 1)
        self.assertEqual(report["phases"]["build"]["total_seconds"], 5.0)
        self.assertEqual(report["phases"]["review"]["total_seconds"], 5.0)
        self.assertEqual(report["total_seconds"], 11.0)

        gap_events = [
            runtime.build_event("phase", "run-2", "build", "started", _ts(0)),
            runtime.build_event("phase", "run-2", "build", "completed_verified", _ts(1)),
            runtime.build_event("phase", "run-2", "review", "started", _ts(3)),
            runtime.build_event("phase", "run-2", "review", "completed_verified", _ts(5)),
        ]
        gap_report = runtime.timing_report(gap_events)
        self.assertEqual(gap_report["phases"]["build"]["total_seconds"], 1.0)
        self.assertEqual(gap_report["phases"]["review"]["total_seconds"], 2.0)
        self.assertEqual(gap_report["total_seconds"], 5.0)
        self.assertNotEqual(gap_report["total_seconds"], 3.0)

        with self.assertRaises(ValueError):
            runtime.timing_report(list(reversed(events)))
        with self.assertRaises(ValueError):
            runtime.timing_report([runtime.build_event("phase", "run-1", "build", "started", _ts(0))])
