"""Independent source-window and common-engine checks for benchmark YAML."""
import json
from pathlib import Path
import tempfile

import pytest
import yaml

from llm_reservoir_agent.benchmark_config import calculate_statistics
from llm_reservoir_agent.workflow import load_settings,run_settings
from llm_reservoir_agent.verification import verify_run

ROOT=Path(__file__).resolve().parents[1]
EXAMPLE=ROOT/'tests/fixtures/fe_walter_current/benchmark.yaml'
STATS=ROOT/'data/benchmark/fe_walter_statistics.json'


def temporary_yaml(folder, mutation=None, statistics=None):
    data=yaml.safe_load(EXAMPLE.read_text())
    data['case']=str(ROOT/'tests/fixtures/cases/fe_walter_reference/case.json')
    data['output']=str(folder/'output')
    # Preserve this suite's explicit legacy-engine compatibility regression.
    # Public rule registration and parity are covered in test_public_examples.
    public = data['agents']['fe_operator']
    parameters = public['rule_parameters']
    data['agents']['fe_operator'] = {
        'reservoir': public['reservoir_id'], 'mode': 'offline', 'strategy': 'benchmark',
        'benchmark': {'statistics': parameters['inflow_statistics_file'],
                      **{key: value for key, value in parameters.items()
                         if key != 'inflow_statistics_file'}},
        'auditors': public.get('auditors', [])}
    data.pop('extensions', None)
    data['agents']['fe_operator']['benchmark']['statistics']=str(STATS)
    if statistics is not None:
        blob=json.loads(STATS.read_text())
        blob['source']['path']=str(ROOT/'data/accepted/fe_walter_inflow_reference_1996_2025.csv.gz')
        statistics(blob)
        path=folder/'stats.json'
        path.write_text(json.dumps(blob))
        data['agents']['fe_operator']['benchmark']['statistics']=str(path)
    if mutation:
        mutation(data)
    path=folder/'experiment.yaml'
    path.write_text(yaml.safe_dump(data))
    return path


def test_benchmark_uses_common_native_engine_without_network():
    with tempfile.TemporaryDirectory() as temp:
        config=temporary_yaml(Path(temp))
        settings=load_settings(config)
        assert settings.report['planned_llm_calls']==0
        assert settings.report['days']==3
        assert settings.report['agent_strategies']=={'fe_operator':'benchmark'}
        def forbidden(*args,**kwargs):
            raise AssertionError('offline benchmark attempted a real transport')
        run_settings(settings,transport=forbidden)
        result=json.loads((Path(settings.report['output'])/'summary.json').read_text())
        assert result['summary']['hydrology_recomputed'] is False
        verified=verify_run(settings.report['output'])
        assert verified['status']=='PASS'
        assert verified['observed_network_calls']==0
        assert verified['max_system_balance_residual_m3']<1e-6
        assert verified['max_routing_difference_cms']==0
        assert verified['audit_binding_counts']=={'versioned_suite':3,'legacy_unbound':0}


@pytest.mark.parametrize('mutation,fragment',[
 (lambda d:d.update(reference_end='2016-01-01'),'precede'),
 (lambda d:d.update(reservoir_id='other_reservoir'),'another reservoir'),
 (lambda d:d.update(mean_inflow_cms=99),'mean does not match'),
 (lambda d:d['monthly_mean_inflow_cms'].pop('12'),'twelve'),
 (lambda d:d['source'].update(sha256='0'*64),'checksum'),
 (lambda d:d.update(reference_day_count=True),'day count'),
])
def test_statistics_errors_stop_during_check(mutation,fragment):
    with tempfile.TemporaryDirectory() as temp:
        path=temporary_yaml(Path(temp),statistics=mutation)
        with pytest.raises(ValueError,match=fragment):
            load_settings(path)
        assert not (Path(temp)/'output').exists()


@pytest.mark.parametrize('field,value', [('mode','llm'),('model','unconfigured'),('prompt','anything'),('release_cms',1)])
def test_benchmark_rejects_provider_or_fallback_settings(field,value):
    with tempfile.TemporaryDirectory() as temp:
        path=temporary_yaml(Path(temp),mutation=lambda d:d['agents']['fe_operator'].update({field:value}))
        with pytest.raises(ValueError,match='deterministic/offline'):
            load_settings(path)


def test_reference_statistics_use_only_the_pre_run_window():
    data=json.loads(STATS.read_text())
    source=(STATS.parent/data['source']['path']).resolve()
    computed=calculate_statistics(source,data['source'],data['reference_start'],data['reference_end'])
    assert computed['reference_day_count']==7305
    assert computed['mean_inflow_cms']==pytest.approx(18.25446484681121)
    # An intentionally incomplete declared interval cannot be silently shortened.
    with pytest.raises(ValueError,match='every declared day'):
        calculate_statistics(source,data['source'],'1995-12-31','2015-12-31')
