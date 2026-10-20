from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
import sys
import types

import pytest

from llm_reservoir_agent.reach_validation import evaluate_periods, simulate_observed_boundary


ROOT = Path(__file__).resolve().parents[1]


def _mock_weather():
    return {
        "dates": ["2024-02-28", "2024-02-29", "2024-03-01"],
        "units": ["local"],
        "zero": ["boundary", "target"],
        "samples": {
            "local": {
                "2024-02-28": [10.0, 2.0, 0.1],
                "2024-02-29": [20.0, 3.0, 0.2],
                "2024-03-01": [30.0, 4.0, 0.3],
            }
        },
        "model": {"Routing": {"boundary": {}, "target": {"boundary": {}}}},
    }


def _install_fake_native(monkeypatch, tmp_path, *, corrupt=False, bad_output=False):
    package = tmp_path / "fake_hydrocnhs"
    package.mkdir()
    native_file = package / "hydrocnhs.py"
    native_file.write_bytes(b"accepted\r\n")
    digest = hashlib.sha256(b"accepted\n").hexdigest()
    environment = tmp_path / "environment"
    environment.mkdir()
    (environment / "hydrocnhs-core.json").write_text(json.dumps({
        "files": [{"path": "hydrocnhs.py", "normalized_sha256": "0" * 64 if corrupt else digest}]
    }))
    calls = []

    class Model:
        def __init__(self, config, **kwargs):
            calls.append(("init", deepcopy(config), kwargs))
            self.dc = types.SimpleNamespace(
                Q_runoff={"local": [0.25, 0.5, 0.75]},
                UH_Lohmann={("boundary", "target"): [0.0, 1.0]},
            )

        def run(self, **kwargs):
            calls.append(("run", kwargs))
            values = kwargs["assigned_Q"]["boundary"]
            return {
                "boundary": values,
                "target": [1.0, math.nan, 3.0] if bad_output else [0.0, values[0], values[1]],
            }

    module = types.SimpleNamespace(
        __file__=str(native_file), Model=Model, create_rn_gen=lambda seed: ("seed", seed)
    )
    monkeypatch.setitem(sys.modules, "hydrocnhs", module)
    return calls


def test_observation_replaces_only_selected_dummy_and_preserves_native_model(monkeypatch, tmp_path):
    weather = _mock_weather()
    original = deepcopy(weather["model"])
    calls = _install_fake_native(monkeypatch, tmp_path)

    result = simulate_observed_boundary(weather, "boundary", [4, 5.5, 6], tmp_path)

    run = calls[1][1]
    assert run["assigned_Q"]["boundary"].tolist() == [4.0, 5.5, 6.0]
    assert run["assigned_Q"]["target"].tolist() == [0.0, 0.0, 0.0]
    assert run["prec"]["local"].tolist() == [1.0, 2.0, 3.0]
    assert run["pet"]["local"].tolist() == [0.1, 0.2, 0.3]
    assert "assigned_UH" not in run
    assert calls[0][1]["Path"] == {"WD": str(tmp_path), "Modules": ""}
    assert "boundary" not in calls[0][1]["Routing"]
    assert "boundary" in calls[0][1]["Routing"]["target"]
    assert weather["model"] == original
    assert result["dates"] == weather["dates"]
    assert result["routed"]["boundary"].tolist() == [4.0, 5.5, 6.0]
    assert result["routed"]["target"] == [0.0, 4.0, 5.5]
    assert result["runoff"] == {"local": [0.25, 0.5, 0.75]}
    assert result["unit_hydrographs"][("boundary", "target")].tolist() == [0.0, 1.0]


def test_corrupt_pin_stops_before_native_model(monkeypatch, tmp_path):
    calls = _install_fake_native(monkeypatch, tmp_path, corrupt=True)
    with pytest.raises(ValueError, match="accepted pin"):
        simulate_observed_boundary(_mock_weather(), "boundary", [1, 2, 3], tmp_path)
    assert calls == []


@pytest.mark.parametrize(
    ("boundary", "flows", "message"),
    [
        ("missing", [1, 2, 3], "zero_flow_node"),
        ("target", [1, 2], "same length"),
        ("boundary", [1, math.nan, 3], "finite"),
        ("boundary", [1, -2, 3], "nonnegative"),
        ("boundary", [1, "2", 3], "number"),
        ("boundary", [1, True, 3], "number"),
    ],
)
def test_boundary_inputs_are_strict(monkeypatch, tmp_path, boundary, flows, message):
    _install_fake_native(monkeypatch, tmp_path)
    with pytest.raises((TypeError, ValueError), match=message):
        simulate_observed_boundary(_mock_weather(), boundary, flows, tmp_path)


def test_boundary_must_be_a_routing_outlet(monkeypatch, tmp_path):
    weather = _mock_weather()
    weather["zero"].append("orphan")
    _install_fake_native(monkeypatch, tmp_path)
    with pytest.raises(ValueError, match="Routing outlet"):
        simulate_observed_boundary(weather, "orphan", [1, 2, 3], tmp_path)


