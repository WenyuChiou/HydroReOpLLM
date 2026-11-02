"""Cross-scale invariants for case-neutral configured reservoir operation."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json

import pytest

from llm_reservoir_agent.experiment import run_experiment
from llm_reservoir_agent.network import validate_inflows, validate_network
from llm_reservoir_agent.verification import verify_run


class FixedRelease:
    policy_id = 'offline-spatiotemporal-fixture'
    network_calls = 0

    def __init__(self, value=5):
        self.value = value
        self.observations = []

    def decide(self, observation):
        self.observations.append(deepcopy(observation))
        return {'release_cms': self.value}

    def describe(self):
        return {'data_kind':'synthetic_fixture', 'model_used':False, 'network_enabled':False}


def fixture(dt=3600, *, start='2024-02-28T23:00:00Z', steps=4, lag=None):
    config = {'schema_version':'llm-reservoir-network.v2', 'data_kind':'synthetic_fixture',
              'start_date': start, 'reservoirs': {'Lake-α': {'inflow_node':'tributary input',
              'physical':{'reservoir_id':'arbitrary-lake','capacity_m3':20_000_000,
                          'dead_storage_m3':0,'initial_storage_m3':500_000,
                          'minimum_release_cms':0,'maximum_release_cms':100,'dt_seconds':dt}}},
              'connections':[{'source':'Lake-α','target':'downstream outlet',
                              'unit_hydrograph':lag or [1.]}], 'outlets':['downstream outlet']}
    initial=datetime.fromisoformat(start.replace('Z','+00:00'))
    dates=[(initial+timedelta(seconds=i*dt)).isoformat().replace('+00:00','Z') for i in range(steps)]
    rows=[{'date':d,'local_inflow_cms':{'tributary input':10.+i,'downstream outlet':2.}} for i,d in enumerate(dates)]
    return config, rows


@pytest.mark.parametrize('dt',[900,3600,7200,86400,172800])
def test_configured_step_controls_clock_storage_and_verified_volumes(tmp_path,dt):
    config,rows=fixture(dt,lag=[0.,1.])
    backend=FixedRelease()
    _,result=run_experiment(config,rows,{'Lake-α':backend},output=tmp_path/'run',run_id='generic-step')
    assert result['status']=='COMPLETED'
    expected=500_000+sum(10+i-5 for i in range(4))*dt
    assert result['summary']['final_storage_m3']['Lake-α']==pytest.approx(expected)
    assert result['summary']['final_channel_storage_m3']==pytest.approx(5*dt)
    observed=[datetime.fromisoformat(o['timestamp'].replace('Z','+00:00')) for o in backend.observations]
    assert observed==[datetime.fromisoformat(r['date'].replace('Z','+00:00')) for r in rows]
    assert all(o['state']['dt_seconds']==dt for o in backend.observations)
    assert backend.observations[0]['release_upper_bound_cms']==pytest.approx(min(100,10+500_000/dt))
    assert verify_run(tmp_path/'run',require_offline=True)['status']=='PASS'


def test_same_network_clock_for_all_reservoirs():
    config,_=fixture()
    config['reservoirs']['other']=deepcopy(config['reservoirs']['Lake-α'])
    config['reservoirs']['other']['inflow_node']='other input'
    config['reservoirs']['other']['physical'].update(reservoir_id='other',dt_seconds=1800)
    config['connections'].append({'source':'other','target':'downstream outlet','unit_hydrograph':[1.]})
    with pytest.raises(ValueError,match='same|common|timestep'):
        validate_network(config)


def test_subdaily_clock_requires_unambiguous_timezone():
    config,_=fixture()
    config['start_date']='2024-02-28T23:00:00'
    with pytest.raises(ValueError,match='timezone|offset|aware'):
        validate_network(config)


@pytest.mark.parametrize('change',['gap','duplicate','reverse'])
def test_invalid_time_sequence_rejected_before_any_decision(tmp_path,change):
    config,rows=fixture()
    if change=='gap': rows.pop(1)
    elif change=='duplicate': rows[1]['date']=rows[0]['date']
    else: rows=list(reversed(rows))
    backend=FixedRelease()
    with pytest.raises(ValueError):
        run_experiment(config,rows,{'Lake-α':backend},output=tmp_path/'invalid',run_id='invalid-clock')
    assert backend.observations==[]
    assert not (tmp_path/'invalid').exists()


@pytest.mark.parametrize('start',['2024-03-10T06:00:00Z','2024-11-03T04:00:00Z'])
def test_hourly_steps_remain_exact_across_dst_dates(tmp_path,start):
    config,rows=fixture(start=start,steps=5)
    backend=FixedRelease()
    run_experiment(config,rows,{'Lake-α':backend},output=tmp_path/'dst',run_id='dst-clock')
    stamps=[datetime.fromisoformat(o['timestamp'].replace('Z','+00:00')) for o in backend.observations]
    assert all((b-a).total_seconds()==3600 for a,b in zip(stamps,stamps[1:]))
    assert verify_run(tmp_path/'dst')['status']=='PASS'


def test_spatial_rename_does_not_change_physical_results(tmp_path):
    a,rows=fixture()
    b=deepcopy(a)
    b['reservoirs']['Reservoir 99']=b['reservoirs'].pop('Lake-α')
    b['connections'][0]['source']='Reservoir 99'
    out=[]
    for name,config in [('Lake-α',a),('Reservoir 99',b)]:
        _,result=run_experiment(config,rows,{name:FixedRelease()},output=tmp_path/name,run_id='rename')
        out.append(result['summary']['final_storage_m3'][name])
        assert verify_run(tmp_path/name)['status']=='PASS'
    assert out[0]==out[1]


@pytest.mark.parametrize('dt',[900,3600,7200,86400])
def test_full_saved_outflow_tail_conserves_water_at_configured_interval(dt):
    from llm_reservoir_agent.downstream import route_saved_outflows
    config,rows=fixture(dt,steps=3)
    result=route_saved_outflows([r['date'] for r in rows],[2,4,0],[1,0,0],[1,1,1],[0,.25,.75],dt_seconds=dt)
    assert len(result['rows'])==5
    assert result['rows'][-1]['channel_storage_end_m3']==pytest.approx(0)
    assert result['volumes_input_m3']==pytest.approx(10*dt)
    assert result['output_m3']==pytest.approx(10*dt)
    assert result['initialization_steps']==2
    assert result['initialization_days']==pytest.approx(2*dt/86400)


def test_routing_kernel_frequency_mismatch_rejected():
    config,_=fixture(3600)
    config['connections'][0]['unit_hydrograph_dt_seconds']=86400
    with pytest.raises(ValueError,match='hydrograph timestep'): validate_network(config)


@pytest.mark.parametrize('dt',[True,0,-1,float('nan'),float('inf'),1e308,1e-10])
def test_invalid_step_duration_rejected(dt):
    from llm_reservoir_agent.timebase import StepClock
    with pytest.raises(ValueError):StepClock('2024-01-01T00:00:00Z',dt)
