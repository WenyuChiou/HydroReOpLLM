"""Provenance and zero-provider-call guard for registered user rules.

Purpose and data flow
---------------------
RuleBasedBackend forwards observations and actions unchanged to a
user-supplied deterministic rule. It describes method identity and checks
that network_calls remains the exact integer zero before and after decisions.
Physical clipping, auditing, routing and recording belong to shared layers.

Dependencies and side effects
-----------------------------
Uses audit.json_snapshot for isolated JSON provenance. Delegated rule
methods may update their own state; this wrapper does not implement their
algorithm. no_model_transport always raises to prevent borrowing live transport.
"""
from .audit import json_snapshot


def no_model_transport(*args, **kwargs):
    """Reject a model-transport request made by a deterministic rule.

    Parameters
    ----------
    *args, **kwargs : object
        Any transport arguments; accepted only to provide a compatible guard.

    Raises
    ------
    RuntimeError
        Always raised because rule_based agents cannot request an LLM.
    """
    raise RuntimeError('rule_based agents cannot request an LLM')


class RuleBasedBackend:
    """Wrap a user rule and require an explicit zero provider-call counter.

    Parameters
    ----------
    backend : object
        Rule with decide(observation) and integer network_calls equal to zero.
        Other attributes are delegated to this object.
    rule_id : str
        Registered rule identity carried into method provenance.

    Raises
    ------
    TypeError
        backend does not implement decide.
    ValueError
        backend does not explicitly report integer network_calls=0.
    """

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
        """Expose the wrapped object for backend state-isolation checks.

        Returns
        -------
        object
            The original backend instance, not a copy.
        """
        return self.backend

    def _check_calls(self):
        count = getattr(self.backend, 'network_calls', None)
        if type(count) is not int or count != 0:
            raise ValueError('rule backend must explicitly report network_calls=0')

    def describe(self):
        """Add rule identity to a JSON snapshot of user-supplied provenance.

        Returns
        -------
        dict
            Rule provenance with backend=rule_based, rule_id and explicit disabled
            model/network flags; a supplied backend label becomes rule_backend.

        Raises
        ------
        TypeError
            Supplied provenance is not a JSON-compatible mapping.
        ValueError
            Provenance contains invalid JSON values.
        """
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
        """Forward one decision while enforcing the zero-call counter.

        Parameters
        ----------
        observation : mapping
            Common reservoir observation passed directly to the user rule.

        Returns
        -------
        object
            The wrapped rule's requested action, unchanged; shared action parsing
            validates the eventual release contract.

        Raises
        ------
        ValueError
            The rule's network_calls counter is invalid before or after the decision.

        Notes
        -----
        Exceptions from the user rule propagate. A post-decision counter failure
        does not roll back state already changed inside that rule.
        """
        self._check_calls()
        action = self.backend.decide(observation)
        self._check_calls()
        return action
