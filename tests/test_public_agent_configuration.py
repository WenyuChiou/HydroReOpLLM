"""User-facing method choices normalize into the same validated engine."""
from copy import deepcopy
import json
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from llm_reservoir_agent.configuration import read_configuration


def read_agent(tmp_path, agent, version='llm-reservoir-experiment.v2'):
    path = tmp_path / 'run.yaml'
    path.write_text(yaml.safe_dump({'schema_version': version, 'agents': {'operator': agent}}))
    return read_configuration(path)[0]['agents']['operator']


def test_public_llm_fields_have_no_implicit_system_prompt(tmp_path):
    data = read_agent(tmp_path, {'reservoir_id': 'lake', 'type': 'llm',
                               'model_profile': 'local', 'prompt_file': 'user.txt'})
    assert data == {'reservoir': 'lake', 'agent_type': 'llm', 'mode': 'llm', 'model': 'local',
                    'prompt': {'user': str(tmp_path / 'user.txt')}}


def test_public_rule_is_an_open_module_id_with_opaque_parameters(tmp_path):
    original = {'reservoir_id': 'lake', 'type': 'rule_based', 'rule': 'my_supply_rule',
                'rule_parameters': {'my_target': 20, 'path': 'opaque/user/value'}}
    copied = deepcopy(original)
    data = read_agent(tmp_path, original)
    assert original == copied
    assert data == {'reservoir': 'lake', 'agent_type': 'rule_based', 'mode': 'offline',
                    'strategy': 'my_supply_rule', 'rule_parameters': original['rule_parameters']}
    from llm_reservoir_agent.agent_configuration import normalize_agent
    assert normalize_agent(data) == data  # Generated operation files re-enter the same loader.


@pytest.mark.parametrize('rule_id', ['my_supply_rule', 'another_user_rule'])
def test_arbitrary_public_rule_needs_neither_prompt_nor_model(tmp_path, rule_id):
    from tests.test_weather_entry import make_bundle
    from llm_reservoir_agent.coupled import load_coupled_settings, run_coupled
    from llm_reservoir_agent.verification import verify_run
    data = make_bundle(tmp_path)
    plugin = tmp_path / 'my_rule'
    plugin.mkdir()
    (plugin / '__init__.py').write_text('''"""User-defined inflow fraction, unrelated to any example algorithm."""
from llm_reservoir_agent.contracts import ReservoirAction

def validate_backend(spec, *, simulation_start, **kwargs):
    assert spec['rule_parameters'] == {'fraction': .3}
    return {'fraction': .3, 'first_day': simulation_start}, {}

def build_backend(settings, **kwargs):
    return Controller(settings['fraction'])

class Controller:
    policy_id = 'user_defined_inflow_fraction'
    network_calls = 0
    def __init__(self, fraction):
        self.fraction = fraction
    def decide(self, observation):
        assert observation['context']['decision_information']['fields']['demand']['value'] == 2
        return ReservoirAction(observation['inflow_cms'] * self.fraction)
''')
    data['extensions'] = {rule_id: 'my_rule/__init__.py'}
    data['agents'] = {'operator': {'reservoir_id': 'lake', 'type': 'rule_based',
        'rule': rule_id, 'rule_parameters': {'fraction': .3},
        'customization': {'information': 'downstream'}}}
    data['information_sources'] = {'demand': {'type': 'static', 'quantity': 'required_flow',
        'unit': 'm3/s', 'location': 'use-point', 'value': 2}}
    data['information_profiles'] = {'downstream': {'fields': {'demand': {'source': 'demand'}}}}
    # The physical ID is supplied by the teaching fixture, not by a hidden mapping.
    data['agents']['operator']['reservoir_id'] = next(iter(json.loads(
        (tmp_path / 'reservoirs.json').read_text())['network']['reservoirs']))
    path = tmp_path / 'simulation.yaml'
    path.write_text(yaml.safe_dump(data))
    settings = load_coupled_settings(path)
    with patch('llm_reservoir_agent.configured_backend.http_json_transport',
               side_effect=AssertionError('constant rule must never call a provider')):
        records, _ = run_coupled(settings)
    assert verify_run(tmp_path / 'output/operation', require_offline=True)['days'] == 4
    assert settings.report['agent_types'] == {'operator': 'rule_based'}
    assert settings.report['agent_rules'] == {'operator': rule_id}
    saved = [json.loads(line) for line in (tmp_path / 'output/operation/decisions.jsonl').read_text().splitlines()]
    assert len(saved) == 4
    for row in records[data['agents']['operator']['reservoir_id']]:
        assert row['transition']['target_release_cms'] == pytest.approx(row['transition']['inflow_cms'] * .3)


