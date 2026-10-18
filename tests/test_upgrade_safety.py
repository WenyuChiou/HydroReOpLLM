"""Reject profile misbinding and stale tutorial outputs without provider calls."""
from copy import deepcopy
import json
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from llm_reservoir_agent.network import PROJECT_ROOT
from examples.fe_walter.extensions.reference_backend import ReferenceBackend
from llm_reservoir_agent.workflow import load_settings, main, run_settings, verify_settings_output



def _pin_example_extension(data):
    # This test copies FE Walter configuration into a disposable directory.
    if data.get("extensions"):
        entries = {"reference_v3_7": "examples/fe_walter/extensions/__init__.py",
                   "hanasaki": "examples/rules/hanasaki/__init__.py"}
        data["extensions"] = {key: str(PROJECT_ROOT / entries[key]) for key in data["extensions"]}
    return data

def benchmark_settings(tmp_path):
    source = PROJECT_ROOT / 'examples/fe_walter/benchmark/experiment.yaml'
    data = yaml.safe_load(source.read_text())
    data['case'] = str(PROJECT_ROOT / 'cases/fe_walter_reference/case.json')
    data['output'] = str(tmp_path / 'output')
    data['agents']['fe_operator']['rule_parameters']['inflow_statistics_file'] = str(
        PROJECT_ROOT / 'data/benchmark/fe_walter_statistics.json')
    path = tmp_path / 'experiment.yaml'
    path.write_text(yaml.safe_dump(_pin_example_extension(data)))
    return load_settings(path)


def test_wrong_profile_identity_stops_check_and_constructor(tmp_path):
    source = PROJECT_ROOT / 'examples/fe_walter/zero_shot/experiment.tutorial.yaml'
    settings = load_settings(source)
    spec = settings.agents['fe_operator']['reference']
    physical = deepcopy(settings.network['reservoirs']['FEWalter']['physical'])
    physical['reservoir_id'] = 'another_reservoir'
    with pytest.raises(ValueError, match='profile must match physical reservoir_id'):
        ReferenceBackend(spec, physical, runtime_root=PROJECT_ROOT)
    case = json.loads((PROJECT_ROOT / 'cases/fe_walter_reference/case.json').read_bytes())
    case['network']['reservoirs']['FEWalter']['physical'] = physical
    case['inflow_source']['path'] = 'inflows.csv'
    (tmp_path / 'inflows.csv').write_bytes((PROJECT_ROOT / 'cases/fe_walter_reference/inflows.csv').read_bytes())
    case_path = tmp_path / 'case.json'
    case_path.write_text(json.dumps(case))
    data = yaml.safe_load(source.read_text())
    data['case'] = str(case_path)
    data['case_root'] = str(tmp_path)
    data['agents']['fe_operator']['customization']['parameters']['reference']['responses'] = str(
        PROJECT_ROOT / 'tests/fixtures/zeroshot_responses.json')
    data['agents']['fe_operator']['customization']['parameters']['reference']['system_prompt'] = str(
        PROJECT_ROOT / 'archive/fe_walter/prompts/available_original.txt')
    config = tmp_path / 'reference.yaml'
    config.write_text(yaml.safe_dump(_pin_example_extension(data)))
    with pytest.raises(ValueError, match='profile must match physical reservoir_id'):
        load_settings(config)


def test_cache_reuses_identical_inputs_and_rejects_changed_settings(tmp_path):
    settings = benchmark_settings(tmp_path)
    with patch('urllib.request.urlopen', side_effect=AssertionError('network forbidden')):
        run_settings(settings)
    assert verify_settings_output(settings)['status'] == 'PASS'
    data = deepcopy(settings.data)
    data['agents']['fe_operator']['rule_parameters']['alpha'] = 0.9
    settings.path.write_text(yaml.safe_dump(_pin_example_extension(data)))
    changed = load_settings(settings.path)
    with pytest.raises(ValueError, match='choose a new run_id/output'):
        verify_settings_output(changed)


def test_cache_rejects_different_implementation(tmp_path):
    settings = benchmark_settings(tmp_path)
    with patch('urllib.request.urlopen', side_effect=AssertionError('network forbidden')):
        run_settings(settings)
    original_read = Path.read_bytes
    target = PROJECT_ROOT / 'src/llm_reservoir_agent/benchmark.py'

    def changed_read(path):
        if path == target:
            return b'# different implementation\n'
        return original_read(path)

    with patch.object(Path, 'read_bytes', changed_read), pytest.raises(ValueError, match='runtime'):
        verify_settings_output(settings)


@pytest.mark.parametrize('flag, expected', [([], False), (['--require-offline'], True)])
def test_verify_cli_forwards_offline_flag(tmp_path, flag, expected):
    with patch('llm_reservoir_agent.verification.verify_run', return_value={'status': 'PASS'}) as verify:
        assert main(['verify', str(tmp_path), *flag]) == 0
    verify.assert_called_once_with(tmp_path, require_offline=expected)
