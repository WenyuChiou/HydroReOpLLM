"""Exercise the published Daily lessons from copied files and preserve lineage."""
from pathlib import Path
import importlib.util
import hashlib
import json
import shutil
from unittest.mock import patch

import pytest

from llm_reservoir_agent.workflow import load_settings, run_settings
from llm_reservoir_agent.verification import verify_run
from examples.fe_walter.coupled.export_comparison import HISTORICAL_PROMPTS, PROMPTS

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize('label,count,storages,channel', [
    ('single', 1, [1_345_600.], 86_400.),
    ('cascade', 3, [1_345_600., 1_086_400., 1_086_400.], 259_200.),
])
def test_published_daily_examples_run_outside_checkout(tmp_path, monkeypatch, label, count, storages, channel):
    """Analytic stocks catch inflow duplication, delay mistakes and shared state."""
    folder = tmp_path / 'research project' / 'examples' / 'daily_offline'
    shutil.copytree(ROOT / 'examples/daily_offline', folder)
    monkeypatch.chdir(tmp_path)
    def forbidden(*args, **kwargs):
        raise AssertionError('Daily lesson must not contact any service')
    with patch('socket.socket.connect', side_effect=forbidden), patch('socket.socket.connect_ex', side_effect=forbidden):
        settings = load_settings(folder / f'{label}.yaml')
        records, result = run_settings(settings)
    output = Path(settings.report['output'])
    proof = verify_run(output, require_offline=True)
    assert proof['status'] == 'PASS'
    assert proof['days'] == 4
    assert proof['observed_network_calls'] == 0
    assert len(records) == count
    assert result['summary']['final_storage_m3'] == pytest.approx(
        {f'Lake_{i+1}': storage for i, storage in enumerate(storages)})
    assert result['summary']['final_channel_storage_m3'] == pytest.approx(channel)
    assert proof['max_system_balance_residual_m3'] <= 1e-6
    assert [record['observation']['timestamp'][:10] for record in records['Lake_1']] == [
        '2020-02-28', '2020-02-29', '2020-03-01', '2020-03-02']
    before = {path.relative_to(output): hashlib.sha256(path.read_bytes()).hexdigest()
              for path in output.rglob('*') if path.is_file()}
    with pytest.raises((ValueError, FileExistsError)):
        run_settings(settings)
    assert before == {path.relative_to(output): hashlib.sha256(path.read_bytes()).hexdigest()
                      for path in output.rglob('*') if path.is_file()}


def test_current_prompt_pins_do_not_relabel_historical_payloads():
    assert set(HISTORICAL_PROMPTS) == set(PROMPTS)
    for method, (name, digest) in PROMPTS.items():
        assert HISTORICAL_PROMPTS[method][0] == name
        assert digest != HISTORICAL_PROMPTS[method][1]
        assert hashlib.sha256((ROOT / 'examples/fe_walter/prompts' / name).read_bytes()).hexdigest() == digest


def test_maintained_source_record_preserves_scientific_receipt():
    case = ROOT / 'examples/fe_walter/operation'
    provenance = json.loads((case / 'provenance.json').read_text())
    engineering = json.loads((case / 'engineering-sources-v2.json').read_text())
    assert engineering['historical_provenance_sha256'] == hashlib.sha256((case / 'provenance.json').read_bytes()).hexdigest()
    assert set(engineering['dependencies']) == set(provenance['shared_dependencies'])
    for name, record in engineering['dependencies'].items():
        assert record['historical_sha256'] == provenance['shared_dependencies'][name]
        assert record['current_sha256'] == hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
    for name, digest in provenance['artifacts'].items():
        assert hashlib.sha256((case / name).read_bytes()).hexdigest() == digest


def test_daily_download_namespace_preserves_historical_teaching(tmp_path):
    spec = importlib.util.spec_from_file_location('daily_download_builder', ROOT / 'docs/build.py')
    builder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(builder)
    with patch('socket.socket.connect', side_effect=AssertionError('network forbidden')):
        builder.prepare(tmp_path)
    assert len(builder.TUTORIAL_DOWNLOADS) == 31
    for source, name in builder.DAILY_DOWNLOADS.items():
        assert (tmp_path / '_daily_downloads' / name).read_bytes() == (ROOT / source).read_bytes()
        assert (tmp_path / source).read_bytes() == (ROOT / source).read_bytes()
