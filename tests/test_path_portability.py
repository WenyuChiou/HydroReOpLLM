"""Source pins must not depend on temporary path spelling or alias expansion."""
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

import pytest

from llm_reservoir_agent import coupled
from test_weather_entry import make_bundle


def aliased_temporary_directory(monkeypatch):
    """Model an existing temp directory reached through a noncanonical alias."""
    original = coupled.tempfile.TemporaryDirectory

    @contextmanager
    def aliased(*args, **kwargs):
        with original(*args, **kwargs) as name:
            child = Path(name) / 'parent-alias'
            child.mkdir()
            yield str(child / '..')

    monkeypatch.setattr(coupled.tempfile, 'TemporaryDirectory', aliased)


def test_temporary_alias_does_not_enter_durable_source_pins(tmp_path, monkeypatch):
    make_bundle(tmp_path)
    aliased_temporary_directory(monkeypatch)
    first = coupled.load_coupled_settings(tmp_path / 'simulation.yaml')
    second = coupled.load_coupled_settings(tmp_path / 'simulation.yaml')
    assert first.report == second.report
    assert not any('hydroops-check-' in key for key in first.files)


def test_real_source_change_still_fails_before_hydrology(tmp_path, monkeypatch):
    make_bundle(tmp_path)
    aliased_temporary_directory(monkeypatch)
    settings = coupled.load_coupled_settings(tmp_path / 'simulation.yaml')
    weather = tmp_path / 'weather.csv'
    weather.write_text(weather.read_text(encoding='utf-8').replace(',10,10,0.1', ',11,10,0.1', 1), encoding='utf-8')
    monkeypatch.setattr('hydrocnhs.Model', lambda *args, **kwargs: pytest.fail('source check must precede hydrology'))
    with pytest.raises(ValueError, match='inputs changed after check'):
        coupled.run_coupled(settings)


def test_exported_resource_remains_resolvable_when_relative_path_is_unavailable(tmp_path):
    from examples.fe_walter.downstream.prepare import _resource_reference
    resource = tmp_path / 'resource.txt'
    resource.write_text('same bytes', encoding='utf-8')
    with patch('examples.fe_walter.downstream.prepare.os.path.relpath', side_effect=ValueError('different volumes')):
        reference = _resource_reference(resource, tmp_path)
    assert Path(reference).is_absolute()
    assert Path(reference).read_bytes() == resource.read_bytes()
