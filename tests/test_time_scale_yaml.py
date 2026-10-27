"""Public daily/hourly YAML integration with offline monthly-output evidence."""

from collections import Counter, defaultdict
import csv
from datetime import date, datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import sys
from unittest.mock import patch

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from llm_reservoir_agent.coupled import load_coupled_settings, prepare_coupled, run_coupled
from llm_reservoir_agent.verification import verify_run
from llm_reservoir_agent.workflow import load_settings, verify_settings_output


def _json(path, value):
    path.write_text(json.dumps(value, allow_nan=False), encoding="utf-8")


def _yaml(path, value):
    path.write_text(yaml.safe_dump(value, sort_keys=False), encoding="utf-8")


def _rows(path):
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def _csv(path, rows):
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _hourly_bundle(root):
    source = json.loads((ROOT / "examples/fixed_interval/case.json").read_bytes())
    network = source["network"]
    network["start_time"] = "2020-02-28T00:00:00Z"
    _json(root / "physical.json", dict(schema_version="reservoir-physical-case.v1",
                                      data_kind="synthetic_fixture", network=network))
    parameters = dict(CN2=100, IS=0.2, Res=0, Sep=0, Alpha=0, Beta=0, Ur=10, Kc=1, Df=0.24)
    model = dict(schema_version="hourly-gwlf-model.v1", start_time="2020-02-27T00:00:00Z",
                 dt_seconds=3600, steps=120, catchments={"a": dict(parameters=parameters,
                 initial=dict(Area=13, S0=0, U0=0, SnowS=0, B0=0), dry_gap_hours=24,
                 routing=dict(dt_seconds=3600, unit_hydrograph=[0.25, 0.5, 0.25]))})
    _yaml(root / "hydrology.yaml", model)
    first = datetime(2020, 2, 27, tzinfo=timezone.utc)
    rows = [dict(timestamp=(first + timedelta(hours=i)).isoformat().replace("+00:00", "Z"),
                 subbasin_id="a", precipitation_mm=(i % 3) + 1, temperature_c=5,
                 pet_cm=0, seasonal_temperature_c=5) for i in range(120)]
    _csv(root / "weather.csv", rows)
    (root / "prompt.txt").write_text("Choose release. $observation $previous_transition", encoding="utf-8")
    data = dict(schema_version="hydroops-coupled-simulation.v1", run_id="hourly-monthly",
                case="physical.json", output="output", max_calls=0,
                start_time="2020-02-28T00:00:00Z", end_time="2020-03-03T00:00:00Z",
                time=dict(simulation_step="hourly", output_step="monthly"),
                hydrology=dict(engine="gwlf_hourly", forcing_step="hourly", model="hydrology.yaml",
                               forcing="weather.csv", inflow_bindings={"I": {"routed": "a"},
                                                                       "Outlet": {"constant": 0}}),
                agents={"fixture": dict(reservoir="R", mode="offline", release_cms=0.2,
                                        prompt={"user": "prompt.txt"}, history_steps=7)})
    _yaml(root / "simulation.yaml", data)
    return data


def _daily_bundle(root, *, explicit=True):
    data = _hourly_bundle(root)
    physical = json.loads((root / "physical.json").read_bytes())
    network = physical["network"]
    network.update(schema_version="llm-reservoir-network.v1", start_date="2020-02-28", outlet="Outlet")
    for key in ("start_time", "dt_seconds", "outlets"):
        network.pop(key)
    network["reservoirs"]["R"]["physical"]["dt_seconds"] = 86400
    _json(root / "physical.json", physical)
    native = yaml.safe_load((ROOT / "data/accepted/fe_walter_hydrology.yaml").read_text(encoding="utf-8"))
    unit, aggregate = native["WaterSystem"]["Outlets"][0], native["WaterSystem"]["Outlets"][-1]
    native["WaterSystem"].update(StartDate="2020/02/27", EndDate="2020/03/02", DataLength=5,
                               NumSubbasins=2, Outlets=["a", "sum"])
    native["RainfallRunoff"] = {"a": native["RainfallRunoff"][unit], "sum": native["RainfallRunoff"][aggregate]}
    native["Routing"] = {"sum": {"a": native["Routing"][aggregate][unit],
                                  "sum": native["Routing"][aggregate][aggregate]}}
    _yaml(root / "hydrology.yaml", native)
    _csv(root / "weather.csv", [dict(date=(date(2020, 2, 27) + timedelta(days=i)).isoformat(),
        subbasin_id="a", precipitation_mm=10 + i, temperature_c=10, pet_cm=0.1) for i in range(5)])
    for key in ("start_time", "end_time"):
        data.pop(key)
    data.update(run_id="daily-monthly", start_date="2020-02-28", end_date="2020-03-02")
    data["hydrology"].update(engine="gwlf_daily", forcing_step="daily", zero_flow_nodes=["sum"],
                             inflow_bindings={"I": {"routed": "sum"}, "Outlet": {"constant": 0}})
    if explicit:
        data["time"] = dict(simulation_step="daily", output_step="monthly")
    else:
        data.pop("time")
        data["hydrology"].pop("engine")
        data["hydrology"].pop("forcing_step")
    _yaml(root / "simulation.yaml", data)
    return data


