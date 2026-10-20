"""Offline case checks; no network calls or accepted hydrological runs."""
from copy import deepcopy
from datetime import date, timedelta
import importlib.util
import json
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]


def module(name):
    path = ROOT / "examples/fe_walter/downstream" / (name + ".py")
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


acquire = module("prepare_observations")
case = module("validate")


def response(days=7):
    series = []
    for station, base in zip(acquire.STATIONS, (100, 200)):
        series.append({"sourceInfo": {"siteCode": [{"agencyCode": "USGS", "value": station}]},
                       "variable": {"variableCode": [{"value": "00060"}], "options": {"option": [{"name": "Statistic", "optionCode": "00003"}]},
                                    "unit": {"unitCode": "ft3/s"}, "noDataValue": -999999},
                       "values": [{"value": [{"dateTime": (date(1989, 1, 1) + timedelta(days=i)).isoformat() + "T00:00:00.000",
                                               "value": str(base + i), "qualifiers": ["A"]} for i in range(days)]}]})
    return {"value": {"timeSeries": series}}


def settings(tmp_path):
    result = yaml.safe_load((ROOT / "examples/fe_walter/downstream/validation.yaml").read_text())
    result["periods"] = {"warmup": ["1989-01-01", "1989-01-01"], "calibration": ["1989-01-02", "1989-01-04"],
                         "validation": ["1989-01-05", "1989-01-07"], "evaluation": ["1989-01-08", "1989-01-09"]}
    path = tmp_path / "validation.yaml"
    path.write_text(yaml.safe_dump(result, sort_keys=False))
    return path, result


def prepared(tmp_path, payload=None):
    raw = tmp_path / "response.json"
    raw.write_text(json.dumps(payload or response()))
    folder = tmp_path / "observations"
    acquire.prepare_observations(folder, date(1989, 1, 1), date(1989, 1, 7), raw)
    return folder


def test_usgs_keeps_calendar_day_flags_and_missing():
    raw = response()
    raw["value"]["timeSeries"][0]["values"][0]["value"][0].update(dateTime="1989-01-01T00:00:00-05:00", qualifiers=["e", "A"])
    raw["value"]["timeSeries"][1]["values"][0]["value"][1]["value"] = "-999999"
    rows = acquire.parse_daily_discharge(raw, date(1989, 1, 1), date(1989, 1, 7))
    assert rows[0] == {"date": "1989-01-01", "station_id": "01447800", "flow_cfs": 100, "qualifiers": "A,e"}
    inventory = acquire.observation_inventory(rows, date(1989, 1, 1), date(1989, 1, 7))
    assert inventory[1]["missing_or_invalid_dates"] == ["1989-01-02"]


@pytest.mark.parametrize("field,value", [("unit", {"unitCode": "m3/s"}), ("variableCode", [{"value": "00065"}]),
                                          ("options", {"option": [{"name": "Statistic", "optionCode": "00001"}]})])
def test_usgs_rejects_wrong_parameter_statistic_or_units(field, value):
    raw = response()
    raw["value"]["timeSeries"][0]["variable"][field] = value
    with pytest.raises(ValueError):
        acquire.parse_daily_discharge(raw, date(1989, 1, 1), date(1989, 1, 7))


def test_usgs_rejects_duplicates_and_nonmidnight():
    raw = response()
    entries = raw["value"]["timeSeries"][0]["values"][0]["value"]
    entries.append(deepcopy(entries[0]))
    with pytest.raises(ValueError, match="Duplicate"):
        acquire.parse_daily_discharge(raw, date(1989, 1, 1), date(1989, 1, 7))
    entries.pop()
    entries[0]["dateTime"] = "1989-01-01T12:00:00"
    with pytest.raises(ValueError, match="midnight"):
        acquire.parse_daily_discharge(raw, date(1989, 1, 1), date(1989, 1, 7))


