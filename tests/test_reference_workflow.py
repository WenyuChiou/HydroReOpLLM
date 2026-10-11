"""Original-policy parity and reference YAML acceptance, without providers."""
from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd
import yaml

from delaware_operations.anik_adapter import load_anik
from llm_reservoir_agent.network import PROJECT_ROOT
from llm_reservoir_agent.reference_backend import ReferenceBackend, _FixtureTransport
from llm_reservoir_agent.verification import verify_run
from llm_reservoir_agent.workflow import load_settings, run_settings


class ReferenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.network_guard = patch('urllib.request.urlopen', side_effect=AssertionError('network forbidden'))
        self.network_guard.start()

    def tearDown(self):
        self.network_guard.stop()
        self.temp.cleanup()

    def fixture(self, method):
        path = PROJECT_ROOT / f'experiments/fe_walter_reference_{method}.yaml'
        data = yaml.safe_load(path.read_text(encoding='utf-8'))
        data['case'] = str((path.parent / data['case']).resolve())
        data['output'] = str(self.root / f'run-{method}')
        spec = data['agents']['fe_operator']['reference']
        for key in ('responses', 'dkp'):
            if key in spec:
                spec[key] = str((path.parent / spec[key]).resolve())
        return data

    def save(self, data):
        path = self.root / 'experiment.yaml'
        path.write_text(yaml.safe_dump(data), encoding='utf-8')
        return path

    def backend(self, method):
        settings = load_settings(self.save(self.fixture(method)))
        spec = settings.agents['fe_operator']['reference']
        physics = settings.network['reservoirs']['FEWalter']['physical']
        return ReferenceBackend(spec, physics, runtime_root=PROJECT_ROOT)

    def test_system_info_and_state_prompt_match_original_factory(self):
        model = load_anik(PROJECT_ROOT)
        zero = sys.modules['zeroshot_llm_release']
        cfg = next(c for c in model.RESERVOIRS if c.inflow_reservoir_key == 'fe_walter')
        cfg = replace(cfg, dkp_path=str(PROJECT_ROOT/'data/anik_v3_7/DKP_FEWalter_Dam_v1.2.md'))
        for method in ('zeroshot', 'dkp'):
            with self.subTest(method=method):
                adapter = self.backend(method)
                transport = _FixtureTransport([])
                with patch.object(model, 'RESULTS_DIR', self.root), patch.object(model, 'LLM_BACKENDS',
                        {'fixture': ('zeroshot_llm_release', 'ReferenceFixture', {})}), patch.object(
                        zero, 'ReferenceFixture', lambda: transport, create=True):
                    original = model.build_policy(cfg, method, 'fixture', pd.Series(dtype=float),
                        prompt_storage=False, hide_availability_line=True, dkp_no_missing_inputs=True,
                        dkp_audit_action='record', zeroshot_audit_action='record')
                self.assertEqual(adapter._policy.info, original.info)
                self.assertEqual(adapter._policy._system_prompt, original._system_prompt)
                state = {'step_days': 1, 'water_level_ft': 1300.0}
                args = (pd.Timestamp('2016-01-01'), 300.0, 1992.61, state)
                a = adapter._policy._build_state_prompt(*args)
                self.assertEqual(a, original._build_state_prompt(*args))
                if method == 'dkp':
                    self.assertIn('Retrieved DKP sections', a)
                    self.assertNotIn((PROJECT_ROOT/'data/anik_v3_7/DKP_FEWalter_Dam_v1.2.md').read_text(), a)
                    self.assertEqual(adapter._policy._system_prompt_sha256,
                        'c018043ce34a6e47024024ce63622d837dffa686a15523eb97d4bdd4ae678352')
                else:
                    self.assertNotIn('Retrieved DKP', a)
                self.assertEqual(adapter.network_calls, 0)

    def test_both_three_day_workflows_preserve_prompt_schema_audit_and_balance(self):
        for method in ('zeroshot', 'dkp'):
            with self.subTest(method=method):
                settings = load_settings(self.save(self.fixture(method)))
                _, result = run_settings(settings)
                summary = result['summary']
                self.assertEqual(summary['observed_network_calls'], 0)
                self.assertEqual(summary['audit_counts'], {'PASS': 3})
                self.assertLess(summary['max_mass_balance_residual_m3'], 1e-6)
                output = Path(settings.report['output'])
                verified = verify_run(output, require_offline=True)
                self.assertEqual(verified['audit_binding_counts']['versioned_suite'], 3)
                payloads = [json.loads(p.read_text()) for p in (output/'raw').glob('policy_*.json')]
                self.assertEqual(len(payloads), 3)
                serialized = json.dumps(payloads)
                self.assertIn('synthetic_fixture', serialized)
                self.assertIn('raw_reply', serialized)
                self.assertIn('release_cfs', serialized)
                self.assertIn('additionalProperties', serialized)
                self.assertIn('model_used', serialized)
                audits = [json.loads(p.read_text()) for p in (output/'raw').glob('audit_*.json')]
                self.assertIn('audit_status', json.dumps(audits))
                with self.assertRaises(FileExistsError):
                    run_settings(settings)

    def test_native_fail_is_retained_without_rewriting_action(self):
        data = self.fixture('dkp')
        fixture = json.loads(Path(data['agents']['fe_operator']['reference']['responses']).read_text())
        for reply in fixture['responses']:
            reply['applicable_target_ft'] = 1420.0
        path = self.root/'bad-target.json'
        path.write_text(json.dumps(fixture))
        data['agents']['fe_operator']['reference']['responses'] = str(path)
        settings = load_settings(self.save(data))
        _, result = run_settings(settings)
        self.assertEqual(result['summary']['audit_counts'], {'FAIL': 3})
        self.assertEqual(result['summary']['observed_network_calls'], 0)
        self.assertIsNone(result['summary'].get('operational_strategy_accepted'))
        raw = '\n'.join(p.read_text() for p in (Path(settings.report['output'])/'raw').glob('audit_*.json'))
        self.assertIn('1420', raw)
        self.assertIn('audit_status', raw)

    def test_native_state_is_not_shared(self):
        a, b = self.backend('zeroshot'), self.backend('zeroshot')
        self.assertIsNot(a.state_owner, b.state_owner)
        a._policy._history.append({'marker': 'only-a'})
        self.assertEqual(len(b._policy._history), 0)
        a._fixture.index = 1
        self.assertEqual(b._fixture.index, 0)

    def test_wrong_physical_profile_and_exhausted_fixture_stop(self):
        settings = load_settings(self.save(self.fixture('dkp')))
        physics = deepcopy(settings.network['reservoirs']['FEWalter']['physical'])
        physics['capacity_m3'] *= 2
        with self.assertRaisesRegex(ValueError, 'physical configuration'):
            ReferenceBackend(settings.agents['fe_operator']['reference'], physics, runtime_root=PROJECT_ROOT)
        load_anik(PROJECT_ROOT)
        with self.assertRaisesRegex(ValueError, 'exhausted'):
            _FixtureTransport([]).decide('system', 'state')

    def test_live_and_generic_override_unknown_options_bad_auditor_rejected(self):
        base = self.fixture('zeroshot')
        patches = [dict(mode='llm'), dict(prompt='other'), dict(model='other'),
                   dict(context={}), dict(strategy='typo'), dict(auditors=[[]])]
        for change in patches:
            data = deepcopy(base)
            data['agents']['fe_operator'].update(change)
            with self.subTest(change=change), self.assertRaises(ValueError):
                load_settings(self.save(data))
        data = deepcopy(base)
        data['agents']['fe_operator']['reference']['dkp'] = 'unexpected'
        with self.assertRaises(ValueError):
            load_settings(self.save(data))
        data = deepcopy(base)
        data['agents']['fe_operator']['reference']['prompt_storage'] = 'false'
        with self.assertRaises(ValueError):
            load_settings(self.save(data))

    def test_fixture_count_declaration_and_after_check_drift_rejected(self):
        data = self.fixture('dkp')
        spec = data['agents']['fe_operator']['reference']
        original = json.loads(Path(spec['responses']).read_text())
        path = self.root/'responses.json'
        spec['responses'] = str(path)
        for fixture in (dict(data_kind='real', responses=original['responses']),
                        dict(data_kind='synthetic_fixture', responses=original['responses'][:1])):
            path.write_text(json.dumps(fixture))
            with self.assertRaises(ValueError):
                load_settings(self.save(data))
        path.write_text(json.dumps(original))
        settings = load_settings(self.save(data))
        original['responses'][0]['reasoning'] = 'changed after check'
        path.write_text(json.dumps(original))
        with self.assertRaisesRegex(ValueError, 'changed after configuration check'):
            run_settings(settings)
        self.assertFalse(Path(data['output']).exists())


if __name__ == '__main__':
    unittest.main()
