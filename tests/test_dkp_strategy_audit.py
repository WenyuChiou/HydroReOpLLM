"""Offline evidence for DKP wiring; fixture targets are never operational targets."""
import hashlib
import json
from unittest.mock import Mock

import pytest
import yaml

from llm_reservoir_agent.auditor import AuditedBackend
from llm_reservoir_agent.configured_backend import ConfiguredBackend
from llm_reservoir_agent.context import ContextValue
from examples.fe_walter.extensions.dkp_audit import (
    AF_TO_M3, CFS_TO_CMS, DKP_MODES, DKP_RESPONSE_SCHEMA, DKPStrategyAudit, validate_dkp_decision,
)
from llm_reservoir_agent.network import PROJECT_ROOT
from llm_reservoir_agent.prompt import PromptSpec
from llm_reservoir_agent.verification import verify_run
from llm_reservoir_agent.workflow import load_settings, run_settings


DKP = PROJECT_ROOT / 'examples/fe_walter/knowledge/DKP_FEWalter_Dam_v1.2.md'
CURVE = PROJECT_ROOT / 'cases/fe_belt_prompton_offline/fe_walter_storage_elevation.csv'
CONFIG = PROJECT_ROOT / 'experiments/fe_walter_dkp_offline.yaml'



def _pin_example_extension(data):
    # This test copies FE Walter configuration into a disposable directory.
    if data.get("extensions"):
        data["extensions"] = {key: str(PROJECT_ROOT / "examples/fe_walter/extensions/__init__.py") for key in data["extensions"]}
    return data

def observation():
    return dict(schema_version='reservoir-observation.v1', timestep=0,
                timestamp='2015-10-01T00:00:00', inflow_cms=3.0, release_upper_bound_cms=28.0,
                state=dict(storage_m3=1793 * AF_TO_M3, capacity_m3=135199473.1344,
                           dead_storage_m3=11101.3362, minimum_release_cms=1.4158423296,
                           maximum_release_cms=283.16846592, dt_seconds=86400.0),
                context=dict(reservoir_id='arbitrary_reservoir'))


def plugin(tmp_path, *, target=True, required=None):
    profile = json.loads((PROJECT_ROOT / 'cases/fe_walter_dkp_offline/audit_profile.json').read_bytes())
    profile['curve_source']['path'] = str(CURVE)
    profile['required_inputs'] = [] if required is None else required
    if target:
        profile['targets_by_date'] = {'2015-10-01':dict(elevation_ft=1340.0,
                                                      source='synthetic audit test only', verified=True)}
    path = tmp_path / 'audit_profile.json'
    path.write_text(json.dumps(profile), encoding='utf-8')
    return DKPStrategyAudit('dkp', dict(type='dkp_strategy', knowledge_id='rules', profile=str(path)),
                            base_path=tmp_path, knowledge_paths={'rules':DKP}, project_root=PROJECT_ROOT)


def decision(release=1.5, mode='store_toward_target', **changes):
    result = dict(schema_version=DKP_RESPONSE_SCHEMA, release_cms=release, operating_mode=mode,
                  rules_applied=['R-RELEASE'], missing_inputs=[], reasoning='Synthetic test reasoning.',
                  applicable_target_ft=1340.0, pool_position='below_target',
                  intended_storage_direction='increase' if release < 3 else 'hold' if release == 3 else 'decrease',
                  release_relation_to_inflow='below_inflow' if release < 3 else 'equal_to_inflow' if release == 3 else 'above_inflow')
    result.update(changes)
    return result


def context(checker, reply=None):
    obs = observation()
    return dict(observation=obs, action=dict(schema_version='reservoir-action.v1', release_cms=(reply or {}).get('release_cms',5)),
                backend_trace=dict(audit_contexts={'dkp':checker.prepare_context(obs)},
                                   **({} if reply is None else dict(decision_metadata=reply))))


