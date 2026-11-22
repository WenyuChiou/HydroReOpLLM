"""Offline hourly YAML driver checks, independent volumes and strict clocks."""

import copy
import csv
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sys
from unittest.mock import patch

import numpy as np
import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from hydrocnhs.rainfall_runoff_model.gwlf_hourly import run_GWLF_hourly
from llm_reservoir_agent.interval_weather import (
    load_interval_weather, simulate_interval_weather, validate_interval_bindings,
)


FIELDS = ["timestamp", "subbasin_id", "precipitation_mm", "temperature_c", "pet_cm",
          "seasonal_temperature_c"]


def catchment(**changes):
    config = dict(parameters=dict(CN2=100, IS=0.2, Res=0, Sep=0, Alpha=0,
                                  Beta=0, Ur=10, Kc=1, Df=0.24),
                  initial=dict(Area=13, S0=0, U0=0, SnowS=0, B0=0),
                  routing=dict(dt_seconds=3600, unit_hydrograph=[0.25, 0.5, 0.25]))
    config.update(changes)
    return config


def case(tmp_path, *, steps=3, model_changes=None, configs=None):
    model = dict(schema_version="hourly-gwlf-model.v1", start_time="2024-02-29T23:00:00Z",
                 dt_seconds=3600, steps=steps, catchments=configs or {"a": catchment()})
    model.update(model_changes or {})
    start = datetime(2024, 2, 29, 23, tzinfo=timezone.utc)
    rows = []
    for i in range(steps):
        stamp = (start + timedelta(hours=i)).isoformat().replace("+00:00", "Z")
        for unit in model["catchments"]:
            rows.append(dict(timestamp=stamp, subbasin_id=unit, precipitation_mm=[10, 20, 30][i % 3],
                             temperature_c=5, pet_cm=0, seasonal_temperature_c=5))
    write_model(tmp_path, model)
    write_rows(tmp_path, rows)
    spec = dict(engine="gwlf_hourly", forcing_step="hourly", model="model.yaml", forcing="forcing.csv",
                inflow_bindings={"local": {"routed": "a"}})
    return spec, model, rows


def write_model(root, model):
    (root / "model.yaml").write_text(yaml.safe_dump(model, sort_keys=False), encoding="utf-8")