def test_normalization_never_overwrites_and_retains_failure(tmp_path):
    folder = prepared(tmp_path)
    before = (folder / "source_manifest.json").read_bytes()
    with pytest.raises(FileExistsError):
        acquire.prepare_observations(folder, date(1989, 1, 1), date(1989, 1, 7), tmp_path / "response.json")
    assert (folder / "source_manifest.json").read_bytes() == before
    bad = tmp_path / "invalid.json"
    bad.write_text("{}")
    with pytest.raises(KeyError):
        acquire.prepare_observations(tmp_path / "failure", date(1989, 1, 1), date(1989, 1, 7), bad)
    assert json.loads((tmp_path / "failure/source_manifest.json").read_text())["status"] == "failed"
    assert (tmp_path / "failure/usgs_daily.json").read_bytes() == bad.read_bytes()


def test_preflight_reads_real_source_pins_and_reports_three_missing_inputs(tmp_path):
    folder = prepared(tmp_path)
    path, _ = settings(tmp_path)
    report, context = case.preflight(path, folder / "observations.csv", folder / "source_manifest.json")
    assert {x["input"] for x in report["blockers"]} == {"native_model", "forcing", "partition"}
    assert report["ready_for_native_run"] is False
    assert report["executed"] == {"native_hydrology": False, "calibration": False, "llm_requests": 0}
    assert context["observed"]["01447800"]["cms"][0] == 100 * 0.028316846592
    assert report["observations"]["01449000"]["periods"]["validation"]["eligible_days"] == 3


def test_preflight_rejects_changed_raw_source(tmp_path):
    folder = prepared(tmp_path)
    path, _ = settings(tmp_path)
    (folder / "usgs_daily.json").write_text("{}")
    with pytest.raises(ValueError, match="must agree"):
        case.preflight(path, folder / "observations.csv", folder / "source_manifest.json")


def test_quality_policy_can_exclude_estimates_without_filling_upstream(tmp_path):
    payload = response()
    payload["value"]["timeSeries"][0]["values"][0]["value"][2]["qualifiers"] = ["A", "e"]
    folder = prepared(tmp_path, payload)
    path, config = settings(tmp_path)
    config["observations"]["include_estimated"] = False
    path.write_text(yaml.safe_dump(config))
    report, context = case.preflight(path, folder / "observations.csv", folder / "source_manifest.json")
    assert any(b["input"] == "upstream_boundary" for b in report["blockers"])
    assert context["observed"]["01447800"]["cms"][2] == 102 * case.CFS_TO_CMS
    assert context["observed"]["01447800"]["eligible"][2] is False


def test_periods_keep_evaluation_independent(tmp_path):
    path, config = settings(tmp_path)
    config["periods"]["evaluation"][0] = "1989-01-07"
    path.write_text(yaml.safe_dump(config))
    with pytest.raises(ValueError, match="non-overlapping"):
        case.read_settings(path)
    assert case.period_dates(["2020-02-28", "2020-03-01"]) == ["2020-02-28", "2020-02-29", "2020-03-01"]


def partition_fixture(tmp_path):
    from shapely.geometry import box, mapping
    weather = {"units": ["LOCAL"], "zero": ["WHITE_HAVEN", "LEHIGHTON"],
               "model": {"RainfallRunoff": {"LOCAL": {"Inputs": {"Area": 1}}},
                         "Routing": {"WHITE_HAVEN": {"WHITE_HAVEN": {}}, "LEHIGHTON": {"WHITE_HAVEN": {}, "LOCAL": {}, "LEHIGHTON": {}}}}}
    geometry = {"crs": "EPSG:5070", "upstream_gauge": "01447800", "downstream_gauge": "01449000",
                "upstream_basin": mapping(box(0, 0, 100, 100)), "downstream_basin": mapping(box(0, 0, 200, 100)),
                "outlet_precision": "synthetic fixture", "subbasins": [{"type": "Feature", "properties": {"subbasin_id": "LOCAL"}, "geometry": mapping(box(100, 0, 200, 100))}]}
    path = tmp_path / "partition.json"
    path.write_text(json.dumps(geometry))
    return path, geometry, weather


