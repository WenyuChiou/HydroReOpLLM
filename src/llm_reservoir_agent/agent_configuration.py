"""Translate one reservoir agent section into the canonical execution vocabulary.

``configuration`` supplies the declaring file's paths; ``workflow`` validates
resources and constructs the selected rule or LLM backend. ``normalize_agent``
copies public or legacy mappings into detached settings without reading files,
calling a model or choosing site rules. Public and legacy names cannot be mixed.
Operating method (rule_based/llm) and execution mode (live/replay) are separate.
Rule parameters keep the selected extension's units; no conversion occurs here.
"""
from copy import deepcopy


# Beginner-facing fields name the controlled reservoir, method and shared profiles.
_PUBLIC = {'reservoir_id', 'type', 'rule', 'rule_parameters', 'model_profile',
           'prompt_file', 'auditors', 'customization'}
# Advanced fields remain available inside ``customization`` for explicit use.
_ADVANCED = {'prompt_version', 'prompt_variables', 'context_providers', 'knowledge',
             'context', 'context_file', 'information', 'response_schema', 'fallback_models', 'history_steps'}
# Legacy names are accepted on their own, but never mixed with the public vocabulary.
_LEGACY = {'reservoir', 'mode', 'strategy', 'model', 'prompt', 'benchmark',
           'release_cms', 'agent_type', *_ADVANCED}
# Extensions receive only these declared customization controls and opaque parameters.
_CUSTOM = {*_ADVANCED, 'system_prompt_file', 'backend', 'parameters', 'execution'}


def _text(value, label):
    """Require a nonempty identifier without coercing numbers or missing values to text."""

    if not isinstance(value, str) or not value.strip():
        raise ValueError(label + ' must be a nonempty string')
    return value


def normalize_agent(spec):
    """Copy one agent declaration into canonical backend settings.

    Extension parameters are opaque, retain their declared units, and cannot replace protected framework settings. This function performs no I/O.

    Parameters
    ----------
    spec : dict or JSON-compatible object
        Public reservoir_id/type settings or a legacy declaration; legacy inputs are copied unchanged.

    Returns
    -------
    dict or object
        Detached canonical settings; rule_based agents use an explicit registered rule, while replay remains an LLM execution mode.

    Raises
    ------
    ValueError
        Public and legacy keys overlap, required identifiers are missing, or customization is incompatible with the selected method.
    """
    if not isinstance(spec, dict) or not (set(spec) & (_PUBLIC - {'auditors', 'rule_parameters'})):
        return deepcopy(spec)
    mixed = set(spec) & _LEGACY
    if mixed:
        raise ValueError('cannot mix public and legacy agent fields: ' + str(sorted(mixed)))
    unknown = set(spec) - _PUBLIC
    if unknown:
        raise ValueError('unsupported agent fields: ' + str(sorted(unknown)))
    kind = spec.get('type')
    if kind not in ('rule_based', 'llm'):
        raise ValueError('agent.type must be rule_based or llm')
    result = {'reservoir': _text(spec.get('reservoir_id'), 'reservoir_id'), 'agent_type': kind}
    if 'auditors' in spec:
        result['auditors'] = deepcopy(spec['auditors'])
    custom = spec.get('customization', {})
    if not isinstance(custom, dict) or set(custom) - _CUSTOM:
        raise ValueError('unsupported customization fields')
    backend = custom.get('backend')
    if ('parameters' in custom or 'execution' in custom) and backend is None:
        raise ValueError('customization parameters/execution require a backend')
    if backend is not None:
        _text(backend, 'customization.backend')
        if backend in ('configured', 'benchmark'):
            raise ValueError('customization.backend must name a registered extension')
        params = custom.get('parameters', {})
        if not isinstance(params, dict):
            raise ValueError('customization.parameters must be a mapping')
        protected = set(params) & (_PUBLIC | _LEGACY | _CUSTOM)
        if protected:
            raise ValueError('customization.parameters contains protected fields: ' + str(sorted(protected)))
        result.update(deepcopy(params))
        result['strategy'] = backend
    execution = custom.get('execution', 'live')
    if execution not in ('live', 'replay'):
        raise ValueError('customization.execution must be live or replay')
    if kind == 'rule_based':
        if 'model_profile' in spec or 'prompt_file' in spec or set(custom) - {'information'}:
            raise ValueError('rule_based uses a rule module and rule_parameters, without LLM customization')
        rule = _text(spec.get('rule'), 'rule')
        if rule in ('configured', 'benchmark'):
            raise ValueError('rule must name a registered rule module')
        params = spec.get('rule_parameters', {})
        if not isinstance(params, dict):
            raise ValueError('rule_parameters must be a mapping')
        # Only the explicitly selected module interprets algorithm parameters.
        # The framework does not maintain a list of reservoir rule algorithms.
        result.update(mode='offline', strategy=rule, rule_parameters=deepcopy(params))
        if 'information' in custom:
            result['information'] = _text(custom['information'], 'customization.information')
        return result
    if 'rule' in spec or 'rule_parameters' in spec:
        raise ValueError('LLM agents use model_profile and prompt_file, without rule settings')
    result['mode'] = 'offline' if execution == 'replay' else 'llm'
    if result['mode'] == 'llm' or 'model_profile' in spec:
        result['model'] = _text(spec.get('model_profile'), 'model_profile')
    if backend is None or 'prompt_file' in spec:
        result['prompt'] = {'user': _text(spec.get('prompt_file'), 'prompt_file')}
    if 'system_prompt_file' in custom:
        result.setdefault('prompt', {})['system'] = _text(custom['system_prompt_file'], 'system_prompt_file')
    for key in _ADVANCED:
        if key in custom:
            result[key] = deepcopy(custom[key])
    return result