@pytest.mark.parametrize('updates,match', [
    ({'type': 'offline'}, 'type'),
    ({'type': 'LLM'}, 'type'),
    ({'reservoir_id': ''}, 'reservoir_id'),
    ({'mode': 'llm'}, 'mix'),
    ({'strategy': 'configured'}, 'mix'),
    ({'model': 'local'}, 'mix'),
    ({'reason': 'some text'}, 'unsupported'),
    ({'rule': 'hanasaki'}, 'LLM'),
    ({'model_profile': None}, 'model_profile'),
    ({'prompt_file': None}, 'prompt_file'),
    ({'customization': {'typo': True}}, 'customization'),
    ({'customization': {'parameters': {'mode': 'offline'}}}, 'backend'),
    ({'customization': {'execution': 'replay'}}, 'backend'),
])
def test_confusing_or_mixed_public_options_fail_before_io(tmp_path, updates, match):
    agent = {'reservoir_id': 'lake', 'type': 'llm', 'model_profile': 'local', 'prompt_file': 'user.txt'}
    agent.update(updates)
    with pytest.raises(ValueError, match=match):
        read_agent(tmp_path, agent)


@pytest.mark.parametrize('rule,params', [('', {}), (None, {}), ('configured', {}),
                                       ('benchmark', {}), ('my_rule', [])])
def test_invalid_rule_module_declarations_are_rejected(tmp_path, rule, params):
    with pytest.raises(ValueError):
        read_agent(tmp_path, {'reservoir_id': 'lake', 'type': 'rule_based',
                             'rule': rule, 'rule_parameters': params})


@pytest.mark.parametrize('protected', ['reservoir', 'mode', 'model', 'prompt', 'strategy',
                                     'auditors', 'release_cms', 'reservoir_id', 'type'])
def test_custom_backend_cannot_override_core_contract(tmp_path, protected):
    with pytest.raises(ValueError, match='protected'):
        read_agent(tmp_path, {'reservoir_id': 'lake', 'type': 'llm', 'model_profile': 'local',
            'customization': {'backend': 'my_backend', 'parameters': {protected: 'override'}}})


def test_custom_backend_replay_is_execution_not_a_third_agent_type(tmp_path):
    data = read_agent(tmp_path, {'reservoir_id': 'lake', 'type': 'llm', 'model_profile': 'local',
        'customization': {'backend': 'my_backend', 'execution': 'replay',
                          'parameters': {'recipe': {'path': 'opaque/value'}}}})
    assert data == {'reservoir': 'lake', 'agent_type': 'llm', 'mode': 'offline', 'model': 'local',
                    'strategy': 'my_backend', 'recipe': {'path': 'opaque/value'}}


def test_nested_configuration_paths_belong_to_the_declaring_file(tmp_path):
    folder = tmp_path / 'ops'
    folder.mkdir()
    (folder / 'agents.yaml').write_text(yaml.safe_dump({'operator': {
        'reservoir_id': 'lake', 'type': 'llm', 'model_profile': 'local', 'prompt_file': 'user.txt',
        'customization': {'system_prompt_file': 'system.txt', 'knowledge': {'manual': 'manual.txt'},
                          'context': {'path': 'opaque/value'}}}}))
    path = tmp_path / 'run.yaml'
    path.write_text(yaml.safe_dump({'schema_version': 'llm-reservoir-experiment.v2',
                                  'agents': {'file': 'ops/agents.yaml'}}))
    data = read_configuration(path)[0]['agents']['operator']
    assert data['prompt'] == {'user': str(folder / 'user.txt'), 'system': str(folder / 'system.txt')}
    assert data['knowledge']['manual'] == str(folder / 'manual.txt')
    assert data['context']['path'] == 'opaque/value'


def test_v1_accepts_public_fields_without_rewriting_legacy(tmp_path):
    public = read_agent(tmp_path, {'reservoir_id': 'lake', 'type': 'llm',
        'model_profile': 'local', 'prompt_file': 'user.txt'}, 'llm-reservoir-experiment.v1')
    assert public['prompt']['user'] == 'user.txt'
    legacy = {'reservoir': 'lake', 'mode': 'offline', 'release_cms': 1, 'prompt': 'old.txt'}
    assert read_agent(tmp_path, legacy, 'llm-reservoir-experiment.v1') == legacy


@pytest.mark.parametrize('count', [None, False, 1, -1])
def test_rule_requires_an_explicit_zero_provider_counter(count):
    from llm_reservoir_agent.rule_based import RuleBasedBackend
    class Rule:
        network_calls = count
        def decide(self, observation):
            return {'schema_version': 'reservoir-action.v1', 'release_cms': 0}
    with pytest.raises(ValueError, match='network_calls=0'):
        RuleBasedBackend(Rule(), 'my_rule')


def test_rule_cannot_borrow_live_transport_and_cannot_hide_calls():
    from llm_reservoir_agent.rule_based import RuleBasedBackend, no_model_transport
    with pytest.raises(RuntimeError, match='cannot request an LLM'):
        no_model_transport('url', {}, {}, 1)
    class Rule:
        network_calls = 0
        def decide(self, observation):
            self.network_calls += 1
            return {'schema_version': 'reservoir-action.v1', 'release_cms': 0}
    with pytest.raises(ValueError, match='network_calls=0'):
        RuleBasedBackend(Rule(), 'my_rule').decide({})
