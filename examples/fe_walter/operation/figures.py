"""Plot saved daily values; no simulation, interpolation or data downloads."""
from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd

CASE_DIR = Path(__file__).resolve().parent
RULE_COLOR = "#526B8A"
OBS_COLOR = "#252525"
INFLOW_COLOR = "#0072B2"


def make_figures(output_dir=None):
    """Return reservoir and two-station figures; optionally export PDF/SVG/PNG.

    All flow values are daily means in cfs. The reservoir release excludes spill.
    Observation gaps remain gaps. Quality exclusions affect scoring, not plotting.
    """
    reservoir = pd.read_csv(CASE_DIR / "outputs/reservoir_daily.csv", parse_dates=["date"])
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


if __name__ == "__main__":
    make_figures(CASE_DIR / "outputs")