def test_partition_checks_actual_area_and_flow_paths(tmp_path):
    path, geometry, weather = partition_fixture(tmp_path)
    _, config = settings(tmp_path)
    result = case.check_partition(path, weather, config)
    assert result["closure_error_m2"] == 0
    assert result["area_km2"] == 0.01
    weather["model"]["Routing"]["WHITE_HAVEN"]["LOCAL"] = {}
    with pytest.raises(ValueError, match="exactly once"):
        case.check_partition(path, weather, config)


def test_partition_rejects_dam_boundary_and_wrong_native_area(tmp_path):
    path, geometry, weather = partition_fixture(tmp_path)
    _, config = settings(tmp_path)
    weather["model"]["RainfallRunoff"]["LOCAL"]["Inputs"]["Area"] = 2
    with pytest.raises(ValueError, match="area disagrees"):
        case.check_partition(path, weather, config)
    geometry["upstream_gauge"] = "FE_WALTER_DAM"
    path.write_text(json.dumps(geometry))
    with pytest.raises(ValueError, match="gauge outlets"):
        case.check_partition(path, weather, config)


def recipe():
    return {"seed": 7, "parameters": [{"name": "recession", "mode": "set", "bounds": [0.1, 0.5], "paths": [["RainfallRunoff", "LOCAL", "Pars", "Res"]]}],
            "ga": {"min_or_max": "max", "pop_size": 2, "num_ellite": 1, "prob_cross": 0.5, "prob_mut": 0.1, "stochastic": False,
                   "max_gen": 0, "sampling_method": "LHC", "drop_record": False, "paral_cores": 1, "paral_verbose": 0, "auto_save": False, "print_level": 1, "plot": False}}


def test_parameter_groups_preserve_source_and_local_differences():
    weather = {"model": {"RainfallRunoff": {"LOCAL": {"Pars": {"Res": 0.2}}}}}
    updated = case.apply_parameters(weather, recipe(), [0.4])
    assert weather["model"]["RainfallRunoff"]["LOCAL"]["Pars"]["Res"] == 0.2
    assert updated["model"]["RainfallRunoff"]["LOCAL"]["Pars"]["Res"] == 0.4
    with pytest.raises(ValueError, match="bounds"):
        case.apply_parameters(weather, recipe(), [0.6])


def test_mapped_parameter_scaling_keeps_declared_physical_limits(tmp_path):
    weather = {"model": {"RainfallRunoff": {
        "LOW": {"Pars": {"CN2": 70.0}}, "HIGH": {"Pars": {"CN2": 95.0}},
    }}}
    config = recipe()
    config["parameters"] = [{"name": "m_CN2", "mode": "scale", "bounds": [0.3, 1.2],
                             "clip": [25, 100], "paths": [["RainfallRunoff", u, "Pars", "CN2"] for u in ["LOW", "HIGH"]]}]
    path = tmp_path / "calibration.yaml"
    path.write_text(yaml.safe_dump(config))
    loaded = case.read_calibration(path, weather)
    low = case.apply_parameters(weather, loaded, [0.3])
    high = case.apply_parameters(weather, loaded, [1.2])
    assert [low["model"]["RainfallRunoff"][u]["Pars"]["CN2"] for u in ["LOW", "HIGH"]] == [25, 28.5]
    assert [high["model"]["RainfallRunoff"][u]["Pars"]["CN2"] for u in ["LOW", "HIGH"]] == [84, 100]
    assert weather["model"]["RainfallRunoff"]["LOW"]["Pars"]["CN2"] == 70


@pytest.mark.parametrize("limits", [[100, 25], [25, float("nan")], [True, 100], [25]])
def test_mapped_parameter_limits_are_validated(tmp_path, limits):
    weather = {"model": {"RainfallRunoff": {"LOCAL": {"Pars": {"Res": 0.2}}}}}
    config = recipe()
    config["parameters"][0].update(mode="scale", clip=limits)
    path = tmp_path / "calibration.yaml"
    path.write_text(yaml.safe_dump(config))
    with pytest.raises(ValueError, match="clip"):
        case.read_calibration(path, weather)



