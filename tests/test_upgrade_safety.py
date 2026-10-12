"""Reject profile misbinding and stale tutorial outputs without provider calls."""
from copy import deepcopy
import json
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from llm_reservoir_agent.network import PROJECT_ROOT
from llm_reservoir_agent.reference_backend import ReferenceBackend
from llm_reservoir_agent.workflow import load_settings, main, run_settings, verify_settings_output


def benchmark_settings(tmp_path):
    source = PROJECT_ROOT / 'examples/fe_walter/benchmark/experiment.yaml'
    data = yaml.safe_load(source.read_text())
    data['case'] = str(PROJECT_ROOT / 'cases/fe_walter_reference/case.json')
    data['output'] = str(tmp_path / 'output')
    data['agents']['fe_operator']['benchmark']['statistics'] = str(
        PROJECT_ROOT / 'data/benchmark/fe_walter_statistics.json')
    path = tmp_path / 'experiment.yaml'
    path.write_text(yaml.safe_dump(data))
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
    data['agents']['fe_operator']['reference']['responses'] = str(
        PROJECT_ROOT / 'tests/fixtures/zeroshot_responses.json')
    data['agents']['fe_operator']['reference']['system_prompt'] = str(
        PROJECT_ROOT / 'prompts/fe_walter_reference/zeroshot_system.txt')
    config = tmp_path / 'reference.yaml'
    config.write_text(yaml.safe_dump(data))
    with pytest.raises(ValueError, match='profile must match physical reservoir_id'):
        load_settings(config)


def test_cache_reuses_identical_inputs_and_rejects_changed_settings(tmp_path):
    settings = benchmark_settings(tmp_path)
    with patch('urllib.request.urlopen', side_effect=AssertionError('network forbidden')):
        run_settings(settings)
    assert verify_settings_output(settings)['status'] == 'PASS'
    data = deepcopy(settings.data)
    data['agents']['fe_operator']['benchmark']['alpha'] = 0.9
    settings.path.write_text(yaml.safe_dump(data))
    changed = load_settings(settings.path)
    with pytest.raises(ValueError, match='choose a new run_id/output'):
        verify_settings_output(changed)


def test_cache_rejects_different_implementation(tmp_path):
    settings = benchmark_settings(tmp_path)
    with patch('urllib.request.urlopen', side_effect=AssertionError('network forbidden')):
        run_settings(settings)
    original_glob = Path.glob
    replacement = tmp_path / 'benchmark.py'
    replacement.write_text('# different implementation\n')
    module_dir = PROJECT_ROOT / 'src/llm_reservoir_agent'

    def changed_glob(path, pattern):
        if path == module_dir and pattern == '*.py':
            return iter([replacement if p.name == 'benchmark.py' else p
                         for p in original_glob(path, pattern)])
        return original_glob(path, pattern)

    with patch.object(Path, 'glob', changed_glob), pytest.raises(ValueError, match='runtime'):
        verify_settings_output(settings)


@pytest.mark.parametrize('flag, expected', [([], False), (['--require-offline'], True)])
def test_verify_cli_forwards_offline_flag(tmp_path, flag, expected):
    with patch('llm_reservoir_agent.verification.verify_run', return_value={'status': 'PASS'}) as verify:
        assert main(['verify', str(tmp_path), *flag]) == 0
    verify.assert_called_once_with(tmp_path, require_offline=expected)
