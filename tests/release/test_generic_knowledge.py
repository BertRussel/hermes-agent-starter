"""Create-once knowledge scaffolding never overwrites an owner's vault."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def creator():
    path = ROOT / "scripts/create_brain_os.py"
    assert path.is_file(), "safe create-once vault tool is missing"
    spec = importlib.util.spec_from_file_location("brain_os", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_new_vault_is_complete_existing_destination_is_never_overwritten(tmp_path):
    import pytest
    module = creator()
    destination = tmp_path / "private-vault"
    module.create_brain_os(ROOT / "brain-os-starter", destination)
    assert (destination / "00-MOC/Home.md").is_file()
    before = {p.relative_to(destination): p.read_bytes() for p in destination.rglob('*') if p.is_file()}
    with pytest.raises(FileExistsError):
        module.create_brain_os(ROOT / "brain-os-starter", destination)
    assert before == {p.relative_to(destination): p.read_bytes() for p in destination.rglob('*') if p.is_file()}


def test_destination_created_during_staging_wins_without_overwrite(tmp_path, monkeypatch):
    import pytest
    module = creator()
    destination = tmp_path / "raced"
    original_copy = module.copy_notes
    def raced_copy(source_fd, target_fd):
        destination.mkdir(exist_ok=True)
        (destination / "owner.txt").write_text("owner's existing data")
        original_copy(source_fd, target_fd)
    monkeypatch.setattr(module, "copy_notes", raced_copy)
    with pytest.raises(FileExistsError):
        module.create_brain_os(ROOT / "brain-os-starter", destination)
    assert (destination / "owner.txt").read_text() == "owner's existing data"
    assert not list(tmp_path.glob(".brain-os-stage-*"))


def test_symlink_source_and_destination_parent_are_refused(tmp_path):
    import pytest
    module = creator()
    real = tmp_path / "real"
    real.mkdir()
    linked = tmp_path / "linked"
    linked.symlink_to(real, target_is_directory=True)
    with pytest.raises(OSError):
        module.create_brain_os(ROOT / "brain-os-starter", linked / "vault")
    assert not (real / "vault").exists()
    source = tmp_path / "source"
    source.mkdir()
    (source / "bad.md").symlink_to(ROOT / "README.md")
    with pytest.raises(ValueError, match="unsafe"):
        module.create_brain_os(source, tmp_path / "vault")
    assert not (tmp_path / "vault").exists()
    assert not list(tmp_path.glob(".brain-os-stage-*"))


def test_interrupted_copy_cleans_only_its_stage(tmp_path, monkeypatch):
    import pytest
    module = creator()
    unrelated = tmp_path / ".brain-os-stage-unrelated"
    unrelated.mkdir()
    def interrupted_copy(source_fd, target_fd):
        raise RuntimeError("simulated interrupted staging")
    monkeypatch.setattr(module, "copy_notes", interrupted_copy)
    with pytest.raises(RuntimeError, match="interrupted"):
        module.create_brain_os(ROOT / "brain-os-starter", tmp_path / "vault")
    assert unrelated.is_dir()
    assert not (tmp_path / "vault").exists()
    assert list(tmp_path.glob(".brain-os-stage-*")) == [unrelated]


def test_every_relative_wikilink_survives_vault_relocation(tmp_path):
    import re
    destination = tmp_path / "relocated"
    creator().create_brain_os(ROOT / "brain-os-starter", destination)
    for note in destination.rglob("*.md"):
        for link in re.findall(r"\[\[([^\]]+)\]\]", note.read_text()):
            target = note.parent / (link.split('|')[0] + '.md')
            assert target.is_file(), (note, link)
