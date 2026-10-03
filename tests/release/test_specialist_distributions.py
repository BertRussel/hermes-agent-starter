import json
import re
import tempfile
import unittest
from pathlib import Path

from hermes_cli.profile_distribution import DistributionError, plan_install, read_manifest


ROOT = Path(__file__).resolve().parents[2]


SPECIALISTS = {
    "art": {
        "contract": "creative-production-contract",
        "tools": ["file", "terminal", "todo", "vision", "web"],
        "authority": "cannot publish or claim final acceptance",
    },
    "recon": {
        "contract": "research-assurance-contract",
        "tools": ["file", "terminal", "todo", "web", "browser", "vision"],
        "authority": "cannot implement or make final decisions",
    },
    "forge": {
        "contract": "bounded-implementation-contract",
        "tools": ["file", "terminal", "todo"],
        "authority": "cannot approve its own output or act on production",
    },
    "eve": {
        "contract": "independent-review-contract",
        "tools": ["file", "terminal", "todo"],
        "authority": "read-only review and cannot implement or own final decision",
    },
}


class SpecialistDistributionContractsTests(unittest.TestCase):
    def _profile_dir(self, role: str) -> Path:
        return ROOT / "profiles" / role

    def _required_files(self, role: str) -> list[str]:
        contract = SPECIALISTS[role]["contract"]
        return [
            "README.md",
            "SOUL.md",
            "config.yaml",
            "distribution.yaml",
            f"skills/{contract}/SKILL.md",
        ]

    def _required_owned_files(self) -> list[str]:
        return [
            "README.md",
            "SOUL.md",
            "config.yaml",
            "distribution.yaml",
            "skills",
        ]

    def _extract_block(self, content: str, key: str) -> str:
        lines = content.splitlines()
        in_block = False
        indent = 0
        out = []
        for line in lines:
            if not in_block:
                if re.match(rf"^{re.escape(key)}:\s*$", line):
                    in_block = True
                    indent = len(line) - len(line.lstrip())
                continue

            current_indent = len(line) - len(line.lstrip())
            if line.strip() == "":
                if in_block:
                    out.append("")
                continue
            if current_indent <= indent:
                break
            out.append(line[indent + 1 :])
        return "\n".join(out)

    def _parse_simple_mapping(self, block: str) -> dict:
        result = {}
        lines = block.splitlines()
        idx = 0
        while idx < len(lines):
            line = lines[idx].strip()
            idx += 1
            if not line or line.startswith("#"):
                continue
            if ":" not in line:
                continue

            key, remainder = [piece.strip() for piece in line.split(":", 1)]
            if remainder == "":
                items = []
                while idx < len(lines):
                    next_line = lines[idx]
                    stripped = next_line.strip()
                    if not stripped.startswith("-"):
                        break
                    if next_line.startswith("- "):
                        items.append(stripped[2:].strip().strip('"').strip("'"))
                    idx += 1
                result[key] = items
                continue

            if remainder.startswith("[") and remainder.endswith("]"):
                inner = remainder[1:-1].strip()
                if not inner:
                    result[key] = []
                else:
                    result[key] = [
                        piece.strip().strip('"').strip("'")
                        for piece in inner.split(",")
                        if piece.strip()
                    ]
                continue

            if remainder.lower() in {"true", "false"}:
                result[key] = remainder.lower() == "true"
            else:
                result[key] = remainder.strip('"').strip("'")
        return result

    def _parse_tools_enabled(self, content: str, section: str) -> list[str]:
        block = self._extract_block(content, section)
        section_data = self._parse_simple_mapping(block)
        value = section_data.get("enabled", [])
        if isinstance(value, list):
            return value
        if isinstance(value, str):
            return [value]
        raise AssertionError(f"{section}.enabled must be a list")

    def _assert_config_contract(self, role: str, text: str):
        terminal = self._parse_simple_mapping(self._extract_block(text, "terminal"))
        memory = self._parse_simple_mapping(self._extract_block(text, "memory"))
        skills = self._parse_simple_mapping(self._extract_block(text, "skills"))

        self.assertEqual(terminal.get("home_mode"), "profile")
        self.assertEqual(terminal.get("auto_source_bashrc"), False)
        self.assertEqual(terminal.get("shell_init_files"), [])

        self.assertEqual(memory.get("memory_enabled"), False)
        self.assertEqual(memory.get("user_profile_enabled"), False)
        self.assertEqual(skills.get("write_approval"), True)

        self.assertEqual(self._parse_tools_enabled(text, "tools"), SPECIALISTS[role]["tools"])

        self.assertEqual(self._parse_tools_enabled(text, "plugins"), [])

        # Disabled or empty explicit surfaces.
        cron = self._parse_simple_mapping(self._extract_block(text, "cron"))
        gateway = self._parse_simple_mapping(self._extract_block(text, "gateway"))
        mcp = self._parse_simple_mapping(self._extract_block(text, "mcp"))
        self.assertEqual(cron.get("enabled", False), False)
        self.assertEqual(gateway.get("dispatch_enabled", False), False)
        self.assertEqual(mcp.get("servers", {}), {})

        # Block forbidden absolute infrastructure + authority surfaces.
        lowered = text.lower()
        self.assertNotIn("/home/", lowered)
        self.assertNotIn("model", lowered)
        self.assertNotIn("provider", lowered)
        self.assertNotIn("endpoint", lowered)
        self.assertNotIn("home-directory", lowered)
        self.assertNotIn("workbench", lowered)
        self.assertNotIn("env-pass", lowered)
        self.assertNotIn("production", lowered)

    def test_01_four_profiles_have_exact_five_payload_files(self):
        for role in SPECIALISTS:
            profile = self._profile_dir(role)
            self.assertTrue(profile.is_dir(), f"missing profile directory for {role}")
            expected = sorted(self._required_files(role))

            collected = sorted(
                [p.relative_to(profile).as_posix() for p in profile.rglob("*") if p.is_file()]
            )
            self.assertEqual(collected, expected, f"unexpected payload file set for {role}")

            for item in profile.rglob("*"):
                rel = item.relative_to(profile).as_posix()
                self.assertFalse(item.is_symlink(), f"symlink present in payload: {role}/{rel}")
                self.assertFalse(any(part.startswith(".") for part in rel.split("/")), f"hidden path present: {role}/{rel}")

    def test_02_specialist_readme_contains_only_safe_placeholders(self):
        for role in SPECIALISTS:
            profile = self._profile_dir(role)
            readme = profile / "README.md"
            self.assertTrue(readme.is_file(), f"missing README for {role}")
            text = readme.read_text(encoding="utf-8", errors="replace")
            self.assertIn("development placeholder", text)
            lowered = text.lower()
            self.assertNotIn("nick", lowered)
            self.assertNotIn("skepsy", lowered)
            self.assertNotIn("bert", lowered)
            self.assertNotIn("par 4", lowered)
            self.assertNotIn("brain os", lowered)

    def test_03_specialist_distribution_manifest_contract(self):
        for role in SPECIALISTS:
            profile = self._profile_dir(role)
            manifest = read_manifest(profile)
            self.assertIsNotNone(manifest, f"missing distribution.yaml for {role}")

            self.assertEqual(manifest.name, role)
            self.assertEqual(manifest.version, "0.1.0-dev")
            self.assertTrue(manifest.description.strip())
            self.assertFalse(manifest.description.lower().startswith("placeholder"))
            self.assertNotIn("proprietary", manifest.description.lower())
            self.assertNotIn("no license", manifest.description.lower())

            self.assertEqual(
                manifest.distribution_owned,
                self._required_owned_files(),
                f"distribution_owned mismatch for {role}",
            )

            self.assertEqual(manifest.author, "")
            self.assertEqual(manifest.license, "")
            self.assertEqual(manifest.env_requires, [])

            self.assertEqual(manifest.source, "")
            self.assertEqual(manifest.installed_at, "")

    def test_04_specialist_plan_install_is_distribution_owning_exact_five_files(self):
        for role in SPECIALISTS:
            profile = self._profile_dir(role)
            with tempfile.TemporaryDirectory() as td:
                plan = plan_install(source=str(profile), workdir=Path(td))

            self.assertEqual(plan.manifest.distribution_owned, self._required_owned_files())

            staged_root = plan.staged_dir
            staged = sorted(
                [
                    p.relative_to(staged_root).as_posix()
                    for p in staged_root.rglob("*")
                    if p.is_file()
                ]
            )
            self.assertEqual(staged, self._required_files(role))
            self.assertEqual(plan.staged_dir == profile.resolve(), True)

    def test_05_specialist_config_contracts_and_authority_surfaces(self):
        for role in SPECIALISTS:
            profile = self._profile_dir(role)
            config = profile / "config.yaml"
            self.assertTrue(config.is_file(), f"missing config.yaml for {role}")

            text = config.read_text(encoding="utf-8", errors="replace")
            self.assertTrue(text)
            self._assert_config_contract(role, text)

            body = text.lower()
            self.assertNotIn("model", body)
            self.assertNotIn("provider", body)

    def test_06_specialist_soul_contract_has_neutral_placeholders(self):
        for role in SPECIALISTS:
            profile = self._profile_dir(role)
            soul = profile / "SOUL.md"
            self.assertTrue(soul.is_file(), f"missing SOUL.md for {role}")

            text = soul.read_text(encoding="utf-8", errors="replace")
            lowered = text.lower()
            for field in (
                "OWNER_OR_COMPANY_NAME", "OWNER_FORM_OF_ADDRESS", "AGENT_NAME",
                "AGENT_INSPIRATION", "AGENT_INSPIRATION_TRAITS",
                "COMMUNICATION_STYLE", "OPTIONAL_HELP_AND_PROJECTS",
            ):
                self.assertNotIn(f"[{field}]", text)
                self.assertNotIn(f"${{{field}}}", text)
            self.assertIn("do not", lowered)
            self.assertIn("owner", lowered)
            self.assertNotIn("private key", lowered)
            self.assertNotIn("bert", lowered)

    def _parse_skill_frontmatter(self, path: Path) -> tuple[dict, str]:
        text = path.read_text(encoding="utf-8", errors="replace")
        lines = text.splitlines()
        self.assertGreaterEqual(len(lines), 4, f"invalid SKILL.md: {path}")
        self.assertEqual(lines[0], "---")
        end = None
        for i in range(1, len(lines)):
            if lines[i] == "---":
                end = i
                break
        self.assertIsNotNone(end)
        header = lines[1:end]

        parsed = {}
        for line in header:
            if ":" not in line:
                continue
            key, value = line.split(":", 1)
            parsed[key.strip()] = value.strip()

        body = "\n".join(lines[end + 1 :]).strip()
        return parsed, body

    def test_07_specialist_skill_frontmatter_and_body_contract(self):
        for role in SPECIALISTS:
            profile = self._profile_dir(role)
            contract = SPECIALISTS[role]["contract"]
            skill = profile / "skills" / contract / "SKILL.md"
            self.assertTrue(skill.is_file(), f"missing skill for {role}")

            frontmatter, body = self._parse_skill_frontmatter(skill)
            self.assertEqual(frontmatter.get("name"), contract)
            self.assertEqual(frontmatter.get("version"), "0.1.0-dev")
            self.assertEqual(frontmatter.get("author"), "Hermes Agent Team")
            self.assertEqual(frontmatter.get("license"), "MIT")
            self.assertTrue(str(frontmatter.get("description", "")).startswith("Use when"))
            self.assertTrue(body)

            lowered_body = body.lower()
            self.assertNotIn("github", lowered_body)
            self.assertNotIn("token", lowered_body)
            self.assertNotIn("secret", lowered_body)
            self.assertIn("evidence", lowered_body)
            self.assertIn("authority", lowered_body)

    def test_08_provenance_marks_required_four_specialists_as_maturing(self):
        provenance = (ROOT / "PROVENANCE.md").read_text(encoding="utf-8", errors="replace")
        row_text = []
        for line in provenance.splitlines():
            clean = line.strip()
            if not clean.startswith("|"):
                continue
            if clean.lower().startswith("| component |"):
                continue
            cells = [cell.strip().lower() for cell in clean.strip("|").split("|")]
            if len(cells) >= 4 and cells[0] in SPECIALISTS:
                row_text.append(cells)

        self.assertEqual(len(row_text), len(SPECIALISTS))
        for row in row_text:
            label = row[0]
            joined = " ".join(row)
            self.assertIn("newly authored", joined)
            self.assertIn("original", joined)
            self.assertIn("mit", joined)
            self.assertIn("pending publication", joined)
            self.assertNotIn("license", joined)
            self.assertNotIn("blocked", joined)

    def test_09_release_payload_integration_blockers_removed(self):
        release = json.loads((ROOT / "release-index.yaml").read_text(encoding="utf-8"))

        publication = release.get("publication", {})
        blockers = publication.get("blockers", [])
        self.assertIsInstance(blockers, list)
        self.assertNotIn("component_payloads", blockers)

        component_payloads = release.get("blockers", {}).get("component_payloads")
        self.assertNotIn(component_payloads, {"blocked", "ready"})

        self.assertEqual(release.get("release_status"), "private_candidate")
        self.assertIn("license", blockers)
        self.assertIn("owner_publication_approval", blockers)
        self.assertFalse(release.get("publication", {}).get("status") == "ready")

    def test_10_specialist_provenance_profile_rows_and_tool_contracts(self):
        for role in SPECIALISTS:
            profile = self._profile_dir(role)

            # Assert the profile contains the required minimal artifact set.
            required = self._required_files(role)
            for rel in required:
                path = profile / rel
                self.assertTrue(path.is_file(), f"missing required file {role}/{rel}")

            # Assert manifest and config paths are not carrying publication authority.
            manifest = read_manifest(profile)
            self.assertIsNotNone(manifest)
            self.assertEqual(manifest.name, role)
            distribution_data = self._parse_simple_mapping(
                Path(profile / "distribution.yaml").read_text(encoding="utf-8", errors="replace")
            )
            self.assertNotIn("author", distribution_data)
            self.assertNotIn("authority", distribution_data)

            config = (profile / "config.yaml").read_text(encoding="utf-8", errors="replace").lower()
            for forbidden in [
                "proprietary",
                "no license",
                "pending license",
                "publication",
                "model:",
                "provider:",
            ]:
                self.assertNotIn(forbidden, config)


if __name__ == "__main__":
    unittest.main()
