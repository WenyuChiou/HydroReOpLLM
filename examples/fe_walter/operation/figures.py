"""Plot daily tables from a new run or the retained reference exports."""
from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd

CASE_DIR = Path(__file__).resolve().parent
RULE_COLOR = "#526B8A"
OBS_COLOR = "#252525"
INFLOW_COLOR = "#0072B2"
# Exact US customary volume conversion used by the five-year reference export.
M3_PER_ACRE_FOOT = 43_560 * 0.3048 ** 3


def make_figures(output_dir=None, *, reservoir=None, flow=None):
    """Return reservoir and two-station figures; optionally export PDF/SVG/PNG.

    All flow values are daily means in cfs. The reservoir release excludes spill.
    Observation gaps remain gaps. Quality exclusions affect scoring, not plotting.
    """
    if reservoir is None:
        reservoir = pd.read_csv(CASE_DIR / "outputs/reservoir_daily.csv", parse_dates=["date"])
    if flow is None:
        flow = pd.read_csv(CASE_DIR / "outputs/streamflow_daily.csv", dtype={"station_id": str}, parse_dates=["date"])
    style = {"font.family": "Arial", "font.size": 9, "axes.labelsize": 9,
             "legend.fontsize": 9, "xtick.labelsize": 9, "ytick.labelsize": 9,
             "svg.fonttype": "none", "pdf.fonttype": 42,
             "axes.spines.top": False, "axes.spines.right": False}
    with plt.rc_context(style):
        fig, axes = plt.subplots(2, 1, figsize=(180 / 25.4, 120 / 25.4), sharex=True,
                                 layout="constrained")
        dates = reservoir.date
        axes[0].plot(dates, reservoir.water_elevation_ft, color=RULE_COLOR, lw=1, label="Rule-based")
        axes[0].plot(dates, reservoir.observed_elevation_ft, color=OBS_COLOR, lw=0.9, label="Observed")
        axes[0].set(ylabel="Water elevation (ft NGVD29)", ylim=(1240, 1520))
        axes[0].legend(loc="upper left", ncol=2, frameon=False)
        axes[1].bar(dates, reservoir.water_release_cfs, width=1, color=RULE_COLOR,
                    linewidth=0, label="Controlled release", rasterized=False)
        axes[1].plot(dates, reservoir.upstream_simulated_inflow_cfs, color=INFLOW_COLOR,
                     lw=0.65, label="Upstream simulated inflow")
        # Spill is a separate path in the mass balance, retained here for interpretation.
        axes[1].plot(dates, reservoir.spill_cfs, color="#9B6A93", lw=0.65, label="Spill")
        axes[1].set(ylabel="Flow (cfs)", ylim=(0, 1.28 * reservoir[["water_release_cfs", "upstream_simulated_inflow_cfs", "spill_cfs"]].max().max()))
        axes[1].legend(loc="upper left", ncol=2, frameon=False)
        downstream, stations = plt.subplots(2, 1, figsize=(180 / 25.4, 120 / 25.4),
                                            sharex=True, sharey=True, layout="constrained")
        for axis, (station, name) in zip(stations, [("01447800", "White Haven"),
                                                  ("01449000", "Lehighton")], strict=True):
            rows = flow.loc[flow.station_id == station]
            axis.plot(rows.date, rows.observed_cfs, color=OBS_COLOR, lw=0.75, label="Observed")
            axis.plot(rows.date, rows.simulated_cfs, color=RULE_COLOR, lw=0.75, label="Rule-based")
            axis.set_ylabel("Streamflow (cfs)")
            axis.set_title(f"{name} (USGS {station})", loc="left", fontsize=9)
            axis.legend(loc="upper left", ncol=2, frameon=False)
        stations[0].set_ylim(0, 1.22 * flow[["observed_cfs", "simulated_cfs"]].max().max())
        for group in (axes, stations):
            for index, axis in enumerate(group):
                axis.text(0.99, 0.94, f"({chr(97 + index)})", transform=axis.transAxes,
                          ha="right", va="top")
                axis.grid(axis="y", color="#DDE3E7", lw=0.4)
                axis.set_axisbelow(True)
                axis.set_xlim(dates.iloc[0], dates.iloc[-1] + pd.Timedelta(days=1))
            group[-1].xaxis.set_major_locator(mdates.YearLocator())
            group[-1].xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
        if output_dir is not None:
            output = Path(output_dir)
            output.mkdir(parents=True, exist_ok=True)
            for figure, name in [(fig, "reservoir_operations"), (downstream, "downstream_streamflow")]:
                for suffix in ("pdf", "svg", "png"):
                    target = output / f"{name}.{suffix}"
                    figure.savefig(target, dpi=600)
                    if suffix == "svg":
                        # Remove exporter line-end padding without changing SVG geometry.
                        target.write_text("\n".join(line.rstrip() for line in
                                                   target.read_text(encoding="utf-8").splitlines()) + "\n",
                                          encoding="utf-8")
        return [fig, downstream]