@pytest.mark.parametrize("entry", ["daily", "hourly", "inflows"])
def test_present_null_time_rejected_during_check(tmp_path, entry):
    if entry == "inflows":
        data = yaml.safe_load((ROOT / "examples/fixed_interval/experiment.yaml").read_text(encoding="utf-8"))
        data["case"] = str(ROOT / "examples/fixed_interval/case.json")
        data["agents"]["fixture"]["prompt"]["user"] = str(ROOT / "examples/fixed_interval/prompt.txt")
        data["output"] = str(tmp_path / "output")
        loader = load_settings
    else:
        data = _daily_bundle(tmp_path) if entry == "daily" else _hourly_bundle(tmp_path)
        loader = load_coupled_settings
    data["time"] = None
    path = tmp_path / "null-time.yaml"
    _yaml(path, data)
    with patch("llm_reservoir_agent.coupled.load_weather", side_effect=AssertionError("weather read")), \
         patch("llm_reservoir_agent.interval_weather.load_interval_weather", side_effect=AssertionError("hourly weather read")):
        with pytest.raises(ValueError, match="time requires exactly"):
            loader(path)
    assert not (tmp_path / "output").exists()


@pytest.fixture(autouse=True)
def no_http():
    calls = []
    def reject(*args, **kwargs):
        calls.append((args, kwargs))
        raise AssertionError("offline YAML test attempted HTTP")
    with patch("llm_reservoir_agent.configured_backend.http_json_transport", reject):
        yield calls
    assert calls == []


def _assert_monthly_integrals(output, *, dt, expected_count):
    raw = _rows(output / "network_flows.csv")
    monthly = _rows(output / "network_flows_monthly.csv")
    counts = Counter(r["node"] for r in raw)
    assert counts and set(counts.values()) == {expected_count}
    volumes = defaultdict(float)
    key = "timestamp" if dt == 3600 else "date"
    for row in raw:
        volumes[(row["node"], row[key][:7])] += float(row["routed_flow_cms"]) * dt
    assert len(monthly) == len(counts) * 2
    for row in monthly:
        assert float(row["routed_flow_volume_m3"]) == pytest.approx(volumes[(row["node"], row["period_start"][:7])])
        assert float(row["covered_seconds"]) == 2 * 86400
        assert row["complete_period"] == "False"
        expected_end = "2020-03-01T00:00:00Z" if row["period_start"].startswith("2020-02") else "2020-04-01T00:00:00Z"
        assert row["period_end"] == expected_end
    assert any(row[key].startswith("2020-02-29") for row in raw)
    trajectory = _rows(output / "reservoir_trajectory.csv")
    monthly_storage = _rows(output / "reservoir_trajectory_monthly.csv")
    assert len(trajectory) == expected_count and len(monthly_storage) == 2
    assert float(monthly_storage[0]["storage_start_m3"]) == float(trajectory[0]["storage_start_m3"])
    assert float(monthly_storage[-1]["storage_end_m3"]) == float(trajectory[-1]["storage_end_m3"])
    assert "mean_storage_m3" not in monthly_storage[0]


