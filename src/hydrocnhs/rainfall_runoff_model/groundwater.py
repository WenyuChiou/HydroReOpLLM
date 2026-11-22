"""Explicit boundary-state semantics for the daily and hourly GWLF kernels.

For a=exp(-Alpha), B=BFt*a/(1-a) maps legacy reference-day discharge depth
to storage at the same pre-step boundary. This is a dry-recession equivalence,
not a migration of soil/CN history or a validation of transferred parameters.
"""
from __future__ import annotations

import math
from numbers import Real

import numpy as np

CONVERSION_VERSION = 'gwlf-groundwater-boundary.v1'


def _nonnegative(value, name):
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, Real):
        raise ValueError(f'{name} must be a finite nonnegative number')
    number = float(value)
    if not math.isfinite(number) or number < 0:
        raise ValueError(f'{name} must be a finite nonnegative number')
    return number


def _positive_alpha(alpha):
    alpha = _nonnegative(alpha, 'Alpha')
    if alpha == 0:
        raise ValueError('Alpha must be positive to map daily BF to a finite deep store')
    return alpha


def daily_baseflow_to_storage(baseflow_cm_per_day, alpha_per_day):
    """Convert pre-step legacy BF (cm/reference day) to deep storage (cm)."""
    bf = _nonnegative(baseflow_cm_per_day, 'BF0')
    alpha = _positive_alpha(alpha_per_day)
    value = bf * math.exp(-alpha) / -math.expm1(-alpha)
    if not math.isfinite(value):
        raise ValueError('BF0/Alpha produces nonfinite equivalent deep storage')
    return value


def storage_to_daily_baseflow(storage_cm, alpha_per_day):
    """Convert pre-step deep storage (cm) to legacy BF (cm/reference day)."""
    storage = _nonnegative(storage_cm, 'B0')
    alpha = _positive_alpha(alpha_per_day)
    try:
        value = storage * math.expm1(alpha)
    except OverflowError as exc:
        raise ValueError('B0/Alpha produces nonfinite equivalent daily baseflow') from exc
    if not math.isfinite(value):
        raise ValueError('B0/Alpha produces nonfinite equivalent daily baseflow')
    return value


def initialize_groundwater(pars, inputs, *, scale):
    """Resolve cold-start B0(cm) or BF0(cm/reference day), never both.

    Daily omitting both retains BF0=Res*S0. Hourly requires one explicit state.
    Kernel-specific restart dictionaries take precedence at execution.
    """
    if scale not in ('daily', 'hourly'):
        raise ValueError('groundwater scale must be daily or hourly')
    supplied = [key for key in ('B0', 'BF0') if key in inputs]
    if len(supplied) > 1 or (scale == 'hourly' and not supplied):
        raise ValueError('initial groundwater requires exactly one of B0 or BF0')
    alpha = _nonnegative(pars['Alpha'], 'Alpha')
    source = supplied[0] if supplied else 'legacy-daily-Res*S0'
    if source == 'B0':
        deep = _nonnegative(inputs['B0'], 'B0')
        bf = storage_to_daily_baseflow(deep, alpha) if scale == 'daily' else None
    else:
        bf = (_nonnegative(inputs['BF0'], 'BF0') if source == 'BF0' else
              _nonnegative(pars['Res'], 'Res') * _nonnegative(inputs['S0'], 'S0'))
        deep = daily_baseflow_to_storage(bf, alpha) if alpha > 0 or scale == 'hourly' else None
    return dict(conversion_version=CONVERSION_VERSION, source=source,
                daily_baseflow_cm_per_day=bf, deep_storage_cm=deep,
                mass_balance_status='COMPUTABLE' if deep is not None else 'UNAVAILABLE_ZERO_ALPHA')


def daily_with_diagnostics(**kwargs):
    """Return diagnostics through joblib results, not child-process list mutation."""
    from .gwlf import run_GWLF
    records = []
    q, state = run_GWLF(**kwargs, diagnostics=records)
    return q, state, records


def validate_daily_diagnostics(pars, inputs, forcing, state):
    """Validate the opt-in diagnostic path without tightening legacy defaults."""
    lengths = set()
    for name, values in forcing.items():
        try:
            array = np.asarray(values, dtype=float)
        except (TypeError, ValueError) as exc:
            raise ValueError(f'{name} must contain finite daily values') from exc
        if array.ndim != 1 or not np.isfinite(array).all():
            raise ValueError(f'{name} must contain finite daily values')
        if name in ('prec', 'pet') and (array < 0).any():
            raise ValueError(f'{name} must contain nonnegative daily depths')
        lengths.add(len(array))
    if len(lengths) != 1:
        raise ValueError('daily diagnostic forcing arrays must have equal length')
    for name, value in state.items():
        _nonnegative(value, name)
    if _nonnegative(inputs['Area'], 'Area') <= 0:
        raise ValueError('diagnostic Area must be positive')
    p = {key: _nonnegative(pars[key], key) for key in ('CN2','IS','Res','Sep','Alpha','Beta','Ur','Kc','Df')}
    if not 0 < p['CN2'] <= 100 or p['Ur'] <= 0 or p['IS'] > 1 or p['Beta'] > 1 or p['Res'] + p['Sep'] > 1:
        raise ValueError('daily diagnostic parameters are outside the physical domain')
