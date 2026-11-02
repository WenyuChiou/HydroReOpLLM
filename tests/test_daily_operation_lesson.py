"""Verify the self-contained Rule teaching lesson and its plotted values."""
from unittest.mock import patch
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest
from examples.fe_walter.operation import execution, figures


def test_lesson_refuses_llm_before_creating_output(tmp_path):
    output = tmp_path / "forbidden"
    with patch("socket.socket.connect", side_effect=AssertionError("network forbidden")):
        with pytest.raises(ValueError, match="Rule-based agents only"):
            execution.create_simulation(execution.CASE_DIR / "llm_available.yaml", output=output)
    assert not output.exists()


def test_fresh_simulation_uses_accepted_sources_and_refuses_overwrite(tmp_path):
    output = tmp_path / "run"
    with patch("socket.socket.connect", side_effect=AssertionError("network forbidden")):
        settings = execution.create_simulation(output=output)
        assert settings.report["planned_llm_calls"] == 0
        assert settings.report["days"] == 1826
        assert settings.report["hydrology_days"] == 13514
        assert settings.weather["paths"]["model"] == execution.CASE_DIR / "hydrology/model.yaml"
        assert "prepared_from" not in settings.data["hydrology"]
        with pytest.raises(FileExistsError):
            execution.create_simulation(output=output)


def test_new_plots_use_new_simulation_columns_only(tmp_path):
    reference = pd.read_csv(figures.CASE_DIR / "outputs/reservoir_daily.csv")
    count = len(reference)
    # Deliberately different synthetic output makes reuse of reference curves visible.
    pd.DataFrame({"date": reference.date, "reservoir_id": ["fe_walter"] * count,
        "storage_end_m3": [4287715.370246947] * count,
        "controlled_release_cms": [2.] * count, "inflow_cms": [3.] * count,
        "spill_cms": [0.] * count}).to_csv(tmp_path / "reservoir_trajectory.csv", index=False)
    pd.concat([pd.DataFrame({"date": reference.date, "node": node,
                            "routed_flow_cms": value})
               for node, value in [("USGS01447800", 4.), ("USGS01449000", 5.)]]) \
        .to_csv(tmp_path / "network_flows.csv", index=False)
    reservoir, flow = figures.run_tables(tmp_path)
    plots = figures.plot_run(tmp_path)
    try:
        np.testing.assert_allclose(reservoir.water_release_cfs, 2 * 35.31466672148859)
        np.testing.assert_allclose(plots[0].axes[0].lines[0].get_ydata(), reservoir.water_elevation_ft)
        assert reservoir.water_elevation_ft.nunique() == 1
        assert not np.array_equal(reservoir.water_elevation_ft, reference.water_elevation_ft)
        for axis, station in zip(plots[1].axes, ["01447800", "01449000"], strict=True):
            np.testing.assert_array_equal(axis.lines[1].get_ydata(), flow[flow.station_id == station].simulated_cfs)
    finally:
        for figure in plots:
            plt.close(figure)
    trajectory = pd.read_csv(tmp_path / "reservoir_trajectory.csv").iloc[:-1]
    trajectory.to_csv(tmp_path / "reservoir_trajectory.csv", index=False)
    with pytest.raises(ValueError, match="dates differ"):
        figures.run_tables(tmp_path)
