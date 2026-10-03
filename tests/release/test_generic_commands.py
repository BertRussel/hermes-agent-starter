"""Actual native command help/ordinary CLI smoke, without live profile state."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]


def environment(tmp_path):
    spec = importlib.util.spec_from_file_location('package', ROOT / 'scripts/full_system_package.py')
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    (tmp_path / 'home').mkdir()
    (tmp_path / 'tmp').mkdir()
    return module.isolated_environment(tmp_path)


def test_native_profile_command_help_matches_documented_route(tmp_path):
    env = environment(tmp_path)
    for verb in ('install', 'update', 'export', 'import'):
        result = subprocess.run([sys.executable, '-B', '-m', 'hermes_cli.main', 'profile', verb, '--help'],
                                env=env, cwd=tmp_path, capture_output=True, text=True, timeout=30)
        assert result.returncode == 0, (verb, result.stderr)
        assert 'usage:' in result.stdout.lower(), (verb, result.stdout)
    assert not (tmp_path / 'home/.hermes/profiles').exists()


def test_customization_cli_reports_validation_not_installation(tmp_path):
    env = environment(tmp_path)
    result = subprocess.run([sys.executable, '-B', str(ROOT / 'scripts/validate_customization.py'),
                             str(ROOT / 'examples/fictional-personal-assistant/customization.json')],
                            env=env, cwd=tmp_path, capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {'status': 'validated', 'authority_policy': 'local-only', 'installed': False}
    assert 'Mira' not in result.stdout and 'Alex' not in result.stdout
