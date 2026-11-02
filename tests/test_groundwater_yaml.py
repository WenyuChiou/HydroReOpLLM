"""Synthetic YAML checks; no event observations, calibration or LLM transport."""
import copy
import json
from unittest.mock import patch

import numpy as np
import pytest
import yaml

from tests.test_time_scale_yaml import _daily_bundle, _hourly_bundle, _yaml
from llm_reservoir_agent.coupled import load_coupled_settings, prepare_coupled, prepared_experiment


def test_daily_diagnostics_preserve_native_routed_flow_and_are_reusable(tmp_path):
    data = _daily_bundle(tmp_path)
    base = load_coupled_settings(tmp_path / 'simulation.yaml')
    prepare_coupled(base)
    data['output'] = 'diagnostic'; data['hydrology']['diagnostics'] = True
    _yaml(tmp_path / 'simulation.yaml', data)
    settings = load_coupled_settings(tmp_path / 'simulation.yaml')
    manifest = prepare_coupled(settings)
    assert (tmp_path/'output/inflows.csv').read_bytes() == (tmp_path/'diagnostic/inflows.csv').read_bytes()
    rows = json.loads((tmp_path/'diagnostic/hydrology_diagnostics.json').read_text())['a']
    assert len(rows) == 5 and [r['step'] for r in rows] == list(range(5))
    assert max(abs(r['mass_balance_residual_m3']) for r in rows) < 2e-7
    assert 'hydrology_state.json' in manifest['generated_files']
    initial = json.loads((tmp_path/'diagnostic/hydrology.json').read_text())['groundwater_initialization']['a']
    assert initial['source'] == 'legacy-daily-Res*S0'
    data['output'] = 'reuse'; data['hydrology']['prepared_from'] = 'diagnostic'
    _yaml(tmp_path/'simulation.yaml', data)
    with patch('llm_reservoir_agent.weather.simulate_weather', side_effect=AssertionError('rerun')):
        prepare_coupled(load_coupled_settings(tmp_path/'simulation.yaml'))
    for name in ['inflows.csv', 'hydrology_diagnostics.json', 'hydrology_state.json']:
        assert (tmp_path/'reuse'/name).read_bytes() == (tmp_path/'diagnostic'/name).read_bytes()
    path = tmp_path/'reuse/hydrology_state.json'; path.write_text('{}')
    with pytest.raises(ValueError, match='checksum'):
        prepared_experiment(load_coupled_settings(tmp_path/'simulation.yaml'))


@pytest.mark.parametrize('hourly', [False, True])
def test_yaml_explicit_BF0_matches_B0_and_conflicts_fail_before_preparation(tmp_path, hourly):
    from hydrocnhs.rainfall_runoff_model.groundwater import daily_baseflow_to_storage
    data = (_hourly_bundle if hourly else _daily_bundle)(tmp_path)
    path = tmp_path/'hydrology.yaml'; model = yaml.safe_load(path.read_text())
    if hourly:
        unit = model['catchments']['a']; unit['parameters']['Alpha'] = .3
        initial, pars = unit['initial'], unit['parameters']
    else:
        unit = model['RainfallRunoff']['a']; initial, pars = unit['Inputs'], unit['Pars']
    initial.pop('B0', None); initial['BF0'] = .24
    _yaml(path, model); prepare_coupled(load_coupled_settings(tmp_path/'simulation.yaml'))
    del initial['BF0']; initial['B0'] = daily_baseflow_to_storage(.24, pars['Alpha'])
    data['output'] = 'storage'; _yaml(path, model); _yaml(tmp_path/'simulation.yaml', data)
    prepare_coupled(load_coupled_settings(tmp_path/'simulation.yaml'))
    import csv
    def flows(path):
        with path.open() as f:return [float(r['local_inflow_cms']) for r in csv.DictReader(f)]
    np.testing.assert_allclose(flows(tmp_path/'output/inflows.csv'), flows(tmp_path/'storage/inflows.csv'), rtol=2e-14, atol=1e-14)
    initial['BF0'] = .24; data['output'] = 'invalid'; _yaml(path, model); _yaml(tmp_path/'simulation.yaml', data)
    with pytest.raises(ValueError, match='exactly one'):
        load_coupled_settings(tmp_path/'simulation.yaml')
    assert not (tmp_path/'invalid').exists()


def test_daily_diagnostics_setting_binds_reuse_and_validates_type(tmp_path):
    data = _daily_bundle(tmp_path); prepare_coupled(load_coupled_settings(tmp_path/'simulation.yaml'))
    data['output'] = 'invalid'; data['hydrology'].update(diagnostics=True, prepared_from='output')
    _yaml(tmp_path/'simulation.yaml', data)
    with pytest.raises(ValueError, match='reusable hydrology differs'):
        prepare_coupled(load_coupled_settings(tmp_path/'simulation.yaml'))
    data['hydrology']['diagnostics'] = 'true'; _yaml(tmp_path/'simulation.yaml', data)
    with pytest.raises(ValueError, match='boolean'):
        load_coupled_settings(tmp_path/'simulation.yaml')


def test_native_diagnostics_survive_process_workers(tmp_path):
    from tests.test_time_scale_yaml import ROOT
    from hydrocnhs import Model
    source = yaml.safe_load((ROOT/'data/accepted/fe_walter_hydrology.yaml').read_text())
    source['WaterSystem'].update(StartDate='2020/01/01', EndDate='2020/02/29', DataLength=60)
    units = source['WaterSystem']['Outlets']
    forcing = {u:np.full(60,10.) for u in units}
    rain = {u:np.full(60,.1) for u in units}
    pet = {u:np.full(60,.02) for u in units}
    kwargs = dict(name='groundwater-test',paral_setting={'verbose':0,'cores_pet':1,'cores_formUH':1,'cores_runoff':2})
    output = {}; model = Model(copy.deepcopy(source), **kwargs)
    model.run(forcing,rain,pet,disable=True,runoff_diagnostics=output)
    assert set(output) == set(units)
    for u in units:
        assert len(output[u]['records']) == 60
        assert set(output[u]['final_state']) == {'BFt','St','Ut','SnowSt','AnteMois'}
