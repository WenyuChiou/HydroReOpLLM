"""Acceptance checks for the saved station comparison; no provider or GWLF run."""
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import yaml

pytest.importorskip("shapely")
pytest.importorskip("pyproj")

from examples.fe_walter.downstream.prepare import (
    CASE, INPUTS, ROOT, channel_kernel, checked_inputs, corrected_settings,
    native_provenance, partition_catchment,
)
from llm_reservoir_agent.coupled import load_coupled_settings
from llm_reservoir_agent.downstream import evaluate_daily_flows

OUTPUT = CASE / "downstream/outputs"


def test_official_source_dates_quality_units_and_pins():
    manifest = checked_inputs(INPUTS)
    data = pd.read_csv(INPUTS / "observations.csv")
    assert data.date.tolist() == pd.date_range("2016-01-01", "2016-12-31").strftime("%Y-%m-%d").tolist()
    assert data.approval_status.eq("Approved").all()
    assert data.discharge_cfs.notna().all()
    np.testing.assert_allclose(data.discharge_cms, data.discharge_cfs * 0.028316846592, rtol=0, atol=1e-13)
    assert manifest["availability_role"] == "evaluation_only"


def test_changed_source_fails_before_calculation(tmp_path):
    import shutil
    for path in INPUTS.iterdir():
        shutil.copyfile(path, tmp_path / path.name)
    with (tmp_path / "observations.csv").open("a") as stream:
        stream.write("changed")
    with pytest.raises(ValueError, match="source bytes changed"):
        checked_inputs(tmp_path)


def test_native_core_is_pinned_before_calculation(tmp_path, monkeypatch):
    from examples.fe_walter.downstream import prepare
    runtime = native_provenance()
    assert len(runtime["core_manifest_sha256"]) == 64
    (tmp_path / "environment").mkdir()
    pin = json.loads((ROOT / "environment/hydrocnhs-core.json").read_text())
    pin["files"][0]["normalized_sha256"] = "0" * 64
    (tmp_path / "environment/hydrocnhs-core.json").write_text(json.dumps(pin))
    monkeypatch.setattr(prepare, "ROOT", tmp_path)
    with pytest.raises(ValueError, match="core differs"):
        native_provenance()


def test_spatial_partition_is_nested_and_preserves_area():
    summary, features = partition_catchment(INPUTS)
    assert 750 < summary["gauge_basin_km2"] < 752
    assert 746 < summary["dam_reach_basin_km2"] < 747
    assert 4 < summary["lateral_area_km2"] < 5
    for part in summary["parts"]:
        assert part["original_area_m2"] == pytest.approx(part["upstream_area_m2"] + part["lateral_area_m2"], abs=0.01)
    assert 1300 < summary["reach_length_m"] < 1500
    assert summary["dam_snap_distance_m"] < 50
    assert summary["gauge_snap_distance_m"] < 100
    assert {f["properties"]["role"] for f in features["features"]} == {
        "gauge_basin", "dam_reach_basin", "lateral_area", "reservoir_to_gauge", "recorded_dam", "USGS01447800"}


def test_native_kernel_roundoff_is_explicit_and_bounded():
    routing = json.loads((OUTPUT / "routing.json").read_text())
    kernel, adjustment = channel_kernel(routing["flow_length_m"], routing["parameters"])
    np.testing.assert_array_equal(kernel, routing["unit_hydrograph"])
    assert min(kernel) >= 0
    assert sum(kernel) == pytest.approx(1, abs=1e-14)
    assert adjustment["negative_roundoff_mass"] < 1e-12
    assert adjustment["discarded_positive_tail_mass"] < 1e-12
    raw = adjustment["native_unit_hydrograph"]
    np.testing.assert_allclose(np.pad(kernel, (0, len(raw) - len(kernel))), raw, rtol=0, atol=1e-12)


