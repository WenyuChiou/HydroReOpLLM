"""Experimental GWLF-derived hourly runoff with explicit water storage.

The pinned daily :mod:`gwlf` and daily HydroCNHS ``Model.run`` are unchanged.
This separate kernel uses event-cumulative SCS-CN excess, a physical five-day
antecedent window and daily-reference rate parameters. It is not an empirically
validated hourly GWLF model. See ``docs/HOURLY_GWLF.md`` before scientific use.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
from collections.abc import Mapping

import numpy as np


MODEL_VERSION = "gwlf-hourly-event-cn.v1"
STATE_VERSION = "gwlf-hourly-state.v1"
_PARAMETERS = ("CN2", "IS", "Res", "Sep", "Alpha", "Beta", "Ur", "Kc", "Df")
_DAY = 86400
_WINDOW = 5 * _DAY
_INTERVALS = (900, 1800, 3600)


def _number(value, name, *, minimum=None, maximum=None):
    if isinstance(value, (bool, np.bool_)) or not isinstance(
        value, (int, float, np.integer, np.floating)
    ):
        raise ValueError(f"{name} must be a finite number")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{name} must be finite")
    if minimum is not None and result < minimum:
        raise ValueError(f"{name} must be >= {minimum}")
    if maximum is not None and result > maximum:
        raise ValueError(f"{name} must be <= {maximum}")
    return result


def _vector(values, name, *, nonnegative=False):
    try:
        raw = list(values)
    except TypeError as exc:
        raise ValueError(f"{name} must be a one-dimensional sequence") from exc
    return [
        _number(v, f"{name}[{i}]", minimum=0 if nonnegative else None)
        for i, v in enumerate(raw)
    ]


def _configuration(pars, inputs, dt_seconds, dry_gap_hours):
    if type(dt_seconds) is not int or dt_seconds not in _INTERVALS:
        raise ValueError("dt_seconds must be 3600, 1800 or 900")
    if not isinstance(pars, Mapping) or not isinstance(inputs, Mapping):
        raise ValueError("pars and inputs must be mappings")
    missing = set(_PARAMETERS) - set(pars)
    if missing:
        raise ValueError(f"missing GWLF parameters: {sorted(missing)}")
    p = {key: _number(pars[key], key, minimum=0) for key in _PARAMETERS}
    if not 0 < p["CN2"] <= 100:
        raise ValueError("CN2 must be > 0 and <= 100")
    if p["IS"] > 1 or p["Beta"] > 1:
        raise ValueError("IS and Beta must be <= 1")
    if p["Res"] + p["Sep"] >= 1:
        raise ValueError("Res + Sep must be < 1 for daily-reference fractions")
    if p["Ur"] <= 0:
        raise ValueError("Ur must be positive")
    if "Area" not in inputs:
        raise ValueError("inputs must contain Area in hectares")
    area = _number(inputs["Area"], "Area", minimum=0)
    if area <= 0:
        raise ValueError("Area must be positive")
    gap = _number(dry_gap_hours, "dry_gap_hours", minimum=0) * 3600
    if gap < dt_seconds or not gap.is_integer() or int(gap) % dt_seconds:
        raise ValueError("dry gap must be a positive whole number of intervals")
    config = dict(parameters=p, area_ha=area, dt_seconds=dt_seconds,
                  dry_gap_seconds=int(gap), model_version=MODEL_VERSION)
    encoded = json.dumps(config, sort_keys=True, allow_nan=False, separators=(",", ":"))
    return p, area, int(gap), hashlib.sha256(encoded.encode()).hexdigest()


def _empty_event():
    return dict(cn=None, input_cm=0.0, runoff_cm=0.0, dry_seconds=0)


def _curve_number(cn2, antecedent, seasonal_temperature):
    cn1 = 4.2 * cn2 / (10 - 0.058 * cn2)
    cn3 = 23 * cn2 / (10 + 0.13 * cn2)
    am1, am2 = (3.6, 5.3) if seasonal_temperature > 10 else (1.3, 2.8)
    if antecedent < am1:
        cn = cn1 + (cn2 - cn1) * antecedent / am1
    elif antecedent <= am2:
        cn = cn2 + (cn3 - cn2) * (antecedent - am1) / (am2 - am1)
    else:
        cn = cn3
    # The analytical transformations give CN<=100; roundoff at CN2=100 must
    # not emit a state outside the same domain enforced on JSON restart.
    return min(100.0, cn)


def _excess(depth, cn, abstraction_fraction):
    retention = max(0.0, 2540 / cn - 25.4)
    abstraction = abstraction_fraction * retention
    if depth <= abstraction:
        return 0.0
    return (depth - abstraction) ** 2 / (depth + (1 - abstraction_fraction) * retention)


def _state(inputs, previous, dt, gap, fingerprint, p):
    count = _WINDOW // dt
    if previous is None:
        for key in ("S0", "U0", "SnowS", "B0"):
            if key not in inputs:
                raise ValueError(f"initial hourly inputs require explicit {key}")
        history = inputs.get("AnteMoisHourly")
        supplied = history is not None
        history = _vector(history, "AnteMoisHourly", nonnegative=True) if supplied else [0.0] * count
        if len(history) != count:
            raise ValueError("AnteMoisHourly must cover exactly 120 physical hours")
        return dict(
            schema_version=STATE_VERSION, model_version=MODEL_VERSION,
            dt_seconds=dt, configuration_sha256=fingerprint, steps_completed=0,
            U=_number(inputs["U0"], "U0", minimum=0),
            S=_number(inputs["S0"], "S0", minimum=0),
            B=_number(inputs["B0"], "B0", minimum=0),
            snow=_number(inputs["SnowS"], "SnowS", minimum=0),
            liquid_history_cm=history,
            history_initialization="provided" if supplied else "zero-filled",
            event=_empty_event(),
        )
    if not isinstance(previous, Mapping):
        raise ValueError("restart vars must be an hourly state mapping")
    state = copy.deepcopy(dict(previous))
    required = {"schema_version", "model_version", "dt_seconds", "configuration_sha256",
                "steps_completed", "U", "S", "B", "snow", "liquid_history_cm",
                "history_initialization", "event"}
    if set(state) != required:
        raise ValueError("restart state fields do not match hourly state schema")
    if (state["schema_version"] != STATE_VERSION or state["model_version"] != MODEL_VERSION
            or type(state["dt_seconds"]) is not int or state["dt_seconds"] != dt
            or state["configuration_sha256"] != fingerprint):
        raise ValueError("restart state configuration, timestep or schema changed")
    if type(state["steps_completed"]) is not int or state["steps_completed"] < 0:
        raise ValueError("restart steps_completed must be a nonnegative integer")
    for key in ("U", "S", "B", "snow"):
        state[key] = _number(state[key], f"state.{key}", minimum=0)
    history = _vector(state["liquid_history_cm"], "state.liquid_history_cm", nonnegative=True)
    if len(history) != count:
        raise ValueError("restart history must cover exactly 120 physical hours")
    state["liquid_history_cm"] = history
    if state["history_initialization"] not in ("provided", "zero-filled"):
        raise ValueError("unknown history initialization")
    event = state["event"]
    if not isinstance(event, Mapping) or set(event) != set(_empty_event()):
        raise ValueError("restart event fields do not match schema")
    event = dict(event)
    for key in ("input_cm", "runoff_cm"):
        event[key] = _number(event[key], f"event.{key}", minimum=0)
    dry = event["dry_seconds"]
    if type(dry) is not int or not 0 <= dry < gap or dry % dt:
        raise ValueError("restart dry duration is inconsistent")
    if event["cn"] is None:
        if event != _empty_event():
            raise ValueError("inactive restart event has nonzero memory")
    else:
        event["cn"] = _number(event["cn"], "event.cn", minimum=0, maximum=100)
        if event["cn"] <= 0 or event["input_cm"] <= 0:
            raise ValueError("active restart event requires positive CN and input")
        expected = _excess(event["input_cm"], event["cn"], p["IS"])
        if not math.isclose(event["runoff_cm"], expected, rel_tol=1e-12, abs_tol=1e-12):
            raise ValueError("restart cumulative event runoff is inconsistent")
    state["event"] = event
    return state


def run_GWLF_hourly(pars, inputs, temp, prec, pet, monthly_Tavg, vars=None, *,
                    dt_seconds=3600, dry_gap_hours=24, diagnostics=None):
    """Run experimental hourly GWLF, returning interval mean cms and restart state.

    ``prec``/``pet`` are cm per interval, not daily totals or rates. Parameters
    retain daily reference units. ``inputs['B0']`` explicitly supplies deep
    storage in cm. Optional diagnostics receive one water-balance record per
    interval only after complete input validation. The caller owns the clock
    and must supply aligned, continuous forcing and seasonal temperatures.
    """
    p, area, gap, fingerprint = _configuration(pars, inputs, dt_seconds, dry_gap_hours)
    temperature = _vector(temp, "temp")
    precipitation = _vector(prec, "prec", nonnegative=True)
    potential_et = _vector(pet, "pet", nonnegative=True)
    seasonal = _vector(monthly_Tavg, "monthly_Tavg")
    lengths = {len(x) for x in (temperature, precipitation, potential_et, seasonal)}
    if len(lengths) != 1:
        raise ValueError("all forcing arrays must have equal length")
    if diagnostics is not None and not isinstance(diagnostics, list):
        raise ValueError("diagnostics must be a list or None")
    state = _state(inputs, vars, dt_seconds, gap, fingerprint, p)
    h = dt_seconds / _DAY
    fraction = p["Res"] + p["Sep"]
    shallow_fraction = -math.expm1(math.log1p(-fraction) * h) if fraction else 0.0
    deep_fraction = -math.expm1(-p["Alpha"] * h)
    depth_to_volume = area * 100  # cm * ha -> m3
    out = np.empty(len(temperature), dtype=float)
    history = state["liquid_history_cm"]
    records = []
    for i, (t, rain_snow, pet_depth, monthly_t) in enumerate(
            zip(temperature, precipitation, potential_et, seasonal, strict=True)):
        u, shallow, deep, snow = (state[k] for k in ("U", "S", "B", "snow"))
        initial_storage = math.fsum((u, shallow, deep, snow))
        rain = rain_snow if t > 0 else 0.0
        snow += rain_snow - rain
        melt = min(snow, p["Df"] * max(t, 0.0) * h)
        snow -= melt
        liquid = rain + melt
        event = state["event"]
        adjustment = 0.0
        if liquid > 0:
            if event["cn"] is None:
                event = _empty_event()
                event["cn"] = _curve_number(p["CN2"], math.fsum(history), monthly_t)
            event["dry_seconds"] = 0
            event["input_cm"] += liquid
            cumulative = _excess(event["input_cm"], event["cn"], p["IS"])
            raw_quick = cumulative - event["runoff_cm"]
            tolerance = 1e-11 * max(1.0, event["input_cm"])
            if raw_quick < -tolerance or raw_quick > liquid + tolerance:
                raise ArithmeticError("cumulative CN increment violates available liquid")
            quick = min(liquid, max(0.0, raw_quick))
            adjustment = quick - raw_quick
            event["runoff_cm"] = cumulative
        else:
            quick = 0.0
            if event["cn"] is not None:
                event["dry_seconds"] += dt_seconds
                if event["dry_seconds"] >= gap:
                    event = _empty_event()
        state["event"] = event
        history.pop(0)
        history.append(liquid)
        ks = 1.0 if u >= p["Ur"] * 0.5 else u / (p["Ur"] * 0.5)
        available = u + liquid - quick
        actual_et = min(available, ks * p["Kc"] * pet_depth)
        percolation = max(available - actual_et - p["Ur"], 0.0)
        u = available - actual_et - percolation
        removed = shallow * shallow_fraction
        shallow_flow = removed * (p["Res"] / fraction) if fraction else 0.0
        seepage = removed - shallow_flow
        shallow = shallow - removed + percolation
        deep_loss = p["Beta"] * seepage
        recharged = deep + seepage - deep_loss
        baseflow = recharged * deep_fraction
        deep = recharged - baseflow
        streamflow = math.fsum((quick, shallow_flow, baseflow))
        final_storage = math.fsum((u, shallow, deep, snow))
        residual = math.fsum((initial_storage, rain_snow, -final_storage,
                              -streamflow, -actual_et, -deep_loss)) * depth_to_volume
        if not all(math.isfinite(v) and v >= 0 for v in (u, shallow, deep, snow, streamflow)):
            raise ArithmeticError("hourly GWLF produced nonfinite or negative water state")
        if not math.isfinite(residual):
            raise ArithmeticError("hourly GWLF produced a nonfinite mass residual")
        out[i] = streamflow * depth_to_volume / dt_seconds
        if not math.isfinite(out[i]):
            raise ArithmeticError("hourly GWLF produced nonfinite discharge")
        records.append(dict(
            step=state["steps_completed"], dt_seconds=dt_seconds,
            precipitation_cm=rain_snow, rain_cm=rain, melt_cm=melt,
            quickflow_cm=quick, shallow_flow_cm=shallow_flow, seepage_cm=seepage,
            baseflow_cm=baseflow, actual_et_cm=actual_et, deep_loss_cm=deep_loss,
            percolation_cm=percolation, storage_start_cm=initial_storage,
            storage_end_cm=final_storage, mass_balance_residual_m3=residual,
            cn=event["cn"], event_input_cm=event["input_cm"],
            event_runoff_cm=event["runoff_cm"], runoff_roundoff_adjustment_cm=adjustment,
        ))
        state.update(U=u, S=shallow, B=deep, snow=snow,
                     steps_completed=state["steps_completed"] + 1)
    if diagnostics is not None:
        diagnostics.extend(records)
    return out, state
