"""Public onboarding layout stays simple, generic, and navigable."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_owner_facing_guides_are_directly_in_docs():
    expected = {
        "OWNER-INTAKE.md",
        "OWNER-INTAKE.pdf",
        "ORACLE-VPS-SETUP.md",
        "HERMES-SETUP.md",
        "DISCORD-SETUP.md",
    }
    assert expected <= {path.name for path in (ROOT / "docs").iterdir() if path.is_file()}
    assert not (ROOT / "templates").exists()


def test_renderable_templates_live_under_docs_templates():
    expected = {
        "SOUL.template.md",
        "USER.template.md",
        "MEMORY.template.md",
        "PRIVATE-AGENT-BIBLE.template.md",
        "BOOTSTRAP-PROMPT.template.md",
    }
    assert expected <= {path.name for path in (ROOT / "docs/templates").iterdir() if path.is_file()}


def test_readme_is_a_short_navigation_page():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert len(readme.splitlines()) <= 140
    for link in (
        "docs/OWNER-INTAKE.pdf",
        "docs/ORACLE-VPS-SETUP.md",
        "docs/HERMES-SETUP.md",
        "docs/DISCORD-SETUP.md",
        "docs/templates/BOOTSTRAP-PROMPT.template.md",
    ):
        assert link in readme
    assert "# Agent instructions" not in readme
    assert "# Human setup" not in readme


def test_public_verifier_profile_is_owner_neutral():
    mapping = json.loads((ROOT / "profiles/roles.json").read_text(encoding="utf-8"))
    assert mapping["native_assignees"]["verifier"] == "verifier"
    assert (ROOT / "profiles/verifier").is_dir()
    assert not (ROOT / "profiles" / ("bert" + "-verifier")).exists()
    assert (ROOT / "profiles/verifier/distribution.yaml").read_text(encoding="utf-8").startswith("name: verifier\n")


def test_public_tracked_text_has_no_bert_verifier_identity():
    forbidden = ("bert" + "-verifier", "Bert" + "-Verifier", "Bert" + " Verifier")
    allowed_roots = (ROOT / "README.md", ROOT / "docs", ROOT / "profiles", ROOT / "runtime-bundle", ROOT / "scripts", ROOT / "tests")
    hits = []
    for root in allowed_roots:
        paths = [root] if root.is_file() else root.rglob("*")
        for path in paths:
            relative = path.relative_to(ROOT)
            if relative.parts[:3] == ("docs", "internal", "controller-only"):
                continue
            if not path.is_file() or path.suffix.lower() not in {".md", ".py", ".json", ".yaml", ".yml"}:
                continue
            text = path.read_text(encoding="utf-8")
            if any(token in text for token in forbidden):
                hits.append(path.relative_to(ROOT).as_posix())
    assert hits == []
