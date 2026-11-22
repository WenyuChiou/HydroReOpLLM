"""Explicit hourly GWLF forcing and routing for the coupled YAML entry point.

CSV depths are accumulated over each hour. Seasonal temperature is supplied in
every row; this adapter does not infer it or resample any forcing or hydrograph.
"""

from __future__ import annotations

import csv
from datetime import datetime, timedelta, timezone
import gzip
import hashlib
import json
import math
from pathlib import Path

import numpy as np

from hydrocnhs.rainfall_runoff_model.gwlf_hourly import (
    _configuration, _state, run_GWLF_hourly,
)


_DT = 3600
_PARAMETERS = {"CN2", "IS", "Res", "Sep", "Alpha", "Beta", "Ur", "Kc", "Df"}
_INITIAL = {"Area", "S0", "U0", "SnowS", "B0", "BF0", "AnteMoisHourly"}
_COLUMNS = ("timestamp", "subbasin_id", "precipitation_mm", "temperature_c",
            "pet_cm", "seasonal_temperature_c")


def _mapping(value, allowed, label, *, required=()):
    if not isinstance(value, dict) or set(value) - set(allowed):
        raise ValueError(f"{label} must be a mapping with known keys")
    missing = set(required) - set(value)
    if missing:
        raise ValueError(f"{label} requires {', '.join(sorted(missing))}")
    return value


def _timestamp(value, label, *, yaml_datetime=False):
    if yaml_datetime and isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str) and "T" in value:
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError(f"{label} must be a UTC timestamp") from exc
    else:
        raise ValueError(f"{label} must be a UTC timestamp")
    if (parsed.tzinfo is None or parsed.utcoffset() != timedelta(0)
            or parsed.microsecond):
        raise ValueError(f"{label} must be a UTC timestamp at whole-second precision")
    parsed = parsed.astimezone(timezone.utc)
    return parsed, parsed.isoformat(timespec="seconds").replace("+00:00", "Z")


def _hourly_step(value, label):
    if type(value) is not int or value != _DT:
        raise ValueError(f"{label} must be the integer 3600 for hourly forcing")


def _validate_model(model):
    _mapping(model, {"schema_version", "start_time", "dt_seconds", "steps", "catchments"},
             "hourly model", required={"schema_version", "start_time", "dt_seconds", "steps", "catchments"})
    if model["schema_version"] != "hourly-gwlf-model.v1":
        raise ValueError("hourly model schema_version must be hourly-gwlf-model.v1")
    _hourly_step(model["dt_seconds"], "model.dt_seconds")
    if type(model["steps"]) is not int or model["steps"] <= 0:
        raise ValueError("hourly model steps must be a positive integer")
    start, canonical = _timestamp(model["start_time"], "model.start_time", yaml_datetime=True)
    catchments = model["catchments"]
    if not isinstance(catchments, dict) or not catchments:
        raise ValueError("hourly model catchments must be a nonempty mapping")
    for unit, config in catchments.items():
        if not isinstance(unit, str) or not unit.strip():
            raise ValueError("catchment names must be nonempty strings")
        _mapping(config, {"parameters", "initial", "dry_gap_hours", "routing"},
                 f"catchment {unit}", required={"parameters", "initial", "routing"})
        _mapping(config["parameters"], _PARAMETERS, f"{unit}.parameters", required=_PARAMETERS)
        _mapping(config["initial"], _INITIAL, f"{unit}.initial",
                 required=_INITIAL - {"AnteMoisHourly", "B0", "BF0"})
        # Use the same validation as the kernel without advancing any water state.
        p, _, gap, fingerprint = _configuration(
            config["parameters"], config["initial"], _DT, config.get("dry_gap_hours", 24))
        _state(config["initial"], None, _DT, gap, fingerprint, p)
        routing = _mapping(config["routing"], {"dt_seconds", "unit_hydrograph"},
                           f"{unit}.routing", required={"dt_seconds", "unit_hydrograph"})
        _hourly_step(routing["dt_seconds"], f"{unit}.routing.dt_seconds")
        weights = routing["unit_hydrograph"]
        if not isinstance(weights, list) or not weights:
            raise ValueError("hourly unit_hydrograph must be a nonempty list")
        if any(isinstance(w, bool) or not isinstance(w, (int, float))
               or not math.isfinite(w) or w < 0 for w in weights):
            raise ValueError("hourly unit_hydrograph weights must be finite and nonnegative")
        if not math.isclose(math.fsum(weights), 1.0, rel_tol=1e-12, abs_tol=1e-12):
            raise ValueError("hourly unit_hydrograph weights must sum to one; no normalization is applied")
    model["start_time"] = canonical
    try:
        dates = [(start + timedelta(seconds=i * _DT)).isoformat(timespec="seconds").replace("+00:00", "Z")
                 for i in range(model["steps"])]
    except OverflowError as exc:
        raise ValueError("hourly model clock exceeds supported datetime range") from exc
    return dates, list(catchments)


