"""Offline state semantics and legacy daily numerical compatibility."""
import copy
import json
import math
from pathlib import Path
import sys

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from hydrocnhs.rainfall_runoff_model.gwlf import run_GWLF
from hydrocnhs.rainfall_runoff_model.gwlf_hourly import run_GWLF_hourly


def params(**changes):
    p = dict(CN2=75., IS=.2, Res=.12, Sep=.08, Alpha=.3, Beta=.25,
             Ur=10., Kc=1., Df=.24)
    return dict(p, **changes)


def initial(**changes):
    return dict(dict(Area=13., Latitude=41., S0=2., U0=4., SnowS=0.), **changes)


def run_daily(p, x, n=48, **kw):
    return run_GWLF(p, x, np.full(n, 12.), np.zeros(n), np.zeros(n), np.full(n, 12.), **kw)


def run_hourly(p, x, n=48, dt=3600, **kw):
    return run_GWLF_hourly(p, x, np.full(n, 12.), np.zeros(n), np.zeros(n),
                           np.full(n, 12.), dt_seconds=dt, **kw)


@pytest.mark.parametrize('case', json.loads((ROOT / 'tests/fixtures/gwlf_daily_legacy.json').read_text())['cases'])
def test_legacy_daily_default_and_restart_match_prechange_oracle(case):
    p, x, f = case['pars'], case['inputs'], case['forcing']
    q, state = run_GWLF(p, x, **f)
    np.testing.assert_array_equal(q, case['expected_cms'])
    assert state == case['expected_state']
    rows = []
    checked, checked_state = run_GWLF(p, x, **f, diagnostics=rows)
    np.testing.assert_array_equal(checked, case['expected_cms'])
    assert checked_state == case['expected_state']
    if p['Alpha'] > 0:
        assert max(abs(row['mass_balance_residual_m3']) for row in rows) < 2e-9
    cut = case['restart_index']
    q, state = run_GWLF(p, x, **{k:v[cut:] for k,v in f.items()}, vars=case['expected_mid_state'])
    np.testing.assert_array_equal(q, case['expected_cms'][cut:])
    assert state == case['expected_state']