def write_rows(root, rows, fields=FIELDS):
    with (root / "forcing.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def test_real_hourly_driver_uses_interval_depths_and_retains_channel_water(tmp_path):
    spec, model, _ = case(tmp_path)
    with patch("hydrocnhs.Model.run", side_effect=AssertionError("daily path called")):
        weather = load_interval_weather(spec, tmp_path)
        result = simulate_interval_weather(weather, ROOT)
    # CN=100 gives every rain depth as immediate runoff; 13ha * 1cm = 1300m3.
    np.testing.assert_allclose(result["runoff"]["a"], np.array([1300, 2600, 3900]) / 3600)
    np.testing.assert_allclose(result["routed"]["a"] * 3600, [325, 1300, 2600])
    balance = result["routing_balance"]["a"]
    assert balance == pytest.approx(dict(runoff_input_volume_m3=7800, routed_output_volume_m3=4225,
                                         final_channel_storage_m3=3575, initial_channel_storage_m3=0,
                                         residual_m3=0))
    assert sum(r["precipitation_cm"] for r in result["diagnostics"]["a"]) == 6
    assert max(abs(r["mass_balance_residual_m3"]) for r in result["diagnostics"]["a"]) < 1e-9
    assert result["states"]["a"]["steps_completed"] == 3
    json.dumps(result["states"], allow_nan=False)
    assert weather["dates"] == ["2024-02-29T23:00:00Z", "2024-03-01T00:00:00Z", "2024-03-01T01:00:00Z"]
    assert weather["paths"] == {"model": tmp_path / "model.yaml", "forcing": tmp_path / "forcing.csv"}
    assert weather["zero"] == [] and weather["dt_seconds"] == weather["model_dt_seconds"] == 3600


def test_real_kernel_with_stores_snow_et_and_explicit_seasonal_input(tmp_path):
    config = catchment(parameters=dict(CN2=75, IS=0.2, Res=0.12, Sep=0.08, Alpha=0.3,
                                       Beta=0.25, Ur=10, Kc=0.8, Df=0.24),
                       initial=dict(Area=13, S0=10, U0=6, SnowS=1, B0=2), dry_gap_hours=2)
    spec, _, rows = case(tmp_path, configs={"a": config})
    for i, row in enumerate(rows):
        row.update(temperature_c=[-2, 8, 12][i], pet_cm=0.03, seasonal_temperature_c=15)
    write_rows(tmp_path, rows)
    result = simulate_interval_weather(load_interval_weather(spec, tmp_path), ROOT)
    actual = result["runoff"]["a"]
    expected, expected_state = run_GWLF_hourly(config["parameters"], config["initial"],
        temp=[-2, 8, 12], prec=[1, 2, 3], pet=[0.03] * 3, monthly_Tavg=[15] * 3,
        dt_seconds=3600, dry_gap_hours=2)
    np.testing.assert_array_equal(actual, expected)
    assert result["states"]["a"] == expected_state
    records = result["diagnostics"]["a"]
    final = result["states"]["a"]
    initial_volume = (10 + 6 + 1 + 2) * 1300
    final_volume = sum(final[k] for k in ("S", "U", "snow", "B")) * 1300
    losses = sum(r["actual_et_cm"] + r["deep_loss_cm"] for r in records) * 1300
    assert initial_volume + 6 * 1300 == pytest.approx(final_volume + sum(actual) * 3600 + losses)


def test_offset_zero_canonicalization_rejects_duplicate_instants(tmp_path):
    spec, _, rows = case(tmp_path)
    rows[0]["timestamp"] = rows[0]["timestamp"].replace("Z", "+00:00")
    write_rows(tmp_path, rows)
    assert load_interval_weather(spec, tmp_path)["dates"][0].endswith("Z")
    rows.append(dict(rows[0], timestamp="2024-02-29T23:00:00Z"))
    write_rows(tmp_path, rows)
    with pytest.raises(ValueError, match="duplicate"):
        load_interval_weather(spec, tmp_path)


@pytest.mark.parametrize("kind", ["missing", "unknown_unit", "unknown_time", "naive", "offset", "fraction", "extra_row_field"])
def test_forcing_requires_complete_unique_utc_clock(tmp_path, kind):
    spec, _, rows = case(tmp_path)
    if kind == "missing":
        rows.pop(1)
    elif kind == "unknown_unit":
        rows[1]["subbasin_id"] = "other"
    elif kind == "unknown_time":
        rows[1]["timestamp"] = "2024-03-01T03:00:00Z"
    elif kind == "naive":
        rows[1]["timestamp"] = "2024-03-01T00:00:00"
    elif kind == "offset":
        rows[1]["timestamp"] = "2024-03-01T00:00:00-05:00"
    elif kind == "fraction":
        rows[1]["timestamp"] = "2024-03-01T00:00:00.1Z"
    write_rows(tmp_path, rows)
    if kind == "extra_row_field":
        with (tmp_path / "forcing.csv").open("a", encoding="utf-8") as stream:
            stream.write("2024-03-01T02:00:00Z,a,1,5,0,5,extra\n")
    with pytest.raises(ValueError):
        load_interval_weather(spec, tmp_path)


@pytest.mark.parametrize(("column", "value"), [
    ("precipitation_mm", -1), ("pet_cm", -1), ("precipitation_mm", "nan"),
    ("temperature_c", "inf"), ("pet_cm", ""), ("seasonal_temperature_c", "nan")])
def test_invalid_forcing_never_reaches_kernel(tmp_path, column, value):
    spec, _, rows = case(tmp_path)
    rows[-1][column] = value
    write_rows(tmp_path, rows)
    with patch("llm_reservoir_agent.interval_weather.run_GWLF_hourly", side_effect=AssertionError("simulation called")):
        with pytest.raises(ValueError, match="finite"):
            load_interval_weather(spec, tmp_path)


@pytest.mark.parametrize("change", [
    {"engine": "GWLF"}, {"forcing_step": "daily"}, {"forcing_step": 3600},
    {"dt_seconds": 3600}, {"zero_flow_nodes": []}, {"inflow_bindings": None, "unexpected": 1}])
def test_unknown_or_inconsistent_spec_rejected(tmp_path, change):
    spec, _, _ = case(tmp_path)
    spec.update(change)
    with pytest.raises(ValueError):
        load_interval_weather(spec, tmp_path)


@pytest.mark.parametrize("change", [
    {"schema_version": "daily"}, {"dt_seconds": 86400}, {"dt_seconds": 3600.0},
    {"steps": True}, {"steps": 0}, {"unexpected": 1}, {"start_time": "2024-02-29"},
    {"catchments": {}}])
def test_bad_model_rejected_before_opening_forcing(tmp_path, change):
    spec, model, _ = case(tmp_path)
    model.update(change)
    write_model(tmp_path, model)
    (tmp_path / "forcing.csv").unlink()
    with pytest.raises(ValueError):
        load_interval_weather(spec, tmp_path)


@pytest.mark.parametrize("kind", ["missing_B0", "negative_storage", "bad_CN", "bad_loss", "unknown_parameter",
                                  "unknown_initial", "bad_gap", "bad_history", "unknown_config", "daily_UH",
                                  "wrong_sum", "negative_UH", "nan_UH", "empty_UH", "unknown_routing"])
def test_bad_catchment_rejected_before_forcing_or_kernel(tmp_path, kind):
    spec, model, _ = case(tmp_path)
    config = model["catchments"]["a"]
    if kind == "missing_B0":
        del config["initial"]["B0"]
    elif kind == "negative_storage":
        config["initial"]["U0"] = -1
    elif kind == "bad_CN":
        config["parameters"]["CN2"] = 101
    elif kind == "bad_loss":
        config["parameters"].update(Res=0.5, Sep=0.5)
    elif kind == "unknown_parameter":
        config["parameters"]["Area"] = 10
    elif kind == "unknown_initial":
        config["initial"]["BFt"] = 1
    elif kind == "bad_gap":
        config["dry_gap_hours"] = 0.5
    elif kind == "bad_history":
        config["initial"]["AnteMoisHourly"] = [0] * 119
    elif kind == "unknown_config":
        config["daily_units"] = True
    elif kind == "daily_UH":
        config["routing"]["dt_seconds"] = 86400
    elif kind == "wrong_sum":
        config["routing"]["unit_hydrograph"] = [1, 1]
    elif kind == "negative_UH":
        config["routing"]["unit_hydrograph"] = [-0.1, 1.1]
    elif kind == "nan_UH":
        config["routing"]["unit_hydrograph"] = [float("nan")]
    elif kind == "empty_UH":
        config["routing"]["unit_hydrograph"] = []
    elif kind == "unknown_routing":
        config["routing"]["daily_normalize"] = True
    write_model(tmp_path, model)
    (tmp_path / "forcing.csv").unlink()
    with patch("llm_reservoir_agent.interval_weather.run_GWLF_hourly", side_effect=AssertionError("simulation called")):
        with pytest.raises(ValueError):
            load_interval_weather(spec, tmp_path)


def test_duplicate_yaml_keys_and_forcing_headers_rejected(tmp_path):
    spec, _, _ = case(tmp_path)
    with (tmp_path / "model.yaml").open("a", encoding="utf-8") as stream:
        stream.write("steps: 3\n")
    with pytest.raises(ValueError, match="unique"):
        load_interval_weather(spec, tmp_path)
    case(tmp_path)
    (tmp_path / "forcing.csv").write_text(",".join(FIELDS + ["temperature_c"]) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="requires exactly"):
        load_interval_weather(spec, tmp_path)


def test_bindings_cover_nodes_and_never_duplicate_catchment(tmp_path):
    spec, _, _ = case(tmp_path, configs={"a": catchment(), "b": catchment()})
    weather = load_interval_weather(spec, tmp_path)
    assert validate_interval_bindings(weather, ["local"]) == ["b"]
    weather["bindings"] = {"local": {"runoff": "a"}, "other": {"routed": "a"}}
    with pytest.raises(ValueError, match="counted twice"):
        validate_interval_bindings(weather, ["local", "other"])
    weather["bindings"] = {"local": {"runoff": "a"}, "other": {"routed": "b"}, "zero": {"constant": 0}}
    assert validate_interval_bindings(weather, ["local", "other", "zero"]) == []


@pytest.mark.parametrize("bindings", [
    {}, {"local": {"constant": True}}, {"local": {"constant": 1}}, {"local": {"constant": "0"}},
    {"local": {"routed": "unknown"}}, {"local": {"runoff": []}},
    {"local": {"runoff": "a", "routed": "a"}}])
def test_invalid_binding_rejected(tmp_path, bindings):
    spec, _, _ = case(tmp_path)
    weather = load_interval_weather(spec, tmp_path)
    weather["bindings"] = bindings
    with pytest.raises(ValueError):
        validate_interval_bindings(weather, ["local"])


def test_dry_gap_hash_and_loading_are_deterministic(tmp_path):
    spec, model, _ = case(tmp_path)
    weather = load_interval_weather(spec, tmp_path)
    first = weather["dry_gap_sha256"]
    assert load_interval_weather(spec, tmp_path)["dry_gap_sha256"] == first
    model["catchments"]["a"]["dry_gap_hours"] = 24
    write_model(tmp_path, model)
    assert load_interval_weather(spec, tmp_path)["dry_gap_sha256"] == first
    model["catchments"]["a"]["dry_gap_hours"] = 12
    write_model(tmp_path, model)
    assert load_interval_weather(spec, tmp_path)["dry_gap_sha256"] != first


def test_mutated_clock_or_later_catchment_forcing_rejected_before_any_execution(tmp_path):
    spec, _, _ = case(tmp_path, configs={"a": catchment(), "b": catchment()})
    weather = load_interval_weather(spec, tmp_path)
    modified = copy.deepcopy(weather)
    modified["dates"].pop(1)
    with patch("llm_reservoir_agent.interval_weather.run_GWLF_hourly", side_effect=AssertionError("simulation called")):
        with pytest.raises(ValueError, match="clock"):
            simulate_interval_weather(modified, ROOT)
        weather["samples"]["b"][weather["dates"][-1]][0] = float("nan")
        with pytest.raises(ValueError, match="invalid"):
            simulate_interval_weather(weather, ROOT)
