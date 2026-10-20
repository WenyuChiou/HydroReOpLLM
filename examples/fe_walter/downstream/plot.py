"""Draw the shared manual, notebook and paper figures from saved daily values."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch, PathPatch
from matplotlib.path import Path as MplPath
import numpy as np
import pandas as pd

COLORS = {"rule": "#526B8A", "llm_available": "#BF795E", "llm_knowledge": "#4F8A7B"}
STYLES = {"rule": "-", "llm_available": "--", "llm_knowledge": "-."}
plt.rcParams.update({"font.family": "Arial", "font.size": 9, "axes.labelsize": 9,
                     "legend.fontsize": 9, "pdf.fonttype": 42, "svg.fonttype": "none"})


def export(fig, destination):
    """Keep dimensions fixed; vector text stays editable and PNG uses 600 dpi."""
    for suffix in ("pdf", "svg", "png"):
        fig.savefig(destination.with_suffix("." + suffix), dpi=600, facecolor="white")


def plot_streamflow(daily):
    """Each method shares the observed reference, dates, and discharge scale."""
    fig, axes = plt.subplots(3, 1, figsize=(180 / 25.4, 145 / 25.4), sharex=True, sharey=True)
    upper = max(daily.gauge_flow_cms.max(), daily.observed_cms.max()) / 0.028316846592
    for letter, (method, color), ax in zip("abc", COLORS.items(), axes):
        data = daily.loc[daily.method == method].sort_values("date")
        dates = pd.to_datetime(data.date)
        label = data.method_label.iloc[0].replace(" additional operating knowledge", "\nadditional operating knowledge")
        # Repeat the final value only at the right interval boundary so the
        # 31 December daily mean occupies its complete day on the step plot.
        edges = dates.tolist() + [dates.iloc[-1] + pd.Timedelta(days=1)]
        observed = (data.observed_cms / 0.028316846592).tolist()
        simulated = (data.gauge_flow_cms / 0.028316846592).tolist()
        ax.step(edges, observed + observed[-1:], where="post", color="#252525",
                linewidth=1.05, label="USGS 01447800", zorder=3)
        ax.step(edges, simulated + simulated[-1:], where="post", color=color,
                linestyle=STYLES[method], linewidth=1.0, label=label, zorder=4)
        initial = data.loc[~data.evaluation_eligible]
        if not initial.empty:
            ax.axvspan(dates.iloc[0], pd.Timestamp(initial.date.max()) + pd.Timedelta(days=1),
                       color="#dce1e4", alpha=0.5, zorder=0)
        ax.set_ylim(0, upper * 1.4)
        ax.set_ylabel("Discharge (cfs)")
        ax.text(-0.12, 0.97, "(" + letter + ")", transform=ax.transAxes, va="top", fontweight="bold")
        ax.legend(loc="upper left", frameon=False, ncol=2, handlelength=2.3,
                           columnspacing=1.4, borderaxespad=0.4)
        ax.grid(axis="y", color="#dce3e6", linewidth=0.5)
        ax.spines[["top", "right"]].set_visible(False)
        ax.set_xlim(pd.Timestamp("2016-01-01"), pd.Timestamp("2017-01-01"))
    axes[-1].set_xticks(pd.date_range("2016-01-01", "2016-12-01", freq="MS"))
    axes[-1].xaxis.set_major_formatter(mdates.DateFormatter("%b"))
    axes[-1].set_xlabel("2016")
    fig.subplots_adjust(left=0.12, right=0.985, top=0.985, bottom=0.09, hspace=0.13)
    return fig


def fill_polygon(ax, polygon, **style):
    """Retain polygon holes rather than painting over lakes or excluded areas."""
    if polygon.geom_type == "MultiPolygon":
        for piece in polygon.geoms:
            fill_polygon(ax, piece, **style)
        return
    if polygon.is_empty:
        return
    from shapely.geometry.polygon import orient
    polygon = orient(polygon, sign=1)
    vertices, codes = [], []
    for ring in (polygon.exterior, *polygon.interiors):
        xy = list(ring.coords)
        vertices.extend(xy)
        codes.extend([MplPath.MOVETO] + [MplPath.LINETO] * (len(xy) - 2) + [MplPath.CLOSEPOLY])
    ax.add_patch(PathPatch(MplPath(vertices, codes), **style))


def plot_watershed(geometry, root):
    """Show the complete gauge watershed and its nested dam-reach watershed."""
    from pyproj import Transformer
    from shapely.geometry import shape
    from shapely.ops import transform
    project = Transformer.from_crs(4326, 5070, always_xy=True).transform
    objects = {f["properties"]["role"]: transform(project, shape(f["geometry"]))
               for f in geometry["features"]}
    old = json.loads((root / "data/figures/fe_walter_map.json").read_text())
    fig, axes = plt.subplots(1, 2, figsize=(180 / 25.4, 105 / 25.4))
    bounds = objects["gauge_basin"].bounds
    local = objects["lateral_area"].bounds
    for index, ax in enumerate(axes):
        fill_polygon(ax, objects["dam_reach_basin"], facecolor="#dcebf1", edgecolor="none", zorder=1)
        fill_polygon(ax, objects["lateral_area"], facecolor="#e7bd87", edgecolor="none", zorder=2)
        fill_polygon(ax, objects["gauge_basin"], facecolor="none", edgecolor="#314d5a", linewidth=0.8, zorder=5)
        for feature in old["layers"]["river_network"]:
            river = shape(feature["geometry"])
            if river.geom_type == "LineString":
                xy = np.asarray(river.coords)
                ax.plot(xy[:, 0], xy[:, 1], color="#4d8eae", linewidth=0.45, zorder=3)
        for feature in old["layers"]["reservoirs"]:
            fill_polygon(ax, shape(feature["geometry"]), facecolor="#4d8eae", edgecolor="#4d8eae", linewidth=0.4, zorder=4)
        xy = np.asarray(objects["reservoir_to_gauge"].coords)
        ax.plot(xy[:, 0], xy[:, 1], color="#176088", linewidth=1.3, zorder=6)
        for role, marker, color in (("recorded_dam", "D", "#213c4a"), ("USGS01447800", "o", "#b94c40")):
            point = objects[role]
            ax.plot(point.x, point.y, marker=marker, markersize=6, color=color,
                    markeredgecolor="white", markeredgewidth=0.6, zorder=8)
        x0, y0, x1, y1 = bounds if index == 0 else local
        margin = 1300 if index == 0 else 500
        ax.set_xlim(x0 - margin, x1 + margin)
        ax.set_ylim(y0 - margin, y1 + margin)
        ax.set_aspect("equal")
        ax.set_axis_off()
        length = 10000 if index == 0 else 1000
        left, right = ax.get_xlim()
        bottom, top = ax.get_ylim()
        x, y = left + (right - left) * 0.06, bottom + (top - bottom) * 0.035
        ax.plot([x, x + length], [y, y], color="#263e49", linewidth=2)
        ax.text(x + length / 2, y + (top - bottom) * 0.018, str(length // 1000) + " km", ha="center", fontsize=9)
        ax.annotate("N", xy=(0.93, 0.94), xytext=(0.93, 0.79), xycoords="axes fraction",
                    ha="center", va="center", arrowprops={"arrowstyle": "-|>", "color": "#263e49"}, fontsize=9)
    # Full labels are outside the mapped area, leaving small local features clear.
    handles = [Patch(facecolor="#dcebf1", label="Upstream watershed"),
               Patch(facecolor="#e7bd87", label="Downstream contributing area"),
               Line2D([], [], color="#314d5a", linewidth=0.8, label="Gauge watershed boundary"),
               Line2D([], [], marker="D", color="#213c4a", linestyle="none", label="Dam outlet"),
               Line2D([], [], marker="o", color="#b94c40", linestyle="none", label="USGS 01447800")]
    fig.legend(handles=handles, loc="lower center", ncol=2, frameon=False,
               bbox_to_anchor=(0.5, 0.015), columnspacing=1.7)
    fig.subplots_adjust(left=0.025, right=0.99, top=0.90, bottom=0.23, wspace=0.12)
    fig.text(0.025, 0.97, "(a) Gauge watershed", va="top", fontsize=9)
    fig.text(0.54, 0.97, "(b) Below the dam", va="top", fontsize=9)
    return fig


def render(folder, root):
    daily = pd.read_csv(folder / "daily.csv")
    geometry = json.loads((folder / "catchment_partition.geojson").read_text())
    for fig, stem in ((plot_streamflow(daily), "streamflow"),
                      (plot_watershed(geometry, root), "watershed")):
        export(fig, folder / stem)
        plt.close(fig)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder", type=Path)
    args = parser.parse_args()
    render(args.folder, Path(__file__).resolve().parents[3])