@pytest.mark.parametrize('alpha', [.008265514706237301, .3, 1e-8])
@pytest.mark.parametrize('dt', [900, 1800, 3600])
def test_conversion_matches_closed_dry_recession(alpha, dt):
    from hydrocnhs.rainfall_runoff_model.groundwater import daily_baseflow_to_storage, storage_to_daily_baseflow
    bf = .24
    b = daily_baseflow_to_storage(bf, alpha)
    assert storage_to_daily_baseflow(b, alpha) == pytest.approx(bf, rel=2e-15)
    p = params(Res=0., Sep=0., Alpha=alpha)
    daily, _ = run_daily(p, initial(BF0=bf, S0=0., U0=0.), n=1)
    rows = []
    hourly, state = run_hourly(p, initial(B0=b, S0=0., U0=0.), n=86400//dt, dt=dt, diagnostics=rows)
    assert float(daily.sum()) * 86400 == pytest.approx(float(hourly.sum()) * dt, rel=2e-13)
    assert state['B'] == pytest.approx(b * math.exp(-alpha), rel=2e-13)


@pytest.mark.parametrize('dt', [900, 1800, 3600])
def test_hourly_BF0_and_B0_are_equivalent_and_restart_does_not_reinitialize(dt):
    from hydrocnhs.rainfall_runoff_model.groundwater import daily_baseflow_to_storage
    p = params(); b = daily_baseflow_to_storage(.24, p['Alpha'])
    q, final = run_hourly(p, initial(BF0=.24), dt=dt)
    expected, expected_state = run_hourly(p, initial(B0=b), dt=dt)
    np.testing.assert_array_equal(q, expected)
    assert final == expected_state
    first, mid = run_hourly(p, initial(BF0=.24), n=17, dt=dt)
    second, split = run_hourly(p, initial(BF0=999.), n=31, dt=dt, vars=json.loads(json.dumps(mid)))
    np.testing.assert_array_equal(np.concatenate([first, second]), q)
    assert split == final


def test_daily_explicit_state_and_diagnostics_do_not_change_legacy_results():
    from hydrocnhs.rainfall_runoff_model.groundwater import daily_baseflow_to_storage
    p = params(); x = initial(); expected, state = run_daily(p, x)
    rows = []
    q, final = run_daily(p, dict(x, BF0=p['Res']*x['S0']), diagnostics=rows)
    np.testing.assert_array_equal(q, expected); assert final == state
    b = daily_baseflow_to_storage(p['Res']*x['S0'], p['Alpha'])
    qb, _ = run_daily(p, dict(x, B0=b))
    np.testing.assert_allclose(qb, expected, rtol=2e-15, atol=1e-15)
    assert len(rows) == 48
    for row in rows:
        assert row['mass_balance_status'] == 'COMPUTABLE'
        assert abs(row['mass_balance_residual_m3']) < 1e-9
        for boundary in ['start', 'end']:
            assert row[f'storage_{boundary}_cm'] == pytest.approx(sum(row[f'{s}_{boundary}_cm'] for s in ['U','S','B','snow']))
    json.dumps(rows, allow_nan=False)


def test_hourly_diagnostics_expose_each_store_without_affecting_chunk_equality():
    p, x = params(), initial(B0=2.)
    full_rows = []; q, final = run_hourly(p, x, diagnostics=full_rows)
    rows = []; first, mid = run_hourly(p, x, n=17, diagnostics=rows)
    second, split = run_hourly(p, x, n=31, vars=mid, diagnostics=rows)
    np.testing.assert_array_equal(np.concatenate([first, second]), q)
    assert split == final and rows == full_rows
    for r in rows:
        assert r['deep_recharge_cm'] == pytest.approx(r['seepage_cm']-r['deep_loss_cm'])
        assert r['B_end_cm'] == pytest.approx(r['B_start_cm']+r['deep_recharge_cm']-r['baseflow_cm'])
        assert r['initial_abstraction_cm'] is None or r['initial_abstraction_cm'] >= 0
        for side in ['start','end']:
            assert r[f'storage_{side}_cm'] == pytest.approx(sum(r[f'{k}_{side}_cm'] for k in ['U','S','B','snow']))


def test_daily_zero_alpha_preserves_legacy_flow_but_does_not_fabricate_deep_storage():
    p = params(Alpha=0.)
    before, state = run_daily(p, initial())
    rows = []; q, final = run_daily(p, initial(), diagnostics=rows)
    np.testing.assert_array_equal(q, before); assert final == state
    assert all(r['B_start_cm'] is None and r['B_end_cm'] is None for r in rows)
    assert all(r['mass_balance_residual_m3'] is None and r['mass_balance_status'] == 'UNAVAILABLE_ZERO_ALPHA' for r in rows)
    json.dumps(rows, allow_nan=False)


@pytest.mark.parametrize('value', [True, -1., math.nan, math.inf, '1'])
def test_invalid_explicit_initialization_is_rejected_before_output(value):
    for fn, x in [(run_daily, initial(BF0=value)), (run_hourly, initial(B0=value))]:
        rows = [{'sentinel': True}]
        with pytest.raises(ValueError): fn(params(), x, diagnostics=rows)
        assert rows == [{'sentinel': True}]


def test_ambiguous_initialization_and_undefined_conversion_fail():
    from hydrocnhs.rainfall_runoff_model.groundwater import daily_baseflow_to_storage, storage_to_daily_baseflow
    for fn in [run_daily, run_hourly]:
        with pytest.raises(ValueError, match='exactly one'):
            fn(params(), initial(BF0=.24, B0=2.))
    for alpha in [0., -1., math.nan, True]:
        with pytest.raises(ValueError): daily_baseflow_to_storage(.24, alpha)
        with pytest.raises(ValueError): storage_to_daily_baseflow(2., alpha)
    with pytest.raises(ValueError): run_hourly(params(Alpha=0.), initial(BF0=0.))


def test_daily_restart_uses_saved_state_over_initialization_and_keeps_inputs_unmodified():
    p, x = params(), initial(BF0=.3)
    before = copy.deepcopy(x); _, state = run_daily(p, x, n=17)
    state_before = copy.deepcopy(state)
    q, final = run_daily(p, dict(x, BF0=999.), n=31, vars=state)
    full, expected = run_daily(p, x, n=48)
    np.testing.assert_array_equal(q, full[17:]); assert final == expected
    assert x == before and state == state_before


@pytest.mark.parametrize('field', ['temp', 'prec', 'pet', 'monthly_Tavg'])
def test_daily_invalid_diagnostic_forcing_does_not_append(field):
    f = dict(temp=[12.,12.], prec=[0.,0.], pet=[0.,0.], monthly_Tavg=[12.,12.])
    f[field][1] = math.nan
    rows = [{'sentinel': True}]
    with pytest.raises(ValueError, match='finite'):
        run_GWLF(params(), initial(), **f, diagnostics=rows)
    assert rows == [{'sentinel': True}]
