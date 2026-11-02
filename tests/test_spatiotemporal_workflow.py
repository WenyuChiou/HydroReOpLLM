"""Configured clock/space integration, with injected responses and no live model."""
from copy import deepcopy
from datetime import datetime, timedelta
import csv
import hashlib
import json
from unittest.mock import patch

import pytest
import yaml

from llm_reservoir_agent.case import load_case, RecordedResponseBackend
from llm_reservoir_agent.workflow import load_settings, run_settings
from llm_reservoir_agent.verification import verify_run
from llm_reservoir_agent.timebase import StepClock
from test_spatiotemporal_generic import fixture, FixedRelease
from test_llm_network import network


def configuration(folder, *, live=False, dt=3600):
    config, rows = fixture(dt, steps=9)
    (folder/'case.json').write_text(json.dumps(dict(schema_version='llm-reservoir-network-case.v1',
        data_kind='synthetic_fixture', network=config, inflow_records=rows)), encoding='utf-8')
    (folder/'prompt.txt').write_text('$observation $information $previous_transition',encoding='utf-8')
    data=dict(schema_version='llm-reservoir-experiment.v1',case='case.json',run_id='arbitrary-case',output='run',
        max_calls=12 if live else 0,
        information_sources={'gauge':dict(type='simulation',quantity='flow',unit='m3/s',location='downstream outlet')},
        information_profiles={'context':dict(fields={'downstream':dict(source='gauge',history=7,required=False)})},
        agents={'operator':dict(reservoir='Lake-α', mode='llm' if live else 'offline',prompt='prompt.txt',
                               information='context',**({'model':'local'} if live else {'release_cms':5}))})
    if live:
        data['models']={'local':dict(provider='ollama',model='injected-fixture',base_url='http://localhost:11434')}
    return data,config,rows


def save(folder,data):
    target=folder/'experiment.yaml'
    target.write_text(yaml.safe_dump(data,allow_unicode=True),encoding='utf-8')
    return load_settings(target)


def reply():
    return dict(done=True,done_reason='stop',message={'content':json.dumps(dict(schema_version='reservoir-action.v1',release_cms=5))})


def test_hourly_information_seven_samples_and_causal_availability(tmp_path):
    data,_,rows=configuration(tmp_path)
    settings=save(tmp_path,data)
    records,result=run_settings(settings)
    field=[r['observation']['context']['decision_information']['fields']['downstream'] for r in records['Lake-α']]
    assert field[0]['status']=='MISSING'
    assert field[1]['available_at']=='2024-02-29T00:00:00Z'
    assert len(field[-1]['history'])==7
    samples=field[-1]['history']
    stamps=[datetime.fromisoformat(s['valid_time'].replace('Z','+00:00')) for s in samples]
    assert all((b-a).total_seconds()==3600 for a,b in zip(stamps,stamps[1:]))
    assert result['summary']['steps']==9
    assert result['summary']['days']==9/24
    assert verify_run(settings.report['output'],require_offline=True)['status']=='PASS'


def test_yaml_window_uses_instants_and_preview_is_valid_iso(tmp_path):
    data,_,rows=configuration(tmp_path)
    data.update(start_date='2024-02-29T01:00:00+01:00',end_date='2024-02-29T04:00:00Z')
    settings=save(tmp_path,data)
    assert len(settings.rows)==5
    assert settings.rows[0]['date']=='2024-02-29T00:00:00+00:00'
    assert settings.report['start']==settings.rows[0]['date']
    assert settings.report['end_exclusive']=='2024-02-29T05:00:00+00:00'
    records,result=run_settings(settings)
    assert records['Lake-α'][0]['observation']['timestamp']==settings.rows[0]['date']
    assert verify_run(settings.report['output'])['steps']==5


@pytest.mark.parametrize('bad',['2024-02-29T00:30:00Z','2024-03-01T00:00:00Z','2024-02-29'])
def test_invalid_window_rejected_before_provider(tmp_path,bad):
    data,_,_=configuration(tmp_path,live=True)
    data['start_date']=bad
    with pytest.raises(ValueError): save(tmp_path,data)
    assert not (tmp_path/'run').exists()


def test_hourly_full_configured_provider_payload_and_recovery(tmp_path):
    from llm_reservoir_agent.recovery import resume_settings
    data,_,_=configuration(tmp_path,live=True)
    settings=save(tmp_path,data)
    payloads=[]
    def interrupted(url,payload,headers,timeout):
        payloads.append(deepcopy(payload))
        if len(payloads)==3: raise TimeoutError('injected interruption')
        return reply()
    with patch('urllib.request.urlopen',side_effect=AssertionError('real network forbidden')):
        with pytest.raises(TimeoutError): run_settings(settings,allow_network=True,transport=interrupted)
        before={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (tmp_path/'run').iterdir() if p.is_file()}
        sent=[]
        def resumed(url,payload,headers,timeout):
            sent.append(payload)
            return reply()
        records,result=resume_settings(settings,tmp_path/'run',output=tmp_path/'resumed',run_id='resumed',
                                      allow_network=True,transport=resumed)
    assert len(sent)==7  # Two saved completed hours replayed without HTTP.
    assert len(records['Lake-α'])==9
    assert before=={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (tmp_path/'run').iterdir() if p.is_file()}
    assert verify_run(tmp_path/'resumed')['status']=='PASS'