def test_independent_routing_preserves_late_water_and_detects_shift():
    context = {"settings": {"upstream": {"model_node": "WHITE_HAVEN", "station_id": "01447800"}, "downstream": {"model_node": "LEHIGHTON"}},
               "weather": {"model": {"Routing": {"WHITE_HAVEN": {"WHITE_HAVEN": {}}, "LEHIGHTON": {"WHITE_HAVEN": {}, "LOCAL": {}, "LEHIGHTON": {}}}}},
               "observed": {"01447800": {"cms": [0, 0, 2]}}}
    native = {"runoff": {"LOCAL": [1, 1, 1]}, "routed": {"LEHIGHTON": [1, 1, 1]},
              "unit_hydrographs": {("WHITE_HAVEN", "LEHIGHTON"): [0, 0.5, 0.5], ("LOCAL", "LEHIGHTON"): [1], ("LEHIGHTON", "LEHIGHTON"): [1]}}
    result = case.verify_routing(context, native)
    assert result["input_m3"] == 5 * 86400
    assert result["tail_m3"] == 2 * 86400
    assert result["tail_days"] == 2
    assert result["max_native_difference_cms"] == 0
    native["routed"]["LEHIGHTON"] = [1, 2, 1]
    with pytest.raises(ArithmeticError, match="convolution"):
        case.verify_routing(context, native)


def test_observed_boundary_rejects_upstream_runoff_paths():
    from llm_reservoir_agent.reach_validation import simulate_observed_boundary
    weather = {"dates": ["1989-01-01"], "zero": ["WHITE_HAVEN"],
               "model": {"Routing": {"WHITE_HAVEN": {"LOCAL": {}}}}}
    with pytest.raises(ValueError, match="without upstream runoff"):
        simulate_observed_boundary(weather, "WHITE_HAVEN", [1], ROOT)


def test_fixed_parameter_exports_separate_metrics_and_flow_units(tmp_path):
    folder = prepared(tmp_path)
    path, config = settings(tmp_path)
    report, context = case.preflight(path, folder / "observations.csv", folder / "source_manifest.json")
    context["weather"] = {"model": {"Routing": {"WHITE_HAVEN": {"WHITE_HAVEN": {}}, "LEHIGHTON": {"WHITE_HAVEN": {}, "LOCAL": {}, "LEHIGHTON": {}}}}}
    native = {"runoff": {"LOCAL": [100 * case.CFS_TO_CMS] * 7}, "routed": {"LEHIGHTON": [(200 + i) * case.CFS_TO_CMS for i in range(7)]},
              "unit_hydrographs": {("WHITE_HAVEN", "LEHIGHTON"): [1], ("LOCAL", "LEHIGHTON"): [1], ("LEHIGHTON", "LEHIGHTON"): [1]},
              "routing_compatibility": {"physical_weights_changed": False, "padding_weights_per_route": 1}}
    case.write_results(tmp_path, context, native, report)
    result = json.loads((tmp_path / "report.json").read_text())
    assert result["metrics"]["calibration"]["kge"] == pytest.approx(1)
    assert result["metrics"]["validation"]["paired_days"] == 3
    assert result["executed"]["llm_requests"] == 0
    import csv
    with (tmp_path / "daily.csv").open() as handle:
        rows = list(csv.DictReader(handle))
    assert float(rows[-1]["downstream_simulated_cfs"]) == pytest.approx(206)
    assert (tmp_path / "routing_kernels.json").is_file()
    kernels = json.loads((tmp_path / "routing_kernels.json").read_text())
    assert kernels["compatibility"] == native["routing_compatibility"]
    assert result["routing_compatibility"] == kernels["compatibility"]