@pytest.mark.parametrize('release,mode', [(1.5,'store_toward_target'),(5,'store_toward_target'),(3,'pass_inflow')])
def test_frozen_rubric_exact_parity_and_no_network(tmp_path, release, mode):
    checker = plugin(tmp_path)
    data = context(checker, decision(release,mode))
    result = checker.audit(data)
    from dkp_llm_release import DKPLLMPolicy
    from zeroshot_llm_release import ReservoirBasicInfo
    import pandas as pd
    info = ReservoirBasicInfo(name='arbitrary_reservoir', purpose=checker.profile['purpose'],
                              capacity_af=observation()['state']['capacity_m3']/AF_TO_M3,
                              min_release_cfs=1.4158423296/CFS_TO_CMS,
                              max_release_cfs=283.16846592/CFS_TO_CMS, prompt_storage=True)
    original = DKPLLMPolicy(info=info, backend=None, dkp_path=DKP, log_path=None, trace_path=None,
                            sample_path=None, max_audit_revisions=0, target_tolerance_ft=0.5)
    runtime = checker.prepare_context(observation())
    day = pd.Timestamp(observation()['timestamp'])
    original._retrieve_operational_sections(day,'',runtime)
    expected = original._audit_decision(day,data['backend_trace']['decision_metadata'],release/CFS_TO_CMS,
                                        release/CFS_TO_CMS,3/CFS_TO_CMS,observation()['state']['storage_m3']/AF_TO_M3,runtime)
    assert result['legacy_audit'] == expected
    assert result['status'] == expected['audit_status']
    assert result['operating_strategy_accepted'] is None
    assert checker.network_calls == 0
    if release == 1.5:
        assert result['status'] == 'PASS'
    else:
        assert result['status'] == 'FAIL'


def test_missing_metadata_or_target_is_unknown_known_fail_kept(tmp_path):
    checker = plugin(tmp_path,target=False,required=['annual_plan'])
    assert checker.audit(context(checker))['status'] == 'UNKNOWN'
    result = checker.audit(context(checker,decision(applicable_target_ft=None,pool_position='unknown')))
    assert result['status'] == 'UNKNOWN'
    assert 'dated_operating_target' in result['reasons']
    assert result['legacy_audit'] is not None
    assert checker.audit(context(checker,decision(5,applicable_target_ft=None,pool_position='unknown')))['status'] == 'FAIL'
    assert checker.audit(context(checker,decision()))['integration_failures']==['model_declared_target_without_supplied_dated_target']


def test_unverified_target_and_unsupported_losses_remain_unknown(tmp_path):
    checker = plugin(tmp_path)
    path = tmp_path/'audit_profile.json'
    data=json.loads(path.read_bytes());data['targets_by_date']['2015-10-01']['verified']=False
    path.write_text(json.dumps(data),encoding='utf-8')
    checker=plugin_from_path(path)
    result=checker.audit(context(checker,decision()))
    assert result['status']=='UNKNOWN'
    assert 'verified_dated_operating_target' in result['reasons']
    obs=observation();obs['context']['evaporation_m3']=100
    assert 'legacy_preview_does_not_include_reservoir_losses' in checker.prepare_context(obs)['runtime_missing_inputs']


def plugin_from_path(path):
    return DKPStrategyAudit('dkp',dict(type='dkp_strategy',knowledge_id='rules',profile=str(path)),
                            base_path=path.parent,knowledge_paths={'rules':DKP},project_root=PROJECT_ROOT)


def test_context_spoof_and_action_metadata_mismatch_rejected(tmp_path):
    checker=plugin(tmp_path);data=context(checker,decision())
    data['backend_trace']['audit_contexts']['dkp']['seasonal_target_ft']=1370
    with pytest.raises(ValueError,match='context does not match'):checker.audit(data)
    data=context(checker,decision());data['action']['release_cms']=7
    with pytest.raises(ValueError,match='differs from'):checker.audit(data)
    data=context(checker,decision());data['backend_trace']['audit_contexts']={}
    assert checker.audit(data)['status']=='UNKNOWN'


@pytest.mark.parametrize('change', ['profile','points','file','spec'])
def test_auditor_drift_stops_before_a_decision(tmp_path,change):
    checker=plugin(tmp_path)
    if change=='profile':checker.profile['target_tolerance_ft']=100
    elif change=='points':checker.points=checker.points[1:]
    elif change=='spec':checker.spec.rubric['stage']='changed'
    else:(tmp_path/'audit_profile.json').write_text('{}',encoding='utf-8')
    with pytest.raises(ValueError,match='changed'):checker.prepare_context(observation())


def test_curve_domain_daily_step_checksum_and_duplicate_profile(tmp_path):
    checker=plugin(tmp_path);obs=observation();obs['state']['storage_m3']=0
    assert checker.prepare_context(obs)['pool_elevation_ft'] is None
    obs=observation();obs['state']['dt_seconds']=3600
    with pytest.raises(ValueError,match='daily'):checker.prepare_context(obs)
    path=tmp_path/'audit_profile.json';data=json.loads(path.read_bytes())
    data['curve_source']['sha256']='0'*64;path.write_text(json.dumps(data),encoding='utf-8')
    with pytest.raises(ValueError,match='checksum'):plugin_from_path(path)
    path.write_text('{"schema_version":"a","schema_version":"b"}',encoding='utf-8')
    with pytest.raises(ValueError,match='duplicate'):plugin_from_path(path)