@pytest.mark.parametrize('form',['daily-node-local-cms.v1','step-node-local-cms.v1'])
def test_pinned_csv_frequency_contract(tmp_path,form):
    _,config,rows=configuration(tmp_path)
    source=tmp_path/'inflow.csv'
    with source.open('w',newline='',encoding='utf-8') as handle:
        writer=csv.writer(handle);writer.writerow(['date','node','local_inflow_cms'])
        for row in rows:
            for node,q in row['local_inflow_cms'].items():writer.writerow([row['date'],node,q])
    case=dict(schema_version='llm-reservoir-network-case.v1',data_kind='synthetic_fixture',network=config,
        inflow_source=dict(path=source.name,sha256=hashlib.sha256(source.read_bytes()).hexdigest(),format=form))
    target=tmp_path/'pinned.json';target.write_text(json.dumps(case),encoding='utf-8')
    if form.startswith('daily'):
        with pytest.raises(ValueError,match='daily timestep'): load_case(target,project_root=tmp_path)
    else:
        actual,loaded=load_case(target,project_root=tmp_path)
        assert loaded==rows


def test_recorded_response_does_not_confuse_hours_of_same_day():
    backend=RecordedResponseBackend([dict(date='2024-01-01T01:00:00Z',release_cms=2)],
                                    data_kind='synthetic_fixture',source_sha256='0'*64)
    with pytest.raises(ValueError,match='differs'):
        backend.decide(dict(timestep=0,timestamp='2024-01-01T02:00:00+00:00',state={'dt_seconds':3600}))


def test_daily_csv_external_passive_rating_is_resolved_before_validation(tmp_path):
    _,config,rows=configuration(tmp_path,dt=86400)
    rating=dict(schema_version='passive-storage-discharge.v1',storage_m3=[0.,20_000_000.],
                discharge_cms=[0.,100.],provenance={'data_kind':'synthetic_fixture'})
    source=tmp_path/'rating.json';source.write_text(json.dumps(rating),encoding='utf-8')
    spec=config['reservoirs']['Lake-α']
    spec.update(operation_mode='passive_outlet',passive_outlet_source=dict(path=source.name,
                sha256=hashlib.sha256(source.read_bytes()).hexdigest()))
    inflow=tmp_path/'daily.csv'
    with inflow.open('w',newline='',encoding='utf-8') as handle:
        writer=csv.writer(handle);writer.writerow(['date','node','local_inflow_cms'])
        for row in rows:
            for node,q in row['local_inflow_cms'].items():writer.writerow([row['date'],node,q])
    target=tmp_path/'passive-case.json'
    target.write_text(json.dumps(dict(schema_version='llm-reservoir-network-case.v1',
        data_kind='synthetic_fixture',network=config,inflow_source=dict(path=inflow.name,
        format='daily-node-local-cms.v1',sha256=hashlib.sha256(inflow.read_bytes()).hexdigest()))),encoding='utf-8')
    loaded,actual=load_case(target,project_root=tmp_path)
    assert loaded['reservoirs']['Lake-α']['passive_outlet']==rating
    assert actual==rows


@pytest.mark.parametrize('dt',[900,3600,7200])
@pytest.mark.parametrize('shape',[dict(count=1),dict(count=3),dict(count=3,branch=True),dict(count=12)])
def test_arbitrary_multireservoir_topologies_use_configured_step(tmp_path,dt,shape):
    from llm_reservoir_agent.experiment import run_experiment
    config,rows=network(days=5,**shape)
    config['start_date']='2024-12-31T23:00:00Z'
    clock=StepClock(config['start_date'],dt)
    for spec in config['reservoirs'].values():spec['physical']['dt_seconds']=dt
    for t,row in enumerate(rows):row['date']=clock.label(t)
    _,result=run_experiment(config,rows,{name:FixedRelease() for name in config['reservoirs']},
                            output=tmp_path/'network',run_id='arbitrary-network')
    assert result['summary']['steps']==5
    assert verify_run(tmp_path/'network',require_offline=True)['status']=='PASS'


@pytest.mark.parametrize('dt',[900,3600])
@pytest.mark.parametrize('passive',[False,True])
def test_hourly_independent_components_and_passive_outlet(tmp_path,dt,passive):
    from test_network_outlets import reservoir_forest
    from llm_reservoir_agent.experiment import run_experiment
    config,rows=reservoir_forest(passive=passive)
    clock=StepClock('2025-07-01T00:00:00Z',dt)
    config['start_date']=clock.label(0)
    for spec in config['reservoirs'].values():spec['physical']['dt_seconds']=dt
    for t,row in enumerate(rows):row['date']=clock.label(t)
    backends={name:FixedRelease() for name,spec in config['reservoirs'].items()
              if spec.get('operation_mode')!='passive_outlet'}
    _,result=run_experiment(config,rows,backends,output=tmp_path/'forest',run_id='forest')
    assert result['summary']['component_count']==2
    assert verify_run(tmp_path/'forest',require_offline=True)['status']=='PASS'


def test_native_daily_weather_does_not_silently_become_hourly(tmp_path):
    from llm_reservoir_agent.coupled import load_coupled_settings
    _,config,_=configuration(tmp_path)
    target=tmp_path/'physical.json'
    target.write_text(json.dumps(dict(schema_version='reservoir-physical-case.v1',network=config,
                                     data_kind='synthetic_fixture')),encoding='utf-8')
    document=dict(schema_version='hydroops-coupled-simulation.v1',case=target.name,
                  run_id='invalid-subdaily-runoff',output='bad-weather',hydrology={})
    path=tmp_path/'weather.yaml';path.write_text(yaml.safe_dump(document),encoding='utf-8')
    with patch('llm_reservoir_agent.coupled.load_weather',side_effect=AssertionError('no native runoff')):
        with pytest.raises(ValueError,match='daily hydrology only'):load_coupled_settings(path)