def test_hourly_public_yaml_check_prepare_run_verify_and_monthly_integrals(tmp_path, no_http):
    _hourly_bundle(tmp_path)
    with patch("llm_reservoir_agent.interval_weather.run_GWLF_hourly", side_effect=AssertionError("check simulated")):
        settings = load_coupled_settings(tmp_path / "simulation.yaml")
    assert settings.report["steps"] == 96 and settings.report["hydrology_steps"] == 120
    assert settings.report["planned_llm_calls"] == 0
    assert not (tmp_path / "output").exists()
    manifest = prepare_coupled(settings)
    expected = {"inflows.csv", "case.json", "experiment.yaml", "hydrology.json", "hydrology_diagnostics.json",
                "hydrology_state.json", "hydrology_routing.json"}
    assert set(manifest["generated_files"]) == expected
    for name, digest in manifest["generated_files"].items():
        assert hashlib.sha256((tmp_path / "output" / name).read_bytes()).hexdigest() == digest
    assert Counter(r["node"] for r in _rows(tmp_path / "output/inflows.csv")) == {"I": 96, "Outlet": 96}
    metadata = json.loads((tmp_path / "output/hydrology.json").read_bytes())
    assert metadata["hydrology_steps"] == 120 and metadata["operation_steps"] == 96
    with patch("llm_reservoir_agent.interval_weather.simulate_interval_weather", side_effect=AssertionError("hydrology rerun")):
        _, summary = run_coupled(settings)
    output = tmp_path / "output/operation"
    verified = verify_run(output, require_offline=True)
    assert summary["status"] == "COMPLETED" and verified["steps"] == 96
    assert verified["observed_network_calls"] == 0 and no_http == []
    assert verify_settings_output(load_settings(tmp_path / "output/experiment.yaml"))["status"] == "PASS"
    _assert_monthly_integrals(output, dt=3600, expected_count=96)


@pytest.mark.parametrize("explicit", [True, False])
def test_daily_public_yaml_preserves_inclusive_dates_and_legacy_default(tmp_path, explicit):
    _daily_bundle(tmp_path, explicit=explicit)
    settings = load_coupled_settings(tmp_path / "simulation.yaml")
    assert settings.report["days"] == 4 and settings.report["hydrology_days"] == 5
    run_coupled(settings)
    output = tmp_path / "output/operation"
    assert verify_run(output, require_offline=True)["days"] == 4
    assert verify_settings_output(load_settings(tmp_path / "output/experiment.yaml"))["status"] == "PASS"
    if explicit:
        _assert_monthly_integrals(output, dt=86400, expected_count=4)
    else:
        assert not list(output.glob("*_monthly.csv"))
        assert len(_rows(output / "reservoir_trajectory.csv")) == 4


@pytest.mark.parametrize("kind", ["monthly_simulation", "unknown_time", "missing_output", "model_step",
                                  "forcing_step", "routing_step", "reservoir_step", "forcing_gap",
                                  "mixed_bounds", "noncanonical_bound", "misaligned_bound", "after_model_end"])
def test_invalid_hourly_configuration_fails_before_output_or_execution(tmp_path, kind):
    data = _hourly_bundle(tmp_path)
    if kind == "monthly_simulation":
        data["time"]["simulation_step"] = "monthly"
    elif kind == "unknown_time":
        data["time"]["timezone"] = "UTC"
    elif kind == "missing_output":
        del data["time"]["output_step"]
    elif kind in {"model_step", "routing_step"}:
        model = yaml.safe_load((tmp_path / "hydrology.yaml").read_text(encoding="utf-8"))
        if kind == "model_step":
            model["dt_seconds"] = 86400
        else:
            model["catchments"]["a"]["routing"]["dt_seconds"] = 86400
        _yaml(tmp_path / "hydrology.yaml", model)
    elif kind == "forcing_step":
        data["hydrology"]["forcing_step"] = "daily"
    elif kind == "reservoir_step":
        physical = json.loads((tmp_path / "physical.json").read_bytes())
        physical["network"]["reservoirs"]["R"]["physical"]["dt_seconds"] = 86400
        _json(tmp_path / "physical.json", physical)
    elif kind == "forcing_gap":
        rows = _rows(tmp_path / "weather.csv"); rows.pop(25)
        _csv(tmp_path / "weather.csv", rows)
    elif kind == "mixed_bounds":
        data["start_date"] = "2020-02-28"
    elif kind == "noncanonical_bound":
        data["start_time"] = "2020-02-28T00:00:00+00:00"
    elif kind == "misaligned_bound":
        data["start_time"] = "2020-02-28T00:30:00Z"
    elif kind == "after_model_end":
        data["end_time"] = "2020-03-03T01:00:00Z"
    _yaml(tmp_path / "simulation.yaml", data)
    with patch("llm_reservoir_agent.interval_weather.run_GWLF_hourly", side_effect=AssertionError("simulation called")):
        with pytest.raises(ValueError):
            load_coupled_settings(tmp_path / "simulation.yaml")
    assert not (tmp_path / "output").exists()


