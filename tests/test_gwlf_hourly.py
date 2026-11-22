"""Contract tests for the experimental, interval-depth GWLF sibling kernel."""

import copy
import hashlib
import json
import math
from pathlib import Path
import sys

import numpy as np
import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from hydrocnhs.rainfall_runoff_model.gwlf_hourly import run_GWLF_hourly


DT_VALUES = (3600, 1800, 900)
LEGACY_GWLF_SHA256 = "dda966f80df3b7ac9c0f5be84c313907f1e54c13e09dbc54d606b28728530a30"


def parameters(**changes):
    values = dict(CN2=75.0, IS=0.2, Res=0.12, Sep=0.08, Alpha=0.3,
                  Beta=0.25, Ur=10.0, Kc=1.0, Df=0.24)
    values.update(changes)
    return values


def initial_inputs(**changes):
    values = dict(Area=13.0, S0=0.0, U0=0.0, SnowS=0.0, B0=0.0)
    values.update(changes)
    return values


def execute(n, *, pars=None, inputs=None, temp=None, prec=None, pet=None,
            monthly_Tavg=None, **options):
    return run_GWLF_hourly(
        parameters() if pars is None else pars,
        initial_inputs() if inputs is None else inputs,
        np.full(n, 5.0) if temp is None else temp,
        np.zeros(n) if prec is None else prec,
        np.zeros(n) if pet is None else pet,
        np.full(n, 5.0) if monthly_Tavg is None else monthly_Tavg,
        **options,
    )


def cumulative_excess(liquid_cm, cn, interception):
    retention = 2540.0 / cn - 25.4
    if liquid_cm <= interception * retention:
        return 0.0
    return ((liquid_cm - interception * retention) ** 2
            / (liquid_cm + (1.0 - interception) * retention))


def dry_cn(cn2):
    return 4.2 * cn2 / (10.0 - 0.058 * cn2)


def wet_cn(cn2):
    return 23.0 * cn2 / (10.0 + 0.13 * cn2)


def assert_mass_closure(cms, state, diagnostics, inputs, dt):
    conversion = 100.0 * inputs["Area"]  # cm over ha -> m3
    assert len(diagnostics) == len(cms)
    assert np.isfinite(cms).all()
    assert (cms >= 0).all()
    for discharge, row in zip(cms, diagnostics):
        components = (row["quickflow_cm"] + row["shallow_flow_cm"]
                      + row["baseflow_cm"])
        assert discharge * dt == pytest.approx(components * conversion, abs=1e-10)
        residual = (row["precipitation_cm"] * conversion - discharge * dt
                    - (row["actual_et_cm"] + row["deep_loss_cm"]
                       + row["storage_end_cm"] - row["storage_start_cm"])
                    * conversion)
        assert residual == pytest.approx(0.0, abs=2e-9)
        assert row["mass_balance_residual_m3"] == pytest.approx(residual, abs=2e-9)
        assert math.isfinite(row["runoff_roundoff_adjustment_cm"])
        assert abs(row["runoff_roundoff_adjustment_cm"]) < 1e-12
    for name in ("U", "S", "B", "snow"):
        assert math.isfinite(state[name])
        assert state[name] >= 0.0
    initial_storage = sum(inputs[name] for name in ("U0", "S0", "B0", "SnowS"))
    final_storage = sum(state[name] for name in ("U", "S", "B", "snow"))
    precipitation = math.fsum(row["precipitation_cm"] for row in diagnostics)
    loss = math.fsum(row["actual_et_cm"] + row["deep_loss_cm"] for row in diagnostics)
    assert precipitation * conversion == pytest.approx(
        float(np.sum(cms)) * dt + (loss + final_storage - initial_storage) * conversion,
        abs=3e-8,
    )