def test_saved_boundaries_components_metrics_and_tail_are_reproducible():
    source = pd.read_csv(CASE / "coupled/outputs/current_tutorial/daily.csv")
    data = pd.read_csv(OUTPUT / "daily.csv")
    tail = pd.read_csv(OUTPUT / "routing_tail.csv")
    report = json.loads((OUTPUT / "report.json").read_text())
    kernel = json.loads((OUTPUT / "routing.json").read_text())["unit_hydrograph"]
    obs = pd.read_csv(INPUTS / "observations.csv").set_index("date")
    assert len(data) == 1098
    for method in ("rule", "llm_available", "llm_knowledge"):
        old = source.loc[source.method == method].sort_values("date")
        rows = data.loc[data.method == method].sort_values("date")
        rest = tail.loc[tail.method == method].sort_values("date")
        assert rows.date.tolist() == old.date.tolist()
        np.testing.assert_allclose(rows.boundary_outflow_cms, old.controlled_release_cms + old.spill_cms, rtol=0, atol=1e-12)
        expected = np.convolve(rows.boundary_outflow_cms.to_numpy(), kernel)
        np.testing.assert_allclose(pd.concat([rows.routed_reservoir_cms, rest.routed_reservoir_cms]), expected, rtol=0, atol=1e-12)
        np.testing.assert_allclose(rows.gauge_flow_cms, rows.routed_reservoir_cms + rows.lateral_inflow_cms, rtol=0, atol=1e-12)
        np.testing.assert_allclose(rows.observed_cms, obs.loc[rows.date].discharge_cms, rtol=0, atol=1e-12)
        metrics = evaluate_daily_flows(rows.date.tolist(), rows.gauge_flow_cms.tolist(),
                                      rows.observed_cms.tolist(), eligible=rows.evaluation_eligible.tolist())
        assert metrics["paired_days"] == 346
        assert metrics["excluded_days"] == 20
        for name in ("mae_cms", "rmse_cms", "bias_cms", "relative_volume_bias", "nse", "kge"):
            assert metrics[name] == pytest.approx(report["methods"][method]["metrics"][name], abs=1e-12)
        ledger = report["methods"][method]["ledger"]
        assert ledger["volumes_input_m3"] == pytest.approx(ledger["output_m3"], abs=1e-6)
        assert ledger["max_balance_residual_m3"] < 1e-6
    lateral = data.pivot(index="date", columns="method", values="lateral_inflow_cms")
    np.testing.assert_array_equal(lateral.iloc[:, 0], lateral.iloc[:, 1])
    np.testing.assert_array_equal(lateral.iloc[:, 0], lateral.iloc[:, 2])


def test_corrected_inputs_load_without_provider_or_hydrology(tmp_path, monkeypatch):
    import socket
    monkeypatch.setattr(socket.socket, "connect", lambda *a, **k: pytest.fail("network access forbidden"))
    model = yaml.safe_load((ROOT / "data/accepted/fe_walter_hydrology.yaml").read_text())
    partition = json.loads((OUTPUT / "partition.json").read_text())
    kernel = json.loads((OUTPUT / "routing.json").read_text())["unit_hydrograph"]
    corrected_settings(tmp_path, partition, kernel, model)
    generated = yaml.safe_load((tmp_path / "corrected_inputs/model.yaml").read_text())
    # Native zero-assigned aggregation nodes retain a one-hectare placeholder;
    # only real weather-driven units contribute to geographic area.
    assert sum(v["Inputs"]["Area"] for name, v in generated["RainfallRunoff"].items()
               if not name.startswith("__")) == pytest.approx(
        sum(v["Inputs"]["Area"] for name, v in model["RainfallRunoff"].items()
            if not name.startswith("__")), abs=1e-7)
    for unit in model["RainfallRunoff"]:
        assert generated["RainfallRunoff"][unit]["Pars"] == model["RainfallRunoff"][unit]["Pars"]
    for name in ("experiment.yaml", "llm_available.yaml", "llm_knowledge.yaml"):
        settings = load_coupled_settings(tmp_path / "corrected_inputs" / name, runtime_root=ROOT)
        assert settings.report["days"] == 366
        assert settings.report["live_ready"] is False
    assert model["RainfallRunoff"]["FEW-R-02"]["Inputs"]["Area"] == 6787.548484166814


def test_teaching_exports_match_their_manifest():
    for name, record in json.loads((OUTPUT / "manifest.json").read_text()).items():
        assert hashlib.sha256((OUTPUT / name).read_bytes()).hexdigest() == record["sha256"]