@pytest.mark.parametrize('change', [dict(extra=1),dict(missing_inputs='none'),dict(reasoning=''),
                                  dict(release_cms=True),dict(rules_applied=[]),dict(schema_version='reservoir-action.v1'),
                                  dict(operating_mode='pass_inflow_typo')])
def test_strict_ten_field_response_rejects_bad_metadata(change):
    with pytest.raises((TypeError,ValueError)):validate_dkp_decision(decision(**change))


@pytest.mark.parametrize('mode',sorted(DKP_MODES))
def test_all_eight_frozen_modes_are_valid_schema_values(mode):
    assert validate_dkp_decision(decision(mode=mode))['operating_mode']==mode


def test_mock_reply_prompt_audit_context_and_original_payload_match(tmp_path):
    checker=plugin(tmp_path)
    knowledge=DKP.read_text(encoding='utf-8')
    prompt=PromptSpec('test','1','$observation $knowledge $dkp_context $previous_transition',('rules',),
                       {'rules':hashlib.sha256(knowledge.encode()).hexdigest()})
    transport=Mock(return_value={'message':{'content':json.dumps(decision())}})
    backend=ConfiguredBackend(agent_id='test',mode='llm',prompt_spec=prompt,knowledge_texts={'rules':knowledge},
                              model=dict(provider='ollama',model='mock-only',base_url='http://localhost:11434',temperature=0.7),
                              response_schema=DKP_RESPONSE_SCHEMA,response_extension=__import__(
                                  'examples.fe_walter.extensions', fromlist=['parse_response']),
                              prompt_variables={'dkp_context': lambda ctx: ContextValue(
                                  checker.prepare_context(ctx.observation), {'source': 'dkp-audit-test'})},
                              audit_context_builders={'dkp':checker.prepare_context},
                              transport=transport)
    wrapped=AuditedBackend(backend,[checker]);action=wrapped.decide(observation())
    assert action==dict(schema_version='reservoir-action.v1',release_cms=1.5)
    assert backend.latest_trace['decision_metadata']==decision()
    assert backend.latest_trace['audit_contexts']['dkp']==checker.prepare_context(observation())
    content=transport.call_args.args[1]['messages'][-1]['content']
    assert 'seasonal_target_storage_af' in content and '1340.0' in content
    assert transport.call_args.args[1]['options']['temperature']==0.7
    assert wrapped.latest_audit['status']=='PASS'
    # This counter counts the injected transport invocation, not an actual HTTP call.
    assert transport.call_count==1


def test_mode_typo_stops_mock_reply_before_physical_action(tmp_path):
    checker=plugin(tmp_path)
    knowledge=DKP.read_text(encoding='utf-8')
    prompt=PromptSpec('test','1','$observation $knowledge',('rules',),
                       {'rules':hashlib.sha256(knowledge.encode()).hexdigest()})
    transport=Mock(return_value={'message':{'content':json.dumps(decision(mode='pass_inflow_typo'))}})
    backend=ConfiguredBackend(agent_id='test',mode='llm',prompt_spec=prompt,knowledge_texts={'rules':knowledge},
                              model=dict(provider='ollama',model='mock-only',base_url='http://localhost:11434'),
                              response_schema=DKP_RESPONSE_SCHEMA,response_extension=__import__(
                                  'examples.fe_walter.extensions', fromlist=['parse_response']),
                              audit_context_builders={'dkp':checker.prepare_context},
                              transport=transport)
    wrapped=AuditedBackend(backend,[checker])
    with pytest.raises(ValueError,match='eight frozen'):wrapped.decide(observation())
    assert wrapped.latest_audit is None
    assert wrapped.latest_trace['audit_execution']['status']=='FAILED'
    assert backend.latest_trace['parsed_action'] is None
    assert transport.call_count==1


def test_invented_citation_neutral_claim_and_clipped_preview_are_visible(tmp_path):
    checker=plugin(tmp_path)
    original=observation()
    assert checker.audit(context(checker,decision(rules_applied=['invented'])))['status']=='FAIL'
    result=checker.audit(context(checker,decision(pool_position='above_target')))
    assert any('pool_position' in r for r in result['legacy_audit']['policy_failures'])
    result=checker.audit(context(checker,decision(500,mode='post_flood_drawdown')))
    assert result['status']=='FAIL'
    assert result['projected_controlled_release_cms']==28
    assert result['legacy_audit']['hard_physics_failures']
    assert observation()==original  # Diagnostic does not implement release or update storage.


