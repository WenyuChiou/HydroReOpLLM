"""Plot the frozen, unsimplified EPSG:5070 GIS extract without downloads."""

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.patheffects as effects
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.lines import Line2D
from matplotlib.path import Path as PlotPath
from matplotlib.patches import Patch, PathPatch, Rectangle


PALETTE = {
    "FEW-D-01": "#E4D4B0",
    "FEW-D-02": "#C5B18A",
    "FEW-X-01": "#BDD3D9",
    "FEW-X-02": "#D1DCE4",
    "FEW-X-03": "#9FB9C9",
    "FEW-R-01": "#C0CFB4",
    "FEW-R-02": "#A2B898",
}

# Manual label placement changes text only; the frozen geometry remains intact.
LABEL_POSITIONS = {
    "FEW-D-01": (1689750, 2201300),
    "FEW-D-02": (1688200, 2207000),
    "FEW-X-01": (1700800, 2197600),
    "FEW-X-02": (1696300, 2189000),
    "FEW-X-03": (1696200, 2200500),
    "FEW-R-01": (1674300, 2200800),
    "FEW-R-02": (1680800, 2198700),
}


def rings(geometry):
    """Return the polygon parts in a Polygon or MultiPolygon geometry."""
    if geometry["type"] == "Polygon":
        return [geometry["coordinates"]]
    if geometry["type"] == "MultiPolygon":
        return geometry["coordinates"]
    raise ValueError("expected polygon geometry")


def polygon(ax, geometry, **style):
    """Add an unsimplified polygon geometry to an axes."""
    for part in rings(geometry):
        vertices, codes = [], []
        for ring in part:
            vertices.extend(ring)
            codes.extend(
                [PlotPath.MOVETO]
                + [PlotPath.LINETO] * (len(ring) - 2)
                + [PlotPath.CLOSEPOLY]
            )
        ax.add_patch(PathPatch(PlotPath(vertices, codes), **style))


def preferred_font():
    """Use Arial when installed and a widely available sans serif otherwise."""
    installed = {item.name for item in font_manager.fontManager.ttflist}
    return "Arial" if "Arial" in installed else "DejaVu Sans"


def add_callout(ax, text, xy, xytext, marker, color, align="left"):
    """Draw one point and its readable, offset label."""
    ax.scatter(
        [xy[0]], [xy[1]], marker=marker, facecolor=color, edgecolor="white",
        linewidth=0.9, s=92, zorder=9,
    )
    ax.annotate(
        text, xy, xytext=xytext, ha=align, va="center", fontsize=14,
        fontweight="bold",
        arrowprops={"arrowstyle": "-", "color": "#3E484E", "lw": 1.2},
        bbox={"boxstyle": "round,pad=0.22", "facecolor": "white",
              "edgecolor": "#C8CDD0", "alpha": 0.96, "linewidth": 0.6},
        zorder=10,
    )


def add_unit_legend(panel):
    """Explain all seven model units and their selection roles."""
    handles = [
        Patch(facecolor=PALETTE["FEW-D-01"], edgecolor="#59666D", label="FEW-D-01 — parameter donor"),
        Patch(facecolor=PALETTE["FEW-D-02"], edgecolor="#59666D", label="FEW-D-02 — parameter donor"),
        Patch(facecolor=PALETTE["FEW-X-01"], edgecolor="#59666D", label="FEW-X-01 — diagnostic only"),
        Patch(facecolor=PALETTE["FEW-X-02"], edgecolor="#59666D", label="FEW-X-02 — diagnostic only"),
        Patch(facecolor=PALETTE["FEW-X-03"], edgecolor="#59666D", label="FEW-X-03 — diagnostic only"),
        Patch(facecolor=PALETTE["FEW-R-01"], edgecolor="#59666D", label="FEW-R-01 — residual unit"),
        Patch(facecolor=PALETTE["FEW-R-02"], edgecolor="#59666D", label="FEW-R-02 — residual unit"),
    ]
    legend = panel.legend(
        handles=handles, loc="upper left", bbox_to_anchor=(0.0, 0.57),
        frameon=False, borderaxespad=0, handlelength=1.2, handleheight=1.0,
        labelspacing=0.42, fontsize=12, title="Model units and roles",
        title_fontsize=14,
    )
    legend.get_title().set_fontweight("bold")
    panel.add_artist(legend)


def add_feature_legend(panel):
    """Explain the mapped hydrographic and point features."""
    handles = [
        Patch(facecolor="#4C91AA", edgecolor="#32647B", label="Reservoir"),
        Line2D([], [], color="#397A98", lw=2, label="River network"),
        Line2D([], [], marker="^", color="none", markerfacecolor="#202A30", markeredgecolor="white", markersize=10, label="USGS gauge"),
        Line2D([], [], marker="s", color="none", markerfacecolor="#9A4F42", markeredgecolor="white", markersize=10, label="Dam / outlet*"),
        Line2D([], [], marker="o", color="none", markerfacecolor="#126B87", markeredgecolor="white", markersize=10, label="River inlet†"),
    ]
    legend = panel.legend(
        handles=handles, loc="lower left", bbox_to_anchor=(0.0, 0.0),
        frameon=False, borderaxespad=0, handlelength=1.7, labelspacing=0.45,
        fontsize=12, title="Mapped features", title_fontsize=14,
    )
    legend.get_title().set_fontweight("bold")


