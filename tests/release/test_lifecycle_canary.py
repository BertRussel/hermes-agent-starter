import argparse
import hashlib
import importlib.util
import inspect
import os
import pathlib
import json
import stat
import subprocess
import shutil
import textwrap
import tempfile
import unittest
from unittest import mock
from typing import Any, Callable, Iterable


REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
CANARY_SCRIPT = REPO_ROOT / "scripts" / "lifecycle_canary.py"


class LifecycleCanaryContractTests(unittest.TestCase):
    """RED tests for the future `scripts/lifecycle_canary.py` contract."""

    def _load_canary_module(self):
        self.assertTrue(
            CANARY_SCRIPT.is_file(),
            f"Lifecycle canary implementation missing: {CANARY_SCRIPT}",
        )
        spec = importlib.util.spec_from_file_location("lifecycle_canary", str(CANARY_SCRIPT))
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)  # type: ignore[union-attr]
        return module

    def _lookup(self, module: Any, *names: str):
        for name in names:
            if hasattr(module, name):
                return getattr(module, name)
        self.fail(f"missing expected symbol, tried: {', '.join(names)}")

    def _require_subcommands(self, parser: argparse.ArgumentParser) -> set[str]:
        subparser_actions = [action for action in parser._actions if isinstance(action, argparse._SubParsersAction)]
        self.assertEqual(len(subparser_actions), 1, "exactly one subparser group expected")
        subparsers = subparser_actions[0]
        return set(subparsers.choices.keys())

    def _make_parser(self, module: Any):
        build_parser = self._lookup(
            module,
            "build_parser",
            "build_argument_parser",
            "create_parser",
            "argument_parser",
        )
        parser = build_parser()
        self.assertIsInstance(parser, argparse.ArgumentParser)
        return parser

    def test_01_canary_script_exists(self):
        self.assertTrue(CANARY_SCRIPT.is_file(), f"expected file {CANARY_SCRIPT}")

    def test_02_public_api_symbols_include_phase_contract(self):
        module = self._load_canary_module()
        required = [
            "LifecycleCanaryError",
            "validate_candidate_head",
            "validate_work_root",
            "validate_candidate_profiles",
            "compute_candidate_inventory",
            "scan_candidate_profiles",
            "validate_path_no_follow",
            "validate_archive_member",
            "run_command",
            "write_json_receipt_atomically",
            "parse_phase_status",
            "run_host_canary",
            "run_docker_canary",
            "run_worker_phase",
            "build_receipt",
            "main",
        ]
        self.assertEqual(
            sorted(m for m in required if hasattr(module, m)),
            sorted(required),
            "public lifecycle contracts are incomplete",
        )

    def test_03_parser_exposes_expected_entrypoints(self):
        module = self._load_canary_module()
        parser = self._make_parser(module)
        commands = self._require_subcommands(parser)
        self.assertEqual(commands, {"host", "docker", "_worker"})

    def test_04_host_parser_accepts_canonical_inputs(self):
        module = self._load_canary_module()
        parser = self._make_parser(module)

        args = parser.parse_args(
            [
                "host",
                "--root",
                str(REPO_ROOT),
                "--candidate-head",
                "d" * 40,
                "--hermes",
                "/usr/bin/env",
                "--work-root",
                str(REPO_ROOT / ".tmp-host-work"),
                "--evidence",
                str(REPO_ROOT / ".tmp-evidence.json"),
            ]
        )
        self.assertEqual(args.command, "host")
        self.assertEqual(args.candidate_head, "d" * 40)
        self.assertEqual(args.root, str(REPO_ROOT))

    def test_05_docker_parser_requires_immutable_image_reference(self):
        module = self._load_canary_module()
        parser = self._make_parser(module)

        args = parser.parse_args(
            [
                "docker",
                "--root",
                str(REPO_ROOT),
                "--candidate-head",
                "d" * 40,
                "--image",
                "hermes:0.19.1",
                "--work-root",
                str(REPO_ROOT / ".tmp-docker-work"),
                "--host-work-root",
                str(REPO_ROOT / ".tmp-host-work-root"),
                "--host-archives",
                str(REPO_ROOT / ".tmp-host-archives"),
                "--host-receipt",
                str(REPO_ROOT / ".tmp-host.json"),
                "--evidence",
                str(REPO_ROOT / ".tmp-docker.json"),
                "--hermes-version",
                "0.19.1",
            ]
        )
        self.assertEqual(args.command, "docker")
        self.assertEqual(args.image, "hermes:0.19.1")
        self.assertEqual(args.host_work_root, str(REPO_ROOT / ".tmp-host-work-root"))
        self.assertEqual(args.host_archives, str(REPO_ROOT / ".tmp-host-archives"))

    def test_06_worker_parser_requires_mode_argument(self):
        module = self._load_canary_module()
        parser = self._make_parser(module)

        args = parser.parse_args([
            "_worker",
            "--mode",
            "docker",
            "--root",
            str(REPO_ROOT),
            "--candidate-head",
            "d" * 40,
            "--work-root",
            str(REPO_ROOT / ".tmp-worker-work"),
            "--input-receipt",
            str(REPO_ROOT / ".tmp-worker-input.json"),
            "--host-archives",
            str(REPO_ROOT / ".tmp-worker-archives"),
            "--execute",
            "--hermes-version",
            "0.20.5",
        ])
        self.assertEqual(args.command, "_worker")
        self.assertEqual(args.mode, "docker")
        self.assertEqual(args.hermes_version, "0.20.5")

    def _make_valid_host_receipt_payload(self, module: Any, candidate_head: str, records: dict[str, dict[str, Any]] | None = None,
                                       *, status: str = "passed") -> dict[str, Any]:
        if records is None:
            records = {
                profile: {
                    "filename": f"{profile}.tar",
                    "sha256": "0" * 64,
                    "members": ["README.md"],
                    "member_count": 1,
                }
                for profile in module.CANDIDATE_PROFILES
            }
        return {
            "mode": "host",
            "status": status,
            "candidate_head": candidate_head,
            "hermes_version": module.CANARY_LIMITS["required_hermes_version"],
            "claims": {"all_claims": True, "secrets_excluded": True},
            "flags": {"archive_records": records},
            "inventory_before": {
                "root": "candidate-root",
                "tree": "0" * 64,
                "entry_count": 0,
                "entries": [],
            },
            "inventory_after": {
                "root": "candidate-root",
                "tree": "0" * 64,
                "entry_count": 0,
                "entries": [],
            },
        }

    def test_06a_canary_limits_require_expected_hermes_version(self):
        module = self._load_canary_module()
        self.assertEqual(module.CANARY_LIMITS["required_hermes_version"], "0.20.5")

    def test_06b_host_receipt_validation_includes_member_count_and_key_set(self):
        module = self._load_canary_module()
        validate = self._lookup(module, "_validate_host_receipt_for_docker")

        candidate_head = "d" * 40
        payload = self._make_valid_host_receipt_payload(module, candidate_head)
        normalized = validate(payload=payload, candidate_head=candidate_head)
        self.assertEqual(normalized["status"], "passed")
        self.assertEqual(normalized["claims"]["all_claims"], True)
        for profile in module.CANDIDATE_PROFILES:
            self.assertIn(profile, normalized["archive_records"])
            self.assertIn("member_count", normalized["archive_records"][profile])

        mutated = dict(payload)
        mutated_records = dict(payload["flags"]["archive_records"])
        mutated_records = {**mutated_records}
        mutated_records.pop("owner-agent")
        mutated_payload = dict(payload)
        mutated_payload["flags"] = {"archive_records": mutated_records}
        with self.assertRaises(ValueError):
            validate(payload=mutated_payload, candidate_head=candidate_head)

        mutated_records = dict(payload["flags"]["archive_records"])
        mutated_records["extra"] = {
            "filename": "extra.tar",
            "sha256": "0" * 64,
            "members": ["extra.txt"],
            "member_count": 1,
        }
        mutated_payload = dict(payload)
        mutated_payload["flags"] = {"archive_records": mutated_records}
        with self.assertRaises(ValueError):
            validate(payload=mutated_payload, candidate_head=candidate_head)

        mutated_records = dict(payload["flags"]["archive_records"])
        mutated_profile = dict(mutated_records["owner-agent"])
        mutated_profile["member_count"] = 0
        mutated_records["owner-agent"] = mutated_profile
        mutated_payload = dict(payload)
        mutated_payload["flags"] = {"archive_records": mutated_records}
        with self.assertRaises(ValueError):
            validate(payload=mutated_payload, candidate_head=candidate_head)

    def test_07_worker_parser_requires_execution_flag(self):
        parser = self._make_parser(self._load_canary_module())
        with self.assertRaises(SystemExit):
            parser.parse_args(
                [
                    "_worker",
                    "--mode",
                    "docker",
                    "--root",
                    str(REPO_ROOT),
                    "--candidate-head",
                    "d" * 40,
                    "--work-root",
                    str(REPO_ROOT / ".tmp-worker-work"),
                    "--input-receipt",
                    str(REPO_ROOT / ".tmp-worker-input.json"),
                    "--host-archives",
                    str(REPO_ROOT / ".tmp-worker-archives"),
                ]
            )

    def test_08_main_forwards_worker_execution_flags(self):
        module = self._load_canary_module()
        with tempfile.TemporaryDirectory() as td:
            work = pathlib.Path(td)
            parser = self._make_parser(module)
            candidate_root = work / "candidate"
            candidate_root.mkdir()
            input_receipt = work / "host-receipt.json"
            input_receipt.write_text(
                json.dumps(
                    {
                        "mode": "host",
                        "status": "passed",
                        "candidate_head": "d" * 40,
                        "hermes_version": "0.20.5",
                        "claims": {"all_claims": True, "secrets_excluded": True},
                        "flags": {
                            "archive_records": {
                                profile: {
                                    "filename": f"{profile}.tar.gz",
                                    "sha256": "0" * 64,
                                    "members": [f"{profile}/local/canary-state.json"],
                                    "member_count": 1,
                                }
                                for profile in ["owner-agent", "art", "recon", "forge", "eve"]
                            }
                        },
                        "inventory_before": {"root": str(candidate_root), "tree": "0" * 64, "entries": [], "entry_count": 0},
                        "inventory_after": {"root": str(candidate_root), "tree": "0" * 64, "entries": [], "entry_count": 0},
                    },
                    sort_keys=True,
                ),
                encoding="utf-8",
            )

            work_root = work / "worker-work"
            (work_root / "archives").mkdir(parents=True)
            for profile in ["owner-agent", "art", "recon", "forge", "eve"]:
                archive = work_root / "archives" / f"{profile}.tar.gz"
                import tarfile

                with tarfile.open(archive, "w:gz") as tar:
                    pass

            with mock.patch.object(module, "run_worker_phase") as mock_run_worker:
                module.main(
                    [
                        "_worker",
                        "--mode",
                        "docker",
                        "--root",
                        str(candidate_root),
                        "--candidate-head",
                        "d" * 40,
                        "--work-root",
                        str(work_root),
                        "--input-receipt",
                        str(input_receipt),
                        "--host-archives",
                        str(work_root / "archives"),
                        "--hermes",
                        "/usr/bin/env",
                        "--execute",
                    ]
                )

            mock_run_worker.assert_called_once()
            kwargs = mock_run_worker.call_args.kwargs
            self.assertTrue(kwargs.get("execute"))
            self.assertFalse(kwargs.get("dry_run", True))

    def test_09_expected_candidate_profile_set_is_stable(self):
        module = self._load_canary_module()
        profiles = self._lookup(
            module,
            "CANDIDATE_PROFILES",
            "EXPECTED_CANDIDATE_PROFILES",
            "CANARY_CANDIDATE_PROFILES",
        )
        self.assertEqual(
            list(profiles),
            ["owner-agent", "art", "recon", "forge", "eve"],
        )

    def test_08_candidate_head_mismatch_is_rejected_before_mutation(self):
        module = self._load_canary_module()
        validate_candidate_head = self._lookup(
            module,
            "validate_candidate_head",
            "validate_candidate_commit",
            "assert_candidate_head",
        )
        validate = validate_candidate_head
        validate("d" * 40, "d" * 40)
        with self.assertRaises(ValueError):
            validate("d" * 40, "e" * 40)

    def test_09_work_root_relative_paths_and_nested_candidates_are_rejected(self):
        module = self._load_canary_module()
        with tempfile.TemporaryDirectory() as td:
            candidate_root = pathlib.Path(td) / "candidate"
            work_root = candidate_root / "nested-work"
            candidate_root.mkdir()
            nested = candidate_root / "nested-work"
            nested.mkdir(parents=True)

            validate_work_root = self._lookup(
                module,
                "validate_work_root",
                "validate_work_root_arg",
                "assert_valid_work_root",
            )
            with self.assertRaises(ValueError):
                validate_work_root(str(candidate_root), str(candidate_root))
            validate_work_root(str(candidate_root), str(work_root))
            with self.assertRaises(ValueError):
                validate_work_root(str(candidate_root), str(candidate_root / ".." / "candidate" / "nested-work"))

    def test_10_candidate_and_archive_paths_require_nofollow_and_non_symlink(self):
        module = self._load_canary_module()
        validator = self._lookup(
            module,
            "validate_path_no_follow",
            "validate_no_follow",
            "assert_no_follow_path",
        )

        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            target = root / "candidate"
            target.mkdir()

            candidate = root / "candidate-link"
            candidate.symlink_to(target)

            archive = root / "archive-link"
            archive.symlink_to(root)

            with self.assertRaises(ValueError):
                validator(candidate)
            validator(target)
            with self.assertRaises(ValueError):
                validator(archive)

    def test_11_duplicate_inode_payloads_are_rejected(self):
        module = self._load_canary_module()
        deduper = self._lookup(
            module,
            "validate_no_duplicate_inodes",
            "assert_no_duplicate_payload_inodes",
            "validate_payload_uniqueness",
        )

        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            src = root / "source"
            src.mkdir()
            original = root / "payload-a.txt"
            original.write_bytes(b"payload")
            linked = root / "payload-b.txt"
            os.link(original, linked)
            with self.assertRaises(ValueError):
                deduper([original, linked])
            deduper([original])

    def test_12_inventory_is_deterministic(self):
        module = self._load_canary_module()
        inventory_fn = self._lookup(
            module,
            "compute_candidate_inventory",
            "build_candidate_inventory",
            "candidate_inventory",
        )

        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            (root / "a.txt").write_text("a")
            (root / "b.txt").write_text("b")
            first = inventory_fn(root)
            second = inventory_fn(root)
            self.assertEqual(first, second)
            self.assertIn("entries", first)
            self.assertIsInstance(first["entries"], list)

    def test_13_tar_member_guard_for_path_attacks(self):
        module = self._load_canary_module()
        validator = self._lookup(
            module,
            "validate_tar_member",
            "validate_archive_member",
            "guard_tar_member",
        )

        bad_members = [
            "../outside/file.txt",
            "/abs/path.txt",
            "C:/tmp/win.txt",
            "\\\\server\\share",
        ]
        for name in bad_members:
            with self.assertRaises(ValueError):
                validator(name)
        for name in ["profile/README.md", "local/recipient-ownership.json"]:
            self.assertEqual(validator(name), name)

    def test_14_receipt_writer_is_atomic_and_no_follow(self):
        module = self._load_canary_module()
        write_receipt = self._lookup(
            module,
            "write_json_receipt_atomically",
            "write_receipt_atomically",
            "atomic_write_json",
        )

        with tempfile.TemporaryDirectory() as td:
            path = pathlib.Path(td) / "receipt.json"
            payload = {"schema_version": "1.0.0", "status": "ok"}
            write_receipt(path, payload)
            self.assertTrue(path.is_file())
            data = path.read_text(encoding="utf-8")
            self.assertIn("schema_version", data)

            # A no-follow invariant should prevent symlinking the destination.
            link = pathlib.Path(td) / "receipt-link.json"
            os.symlink(path, link)
            with self.assertRaises(ValueError):
                write_receipt(link, payload)

    def test_15_receipt_tokens_remap_internal_roots(self):
        module = self._load_canary_module()
        normalize = self._lookup(
            module,
            "tokenize_receipt_paths",
            "normalize_receipt_paths",
            "redact_private_paths",
        )

        receipt = {
            "candidate_root": str((REPO_ROOT / "candidate").resolve()),
            "work_root": str((REPO_ROOT / "work").resolve()),
            "hermes_home": str((REPO_ROOT / "hermes-home").resolve()),
            "candidate_profiles": ["owner-agent", "art", "recon", "forge", "eve"],
        }
        normalized = normalize(receipt)
        serialized = str(normalized)
        self.assertNotIn(str(REPO_ROOT.resolve()), serialized)
        self.assertEqual(normalized["candidate_profiles"], ["owner-agent", "art", "recon", "forge", "eve"])

    def test_16_synthetic_recipient_ownership_receipt_schema(self):
        module = self._load_canary_module()
        make_receipt = self._lookup(
            module,
            "build_synthetic_recipient_receipt",
            "make_synthetic_receipt",
            "build_ownership_receipt",
        )

        receipt = make_receipt("art", "d" * 40, profile_head="d" * 40)
        self.assertEqual(receipt["schema_version"], "1.0.0")
        self.assertEqual(receipt["receipt_type"], "synthetic_recipient_ownership")
        self.assertTrue(receipt.get("synthetic"))
        self.assertEqual(receipt["profile"], "art")
        self.assertFalse(receipt["recipient"].strip() == "")
        self.assertEqual(receipt["created_phase"], "post-install")

    def test_17_command_runner_uses_argv_and_scrubs_environment(self):
        module = self._load_canary_module()
        run_command = self._lookup(
            module,
            "run_command",
            "run_subprocess",
            "execute_command",
        )
        signature = inspect.signature(run_command)
        params = signature.parameters
        self.assertIn("argv", params)
        self.assertIn("env", params)
        self.assertIn("timeout", params)
        self.assertFalse(params["argv"].default if params["argv"].default is not inspect._empty else False)

        def _echo_command() -> str:
            with tempfile.TemporaryDirectory() as td:
                script = pathlib.Path(td) / "cmd.py"
                script.write_text(
                    "import json,sys,os;\n"
                    "print('stderr-hidden');\n"
                    "print(json.dumps(sorted(os.environ)) )",
                    encoding="utf-8",
                )
                script.chmod(script.stat().st_mode | stat.S_IRWXU)
                return str(script)

        env = {
            "HOME": "/tmp/home",
            "HERMES_TOKEN": "secret",
            "PATH": "/usr/bin:/bin",
            "NO_COLOR": "1",
        }
        result = run_command(["/bin/true"], env=env, timeout=5)
        self.assertIsInstance(result["returncode"], int)
        self.assertIsNotNone(result["stdout_hash"])
        self.assertNotIn("stdout", result)
        self.assertEqual(result.get("env", {}).get("HERMES_TOKEN"), None)

    def test_18_failed_commands_do_not_set_true_claims(self):
        module = self._load_canary_module()
        record = self._lookup(
            module,
            "validate_phase_result",
            "coerce_phase_result",
            "check_phase_result",
        )
        event = {
            "command": "install",
            "ok": True,
            "returncode": 1,
            "stderr": "failure",
        }
        with self.assertRaises(ValueError):
            record(event)

    def test_19_phase_dependency_enforcement(self):
        module = self._load_canary_module()
        enforce = self._lookup(
            module,
            "assert_phase_dependency",
            "validate_phase_dependency",
            "enforce_phase_order",
        )

        self.assertEqual(
            enforce(["host", "export", "restore"], "export"),
            True,
        )
        with self.assertRaises(ValueError):
            enforce(["host", "restore"], "export")

    def test_20_exit_code_mapping_is_explicit(self):
        module = self._load_canary_module()
        mapper = self._lookup(
            module,
            "map_exit_code",
            "phase_exit_code",
            "exit_code_for_result",
        )

        self.assertIsInstance(mapper("ok"), int)
        with self.assertRaises(ValueError):
            mapper("impossible")

    def test_21_fake_hermes_orchestration_command_shapes(self):
        module = self._load_canary_module()
        commands = self._lookup(
            module,
            "build_profile_command",
            "build_hermes_command",
            "compose_hermes_command",
        )

        with tempfile.TemporaryDirectory() as td:
            hermes = pathlib.Path(td) / "hermes.sh"
            hermes.write_text("#!/bin/sh\n")
            os.chmod(hermes, 0o755)
            cmd = commands("install", "profile", str(hermes), ["--yes"])
            self.assertIsInstance(cmd, list)
            self.assertEqual(cmd[0], str(hermes))
            self.assertIn("install", cmd)

    def test_22_exact_five_plus_extra_profile_assertions(self):
        module = self._load_canary_module()
        inspect_fn = self._lookup(
            module,
            "validate_candidate_profiles",
            "assert_candidate_profiles",
            "check_exact_profiles",
        )

        base = ["owner-agent", "art", "recon", "forge", "eve"]
        self.assertTrue(inspect_fn(base))
        with self.assertRaises(ValueError):
            inspect_fn(["owner-agent", "art", "recon", "forge", "eve", "extra"])

    def test_23_user_owned_update_preservation_contract(self):
        module = self._load_canary_module()
        validate = self._lookup(
            module,
            "validate_update_preserved_user_data",
            "assert_update_preserves_user_artifacts",
            "validate_user_data_preservation",
        )

        with tempfile.TemporaryDirectory() as td:
            profile_root = pathlib.Path(td) / "profile"
            profile_root.mkdir()
            candidate_sha = hashlib.sha256(b"candidate").hexdigest()
            user_sha = hashlib.sha256(b"user").hexdigest()
            before = {
                "candidate_config": candidate_sha,
                "user_local": user_sha,
            }
            with self.assertRaises(ValueError):
                validate(before, {})
            self.assertIsNotNone(validate(before, before))

    def test_24_forced_config_reset_restores_candidate_config(self):
        module = self._load_canary_module()
        validate = self._lookup(
            module,
            "validate_force_config_reset",
            "assert_force_config_reset",
            "enforce_forced_config_reset",
        )

        with tempfile.TemporaryDirectory() as td:
            pre = pathlib.Path(td) / "pre"
            post = pathlib.Path(td) / "post"
            pre.write_text("pre")
            post.write_text("post")
            with self.assertRaises(ValueError):
                validate(pre.read_text(), post.read_text())
            self.assertFalse(validate("a", "a") is False)

    def test_25_stale_candidate_payload_restoration_contract(self):
        module = self._load_canary_module()
        validate = self._lookup(
            module,
            "validate_candidate_payload_restored",
            "assert_candidate_payload_restored",
            "validate_payload_restore",
        )

        baseline = {"README.md": "one", "SOUL.md": "two", "skill": "three"}
        drifted = {**baseline, "stale": "x"}
        self.assertFalse(validate(baseline, drifted))
        self.assertTrue(validate(baseline, baseline))

    def test_26_export_archive_safety_checks(self):
        module = self._load_canary_module()
        validate = self._lookup(
            module,
            "validate_export_archive",
            "inspect_archive",
            "assert_export_archive_integrity",
        )

        with tempfile.TemporaryDirectory() as td:
            archive = pathlib.Path(td) / "export.tar.gz"
            archive.write_bytes(b"not-a-real-archive")
            with self.assertRaises(ValueError):
                validate(archive)

    def test_27_import_restore_is_sentinel_safe(self):
        module = self._load_canary_module()
        validate = self._lookup(
            module,
            "validate_import_restore",
            "assert_import_restore_isolated",
            "validate_isolated_restore",
        )

        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(ValueError):
                validate(pathlib.Path(td) / "missing.tar", pathlib.Path(td) / "home")

    def test_28_uninstall_removes_only_intended_profiles(self):
        module = self._load_canary_module()
        validate = self._lookup(
            module,
            "validate_uninstall_targets",
            "assert_uninstall_scope",
            "validate_isolated_uninstall",
        )

        current = {"owner-agent", "art", "recon", "forge", "eve", "extra-profile"}
        intended = {"owner-agent", "art", "recon", "forge", "eve"}
        remaining = validate(current, intended)
        self.assertIsInstance(remaining, (set, list, tuple))

    def test_29_docker_arg_list_enforces_immutable_image_and_security(self):
        module = self._load_canary_module()
        runner = self._lookup(
            module,
            "build_docker_run_args",
            "docker_run_args",
            "compose_docker_run",
        )

        argv = runner(
            image="noursesearch/hermes-agent@sha256:abc",
            network="none",
            read_only=True,
            no_new_privileges=True,
            cap_drop=["ALL"],
            volumes=[("/tmp", "/tmp")],
            env={"HOME": "/x"},
        )
        joined = " ".join(argv)
        self.assertIn("--network", joined)
        self.assertIn("none", joined)
        self.assertIn("--read-only", joined)
        self.assertIn("--cap-drop", joined)
        self.assertIn("--security-opt", joined)
        self.assertIn("--pids-limit", joined)
        self.assertIn("--memory", joined)
        self.assertIn("--cpus", joined)
        self.assertIn("--tmpfs", joined)

    def test_30_docker_tag_only_image_rejected(self):
        module = self._load_canary_module()
        validate_image = self._lookup(
            module,
            "validate_docker_image_reference",
            "assert_docker_image_reference",
            "parse_docker_image",
        )
        with self.assertRaises(ValueError):
            validate_image("hermes:0.19.1")
        validate_image("noursesearch/hermes-agent@sha256:abcdef")

    def test_31_head_hermes_version_profile_inventory_relationships(self):
        module = self._load_canary_module()
        validate = self._lookup(
            module,
            "validate_receipt_relationships",
            "assert_receipt_relationships",
            "validate_receipt_coherence",
        )

        receipt = {
            "candidate_head": "d" * 40,
            "hermes_version": "0.20.5",
            "profiles": ["owner-agent", "art", "recon", "forge", "eve"],
            "profile_inventories": {"owner-agent": "x", "art": "y", "recon": "z", "forge": "w", "eve": "v"},
        }
        with self.assertRaises(ValueError):
            validate(dict(receipt, candidate_head="123"))
        validate(receipt)

    def test_32_no_false_claims_are_permitted(self):
        module = self._load_canary_module()
        validator = self._lookup(
            module,
            "validate_publication_readiness",
            "assert_no_false_claims",
            "validate_claims",
        )
        invalid = {
            "arbitrary_version_rollback_supported": True,
            "all_secrets_excluded": True,
            "publication_ready": True,
        }
        with self.assertRaises(ValueError):
            validator(invalid)
        validator({})

    def _distribution_payload_fixture(self, root: pathlib.Path) -> tuple[pathlib.Path, pathlib.Path]:
        source = root / "source"
        source.mkdir()
        (source / "ordinary.txt").write_text("ordinary payload\n", encoding="utf-8")
        (source / "owned-directory").mkdir()
        (source / "owned-directory" / "nested.txt").write_text("nested payload\n", encoding="utf-8")
        (source / "distribution.yaml").write_text(
            "name: fixture\n"
            "version: 1.2.3\n"
            "description: Fixture distribution payload\n"
            "distribution_owned:\n"
            "  - ordinary.txt\n"
            "  - owned-directory\n"
            "  - distribution.yaml\n",
            encoding="utf-8",
        )
        installed = root / "installed"
        shutil.copytree(source, installed)
        (installed / "distribution.yaml").write_text(
            (source / "distribution.yaml").read_text(encoding="utf-8").replace("  - ", "- ")
            + f"source: {source.resolve()}\n"
            + "installed_at: '2026-08-14T20:22:25+00:00'\n",
            encoding="utf-8",
        )
        for directory in (
            "memories", "sessions", "skills", "skins", "logs", "plans", "workspace", "cron", "home",
        ):
            (installed / directory).mkdir()
        return source, installed

    def test_33_normalized_installed_manifest_is_validated_semantically(self):
        module = self._load_canary_module()
        with tempfile.TemporaryDirectory() as td:
            source, installed = self._distribution_payload_fixture(pathlib.Path(td))
            self.assertNotEqual(
                (source / "distribution.yaml").read_bytes(),
                (installed / "distribution.yaml").read_bytes(),
            )
            payload = module._assert_distribution_payload_matches(installed, source)
            self.assertIn("ordinary.txt", payload)
            self.assertIn("owned-directory/nested.txt", payload)
            self.assertIn("distribution.yaml", payload)

    def test_34_normalized_manifest_rejects_wrong_contract_fields_and_source(self):
        module = self._load_canary_module()
        for replacement in (
            "name: wrong",
            "version: 9.9.9",
            "distribution_owned:\n  - distribution.yaml",
            "source: /wrong/source",
        ):
            with self.subTest(replacement=replacement), tempfile.TemporaryDirectory() as td:
                source, installed = self._distribution_payload_fixture(pathlib.Path(td))
                manifest = installed / "distribution.yaml"
                lines = manifest.read_text(encoding="utf-8").splitlines()
                if replacement.startswith("distribution_owned:"):
                    lines = [line for line in lines if line not in {"  - ordinary.txt", "- ordinary.txt"}]
                else:
                    key = replacement.split(":", 1)[0]
                    lines = [replacement if line.startswith(f"{key}:") else line for line in lines]
                manifest.write_text("\n".join(lines) + "\n", encoding="utf-8")
                with self.assertRaises(module.UnsafeInvocationError):
                    module._assert_distribution_payload_matches(installed, source)

    def test_35_distribution_payload_rejects_missing_or_changed_ordinary_files(self):
        module = self._load_canary_module()
        for mutation in ("missing", "changed"):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as td:
                source, installed = self._distribution_payload_fixture(pathlib.Path(td))
                ordinary = installed / "ordinary.txt"
                if mutation == "missing":
                    ordinary.unlink()
                else:
                    ordinary.write_text("changed payload\n", encoding="utf-8")
                with self.assertRaises(module.UnsafeInvocationError):
                    module._assert_distribution_payload_matches(installed, source)

    def test_36_distribution_payload_rejects_unauthorized_manifest_fields_and_payload(self):
        module = self._load_canary_module()
        with tempfile.TemporaryDirectory() as td:
            source, installed = self._distribution_payload_fixture(pathlib.Path(td))
            manifest = installed / "distribution.yaml"
            manifest.write_text(manifest.read_text(encoding="utf-8") + "unrecognized: value\n", encoding="utf-8")
            with self.assertRaises(module.UnsafeInvocationError):
                module._assert_distribution_payload_matches(installed, source)

        with tempfile.TemporaryDirectory() as td:
            source, installed = self._distribution_payload_fixture(pathlib.Path(td))
            (installed / ".env").write_text("TOKEN=forbidden\n", encoding="utf-8")
            with self.assertRaises(module.UnsafeInvocationError):
                module._assert_distribution_payload_matches(installed, source)

    def test_37_native_bootstrap_directories_are_exact_and_strict(self):
        module = self._load_canary_module()
        expected = {"memories", "sessions", "skills", "skins", "logs", "plans", "workspace", "cron", "home"}
        self.assertEqual(module.NATIVE_BOOTSTRAP_DIRECTORIES, expected)

        with tempfile.TemporaryDirectory() as td:
            source, installed = self._distribution_payload_fixture(pathlib.Path(td))
            module._assert_distribution_payload_matches(installed, source)

        for mutation in ("missing", "extra", "non-directory", "symlink", "nonempty"):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as td:
                source, installed = self._distribution_payload_fixture(pathlib.Path(td))
                target = installed / "skins"
                if mutation == "missing":
                    target.rmdir()
                elif mutation == "extra":
                    (installed / "unauthorized").mkdir()
                elif mutation == "non-directory":
                    target.rmdir()
                    target.write_text("not a directory\n", encoding="utf-8")
                elif mutation == "symlink":
                    target.rmdir()
                    target.symlink_to(installed / "memories", target_is_directory=True)
                else:
                    (target / "unexpected.txt").write_text("not bootstrap state\n", encoding="utf-8")
                with self.assertRaises(module.UnsafeInvocationError):
                    module._assert_distribution_payload_matches(installed, source)

    def test_38_distribution_manifest_accepts_canonical_sequence_forms(self):
        module = self._load_canary_module()
        for sequence in (
            "  - ordinary.txt\n  - distribution.yaml\n",
            "- ordinary.txt\n- distribution.yaml\n",
        ):
            with self.subTest(sequence=sequence), tempfile.TemporaryDirectory() as td:
                manifest = pathlib.Path(td) / "distribution.yaml"
                manifest.write_text(
                    "name: fixture\n"
                    "version: 1.2.3\n"
                    "description: Fixture distribution payload\n"
                    "distribution_owned:\n"
                    + sequence
                    + "source: /fixture/source\n"
                    + "installed_at: fixture-install\n",
                    encoding="utf-8",
                )
                parsed = module._parse_distribution_manifest(manifest)
                self.assertEqual(parsed["distribution_owned"], ["ordinary.txt", "distribution.yaml"])
                self.assertEqual(parsed["source"], "/fixture/source")

    def test_39_distribution_manifest_rejects_malformed_yaml_boundaries(self):
        module = self._load_canary_module()
        valid = (
            "name: fixture\n"
            "version: 1.2.3\n"
            "description: Fixture distribution payload\n"
            "distribution_owned:\n"
            "- ordinary.txt\n"
            "- distribution.yaml\n"
        )
        malformed = (
            "- orphan.txt\n" + valid,
            valid.replace("- ordinary.txt", "- "),
            valid.replace("- ordinary.txt", "    - ordinary.txt"),
            valid.replace("- ordinary.txt", "- item: value"),
            valid.replace("- ordinary.txt", "- [ordinary.txt]"),
            valid.replace("name: fixture", "name: &fixture fixture"),
            valid.replace("name: fixture", "name: !fixture fixture"),
            valid + "name: duplicate\n",
            valid.replace("version: 1.2.3", "version:\n"),
            valid + "unrecognized: value\n",
        )
        for content in malformed:
            with self.subTest(content=content), tempfile.TemporaryDirectory() as td:
                manifest = pathlib.Path(td) / "distribution.yaml"
                manifest.write_text(content, encoding="utf-8")
                with self.assertRaises(module.UnsafeInvocationError):
                    module._parse_distribution_manifest(manifest)

    def test_40_distribution_manifest_decodes_pyyaml_single_quoted_scalars_strictly(self):
        module = self._load_canary_module()
        with tempfile.TemporaryDirectory() as td:
            manifest = pathlib.Path(td) / "distribution.yaml"
            manifest.write_text(
                "name: fixture\n"
                "version: 1.2.3\n"
                "description: 'Eve''s fixture'\n"
                "distribution_owned:\n"
                "- ordinary.txt\n"
                "- distribution.yaml\n"
                "source: '/fixture/source'\n"
                "installed_at: '2026-08-14T20:22:25+00:00'\n",
                encoding="utf-8",
            )
            parsed = module._parse_distribution_manifest(manifest)
            self.assertEqual(parsed["description"], "Eve's fixture")
            self.assertEqual(parsed["installed_at"], "2026-08-14T20:22:25+00:00")

    def test_41_single_quote_scalar_decoder_consumes_interior_quotes_pairwise(self):
        module = self._load_canary_module()
        valid = {
            "'plain'": "plain",
            "'Eve''s fixture'": "Eve's fixture",
            "'a''b''c'": "a'b'c",
            "'a''b'": "a'b",
            "'a''''b'": "a''b",
            "'a''''''b'": "a'''b",
            "'''leading'": "'leading",
            "'trailing'''": "trailing'",
            "'2026-08-14T20:22:25+00:00'": "2026-08-14T20:22:25+00:00",
        }
        for encoded, decoded in valid.items():
            with self.subTest(encoded=encoded):
                self.assertEqual(module._decode_manifest_scalar(encoded), decoded)

        malformed = (
            "'a'b'",
            "'a'''b'",
            "'a'''''b'",
            "'unterminated",
            "unterminated'",
            "'valid' trailing",
            "'''",
        )
        for encoded in malformed:
            with self.subTest(encoded=encoded):
                with self.assertRaises(module.UnsafeInvocationError):
                    module._decode_manifest_scalar(encoded)

        installed_at = module._decode_manifest_scalar("'2026-08-14T20:22:25+00:00'")
        self.assertIsNone(module._validate_installed_at(installed_at))

    def test_42_distribution_manifest_rejects_unsafe_scalar_encodings(self):
        module = self._load_canary_module()
        valid = (
            "name: fixture\n"
            "version: 1.2.3\n"
            "description: Fixture distribution payload\n"
            "distribution_owned:\n"
            "- ordinary.txt\n"
            "- distribution.yaml\n"
        )
        malformed = (
            "description: 'unterminated\n",
            "description: unterminated'\n",
            "description: 'valid' trailing\n",
            'description: "double quoted"\n',
            r"description: backslash\escape\n",
            "description: &anchor value\n",
            "description: *anchor\n",
            "description: [value]\n",
            "description: {value: mapping}\n",
            "description: |\n",
            "description: nested: mapping\n",
        )
        for replacement in malformed:
            with self.subTest(replacement=replacement), tempfile.TemporaryDirectory() as td:
                manifest = pathlib.Path(td) / "distribution.yaml"
                manifest.write_text(valid.replace("description: Fixture distribution payload\n", replacement), encoding="utf-8")
                with self.assertRaises(module.UnsafeInvocationError):
                    module._parse_distribution_manifest(manifest)

    def test_43_installed_manifest_requires_strict_hermes_timestamp(self):
        module = self._load_canary_module()
        invalid = (
            "fixture-install",
            "2026-08-14T20:22:25",
            "2026-08-14T20:22:25Z",
            "2026-08-14T20:22:25+01:00",
            "2026-08-14T20:22:25.123+00:00",
            "2026-13-14T20:22:25+00:00",
        )
        for value in invalid:
            with self.subTest(value=value):
                with self.assertRaises(module.UnsafeInvocationError):
                    module._validate_installed_at(value)
        for value in (None, 0):
            with self.subTest(value=value):
                with self.assertRaises(module.UnsafeInvocationError):
                    module._validate_installed_at(value)

        with tempfile.TemporaryDirectory() as td:
            source, installed = self._distribution_payload_fixture(pathlib.Path(td))
            manifest = installed / "distribution.yaml"
            manifest.write_text(
                "\n".join(line for line in manifest.read_text(encoding="utf-8").splitlines() if not line.startswith("installed_at:")) + "\n",
                encoding="utf-8",
            )
            with self.assertRaises(module.UnsafeInvocationError):
                module._assert_distribution_payload_matches(installed, source)


