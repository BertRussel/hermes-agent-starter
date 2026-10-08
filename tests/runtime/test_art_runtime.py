from __future__ import annotations

import ast
import copy
import importlib
import math
import sys
from pathlib import Path
from typing import Any, Callable
import unittest


REPO_ROOT = Path(__file__).resolve().parents[2]
RUNTIME_SRC_ROOT = REPO_ROOT / "runtimes" / "art-runtime" / "src"
RUNTIME_ROOT = REPO_ROOT / "runtimes" / "art-runtime"
RUNTIME_RUNTIME_PATH = RUNTIME_SRC_ROOT / "art_runtime" / "runtime.py"
RUNTIME_INIT_PATH = RUNTIME_SRC_ROOT / "art_runtime" / "__init__.py"


def load_art_runtime():
    old_path = list(sys.path)
    if str(RUNTIME_SRC_ROOT) not in sys.path:
        sys.path.insert(0, str(RUNTIME_SRC_ROOT))
    try:
        return importlib.import_module("art_runtime")
    finally:
        sys.path[:] = old_path


class ArtRuntimeContractTests(unittest.TestCase):
    def _module(self):
        return load_art_runtime()

    def _assert_contract_error(self, fn: Callable[[Any], Any], code: str) -> None:
        runtime = self._module()
        with self.assertRaises(runtime.ContractError) as ctx:
            fn(runtime)
        self.assertEqual(ctx.exception.code, code)

    def _job_contract(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "run_id": "safe-id",
            "capability": "synthetic_contract_v1",
            "inputs": [
                {
                    "path": "inputs/example.json",
                    "sha256": "0" * 64,
                    "bytes": 123,
                }
            ],
            "outputs": ["outputs/candidate.json"],
            "limits": {
                "max_input_bytes": 1048576,
                "max_output_bytes": 16777216,
                "max_cycles": 3,
            },
            "external_access": False,
            "publication_authority": False,
        }

    def _candidate_manifest(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "run_id": "safe-id",
            "status": "candidate",
            "files": [
                {
                    "path": "outputs/candidate.json",
                    "sha256": "a" * 64,
                    "bytes": 123,
                }
            ],
            "source_sha256": ["b" * 64],
            "privacy": {
                "contains_customer_data": False,
                "contains_secrets": False,
            },
            "rights": {
                "state": "unknown",
                "external_use_allowed": False,
            },
            "external_access": False,
            "publication_authority": False,
            "approval_receipt": None,
        }

    def test_public_exports_exact_set(self):
        runtime = self._module()
        self.assertTrue(hasattr(runtime, "__all__"))
        self.assertEqual(
            list(runtime.__all__),
            [
                "ContractError",
                "canonical_json_bytes",
                "validate_candidate_manifest",
                "validate_job_contract",
                "validate_relative_path",
                "validate_sha256",
                "validate_transition",
            ],
        )
        for name in runtime.__all__:
            self.assertTrue(hasattr(runtime, name))

    def test_validate_job_contract_detached_valid_contract(self):
        runtime = self._module()
        contract = self._job_contract()
        contract["inputs"].append({"path": "inputs/second.json", "sha256": "1" * 64, "bytes": 0})
        contract_snapshot = copy.deepcopy(contract)

        normalized = runtime.validate_job_contract(contract)
        self.assertIsNot(contract, normalized)
        self.assertIsNot(contract["inputs"], normalized["inputs"])
        self.assertIsNot(contract["limits"], normalized["limits"])
        self.assertEqual(contract, contract_snapshot)
        self.assertEqual(normalized["inputs"], contract_snapshot["inputs"])

        normalized["inputs"][0]["bytes"] = 7
        self.assertEqual(contract["inputs"][0]["bytes"], 123)

    def test_validate_candidate_manifest_detached_valid_manifest(self):
        runtime = self._module()
        manifest = self._candidate_manifest()
        manifest["files"].append({"path": "outputs/secondary.json", "sha256": "c" * 64, "bytes": 5})
        manifest_snapshot = copy.deepcopy(manifest)

        normalized = runtime.validate_candidate_manifest(manifest)
        self.assertIsNot(manifest, normalized)
        self.assertIsNot(manifest["files"], normalized["files"])
        self.assertEqual(manifest, manifest_snapshot)
        self.assertEqual(normalized["files"], manifest_snapshot["files"])

        normalized["files"][0]["bytes"] = 7
        self.assertEqual(manifest["files"][0]["bytes"], 123)

    def test_validators_do_not_mutate_caller(self):
        runtime = self._module()
        contract = self._job_contract()
        manifest = self._candidate_manifest()
        contract["inputs"].append({"path": "inputs/second.json", "sha256": "1" * 64, "bytes": 0})
        manifest["files"].append({"path": "outputs/secondary.json", "sha256": "c" * 64, "bytes": 5})

        contract_snapshot = copy.deepcopy(contract)
        manifest_snapshot = copy.deepcopy(manifest)

        normalized_contract = runtime.validate_job_contract(contract)
        normalized_manifest = runtime.validate_candidate_manifest(manifest)

        self.assertEqual(contract, contract_snapshot)
        self.assertEqual(manifest, manifest_snapshot)
        self.assertIsNot(contract, normalized_contract)
        self.assertIsNot(manifest, normalized_manifest)
        self.assertIsNot(contract["inputs"], normalized_contract["inputs"])
        self.assertIsNot(manifest["files"], normalized_manifest["files"])
        normalized_contract["inputs"][1]["bytes"] = 1
        normalized_manifest["files"][0]["bytes"] = 99
        self.assertEqual(contract["inputs"][1]["bytes"], 0)
        self.assertEqual(manifest["files"][0]["bytes"], 123)
        self.assertEqual(manifest["files"][1], {"path": "outputs/secondary.json", "sha256": "c" * 64, "bytes": 5})

    def test_job_contract_missing_and_unknown_root_keys(self):
        valid = self._job_contract()
        self._assert_contract_error(
            lambda rt: rt.validate_job_contract({k: v for k, v in valid.items() if k != "capability"}),
            "missing_job_root_keys",
        )
        self._assert_contract_error(
            lambda rt: rt.validate_job_contract({**valid, "rogue": True}),
            "unexpected_job_root_keys",
        )

    def test_candidate_manifest_missing_and_unknown_root_keys(self):
        valid = self._candidate_manifest()
        self._assert_contract_error(
            lambda rt: rt.validate_candidate_manifest({k: v for k, v in valid.items() if k != "files"}),
            "missing_candidate_root_keys",
        )
        self._assert_contract_error(
            lambda rt: rt.validate_candidate_manifest({**valid, "rogue": True}),
            "unexpected_candidate_root_keys",
        )

    def test_wrong_scalars_and_containers_reject_boolean_as_integer(self):
        self._assert_contract_error(
            lambda rt: rt.validate_job_contract({**self._job_contract(), "schema_version": True}),
            "invalid_schema_version",
        )
        self._assert_contract_error(
            lambda rt: rt.validate_job_contract({**self._job_contract(), "inputs": ()}),
            "invalid_inputs_type",
        )
        self._assert_contract_error(
            lambda rt: rt.validate_job_contract({**self._job_contract(), "limits": [1, 2, 3]}),
            "invalid_limits_type",
        )
        self._assert_contract_error(
            lambda rt: rt.validate_candidate_manifest({**self._candidate_manifest(), "source_sha256": "not-list"}),
            "invalid_source_sha256_type",
        )

    def test_invalid_run_ids(self):
        invalid = ["Bad-ID", "", "-start", "a" * 64 + "a", "A-B", "a..b", "a//b", "bad$$"]
        for run_id in invalid:
            self._assert_contract_error(
                lambda rt, run_id=run_id: rt.validate_job_contract({**self._job_contract(), "run_id": run_id}),
                "invalid_run_id",
            )
            self._assert_contract_error(
                lambda rt, run_id=run_id: rt.validate_candidate_manifest({**self._candidate_manifest(), "run_id": run_id}),
                "invalid_run_id",
            )

    def test_validate_relative_path_rejects_invalid_forms(self):
        runtime = self._module()
        for bad in ["", "/abs/path.json", "foo\\bar.json", "foo/./bar.json", "foo/../bar.json", "foo//bar", "a\tb", "http://example.com/x"]:
            self._assert_contract_error(lambda rt, bad=bad: rt.validate_relative_path(bad), "invalid_path")
        for good in ["inputs/example.json", "outputs/candidate.json", "a.b/c_d"]:
            self.assertEqual(runtime.validate_relative_path(good), good)

    def test_duplicates_and_aliases_rejected(self):
        self._assert_contract_error(
            lambda rt: rt.validate_job_contract(
                {
                    **self._job_contract(),
                    "inputs": [
                        {"path": "inputs/x.json", "sha256": "a" * 64, "bytes": 1},
                        {"path": "inputs/x.json", "sha256": "b" * 64, "bytes": 2},
                    ],
                }
            ),
            "duplicate_input_path",
        )
        self._assert_contract_error(
            lambda rt: rt.validate_job_contract(
                {
                    **self._job_contract(),
                    "outputs": ["outputs/x.json", "outputs/x.json"],
                }
            ),
            "duplicate_output_path",
        )
        self._assert_contract_error(
            lambda rt: rt.validate_job_contract(
                {
                    **self._job_contract(),
                    "inputs": [{"path": "inputs/x.json", "sha256": "a" * 64, "bytes": 1}],
                    "outputs": ["inputs/x.json"],
                }
            ),
            "input_output_alias",
        )

    def test_validate_sha256_rejects_invalid_values(self):
        self._assert_contract_error(
            lambda rt: rt.validate_sha256(123),
            "invalid_sha256_type",
        )
        self._assert_contract_error(
            lambda rt: rt.validate_sha256("GG" * 32),
            "invalid_sha256_format",
        )
        self._assert_contract_error(
            lambda rt: rt.validate_sha256("A" * 64),
            "invalid_sha256_format",
        )
        self._assert_contract_error(
            lambda rt: rt.validate_sha256("abc"),
            "invalid_sha256_format",
        )

    def test_input_and_output_limits_rejected(self):
        self._assert_contract_error(
            lambda rt: rt.validate_job_contract(
                {
                    **self._job_contract(),
                    "inputs": [{"path": "inputs/x.json", "sha256": "a" * 64, "bytes": 1048577}],
                }
            ),
            "input_bytes_exceeded",
        )
        self._assert_contract_error(
            lambda rt: rt.validate_job_contract(
                {
                    **self._job_contract(),
                    "limits": {
                        "max_input_bytes": 1048577,
                        "max_output_bytes": 16777216,
                        "max_cycles": 3,
                    },
                }
            ),
            "invalid_limits_values",
        )
        self._assert_contract_error(
            lambda rt: rt.validate_job_contract(
                {
                    **self._job_contract(),
                    "limits": {
                        "max_input_bytes": 1048576,
                        "max_output_bytes": 16777217,
                        "max_cycles": 3,
                    },
                }
            ),
            "invalid_limits_values",
        )
        self._assert_contract_error(
            lambda rt: rt.validate_job_contract(
                {
                    **self._job_contract(),
                    "limits": {
                        "max_input_bytes": 1048576,
                        "max_output_bytes": 16777216,
                        "max_cycles": 4,
                    },
                }
            ),
            "invalid_limits_values",
        )

    def test_authority_and_receipt_constraints(self):
        self._assert_contract_error(
            lambda rt: rt.validate_job_contract({**self._job_contract(), "external_access": True}),
            "forbidden_authority",
        )
        self._assert_contract_error(
            lambda rt: rt.validate_job_contract({**self._job_contract(), "publication_authority": True}),
            "forbidden_authority",
        )
        self._assert_contract_error(
            lambda rt: rt.validate_candidate_manifest(
                {
                    **self._candidate_manifest(),
                    "privacy": {
                        "contains_customer_data": True,
                        "contains_secrets": False,
                    },
                }
            ),
            "forbidden_privacy",
        )
        self._assert_contract_error(
            lambda rt: rt.validate_candidate_manifest(
                {
                    **self._candidate_manifest(),
                    "rights": {
                        "state": "unknown",
                        "external_use_allowed": True,
                    },
                }
            ),
            "forbidden_rights",
        )
        self._assert_contract_error(
            lambda rt: rt.validate_candidate_manifest(
                {**self._candidate_manifest(), "approval_receipt": {"receipt": "x"}}
            ),
            "invalid_approval_receipt",
        )
        self._assert_contract_error(
            lambda rt: rt.validate_candidate_manifest({**self._candidate_manifest(), "external_access": True}),
            "forbidden_authority",
        )
        self._assert_contract_error(
            lambda rt: rt.validate_candidate_manifest({**self._candidate_manifest(), "publication_authority": True}),
            "forbidden_authority",
        )

    def test_forbidden_authority_statuses(self):
        for status in ["approved", "final", "published", "production", "released"]:
            self._assert_contract_error(
                lambda rt, status=status: rt.validate_candidate_manifest({**self._candidate_manifest(), "status": status}),
                "invalid_status",
            )

    def test_validate_transition_edges(self):
        runtime = self._module()
        self.assertEqual(runtime.validate_transition("initialized", "candidate"), "candidate")
        self.assertEqual(runtime.validate_transition("initialized", "blocked"), "blocked")
        self.assertEqual(runtime.validate_transition("candidate", "rejected"), "rejected")
        self.assertEqual(runtime.validate_transition("candidate", "blocked"), "blocked")
        self.assertEqual(runtime.validate_transition("candidate", "reviewable_awaiting_owner"), "reviewable_awaiting_owner")
        self.assertEqual(runtime.validate_transition("rejected", "candidate"), "candidate")
        self.assertEqual(runtime.validate_transition("rejected", "blocked"), "blocked")

        self._assert_contract_error(lambda rt: rt.validate_transition("candidate", "initialized"), "invalid_transition")
        self._assert_contract_error(lambda rt: rt.validate_transition("rejected", "rejected"), "invalid_transition")
        self._assert_contract_error(lambda rt: rt.validate_transition("blocked", "candidate"), "invalid_transition")
        self._assert_contract_error(lambda rt: rt.validate_transition("reviewable_awaiting_owner", "candidate"), "invalid_transition")

    def test_canonical_json_bytes(self):
        runtime = self._module()
        payload = {
            "z": 1,
            "a": [3, 1, 2],
            "m": {"b": 2, "a": 1},
        }
        expected = b'{"a":[3,1,2],"m":{"a":1,"b":2},"z":1}\n'
        output = runtime.canonical_json_bytes(payload)
        self.assertEqual(bytes(output), expected)
        with self.assertRaises(ValueError):
            runtime.canonical_json_bytes({"bad": float("nan")})
        with self.assertRaises(ValueError):
            runtime.canonical_json_bytes({"bad": math.inf})

    def test_validators_do_not_mutate_caller(self):
        runtime = self._module()
        contract = self._job_contract()
        manifest = self._candidate_manifest()

        normalized = runtime.validate_job_contract(copy.deepcopy(contract))
        normalized["inputs"].append({"path": "outputs/poke.json", "sha256": "f" * 64, "bytes": 1})
        self.assertEqual(contract, self._job_contract())

        normalized = runtime.validate_candidate_manifest(copy.deepcopy(manifest))
        normalized["files"].append({"path": "outputs/poke.json", "sha256": "f" * 64, "bytes": 1})
        self.assertEqual(manifest, self._candidate_manifest())

    def test_source_ast_import_allowlist(self):
        if not RUNTIME_RUNTIME_PATH.exists():
            self.skipTest("art runtime source not yet implemented")

        tree = ast.parse(RUNTIME_RUNTIME_PATH.read_text(encoding="utf-8"))
        allowed_roots = {"__future__", "copy", "json", "math", "re", "pathlib", "typing", "collections"}
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.module is None:
                    continue
                self.assertIn(node.module.split(".")[0], allowed_roots)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    self.assertIn(alias.name.split(".")[0], allowed_roots)

    def test_source_ast_prohibited_surfaces(self):
        if not RUNTIME_RUNTIME_PATH.exists():
            self.skipTest("art runtime source not yet implemented")

        tree = ast.parse(RUNTIME_RUNTIME_PATH.read_text(encoding="utf-8"))
        banned_import_roots = {"os", "subprocess", "random", "time", "socket", "urllib", "http", "importlib"}
        banned_call_names = {"eval", "exec", "compile", "open", "__import__", "getenv", "system", "popen", "run"}

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    self.assertNotIn(alias.name.split(".")[0], banned_import_roots)

            if isinstance(node, ast.ImportFrom) and node.module is not None:
                self.assertNotIn(node.module.split(".")[0], banned_import_roots)

            if isinstance(node, ast.Call):
                func_name = None
                if isinstance(node.func, ast.Name):
                    func_name = node.func.id
                elif isinstance(node.func, ast.Attribute):
                    func_name = node.func.attr

                if func_name in banned_call_names:
                    self.fail(f"prohibited runtime surface detected: {func_name}")

    def test_art_runtime_manifest_owned_files_exactly_four(self):
        if not (RUNTIME_ROOT.exists() and RUNTIME_RUNTIME_PATH.exists() and RUNTIME_INIT_PATH.exists()):
            self.skipTest("art runtime source not yet implemented")

        expected = {
            "README.md",
            "runtime.yaml",
            "src/art_runtime/__init__.py",
            "src/art_runtime/runtime.py",
        }

        collected_files = {
            path.relative_to(RUNTIME_ROOT).as_posix()
            for path in RUNTIME_ROOT.rglob("*")
            if path.is_file() and not path.is_symlink()
        }

        self.assertEqual(collected_files, expected)
        for rel in collected_files:
            self.assertFalse(any(part.startswith(".") for part in rel.split("/")))


if __name__ == "__main__":
    unittest.main()
