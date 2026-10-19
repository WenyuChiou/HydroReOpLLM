"""Original-policy parity and reference YAML acceptance, without providers."""
from copy import deepcopy
from dataclasses import replace
import json
import hashlib
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd
import yaml

from reference_oracle import load_anik, require_reference_dir
from llm_reservoir_agent.network import PROJECT_ROOT
from examples.fe_walter.extensions.reference_backend import ReferenceBackend, _FixtureTransport
from llm_reservoir_agent.context import DecisionContext
from llm_reservoir_agent.verification import verify_run
from llm_reservoir_agent.workflow import load_settings, run_settings



def _pin_example_extension(data):
    # This test copies FE Walter configuration into a disposable directory.
    if data.get("extensions"):
        data["extensions"] = {key: str(PROJECT_ROOT / "examples/fe_walter/extensions/__init__.py") for key in data["extensions"]}
    return data

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
        prompt = ('available_information.txt' if method == 'zeroshot' else 'retrieved_knowledge.txt')
        spec.update(system_prompt=str(PROJECT_ROOT / 'examples/fe_walter/prompts' / prompt),
                    system_prompt_mode='custom')
        return data

    def history_root(self):
        configured = os.environ.get('HYDROOPS_FE_WALTER_HISTORY_DIR')
        if not configured:
            self.skipTest('historical FE Walter prompt bundle is optional')
        root = Path(configured).resolve()
        if not root.is_dir():
            self.fail('configured HYDROOPS_FE_WALTER_HISTORY_DIR is invalid')
        return root

    def original_fixture(self, method):
        self.history_root()
        data = self.fixture(method)
        spec = data['agents']['fe_operator']['reference']
        spec.pop('system_prompt')
        spec['system_prompt_mode'] = 'original'
        return data

    def save(self, data):
        path = self.root / 'experiment.yaml'
        path.write_text(yaml.safe_dump(_pin_example_extension(data)), encoding='utf-8')
        return path

    def backend(self, method, *, historical=False):
        data = self.original_fixture(method) if historical else self.fixture(method)
        settings = load_settings(self.save(data))
        spec = settings.agents['fe_operator']['reference']
        physics = settings.network['reservoirs']['FEWalter']['physical']
        return ReferenceBackend(spec, physics, runtime_root=PROJECT_ROOT)

    def test_system_info_and_state_prompt_match_original_factory(self):
        self.history_root()
        model = load_anik(PROJECT_ROOT)
        zero = sys.modules['zeroshot_llm_release']
        cfg = next(c for c in model.RESERVOIRS if c.inflow_reservoir_key == 'fe_walter')
        cfg = replace(cfg, dkp_path=str(PROJECT_ROOT/'examples/fe_walter/knowledge/operating_rules.md'))
        for method in ('zeroshot', 'dkp'):
            with self.subTest(method=method):
                adapter = self.backend(method, historical=True)
                transport = _FixtureTransport([])
                with patch.object(model, 'RESULTS_DIR', self.root), patch.object(model, 'LLM_BACKENDS',
                        {'fixture': ('zeroshot_llm_release', 'ReferenceFixture', {})}), patch.object(
                        zero, 'ReferenceFixture', lambda: transport, create=True):
                    original = model.build_policy(cfg, method, 'fixture', pd.Series(dtype=float),
                        prompt_storage=False, hide_availability_line=True, dkp_no_missing_inputs=True,
                        dkp_audit_action='record', zeroshot_audit_action='record')
                self.assertEqual(adapter._system_prompt, original._system_prompt)
                state = {'step_days': 1, 'pool_elevation_ft': 1300.0}
                args = (pd.Timestamp('2016-01-01'), 300.0, 1992.61, state)
                obs = {'schema_version': 'reservoir-observation.v1', 'timestep': 0,
                       'timestamp': '2016-01-01', 'inflow_cms': 300.0 * model.CFS_TO_CMS,
                       'release_upper_bound_cms': adapter._physical['maximum_release_cms'],
                       'state': dict(adapter._physical, storage_m3=1992.61 * model.CF_PER_ACREFT * model.M3_PER_CF),
                       'context': {}}
                a = adapter._formatter(DecisionContext('fe_walter', obs, None)).value
                self.assertEqual(a, original._build_state_prompt(*args))
                if method == 'dkp':
                    self.assertIn('Retrieved DKP sections', a)
                    self.assertNotIn((PROJECT_ROOT/'examples/fe_walter/knowledge/operating_rules.md').read_text(encoding='utf-8'), a)
                    self.assertEqual(adapter._original_prompt_sha256,
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
                payloads = [json.loads(p.read_text(encoding='utf-8')) for p in (output/'raw').glob('policy_*.json')]
                self.assertEqual(len(payloads), 3)
                serialized = json.dumps(payloads)
                self.assertIn('synthetic_fixture', serialized)
                self.assertIn('raw_reply', serialized)
                self.assertIn('release_cfs', serialized)
                self.assertIn('additionalProperties', serialized)
                self.assertIn('model_used', serialized)
                audits = [json.loads(p.read_text(encoding='utf-8')) for p in (output/'raw').glob('audit_*.json')]
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
        raw = '\n'.join(p.read_text(encoding='utf-8') for p in (Path(settings.report['output'])/'raw').glob('audit_*.json'))
        self.assertIn('1420', raw)
        self.assertIn('audit_status', raw)

    def test_native_state_is_not_shared(self):
        a, b = self.backend('zeroshot'), self.backend('zeroshot')
        self.assertIsNot(a.state_owner, b.state_owner)
        a._formatter.history.append({'marker': 'only-a'})
        self.assertEqual(len(b._formatter.history), 0)
        a._fixture.index = 1
        self.assertEqual(b._fixture.index, 0)

    def test_wrong_physical_profile_and_exhausted_fixture_stop(self):
        settings = load_settings(self.save(self.fixture('dkp')))
        physics = deepcopy(settings.network['reservoirs']['FEWalter']['physical'])
        physics['capacity_m3'] *= 2
        with self.assertRaisesRegex(ValueError, 'physical configuration'):
            ReferenceBackend(settings.agents['fe_operator']['reference'], physics, runtime_root=PROJECT_ROOT)
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

    def external_fixture(self, method, *, mode='original', suffix='', crlf=False):
        data = self.fixture(method)
        blob = (self.history_root() / ('archive/fe_walter/prompts/' + {
            'zeroshot': 'available_original.txt', 'dkp': 'retrieved_original.txt'}[method])).read_bytes()
        if crlf:
            blob = blob.replace(b'\n', b'\r\n')
        path = self.root / f'{method}-system.txt'
        path.write_bytes(blob + suffix.encode('utf-8'))
        data['agents']['fe_operator']['reference'].update(system_prompt=str(path), system_prompt_mode=mode)
        return data

    def test_external_system_text_matches_original_and_keeps_daily_builder(self):
        for method in ('zeroshot', 'dkp'):
            for crlf in (False, True):
                with self.subTest(method=method, crlf=crlf):
                    original = self.backend(method, historical=True)
                    settings = load_settings(self.save(self.external_fixture(method, crlf=crlf)))
                    spec = settings.agents['fe_operator']['reference']
                    backend = ReferenceBackend(spec, settings.network['reservoirs']['FEWalter']['physical'], runtime_root=PROJECT_ROOT)
                    self.assertEqual(backend._system_prompt, original._system_prompt)
                    self.assertEqual(backend._formatter.sections if hasattr(backend._formatter, 'sections') else None,
                                     original._formatter.sections if hasattr(original._formatter, 'sections') else None)
                    self.assertEqual(backend.describe()['system_prompt_source'], 'file')
                    self.assertTrue(backend.describe()['matches_original_system_prompt'])
                    self.assertIn(spec['system_prompt'], settings.files)

    def test_modified_prompt_needs_custom_mode_and_is_saved_with_actual_hash(self):
        for method in ('zeroshot', 'dkp'):
            with self.subTest(method=method):
                data = self.external_fixture(method, suffix='\nAdditional experimental instruction.\n')
                with self.assertRaisesRegex(ValueError, 'differs from original builder'):
                    load_settings(self.save(data))
                data['agents']['fe_operator']['reference']['system_prompt_mode'] = 'custom'
                settings = load_settings(self.save(data))
                spec = settings.agents['fe_operator']['reference']
                physics = settings.network['reservoirs']['FEWalter']['physical']
                backend = ReferenceBackend(spec, physics, runtime_root=PROJECT_ROOT)
                described = backend.describe()
                actual = hashlib.sha256(Path(spec['system_prompt']).read_bytes()).hexdigest()
                self.assertEqual(described['prompt_sha256'], actual)
                self.assertEqual(described['reference_source_sha256']['system_prompt'], actual)
                self.assertFalse(described['matches_original_system_prompt'])
                self.assertEqual(described['system_prompt_mode'], 'custom')
                self.assertTrue(described['prompt_strategy_id'].endswith('_custom_system'))
                _, result = run_settings(settings)
                self.assertEqual(result['summary']['observed_network_calls'], 0)
                output = Path(settings.report['output'])
                verified = verify_run(output, require_offline=True)
                self.assertEqual(verified['audit_binding_counts']['versioned_suite'], 3)
                payloads = list((output/'raw').glob('policy_*.json'))
                self.assertEqual(len(payloads), 3)
                for p in payloads:
                    text = p.read_text(encoding='utf-8')
                    self.assertIn('Additional experimental instruction.', text)
                    system = json.loads(text)['backend_trace']['system']
                    self.assertEqual(hashlib.sha256(system.encode('utf-8')).hexdigest(), actual)
                decisions = [json.loads(line) for line in (output/'decisions.jsonl').read_text().splitlines()]
                self.assertEqual(len(decisions), 3)
                for record in decisions:
                    provenance = record['provenance']
                    self.assertEqual(provenance['prompt_sha256'], actual)
                    self.assertEqual(provenance['system_prompt_mode'], 'custom')
                    self.assertFalse(provenance['matches_original_system_prompt'])
                    self.assertTrue(provenance['prompt_strategy_id'].endswith('_custom_system'))
                self.assertIsNone(result['summary'].get('operational_strategy_accepted'))

    def test_external_prompt_drift_is_rejected_before_output(self):
        data = self.external_fixture('dkp')
        settings = load_settings(self.save(data))
        spec = settings.agents['fe_operator']['reference']
        Path(spec['system_prompt']).write_text('Changed after check', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'changed after validation'):
            ReferenceBackend(spec, settings.network['reservoirs']['FEWalter']['physical'], runtime_root=PROJECT_ROOT)
        with self.assertRaisesRegex(ValueError, 'changed after|differs from original'):
            run_settings(settings)
        self.assertFalse(Path(settings.report['output']).exists())

    def test_external_prompt_invalid_settings_fail_closed(self):
        for patch_spec in ({'system_prompt': ''}, {'system_prompt_mode': 'typo'}, {'system_prompt_mode': 'custom'}):
            data = self.fixture('zeroshot')
            data['agents']['fe_operator']['reference'].update(patch_spec)
            if patch_spec == {'system_prompt_mode': 'custom'}:
                data['agents']['fe_operator']['reference'].pop('system_prompt')
            with self.subTest(patch=patch_spec), self.assertRaises(ValueError):
                load_settings(self.save(data))
        for contents, exception in ((b'   ', ValueError), (b'\xff', UnicodeDecodeError)):
            data = self.external_fixture('zeroshot')
            Path(data['agents']['fe_operator']['reference']['system_prompt']).write_bytes(contents)
            with self.subTest(contents=contents), self.assertRaises(exception):
                load_settings(self.save(data))


if __name__ == '__main__':
    unittest.main()
