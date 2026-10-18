"""No provider contact: settings, portable core and daily workflow acceptance."""
from copy import deepcopy
import hashlib
import importlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

import yaml

from llm_reservoir_agent.configured_audit import ConfiguredAudit
from llm_reservoir_agent.network import PROJECT_ROOT
from llm_reservoir_agent.verification import verify_run
from llm_reservoir_agent.workflow import load_settings, run_settings
from test_llm_network import network


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.prompt = self.root / "prompt.txt"
        self.prompt.write_text('$agent_id $observation $knowledge $previous_transition', encoding='utf-8')

    def tearDown(self):
        self.temp.cleanup()

    def fixture(self, count=1, mode='offline'):
        config, rows = network(count=count, days=2)
        case = self.root / 'case.json'
        case.write_text(json.dumps(dict(schema_version='llm-reservoir-network-case.v1',
                                      data_kind='synthetic_fixture', network=config, inflow_records=rows)), encoding='utf-8')
        data = dict(schema_version='llm-reservoir-experiment.v1', case='case.json', run_id=f'size-{count}',
                    output=f'run-{count}', auditors={'bounds':dict(type='release_bounds')},
                    agents={f'operator-{i}':dict(reservoir=name,mode=mode,prompt='prompt.txt',auditors=['bounds'],
                                               **({'release_cms':5} if mode=='offline' else {'model':'local'}))
                            for i,name in enumerate(config['reservoirs'])})
        if mode == 'llm':
            data['models'] = {'local':dict(provider='ollama',model='test-model',base_url='http://localhost:11434',temperature=0.7)}
            data['max_calls'] = count * 2
        return data

    def save(self, data):
        path = self.root/'experiment.yaml'
        path.write_text(yaml.safe_dump(data), encoding='utf-8')
        return path

    def test_one_three_ten_agents_other_case_names_and_offline_balance(self):
        for count in (1,3,10):
            with self.subTest(count=count):
                settings = load_settings(self.save(self.fixture(count)))
                self.assertEqual(settings.report['agent_count'], count)
                _, result = run_settings(settings)
                self.assertEqual(result['summary']['observed_network_calls'],0)
                self.assertLess(result['summary']['max_mass_balance_residual_m3'],1e-6)
                self.assertEqual(verify_run(settings.report['output'],require_offline=True)['audit_binding_counts']['versioned_suite'],count*2)

    def test_shipped_profiles_check_without_network_or_output_creation(self):
        with patch('urllib.request.urlopen', side_effect=AssertionError('network forbidden')):
            for path in (PROJECT_ROOT/'experiments').glob('*.yaml'):
                with self.subTest(profile=path.name):
                    data = yaml.safe_load(path.read_text(encoding='utf-8'))
                    original_audit = any(
                        audit.get('type') == 'dkp_strategy'
                        for audit in data.get('auditors', {}).values()
                    )
                    if original_audit and not os.environ.get('HYDROOPS_ANIK_SOURCE_DIR'):
                        # The frozen diagnostic requires the optional original
                        # source; current framework profiles must still load.
                        with self.assertRaisesRegex(RuntimeError, 'HYDROOPS_ANIK_SOURCE_DIR'):
                            load_settings(path)
                    else:
                        settings = load_settings(path)
                        self.assertEqual(settings.report['network_calls'],0)
        actual = load_settings(PROJECT_ROOT/'experiments/fe_belt_prompton.yaml')
        self.assertEqual(actual.report['agent_count'],2)
        self.assertEqual(actual.report['passive_reservoir_count'],1)
        self.assertFalse(actual.report['live_ready'])

    def test_live_opt_in_budget_and_mocked_causal_feedback(self):
        settings = load_settings(self.save(self.fixture(mode='llm')))
        transport = Mock(return_value={'message':{'content':'{"schema_version":"reservoir-action.v1","release_cms":5}'}})
        with self.assertRaises(ValueError):
            run_settings(settings,transport=transport)
        transport.assert_not_called()
        _, result = run_settings(settings,allow_network=True,transport=transport)
        self.assertEqual(transport.call_count,2)
        self.assertEqual(result['summary']['observed_network_calls'],2)
        self.assertEqual(transport.call_args_list[0].args[1]['options']['temperature'],0.7)
        first = json.dumps(transport.call_args_list[0].args[1])
        second = json.dumps(transport.call_args_list[1].args[1])
        self.assertIn('null',first)
        self.assertIn('storage_end_m3',second)
        self.assertEqual(verify_run(settings.report['output'])['audit_binding_counts']['versioned_suite'],2)

    def test_missing_duplicate_unknown_passive_and_typos_rejected(self):
        base = self.fixture(3)
        changes = []
        d=deepcopy(base);d['agents'].pop('operator-0');changes.append(d)
        d=deepcopy(base);d['agents']['operator-1']['reservoir']='R1';changes.append(d)
        d=deepcopy(base);d['agents']['operator-0']['reservoir']='unknown';changes.append(d)
        d=deepcopy(base);d['agents']['operator-0']['temperature']=0.7;changes.append(d)
        d=deepcopy(base);d['agents']['operator-0']['auditors']=['unknown'];changes.append(d)
        d=deepcopy(base);d['agents']['operator-0']['prompt']='absent';changes.append(d)
        for data in changes:
            with self.subTest(data=data),self.assertRaises((ValueError,FileNotFoundError)):
                load_settings(self.save(data))
        path=self.save(base)
        path.write_text(path.read_text()+'\nrun_id: duplicate\n',encoding='utf-8')
        with self.assertRaises(ValueError):load_settings(path)

    def test_input_drift_and_existing_output_rejected(self):
        settings = load_settings(self.save(self.fixture()))
        self.prompt.write_text('changed $observation',encoding='utf-8')
        with self.assertRaises(ValueError):run_settings(settings)
        settings=load_settings(settings.path)
        Path(settings.report['output']).mkdir()
        with self.assertRaises(FileExistsError):run_settings(settings)

    def test_real_case_not_live_ready_cannot_run_llm(self):
        original=PROJECT_ROOT/'experiments/fe_belt_prompton.yaml'
        data=yaml.safe_load(original.read_text())
        data['case']=str(PROJECT_ROOT/'cases/fe_belt_prompton_offline/case.json')
        data['models']={'local':dict(provider='ollama',model='test',base_url='http://localhost:11434')}
        data['max_calls']=14
        for a in data['agents'].values():
            a.update(mode='llm',model='local',prompt=str(PROJECT_ROOT/'templates/legacy/prompts/operator.txt'))
            a.pop('release_cms')
        settings=load_settings(self.save(data));transport=Mock()
        with self.assertRaises(ValueError):run_settings(settings,allow_network=True,transport=transport)
        transport.assert_not_called()

    def test_configured_audit_missing_target_is_unknown_and_rules_retained(self):
        plugin=ConfiguredAudit('target',dict(type='field_range',path='observation.state.target',minimum=1,maximum=3))
        self.assertEqual(plugin.audit({'observation':{'state':{}},'action':{}})['status'],'UNKNOWN')
        self.assertEqual(plugin.audit({'observation':{'state':{'target':0}},'action':{}})['status'],'FAIL')
        self.assertEqual(plugin.audit({'observation':{'state':{'target':2}},'action':{}})['status'],'PASS')

    def test_complete_bundled_core_hashes_modules_and_package_data(self):
        import hydrocnhs
        self.assertEqual(Path(hydrocnhs.__file__).resolve().parent,PROJECT_ROOT/'src/hydrocnhs')
        manifest=json.loads((PROJECT_ROOT/'third_party/hydrocnhs/SOURCE.json').read_text())
        for path,spec in manifest['files'].items():
            self.assertEqual(hashlib.sha256((PROJECT_ROOT/path).read_bytes()).hexdigest(),spec['sha256'],path)
        for module in ('calibration','model_builder','routing','rainfall_runoff_model.gwlf',
                       'rainfall_runoff_model.abcd','rainfall_runoff_model.pet_hamon','water_quality_model.sediment'):
            importlib.import_module('hydrocnhs.'+module)
        self.assertTrue((Path(hydrocnhs.__file__).parent/'Config_logging.yaml').is_file())

    def test_external_region_names_prompt_bindings_and_insufficient_budget(self):
        data=self.fixture(3)
        case=self.root/'case.json'
        original=json.loads(case.read_text())
        names={'R1':'AlpineDam','R2':'CityReservoir','R3':'CoastalPool'}
        cfg=original['network']
        cfg['reservoirs']={names[k]:v for k,v in cfg['reservoirs'].items()}
        for edge in cfg['connections']:
            edge['source']=names.get(edge['source'],edge['source'])
            edge['target']=names.get(edge['target'],edge['target'])
        case.write_text(json.dumps(original),encoding='utf-8')
        for a in data['agents'].values():a['reservoir']=names[a['reservoir']]
        settings=load_settings(self.save(data))
        self.assertEqual(set(settings.report['agent_reservoirs'].values()),set(names.values()))
        _,result=run_settings(settings)
        self.assertEqual(result['summary']['observed_network_calls'],0)
        self.assertEqual(verify_run(settings.report['output'],require_offline=True)['audit_binding_counts']['versioned_suite'],6)
        live=self.fixture(3,'llm');live['max_calls']=5
        with self.assertRaises(ValueError):load_settings(self.save(live))

    def test_passive_assignment_unknown_placeholder_and_unsafe_yaml_rejected(self):
        data=yaml.safe_load((PROJECT_ROOT/'experiments/fe_belt_prompton.yaml').read_text())
        data['case']=str(PROJECT_ROOT/'cases/fe_belt_prompton_offline/case.json')
        for a in data['agents'].values():a['prompt']=str(self.prompt)
        data['agents']['passive']=dict(reservoir='Prompton',mode='offline',release_cms=1,prompt=str(self.prompt))
        with self.assertRaises(ValueError):load_settings(self.save(data))
        self.prompt.write_text('$unknown_placeholder',encoding='utf-8')
        with self.assertRaises(KeyError):load_settings(self.save(self.fixture()))
        path=self.root/'unsafe.yaml';path.write_text('!!python/object/apply:os.system [echo forbidden]',encoding='utf-8')
        with self.assertRaises(yaml.constructor.ConstructorError):load_settings(path)


if __name__=='__main__':unittest.main()
