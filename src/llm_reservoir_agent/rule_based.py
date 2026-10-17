"""Guard and describe any explicitly registered deterministic rule backend.

The module implements the user's rule. This adapter supplies method provenance
and requires an explicit zero provider-call counter. Common policy adaptation,
audit, physics, routing and recording remain the same as for an LLM agent.
"""
from .audit import json_snapshot


def no_model_transport(*args, **kwargs):
    """A rule module cannot borrow a live transport from a mixed-method run."""
    raise RuntimeError('rule_based agents cannot request an LLM')


class RuleBasedBackend:
    """Wrap a user rule without interpreting its algorithm or parameters."""

    def __init__(self, backend, rule_id):
        self.backend = backend
        self.rule_id = rule_id
        if not callable(getattr(backend, 'decide', None)):
            raise TypeError('rule backend must provide decide(observation)')
        self._check_calls()

    def __getattr__(self, name):
        return getattr(self.backend, name)

    @property
    def state_owner(self):
        return self.backend

    def _check_calls(self):
        count = getattr(self.backend, 'network_calls', None)
        if type(count) is not int or count != 0:
            raise ValueError('rule backend must explicitly report network_calls=0')

    def describe(self):
        describe = getattr(self.backend, 'describe', None)
        supplied = describe() if callable(describe) else getattr(self.backend, 'provenance', None)
        result = {} if supplied is None else json_snapshot(supplied, label='rule provenance')
        if not isinstance(result, dict):
            raise TypeError('rule provenance must be a mapping')
        if 'backend' in result:
            result['rule_backend'] = result['backend']
        result.update(backend='rule_based', rule_id=self.rule_id, model_used=False, network_enabled=False)
        return result

    def decide(self, observation):
        self._check_calls()
        action = self.backend.decide(observation)
        self._check_calls()
        return action