def test_invalid_native_output_is_not_hidden(monkeypatch, tmp_path):
    _install_fake_native(monkeypatch, tmp_path, bad_output=True)
    with pytest.raises(ArithmeticError, match="invalid daily flow"):
        simulate_observed_boundary(_mock_weather(), "boundary", [1, 2, 3], tmp_path)


def test_evaluate_periods_handles_leap_day_exact_metrics_and_eligible_masks():
    result = evaluate_periods(
        ["2024-02-28", "2024-02-29", "2024-03-01", "2024-03-02"],
        [1.0, 20.0, 5.0, 8.0],
        [2.0, 4.0, None, 8.0],
        {"calibration": ["2024-02-28", "2024-02-29"],
         "validation": ["2024-03-01", "2024-03-02"]},
        eligible=[True, False, True, True],
    )

    assert result["calibration"]["start"] == "2024-02-28"
    assert result["calibration"]["end"] == "2024-02-29"
    assert result["calibration"]["paired_days"] == 1
    assert result["calibration"]["excluded_days"] == 1
    assert result["calibration"]["mae_cms"] == pytest.approx(1.0)
    assert result["calibration"]["rmse_cms"] == pytest.approx(1.0)
    assert result["calibration"]["bias_cms"] == pytest.approx(-1.0)
    assert result["calibration"]["relative_volume_bias"] == pytest.approx(-0.5)
    assert result["calibration"]["nse"] is None
    assert result["calibration"]["kge"] is None
    assert result["validation"]["paired_days"] == 1
    assert result["validation"]["missing_days"] == 1
    assert result["validation"]["mae_cms"] == pytest.approx(0.0)


@pytest.mark.parametrize(
    ("dates", "periods", "message"),
    [
        (["2024-02-28", "2024-03-01"], {"a": ["2024-02-28", "2024-03-01"]}, "consecutive"),
        (["2024-02-28", "2024-02-29", "2024-03-01"],
         {"a": ["2024-02-28", "2024-02-29"], "b": ["2024-02-29", "2024-03-01"]},
         "nonoverlapping"),
        (["2024-02-28", "2024-02-29"], {"a": ["2024-02-27", "2024-02-28"]}, "bounded"),
    ],
)
def test_evaluate_periods_rejects_calendar_and_interval_errors(dates, periods, message):
    with pytest.raises(ValueError, match=message):
        evaluate_periods(dates, [1.0] * len(dates), [1.0] * len(dates), periods)


def test_real_native_observed_boundary_keeps_channel_routing():
    yaml = pytest.importorskip("yaml")
    native = yaml.safe_load((ROOT / "data/accepted/fe_walter_hydrology.yaml").read_text())
    source = native["WaterSystem"]["Outlets"][0]
    aggregate = native["WaterSystem"]["Outlets"][-1]
    direct = deepcopy(native["Routing"][aggregate][aggregate])
    channel = deepcopy(native["Routing"][aggregate][source])
    channel["Inputs"]["FlowLength"] = max(channel["Inputs"]["FlowLength"], 50_000.0)
    dummy = deepcopy(native["RainfallRunoff"][aggregate])
    native["WaterSystem"].update(
        StartDate="2024/01/01", EndDate="2024/01/05", DataLength=5,
        NumSubbasins=3, Outlets=["local", "boundary", "target"],
        RainfallRunoff="ABCD", Routing="Lohmann", ABM=None,
    )
    for name in ("local", "boundary", "target"):
        native["RainfallRunoff"][name] = deepcopy(dummy)
        native["RainfallRunoff"][name]["Inputs"] = {
            "Area": 100.0, "Latitude": 41.0, "XL": 10.0, "SnowS": 0.0
        }
        native["RainfallRunoff"][name]["Pars"] = {
            "a": 0.95, "b": 100.0, "c": 0.5, "d": 0.5, "Df": 0.2
        }
    native["RainfallRunoff"] = {name: native["RainfallRunoff"][name]
                                for name in ("local", "boundary", "target")}
    native["Routing"] = {
        "boundary": {"boundary": direct},
        "target": {"boundary": channel, "target": deepcopy(direct)},
    }
    dates = [f"2024-01-0{day}" for day in range(1, 6)]
    weather = {
        "dates": dates,
        "units": ["local"],
        "zero": ["boundary", "target"],
        "samples": {"local": {day: [0.0, 10.0, 0.0] for day in dates}},
        "model": native,
    }

    result = simulate_observed_boundary(weather, "boundary", [10, 0, 0, 0, 0], ROOT)

    assert result["routed"]["boundary"] == pytest.approx([10, 0, 0, 0, 0])
    assert result["routed"]["target"][0] < 10.0
    assert sum(result["routed"]["target"][1:]) > 0.0
