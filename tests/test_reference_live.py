"""Live interface acceptance with injected replies and blocked HTTP sockets."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from io import BytesIO

import yaml

from llm_reservoir_agent.network import PROJECT_ROOT
from llm_reservoir_agent.configured_backend import http_json_transport as original_http_transport
from examples.fe_walter.extensions.reference_backend import ReferenceBackend
from llm_reservoir_agent.verification import verify_run
from llm_reservoir_agent.workflow import load_settings, run_settings



def _pin_example_extension(data):
    # This test copies FE Walter configuration into a disposable directory.
    if data.get("extensions"):
        data["extensions"] = {key: str(PROJECT_ROOT / "examples/fe_walter/extensions/__init__.py") for key in data["extensions"]}
    return data

class ReferenceLiveTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.guard = patch('llm_reservoir_agent.configured_backend.http_json_transport',
                           side_effect=AssertionError('real network forbidden'))
        self.guard.start()

    def tearDown(self):
        self.guard.stop()
        self.temp.cleanup()

    def settings(self, method, provider='ollama', ready=True, run_suffix=''):
        folder = 'zero_shot' if method == 'zeroshot' else method
        p = PROJECT_ROOT / f'examples/fe_walter/{folder}/experiment.llm.yaml'
        data = yaml.safe_load(p.read_text(encoding='utf-8'))
        case = json.loads((p.parent / data['case']).resolve().read_text())
        (self.root / 'inflows.csv').write_bytes((PROJECT_ROOT / 'cases/fe_walter_reference/inflows.csv').read_bytes())
        case['inflow_source']['path'] = 'inflows.csv'
        case['live_readiness']['ready'] = ready # Temporary diagnostic case only.
        cp = self.root / 'case.json'
        cp.write_text(json.dumps(case))
        data['case'] = str(cp)
        data['case_root'] = str(self.root)
        data['output'] = str(self.root / f'run-{method}-{provider}{run_suffix}')
        spec = data['agents']['fe_operator']['customization']['parameters']['reference']
        for key in ('system_prompt', 'dkp'):
            if key in spec:
                spec[key] = str((p.parent / spec[key]).resolve())
        data['models']['reservoir_model'].update(provider=provider, model='mock-model')
        dest = self.root / 'experiment.yaml'
        dest.write_text(yaml.safe_dump(_pin_example_extension(data)), encoding='utf-8')
        return load_settings(dest)

    def replies(self, method):
        return json.loads((PROJECT_ROOT/f'cases/fe_walter_reference/{method}_responses.json').read_text())['responses']

    def test_shipped_live_plans_are_network_free_and_blocked(self):
        for folder in ('zero_shot', 'dkp'):
            settings = load_settings(PROJECT_ROOT/f'examples/fe_walter/{folder}/experiment.llm.yaml')
            self.assertFalse(settings.report['live_ready'])
            self.assertEqual(settings.report['planned_llm_calls'], 3)
            self.assertEqual(settings.report['network_calls'], 0)
            self.assertEqual(settings.agents['fe_operator']['model']['temperature'], 0.7)
            with self.assertRaisesRegex(ValueError, 'live-ready'):
                run_settings(settings, allow_network=True)
            self.assertFalse(Path(settings.report['output']).exists())

    def test_both_methods_both_providers_keep_native_prompts_schema_audits_feedback(self):
        for method in ('zeroshot', 'dkp'):
            for provider in ('ollama', 'openai_compatible'):
                with self.subTest(method=method, provider=provider):
                    settings = self.settings(method, provider)
                    replies = self.replies(method)
                    requests = []
                    def fake(url, payload, headers, timeout):
                        requests.append(deepcopy(payload))
                        reply = replies[len(requests)-1]
                        content = json.dumps(reply)
                        return ({'message': {'content': content}, 'eval_count': 17, 'done': True, 'done_reason': 'stop'} if provider == 'ollama'
                                else {'id': 'mock-request', 'choices': [{'message': {'content': content}, 'finish_reason': 'stop'}],
                                      'usage': {'completion_tokens': 17}})
                    _, result = run_settings(settings, allow_network=True, transport=fake)
                    self.assertEqual(len(requests), 3)
                    self.assertEqual(result['summary']['observed_network_calls'], 3) # Injected attempts, not HTTP.
                    self.assertEqual(result['summary']['audit_counts'], {'PASS': 3})
                    self.assertLess(result['summary']['max_mass_balance_residual_m3'], 1e-6)
                    verified = verify_run(Path(settings.report['output']))
                    self.assertEqual(verified['audit_binding_counts']['versioned_suite'], 3)
                    original = Path(settings.agents['fe_operator']['reference']['system_prompt']).read_text(encoding='utf-8')
                    for req in requests:
                        self.assertEqual(req['messages'][0]['content'], original)
                        temperature = req['options']['temperature'] if provider == 'ollama' else req['temperature']
                        self.assertEqual(temperature, 0.7)
                        schema = req['format'] if provider == 'ollama' else req['response_format']['json_schema']['schema']
                        self.assertEqual(len(schema['required']), 6 if method == 'zeroshot' else 8)
                        self.assertEqual(schema['additionalProperties'], False)
                        self.assertEqual('Retrieved DKP sections' in req['messages'][1]['content'], method == 'dkp')
                    self.assertNotEqual(requests[0]['messages'][1]['content'], requests[1]['messages'][1]['content'])
                    self.assertIn('2016-01-01', requests[1]['messages'][1]['content'])
                    raw = '\n'.join(p.read_text(encoding='utf-8') for p in Path(settings.report['output']).glob('raw/policy_*.json'))
                    for token in ('request_sha256', 'raw_reply', 'schema', 'audit_execution', '0.7'):
                        self.assertIn(token, raw)

    def test_permission_budget_and_fixture_fallback_fail_closed(self):
        settings = self.settings('dkp')
        with self.assertRaisesRegex(ValueError, 'allow-network'):
            run_settings(settings, transport=lambda *a: self.fail('called'))
        data = yaml.safe_load(settings.path.read_text())
        for change in ('budget', 'responses', 'model'):
            bad = deepcopy(data)
            if change == 'budget': bad['max_calls'] = 2
            elif change == 'responses':
                bad['agents']['fe_operator']['customization']['parameters']['reference']['responses'] = 'ignored.json'
            else: bad['agents']['fe_operator']['model_profile'] = 'missing'
            settings.path.write_text(yaml.safe_dump(bad))
            with self.assertRaises(ValueError): load_settings(settings.path)

    def test_live_native_audit_fail_is_preserved_without_revision_calls(self):
        settings = self.settings('dkp')
        replies = self.replies('dkp')
        attempts = []
        def fake(*args):
            reply = deepcopy(replies[len(attempts)])
            reply['applicable_target_ft'] = 1420.0
            attempts.append(1)
            return {'message': {'content': json.dumps(reply)}, 'done': True, 'done_reason': 'stop'}
        _, result = run_settings(settings, allow_network=True, transport=fake)
        self.assertEqual(len(attempts), 3)
        self.assertEqual(result['summary']['audit_counts'], {'FAIL': 3})
        self.assertIsNone(result['summary'].get('operational_strategy_accepted'))
        self.assertEqual(verify_run(Path(settings.report['output']))['audit_binding_counts']['versioned_suite'], 3)

    def test_http_serialization_preserves_native_schema_field_order_without_network(self):
        from llm_reservoir_agent.configured_backend import chat_request
        settings = self.settings('dkp')
        agent = settings.agents['fe_operator']
        backend = ReferenceBackend(agent['reference'], settings.network['reservoirs']['FEWalter']['physical'],
                                   runtime_root=PROJECT_ROOT, mode='llm', model=agent['model'], transport=lambda *a: {})
        schema = backend._parser.schema
        url, payload = chat_request(agent['model'], [], schema=schema)
        captured = []
        class FakeOpener:
            def open(self, request, timeout):
                captured.append(json.loads(request.data))
                return BytesIO(b'{}')
        with patch('llm_reservoir_agent.configured_backend.build_opener', return_value=FakeOpener()):
            original_http_transport(url, payload, {}, 1)
        self.assertEqual(list(captured[0]['format']['properties']), list(schema['properties']))

    def test_failure_and_malformed_reply_never_apply_physics_or_retry(self):
        for method in ('zeroshot', 'dkp'):
            for failure in ('timeout', 'json', 'nonfinite', 'missing', 'extra', 'enum', 'boolean'):
                with self.subTest(method=method, failure=failure):
                    settings = self.settings(method, run_suffix=f'-{failure}')
                    attempts = []
                    def fake(*args):
                        attempts.append(1)
                        if failure == 'timeout': raise TimeoutError('secret must not reach trace')
                        if failure in ('json', 'nonfinite'):
                            content = '{' if failure == 'json' else '{"release_cfs": NaN}'
                        else:
                            reply = deepcopy(self.replies(method)[0])
                            if failure == 'missing': del reply['reasoning']
                            elif failure == 'extra': reply['invented'] = 1
                            elif failure == 'enum': reply['pool_position'] = 'invented'
                            else: reply['release_cfs'] = True
                            content = json.dumps(reply)
                        return {'message': {'content': content}, 'done': True, 'done_reason': 'stop'}
                    with self.assertRaisesRegex(RuntimeError, 'physics was not applied'):
                        run_settings(settings, allow_network=True, transport=fake)
                    self.assertEqual(len(attempts), 1)
                    output = Path(settings.report['output'])
                    if (output/'reservoir_trajectory.csv').exists():
                        self.assertLessEqual(len((output/'reservoir_trajectory.csv').read_text().splitlines()), 1)
                    raw = '\n'.join(p.read_text(encoding='utf-8') for p in output.rglob('*.json'))
                    self.assertNotIn('secret must not reach trace', raw)
                    # Each attempt has a fresh output; prior failed evidence is retained.

    def test_missing_credential_does_not_call_transport(self):
        settings = self.settings('zeroshot')
        agent = settings.agents['fe_operator']
        model = dict(agent['model'], api_key_env='RESERVOIR_TEST_ABSENT_KEY')
        backend = ReferenceBackend(agent['reference'], settings.network['reservoirs']['FEWalter']['physical'],
                                   runtime_root=PROJECT_ROOT, mode='llm', model=model,
                                   transport=lambda *a: self.fail('called'))
        with patch.dict('os.environ', {}, clear=True), self.assertRaisesRegex(RuntimeError, 'request or response failed'):
            backend._fixture.decide('system', 'prompt')
        self.assertEqual(backend.network_calls, 0)

    def test_incomplete_or_missing_completion_status_rejects_valid_native_json(self):
        for method in ('zeroshot', 'dkp'):
            for provider in ('ollama', 'openai_compatible'):
                for status in ('length', 'missing', 'incomplete'):
                    with self.subTest(method=method, provider=provider, status=status):
                        settings = self.settings(method, provider, run_suffix=f'-{status}')
                        attempts = []
                        def fake(*args):
                            attempts.append(1)
                            content = json.dumps(self.replies(method)[0]) # Complete, valid native JSON.
                            if provider == 'ollama':
                                raw = {'message': {'content': content}}
                                if status == 'length': raw.update(done=True, done_reason='length')
                                elif status == 'incomplete': raw.update(done=False)
                                return raw
                            choice = {'message': {'content': content}}
                            if status != 'missing': choice['finish_reason'] = 'length' if status == 'length' else None
                            return {'choices': [choice]}
                        rejects = status == 'length' or (provider == 'ollama' and status == 'incomplete')
                        if rejects:
                            with self.assertRaisesRegex(RuntimeError, 'physics was not applied'):
                                run_settings(settings, allow_network=True, transport=fake)
                            self.assertEqual(len(attempts), 1)
                        else:
                            _, result = run_settings(settings, allow_network=True, transport=fake)
                            self.assertEqual(sum(result['summary']['audit_counts'].values()), 3)
                            self.assertEqual(len(attempts), 3)
                        output = Path(settings.report['output'])
                        if rejects and (output/'reservoir_trajectory.csv').exists():
                            self.assertLessEqual(len((output/'reservoir_trajectory.csv').read_text().splitlines()), 1)


if __name__ == '__main__':
    unittest.main()