def test_calibration_never_exposes_validation_to_native_search(tmp_path, monkeypatch):
    import hydrocnhs.calibration
    import llm_reservoir_agent.reach_validation as core
    folder = prepared(tmp_path)
    path, config = settings(tmp_path)
    _, context = case.preflight(path, folder / "observations.csv", folder / "source_manifest.json")
    context["weather"] = {"dates": context["days"], "units": ["LOCAL"], "samples": {"LOCAL": {d: [0, 0, 0] for d in context["days"]}},
                          "model": {"WaterSystem": {"EndDate": "1989/01/07", "DataLength": 7}, "RainfallRunoff": {"LOCAL": {"Pars": {"Res": 0.2}}}}}
    recipe_path = tmp_path / "calibration.yaml"
    recipe_path.write_text(yaml.safe_dump(recipe()))
    seen = []
    def simulate(weather, node, upstream, root):
        seen.append((list(weather["dates"]), len(upstream)))
        return {"routed": {"LEHIGHTON": [x * case.CFS_TO_CMS for x in (200, 201, 202, 203)]}}
    class FakeGA:
        def __init__(self, evaluator, rn_gen):
            self.evaluator = evaluator
        def set(self, inputs, config, name):
            assert inputs["par_name"] == ["recession"]
        def run(self):
            assert self.evaluator([0.4], (str(tmp_path), 0, 0, None, None))[0] == pytest.approx(1)
            self.solution = [[0.4]]
    monkeypatch.setattr(core, "simulate_observed_boundary", simulate)
    monkeypatch.setattr(case, "verify_routing", lambda context, native: {})  # Routing is tested separately with independent values.
    monkeypatch.setattr(hydrocnhs.calibration, "GA_DEAP", FakeGA)
    frozen, report = case.calibrate(tmp_path, context, recipe_path)
    assert seen == [(["1989-01-01", "1989-01-02", "1989-01-03", "1989-01-04"], 4)]
    assert frozen["dates"][-1] == "1989-01-07"
    assert report["last_simulated_day_during_search"] == "1989-01-04"
    assert context["weather"]["model"]["RainfallRunoff"]["LOCAL"]["Pars"]["Res"] == 0.2


def test_native_ga_interface_with_synthetic_flow_evaluator(tmp_path, monkeypatch):
    import llm_reservoir_agent.reach_validation as core
    folder = prepared(tmp_path)
    path, config = settings(tmp_path)
    _, context = case.preflight(path, folder / "observations.csv", folder / "source_manifest.json")
    context["weather"] = {"dates": context["days"], "units": ["LOCAL"], "samples": {"LOCAL": {d: [0, 0, 0] for d in context["days"]}},
                          "model": {"WaterSystem": {"EndDate": "1989/01/07", "DataLength": 7}, "RainfallRunoff": {"LOCAL": {"Pars": {"Res": 0.2}}}}}
    recipe_path = tmp_path / "calibration.yaml"
    config = recipe()
    config["ga"].update(max_gen=1, prob_cross=1.0)
    recipe_path.write_text(yaml.safe_dump(config))
    seen = []
    def simulate(weather, node, upstream, runtime):
        seen.append(weather["dates"][-1])
        factor = 4 + weather["model"]["RainfallRunoff"]["LOCAL"]["Pars"]["Res"]
        return {"routed": {"LEHIGHTON": [(200 + i) * case.CFS_TO_CMS * factor for i in range(4)]}}
    monkeypatch.setattr(core, "simulate_observed_boundary", simulate)
    monkeypatch.setattr(case, "verify_routing", lambda context, native: {})  # Exercise the native optimizer interface only.
    frozen, report = case.calibrate(tmp_path, context, recipe_path)
    assert len(seen) >= 3  # Negative raw KGE must still permit a new generation.
    assert set(seen) == {"1989-01-04"}
    assert 0.1 <= report["values"][0] <= 0.5
    assert (tmp_path / "native_calibration").is_dir()
    assert frozen["dates"][-1] == "1989-01-07"
    records = [json.loads(line) for line in (tmp_path / "candidate_evaluations.jsonl").read_text().splitlines()]
    assert all(row["kge"] < 0 and row["selection_fitness"] > 0 for row in records)
    assert report["selection_fitness"] == "1 / (2 - KGE)"


def test_kge_selection_weights_are_positive_and_preserve_order():
    import math
    scores = [-1e308, -10, -0.1, 0, 1]
    weights = [case.kge_selection_fitness(value) for value in scores]
    assert all(math.isfinite(value) and value > 0 for value in weights)
    assert weights == sorted(set(weights))
    for value in [float("nan"), float("inf"), 1.1]:
        with pytest.raises(ValueError):
            case.kge_selection_fitness(value)


