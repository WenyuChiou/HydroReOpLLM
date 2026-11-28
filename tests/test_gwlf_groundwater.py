"""Offline state semantics and daily numerical compatibility for GWLF."""
import copy
import json
import math
from pathlib import Path
import sys

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from hydrocnhs.rainfall_runoff_model.gwlf import run_GWLF


def params(**changes):
    p = dict(CN2=75., IS=.2, Res=.12, Sep=.08, Alpha=.3, Beta=.25, Ur=10., Kc=1., Df=.24)
    return dict(p, **changes)


def initial(**changes):
    return dict(dict(Area=13., Latitude=41., S0=2., U0=4., SnowS=0.), **changes)


def run_daily(p, x, n=48, **kw):
    return run_GWLF(p, x, np.full(n, 12.), np.zeros(n), np.zeros(n), np.full(n, 12.), **kw)


def test_groundwater_storage_conversion_roundtrip_and_invalid_inputs():
    from hydrocnhs.rainfall_runoff_model.groundwater import daily_baseflow_to_storage, storage_to_daily_baseflow

    for alpha in (.008265514706237301, .3, 1e-8):
        bf = .24
        b = daily_baseflow_to_storage(bf, alpha)
        assert storage_to_daily_baseflow(b, alpha) == pytest.approx(bf, rel=2e-15)

    for alpha in (0., -1., math.nan, True):
        with pytest.raises(ValueError):
            daily_baseflow_to_storage(.24, alpha)
        with pytest.raises(ValueError):
            storage_to_daily_baseflow(2., alpha)


def test_daily_explicit_state_and_diagnostics_do_not_change_legacy_results():
    from hydrocnhs.rainfall_runoff_model.groundwater import daily_baseflow_to_storage

    p = params()
    x = initial()
    expected, state = run_daily(p, x)
    rows = []
    q, final = run_daily(p, dict(x, BF0=p["Res"] * x["S0"]), diagnostics=rows)
    np.testing.assert_array_equal(q, expected)
    assert final == state
    b = daily_baseflow_to_storage(p["Res"] * x["S0"], p["Alpha"])
    qb, _ = run_daily(p, dict(x, B0=b))
    np.testing.assert_allclose(qb, expected, rtol=2e-15, atol=1e-15)
    assert len(rows) == 48
    for row in rows:
        assert row["mass_balance_status"] == "COMPUTABLE"
        assert abs(row["mass_balance_residual_m3"]) < 1e-9
        for boundary in ("start", "end"):
            assert row[f"storage_{boundary}_cm"] == pytest.approx(
                sum(row[f"{s}_{boundary}_cm"] for s in ("U", "S", "B", "snow"))
            )
    json.dumps(rows, allow_nan=False)


def test_daily_zero_alpha_preserves_legacy_flow_but_does_not_fabricate_deep_storage():
    p = params(Alpha=0.)
    before, state = run_daily(p, initial())
    rows = []
    q, final = run_daily(p, initial(), diagnostics=rows)
    np.testing.assert_array_equal(q, before)
    assert final == state
    assert all(r["B_start_cm"] is None and r["B_end_cm"] is None for r in rows)
    assert all(
        r["mass_balance_residual_m3"] is None and r["mass_balance_status"] == "UNAVAILABLE_ZERO_ALPHA"
        for r in rows
    )
    json.dumps(rows, allow_nan=False)


@pytest.mark.parametrize("value", [True, -1., math.nan, math.inf, "1"])
def test_invalid_explicit_initialization_is_rejected_before_output(value):
    rows = [{"sentinel": True}]
    with pytest.raises(ValueError):
        run_daily(params(), initial(BF0=value), diagnostics=rows)
    assert rows == [{"sentinel": True}]


def test_ambiguous_daily_initialization_fails():
    with pytest.raises(ValueError, match="exactly one"):
        run_daily(params(), initial(BF0=.24, B0=2.))


def test_daily_restart_uses_saved_state_over_initialization_and_keeps_inputs_unmodified():
    p, x = params(), initial(BF0=.3)
    before = copy.deepcopy(x)
    _, state = run_daily(p, x, n=17)
    state_before = copy.deepcopy(state)
    q, final = run_daily(p, dict(x, BF0=999.), n=31, vars=state)
    full, expected = run_daily(p, x, n=48)
    np.testing.assert_array_equal(q, full[17:])
    assert final == expected
    assert x == before and state == state_before


@pytest.mark.parametrize("field", ["temp", "prec", "pet", "monthly_Tavg"])
def test_daily_invalid_diagnostic_forcing_does_not_append(field):
    f = dict(temp=[12., 12.], prec=[0., 0.], pet=[0., 0.], monthly_Tavg=[12., 12.])
    f[field][1] = math.nan
    rows = [{"sentinel": True}]
    with pytest.raises(ValueError, match="finite"):
        run_GWLF(params(), initial(), **f, diagnostics=rows)
    assert rows == [{"sentinel": True}]