@pytest.mark.parametrize("dt", DT_VALUES)
def test_24_hour_shallow_recession_preserves_daily_survival_and_res_sep_partition(dt):
    pars = parameters(Alpha=0.0)
    inputs = initial_inputs(S0=10.0, B0=2.0)
    rows = []
    cms, state = execute(86400 // dt, pars=pars, inputs=inputs,
                         dt_seconds=dt, diagnostics=rows)
    total_fraction = pars["Res"] + pars["Sep"]
    assert state["S"] == pytest.approx(inputs["S0"] * (1.0 - total_fraction), abs=2e-13)
    assert math.fsum(row["shallow_flow_cm"] for row in rows) == pytest.approx(1.2)
    assert math.fsum(row["seepage_cm"] for row in rows) == pytest.approx(0.8)
    assert math.fsum(row["deep_loss_cm"] for row in rows) == pytest.approx(0.2)
    assert state["B"] == pytest.approx(2.6)
    assert all(row["baseflow_cm"] == 0.0 for row in rows)
    interval_loss = 1.0 - (1.0 - total_fraction) ** (dt / 86400.0)
    expected_shallow = inputs["S0"] * interval_loss * pars["Res"] / total_fraction
    assert cms[0] == pytest.approx(expected_shallow * 100.0 * inputs["Area"] / dt)
    assert_mass_closure(cms, state, rows, inputs, dt)


@pytest.mark.parametrize("dt", DT_VALUES)
def test_explicit_deep_storage_has_analytical_exponential_recession(dt):
    pars = parameters(Res=0.0, Sep=0.0, Alpha=0.36)
    inputs = initial_inputs(B0=4.0)
    rows = []
    n = 2 * 86400 // dt
    cms, state = execute(n, pars=pars, inputs=inputs, dt_seconds=dt, diagnostics=rows)
    expected_storage = inputs["B0"] * math.exp(-pars["Alpha"] * 2.0)
    assert state["B"] == pytest.approx(expected_storage, abs=2e-13)
    expected_survival = math.exp(-pars["Alpha"] * dt / 86400.0)
    expected_depths = [inputs["B0"] * expected_survival ** step
                       * (1.0 - expected_survival) for step in range(n)]
    np.testing.assert_allclose([row["baseflow_cm"] for row in rows], expected_depths,
                               rtol=2e-13, atol=1e-14)
    assert math.fsum(row["baseflow_cm"] for row in rows) == pytest.approx(
        inputs["B0"] - expected_storage)
    assert_mass_closure(cms, state, rows, inputs, dt)


def test_deep_recharge_and_outflow_share_explicit_mass_storage():
    pars = parameters(Alpha=0.7, Beta=0.25)
    inputs = initial_inputs(S0=10.0, B0=2.0)
    rows = []
    cms, state = execute(1, pars=pars, inputs=inputs, diagnostics=rows)
    seepage = inputs["S0"] * (1.0 - 0.8 ** (1.0 / 24.0)) * 0.08 / 0.2
    recharge = (1.0 - pars["Beta"]) * seepage
    expected_flow = (inputs["B0"] + recharge) * (1.0 - math.exp(-0.7 / 24.0))
    assert rows[0]["seepage_cm"] == pytest.approx(seepage)
    assert rows[0]["baseflow_cm"] == pytest.approx(expected_flow)
    assert state["B"] == pytest.approx(inputs["B0"] + recharge - expected_flow)
    assert_mass_closure(cms, state, rows, inputs, 3600)


@pytest.mark.parametrize("dt", DT_VALUES)
def test_cumulative_cn_excess_is_invariant_for_partitioned_single_storm(dt):
    pars = parameters(Res=0.0, Sep=0.0, Alpha=0.0, Ur=100.0)
    inputs = initial_inputs()
    n = 6 * 3600 // dt
    rows = []
    cms, state = execute(n, pars=pars, inputs=inputs, prec=np.full(n, 12.0 / n),
                         dt_seconds=dt, diagnostics=rows)
    cn = dry_cn(pars["CN2"])
    expected_runoff = cumulative_excess(12.0, cn, pars["IS"])
    assert math.fsum(row["quickflow_cm"] for row in rows) == pytest.approx(expected_runoff)
    assert state["event"]["input_cm"] == pytest.approx(12.0)
    assert state["event"]["runoff_cm"] == pytest.approx(expected_runoff)
    assert all(row["cn"] == pytest.approx(cn) for row in rows)
    assert state["U"] == pytest.approx(12.0 - expected_runoff)
    assert cms.dtype.kind == "f"
    assert cms.shape == (n,)
    assert_mass_closure(cms, state, rows, inputs, dt)


