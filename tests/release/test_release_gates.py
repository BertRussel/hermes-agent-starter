import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import hashlib
from pathlib import Path
import unittest
from unittest.mock import patch
import copy

from hermes_cli.profile_distribution import DistributionError, plan_install, read_manifest
from scripts import verify_release as verifier


SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "verify_release.py"


class VerifyReleaseTests(unittest.TestCase):
    def owner_profile_dir(self) -> Path:
        """Root of the candidate owner profile under this repository."""
        return Path(__file__).resolve().parents[2] / "profiles" / "owner-agent"

    def run_verify(self, root: Path, args=None, env=None):
        if args is None:
            args = []
        cmd = [sys.executable, str(SCRIPT), "--root", str(root), *args]
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
        )
        return proc

    def init_git_fixture(self, root: Path) -> None:
        subprocess.run(["git", "-C", str(root), "init"], check=True, capture_output=True, text=True)
        subprocess.run(["git", "-C", str(root), "config", "user.email", "ci@example.com"], check=True, capture_output=True, text=True)
        subprocess.run(["git", "-C", str(root), "config", "user.name", "CI Bot"], check=True, capture_output=True, text=True)
        subprocess.run(["git", "-C", str(root), "add", "."], check=True, capture_output=True, text=True)
        subprocess.run(["git", "-C", str(root), "commit", "-qm", "fixture"], check=True, capture_output=True, text=True)

    def git_head_for_root(self, root: Path) -> str:
        proc = subprocess.run(
            [
                "git",
                "--no-replace-objects",
                "-C",
                str(root),
                "rev-parse",
                "HEAD",
            ],
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            self.fail(f"unable to read git head for fixture: {proc.stderr}")
        return proc.stdout.splitlines()[0].strip()

    def git_fixture_with_receipts(self, root: Path) -> Path:
        root = self.make_realistic_slice1_fixture(root)
        self.init_git_fixture(root)
        return root

    def make_linked_git_receipt_fixture(self, root: Path):
        main = self.git_fixture_with_receipts(root / "main")
        linked = root / "linked"
        subprocess.run(
            [
                "git",
                "-C",
                str(main),
                "worktree",
                "add",
                "--detach",
                str(linked),
                "HEAD",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        return main, linked

    def candidate_head(self, root: Path) -> str:
        if not (root / ".git").is_dir():
            return "0" * 40
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
            return "0" * 40

        head = proc.stdout.strip()
        if not re.fullmatch(r"[0-9a-f]{40}", head):
            return "0" * 40
        return head

    def write_receipt(self, root: Path, name: str, payload: dict, directory: Path | None = None) -> Path:
        receipt_dir = directory if directory is not None else root
        receipt_dir.mkdir(parents=True, exist_ok=True)
        path = receipt_dir / name
        path.write_text(json.dumps(payload) + "\n", encoding="utf-8")
        return path

    def receipt_archive_records(self) -> dict:
        return {
            profile: {
                "filename": f"{profile}.tar",
                "sha256": "a" * 64,
                "members": ["README.md"],
                "member_count": 1,
            }
            for profile in sorted(verifier.CANDIDATE_PROFILES)
        }

    def make_receipt_payload(
        self,
        *,
        mode: str,
        candidate_head: str,
        candidate_profiles=None,
        claims=None,
        overrides=None,
    ) -> dict:
        if candidate_profiles is None:
            candidate_profiles = sorted(verifier.CANDIDATE_PROFILES)
        if claims is None:
            claims = {"all_claims": True}
            if mode == "host":
                claims.update({name: True for name in verifier.COMPATIBILITY_REQUIREMENT_CLAIMS})
            elif mode == "docker":
                claims.update({"all_claims": True})

        payload = {
            "schema_version": "1.0.0",
            "receipt_type": "lifecycle-canary",
            "mode": mode,
            "type": mode,
            "status": "passed",
            "hermes_version": verifier.CANDIDATE_HERMES_VERSION,
            "candidate_head": candidate_head,
            "candidate_profiles": candidate_profiles,
            "claims": claims,
            "flags": {
                "archive_records": self.receipt_archive_records(),
            },
        }
        if overrides:
            payload.update(overrides)
        if mode == "docker":
            payload["flags"].setdefault("host_archive_hashes", self.receipt_archive_records())
        return payload

    def test_00_candidate_hermes_version_is_expected(self):
        self.assertEqual(verifier.CANDIDATE_HERMES_VERSION, "0.20.5")

    def test_00_release_index_documents_expected_compatibility_version(self):
        root = Path(__file__).resolve().parents[2]
        release_index = (root / "release-index.yaml").read_text(encoding="utf-8")
        self.assertIn('"version": "0.20.5"', release_index)

    def test_00_readme_declares_expected_compatibility_hermes_version(self):
        root = Path(__file__).resolve().parents[2]
        readme = (root / "README.md").read_text(encoding="utf-8")
        self.assertIn("it to be exactly `0.20.5`", readme)

    def write_compatibility_receipts(
        self,
        root: Path,
        *,
        directory: Path | None = None,
        host_payload: dict | None,
        docker_payload: dict | None,
    ) -> tuple[Path | None, Path | None]:
        host_path = None
        docker_path = None

        if host_payload is not None:
            host_path = "host-compatibility-receipt.json"
            host_path = self.write_receipt(root, host_path, host_payload, directory=directory)

        if docker_payload is not None:
            docker_path = "docker-compatibility-receipt.json"
            docker_path = self.write_receipt(root, docker_path, docker_payload, directory=directory)

        return host_path, docker_path

    def set_release_component(self, data: dict, name: str, key: str, value) -> None:
        for component in data.get("components", []):
            if component.get("name") == name:
                component[key] = value
                return
        self.fail(f"component not found: {name}")

    def mutation_with_release_payload(self, root: Path, mutator):
        data = json.loads((root / "release-index.yaml").read_text(encoding="utf-8"))
        mutator(data)
        (root / "release-index.yaml").write_text(json.dumps(data) + "\n", encoding="utf-8")

    def mutate_runtime_manifest(
        self, root: Path, changes: dict, *, remove_keys=None, component: str = "engineering-runtime"
    ):
        if remove_keys is None:
            remove_keys = []

        manifest_path = root / "runtimes" / component / "runtime.yaml"
        text = manifest_path.read_text(encoding="utf-8")

        for key in remove_keys:
            lines = []
            skip_list = False
            skip_key = False
            for line in text.splitlines(True):
                if skip_list:
                    if line.startswith("  - "):
                        continue
                    skip_list = False
                if skip_key:
                    continue
                if line.startswith(f"{key}:"):
                    skip_key = True
                    if line.startswith("owned_files:"):
                        skip_list = True
                    continue
                lines.append(line)
            text = "".join(lines)

        for key, value in changes.items():
            if isinstance(value, bool):
                value = "true" if value else "false"
            elif isinstance(value, (int, float)):
                value = str(value)

            if key == "dependencies" and isinstance(value, list):
                replacement = "dependencies:\n" + "".join(f"  - {item}\n" for item in value)
                if not value:
                    replacement += ""
                text = re.sub(r"^dependencies:\s*\[.*\]\n", replacement, text, flags=re.MULTILINE)
                if "dependencies:" not in text:
                    text = text.rstrip() + "\n" + replacement + "\n"
                continue

            if key == "owned_files" and isinstance(value, list):
                new_block = "owned_files:\n" + "".join(f"  - {item}\n" for item in value)
                text = re.sub(
                    r"^owned_files:\n(?:  - .*\n)*(?=^publication_authority:)",
                    new_block,
                    text,
                    flags=re.MULTILINE,
                )
                if "owned_files:" not in text:
                    text = text.rstrip() + "\n" + new_block + "\n"
                continue

            pattern = rf"^{re.escape(key)}: .*\n"
            if re.search(pattern, text, flags=re.MULTILINE):
                text = re.sub(pattern, f"{key}: {value}\n", text, flags=re.MULTILINE)
            else:
                text = text.rstrip() + "\n" + f"{key}: {value}\n"

        manifest_path.write_text(text, encoding="utf-8")

    def write_json(self, root: Path, payload: dict):
        (root / "release-index.yaml").write_text(json.dumps(payload, indent=2) + "\n")

    def make_component_readme(self, root: Path, rel: str, text: str = ""):
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            f"# {rel}\n\n"
            "Status: development\n"
            "Purpose: development placeholder\n"
            "Payload import: none\n"
            "Boundary: blocked until gates pass\n"
            + text
        )

    def _fixture_provenance_markdown(self) -> str:
        return (
            "| Component | Provenance | Status | Notes |\n"
            "| --- | --- | --- | --- |\n"
            "| owner-agent | newly authored | original | pending publication |\n"
            "| art | no-payload | blocked | pending |\n"
            "| recon | no-payload | unresolved | blocked |\n"
            "| forge | no-payload | blocked | unresolved |\n"
            "| eve | no-payload | blocked | pending |\n"
            "| engineering-runtime | newly authored | original | stdlib-only publication pending ready |\n"
            "| art-runtime | newly authored | original | clean-room stdlib-only publication pending ready |\n"
        )

    def _fixture_owner_profile_payload(self) -> dict:
        return {
            "profiles/owner-agent/README.md": (
                "# Owner Agent (neutral development profile)\n\n"
                "This profile owns only owner-oriented local governance.\n\n"
                "Native `hermes profile install <local-owner-directory>` is only a future clean-host canary command and is not run in this slice.\n"
                "Release blockers remain in place until explicit owner acceptance and publication review.\n"
            ),
            "profiles/owner-agent/SOUL.md": (
                "You are [AGENT_NAME], a neutral owner-operated Hermes helper.\n"
                "You represent [OWNER_OR_COMPANY_NAME] and address them as [OWNER_FORM_OF_ADDRESS].\n"
                "Your character follows [AGENT_INSPIRATION] and [AGENT_INSPIRATION_TRAITS].\n"
                "Communication style is [COMMUNICATION_STYLE]. Optional scope: [OPTIONAL_HELP_AND_PROJECTS].\n\n"
                "Before any consequential choice, explain alternatives and risks first.\n"
                "Require owner approval for production, credentials, payments, account, publication, destructive work, or any external side effect.\n"
                "You must not inherit another identity, profile, state, or authority (no-inherited authority). Preserve owner auth, messaging, memory, and session boundaries.\n"
                "Report installed, connected, verified, and authorized status truthfully and only when substantiated by direct context.\n"
                "Always protect secrets and secret-bearing paths. Never fabricate ownership claims.\n"
                "At handoff, include owner acceptance signals and setup-access revocation status; do not claim unresolved publication authority until explicit owner acceptance.\n"
            ),
            "profiles/owner-agent/config.yaml": (
                "terminal:\n"
                "  home_mode: profile\n"
                "  auto_source_bashrc: false\n"
                "  shell_init_files: []\n"
                "memory:\n"
                "  memory_enabled: false\n"
                "  user_profile_enabled: false\n"
                "skills:\n"
                "  write_approval: true\n"
            ),
            "profiles/owner-agent/distribution.yaml": (
                "name: owner-agent\n"
                "version: 0.1.0-dev\n"
                "description: Neutral owner payload for this slice\n"
                "distribution_owned:\n"
                "  - README.md\n"
                "  - SOUL.md\n"
                "  - config.yaml\n"
                "  - distribution.yaml\n"
                "  - skills\n"
                ),
            "profiles/owner-agent/skills/client-agent-operations/SKILL.md": (
                "---\n"
                "name: client-agent-operations\n"
                "description: Use when coordinating owner-directed client operations safely.\n"
                "version: 0.1.0-dev\n"
                "author: Hermes Agent Team\n"
                "license: Pending owner decision\n"
                "---\n"
                "Use when an owner requires safe operational guidance and routing.\n\n"
                "Status truth is preferred before escalation.\n"
                "Authority boundaries must remain explicit and honored.\n"
                "Specialist routing follows owner preference and local policy.\n"
                "Privacy and authentication guidance are minimal and non-disclosing.\n"
                "Keep durable knowledge in summaries for owner handoff.\n"
                "Include setup-access revocation and access handoff expectations.\n"
            ),
        }

    def make_release_payload(self, *, root: Path, components=None):
        if components is None:
            components = {
                "owner-agent": "profiles/owner-agent",
                "art": "profiles/art",
                "recon": "profiles/recon",
                "forge": "profiles/forge",
                "eve": "profiles/eve",
                "engineering-runtime": "runtimes/engineering-runtime",
                "art-runtime": "runtimes/art-runtime",
            }
        payload = {
            "schema_version": "1.0.0",
            "release_status": "development",
            "components": [
                {
                    "name": name,
                    "path": relpath,
                    "version": "0.1.0-dev" if name in {"engineering-runtime", "art-runtime"} else "0.0.0-dev",
                    "status": "ready" if name in {"engineering-runtime", "art-runtime"} else "development",
                }
                for name, relpath in components.items()
            ],
            "compatibility": {
                "hermes_requirement": "unresolved",
            },
            "publication": {
                "status": "blocked",
                "blockers": [
                    "license",
                    "provenance",
                    "native_installation",
                    "clean_host_canaries",
                    "independent_review",
                ],
            },
            "blockers": {
                "license": "pending",
                "provenance": "pending",
                "native_installation": "blocked",
                "clean_host_canaries": "not_run",
                "independent_review": "pending",
            },
        }
        self.write_json(root, payload)

    def make_valid_root(self, root: Path, *, extras=None):
        if extras is None:
            extras = {}
        root.mkdir(parents=True, exist_ok=True)
        allowed_paths = [
            "README.md",
            "SECURITY.md",
            "THIRD_PARTY_NOTICES.md",
            "release-index.yaml",
            "PROVENANCE.md",
            "profiles/owner-agent/README.md",
            "profiles/art/README.md",
            "profiles/recon/README.md",
            "profiles/forge/README.md",
            "profiles/eve/README.md",
            "runtimes/engineering-runtime/README.md",
            "runtimes/engineering-runtime/runtime.yaml",
            "runtimes/engineering-runtime/src/engineering_runtime/__init__.py",
            "runtimes/engineering-runtime/src/engineering_runtime/runtime.py",
            "runtimes/art-runtime/README.md",
            "runtimes/art-runtime/runtime.yaml",
            "runtimes/art-runtime/src/art_runtime/__init__.py",
            "runtimes/art-runtime/src/art_runtime/runtime.py",
            "scripts/verify_release.py",
            "tests/__init__.py",
            "tests/release/__init__.py",
            "tests/release/test_release_gates.py",
        ]
        for rel in allowed_paths:
            path = root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            if rel in {"runtimes/engineering-runtime/README.md", "runtimes/art-runtime/README.md"}:
                path.write_text(f"# {rel}\n\n")
                continue
            if rel == "runtimes/engineering-runtime/runtime.yaml":
                path.write_text(
                    "name: engineering-runtime\n"
                    "version: 0.1.0-dev\n"
                    "description: Core engineering-runtime scaffold for Slice 4B runtime contracts.\n"
                    "python_requires: >=3.11\n"
                    "dependencies: []\n"
                    "stdlib_only: true\n"
                    "owned_files:\n"
                    "  - README.md\n"
                    "  - runtime.yaml\n"
                    "  - src/engineering_runtime/__init__.py\n"
                    "  - src/engineering_runtime/runtime.py\n"
                    "publication_authority: none\n"
                )
                continue
            if rel == "runtimes/art-runtime/runtime.yaml":
                path.write_text(
                    "name: art-runtime\n"
                    "version: 0.1.0-dev\n"
                    "description: Pure-stdlib validator runtime for Art candidate job and manifest contracts.\n"
                    "python_requires: >=3.11\n"
                    "dependencies: []\n"
                    "stdlib_only: true\n"
                    "owned_files:\n"
                    "  - README.md\n"
                    "  - runtime.yaml\n"
                    "  - src/art_runtime/__init__.py\n"
                    "  - src/art_runtime/runtime.py\n"
                    "publication_authority: none\n"
                )
                continue
            if rel == "runtimes/art-runtime/src/art_runtime/__init__.py":
                path.write_text(
                    "from .runtime import artify\n\n"
                    "__all__ = [" + '"artify"' + "]\n"
                )
                continue
            if rel == "runtimes/art-runtime/src/art_runtime/runtime.py":
                path.write_text(
                    "from __future__ import annotations\n"
                    "import copy\n"
                    "import json\n"
                    "import math\n"
                    "import re\n"
                    "from pathlib import Path\n"
                    "from typing import Any\n"
                    "from collections import deque\n"
                    "\n"
                    "def artify(payload: Any) -> Any:\n"
                    "    return copy.deepcopy(payload)\n"
                    "\n"
                    "def is_clean(value: int) -> bool:\n"
                    "    return isinstance(value, int) and not math.isnan(value) if isinstance(value, float) else True\n"
                    "\n"
                    "def contains_clean_room(path: Path) -> bool:\n"
                    "    text = path.read_text(encoding=\"utf-8\")\n"
                    "    return bool(re.search(r\"clean-room\", text))\n"
                )
                continue
            if path.name.endswith(".py"):
                path.write_text("# pytest stub for copy\n")
            elif rel in {"README.md", "SECURITY.md", "THIRD_PARTY_NOTICES.md"}:
                path.write_text(f"# {rel}\n\n")
            elif rel == "PROVENANCE.md":
                path.write_text(self._fixture_provenance_markdown())
            elif rel.startswith("profiles/"):
                if rel.startswith("profiles/owner-agent/"):
                    fixture_payloads = self._fixture_owner_profile_payload()
                    if rel in fixture_payloads:
                        path.write_text(fixture_payloads[rel])
                    elif rel == "profiles/owner-agent/README.md":
                        self.make_component_readme(root, rel)
                    else:
                        path.parent.mkdir(parents=True, exist_ok=True)
                        path.write_text("# owner placeholder\n")
                else:
                    self.make_component_readme(root, rel)
            elif rel == "scripts/verify_release.py":
                path.write_text("# placeholder verifier\n")

        owner_payload_root = root / "profiles" / "owner-agent"
        for file_path, content in self._fixture_owner_profile_payload().items():
            if file_path.startswith("profiles/owner-agent"):
                path = root / file_path
                if path.is_dir():
                    path.mkdir(parents=True, exist_ok=True)
                else:
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text(content)
        owner_skill = root / "profiles" / "owner-agent" / "skills" / "client-agent-operations" / "SKILL.md"
        owner_skill.parent.mkdir(parents=True, exist_ok=True)
        owner_skill.write_text(self._fixture_owner_profile_payload()[
            "profiles/owner-agent/skills/client-agent-operations/SKILL.md"
        ])

        owner_readme = owner_payload_root / "README.md"
        if owner_readme.is_file():
            owner_readme.write_text(self._fixture_owner_profile_payload()["profiles/owner-agent/README.md"])

        if (root / "PROVENANCE.md").is_file():
            pass

        for line in extras.get("extra_files", []):
            extra_path = root / line
            extra_path.parent.mkdir(parents=True, exist_ok=True)
            extra_path.write_text("placeholder")

        self.make_release_payload(root=root)
        return root

    def make_realistic_slice1_fixture(self, root: Path):
        source_root = SCRIPT.parents[1]

        root = root / "slice1"
        root.mkdir(parents=True, exist_ok=True)

        shutil.copytree(source_root / "profiles", root / "profiles")
        shutil.copytree(source_root / "runtimes", root / "runtimes")
        shutil.copytree(source_root / "scripts", root / "scripts")
        shutil.copytree(source_root / "tests", root / "tests")

        # Avoid repository-local generated noise from affecting this fixture.
        for noisy_path in [
            root / "scripts" / "__pycache__",
            root / "tests" / "__pycache__",
            root / "tests" / "release" / "__pycache__",
            root / "tests" / "release" / ".pytest_cache",
        ]:
            if noisy_path.exists():
                shutil.rmtree(noisy_path)

        for pyc in root.rglob("*.pyc"):
            pyc.unlink()

        for filename in [
            "README.md",
            "SECURITY.md",
            "THIRD_PARTY_NOTICES.md",
            "release-index.yaml",
            "PROVENANCE.md",
        ]:
            shutil.copy2(source_root / filename, root / filename)

        return root

    def generate_fragmented_term(self, *parts):
        return "".join(parts)

    def make_deny_file(self, content: str) -> Path:
        fd, path = tempfile.mkstemp(prefix="hermes-deny-", text=True)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(content)
        return Path(path)

    def test_01_valid_slice1_structure_reports_not_ready(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.make_valid_root(root)
            proc = self.run_verify(root)
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            data = json.loads(proc.stdout)
            self.assertTrue(data["ok"])
            self.assertFalse(data["release_ready"])
            self.assertTrue(any(err["code"] == "publication_blocked" for err in data["warnings"]))
            self.assertSetEqual(
                set(data["components"]),
                {
                    "owner-agent",
                    "art",
                    "art-runtime",
                    "engineering-runtime",
                    "eve",
                    "forge",
                    "recon",
                },
            )

    def test_02_require_ready_fails_when_publication_blocked(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.make_valid_root(root)
            proc = self.run_verify(root, ["--require-ready"])
            self.assertNotEqual(proc.returncode, 0)
            data = json.loads(proc.stdout)
            self.assertFalse(data["release_ready"])
            self.assertTrue(any(err["code"] == "publication_blocked" for err in data["warnings"]))

    def test_03_reject_wrong_engineering_runtime_version(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.make_valid_root(root)
            self.mutation_with_release_payload(
                root,
                lambda payload: self.set_release_component(payload, "engineering-runtime", "version", "9.9.9"),
            )
            proc = self.run_verify(root)
            self.assertNotEqual(proc.returncode, 0)
            out = json.loads(proc.stdout)
            self.assertFalse(out["ok"])
            self.assertTrue(any(err["code"] == "component_version_mismatch" for err in out["errors"]))

    def test_04_reject_wrong_engineering_runtime_status(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.make_valid_root(root)
            self.mutation_with_release_payload(
                root,
                lambda payload: self.set_release_component(
                    payload,
                    "engineering-runtime",
                    "status",
                    "development",
                ),
            )
            proc = self.run_verify(root)
            self.assertNotEqual(proc.returncode, 0)
            out = json.loads(proc.stdout)
            self.assertFalse(out["ok"])
            self.assertTrue(any(err["code"] == "component_status_mismatch" for err in out["errors"]))

    def test_05_reject_wrong_art_runtime_version(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.make_valid_root(root)
            self.mutation_with_release_payload(
                root,
                lambda payload: self.set_release_component(
                    payload,
                    "art-runtime",
                    "version",
                    "9.9.9",
                ),
            )
            proc = self.run_verify(root)
            self.assertNotEqual(proc.returncode, 0)
            out = json.loads(proc.stdout)
            self.assertFalse(out["ok"])
            self.assertTrue(any(err["code"] == "component_version_mismatch" for err in out["errors"]))

    def test_06_reject_wrong_art_runtime_status(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.make_valid_root(root)
            self.mutation_with_release_payload(
                root,
                lambda payload: self.set_release_component(payload, "art-runtime", "status", "development"),
            )
            proc = self.run_verify(root)
            self.assertNotEqual(proc.returncode, 0)
            out = json.loads(proc.stdout)
            self.assertFalse(out["ok"])
            self.assertTrue(any(err["code"] == "component_status_mismatch" for err in out["errors"]))

    def test_07_reject_wrong_art_runtime_path(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.make_valid_root(root)
            self.mutation_with_release_payload(
                root,
                lambda payload: self.set_release_component(
                    payload,
                    "art-runtime",
                    "path",
                    "runtimes/art-runtime-bad",
                ),
            )
            proc = self.run_verify(root)
            self.assertNotEqual(proc.returncode, 0)
            out = json.loads(proc.stdout)
            self.assertFalse(out["ok"])
            self.assertTrue(
                any(
                    err["code"] in {"component_path_invalid", "component_path_not_found"}
                    for err in out["errors"]
                )
            )

    def test_08_reject_publication_ready_with_unresolved_blockers_and_blocking_state(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.make_valid_root(root)
            self.mutation_with_release_payload(
                root,
                lambda payload: payload["publication"].update(
                    {
                        "status": "ready",
                        "blockers": {
                            "license": "pending",
                            "provenance": "blocked",
                        },
                    }
                ),
            )
            proc = self.run_verify(root)
            self.assertNotEqual(proc.returncode, 0)
            out = json.loads(proc.stdout)
            self.assertFalse(out["ok"])
            self.assertFalse(out["release_ready"])
            self.assertTrue(
                any(err["code"] == "publication_ready_blocker_state" for err in out["errors"])
            )
            self.assertTrue(any(err["code"] == "compatibility_not_ready" for err in out["errors"]))

    def test_09_reject_publication_ready_with_blocker_list(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.make_valid_root(root)
            self.mutation_with_release_payload(
                root,
                lambda payload: payload["publication"].update(
                    {
                        "status": "ready",
                        "blockers": ["license", "provenance"],
                    }
                ),
            )
            proc = self.run_verify(root)
            self.assertNotEqual(proc.returncode, 0)
            out = json.loads(proc.stdout)
            self.assertFalse(out["ok"])
            self.assertFalse(out["release_ready"])
            self.assertTrue(
                any(err["code"] == "publication_ready_blocker_present" for err in out["errors"])
            )

    def test_10_reject_premature_publication_ready_for_non_ready_components(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.make_valid_root(root)
            self.mutation_with_release_payload(
                root,
                lambda payload: payload["publication"].update(
                    {
                        "status": "ready",
                        "blockers": {},
                    }
                ),
            )
            proc = self.run_verify(root)
            self.assertNotEqual(proc.returncode, 0)
            out = json.loads(proc.stdout)
            self.assertFalse(out["ok"])
            self.assertFalse(out["release_ready"])
            self.assertTrue(any(err["code"] == "component_not_ready" for err in out["errors"]))

    def test_10b_reject_stale_art_runtime_payload_blocker(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.make_valid_root(root)
            self.mutation_with_release_payload(
                root,
                lambda payload: payload.setdefault("blockers", {}).update(
                    {
                        "art_runtime_payload": "pending",
                    },
                ),
            )
            self.mutation_with_release_payload(
                root,
                lambda payload: payload.setdefault("publication", {}).setdefault("blockers", []).append(
                    "art_runtime_payload"
                ),
            )
            proc = self.run_verify(root)
            self.assertNotEqual(proc.returncode, 0)
            out = json.loads(proc.stdout)
            self.assertFalse(out["ok"])
            self.assertTrue(
                any(err["code"] == "publication_blocker_obsolete" for err in out["errors"])
            )

    def test_11_reject_engineering_runtime_manifest_with_extra_key(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.make_valid_root(root)
            self.mutate_runtime_manifest(root, {"extra_debug": True})
            proc = self.run_verify(root)
            self.assertNotEqual(proc.returncode, 0)
            out = json.loads(proc.stdout)
            self.assertFalse(out["ok"])
            self.assertTrue(any(err["code"] == "provenance_row_policy" for err in out["errors"]))

    def test_12_reject_engineering_runtime_manifest_dependency_mutation(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.make_valid_root(root)
            self.mutate_runtime_manifest(root, {"dependencies": ["requests"]})
            proc = self.run_verify(root)
            self.assertNotEqual(proc.returncode, 0)
            out = json.loads(proc.stdout)
            self.assertFalse(out["ok"])
            self.assertTrue(any(err["code"] == "provenance_row_policy" for err in out["errors"]))

    def test_13_reject_engineering_runtime_manifest_version_mutation(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.make_valid_root(root)
            self.mutate_runtime_manifest(root, {"version": "9.9.9"})
            proc = self.run_verify(root)
            self.assertNotEqual(proc.returncode, 0)
            out = json.loads(proc.stdout)
            self.assertFalse(out["ok"])
            self.assertTrue(any(err["code"] == "provenance_row_policy" for err in out["errors"]))

    def test_14_reject_engineering_runtime_manifest_owned_file_mutation(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.make_valid_root(root)
            self.mutate_runtime_manifest(root, {"owned_files": ["README.md", "runtime.yaml"]})
            proc = self.run_verify(root)
            self.assertNotEqual(proc.returncode, 0)
            out = json.loads(proc.stdout)
            self.assertFalse(out["ok"])
            self.assertTrue(any(err["code"] == "provenance_row_policy" for err in out["errors"]))

    def test_14b_reject_art_runtime_manifest_with_extra_key(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.make_valid_root(root)
            self.mutate_runtime_manifest(root, {"extra_debug": True}, component="art-runtime")
            proc = self.run_verify(root)
            self.assertNotEqual(proc.returncode, 0)
            out = json.loads(proc.stdout)
            self.assertFalse(out["ok"])
            self.assertTrue(any(err["code"] == "runtime_manifest_key_mismatch" for err in out["errors"]))

    def test_14c_reject_art_runtime_manifest_wrong_payload_file_list(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.make_valid_root(root)
            self.mutate_runtime_manifest(
                root,
                {"owned_files": ["README.md", "runtime.yaml", "src/art_runtime/__init__.py"]},
                component="art-runtime",
            )
            proc = self.run_verify(root)
            self.assertNotEqual(proc.returncode, 0)
            out = json.loads(proc.stdout)
            self.assertFalse(out["ok"])
            self.assertTrue(any(err["code"] == "runtime_manifest_value_mismatch" for err in out["errors"]))

    def test_14d_reject_art_runtime_missing_payload_file(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.make_valid_root(root)
            (root / "runtimes/art-runtime/src/art_runtime/runtime.py").unlink()
            proc = self.run_verify(root)
            self.assertNotEqual(proc.returncode, 0)
            out = json.loads(proc.stdout)
            self.assertFalse(out["ok"])
            self.assertTrue(any(err["code"] == "runtime_payload_missing_file" for err in out["errors"]))

    def test_14e_reject_art_runtime_unowned_payload_file(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.make_valid_root(root)
            (root / "runtimes/art-runtime/unowned.py").write_text("print(1)\n")
            proc = self.run_verify(root)
            self.assertNotEqual(proc.returncode, 0)
            out = json.loads(proc.stdout)
            self.assertFalse(out["ok"])
            self.assertTrue(any(err["code"] == "runtime_payload_unowned_file" for err in out["errors"]))

    def test_14f_reject_art_runtime_hidden_payload_path(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.make_valid_root(root)
            (root / "runtimes/art-runtime/.hidden").write_text("payload")
            proc = self.run_verify(root)
            self.assertNotEqual(proc.returncode, 0)
            out = json.loads(proc.stdout)
            self.assertFalse(out["ok"])
            self.assertTrue(any(err["code"] == "runtime_payload_hidden_path" for err in out["errors"]))

    def test_14g_reject_art_runtime_source_syntax_error(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.make_valid_root(root)
            runtime_py = root / "runtimes/art-runtime/src/art_runtime/runtime.py"
            runtime_py.write_text("if True\n")
            proc = self.run_verify(root)
            self.assertNotEqual(proc.returncode, 0)
            out = json.loads(proc.stdout)
            self.assertFalse(out["ok"])
            self.assertTrue(any(err["code"] == "runtime_source_syntax_error" for err in out["errors"]))

    def test_14h_reject_art_runtime_disallowed_import_or_call(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.make_valid_root(root)
            runtime_py = root / "runtimes/art-runtime/src/art_runtime/runtime.py"
            runtime_py.write_text(
                "from __future__ import annotations\n"
                "import os\n\n"
                "def artify(payload):\n"
                "    return eval(str(payload))\n"
            )
            proc = self.run_verify(root)
            self.assertNotEqual(proc.returncode, 0)
            out = json.loads(proc.stdout)
            self.assertFalse(out["ok"])
            self.assertTrue(
                any(
                    err["code"] in {"runtime_source_import_violation", "runtime_source_call_violation"}
                    for err in out["errors"]
                )
            )

    def test_15_malformed_index_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            root.mkdir(parents=True, exist_ok=True)
            (root / "release-index.yaml").write_text('{"schema_version":')
            proc = self.run_verify(root)
            self.assertNotEqual(proc.returncode, 0)
            data = json.loads(proc.stdout)
            self.assertFalse(data["ok"])
            self.assertTrue(any(err["code"] == "invalid_index" for err in data["errors"]))

    def test_04_duplicate_unknown_and_missing_components(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.make_valid_root(root)
            data = json.loads((root / "release-index.yaml").read_text())
            data["components"][0]["name"] = "owner-agent"
            data["components"][1]["name"] = "owner-agent"
            (root / "release-index.yaml").write_text(json.dumps(data) + "\n")
            proc = self.run_verify(root)
            self.assertNotEqual(proc.returncode, 0)
            duplicate = json.loads(proc.stdout)
            self.assertFalse(duplicate["ok"])
            self.assertTrue(any(err["code"] == "duplicate_component" for err in duplicate["errors"]))

            data = json.loads((root / "release-index.yaml").read_text())
            data["components"].pop()
            data["components"][0]["name"] = "wrong-name"
            (root / "release-index.yaml").write_text(json.dumps(data) + "\n")
            proc = self.run_verify(root)
            self.assertNotEqual(proc.returncode, 0)
            changed = json.loads(proc.stdout)
            self.assertFalse(changed["ok"])
            self.assertTrue(
                any(err["code"] == "component_count" for err in changed["errors"])
                or any(err["code"] == "component_name" for err in changed["errors"])
                or any(err["code"] == "unknown_component" for err in changed["errors"])
            )

    def test_05_absolute_or_traversal_component_path_fails(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.make_valid_root(root)
            data = json.loads((root / "release-index.yaml").read_text())
            data["components"][0]["path"] = "/tmp/outside"
            (root / "release-index.yaml").write_text(json.dumps(data) + "\n")
            proc = self.run_verify(root)
            self.assertNotEqual(proc.returncode, 0)
            out = json.loads(proc.stdout)
            self.assertTrue(any(err["code"] == "component_path_invalid" for err in out["errors"]))

            data = json.loads((root / "release-index.yaml").read_text())
            data["components"][0]["path"] = "../outside"
            data["components"][0]["name"] = "owner-agent"
            (root / "release-index.yaml").write_text(json.dumps(data) + "\n")
            proc = self.run_verify(root)
            self.assertNotEqual(proc.returncode, 0)
            out = json.loads(proc.stdout)
            self.assertTrue(any(err["code"] == "component_path_invalid" for err in out["errors"]))

    def test_06_rejects_symlinks(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.make_valid_root(root)
            target = root / "profiles" / "owner-agent" / "real.txt"
            target.write_text("link target")
            os.symlink(target, root / "profiles" / "owner-agent" / "bad_link.txt")
            proc = self.run_verify(root)
            self.assertNotEqual(proc.returncode, 0)
            out = json.loads(proc.stdout)
            self.assertTrue(any(err["code"] == "symlink_found" for err in out["errors"]))

    def test_07_rejects_hardlinks(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.make_valid_root(root)
            src = root / "profiles" / "owner-agent" / "dup_source.txt"
            src.write_text("x")
            os.link(src, root / "profiles" / "owner-agent" / "dup_link.txt")
            proc = self.run_verify(root)
            self.assertNotEqual(proc.returncode, 0)
            out = json.loads(proc.stdout)
            self.assertTrue(any(err["code"] == "hardlink_found" for err in out["errors"]))

    def test_08_rejects_forbidden_private_filenames(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.make_valid_root(root)
            forbidden = root / "profiles" / "owner-agent" / ".env"
            forbidden.write_text("SECRET=1")
            proc = self.run_verify(root)
            self.assertNotEqual(proc.returncode, 0)
            out = json.loads(proc.stdout)
            self.assertTrue(any(err["code"] in {"forbidden_filename", "forbidden_path"} for err in out["errors"]))

    def test_09_deny_term_detection_without_disclosure(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.make_valid_root(root)
            (root / "profiles" / "owner-agent" / "README.md").write_text(
                "This repository contains TOP_SECRET_KEY material.\n"
            )
            deny = self.make_deny_file("TOP_SECRET_KEY\n")
            try:
                proc = self.run_verify(root, ["--deny-term-file", str(deny)])
            finally:
                deny.unlink(missing_ok=True)
            self.assertNotEqual(proc.returncode, 0)
            self.assertNotIn("TOP_SECRET_KEY", proc.stdout)
            out = json.loads(proc.stdout)
            self.assertTrue(any(err["code"] == "deny_term" for err in out["errors"]))

    def test_10_secret_pattern_detection_without_disclosure(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.make_valid_root(root)
            secret_file = root / "profiles" / "recon" / "README.md"
            secret_key_prefix = self.generate_fragmented_term("ap", "i") + self.generate_fragmented_term("_", "k") + "ey"
            secret_token = self.generate_fragmented_term(
                "A",
                "K",
                "I",
                "A",
                "_",
                "TEST",
                "_",
                "SECRET",
                "_",
                "TOKEN",
            )
            secret_file.write_text(f"{secret_key_prefix}={secret_token}\n")
            proc = self.run_verify(root)
            self.assertNotEqual(proc.returncode, 0)
            self.assertNotIn(secret_token, proc.stdout)
            out = json.loads(proc.stdout)
            self.assertTrue(any("secret" in err["code"] for err in out["errors"]))

    def test_11_dedicated_secret_detectors_match_standalone_aws_and_github_tokens(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.make_valid_root(root)
            aws_token = self.generate_fragmented_term(
                "AKIA",
                "ABCD",
                "EFGH",
                "IJKL",
                "MNOP",
            )
            github_token = self.generate_fragmented_term(
                "ghp_",
                "ABCD",
                "EFGH",
                "IJKL",
                "MNOP",
                "QRST",
                "UVWX",
                "YZ01",
                "2345",
                "6789",
            )
            (root / "profiles" / "recon" / "README.md").write_text(
                f"{aws_token}\n{github_token}\n"
            )
            proc = self.run_verify(root)
            self.assertNotEqual(proc.returncode, 0)
            self.assertNotIn(aws_token, proc.stdout)
            self.assertNotIn(github_token, proc.stdout)
            out = json.loads(proc.stdout)
            codes = [err["code"] for err in out["errors"]]
            self.assertIn("secret_aws_access_key", codes)
            self.assertIn("secret_github_pat", codes)

    def test_12_dedicated_secret_detectors_do_not_match_near_miss_tokens(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.make_valid_root(root)
            aws_wrong_prefix = self.generate_fragmented_term("akia", "A" * 16)
            aws_wrong_length = self.generate_fragmented_term("AKIA", "A" * 15)
            aws_with_disallowed_char = self.generate_fragmented_term("AKIA", "ABCD", "EFGH", "IJKL", "MN-OP")
            github_wrong_length = self.generate_fragmented_term("ghp_", "A" * 35)
            github_wrong_prefix = self.generate_fragmented_term("ghq_", "A" * 36)

            (root / "profiles" / "recon" / "README.md").write_text(
                "\\n".join(
                    [
                        aws_wrong_prefix,
                        aws_wrong_length,
                        aws_with_disallowed_char,
                        github_wrong_length,
                        github_wrong_prefix,
                    ]
                )
                + "\n"
            )

            proc = self.run_verify(root)
            self.assertEqual(proc.returncode, 0)
            out = json.loads(proc.stdout)
            codes = [err["code"] for err in out["errors"]]
            self.assertNotIn("secret_aws_access_key", codes)
            self.assertNotIn("secret_github_pat", codes)
            self.assertNotIn(aws_wrong_prefix, proc.stdout)
            self.assertNotIn(aws_wrong_length, proc.stdout)
            self.assertNotIn(aws_with_disallowed_char, proc.stdout)
            self.assertNotIn(github_wrong_length, proc.stdout)
            self.assertNotIn(github_wrong_prefix, proc.stdout)

    def test_13_deny_term_input_failures(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.make_valid_root(root)
            missing = Path(tempfile.mktemp(prefix="hermes-deny-missing-"))
            proc = self.run_verify(root, ["--deny-term-file", str(missing)])
            self.assertNotEqual(proc.returncode, 0)
            self.assertTrue(
                any(err["code"] == "deny_term_file_invalid" for err in json.loads(proc.stdout)["errors"])
            )

            empty = Path(tempfile.mktemp(prefix="hermes-deny-empty-"))
            empty.write_text("")
            proc = self.run_verify(root, ["--deny-term-file", str(empty)])
            empty.unlink(missing_ok=True)
            self.assertNotEqual(proc.returncode, 0)
            self.assertTrue(any(err["code"] == "deny_term_file_empty" for err in json.loads(proc.stdout)["errors"]))

    def test_14_deterministic_output_ordering(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.make_valid_root(root)
            (root / "profiles" / "recon" / "README.md").write_text("TOPSECRET token=ALPHA\n")
            deny = self.make_deny_file("TOPSECRET\n")
            try:
                proc1 = self.run_verify(root, ["--deny-term-file", str(deny)])
                proc2 = self.run_verify(root, ["--deny-term-file", str(deny)])
            finally:
                deny.unlink(missing_ok=True)
            self.assertEqual(proc1.returncode, proc2.returncode)
            self.assertEqual(json.loads(proc1.stdout), json.loads(proc2.stdout))

    def test_13_no_repository_private_path_leak_in_source(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.make_valid_root(root)
            deny = self.make_deny_file(self.generate_fragmented_term("/", "home", "/", "synthetic", "-", "owner", "/") + "\n")
            try:
                proc = self.run_verify(root, ["--deny-term-file", str(deny)])
            finally:
                deny.unlink(missing_ok=True)
            self.assertEqual(proc.returncode, 0)
            self.assertNotIn("/home", proc.stdout)
            self.assertTrue(json.loads(proc.stdout)["ok"])

    def test_14_warning_deduplication_is_exact_and_unique(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.make_valid_root(root)
            proc = self.run_verify(root)
            self.assertEqual(proc.returncode, 0)
            data = json.loads(proc.stdout)
            warnings = data["warnings"]
            self.assertEqual(len(warnings), len({
                (
                    item.get("code"),
                    item.get("message"),
                    item.get("path"),
                    item.get("line"),
                    json.dumps(item.get("details", {}), sort_keys=True),
                )
                for item in warnings
            }))
            self.assertEqual(len([w for w in warnings if w["code"] == "publication_blocked"]), 1)
            blocker_entries = [w for w in warnings if w["code"] == "publication_blocker"]
            self.assertEqual(len(blocker_entries), 5)
            self.assertSetEqual(
                set(item.get("blocker") for item in blocker_entries),
                {
                    "license",
                    "provenance",
                    "native_installation",
                    "clean_host_canaries",
                    "independent_review",
                },
            )

    def test_15_verifier_fixture_runs_clean_with_real_sources(self):
        with tempfile.TemporaryDirectory() as td:
            source_root = self.make_realistic_slice1_fixture(Path(td))
            proc = self.run_verify(source_root)
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            data = json.loads(proc.stdout)
            self.assertTrue(data["ok"])
            self.assertFalse(data["release_ready"])
            self.assertFalse(any(err["code"].startswith("secret_") for err in data["errors"]))

    def test_15a_compatibility_receipts_must_be_provided_as_pairs(self):
        with tempfile.TemporaryDirectory() as td:
            root = self.make_realistic_slice1_fixture(Path(td))
            head = self.candidate_head(root)
            host_payload = self.make_receipt_payload(mode="host", candidate_head=head)
            receipt_dir = Path(td) / "receipts"
            host_payload_path, _ = self.write_compatibility_receipts(
                root,
                directory=receipt_dir,
                host_payload=host_payload,
                docker_payload=None,
            )

            proc = self.run_verify(root, args=["--host-receipt", str(host_payload_path)])
            self.assertNotEqual(proc.returncode, 0)
            out = json.loads(proc.stdout)
            self.assertTrue(any(err["code"] == "receipt_arg_mismatch" for err in out["errors"]))

    def test_15b_compatibility_receipt_special_or_symlink_paths_are_invalid(self):
        with tempfile.TemporaryDirectory() as td:
            root = self.make_realistic_slice1_fixture(Path(td))
            head = self.candidate_head(root)
            host_payload = self.make_receipt_payload(mode="host", candidate_head=head)
            docker_payload = self.make_receipt_payload(mode="docker", candidate_head=head)
            docker_payload["flags"]["host_receipt_mode"] = "host"
            docker_payload["flags"]["host_receipt_status"] = "passed"
            docker_payload["flags"]["image_id"] = "sha256:" + "d" * 64
            docker_payload["flags"]["host_receipt_claims"] = host_payload["claims"]
            docker_payload["flags"]["host_archive_hashes"] = self.receipt_archive_records()
            receipt_dir = Path(td) / "receipts"
            host_payload_path, docker_payload_path = self.write_compatibility_receipts(
                root,
                directory=receipt_dir,
                host_payload=host_payload,
                docker_payload=docker_payload,
            )

            if host_payload_path is None:
                self.fail("host compatibility receipt path missing")
            if docker_payload_path is None:
                self.fail("docker compatibility receipt path missing")

            host_payload_path.unlink()
            os.symlink(str(root / "release-index.yaml"), str(host_payload_path))

            proc = self.run_verify(root, args=["--host-receipt", str(host_payload_path), "--docker-receipt", str(docker_payload_path)])
            self.assertNotEqual(proc.returncode, 0)
            out = json.loads(proc.stdout)
            self.assertTrue(any(err["code"] == "compatibility_receipt_invalid_path" for err in out["errors"]))

    def test_15c_compatibility_receipt_invalid_mode_version_head_hash_image(self):
        with tempfile.TemporaryDirectory() as td:
            root = self.make_realistic_slice1_fixture(Path(td))
            head = self.candidate_head(root)

            bad_version_host = self.make_receipt_payload(mode="host", candidate_head=head, overrides={"hermes_version": "0.0.0"})
            receipt_dir = Path(td) / "receipts"
            host_payload_path, _ = self.write_compatibility_receipts(
                root,
                directory=receipt_dir,
                host_payload=bad_version_host,
                docker_payload=None,
            )
            proc = self.run_verify(
                root,
                args=["--host-receipt", str(host_payload_path), "--docker-receipt", str(receipt_dir / "does-not-exist.json")],
            )
            self.assertNotEqual(proc.returncode, 0)
            out = json.loads(proc.stdout)
            self.assertTrue(any(err["code"] == "compatibility_receipt_invalid_version" for err in out["errors"]))

            root2 = self.make_realistic_slice1_fixture(Path(td) / "case2")
            head = self.candidate_head(root2)
            host_payload = self.make_receipt_payload(mode="host", candidate_head=head)
            docker_payload = self.make_receipt_payload(mode="docker", candidate_head="f" * 40)
            docker_payload["flags"]["host_receipt_mode"] = "host"
            docker_payload["flags"]["host_receipt_status"] = "passed"
            docker_payload["flags"]["host_receipt_claims"] = host_payload["claims"]
            docker_payload["flags"]["host_archive_hashes"] = self.receipt_archive_records()
            receipt_dir2 = Path(td) / "receipts2"
            host_payload_path, docker_payload_path = self.write_compatibility_receipts(
                root2,
                directory=receipt_dir2,
                host_payload=host_payload,
                docker_payload=docker_payload,
            )
            if host_payload_path is None:
                self.fail("host compatibility receipt path missing")
            if docker_payload_path is None:
                self.fail("docker compatibility receipt path missing")

            # force three independent compatibility failure modes to hit the strict validator
            docker_payload_path.write_text(
                json.dumps(
                    {
                        **(json.loads(docker_payload_path.read_text(encoding="utf-8"))),
                        "candidate_head": "f" * 40,
                    },
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
            )

            proc = self.run_verify(
                root2,
                args=["--host-receipt", str(host_payload_path), "--docker-receipt", str(docker_payload_path)],
            )
            out = json.loads(proc.stdout)
            self.assertNotEqual(proc.returncode, 0)
            self.assertTrue(any(err["code"] in {"compatibility_receipt_invalid_head", "compatibility_receipt_mismatched_host_hash", "compatibility_receipt_invalid_mode", "compatibility_receipt_invalid_image"} for err in out["errors"]))

    def test_15d_compatibility_receipt_false_or_missing_claim_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = self.make_realistic_slice1_fixture(Path(td))
            head = self.candidate_head(root)
            host_payload = self.make_receipt_payload(mode="host", candidate_head=head)
            host_payload["claims"]["secrets_excluded"] = False
            receipt_dir = Path(td) / "receipts"
            host_payload_path, _ = self.write_compatibility_receipts(
                root,
                directory=receipt_dir,
                host_payload=host_payload,
                docker_payload=None,
            )

            proc = self.run_verify(root, args=["--host-receipt", str(host_payload_path), "--docker-receipt", str(receipt_dir / "missing-docker.json")])
            self.assertNotEqual(proc.returncode, 0)
            out = json.loads(proc.stdout)
            self.assertTrue(any(err["code"] == "compatibility_receipt_invalid_claim" for err in out["errors"]))

    def test_15e_compatibility_receipt_profile_set_must_match_exactly(self):
        with tempfile.TemporaryDirectory() as td:
            root = self.make_realistic_slice1_fixture(Path(td))
            head = self.candidate_head(root)
            host_payload = self.make_receipt_payload(
                mode="host",
                candidate_head=head,
                candidate_profiles=["owner-agent", "art", "recon", "forge", "eve", "extra"],
            )
            receipt_dir = Path(td) / "receipts"
            host_payload_path, _ = self.write_compatibility_receipts(
                root,
                directory=receipt_dir,
                host_payload=host_payload,
                docker_payload=None,
            )

            proc = self.run_verify(root, args=["--host-receipt", str(host_payload_path), "--docker-receipt", str(receipt_dir / "missing-docker.json")])
            self.assertNotEqual(proc.returncode, 0)
            out = json.loads(proc.stdout)
            self.assertTrue(any(err["code"] == "compatibility_receipt_invalid_profile_set" for err in out["errors"]))

    def test_15f_compatibility_receipts_with_valid_host_and_docker_pair(self):
        with tempfile.TemporaryDirectory() as td:
            root = self.make_realistic_slice1_fixture(Path(td))
            head = self.candidate_head(root)
            receipt_dir = Path(td) / "receipts"

            host_payload = self.make_receipt_payload(mode="host", candidate_head=head)
            host_payload_path = self.write_receipt(root, "host-compatibility-receipt.json", host_payload, directory=receipt_dir)
            host_digest = hashlib.sha256(host_payload_path.read_bytes()).hexdigest()

            docker_payload = self.make_receipt_payload(mode="docker", candidate_head=head)
            docker_payload["flags"].update(
                {
                    "host_receipt_mode": "host",
                    "host_receipt_status": "passed",
                    "host_receipt_claims": host_payload["claims"],
                    "host_receipt_sha256": host_digest,
                    "host_archive_hashes": self.receipt_archive_records(),
                    "image_id": "sha256:" + "c" * 64,
                }
            )
            docker_payload_path = self.write_receipt(root, "docker-compatibility-receipt.json", docker_payload, directory=receipt_dir)

            proc = self.run_verify(
                root,
                args=["--host-receipt", str(host_payload_path), "--docker-receipt", str(docker_payload_path)],
            )
            self.assertEqual(proc.returncode, 0)
            out = json.loads(proc.stdout)
            compat_errors = [err["code"] for err in out["errors"] if err["code"].startswith("compatibility_")]
            self.assertFalse(compat_errors)

    def test_15fa_compatibility_receipt_archive_records_must_match_exactly(self):
        with tempfile.TemporaryDirectory() as td:
            root = self.make_realistic_slice1_fixture(Path(td))
            head = self.candidate_head(root)

            host_payload = self.make_receipt_payload(mode="host", candidate_head=head)
            host_payload_path = self.write_receipt(root, "host-compatibility-receipt.json", host_payload, directory=Path(td))
            host_digest = hashlib.sha256(host_payload_path.read_bytes()).hexdigest()

            base_docker_payload = self.make_receipt_payload(mode="docker", candidate_head=head)
            base_docker_payload["flags"].update(
                {
                    "host_receipt_mode": "host",
                    "host_receipt_status": "passed",
                    "host_receipt_claims": host_payload["claims"],
                    "host_receipt_sha256": host_digest,
                    "image_id": "sha256:" + "c" * 64,
                }
            )

            base_records = self.receipt_archive_records()

            def check(mutated_records, expect_code):
                docker_payload = copy.deepcopy(base_docker_payload)
                docker_payload["flags"]["host_archive_hashes"] = mutated_records
                docker_payload_path = self.write_receipt(root, "docker-compatibility-receipt.json", docker_payload, directory=Path(td))

                proc = self.run_verify(
                    root,
                    args=["--host-receipt", str(host_payload_path), "--docker-receipt", str(docker_payload_path)],
                )
                self.assertNotEqual(proc.returncode, 0)
                out = json.loads(proc.stdout)
                self.assertTrue(any(err["code"] == expect_code for err in out["errors"]))

            records = copy.deepcopy(base_records)
            del records["owner-agent"]
            check(records, "compatibility_receipt_mismatched_archive_records")

            records = copy.deepcopy(base_records)
            records["extra"] = copy.deepcopy(records["owner-agent"])
            check(records, "compatibility_receipt_mismatched_archive_records")

            records = copy.deepcopy(base_records)
            records["renamed-profile"] = records.pop("eve")
            check(records, "compatibility_receipt_mismatched_archive_records")

            records = copy.deepcopy(base_records)
            records["owner-agent"]["filename"] = "owner-agent-changed.tar"
            check(records, "compatibility_receipt_mismatched_archive_records")

            records = copy.deepcopy(base_records)
            records["owner-agent"]["sha256"] = "b" * 64
            check(records, "compatibility_receipt_mismatched_archive_records")

            records = copy.deepcopy(base_records)
            records["owner-agent"]["members"] = ["README.md", "extra"]
            records["owner-agent"]["member_count"] = 2
            check(records, "compatibility_receipt_mismatched_archive_records")

            records = copy.deepcopy(base_records)
            records["owner-agent"]["members"] = ["extra", "README.md"]
            records["owner-agent"]["member_count"] = 2
            check(records, "compatibility_receipt_mismatched_archive_records")

            records = copy.deepcopy(base_records)
            records["owner-agent"]["member_count"] = 2
            check(records, "compatibility_receipt_invalid_archive")

            records = copy.deepcopy(base_records)
            del records["owner-agent"]["member_count"]
            check(records, "compatibility_receipt_invalid_archive")

    def test_15g_compatibility_argument_pair_is_required(self):
        with tempfile.TemporaryDirectory() as td:
            root = self.make_realistic_slice1_fixture(Path(td))
            proc = self.run_verify(root, args=["--host-receipt", str(root / "host-only.json")])
            self.assertNotEqual(proc.returncode, 0)
            out = json.loads(proc.stdout)
            self.assertTrue(any(err["code"] == "receipt_arg_mismatch" for err in out["errors"]))

    def test_15h_verify_help_displays_receipt_options(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            proc = self.run_verify(root, args=["--help"])
            self.assertEqual(proc.returncode, 0)
            self.assertIn("--host-receipt", proc.stdout)
            self.assertIn("--docker-receipt", proc.stdout)

    def test_15i_candidate_head_from_linked_worktree(self):
        with tempfile.TemporaryDirectory() as td:
            _, linked_root = self.make_linked_git_receipt_fixture(Path(td))

            self.assertTrue((linked_root / ".git").is_file())

            expected_head = self.git_head_for_root(linked_root)
            observed_head = verifier._candidate_head_for_receipts(linked_root)

            self.assertNotEqual(expected_head, "0" * 40)
            self.assertEqual(observed_head, expected_head)

    def test_15j_candidate_head_for_non_git_fixture_returns_placeholder(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            observed_head = verifier._candidate_head_for_receipts(root)

            self.assertEqual(observed_head, "0" * 40)

    def test_15k_candidate_head_rejects_malformed_output(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)

            with patch(
                "scripts.verify_release.subprocess.run",
                return_value=subprocess.CompletedProcess(
                    args=["git", "--no-replace-objects", "-C", str(root), "rev-parse", "HEAD"],
                    returncode=0,
                    stdout="not-a-valid-sha\n",
                    stderr="",
                ),
            ):
                observed_head = verifier._candidate_head_for_receipts(root)

            self.assertEqual(observed_head, "0" * 40)

    def test_15l_compatibility_receipt_exact_head_mismatch_remains_invalid(self):
        with tempfile.TemporaryDirectory() as td:
            root = self.git_fixture_with_receipts(Path(td) / "slice")
            expected_head = self.git_head_for_root(root)
            self.assertNotEqual(expected_head, "0" * 40)

            host_payload = self.make_receipt_payload(mode="host", candidate_head="f" * 40)
            receipt_dir = Path(td) / "receipts"
            host_payload_path = self.write_receipt(root, "host-compatibility-receipt.json", host_payload, directory=receipt_dir)
            host_digest = hashlib.sha256(host_payload_path.read_bytes()).hexdigest()

            docker_payload = self.make_receipt_payload(mode="docker", candidate_head="f" * 40)
            docker_payload["flags"].update(
                {
                    "host_receipt_mode": "host",
                    "host_receipt_status": "passed",
                    "host_receipt_claims": host_payload["claims"],
                    "host_receipt_sha256": host_digest,
                    "host_archive_hashes": self.receipt_archive_records(),
                    "image_id": "sha256:" + "c" * 64,
                }
            )
            docker_payload_path = self.write_receipt(root, "docker-compatibility-receipt.json", docker_payload, directory=receipt_dir)

            proc = self.run_verify(
                root,
                args=["--host-receipt", str(host_payload_path), "--docker-receipt", str(docker_payload_path)],
            )

            self.assertNotEqual(proc.returncode, 0)
            out = json.loads(proc.stdout)
            self.assertTrue(any(err["code"] == "compatibility_receipt_invalid_head" for err in out["errors"]))

    def test_16_owner_profile_exact_recursive_files(self):
        owner_dir = self.owner_profile_dir()
        self.assertTrue(owner_dir.is_dir())

        collected = []
        for path in owner_dir.rglob("*"):
            rel = path.relative_to(owner_dir).as_posix()
            self.assertFalse(path.is_symlink(), f"symlink payload entry must be rejected: {rel}")

            for part in path.relative_to(owner_dir).parts:
                self.assertFalse(part.startswith("."), f"hidden payload path must be rejected: {rel}")

            if path.is_dir():
                if rel:
                    self.assertIn(
                        rel,
                        {
                            "skills",
                            "skills/client-agent-operations",
                        },
                        f"unexpected profile directory: {rel}",
                    )
                continue

            collected.append(rel)

        expected = [
            "README.md",
            "SOUL.md",
            "config.yaml",
            "distribution.yaml",
            "skills/client-agent-operations/SKILL.md",
        ]
        self.assertListEqual(sorted(collected), expected)

    def _assert_no_absolute_path_values(self, value):
        if isinstance(value, str):
            self.assertFalse(
                value.startswith("/"),
                f"absolute path leaked in config value: {value}",
            )
            return
        if isinstance(value, dict):
            for item in value.values():
                self._assert_no_absolute_path_values(item)
            return
        if isinstance(value, (list, tuple)):
            for item in value:
                self._assert_no_absolute_path_values(item)

    def test_17_owner_read_manifest_contract_fields(self):
        owner_dir = self.owner_profile_dir()
        manifest = read_manifest(owner_dir)
        self.assertIsNotNone(manifest, "distribution.yaml is missing")
        self.assertEqual(manifest.name, "owner-agent")
        self.assertEqual(manifest.version, "0.1.0-dev")
        self.assertEqual(manifest.env_requires, [])
        self.assertEqual(manifest.author, "")
        self.assertEqual(manifest.license, "")
        self.assertEqual(manifest.distribution_owned, [
            "README.md",
            "SOUL.md",
            "config.yaml",
            "distribution.yaml",
            "skills",
        ])

    def test_18_owner_plan_install_accepts_owner_payload(self):
        owner_dir = self.owner_profile_dir()
        with tempfile.TemporaryDirectory() as td:
            try:
                plan = plan_install(source=str(owner_dir), workdir=Path(td) / "work")
            except DistributionError as exc:
                self.fail(f"plan_install should accept owner payload, but failed: {exc}")

        self.assertIsNotNone(plan)

        self.assertEqual(plan.manifest.name, "owner-agent")
        self.assertEqual(plan.manifest.source, str(owner_dir.resolve()))
        self.assertEqual(plan.provenance, str(owner_dir.resolve()))
        self.assertEqual(plan.staged_dir, owner_dir.resolve())
        # Current Hermes install plans expose the staged payload rather than
        # duplicating its directory facts as has_skills/has_cron attributes.
        self.assertTrue((plan.staged_dir / "skills").is_dir())
        self.assertFalse((plan.staged_dir / "cron").exists())

    def test_19_owner_soul_contract_terms(self):
        soul_path = self.owner_profile_dir() / "SOUL.md"
        self.assertTrue(soul_path.is_file())
        soul = soul_path.read_text(encoding="utf-8")
        for field in (
            "OWNER_OR_COMPANY_NAME", "OWNER_FORM_OF_ADDRESS", "AGENT_NAME",
            "AGENT_INSPIRATION", "AGENT_INSPIRATION_TRAITS",
            "COMMUNICATION_STYLE", "OPTIONAL_HELP_AND_PROJECTS",
        ):
            self.assertIn(f"[{field}]", soul)

    def test_20_owner_config_contract_fields(self):
        import yaml

        config_path = self.owner_profile_dir() / "config.yaml"
        self.assertTrue(config_path.is_file())
        with config_path.open(encoding="utf-8") as handle:
            data = yaml.safe_load(handle)

        self.assertIsNotNone(data)
        self.assertIsInstance(data, dict)
        self.assertFalse(data.get("model", None))
        self.assertIn("terminal", data)
        self.assertIn("memory", data)
        self.assertIn("skills", data)

        terminal = data["terminal"]
        self.assertIsInstance(terminal, dict)
        self.assertIn("home_mode", terminal)
        self.assertEqual(terminal["home_mode"], "profile")
        self.assertIn("auto_source_bashrc", terminal)
        self.assertFalse(terminal["auto_source_bashrc"])
        self.assertIn("shell_init_files", terminal)
        self.assertListEqual(terminal["shell_init_files"], [])

        memory = data["memory"]
        self.assertIsInstance(memory, dict)
        self.assertIn("memory_enabled", memory)
        self.assertFalse(memory["memory_enabled"])
        self.assertIn("user_profile_enabled", memory)
        self.assertFalse(memory["user_profile_enabled"])

        skills_cfg = data["skills"]
        self.assertIsInstance(skills_cfg, dict)
        self.assertIn("write_approval", skills_cfg)
        self.assertTrue(skills_cfg["write_approval"])

        self.assertEqual(set(data.keys()), {"terminal", "memory", "skills"})
        self._assert_no_absolute_path_values(data)

    def test_21_owner_skill_frontmatter_contract(self):
        skill_path = self.owner_profile_dir() / "skills" / "client-agent-operations" / "SKILL.md"
        self.assertTrue(skill_path.is_file())
        text = skill_path.read_text(encoding="utf-8")
        self.assertTrue(text.startswith("---\n"))
        close = text.index("---", 3)
        yaml_body = text[3:close].strip()
        self.assertTrue(yaml_body)
        import yaml

        parsed = yaml.safe_load(yaml_body)
        self.assertEqual(parsed.get("name"), "client-agent-operations")
        self.assertIn("client", str(parsed.get("description", "")).lower())
        self.assertIn("owner", str(parsed.get("description", "")).lower())
        self.assertEqual(parsed.get("author"), "Hermes Agent Team")
        self.assertEqual(parsed.get("license"), "Pending owner decision")
        self.assertIn("status truth", text)
        self.assertIn("authority boundaries", text)
        self.assertIn("specialist routing", text)
        self.assertIn("privacy", text)
        self.assertIn("authentication", text)
        self.assertIn("durable knowledge", text)
        self.assertIn("handoff", text)
        self.assertIn("access revocation", text)

        self.assertIn("version", parsed)
        self.assertTrue(parsed["version"])
        self.assertTrue(str(parsed.get("description", "")).startswith("Use when "))

        body = text[close + 3 :].strip()
        self.assertTrue(body)

        self.assertNotIn("TOKEN", text)
        self.assertNotRegex(text, r"[A-Za-z0-9_]{35,}")

        github_term = self.generate_fragmented_term("github", ".", "com")
        home_term = self.generate_fragmented_term("/", "home", "/")
        token_term = self.generate_fragmented_term("TOKEN")
        self.assertNotIn(github_term, text)
        self.assertNotIn(home_term, text)
        self.assertNotIn(token_term, text)

    def test_22_owner_provenance_component_rows(self):
        provenance_path = self.owner_profile_dir().parent.parent / "PROVENANCE.md"
        self.assertTrue(provenance_path.is_file())
        provenance = provenance_path.read_text(encoding="utf-8")
        rows = []
        for line in provenance.splitlines():
            stripped = line.strip()
            if not stripped.startswith("|"):
                continue
            cells = [cell.strip() for cell in stripped.strip("|").split("|")]
            if not cells:
                continue
            first_cell = cells[0].strip().lower()
            if first_cell == "component":
                continue
            if set(first_cell) <= {"-", ":"}:
                continue
            if len(cells) < 2:
                continue
            rows.append(cells)

        required_components = [
            "owner-agent",
            "art",
            "recon",
            "forge",
            "eve",
            "engineering-runtime",
            "art-runtime",
        ]

        self.assertEqual(len(rows), len(required_components))

        row_lookup = {}
        for row in rows:
            name = row[0]
            self.assertNotIn(name, row_lookup, f"duplicate provenance row for component: {name}")
            row_lookup[name] = row

        self.assertEqual(set(row_lookup.keys()), set(required_components))

        owner_row = " ".join(row_lookup["owner-agent"]).lower()
        self.assertIn("newly authored", owner_row)
        self.assertIn("original", owner_row)
        self.assertIn("pending", owner_row)
        self.assertIn("publication", owner_row)

        for component, row in row_lookup.items():
            if component == "owner-agent":
                continue
            if component in {"engineering-runtime", "art-runtime"}:
                text_row = " ".join(row).lower()
                required_terms = {
                    "newly authored",
                    "original",
                    "stdlib-only",
                    "publication pending",
                    "ready",
                }
                if component == "art-runtime":
                    required_terms.add("clean-room")
                for term in required_terms:
                    self.assertIn(term, text_row)
                self.assertNotIn("blocked", text_row)
                self.assertNotIn("unresolved", text_row)
                continue

            text_row = " ".join(row).lower()
            self.assertIn("no-payload", text_row)
            self.assertTrue(
                "blocked" in text_row
                or "pending" in text_row
                or "unresolved" in text_row
            )
            self.assertNotIn("public-ready", text_row)
            self.assertNotIn("publication-authorized", text_row)
            self.assertNotIn("public-license", text_row)

    def test_23_neutral_expected_terms_are_safe_and_generic(self):
        expected_terms = [
            "[AGENT_NAME]",
            "[OWNER_OR_COMPANY_NAME]",
            "[OWNER_FORM_OF_ADDRESS]",
            "[AGENT_INSPIRATION]",
            "[AGENT_INSPIRATION_TRAITS]",
            "[COMMUNICATION_STYLE]",
            "[OPTIONAL_HELP_AND_PROJECTS]",
            "owner-agent",
            "client-agent-operations",
        ]
        for term in expected_terms:
            self.assertIsInstance(term, str)
            self.assertNotEqual(term.strip(), "")
            self.assertFalse(term.startswith("/") and "/" in term)
            self.assertNotIn("github.com", term)
            self.assertNotIn("/home/", term)
            self.assertNotRegex(term, r"[A-Za-z0-9_]{35,}")

    def test_24_owner_payload_missing_provenance_fails(self):
        with tempfile.TemporaryDirectory() as td:
            source_root = self.make_realistic_slice1_fixture(Path(td))
            (source_root / "PROVENANCE.md").unlink()
            proc = self.run_verify(source_root)
            self.assertNotEqual(proc.returncode, 0)
            out = json.loads(proc.stdout)
            self.assertTrue(any(err["code"] == "provenance_missing" for err in out["errors"]))

    def test_25_owner_payload_missing_required_file_fails_contract(self):
        with tempfile.TemporaryDirectory() as td:
            source_root = self.make_realistic_slice1_fixture(Path(td))
            (source_root / "profiles" / "owner-agent" / "SOUL.md").unlink()
            proc = self.run_verify(source_root)
            self.assertNotEqual(proc.returncode, 0)
            out = json.loads(proc.stdout)
            self.assertTrue(
                any(err["code"] == "owner_contract_mismatch" for err in out["errors"])
                or any(err["code"] == "owner_payload_mismatch" for err in out["errors"])
            )

    def test_26_owner_distribution_contract_forbids_author_license_fields(self):
        with tempfile.TemporaryDirectory() as td:
            source_root = self.make_realistic_slice1_fixture(Path(td))
            distribution = source_root / "profiles" / "owner-agent" / "distribution.yaml"
            text = distribution.read_text(encoding="utf-8")
            text += "author: Bad\nlicense: Bad\n"
            distribution.write_text(text)
            proc = self.run_verify(source_root)
            self.assertNotEqual(proc.returncode, 0)
            out = json.loads(proc.stdout)
            self.assertTrue(
                any(err["code"] == "distribution_contract_mismatch" for err in out["errors"])
            )


if __name__ == "__main__":
    unittest.main()