def test_daily_cannot_request_finer_hourly_output(tmp_path):
    data = _daily_bundle(tmp_path)
    data["time"]["output_step"] = "hourly"
    _yaml(tmp_path / "simulation.yaml", data)
    with patch("hydrocnhs.Model", side_effect=AssertionError("daily model constructed")):
        with pytest.raises(ValueError, match="finer"):
            load_coupled_settings(tmp_path / "simulation.yaml")
    assert not (tmp_path / "output").exists()


def test_duplicate_time_yaml_key_rejected(tmp_path):
    _hourly_bundle(tmp_path)
    path = tmp_path / "simulation.yaml"
    with path.open("a", encoding="utf-8") as stream:
        stream.write("time:\n  simulation_step: hourly\n  output_step: monthly\n")
    with pytest.raises(ValueError, match="unique"):
        load_coupled_settings(path)
    assert not (tmp_path / "output").exists()


def test_hourly_prepared_from_reuses_pinned_inflow_diagnostics_and_states(tmp_path):
    data = _hourly_bundle(tmp_path)
    prepare_coupled(load_coupled_settings(tmp_path / "simulation.yaml"))
    data.update(output="reused", run_id="reused-hourly")
    data["hydrology"]["prepared_from"] = "output"
    _yaml(tmp_path / "simulation.yaml", data)
    with patch("llm_reservoir_agent.interval_weather.simulate_interval_weather", side_effect=AssertionError("hydrology rerun")):
        run_coupled(load_coupled_settings(tmp_path / "simulation.yaml"))
    for name in ("inflows.csv", "hydrology_diagnostics.json", "hydrology_state.json", "hydrology_routing.json"):
        assert (tmp_path / "reused" / name).read_bytes() == (tmp_path / "output" / name).read_bytes()
    assert verify_run(tmp_path / "reused/operation", require_offline=True)["steps"] == 96


@pytest.mark.parametrize("reuse", [False, True])
def test_hourly_state_tamper_rejected_before_operation(tmp_path, reuse):
    data = _hourly_bundle(tmp_path)
    prepare_coupled(load_coupled_settings(tmp_path / "simulation.yaml"))
    path = tmp_path / "output/hydrology_state.json"
    states = json.loads(path.read_bytes()); states["a"]["B"] += 1
    _json(path, states)
    if reuse:
        data.update(output="reused", run_id="reused-hourly")
        data["hydrology"]["prepared_from"] = "output"
        _yaml(tmp_path / "simulation.yaml", data)
    with patch("llm_reservoir_agent.interval_weather.simulate_interval_weather", side_effect=AssertionError("hydrology rerun")):
        with pytest.raises(ValueError, match="checksum"):
            run_coupled(load_coupled_settings(tmp_path / "simulation.yaml"))
    assert not (tmp_path / "output/operation").exists()
    assert not (tmp_path / "reused/operation").exists()


def test_monthly_numeric_tamper_rejected_even_with_refreshed_hash(tmp_path):
    _hourly_bundle(tmp_path)
    run_coupled(load_coupled_settings(tmp_path / "simulation.yaml"))
    output = tmp_path / "output/operation"
    name = "network_flows_monthly.csv"
    monthly = _rows(output / name)
    monthly[0]["routed_flow_volume_m3"] = str(float(monthly[0]["routed_flow_volume_m3"]) + 1)
    _csv(output / name, monthly)
    summary = json.loads((output / "summary.json").read_bytes())
    summary["summary"]["additional_output_files"][name] = hashlib.sha256((output / name).read_bytes()).hexdigest()
    _json(output / "summary.json", summary)
    _json(output / "index.json", summary)
    with pytest.raises(ValueError, match="temporal output differs"):
        verify_run(output, require_offline=True)
    with pytest.raises(ValueError, match="temporal output differs"):
        verify_settings_output(load_settings(tmp_path / "output/experiment.yaml"))
