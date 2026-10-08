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


def test_two_unrelated_fictional_identities_validate_as_exact_private_overlay_data():
    module = validator()
    identities = [
        {"OWNER_OR_COMPANY_NAME": "Fictional Astronomy Club", "OWNER_FORM_OF_ADDRESS": "Coordinator",
         "AGENT_NAME": "Mira", "AGENT_INSPIRATION": "original navigator", "AGENT_INSPIRATION_TRAITS": "calm",
         "COMMUNICATION_STYLE": "concise", "OPTIONAL_HELP_AND_PROJECTS": "fictional astronomy"},
        {"OWNER_OR_COMPANY_NAME": "Fictional Garden", "OWNER_FORM_OF_ADDRESS": "Steward",
         "AGENT_NAME": "Rowan", "AGENT_INSPIRATION": "original cartographer", "AGENT_INSPIRATION_TRAITS": "patient",
         "COMMUNICATION_STYLE": "detailed", "OPTIONAL_HELP_AND_PROJECTS": "fictional garden"},
    ]
    results = [module.validate_customization(value) for value in identities]
    assert [value["AGENT_NAME"] for value in results] == ["Mira", "Rowan"]
    assert results[0]["AGENT_INSPIRATION"] == "original navigator"
    assert results[0] == identities[0], "validation mutated caller data"


def test_shipped_examples_validate_without_private_factory_inputs():
    module = validator()
    for name in ("fictional-personal-assistant", "fictional-project-agent"):
        data = json.loads((ROOT / "examples" / name / "customization.json").read_text())
        assert module.validate_customization(data) == data


@pytest.mark.parametrize("field,value", [
    ("AUTHORITY_POLICY", "administrator"), ("API_KEY", "not-a-credential"),
    ("AGENT_NAME", "${EXECUTE}"), ("AGENT_NAME", "a\nnew directive"),
    ("AGENT_NAME", "{{tool}}"), ("OWNER_OR_COMPANY_NAME", ""),
    ("OWNER_FORM_OF_ADDRESS", "$(command)"), ("AGENT_INSPIRATION_TRAITS", "a\nnew directive"),
    ("COMMUNICATION_STYLE", ["concise"]),
])
def test_invalid_or_authority_bearing_customization_is_rejected(field, value):
    data = json.loads((ROOT / "examples/fictional-personal-assistant/customization.json").read_text())
    data[field] = value
    with pytest.raises(ValueError):
        validator().validate_customization(data)


def test_exact_schema_rejects_removed_runtime_and_identity_binding_fields():
    data = json.loads((ROOT / "examples/fictional-personal-assistant/customization.json").read_text())
    data["KNOWLEDGE_ROOT"] = "/private/vault"
    with pytest.raises(ValueError, match="unexpected"):
        validator().validate_customization(data)
