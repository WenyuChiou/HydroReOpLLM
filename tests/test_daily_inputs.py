"""Trace variables preserve both decisions and physical outcomes, without providers."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
from unittest.mock import patch

import pytest
import yaml

from examples.fe_walter.extensions.daily_inputs import reference_variables
from llm_reservoir_agent.network import PROJECT_ROOT
from llm_reservoir_agent.workflow import load_settings, run_settings


@pytest.mark.parametrize('method', ['zeroshot', 'dkp'])
def test_actual_history_matches_previous_implemented_release(method):
    original = PROJECT_ROOT / f'tests/fixtures/fe_walter_current/{method}.yaml'
    data = yaml.safe_load(original.read_text(encoding='utf-8'))
    data['extensions'] = {key: str((original.parent / value).resolve())
                          for key, value in data.get('extensions', {}).items()}
    data['case'] = str((original.parent / data['case']).resolve())
    spec = data['agents']['fe_operator']['customization']['parameters']['reference']
    for key in ('system_prompt', 'responses', 'dkp'):
        if key in spec:
            spec[key] = str((original.parent / spec[key]).resolve())
    with tempfile.TemporaryDirectory() as folder, patch('urllib.request.urlopen', side_effect=AssertionError('network forbidden')):
        folder = Path(folder)
        data['output'] = str(folder / 'run')
        config = folder / 'experiment.yaml'
        config.write_text(yaml.safe_dump(data), encoding='utf-8')
        run_settings(load_settings(config))
        variables = sorted((json.loads(p.read_text(encoding='utf-8'))['backend_trace']['input_variables']
                            for p in (folder / 'run/raw').glob('policy_*.json')),
                           key=lambda item: item['timestep'])
        first, second = variables[:2]
        assert first['native_history'] == []
        history = second['native_history'][-1]
        physics = [json.loads(line) for line in (folder / 'run/physics.jsonl').read_text(encoding='utf-8').splitlines()]
        assert history['implemented_release_cfs'] * 0.028316847 == pytest.approx(physics[0]['record']['transition']['total_outflow_cms'])
        assert 'decision_release_cfs' in history
        assert second['reservoir_profile'] == 'fe_walter'
        assert first['pool_elevation_start_ft'] == pytest.approx(1300.0)
        assert first['storage_start_af'] == pytest.approx(1992.61)


def test_non_fe_native_dkp_fails_before_execution(tmp_path):
    original = PROJECT_ROOT / 'tests/fixtures/fe_walter_current/dkp.yaml'
    data = yaml.safe_load(original.read_text(encoding='utf-8'))
    data['extensions'] = {key: str((original.parent / value).resolve())
                          for key, value in data.get('extensions', {}).items()}
    data['case'] = str((original.parent / data['case']).resolve())
    data['output'] = str(tmp_path/'run')
    spec = data['agents']['fe_operator']['customization']['parameters']['reference']
    spec['profile'] = 'beltzville'
    for key in ('system_prompt','responses','dkp'):
        spec[key] = str((original.parent/spec[key]).resolve())
    config = tmp_path/'experiment.yaml'
    config.write_text(yaml.safe_dump(data),encoding='utf-8')
    with pytest.raises(ValueError,match='FE Walter-specific'):
        load_settings(config)
    assert not (tmp_path/'run').exists()