@pytest.mark.parametrize("dt", DT_VALUES)
def test_antecedent_history_spans_120_physical_hours_and_excludes_current_input(dt):
    pars = parameters(Res=0.0, Sep=0.0, Ur=100.0)
    inputs = initial_inputs(AnteMoisHourly=[4.0 * dt / 3600.0] * (120 * 3600 // dt))
    observed = []
    for preceding_hours in (119, 120):
        _, state = execute(preceding_hours * 3600 // dt, pars=pars, inputs=inputs,
                           dt_seconds=dt)
        rows = []
        _, state = execute(1, pars=pars, inputs=inputs, prec=[0.1], vars=state,
                           dt_seconds=dt, diagnostics=rows)
        assert len(state["liquid_history_cm"]) == 120 * 3600 // dt
        assert state["history_initialization"] == "provided"
        observed.append(rows[0]["cn"])
    assert observed[0] == pytest.approx(wet_cn(pars["CN2"]))
    assert observed[1] == pytest.approx(dry_cn(pars["CN2"]))


@pytest.mark.parametrize("dt", DT_VALUES)
def test_event_cn_is_frozen_while_recent_liquid_input_and_season_change(dt):
    n = 10 * 3600 // dt
    pars = parameters(Res=0.0, Sep=0.0, Ur=100.0)
    rows = []
    _, state = execute(n, pars=pars, prec=np.full(n, 20.0 / n),
                       monthly_Tavg=np.linspace(0.0, 25.0, n),
                       dt_seconds=dt, diagnostics=rows)
    assert all(row["cn"] == pytest.approx(dry_cn(pars["CN2"])) for row in rows)
    assert sum(state["liquid_history_cm"]) == pytest.approx(20.0)
    assert state["history_initialization"] == "zero-filled"


@pytest.mark.parametrize("dt", DT_VALUES)
def test_event_abstraction_resets_at_exactly_24_dry_hours(dt):
    pars = parameters(Res=0.0, Sep=0.0, Ur=100.0)
    inputs = initial_inputs()
    _, first = execute(1, pars=pars, inputs=inputs, prec=[6.0], dt_seconds=dt)
    almost_gap = 24 * 3600 // dt - 1
    _, retained = execute(almost_gap, pars=pars, inputs=inputs, vars=first, dt_seconds=dt)
    assert retained["event"]["input_cm"] == pytest.approx(6.0)
    assert retained["event"]["dry_seconds"] == 86400 - dt
    retained_rows = []
    execute(1, pars=pars, inputs=inputs, vars=retained, prec=[1.0],
            dt_seconds=dt, diagnostics=retained_rows)
    assert retained_rows[0]["event_input_cm"] == pytest.approx(7.0)
    assert retained_rows[0]["cn"] == pytest.approx(dry_cn(pars["CN2"]))
    _, expired = execute(1, pars=pars, inputs=inputs, vars=retained, dt_seconds=dt)
    assert expired["event"]["cn"] is None
    assert expired["event"]["input_cm"] == 0.0
    assert expired["event"]["runoff_cm"] == 0.0
    new_rows = []
    execute(1, pars=pars, inputs=inputs, vars=expired, prec=[1.0],
            dt_seconds=dt, diagnostics=new_rows)
    assert new_rows[0]["event_input_cm"] == pytest.approx(1.0)
    assert new_rows[0]["cn"] == pytest.approx(wet_cn(pars["CN2"]))


@pytest.mark.parametrize("dt", DT_VALUES)
def test_snowmelt_uses_daily_degree_factor_and_pet_is_already_interval_depth(dt):
    pars = parameters(Res=0.0, Sep=0.0, Alpha=0.0, Df=0.24, Ur=100.0)
    inputs = initial_inputs(U0=60.0, SnowS=5.0)
    n = 86400 // dt
    rows = []
    cms, state = execute(n, pars=pars, inputs=inputs, temp=np.full(n, 5.0),
                         pet=np.full(n, 0.48 / n), dt_seconds=dt, diagnostics=rows)
    assert math.fsum(row["melt_cm"] for row in rows) == pytest.approx(1.2)
    assert math.fsum(row["actual_et_cm"] for row in rows) == pytest.approx(0.48)
    assert state["snow"] == pytest.approx(3.8)
    assert state["U"] == pytest.approx(60.72)
    assert_mass_closure(cms, state, rows, inputs, dt)


def test_snowfall_accumulates_and_melt_cannot_exceed_available_snow():
    inputs = initial_inputs(SnowS=0.1)
    rows = []
    cms, state = execute(2, inputs=inputs, temp=[-1.0, 100.0], prec=[0.4, 0.0],
                         diagnostics=rows)
    assert rows[0]["rain_cm"] == 0.0
    assert rows[0]["melt_cm"] == 0.0
    assert rows[1]["melt_cm"] == pytest.approx(0.5)
    assert state["snow"] == 0.0
    assert_mass_closure(cms, state, rows, inputs, 3600)


@pytest.mark.parametrize("dt", DT_VALUES)
def test_json_split_restart_is_exact_and_does_not_mutate_caller_objects(dt):
    n = 72 * 3600 // dt
    intervals_per_hour = 3600 // dt
    temp = np.repeat(np.tile([-2.0, 4.0, 8.0], 24), intervals_per_hour)
    prec = np.repeat(np.tile([0.2, 0.7, 0.0, 0.0, 0.0, 0.0], 12)
                     / intervals_per_hour, intervals_per_hour)
    pet = np.full(n, 0.01 / intervals_per_hour)
    monthly = np.linspace(5.0, 20.0, n)
    inputs = initial_inputs(S0=4.0, U0=3.0, B0=2.0, SnowS=1.0)
    pars = parameters(Ur=5.0)
    before = copy.deepcopy((inputs, pars, temp, prec, pet, monthly))
    full_rows = []
    full, expected_state = execute(n, pars=pars, inputs=inputs, temp=temp, prec=prec,
                                   pet=pet, monthly_Tavg=monthly, dt_seconds=dt,
                                   diagnostics=full_rows)
    pieces, rows, state = [], [], None
    start = 0
    for stop in (5 * intervals_per_hour, 25 * intervals_per_hour, n):
        previous = copy.deepcopy(state)
        part, updated = execute(stop - start, pars=pars, inputs=inputs,
                                temp=temp[start:stop], prec=prec[start:stop],
                                pet=pet[start:stop], monthly_Tavg=monthly[start:stop],
                                vars=state, dt_seconds=dt, diagnostics=rows)
        assert state == previous
        state = json.loads(json.dumps(updated, allow_nan=False))
        pieces.append(part)
        start = stop
    np.testing.assert_array_equal(np.concatenate(pieces), full)
    assert state == expected_state
    assert rows == full_rows
    assert state["schema_version"] == "gwlf-hourly-state.v1"
    assert state["steps_completed"] == n
    assert inputs == before[0]
    assert pars == before[1]
    for actual, original in zip((temp, prec, pet, monthly), before[2:]):
        np.testing.assert_array_equal(actual, original)
    assert_mass_closure(full, expected_state, full_rows, inputs, dt)


@pytest.mark.parametrize("name,value", [
    ("CN2", 0.0), ("CN2", 100.01), ("IS", -0.01), ("IS", 1.01),
    ("Res", -0.01), ("Sep", -0.01), ("Res", 0.92),
    ("Alpha", -0.01), ("Beta", -0.01), ("Beta", 1.01),
    ("Ur", 0.0), ("Kc", -0.01), ("Df", -0.01),
    ("CN2", math.nan), ("Res", math.inf), ("Alpha", -math.inf),
])
def test_invalid_parameter_domain_rejected_before_diagnostics(name, value):
    rows = [{"sentinel": True}]
    with pytest.raises((ValueError, TypeError)):
        execute(2, pars=parameters(**{name: value}), diagnostics=rows)
    assert rows == [{"sentinel": True}]


@pytest.mark.parametrize("name,value", [
    ("Area", 0.0), ("Area", -1.0), ("Area", math.nan),
    ("S0", -1.0), ("U0", -1.0), ("SnowS", -1.0), ("B0", -1.0),
    ("B0", math.inf), ("U0", math.nan),
    ("AnteMoisHourly", [0.0] * 119),
    ("AnteMoisHourly", [-1.0] + [0.0] * 119),
    ("AnteMoisHourly", [math.nan] + [0.0] * 119),
])
def test_invalid_initial_input_rejected_atomically(name, value):
    rows = [{"sentinel": True}]
    with pytest.raises((ValueError, TypeError)):
        execute(2, inputs=initial_inputs(**{name: value}), diagnostics=rows)
    assert rows == [{"sentinel": True}]


def test_explicit_deep_initial_storage_is_required():
    inputs = initial_inputs()
    del inputs["B0"]
    with pytest.raises((ValueError, KeyError)):
        execute(1, inputs=inputs)


@pytest.mark.parametrize("name,value", [
    ("temp", [5.0, math.nan]), ("prec", [0.0, math.inf]),
    ("pet", [0.0, -0.1]), ("prec", [0.0, -0.1]),
    ("monthly_Tavg", [5.0, -math.inf]), ("prec", [[0.0], [0.0]]),
    ("pet", [0.0]), ("monthly_Tavg", [5.0]), ("temp", 5.0),
])
def test_complete_forcing_is_validated_before_any_diagnostics_append(name, value):
    rows = [{"sentinel": True}]
    with pytest.raises((ValueError, TypeError)):
        execute(2, diagnostics=rows, **{name: value})
    assert rows == [{"sentinel": True}]


@pytest.mark.parametrize("dt", [True, False, 60, 86400, 3600.5, 0, -900, math.nan])
def test_unsupported_timesteps_are_rejected(dt):
    with pytest.raises((ValueError, TypeError)):
        execute(1, dt_seconds=dt)


@pytest.mark.parametrize("gap", [0.0, -1.0, math.nan, math.inf])
def test_invalid_dry_gaps_are_rejected(gap):
    with pytest.raises((ValueError, TypeError)):
        execute(1, dry_gap_hours=gap)


@pytest.mark.parametrize("change", ["parameters", "area", "dry_gap", "timestep"])
def test_restart_rejects_changed_fixed_configuration_atomically(change):
    pars, inputs = parameters(), initial_inputs()
    _, state = execute(2, pars=pars, inputs=inputs, prec=[0.0, 0.5])
    options = {}
    if change == "parameters":
        pars["CN2"] += 1.0
    elif change == "area":
        inputs["Area"] += 1.0
    elif change == "dry_gap":
        options["dry_gap_hours"] = 12.0
    else:
        options["dt_seconds"] = 1800
    before = copy.deepcopy(state)
    rows = [{"sentinel": True}]
    with pytest.raises((ValueError, TypeError)):
        execute(1, pars=pars, inputs=inputs, vars=state, diagnostics=rows, **options)
    assert rows == [{"sentinel": True}]
    assert state == before


@pytest.mark.parametrize("path,value", [
    (("schema_version",), "daily"), (("model_version",), "unrecognized"),
    (("U",), -0.01), (("S",), math.nan), (("B",), math.inf), (("snow",), -0.01),
    (("steps_completed",), -1), (("steps_completed",), 1.5),
    (("liquid_history_cm",), [0.0] * 119),
    (("liquid_history_cm",), [-1.0] + [0.0] * 119),
    (("liquid_history_cm",), [math.nan] + [0.0] * 119),
    (("event", "cn"), None), (("event", "cn"), 101.0),
    (("event", "input_cm"), -0.01), (("event", "runoff_cm"), 20.0),
    (("event", "runoff_cm"), 0.01), (("event", "dry_seconds"), -3600),
    (("event", "dry_seconds"), 1),
])
def test_invalid_restart_state_is_rejected_before_diagnostics(path, value):
    _, state = execute(1, prec=[0.5])
    target = state
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    before = copy.deepcopy(state)
    rows = [{"sentinel": True}]
    with pytest.raises((ValueError, TypeError)):
        execute(2, vars=state, diagnostics=rows)
    assert rows == [{"sentinel": True}]
    # NaN is intentionally invalid and requires a representation-based comparison.
    assert json.dumps(state, sort_keys=True) == json.dumps(before, sort_keys=True)


def test_legacy_daily_restart_state_is_rejected():
    state = dict(BFt=1.0, St=1.0, Ut=1.0, SnowSt=0.0, AnteMois=[0.0] * 5)
    with pytest.raises((ValueError, TypeError)):
        execute(1, vars=state)


@pytest.mark.parametrize("dt", DT_VALUES)
def test_cn2_100_wet_cold_start_survives_json_restart(dt):
    pars = parameters(CN2=100.0)
    inputs = initial_inputs()
    full_rows = []
    full, full_state = execute(2, pars=pars, inputs=inputs, prec=[1.0, 0.5],
                               dt_seconds=dt, diagnostics=full_rows)
    rows = []
    first, state = execute(1, pars=pars, inputs=inputs, prec=[1.0],
                           dt_seconds=dt, diagnostics=rows)
    state = json.loads(json.dumps(state, allow_nan=False))
    assert state["event"]["cn"] == 100.0
    second, state = execute(1, pars=pars, inputs=inputs, prec=[0.5], vars=state,
                            dt_seconds=dt, diagnostics=rows)
    np.testing.assert_array_equal(np.concatenate((first, second)), full)
    assert state == full_state
    assert rows == full_rows
    assert [row["quickflow_cm"] for row in rows] == [1.0, 0.5]
    assert_mass_closure(full, full_state, full_rows, inputs, dt)


@pytest.mark.parametrize("dt", DT_VALUES)
def test_zero_sep_produces_exactly_zero_deep_flux_and_storage(dt):
    pars = parameters(Res=0.02, Sep=0.0)
    inputs = initial_inputs(S0=1.0, B0=0.0)
    rows = []
    cms, state = execute(86400 // dt, pars=pars, inputs=inputs,
                         dt_seconds=dt, diagnostics=rows)
    assert state["S"] == pytest.approx(0.98, abs=2e-13)
    assert math.fsum(row["shallow_flow_cm"] for row in rows) == pytest.approx(0.02)
    for row in rows:
        assert row["seepage_cm"] == 0.0
        assert row["deep_loss_cm"] == 0.0
        assert row["baseflow_cm"] == 0.0
    assert state["B"] == 0.0
    assert_mass_closure(cms, state, rows, inputs, dt)


def test_daily_gwlf_local_extension_preserves_upstream_provenance():
    source = ROOT / "src/hydrocnhs/rainfall_runoff_model/gwlf.py"
    entry = json.loads((ROOT / "third_party/hydrocnhs/SOURCE.json").read_text())["files"][
        "src/hydrocnhs/rainfall_runoff_model/gwlf.py"]
    assert entry["upstream_sha256"] == LEGACY_GWLF_SHA256
    assert hashlib.sha256(source.read_bytes()).hexdigest() == entry["sha256"]
