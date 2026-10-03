"""Bible coverage and navigation are necessary, not operational acceptance."""
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]


def test_generic_bible_has_every_required_linked_operating_chapter():
    index = ROOT / "docs/AGENT-BIBLE.md"
    assert index.is_file(), "generic operational Bible is missing"
    matrix = json.loads((ROOT / "docs/bible/coverage.json").read_text())
    assert len(matrix["chapters"]) == 25
    for chapter in matrix["chapters"]:
        path = ROOT / "docs" / chapter["path"]
        assert path.is_file(), chapter
        assert chapter["path"] in index.read_text()
        body = path.read_text()
        for heading in ("Actor and authority", "Prerequisites and version", "Inputs", "Procedure",
                        "Expected results", "Independent verification", "Failure and recovery", "Privacy and outputs", "Sources"):
            assert f"## {heading}" in body, (path, heading)
        for target in re.findall(r"\]\(([^)]+)\)", body):
            if not target.startswith(("https://", "http://", "#")):
                assert (path.parent / target.split('#')[0]).is_file(), (path, target)
    assert matrix["operational_acceptance"] == "pending-independent-onboarding-trial"
