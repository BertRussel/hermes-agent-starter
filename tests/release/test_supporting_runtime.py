"""Supporting runtime boundaries; local private feeds are never network requests."""
import importlib.util
from pathlib import Path

import pytest
import wave
import tomllib


def implementation():
    root = Path(__file__).resolve().parents[2]
    spec = importlib.util.spec_from_file_location("supporting_runtime", root / "runtimes/supporting-runtime/src/supporting_runtime/runtime.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_research_preserves_https_citation_without_claiming_external_verification():
    result = implementation().research_feed(b'<rss><channel><item><title>Local</title><link>https://example.com/source</link></item></channel></rss>')
    assert result[0]["source"] == "https://example.com/source"
    assert "not independent factual verification" in result[0]["evidence"]


@pytest.mark.parametrize("link", ["https://user:pw@example.com/source", "https://", "https://example.com/\ncontrol"])
def test_research_rejects_credentials_missing_hosts_and_controls(link):
    feed = f'<rss><channel><item><title>Local</title><link>{link}</link></item></channel></rss>'.encode()
    with pytest.raises(ValueError):
        implementation().research_feed(feed)


def test_research_rejects_entities_and_unbounded_input():
    module = implementation()
    for payload in (b'<!DOCTYPE rss [<!ENTITY x "value">]><rss/>', b'x' * (1024 * 1024 + 1)):
        with pytest.raises(ValueError, match="unsafe"):
            module.research_feed(payload)


def test_media_canary_writes_and_reopens_actual_pcm_audio(tmp_path):
    destination = tmp_path / "media"
    report = implementation().media_canary(destination)
    assert report["audio"] == "passed"
    with wave.open(str(destination / "local.wav"), "rb") as audio:
        assert audio.getnframes() == 8000
        assert audio.getframerate() == 8000
        assert audio.getnchannels() == 1
        assert audio.getsampwidth() == 2
        assert any(audio.readframes(8000))
    with pytest.raises(ValueError, match="absent"):
        implementation().media_canary(destination)


def test_supporting_environment_has_installable_dependency_metadata():
    root = Path(__file__).resolve().parents[2] / "runtimes/supporting-runtime"
    metadata = tomllib.loads((root / "pyproject.toml").read_text())
    assert metadata["project"]["name"] == "handoff-supporting-runtime"
    assert metadata["build-system"]["requires"] == ["setuptools==79.0.1"]
    assert "python-docx==1.2.0" in metadata["project"]["dependencies"]


def test_original_legal_creative_route_renders_editable_svg_and_real_png(tmp_path):
    from PIL import Image
    import xml.etree.ElementTree as ET
    module = implementation()
    assert hasattr(module, 'render_geometric_art'), 'original public geometric creative route missing'
    design = {'width': 32, 'height': 32, 'rectangles': [
        {'x': 2, 'y': 2, 'width': 28, 'height': 28, 'fill': '#123456'}]}
    destination = tmp_path / 'original-art'
    report = module.render_geometric_art(design, destination)
    assert report['status'] == 'rendered-not-owner-approved'
    assert report['source_rights'] == 'original-input-required'
    assert ET.parse(destination / 'editable.svg').getroot().tag == '{http://www.w3.org/2000/svg}svg'
    with Image.open(destination / 'render.png') as image:
        assert image.size == (32, 32)
        assert image.getbbox() == (2, 2, 30, 30)
        assert image.getpixel((2, 2)) == (18, 52, 86, 255)
    assert design['rectangles'][0]['width'] == 28, 'renderer mutated input'


def test_geometric_route_rejects_untrusted_assets_and_existing_output(tmp_path):
    module = implementation()
    design = {'width': 32, 'height': 32, 'rectangles': [
        {'x': 2, 'y': 2, 'width': 28, 'height': 28, 'fill': '#123456'}]}
    invalid = [dict(design, width=True), dict(design, width=4096),
               dict(design, rectangles=[]), dict(design, external='https://example.com/image')]
    for updates in ({'fill': 'url(https://example.com)'}, {'x': -1}, {'width': 33}, {'x': True},
                    {'script': 'untrusted'}):
        invalid.append(dict(design, rectangles=[dict(design['rectangles'][0], **updates)]))
    for candidate in invalid:
        with pytest.raises(ValueError):
            module.render_geometric_art(candidate, tmp_path / 'rejected')
        assert not (tmp_path / 'rejected').exists()
    existing = tmp_path / 'existing'
    existing.mkdir()
    with pytest.raises(ValueError, match='absent'):
        module.render_geometric_art(design, existing)
    link = tmp_path / 'symlink'
    link.symlink_to(tmp_path / 'missing')
    with pytest.raises(ValueError, match='absent'):
        module.render_geometric_art(design, link)


def test_geometric_revision_measures_actual_changed_pixels(tmp_path):
    from PIL import Image, ImageChops
    module = implementation()
    base = {'width': 32, 'height': 32, 'rectangles': [
        {'x': 2, 'y': 2, 'width': 28, 'height': 28, 'fill': '#123456'}]}
    changed = dict(base, rectangles=[dict(base['rectangles'][0], width=20)])
    module.render_geometric_art(base, tmp_path / 'base')
    module.render_geometric_art(changed, tmp_path / 'changed')
    with Image.open(tmp_path / 'base/render.png') as a, Image.open(tmp_path / 'changed/render.png') as b:
        assert ImageChops.difference(a, b).getbbox() == (22, 2, 30, 30)
        assert sum(a.getpixel((x, y)) != b.getpixel((x, y))
                   for x in range(32) for y in range(32)) == 224