def render(source, output):
    """Render editable SVG/PDF and a 200 dpi PNG from the frozen extract."""
    data = json.loads(source.read_text(encoding="utf-8"))
    assert data["crs"]["authority"] == "EPSG:5070"
    assert len(data["subbasins"]) == 7
    assert [feature["properties"]["subbasin_id"] for feature in data["subbasins"]] == list(PALETTE)

    plt.rcParams.update({
        "svg.fonttype": "none", "pdf.fonttype": 42,
        "font.family": preferred_font(), "text.color": "#202A30",
    })
    fig = plt.figure(figsize=(12, 8), facecolor="white")
    ax = fig.add_axes([0.035, 0.155, 0.69, 0.75])
    panel = fig.add_axes([0.75, 0.145, 0.235, 0.76])
    panel.axis("off")

    for feature in data["subbasins"]:
        unit_id = feature["properties"]["subbasin_id"]
        polygon(ax, feature["geometry"], facecolor=PALETTE[unit_id],
                edgecolor="#59666D", lw=0.9, zorder=1)

    for feature in data["layers"]["river_network"]:
        geometry = feature["geometry"]
        lines = [geometry["coordinates"]] if geometry["type"] == "LineString" else geometry["coordinates"]
        for line in lines:
            ax.plot(*zip(*line), color="#397A98", lw=0.85, alpha=0.88, zorder=2)

    for feature in data["layers"]["reservoirs"]:
        polygon(ax, feature["geometry"], facecolor="#4C91AA",
                edgecolor="#32647B", lw=1.0, zorder=4)

    for feature in data["subbasins"]:
        unit_id = feature["properties"]["subbasin_id"]
        ax.text(
            *LABEL_POSITIONS[unit_id], unit_id, fontsize=14, fontweight="bold",
            ha="center", va="center", zorder=6,
            path_effects=[effects.withStroke(linewidth=3.2, foreground="white")],
        )

    gauge_positions = {"01447500": (1677200, 2196900), "01447720": (1689300, 2187850)}
    for feature in data["layers"]["usgs_gauges"]:
        gauge_id = feature["properties"]["usgs_id"]
        add_callout(ax, f"USGS {gauge_id}", feature["geometry"]["coordinates"],
                    gauge_positions[gauge_id], "^", "#202A30", align="center")

    for feature in data["layers"]["map_points"]:
        point_id = feature["properties"]["point_id"]
        xy = feature["geometry"]["coordinates"]
        if "OUTLET" in point_id:
            add_callout(ax, "Dam / outlet*", xy, (1668500, 2188350), "s", "#9A4F42")
        else:
            add_callout(ax, "River inlet†", xy, (1668500, 2193900), "o", "#126B87")

    xmin, ymin, xmax, ymax = data["viewport_bounds_epsg5070"]
    pad = 1800
    ax.set(xlim=(xmin - pad, xmax + pad), ylim=(ymin - pad, ymax + pad))
    ax.set_aspect("equal")
    ax.axis("off")

    scale_y, scale_x = ymin + 900, xmin + 1200
    ax.plot([scale_x, scale_x + 10000], [scale_y, scale_y], color="#202A30", lw=3, zorder=12)
    ax.plot([scale_x, scale_x], [scale_y - 250, scale_y + 250], color="#202A30", lw=2, zorder=12)
    ax.plot([scale_x + 10000, scale_x + 10000], [scale_y - 250, scale_y + 250], color="#202A30", lw=2, zorder=12)
    ax.text(scale_x + 5000, scale_y + 750, "10 km", ha="center", fontsize=13, fontweight="bold")

    arrow_x = xmax - 1700
    ax.annotate("", xy=(arrow_x, ymax - 1000), xytext=(arrow_x, ymax - 5600),
                arrowprops={"arrowstyle": "-|>", "color": "#202A30", "lw": 1.8})
    ax.text(arrow_x, ymax - 6300, "Grid north", ha="center", va="top",
            fontsize=12, fontweight="bold")

    basin = data["layers"]["delaware_river_basin"][0]["geometry"]
    inset = panel.inset_axes([0.05, 0.68, 0.9, 0.32])
    polygon(inset, basin, facecolor="#ECEFEA", edgecolor="#778174", lw=0.8)
    outer = rings(basin)[0][0]
    xs, ys = zip(*outer)
    inset.set(xlim=(min(xs) - 10000, max(xs) + 10000),
              ylim=(min(ys) - 10000, max(ys) + 10000))
    inset.set_aspect("equal")
    inset.axis("off")
    inset.add_patch(Rectangle((xmin, ymin), xmax - xmin, ymax - ymin,
                              fill=False, edgecolor="#9A4F42", lw=1.5))
    inset.set_title("Delaware River Basin", fontsize=14, fontweight="bold", pad=4)

    add_unit_legend(panel)
    add_feature_legend(panel)

    fig.suptitle("Francis E. Walter Reservoir study units", fontsize=20,
                 fontweight="bold", y=0.965)
    fig.text(
        0.04, 0.055,
        "Frozen NHDPlus HR / NLDI / WBD extract (EPSG:5070).\n"
        "*Dam/outlet: project record, not an external survey.  "
        "†Inlet: river–waterbody boundary crossing derived from source geometry.\n"
        "D units supply parameters; X units are diagnostics excluded from parameter selection; "
        "R units are residuals. The map does not establish a live hydrology trace.",
        fontsize=10.5, linespacing=1.35, va="bottom",
    )

    output.parent.mkdir(parents=True, exist_ok=True)
    for extension in ("svg", "pdf", "png"):
        fig.savefig(output.with_suffix("." + extension), dpi=200, facecolor="white")
    plt.close(fig)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=Path("data/figures/fe_walter_map.json"))
    parser.add_argument("--output", type=Path, default=Path("docs/figures/fe-walter-study-map"))
    args = parser.parse_args()
    render(args.source, args.output)
