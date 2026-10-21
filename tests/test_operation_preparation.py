"""Exercise the committed preparation and figure values without model execution."""
from unittest.mock import patch

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from examples.fe_walter.operation import figures, preflight


def test_preparation_has_shared_inputs_and_no_execution():
    with patch("socket.socket.connect", side_effect=AssertionError("network forbidden")), \
         patch("llm_reservoir_agent.workflow.run_settings", side_effect=AssertionError("simulation forbidden")):
        report = preflight.check_preparation()
    assert report["engineering_ready"] is True
    assert report["live_ready"] is False
    assert report["days"] == 1826
    assert [row["planned_llm_calls"] for row in report["methods"]] == [0, 1826, 1826]
    assert report["saved_results"] == {
        "rule": "complete", "llm_available": "not executed", "llm_knowledge": "not executed"}


def test_figures_keep_every_saved_daily_value():
    reservoir = pd.read_csv(figures.CASE_DIR / "outputs/reservoir_daily.csv")
    flow = pd.read_csv(figures.CASE_DIR / "outputs/streamflow_daily.csv", dtype={"station_id": str})
    plots = figures.make_figures()
    try:
        elevation, release = plots[0].axes
        np.testing.assert_array_equal(elevation.lines[0].get_ydata(), reservoir.water_elevation_ft)
        np.testing.assert_array_equal(elevation.lines[1].get_ydata(), reservoir.observed_elevation_ft)
        np.testing.assert_array_equal([bar.get_height() for bar in release.patches], reservoir.water_release_cfs)
        assert len(release.patches) == 1826
        assert {bar.get_width() for bar in release.patches} == {1.0}
        np.testing.assert_array_equal(release.lines[0].get_ydata(), reservoir.upstream_simulated_inflow_cfs)
        np.testing.assert_array_equal(release.lines[1].get_ydata(), reservoir.spill_cfs)
        for axis, station in zip(plots[1].axes, ["01447800", "01449000"], strict=True):
            rows = flow[flow.station_id == station]
            np.testing.assert_array_equal(axis.lines[0].get_ydata(), rows.observed_cfs)
            np.testing.assert_array_equal(axis.lines[1].get_ydata(), rows.simulated_cfs)
        assert plots[1].axes[0].get_ylim() == plots[1].axes[1].get_ylim()
    finally:
        for figure in plots:
            plt.close(figure)