def test_notebook_run_reuses_the_observation_paths_checked_in_yaml(tmp_path):
    import importlib
    import subprocess
    import sys
    from datetime import datetime, timezone
    folder = prepared(tmp_path)
    path, config = settings(tmp_path)
    config["observations"].update(file=str(folder / "observations.csv"), source_manifest=str(folder / "source_manifest.json"))
    path.write_text(yaml.safe_dump(config, sort_keys=False))
    notebook = json.loads((ROOT / "tutorials/downstream_validation.ipynb").read_text(encoding="utf-8"))
    namespace = {"ROOT": ROOT, "CASE": ROOT / "examples/fe_walter/downstream", "STUDY": tmp_path,
                 "SETTINGS": path, "OBSERVATIONS": tmp_path / "absent-default-folder", "importlib": importlib,
                 "json": json, "sys": sys, "subprocess": subprocess, "datetime": datetime, "timezone": timezone}
    for index in (8, 11):
        exec(compile("".join(notebook["cells"][index]["source"]), f"notebook-cell-{index}", "exec"), namespace)
    checked = namespace["report"]
    command = namespace["command"]
    def option(flag):
        return Path(command[command.index(flag) + 1]) if flag in command else None
    executed, _ = case.preflight(option("--settings"), option("--observations"), option("--source-manifest"))
    assert checked["inputs"]["observations"] == executed["inputs"]["observations"]
    assert checked["inputs"]["source_manifest"] == executed["inputs"]["source_manifest"]
    assert executed["observations"]["01447800"]["eligible_days"] == 7


def test_actual_gwlf_lateral_runoff_and_observed_boundary_close_routing_volume():
    from llm_reservoir_agent.reach_validation import simulate_observed_boundary
    native = yaml.safe_load((ROOT / "data/accepted/fe_walter_hydrology.yaml").read_text())
    original = native["WaterSystem"]["Outlets"][0]
    aggregate = native["WaterSystem"]["Outlets"][-1]
    local = deepcopy(native["RainfallRunoff"][original])
    local["Inputs"]["Area"] = 100
    dummy = deepcopy(native["RainfallRunoff"][aggregate])
    direct = deepcopy(native["Routing"][aggregate][aggregate])
    channel = deepcopy(native["Routing"][aggregate][original])
    channel["Inputs"]["FlowLength"] = 50000
    native["WaterSystem"].update(StartDate="2024/01/01", EndDate="2024/02/29", DataLength=60,
                                 NumSubbasins=3, Outlets=["LOCAL", "WHITE_HAVEN", "LEHIGHTON"])
    native["RainfallRunoff"] = {"LOCAL": local, "WHITE_HAVEN": deepcopy(dummy), "LEHIGHTON": deepcopy(dummy)}
    local_route = deepcopy(native["Routing"][aggregate][original])
    native["Routing"] = {"WHITE_HAVEN": {"WHITE_HAVEN": deepcopy(direct)},
                         "LEHIGHTON": {"WHITE_HAVEN": channel, "LOCAL": local_route, "LEHIGHTON": deepcopy(direct)}}
    days = [(date(2024, 1, 1) + timedelta(days=i)).isoformat() for i in range(60)]
    weather = {"model": native, "dates": days, "units": ["LOCAL"], "zero": ["WHITE_HAVEN", "LEHIGHTON"],
               "samples": {"LOCAL": {day: [10 if i % 3 == 0 else 0, 10, 0.1] for i, day in enumerate(days)}}}
    upstream = [1] * 59 + [10]
    result = simulate_observed_boundary(weather, "WHITE_HAVEN", upstream, ROOT)
    context = {"weather": weather, "settings": {"upstream": {"model_node": "WHITE_HAVEN", "station_id": "01447800"},
                                                "downstream": {"model_node": "LEHIGHTON"}}, "observed": {"01447800": {"cms": upstream}}}
    ledger = case.verify_routing(context, result)
    assert sum(result["runoff"]["LOCAL"]) > 0
    assert ledger["tail_m3"] > 0
    assert ledger["max_native_difference_cms"] < 1e-10
    assert abs(ledger["volume_residual_m3"]) < 1e-6