def external_config(tmp_path):
    data=yaml.safe_load(CONFIG.read_text(encoding='utf-8'))
    base=CONFIG.parent
    for key in ('case','output'):data[key]=str((base/data[key]).resolve())
    data['output']=str(tmp_path/'run')
    for a in data['agents'].values():
        for key in ('prompt','context_file'):a[key]=str((base/a[key]).resolve())
        a['knowledge']={k:str((base/v).resolve()) for k,v in a['knowledge'].items()}
    data['auditors']['dkp_strategy']['profile']=str((base/data['auditors']['dkp_strategy']['profile']).resolve())
    return data


def save(tmp_path,data):
    path=tmp_path/'experiment.yaml';path.write_text(yaml.safe_dump(_pin_example_extension(data)),encoding='utf-8');return path


def test_seven_daily_steps_keep_bounds_pass_and_dkp_unknown_offline(tmp_path):
    data=external_config(tmp_path);settings=load_settings(save(tmp_path,data))
    assert settings.report['live_ready'] is False
    transport=Mock(side_effect=AssertionError('real network forbidden'))
    _,result=run_settings(settings,transport=transport)
    transport.assert_not_called()
    assert result['summary']['observed_network_calls']==0
    assert result['summary']['max_mass_balance_residual_m3'] < 1e-6
    verified=verify_run(settings.report['output'],require_offline=True)
    assert verified['audit_binding_counts']['versioned_suite']==7
    for raw in (tmp_path/'run/raw').glob('policy_*.json'):
        text=raw.read_text(encoding='utf-8')
        assert '"model_used":false' in text.replace(' ','').replace('\n','')
    audits=[json.loads(line) for line in (tmp_path/'run/audit.jsonl').read_text(encoding='utf-8').splitlines()]
    assert len(audits)==7
    assert all(row['status']=='UNKNOWN' for row in audits)
    for row in audits:
        payload=json.loads((tmp_path/'run'/row['original_payload_ref']['path']).read_bytes())
        by_id={c['auditor_spec']['auditor_id']:c['payload'] for c in payload['components']}
        assert by_id['release_limits']['status']=='PASS'
        assert 'structured_DKP_decision' in by_id['dkp_strategy']['reasons']


def test_real_case_live_blocked_and_dkp_schema_requires_context_and_knowledge(tmp_path):
    data=external_config(tmp_path)
    a=data['agents']['fe_operator'];a['mode']='llm';a.pop('release_cms');data['max_calls']=7
    transport=Mock()
    settings=load_settings(save(tmp_path,data))
    with pytest.raises(ValueError,match='live-ready'):run_settings(settings,allow_network=True,transport=transport)
    transport.assert_not_called()
    a['auditors']=['release_limits']
    with pytest.raises(ValueError,match='requires a configured'):load_settings(save(tmp_path,data))
    a['auditors']=['release_limits','dkp_strategy'];a['knowledge']={}
    with pytest.raises(ValueError,match='knowledge_id'):load_settings(save(tmp_path,data))
    a['knowledge']={'fe_walter_dkp':str(DKP)}
    prompt=tmp_path/'bad_prompt.txt';prompt.write_text('$knowledge',encoding='utf-8');a['prompt']=str(prompt)
    with pytest.raises(ValueError,match='placeholders'):load_settings(save(tmp_path,data))


@pytest.mark.parametrize('count',[1,3,10])
def test_dkp_assignment_works_with_arbitrary_reservoir_counts_and_names(tmp_path,count):
    from test_llm_network import network
    config,rows=network(count=count,days=2)
    case=tmp_path/'case.json'
    case.write_text(json.dumps(dict(schema_version='llm-reservoir-network-case.v1',
                                    data_kind='synthetic_fixture',network=config,inflow_records=rows)),encoding='utf-8')
    data=external_config(tmp_path);data['case']=str(case)
    original=data['agents']['fe_operator']
    data['agents']={f'region_operator_{i}':dict(original,reservoir=name) for i,name in enumerate(config['reservoirs'])}
    data.pop('start_date');data.pop('end_date')
    settings=load_settings(save(tmp_path,data));transport=Mock()
    _,result=run_settings(settings,transport=transport)
    transport.assert_not_called()
    assert result['summary']['observed_network_calls']==0
    assert verify_run(settings.report['output'],require_offline=True)['audit_binding_counts']['versioned_suite']==count*2
