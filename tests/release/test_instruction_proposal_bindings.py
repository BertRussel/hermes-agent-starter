"""The public package never carries controller-only instruction proposals."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_public_package_omits_controller_only_instruction_proposals():
    spec = importlib.util.spec_from_file_location('package', ROOT / 'scripts/full_system_package.py')
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert hasattr(module, 'instruction_proposal_bindings'), 'foreground path/hash binding missing'
    receipt = module.instruction_proposal_bindings(ROOT)
    assert receipt['status'] == 'not-shipped-public-system'
    assert receipt['targets'] == []
    assert receipt['role_targets'] == []
    assert not (ROOT / 'docs/internal/controller-only/instruction-proposals.json').exists()
    assert set(receipt['role_current_sha256']) == {
        f'profiles/{role}/SOUL.md' for role in module.PROFILES}

