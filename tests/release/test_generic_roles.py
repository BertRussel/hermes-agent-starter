"""Neutral product roles preserve the native assignee contract."""
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def package():
    spec = importlib.util.spec_from_file_location("full_system_package", ROOT / "scripts/full_system_package.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_public_roles_bind_one_canonical_distribution_each():
    path = ROOT / "profiles/roles.json"
    assert path.is_file(), "public/native role mapping is missing"
    mapping = json.loads(path.read_text())
    expected = {"owner-agent": "owner-agent", "implementer": "forge", "verifier": "verifier",
                "reviewer": "eve", "researcher": "recon", "designer": "art"}
    assert mapping == {"schema_version": 1, "native_assignees": expected}
    inventory = package().installable_profile_resources(ROOT)
    for role, native in expected.items():
        for path in (ROOT / "profiles" / native).rglob("*"):
            if path.is_file():
                name = f"profiles/{native}/{path.relative_to(ROOT / 'profiles' / native).as_posix()}"
                assert inventory[name] == path.read_bytes(), (role, name)
    assert len(set(expected.values())) == 6


def test_profile_archive_only_accepts_hash_bound_unchanged_instructions(tmp_path):
    import pytest
    module = package()
    source = ROOT / "profiles/forge"
    bound = {"SOUL.md": module.digest((source / "SOUL.md").read_bytes())}
    archive = tmp_path / "profile.tar.gz"
    module.build_archive(source, archive, instruction_hashes=bound)
    restored = module.restore_archive(archive, tmp_path / "restored", instruction_hashes=bound)
    assert (restored / "SOUL.md").read_bytes() == (source / "SOUL.md").read_bytes()
    with pytest.raises(ValueError, match="instruction hash"):
        module.restore_archive(archive, tmp_path / "rejected", instruction_hashes={"SOUL.md": "0" * 64})
    assert not (tmp_path / "rejected").exists()
    with pytest.raises(ValueError, match="payload scan"):
        module.build_archive(source, tmp_path / "unbound.tar.gz")


def test_native_install_canary_checks_all_six_extracted_distributions(tmp_path):
    import subprocess
    import sys
    module = package()
    assert hasattr(module, "native_profile_canary"), "native disposable six-profile install canary missing"
    restored = tmp_path / "restored"
    restored.mkdir()
    for native in module.PROFILES:
        source = ROOT / "profiles" / native
        bound = {"SOUL.md": module.digest((source / "SOUL.md").read_bytes())}
        archive = tmp_path / f"{native}.tar.gz"
        module.build_archive(source, archive, instruction_hashes=bound)
        module.restore_archive(archive, restored / native, instruction_hashes=bound)
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    env = module.isolated_environment(runtime)
    (runtime / "home").mkdir()
    (runtime / "tmp").mkdir()
    result = subprocess.run([sys.executable, "-B", "-c", module.native_profile_canary(), str(restored)],
                            cwd=runtime, env=env, capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stderr
    receipt = json.loads(result.stdout)
    assert receipt["installed"] == list(module.PROFILES)
    assert receipt["exact_source_hashes"] is True
    assert receipt["private_state_preserved"] is True
    assert receipt["activated"] is False
    assert receipt['version_update_rollback'] == 'passed-distribution-metadata-and-readme'
    assert receipt['vault_preserved'] is True


def test_canonical_acceptance_exercises_extracted_profiles_in_rebuilt_runtime():
    import inspect
    body = inspect.getsource(package().accept_full_system)
    assert 'sources["profile-distributions"] = installable_profile_resources(root)' in body
    assert 'native_profile_canary()' in body
    assert 'extracted["profile-distributions"]' in body
    assert 'sources["generic-foundation"]' in body
    assert 'render_geometric_art' in body
    assert 'changed_pixel_count' in body


def test_hash_bound_instruction_cannot_exempt_a_traversing_path():
    module = package()
    data = b"unchanged test data"
    name = "../SOUL.md"
    assert module.archive_scan(name, data, {name: module.digest(data)}) == ["forbidden_path"]