def run_tables(run_output):
    """Join this run's simulated values to the retained observation columns only.

    Storage uses the case's accepted elevation curve; m³/s converts to cfs.
    The reference simulation columns are never used for a new run's figures.
    """
    from examples.fe_walter.extensions.native_case import load_case_profile
    import numpy as np

    folder = Path(run_output)
    trajectory = pd.read_csv(folder / "reservoir_trajectory.csv", parse_dates=["date"])
    trajectory["date"] = trajectory.date.dt.normalize()
    if set(trajectory.reservoir_id) != {"fe_walter"} or trajectory.date.duplicated().any():
        raise ValueError("Expected one FE Walter transition per date")
    observed = pd.read_csv(CASE_DIR / "outputs/reservoir_daily.csv", parse_dates=["date"],
                           usecols=["date", "observed_elevation_ft"])
    if trajectory.date.tolist() != observed.date.tolist():
        raise ValueError("Run and observation dates differ")
    profile = load_case_profile(CASE_DIR.parents[2])
    elevation = [profile.storage_to_elevation(s / M3_PER_ACRE_FOOT) for s in trajectory.storage_end_m3]
    if any(value is None for value in elevation):
        raise ValueError("Run storage is outside the elevation curve")
    cms_to_cfs = 35.31466672148859
    reservoir = observed.assign(water_elevation_ft=elevation,
        water_release_cfs=trajectory.controlled_release_cms.to_numpy() * cms_to_cfs,
        upstream_simulated_inflow_cfs=trajectory.inflow_cms.to_numpy() * cms_to_cfs,
        spill_cfs=trajectory.spill_cms.to_numpy() * cms_to_cfs)
    simulated = pd.read_csv(folder / "network_flows.csv", parse_dates=["date"],
                            usecols=["date", "node", "routed_flow_cms"])
    simulated = simulated[simulated.node.isin(["USGS01447800", "USGS01449000"])].copy()
    simulated["date"] = simulated.date.dt.normalize()
    simulated["station_id"] = simulated.node.str.removeprefix("USGS")
    simulated["simulated_cfs"] = simulated.routed_flow_cms * cms_to_cfs
    observations = pd.read_csv(CASE_DIR / "outputs/streamflow_daily.csv", parse_dates=["date"],
        dtype={"station_id": str}, usecols=["date", "station_id", "observed_cfs", "primary_eligible"])
    flow = observations.merge(simulated[["date", "station_id", "simulated_cfs"]],
                               on=["date", "station_id"], how="left", validate="one_to_one")
    if len(simulated) != len(observations) or not np.isfinite(flow.simulated_cfs).all():
        raise ValueError("Incomplete downstream results")
    return reservoir, flow


def plot_run(run_output, *, export=False):
    """Draw figures from this run; optionally save its own CSV/PDF/SVG/PNG files."""
    reservoir, flow = run_tables(run_output)
    folder = Path(run_output) / "figures" if export else None
    plots = make_figures(folder, reservoir=reservoir, flow=flow)
    if export:
        reservoir.to_csv(folder / "reservoir_daily.csv", index=False)
        flow.to_csv(folder / "streamflow_daily.csv", index=False)
    return plots


if __name__ == "__main__":
    make_figures(CASE_DIR / "outputs")
