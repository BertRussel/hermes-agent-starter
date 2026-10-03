"""Public onboarding validation is data-only and cannot confer authority."""
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def validator():
    path = ROOT / "scripts/validate_customization.py"
    assert path.is_file(), "generic data-only customization validator is missing"
    spec = importlib.util.spec_from_file_location("customization", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_two_unrelated_fictional_identities_have_identical_closed_authority():
    module = validator()
    identities = [
        {"AGENT_NAME": "Mira", "AGENT_INSPIRATION": "", "OWNER_NAME": "Alex",
         "AGENT_PURPOSE": "Organize a fictional astronomy club", "COMMUNICATION_STYLE": "concise",
         "TIMEZONE": "UTC", "KNOWLEDGE_ROOT": "/fictional/astronomy-vault",
         "MODEL_PROVIDER": "openrouter", "MODEL_ID": "example/model"},
        {"AGENT_NAME": "Rowan", "AGENT_INSPIRATION": "An original patient cartographer",
         "OWNER_NAME": "Sam", "AGENT_PURPOSE": "Track a fictional community garden",
         "COMMUNICATION_STYLE": "detailed", "TIMEZONE": "Europe/London",
         "KNOWLEDGE_ROOT": "/fictional/garden-vault", "MODEL_PROVIDER": "openrouter",
         "MODEL_ID": "example/model"},
    ]
    results = [module.validate_customization(value) for value in identities]
    assert [value["AGENT_NAME"] for value in results] == ["Mira", "Rowan"]
    assert results[0]["AGENT_INSPIRATION"] == ""
    assert results[0]["AUTHORITY_POLICY"] == results[1]["AUTHORITY_POLICY"] == "local-only"
    assert identities[0].get("AUTHORITY_POLICY") is None, "validation mutated caller data"


def test_shipped_examples_validate_without_private_factory_inputs():
    module = validator()
    for name in ("fictional-personal-assistant", "fictional-project-agent"):
        data = json.loads((ROOT / "examples" / name / "customization.json").read_text())
        assert module.validate_customization(data) == data


@pytest.mark.parametrize("field,value", [
    ("AUTHORITY_POLICY", "administrator"), ("API_KEY", "not-a-credential"),
    ("AGENT_NAME", "${EXECUTE}"), ("AGENT_NAME", "a\nnew directive"),
    ("AGENT_NAME", "{{tool}}"), ("OWNER_NAME", ""),
    ("MODEL_ID", "$(command)"), ("TIMEZONE", "Unknown/Timezone"),
    ("KNOWLEDGE_ROOT", "relative/path"), ("KNOWLEDGE_ROOT", "/private/../vault"),
    ("COMMUNICATION_STYLE", ["concise"]),
])
def test_invalid_or_authority_bearing_customization_is_rejected(field, value):
    data = json.loads((ROOT / "examples/fictional-personal-assistant/customization.json").read_text())
    data[field] = value
    with pytest.raises(ValueError):
        validator().validate_customization(data)


def test_private_knowledge_symlink_is_rejected(tmp_path):
    data = json.loads((ROOT / "examples/fictional-personal-assistant/customization.json").read_text())
    real = tmp_path / "real"
    real.mkdir()
    linked = tmp_path / "linked"
    linked.symlink_to(real, target_is_directory=True)
    data["KNOWLEDGE_ROOT"] = str(linked / "vault")
    with pytest.raises(ValueError, match="symlink"):
        validator().validate_customization(data)