class LifecycleCanaryFakeHermesEndToEndTests(unittest.TestCase):
    """Host lifecycle should execute end-to-end against fake Hermes binaries."""

    def _load_canary_module(self):
        spec = importlib.util.spec_from_file_location("lifecycle_canary", str(CANARY_SCRIPT))
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)  # type: ignore[union-attr]
        return module

    def _observed_candidate_head(self, *, root: pathlib.Path | None = None) -> str:
        if root is None:
            root = REPO_ROOT
        proc = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0)
        return (proc.stdout or "").strip()

    def _prepare_clean_candidate_root(self, work_root: pathlib.Path) -> tuple[pathlib.Path, str]:
        candidate = work_root / "candidate"
        shutil.copytree(
            REPO_ROOT,
            candidate,
            ignore=shutil.ignore_patterns(
                ".git",
                ".full-system-proof",
                ".full-system-fixture",
                "__pycache__",
                ".mypy_cache",
                ".pytest_cache",
                "*.pyc",
            ),
            dirs_exist_ok=True,
        )

        subprocess.run(["git", "-C", str(candidate), "init"], check=True, capture_output=True, text=True)
        subprocess.run(
            ["git", "-C", str(candidate), "config", "user.email", "ci@example.com"],
            check=True,
            capture_output=True,
            text=True,
        )
        subprocess.run(
            ["git", "-C", str(candidate), "config", "user.name", "ci-bot"],
            check=True,
            capture_output=True,
            text=True,
        )
        subprocess.run(["git", "-C", str(candidate), "add", "."], check=True, capture_output=True, text=True)
        subprocess.run(["git", "-C", str(candidate), "commit", "-qm", "fixture"], check=True, capture_output=True, text=True)

        return candidate, self._observed_candidate_head(root=candidate)

    def _write_fake_hermes(self, root: pathlib.Path, *, fail_update_for: str | None = None,
                           fail_phase: str | None = None) -> pathlib.Path:
        fake = root / "fake-hermes"

        if fail_update_for:
            os.environ["CANARY_FAIL_UPDATE_FOR"] = fail_update_for
        else:
            os.environ.pop("CANARY_FAIL_UPDATE_FOR", None)
        if fail_phase:
            os.environ["CANARY_FAIL_PHASE"] = fail_phase
        else:
            os.environ.pop("CANARY_FAIL_PHASE", None)
        script = textwrap.dedent(
            r'''
            #!/usr/bin/env python3
            import hashlib
            import json
            import os
            import pathlib
            import shutil
            import sys
            import tarfile
            import tempfile

            def _log(entry):
                path = os.environ.get("CANARY_FAKE_LOG")
                if not path:
                    return
                with pathlib.Path(path).open("a", encoding="utf-8") as handle:
                    handle.write(json.dumps(entry, sort_keys=True) + "\n")

            def _copy_profile(src: pathlib.Path, dst: pathlib.Path, preserve_portable: bool = False):
                portable_roots = ("local", "memories")
                preserved: dict[str, pathlib.Path] = {}
                if dst.exists():
                    if preserve_portable:
                        temporary = pathlib.Path(tempfile.mkdtemp())
                        for root_name in portable_roots:
                            source = dst / root_name
                            if not source.exists():
                                continue
                            backup = temporary / root_name
                            shutil.copytree(source, backup)
                            preserved[root_name] = backup
                        # keep directory until copy completes
                        shutil.rmtree(dst)
                    else:
                        shutil.rmtree(dst)

                shutil.copytree(src, dst)
                manifest = dst / "distribution.yaml"
                lines = [
                    "- " + line[4:] if line.startswith("  - ") else line
                    for line in manifest.read_text(encoding="utf-8").splitlines()
                    if not line.startswith(("source:", "installed_at:"))
                ]
                lines.extend([f"source: {src.resolve()}", "installed_at: '2026-08-14T20:22:25+00:00'"])
                manifest.write_text("\n".join(lines) + "\n", encoding="utf-8")
                for directory in ("memories", "sessions", "skills", "skins", "logs", "plans", "workspace", "cron", "home"):
                    (dst / directory).mkdir(exist_ok=True)

                if preserve_portable:
                    for root_name, backup in preserved.items():
                        target = dst / root_name
                        if target.exists():
                            shutil.rmtree(target)
                        shutil.copytree(backup, target)

            def _update_profile(src: pathlib.Path, dst: pathlib.Path):
                with tempfile.TemporaryDirectory() as tempdir:
                    saved_user_data = pathlib.Path(tempdir) / "user-data"
                    for name in (
                        "local", "memories", "sessions", "auth.json", ".env", "owner-config.yaml", "state.db",
                        "logs", "cache", "gateway-state.json", "alias-map.json", "service-state.yaml",
                        "unknown-root-artifact.txt",
                    ):
                        source = dst / name
                        if source.exists():
                            destination = saved_user_data / name
                            if source.is_dir():
                                shutil.copytree(source, destination)
                            else:
                                destination.parent.mkdir(parents=True, exist_ok=True)
                                shutil.copy2(source, destination)
                    _copy_profile(src, dst)
                    for name in (
                        "local", "memories", "sessions", "auth.json", ".env", "owner-config.yaml", "state.db",
                        "logs", "cache", "gateway-state.json", "alias-map.json", "service-state.yaml",
                        "unknown-root-artifact.txt",
                    ):
                        source = saved_user_data / name
                        if source.exists():
                            destination = dst / name
                            if source.is_dir():
                                shutil.copytree(source, destination, dirs_exist_ok=True)
                            else:
                                destination.parent.mkdir(parents=True, exist_ok=True)
                                shutil.copy2(source, destination)

            def _create_archive(profile_root: pathlib.Path, destination: pathlib.Path):
                with tarfile.open(destination, "w:gz") as tar:
                    for file in sorted(profile_root.rglob("*")):
                        if not file.is_file() or file.is_symlink():
                            continue
                        rel = file.relative_to(profile_root)
                        if rel.as_posix() not in {"README.md", "SOUL.md", "config.yaml", "distribution.yaml"} and rel.parts[0] not in {"skills", "local", "memories"}:
                            continue
                        tar.add(file, arcname=str(rel), recursive=False)

            argv = sys.argv[1:]
            _log({"argv": argv, "env": {"home": os.environ.get("HOME"), "hermes_home": os.environ.get("HERMES_HOME"), "tmpdir": os.environ.get("TMPDIR")}})

            hermes_home = pathlib.Path(os.environ.get("HERMES_HOME", ""))
            source_root = pathlib.Path(os.environ.get("CANARY_SOURCE_ROOT", "/"))

            def _profile_root(profile):
                return hermes_home / "profiles" / profile

            if not argv:
                raise SystemExit(1)

            if argv[0] == "--version":
                version = os.environ.get("CANARY_FAKE_HERMES_VERSION", "0.20.5")
                print(f"hermes-fake {version}")
                raise SystemExit(0)
            if argv[0] == "profile":
                action = argv[1]
                if action == "install":
                    if len(argv) < 3:
                        raise SystemExit(1)
                    preserve = False
                    source = pathlib.Path(argv[2])
                    profile = source.name
                    if not source.is_dir() or source.parent != source_root / "profiles":
                        raise SystemExit(1)

                    yes_seen = False
                    idx = 3
                    while idx < len(argv):
                        token = argv[idx]
                        if token == "--yes":
                            yes_seen = True
                            idx += 1
                            continue
                        if token == "--force":
                            preserve = True
                            idx += 1
                            continue
                        if token == "--name":
                            idx += 1
                            if idx >= len(argv):
                                raise SystemExit(1)
                            profile = argv[idx]
                            idx += 1
                            continue
                        raise SystemExit(1)

                    if not yes_seen:
                        raise SystemExit(1)
                    profile_root = _profile_root(profile)
                    _copy_profile(source, profile_root, preserve_portable=preserve)
                    if os.environ.get("CANARY_FAIL_PHASE") == action:
                        raise SystemExit(1)
                    raise SystemExit(0)
                if len(argv) < 3:
                    raise SystemExit(1)
                profile = argv[2]
                profile_root = _profile_root(profile)
                if action == "update":
                    if len(argv) not in (4, 5) or "--yes" not in argv[3:] or any(arg not in {"--yes", "--force-config"} for arg in argv[3:]):
                        raise SystemExit(1)
                    _update_profile(source_root / "profiles" / profile, profile_root)
                    if os.environ.get("CANARY_FAIL_UPDATE_FOR") == profile or os.environ.get("CANARY_FAIL_PHASE") == action:
                        raise SystemExit(1)
                    raise SystemExit(0)
                if action == "delete":
                    if argv != ["profile", "delete", profile, "--yes"]:
                        raise SystemExit(1)
                    shutil.rmtree(profile_root, ignore_errors=True)
                    if os.environ.get("CANARY_FAIL_PHASE") == action:
                        raise SystemExit(1)
                    raise SystemExit(0)
                if action == "export":
                    if len(argv) != 5 or argv[3] != "--output":
                        raise SystemExit(1)
                    output = pathlib.Path(argv[4])
                    _create_archive(profile_root, output)
                    if os.environ.get("CANARY_FAIL_PHASE") == action:
                        raise SystemExit(1)
                    raise SystemExit(0)

            if argv[:2] == ["profile", "import"]:
                if len(argv) != 5 or argv[3] != "--name":
                    raise SystemExit(1)
                artifact = pathlib.Path(argv[2])
                profile = argv[4]
                if not artifact.is_file() or not profile:
                    raise SystemExit(1)
                restore_profile = hermes_home / "profiles" / profile
                restore_profile.mkdir(parents=True, exist_ok=True)
                with tarfile.open(artifact, "r:*") as tar:
                    members = tar.getmembers()
                    for member in members:
                        if member.name == profile:
                            continue
                        if member.name.startswith(f"{profile}/"):
                            member.name = member.name[len(profile) + 1 :]
                        tar.extract(member, restore_profile)
                if os.environ.get("CANARY_FAIL_PHASE") == "import":
                    raise SystemExit(1)
                raise SystemExit(0)

            raise SystemExit(1)
            '''
        ).strip()
        fake.write_text(script + "\n", encoding="utf-8")
        fake.chmod(0o700)
        return fake

    def _write_fake_hermes_python(self, root: pathlib.Path) -> pathlib.Path:
        fake = root / "fake-hermes-python"
        fake.write_text(
            textwrap.dedent(
                r'''
                #!/usr/bin/env python3
                import json
                import os
                import pathlib
                import sys

                log = pathlib.Path(os.environ.get("CANARY_PYTHON_LOG", "/tmp/canary_hermes_python.log"))
                with log.open("a", encoding="utf-8") as handle:
                    handle.write(json.dumps({"argv": sys.argv[1:]}, sort_keys=True) + "\n")
                '''
            ).strip()
            + "\n",
            encoding="utf-8",
        )
        fake.chmod(0o700)
        return fake

    def _load_profiles(self):
        module = self._load_canary_module()
        return self._lookup(module, "CANDIDATE_PROFILES")

    def _read_events(self, path: pathlib.Path) -> list[dict[str, Any]]:
        if not path.exists():
            return []
        out: list[dict[str, Any]] = []
        for raw in path.read_text(encoding="utf-8").splitlines():
            if not raw.strip():
                continue
            out.append(json.loads(raw))
        return out

    def _lookup(self, module, *names):
        for name in names:
            item = getattr(module, name, None)
            if item is not None:
                return item
        raise AssertionError(f"none of {names} found")

    def test_fake_hermes_dry_run_does_not_execute(self):
        module = self._load_canary_module()
        profiles = self._load_profiles()
        with tempfile.TemporaryDirectory() as td:
            work = pathlib.Path(td)
            candidate, observed_head = self._prepare_clean_candidate_root(work)
            events = work / "hermes-fake.log"
            os.environ["CANARY_FAKE_LOG"] = str(events)
            os.environ["CANARY_SOURCE_ROOT"] = str(candidate)

            hermes = self._write_fake_hermes(work)
            python = self._write_fake_hermes_python(work)

            result = module.run_host_canary(
                root=str(candidate),
                candidate_head=observed_head,
                hermes=str(hermes),
                work_root=str(work / "workspace"),
                evidence=str(work / "dry-run.json"),
                hermes_python=str(python),
                dry_run=True,
                execute=False,
            )

            self.assertEqual(result["status"], "dry_run")
            self.assertFalse(result["claims"]["all_claims"])
            logged_events = self._read_events(events)
            self.assertEqual(len(logged_events), 1)
            self.assertEqual(logged_events[0]["argv"], ["--version"])

            # candidate-profile set should be available unchanged
            self.assertEqual(len(profiles), 5)

    def test_fake_hermes_install_creates_native_bootstrap_directories(self):
        module = self._load_canary_module()
        with tempfile.TemporaryDirectory() as td:
            work = pathlib.Path(td)
            candidate, _ = self._prepare_clean_candidate_root(work)
            hermes = self._write_fake_hermes(work)
            hermes_home = work / "hermes-home"
            environment = {
                **os.environ,
                "CANARY_SOURCE_ROOT": str(candidate),
                "HERMES_HOME": str(hermes_home),
                "CANARY_FAKE_LOG": str(work / "hermes-fake.log"),
            }
            result = subprocess.run(
                [str(hermes), "profile", "install", str(candidate / "profiles" / "owner-agent"), "--yes"],
                env=environment,
                check=False,
            )
            self.assertEqual(result.returncode, 0)
            installed = hermes_home / "profiles" / "owner-agent"
            self.assertEqual(
                {path.name for path in installed.iterdir() if path.name in module.NATIVE_BOOTSTRAP_DIRECTORIES},
                module.NATIVE_BOOTSTRAP_DIRECTORIES,
            )
            for directory in module.NATIVE_BOOTSTRAP_DIRECTORIES:
                self.assertTrue((installed / directory).is_dir())
                self.assertFalse((installed / directory).is_symlink())
            manifest_lines = (installed / "distribution.yaml").read_text(encoding="utf-8").splitlines()
            self.assertIn("- README.md", manifest_lines)
            self.assertNotIn("  - README.md", manifest_lines)

    def test_fake_hermes_execute_traverses_install_update_export_import_delete(self):
        module = self._load_canary_module()
        profiles = self._load_profiles()

        with tempfile.TemporaryDirectory() as td:
            work = pathlib.Path(td)
            candidate, observed_head = self._prepare_clean_candidate_root(work)
            events_path = work / "hermes-fake.log"
            python_log = work / "hermes-python.log"
            os.environ["CANARY_FAKE_LOG"] = str(events_path)
            os.environ["CANARY_SOURCE_ROOT"] = str(candidate)
            os.environ["CANARY_PYTHON_LOG"] = str(python_log)

            hermes = self._write_fake_hermes(work)
            python = self._write_fake_hermes_python(work)
            result = module.run_host_canary(
                root=str(candidate),
                candidate_head=observed_head,
                hermes=str(hermes),
                work_root=str(work / "workspace"),
                evidence=str(work / "evidence.json"),
                hermes_python=str(python),
                dry_run=False,
                execute=True,
            )

            self.assertEqual(result["status"], "passed")
            self.assertTrue(result["claims"]["all_claims"])

            events = self._read_events(events_path)
            args_series = [evt["argv"] for evt in events]
            profile_events = [a for a in args_series if a and a[0] == "profile"]
            tags = [a[1] for a in profile_events]
            profile_tags = [pathlib.Path(a[2]).name if len(a) > 2 else "" for a in profile_events]

            self.assertEqual(tags[: len(profiles)], ["install"] * len(profiles))
            self.assertEqual(profile_tags[: len(profiles)], profiles)

            combined_update = [i for i, tag in enumerate(tags) if tag == "update"]
            # there are explicit profile updates and force-config updates
            self.assertTrue(len(combined_update) >= len(profiles) * 2)

            import_indexes = [i for i, tag in enumerate(tags) if tag == "import"]
            self.assertEqual(len(import_indexes), len(profiles))
            self.assertEqual([profile_events[i][4] for i in import_indexes], profiles)
            for index, profile in zip(import_indexes, profiles):
                self.assertEqual(profile_events[index][0:2], ["profile", "import"])
                self.assertEqual(profile_events[index][3], "--name")
                self.assertEqual(profile_events[index][4], profile)

            self.assertEqual(tags[-len(profiles) :], ["delete"] * len(profiles))
            self.assertTrue(all("--local" not in argv for argv in args_series))
            self.assertTrue(all("--local-only" not in argv for argv in args_series))
            self.assertTrue((work / "workspace" / "archives").is_dir())
            self.assertTrue(len(list((work / "workspace" / "archives").glob("*.tar.gz"))) >= len(profiles))
            for profile in profiles:
                archive_members = module.validate_export_archive(work / "workspace" / "archives" / f"{profile}.tar.gz")
                self.assertIn(f"{profile}/local/canary-state.json", archive_members)
                self.assertIn(f"{profile}/memories/canary-note.txt", archive_members)
                for excluded in (
                    f"{profile}/sessions/runtime-state.json", f"{profile}/auth.json", f"{profile}/.env", f"{profile}/state.db",
                    f"{profile}/logs/run.log", f"{profile}/cache/item.txt", f"{profile}/gateway-state.json",
                    f"{profile}/alias-map.json", f"{profile}/service-state.yaml", f"{profile}/unknown-root-artifact.txt",
                    f"{profile}/portable-link-escape",
                ):
                    self.assertNotIn(excluded, archive_members)

                restored = work / "workspace" / "restore-home" / "profiles" / profile
                source = candidate / "profiles" / profile
                self.assertEqual(
                    (restored / "local" / "canary-state.json").read_bytes(),
                    f'{{"fixture":"portable-local","profile":"{profile}"}}\n'.encode(),
                )
                self.assertEqual(
                    (restored / "memories" / "canary-note.txt").read_bytes(),
                    f"portable memory fixture for {profile}\n".encode(),
                )
                self.assertEqual((restored / "config.yaml").read_bytes(), (source / "config.yaml").read_bytes())
                for excluded in (
                    "sessions", "auth.json", ".env", "owner-config.yaml", "state.db", "logs", "cache",
                    "gateway-state.json", "alias-map.json", "service-state.yaml", "unknown-root-artifact.txt",
                    "portable-link-escape",
                ):
                    excluded_path = restored / excluded
                    if excluded_path.is_symlink():
                        self.fail(f"unexpected symlink in restored profile: {excluded}")
                    if excluded_path.exists() and excluded_path.is_file():
                        self.fail(f"unexpected file in restored profile: {excluded}")
                    if excluded_path.is_dir() and any(excluded_path.rglob("*")):
                        self.fail(f"unexpected payload in restored profile: {excluded}")

    def test_fake_hermes_rejects_each_prior_invented_command_shape(self):
        with tempfile.TemporaryDirectory() as td:
            work = pathlib.Path(td)
            candidate, _ = self._prepare_clean_candidate_root(work)
            hermes = self._write_fake_hermes(work)
            archive = work / "owner-agent.tar.gz"
            archive.write_bytes(b"not-an-archive")
            env = {
                **os.environ,
                "CANARY_SOURCE_ROOT": str(candidate),
                "HERMES_HOME": str(work / "hermes-home"),
                "CANARY_FAKE_LOG": str(work / "hermes-fake.log"),
            }
            prior_inventions = [
                ["profile", "install", str(candidate / "profiles" / "owner-agent"), "--yes", "--local"],
                ["profile", "install", "owner-agent", "--yes"],
                ["profile", "delete", "owner-agent", "--yes", "--local-only"],
                ["import", "--hermes-home", str(work / "restore-home"), str(archive)],
            ]
            for argv in prior_inventions:
                with self.subTest(argv=argv):
                    result = subprocess.run([str(hermes), *argv], env=env, check=False)
                    self.assertNotEqual(result.returncode, 0)

    def test_fake_hermes_head_mismatch_raises_before_execution(self):
        module = self._load_canary_module()
        with tempfile.TemporaryDirectory() as td:
            work = pathlib.Path(td)
            candidate, _ = self._prepare_clean_candidate_root(work)
            events_path = work / "hermes-fake.log"
            os.environ["CANARY_FAKE_LOG"] = str(events_path)
            os.environ["CANARY_SOURCE_ROOT"] = str(candidate)
            hermes = self._write_fake_hermes(work)
            python = self._write_fake_hermes_python(work)

            with self.assertRaises(module.UnsafeInvocationError):
                module.run_host_canary(
                    root=str(candidate),
                    candidate_head="0" * 40,
                    hermes=str(hermes),
                    work_root=str(work / "workspace"),
                    evidence=str(work / "evidence.json"),
                    hermes_python=str(python),
                    dry_run=False,
                    execute=True,
                )

            events = self._read_events(events_path)
            self.assertEqual(len(events), 1)
            self.assertEqual(events[0]["argv"], ["--version"])

    def test_fake_hermes_phase_failure_is_open_closed(self):
        module = self._load_canary_module()
        with tempfile.TemporaryDirectory() as td:
            work = pathlib.Path(td)
            candidate, observed_head = self._prepare_clean_candidate_root(work)
            events_path = work / "hermes-fake.log"
            os.environ["CANARY_FAKE_LOG"] = str(events_path)
            os.environ["CANARY_SOURCE_ROOT"] = str(candidate)

            hermes = self._write_fake_hermes(work, fail_update_for="recon")
            python = self._write_fake_hermes_python(work)

            with self.assertRaises(module.LifecycleCanaryError):
                module.run_host_canary(
                    root=str(candidate),
                    candidate_head=observed_head,
                    hermes=str(hermes),
                    work_root=str(work / "workspace"),
                    evidence=str(work / "evidence.json"),
                    hermes_python=str(python),
                    dry_run=False,
                    execute=True,
                )

            events = self._read_events(events_path)
            tags = [evt["argv"][1] if len(evt["argv"]) > 1 else "" for evt in events]
            self.assertIn("update", tags)
            self.assertIn("delete", tags)
            receipt = json.loads((work / "evidence.json").read_text(encoding="utf-8"))
            self.assertEqual(receipt["status"], "failed")
            self.assertFalse(receipt["claims"]["all_claims"])

    def test_sensitive_restore_names_are_rejected_and_ordinary_names_are_accepted(self):
        module = self._load_canary_module()
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            for name in (
                "auth", "se" "cret", "token", "pass" "word", "pass" "wd", "credential",
                "api" "_key", "access" "_key", "private" "_key", "provider", "aws", "azure", "gcp",
                "gateway-state.json", "alias-map", "service-state.yaml",
            ):
                candidate = root / name
                candidate.write_text("ordinary: content\n", encoding="utf-8")
                self.assertFalse(module._verify_no_secret_names(root), name)
                candidate.unlink()
            ordinary = root / "notes.yaml"
            ordinary.write_text("ordinary: accepted\n", encoding="utf-8")
            self.assertTrue(module._verify_no_secret_names(root))
            for field in (
                "auth", "se" "cret", "token", "pass" "word", "pass" "wd", "credential",
                "api" "_key", "access" "_key", "private" "_key", "provider", "aws", "azure", "gcp",
            ):
                ordinary.write_text(f"{field}: rejected\n", encoding="utf-8")
                self.assertFalse(module._verify_no_secret_names(root), field)
            ordinary.write_text("ordinary: accepted\n", encoding="utf-8")
            self.assertTrue(module._verify_no_secret_names(root))

    def test_sensitive_tar_member_names_are_rejected_and_ordinary_members_are_accepted(self):
        module = self._load_canary_module()
        self.assertTrue(module._assert_secret_exclusion_in_tar(["local/notes.yaml"]))
        for member in (
            "local/gateway-state.json",
            "memories/alias-map",
            "sessions/service-state.yaml",
        ):
            with self.subTest(member=member):
                self.assertFalse(module._assert_secret_exclusion_in_tar([member]))

    def test_noop_success_and_each_phase_failure_emit_bounded_cleanup_receipts(self):
        module = self._load_canary_module()
        for phase in ("install", "update", "import", "delete"):
            with self.subTest(phase=phase), tempfile.TemporaryDirectory() as td:
                work = pathlib.Path(td)
                candidate, observed_head = self._prepare_clean_candidate_root(work)
                events_path = work / "hermes-fake.log"
                os.environ["CANARY_FAKE_LOG"] = str(events_path)
                os.environ["CANARY_SOURCE_ROOT"] = str(candidate)
                hermes = self._write_fake_hermes(work, fail_phase=phase)
                with self.assertRaises(module.LifecycleCanaryError):
                    module.run_host_canary(
                        root=str(candidate), candidate_head=observed_head, hermes=str(hermes),
                        work_root=str(work / "workspace"), evidence=str(work / "evidence.json"), execute=True,
                    )
                receipt = json.loads((work / "evidence.json").read_text(encoding="utf-8"))
                self.assertEqual(receipt["status"], "failed")
                self.assertFalse(receipt["claims"]["all_claims"])
                self.assertTrue((work / ".lifecycle-parent-sentinel").exists())
                self.assertTrue(any(evt["argv"][1:2] == ["delete"] for evt in self._read_events(events_path)))

        with tempfile.TemporaryDirectory() as td:
            work = pathlib.Path(td)
            candidate, observed_head = self._prepare_clean_candidate_root(work)
            noop = work / "noop-hermes"
            noop.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            noop.chmod(0o700)
            with self.assertRaises(module.LifecycleCanaryError):
                module.run_host_canary(
                    root=str(candidate), candidate_head=observed_head, hermes=str(noop),
                    work_root=str(work / "workspace"), evidence=str(work / "evidence.json"), execute=True,
                )

    def test_docker_run_is_dry_run_when_not_execute(self):
        module = self._load_canary_module()
        with tempfile.TemporaryDirectory() as td:
            work = pathlib.Path(td)
            candidate, observed_head = self._prepare_clean_candidate_root(work)
            host_receipt = work / "host-receipt.json"
            inventory = module.tokenize_receipt_paths(
                module.compute_candidate_inventory(candidate),
                candidate_root=str(candidate),
                work_root=str(work / "docker-work"),
            )
            records = {
                profile: {
                    "filename": f"{profile}.tar.gz",
                    "sha256": "a" * 64,
                    "members": [f"{profile}/local", f"{profile}/memories"],
                    "member_count": 2,
                }
                for profile in module.CANDIDATE_PROFILES
            }
            payload = {
                "mode": "host",
                "status": "passed",
                "candidate_head": observed_head,
                "hermes_version": "0.20.5",
                "claims": {
                    "all_claims": True,
                    "secrets_excluded": True,
                },
                "flags": {
                    "archive_records": records,
                },
                "inventory_before": inventory,
                "inventory_after": inventory,
            }
            host_receipt.write_text(json.dumps(payload), encoding="utf-8")

            calls: list[list[str]] = []
            original_run = module.run_command

            def fake_run_command(argv: list[str], **kwargs: Any) -> dict[str, Any]:
                calls.append(list(argv))
                return {
                    "command": list(argv),
                    "returncode": 0,
                    "stdout_hash": "deadbeef",
                    "stderr_hash": "000000",
                    "elapsed_seconds": 0.0,
                    "env": kwargs.get("env", {}),
                }

            try:
                module.run_command = fake_run_command
                receipt = module.run_docker_canary(
                    root=str(candidate),
                    candidate_head=observed_head,
                    image="hermes@sha256:" + "b" * 64,
                    work_root=str(work / "docker-work"),
                    host_work_root=str(work / "host-work"),
                    host_receipt=str(host_receipt),
                    host_archives=str(work / "host-archives"),
                    evidence=str(work / "evidence.json"),
                    dry_run=True,
                    execute=False,
                )
            finally:
                module.run_command = original_run

            self.assertEqual(receipt["status"], "dry_run")
            self.assertEqual(receipt["phase_history"][0]["phase"], "preflight")
            self.assertEqual(calls, [])

    def test_docker_bad_image_reference_is_rejected(self):
        module = self._load_canary_module()
        with tempfile.TemporaryDirectory() as td:
            work = pathlib.Path(td)
            candidate, observed_head = self._prepare_clean_candidate_root(work)
            with self.assertRaises(ValueError):
                module.run_docker_canary(
                    root=str(candidate),
                    candidate_head=observed_head,
                    image="hermes:0.19.1",
                    work_root=str(work / "docker-work"),
                    host_work_root=str(work / "host-work"),
                    host_receipt=str(work / "host-receipt.json"),
                    host_archives=str(work / "host-archives"),
                    evidence=str(work / "evidence.json"),
                    dry_run=True,
                )

    def test_docker_rejects_untruthful_host_receipt_claims(self):
        module = self._load_canary_module()
        with tempfile.TemporaryDirectory() as td:
            work = pathlib.Path(td)
            candidate, observed_head = self._prepare_clean_candidate_root(work)
            host_receipt = work / "host-receipt.json"
            payload = {
                "mode": "host",
                "status": "failed",
                "candidate_head": observed_head,
                "hermes_version": "0.20.5",
                "claims": {
                    "all_claims": True,
                    "secrets_excluded": True,
                },
                "flags": {"archive_records": {}},
                "inventory_before": {
                    "root": str(candidate),
                    "tree": "0" * 64,
                    "entries": [],
                    "entry_count": 0,
                },
                "inventory_after": {
                    "root": str(candidate),
                    "tree": "0" * 64,
                    "entries": [],
                    "entry_count": 0,
                },
            }
            host_receipt.write_text(json.dumps(payload), encoding="utf-8")

            with self.assertRaises(ValueError):
                module.run_docker_canary(
                    root=str(candidate),
                    candidate_head=observed_head,
                    image="hermes@sha256:" + "b" * 64,
                    work_root=str(work / "docker-work"),
                    host_work_root=str(work / "host-work"),
                    host_receipt=str(host_receipt),
                    host_archives=str(work / "host-archives"),
                    evidence=str(work / "evidence.json"),
                    dry_run=True,
                )

    def test_docker_hardened_container_invocation(self):
        module = self._load_canary_module()
        with tempfile.TemporaryDirectory() as td:
            work = pathlib.Path(td)
            candidate, observed_head = self._prepare_clean_candidate_root(work)

            events_path = work / "hermes-fake.log"
            os.environ["CANARY_FAKE_LOG"] = str(events_path)
            os.environ["CANARY_SOURCE_ROOT"] = str(candidate)
            hermes = self._write_fake_hermes(work)
            hermes_python = self._write_fake_hermes_python(work)

            host_receipt_path = work / "host-receipt.json"
            module.run_host_canary(
                root=str(candidate),
                candidate_head=observed_head,
                hermes=str(hermes),
                work_root=str(work / "host-work"),
                evidence=str(host_receipt_path),
                hermes_python=str(hermes_python),
                execute=True,
            )

            host_receipt = json.loads(host_receipt_path.read_text(encoding="utf-8"))
            host_receipt_records = host_receipt["flags"]["archive_records"]
            self.assertEqual(set(host_receipt_records), set(module.CANDIDATE_PROFILES))
            owner_portable_member = "owner-agent/local/canary-state.json"
            self.assertIn(owner_portable_member, host_receipt_records["owner-agent"]["members"])

            source_owner = candidate / "profiles" / "owner-agent"
            self.assertFalse((source_owner / "local").exists())
            self.assertFalse((source_owner / "memories").exists())

            original_run = module.run_command
            captured: dict[str, Any] = {}

            def fake_run_command(argv: list[str], **kwargs: Any) -> dict[str, Any]:
                captured["argv"] = list(argv)
                worker_mount = pathlib.Path(work / "docker-work" / "docker-worker-receipt.json")
                worker_mount.parent.mkdir(parents=True, exist_ok=True)
                evidence_path = worker_mount
                worker_receipt = {
                    "mode": "docker",
                    "status": "passed",
                    "candidate_head": observed_head,
                    "hermes_version": "0.20.5",
                    "claims": {"all_claims": True},
                    "flags": {},
                    "phase_history": [],
                }
                evidence_path.write_text(json.dumps(worker_receipt), encoding="utf-8")
                return {
                    "command": list(argv),
                    "returncode": 0,
                    "stdout_hash": "".ljust(64, "a"),
                    "stderr_hash": "".ljust(64, "0"),
                    "elapsed_seconds": 0.0,
                    "env": kwargs.get("env", {}),
                }

            try:
                module.run_command = fake_run_command
                receipt = module.run_docker_canary(
                    root=str(candidate),
                    candidate_head=observed_head,
                    image="hermes@sha256:" + "c" * 64,
                    work_root=str(work / "docker-work"),
                    host_work_root=str(work / "host-work"),
                    host_receipt=str(host_receipt_path),
                    host_archives=str(work / "host-work" / "archives"),
                    evidence=str(work / "evidence.json"),
                    execute=True,
                )
            finally:
                module.run_command = original_run

            argv = captured.get("argv", [])
            self.assertIn("--network", argv)
            self.assertIn("none", argv)
            self.assertIn("--read-only", argv)
            self.assertIn("--security-opt", argv)
            self.assertIn("no-new-privileges", " ".join(argv))
            self.assertIn("--cap-drop", argv)
            self.assertIn("--pids-limit", argv)
            self.assertIn("--memory", argv)
            self.assertIn("--cpus", argv)
            self.assertIn("--tmpfs", argv)
            joined = " ".join(argv)
            self.assertIn(f"{str(candidate)}:/candidate:ro", joined)
            self.assertIn("/candidate-host/receipt.json:ro", joined)
            self.assertIn("/candidate-host/archives:ro", joined)
            work_mount = str(work / "docker-work")
            self.assertIn(f"{work_mount}:/tmp/candidate-work", joined)
            self.assertIn(f"{work_mount}:/tmp/candidate-work:rw", joined)
            self.assertNotIn("/var/run/docker.sock", joined)
            joined = " ".join(argv)
            self.assertIn("-e PATH=/usr/bin:/bin", joined)
            self.assertIn("-e HOME=/tmp/home", joined)
            self.assertIn("-e TMPDIR=/tmp", joined)
            self.assertIn("-v", argv)
            tmpfs_index = argv.index("--tmpfs")
            self.assertEqual(argv[tmpfs_index + 1], "/tmp:rw,noexec,nosuid,nodev,size=64m")
            expected_uid = os.lstat(host_receipt_path).st_uid
            expected_gid = os.lstat(host_receipt_path).st_gid
            self.assertIn("--user", argv)
            user_index = argv.index("--user")
            self.assertEqual(argv[user_index + 1], f"{expected_uid}:{expected_gid}")
            self.assertEqual(receipt["status"], "passed")

    def test_docker_rejects_owner_mismatch_between_receipt_archive_and_work_root(self):
        module = self._load_canary_module()
        with tempfile.TemporaryDirectory() as td:
            work = pathlib.Path(td)
            candidate, observed_head = self._prepare_clean_candidate_root(work)

            events_path = work / "hermes-fake.log"
            os.environ["CANARY_FAKE_LOG"] = str(events_path)
            os.environ["CANARY_SOURCE_ROOT"] = str(candidate)
            hermes = self._write_fake_hermes(work)
            hermes_python = self._write_fake_hermes_python(work)

            host_receipt_path = work / "host-receipt.json"
            module.run_host_canary(
                root=str(candidate),
                candidate_head=observed_head,
                hermes=str(hermes),
                work_root=str(work / "host-work"),
                evidence=str(host_receipt_path),
                hermes_python=str(hermes_python),
                execute=True,
            )

            original_owner_fn = module._path_owner_identity

            def fake_owner(path: os.PathLike[str] | str) -> tuple[int, int]:
                if str(path) == str(host_receipt_path):
                    return (1111, 1111)
                if str(path).endswith("host-work"):
                    return (2222, 2222)
                if str(path).endswith("archives"):
                    return (3333, 3333)
                return original_owner_fn(path)

            try:
                module._path_owner_identity = fake_owner
                with self.assertRaises(module.UnsafeInvocationError):
                    module.run_docker_canary(
                        root=str(candidate),
                        candidate_head=observed_head,
                        image="hermes@sha256:" + "c" * 64,
                        work_root=str(work / "docker-work"),
                        host_work_root=str(work / "host-work"),
                        host_receipt=str(host_receipt_path),
                        host_archives=str(work / "host-work" / "archives"),
                        evidence=str(work / "evidence.json"),
                        execute=True,
                    )
            finally:
                module._path_owner_identity = original_owner_fn

    def test_worker_inventory_comparison_is_candidate_root_independent(self):
        module = self._load_canary_module()
        with tempfile.TemporaryDirectory() as td:
            work = pathlib.Path(td)
            candidate, observed_head = self._prepare_clean_candidate_root(work)

            # Ensure each profile has a valid archive record shape, even though execute=false path won't copy files.
            inventory = module.compute_candidate_inventory(candidate)
            alt_root = str(pathlib.Path(candidate).parent / "different-root")
            alt_inventory = dict(inventory)
            alt_inventory["root"] = alt_root

            host_receipt = {
                "mode": "host",
                "status": "passed",
                "candidate_head": observed_head,
                "hermes_version": module.CANARY_LIMITS["required_hermes_version"],
                "claims": {
                    "all_claims": True,
                    "secrets_excluded": True,
                },
                "flags": {
                    "archive_records": {
                        profile: {
                            "filename": f"{profile}.tar.gz",
                            "sha256": "0" * 64,
                            "members": [],
                            "member_count": 0,
                        }
                        for profile in module.CANDIDATE_PROFILES
                    }
                },
                "inventory_before": alt_inventory,
                "inventory_after": alt_inventory,
            }

            host_receipt_path = work / "host-receipt.json"
            host_receipt_path.write_text(json.dumps(host_receipt), encoding="utf-8")

            receipt = module.run_worker_phase(
                mode="docker",
                root=str(candidate),
                input_receipt=str(host_receipt_path),
                candidate_head=observed_head,
                work_root=str(work / "worker-work"),
                host_receipt=str(host_receipt_path),
                host_archives=str(work / "host-work" / "archives"),
                hermes=str(work / "usr/bin/hermes"),
                dry_run=True,
            )
            self.assertEqual(receipt["status"], "dry_run")

            bad_inventory = dict(alt_inventory)
            bad_inventory["entries"] = list(alt_inventory["entries"])
            bad_inventory["entries"][0]["sha256"] = "f" * 64
            bad_receipt = dict(host_receipt)
            bad_receipt["inventory_before"] = bad_inventory
            bad_receipt_path = work / "bad-host-receipt.json"
            bad_receipt_path.write_text(json.dumps(bad_receipt), encoding="utf-8")

            with self.assertRaises(ValueError):
                module.run_worker_phase(
                    mode="docker",
                    root=str(candidate),
                    input_receipt=str(bad_receipt_path),
                    candidate_head=observed_head,
                    work_root=str(work / "worker-work"),
                    host_receipt=str(bad_receipt_path),
                    host_archives=str(work / "host-work" / "archives"),
                    hermes=str(work / "usr/bin/hermes"),
                    dry_run=True,
                )

    def test_docker_worker_restore_and_archive_mismatch_detection(self):
        module = self._load_canary_module()
        with tempfile.TemporaryDirectory() as td:
            work = pathlib.Path(td)
            candidate, observed_head = self._prepare_clean_candidate_root(work)

            events_path = work / "hermes-fake.log"
            os.environ["CANARY_FAKE_LOG"] = str(events_path)
            os.environ["CANARY_SOURCE_ROOT"] = str(candidate)
            hermes = self._write_fake_hermes(work)
            hermes_python = self._write_fake_hermes_python(work)
            host_receipt_path = work / "host-receipt.json"
            host_work_root = work / "host-work"

            host = module.run_host_canary(
                root=str(candidate),
                candidate_head=observed_head,
                hermes=str(hermes),
                work_root=str(host_work_root),
                evidence=str(host_receipt_path),
                hermes_python=str(hermes_python),
                execute=True,
            )

            worker_result = module.run_worker_phase(
                mode="docker",
                root=str(candidate),
                candidate_head=observed_head,
                input_receipt=str(host_receipt_path),
                host_receipt=str(host_receipt_path),
                work_root=str(work / "worker-work"),
                host_archives=str(host_work_root / "archives"),
                hermes=str(hermes),
                execute=True,
            )
            self.assertEqual(worker_result["status"], "passed")
            self.assertTrue(worker_result["claims"]["all_claims"])

            # corrupt one archive and verify mismatch failure path is enforced
            archive_files = sorted((host_work_root / "archives").glob("*.tar.gz"))
            assert archive_files, "expected at least one archive"
            archive_files[0].write_bytes(archive_files[0].read_bytes() + b"corrupt")
            with self.assertRaises(module.UnsafeInvocationError):
                module.run_worker_phase(
                    mode="docker",
                    root=str(candidate),
                    candidate_head=observed_head,
                    input_receipt=str(host_receipt_path),
                    host_receipt=str(host_receipt_path),
                    work_root=str(work / "worker-work-mismatch"),
                    host_archives=str(host_work_root / "archives"),
                    hermes=str(hermes),
                    execute=True,
                )

if __name__ == "__main__":
    unittest.main()