def _values(row):
    try:
        values = [float(row[key]) for key in _COLUMNS[2:]]
    except (TypeError, ValueError) as exc:
        raise ValueError("hourly forcing values must be finite numbers") from exc
    if not all(math.isfinite(x) for x in values) or values[0] < 0 or values[2] < 0:
        raise ValueError("hourly forcing requires finite temperatures and nonnegative precipitation/PET")
    return values


def load_interval_weather(spec, base):
    """Validate the full hourly clock, catchments and forcing without simulation."""
    import yaml
    from .workflow import UniqueLoader

    _mapping(spec, {"engine", "forcing_step", "model", "forcing", "inflow_bindings", "prepared_from"},
             "hourly hydrology", required={"forcing_step", "model", "forcing", "inflow_bindings"})
    if spec.get("engine", "gwlf_hourly") != "gwlf_hourly":
        raise ValueError("hourly hydrology engine must be gwlf_hourly")
    if spec["forcing_step"] != "hourly":
        raise ValueError("hourly hydrology forcing_step must be hourly")
    paths = {}
    for key in ("model", "forcing"):
        if not isinstance(spec[key], str) or not spec[key].strip():
            raise ValueError(f"hourly hydrology requires {key} path")
        paths[key] = (Path(base) / spec[key]).resolve()
    model = yaml.load(paths["model"].read_text(encoding="utf-8-sig"), Loader=UniqueLoader)
    dates, units = _validate_model(model)
    samples = {u: {} for u in units}
    date_set = set(dates)
    opener = gzip.open if paths["forcing"].suffix == ".gz" else open
    with opener(paths["forcing"], "rt", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if (reader.fieldnames is None or len(reader.fieldnames) != len(set(reader.fieldnames))
                or set(reader.fieldnames) != set(_COLUMNS)):
            raise ValueError("hourly forcing requires exactly " + ",".join(_COLUMNS))
        for row in reader:
            if None in row or any(value is None for value in row.values()):
                raise ValueError("hourly forcing row has missing or extra fields")
            unit = row["subbasin_id"]
            _, stamp = _timestamp(row["timestamp"], "forcing timestamp")
            if unit not in samples or stamp not in date_set or stamp in samples[unit]:
                raise ValueError("hourly forcing contains an unknown catchment/timestamp or duplicate sample")
            samples[unit][stamp] = _values(row)
    if any(set(samples[u]) != date_set for u in units):
        raise ValueError("hourly forcing must cover every model timestamp for every catchment")
    gaps = {u: float(model["catchments"][u].get("dry_gap_hours", 24)) for u in units}
    encoded_gaps = json.dumps(gaps, sort_keys=True, allow_nan=False, separators=(",", ":"))
    from hydrocnhs.rainfall_runoff_model.groundwater import initialize_groundwater
    initialization = {u: initialize_groundwater(model["catchments"][u]["parameters"],
                      model["catchments"][u]["initial"], scale="hourly") for u in units}
    return dict(model=model, dates=dates, units=units, zero=[], samples=samples,
                paths=paths, bindings=spec["inflow_bindings"], dt_seconds=_DT,
                model_dt_seconds=model["dt_seconds"], engine="gwlf_hourly",
                dry_gap_sha256=hashlib.sha256(encoded_gaps.encode()).hexdigest(),
                groundwater_initialization=initialization)


def validate_interval_bindings(weather, routing_nodes):
    """Require one explicit lateral boundary and count each catchment at most once."""
    bindings = weather["bindings"]
    if not isinstance(bindings, dict) or set(bindings) != set(routing_nodes):
        raise ValueError("inflow_bindings must cover every operation-network local-flow node")
    units, used = set(weather["units"]), set()
    for binding in bindings.values():
        if not isinstance(binding, dict) or len(binding) != 1:
            raise ValueError("each inflow binding requires one runoff, routed or constant field")
        kind, source = next(iter(binding.items()))
        if kind == "constant":
            if isinstance(source, bool) or not isinstance(source, (int, float)) or source != 0:
                raise ValueError("constant boundary is explicit zero lateral inflow only")
            continue
        if kind not in {"runoff", "routed"} or not isinstance(source, str) or source not in units:
            raise ValueError("unknown inflow binding source or type")
        if source in used:
            raise ValueError("inflow bindings overlap; a catchment would be counted twice")
        used.add(source)
    return sorted(units - used)


def simulate_interval_weather(weather, runtime_root):
    """Run real hourly GWLF and explicit hourly UH; retain water beyond the clock.

    ``runtime_root`` keeps the common weather-driver signature. This driver has
    no runtime files, native daily Model.run calls, network access or PET inference.
    """
    del runtime_root
    _hourly_step(weather["dt_seconds"], "weather.dt_seconds")
    dates, units = _validate_model(weather["model"])
    if dates != weather["dates"] or units != weather["units"]:
        raise ValueError("loaded hourly model clock or catchments changed")
    # Validate every stored series before running the first catchment.
    series = {}
    for unit in units:
        if set(weather["samples"][unit]) != set(dates):
            raise ValueError("loaded hourly samples do not cover the model clock")
        series[unit] = np.asarray([weather["samples"][unit][d] for d in dates], dtype=float)
        values = series[unit]
        if (values.shape != (len(dates), 4) or not np.isfinite(values).all()
                or (values[:, (0, 2)] < 0).any()):
            raise ValueError("loaded hourly forcing is invalid")
    result = {key: {} for key in ("runoff", "routed", "diagnostics", "states", "routing_balance")}
    for unit, values in series.items():
        config = weather["model"]["catchments"][unit]
        diagnostics = []
        runoff, state = run_GWLF_hourly(
            config["parameters"], config["initial"], temp=values[:, 1],
            prec=values[:, 0] / 10.0, pet=values[:, 2], monthly_Tavg=values[:, 3],
            dt_seconds=_DT, dry_gap_hours=config.get("dry_gap_hours", 24),
            diagnostics=diagnostics)
        full = np.convolve(runoff, config["routing"]["unit_hydrograph"], mode="full")
        routed = full[:len(dates)]
        if not np.isfinite(full).all() or (full < 0).any():
            raise ArithmeticError("hourly routing produced invalid discharge")
        input_volume = math.fsum(runoff) * _DT
        output_volume = math.fsum(routed) * _DT
        channel_storage = math.fsum(full[len(dates):]) * _DT
        residual = math.fsum((input_volume, -output_volume, -channel_storage))
        if not all(math.isfinite(x) for x in (input_volume, output_volume, channel_storage, residual)):
            raise ArithmeticError("hourly routing produced a nonfinite water balance")
        result["runoff"][unit] = runoff
        result["routed"][unit] = routed
        result["diagnostics"][unit] = diagnostics
        result["states"][unit] = state
        result["routing_balance"][unit] = dict(
            runoff_input_volume_m3=input_volume, routed_output_volume_m3=output_volume,
            final_channel_storage_m3=channel_storage, initial_channel_storage_m3=0.0,
            residual_m3=residual)
    return result
