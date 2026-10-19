"""Build the saved-evidence tutorials and current teaching figures.

Cells read repository files only. Execution blocks socket and urllib access,
never calls a provider, and never runs hydrology or reservoir simulation.
"""
from __future__ import annotations

import argparse
import base64
import contextlib
import hashlib
import io
import json
import os
import platform
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
TUTORIALS = ROOT / "tutorials"
CURRENT = ROOT / "examples/fe_walter/coupled/outputs/current_tutorial"
SEASONAL_CRITERIA = ROOT / "examples/fe_walter/seasonal_pool_criteria.json"
OPERATING_KNOWLEDGE = ROOT / "examples/fe_walter/knowledge/operating_rules.md"
NOTEBOOKS = ("main.ipynb", "advanced.ipynb")
LABELS = {
    "rule": "Rule-based",
    "llm_available": "LLM without additional operating knowledge",
    "llm_knowledge": "LLM with additional operating knowledge",
}
METHOD_COLORS = {"rule": "#526B8A", "llm_available": "#BF795E",
                 "llm_knowledge": "#4F8A7B"}
CMS_TO_CFS = 1 / 0.028316846592  # Exact international foot: (0.3048 m)^3.
FIGURE_FONT_FAMILY = "Arial"


def _legend_label(label):
    """Wrap long method names while preserving their full display wording."""
    return label.replace(" operating knowledge", "\noperating knowledge")


def _add_elevation_legend(axis):
    """Align the two short entries above the two wrapped LLM method names."""
    handles, labels = axis.get_legend_handles_labels()
    by_label = dict(zip(labels, handles, strict=True))
    # Matplotlib fills columns first: these entries form two matching rows.
    order = [LABELS["rule"], LABELS["llm_available"],
             "Seasonal pool reference", LABELS["llm_knowledge"]]
    return axis.legend(
        [by_label[label] for label in order], [_legend_label(label) for label in order],
        loc="upper left", ncol=2, alignment="left", frameon=False, fontsize=9,
        handlelength=2.4, handletextpad=0.65, columnspacing=1.8, labelspacing=0.65)


def _seasonal_reference_points(criteria, year=2016):
    """Show seasonal levels with vertical switches at the two mid-month markers."""
    import pandas as pd

    seasons = {season["id"]: season for season in criteria["seasons"]}
    if criteria.get("unit") != "ft" or set(seasons) != {
            "winter_hold", "spring_fill", "summer", "fall_drawdown"}:
        raise ValueError("unexpected FE Walter seasonal criteria")
    winter = (float(seasons["winter_hold"]["minimum_ft"])
              + float(seasons["winter_hold"]["maximum_ft"])) / 2
    summer = float(seasons["summer"]["maximum_ft"])
    # The agreed display uses vertical switches on May 15 and October 15.
    # Repeated dates make the transitions vertical without interpolating a
    # daily target or changing the saved operation/audit settings.
    return pd.DatetimeIndex([
        pd.Timestamp(year, 1, 1), pd.Timestamp(year, 5, 15),
        pd.Timestamp(year, 5, 15), pd.Timestamp(year, 10, 15),
        pd.Timestamp(year, 10, 15), pd.Timestamp(year, 12, 31),
    ]), [winter, winter, summer, summer, winter, winter]


def _reserve_legend_headroom(axes, lower, maximum, *, flow=False):
    """Keep upper-left legends above all data, using actual rendered text size."""
    from matplotlib.ticker import MaxNLocator

    figure = axes[0].figure
    figure.canvas.draw()
    renderer = figure.canvas.get_renderer()
    reserved = max(ax.get_legend().get_window_extent(renderer).height
                   / ax.get_window_extent(renderer).height for ax in axes) + 0.09
    if reserved >= 0.8:
        raise ValueError("legend needs a taller panel at the required font size")
    upper = lower + (maximum - lower) / (1 - reserved)
    ticks = (MaxNLocator(nbins=3, min_n_ticks=3, steps=[1, 2, 5, 10])
             .tick_values(0, upper)) if flow else None
    for ax in axes:
        ax.set_ylim(lower, upper)
        if flow:
            ax.set_yticks(ticks[ticks <= upper])


def plot_reservoir_operations(daily, seasonal_criteria=None):
    """Return a paper-width figure of saved elevation and controlled release.

    The axes share dates but retain separate units. Each method has its own
    release row, converting saved m³/s to cfs for display, excluding spill.
    A shared inflow trace makes retention and drawdown visible beside release.
    Paper exports and the executed tutorial use this same renderer.
    """
    import matplotlib.dates as mdates
    import matplotlib.pyplot as plt
    import pandas as pd

    style = {"font.family": FIGURE_FONT_FAMILY, "font.size": 10,
             "axes.labelsize": 10, "axes.titlesize": 11,
             "xtick.labelsize": 9, "ytick.labelsize": 9,
             "pdf.fonttype": 42, "svg.fonttype": "none", "axes.grid": False}
    with plt.rc_context(style):
        fig, axes = plt.subplots(
            4, 1, figsize=(180 / 25.4, 160 / 25.4), sharex=True,
            gridspec_kw={"height_ratios": [2.3, 1, 1, 1]})
        elevation, *release_axes = axes
        fig.subplots_adjust(left=0.15, right=0.985, bottom=0.095,
                            top=0.955, hspace=0.43)
        release_max = float(daily[["controlled_release_cms", "inflow_cms"]].max().max()) * CMS_TO_CFS
        for index, (method, label) in enumerate(LABELS.items()):
            rows = daily.loc[daily["method"].eq(method)]
            dates = pd.to_datetime(rows["date"])
            color = METHOD_COLORS[method]
            elevation.plot(dates, rows["pool_elevation_end_ft"], label=label,
                           color=color, linestyle=("-", "--", "-.")[index], linewidth=1.35)
            release = release_axes[index]
            # Every bar has the same width in days. Avoid outlines and pixel
            # snapping, which can obscure gaps in a dense annual raster image.
            release.bar(dates, rows["controlled_release_cms"] * CMS_TO_CFS, width=0.72,
                        color=color, linewidth=0, edgecolor="none",
                        antialiased=False, snap=False, zorder=3)
            release.plot(dates, rows["inflow_cms"] * CMS_TO_CFS, color="#2878B5", linewidth=0.8,
                         drawstyle="steps-mid", label="Upstream simulated inflow", zorder=4)
            release.set(ylim=(0, release_max), ylabel="Water release\n(cfs)")
            release.set_title(f"({chr(98 + index)}) Water release ({label})", loc="left", fontweight="bold")
            release.legend(loc="upper left", frameon=False, fontsize=9,
                           handlelength=2.1, borderaxespad=0.35)
        if seasonal_criteria is None:
            seasonal_criteria = json.loads(SEASONAL_CRITERIA.read_text(encoding="utf-8"))
        seasonal_dates, seasonal_levels = _seasonal_reference_points(seasonal_criteria)
        elevation.plot(seasonal_dates, seasonal_levels, color="#111111", linestyle="--",
                       linewidth=1.0, label="Seasonal pool reference", zorder=5)
        elevation.set(title="(a) Water elevation", ylabel="Water elevation\n(ft)")
        release_axes[-1].set_xlabel("Operation date (2016)")
        for ax in axes:
            ax.title.set_position((0, 1.0))
            ax.title.set_horizontalalignment("left")
            ax.title.set_fontweight("bold")
            ax.spines[["top", "right"]].set_visible(False)
            ax.grid(axis="y", color="#DCE1E1", linewidth=0.45, zorder=0)
            ax.grid(axis="x", color="#E8ECEC", linewidth=0.4, zorder=0)
        release_axes[-1].set_xlim(
            pd.to_datetime(daily["date"]).min() - pd.Timedelta(days=0.5),
            pd.to_datetime(daily["date"]).max() + pd.Timedelta(days=0.5))
        release_axes[-1].xaxis.set_major_locator(
            mdates.MonthLocator(bymonth=(1, 3, 5, 7, 9, 11)))
        release_axes[-1].xaxis.set_major_formatter(mdates.DateFormatter("%b"))
        _add_elevation_legend(elevation)
        minimum = float(daily["pool_elevation_end_ft"].min()) - 5
        maximum = max(float(daily["pool_elevation_end_ft"].max()), max(seasonal_levels))
        _reserve_legend_headroom([elevation], minimum, maximum)
        _reserve_legend_headroom(release_axes, 0, release_max, flow=True)
        return fig

SETUP = '''from pathlib import Path
import html, json, re, sys
ROOT = next(p for p in [Path.cwd(), *Path.cwd().parents] if (p / "src/hydrocnhs").is_dir())
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))
import pandas as pd
import matplotlib.pyplot as plt
from tutorials.build_notebooks import CMS_TO_CFS

class ReadableText:
    def __init__(self, title, text):
        self.title, self.text = title, text
    def _repr_markdown_(self):
        fence = "`" * max(4, 1 + max((len(run) for run in re.findall(r"`+", self.text)), default=0))
        return f"#### {self.title}\\n\\n{fence}text\\n{self.text}\\n{fence}"
    def _repr_html_(self):
        return f'<h4>{html.escape(self.title)}</h4><pre>{html.escape(self.text)}</pre>'

pd.set_option("display.max_colwidth", 120)
plt.rcParams.update({"figure.dpi": 120, "axes.grid": True, "grid.alpha": 0.25,
                     "font.family": "Arial", "font.size": 11, "axes.titlesize": 12,
                     "axes.labelsize": 11, "legend.fontsize": 11})
'''


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _save_figure_formats(fig, stem: str, figures: list[Path], raster_dpi: int) -> None:
    """Regenerate every format so provenance cannot describe stale figures."""
    for ext in ("png", "svg", "pdf"):
        path = CURRENT / f"{stem}.{ext}"
        fig.savefig(path, **({"dpi": raster_dpi} if ext == "png" else {}))
        if ext == "svg":
            path.write_bytes(("\n".join(
                line.rstrip() for line in path.read_text(encoding="utf-8").splitlines()
            ) + "\n").encode("utf-8"))
        figures.append(path)


def _prepare_current_outputs() -> dict:
    """Combine the three approved saved arms and render teaching figures."""
    import matplotlib.dates as mdates
    import matplotlib.pyplot as plt
    import numpy as np
    import pandas as pd

    # Authoring size is the intended paper width, so fonts need no downscaling.
    # Embed TrueType fonts in PDF; keep SVG labels as editable text.
    paper_width_mm, raster_dpi = 180, 600
    plt.rcParams.update({"font.family": FIGURE_FONT_FAMILY, "font.size": 10,
                         "axes.titlesize": 10, "axes.labelsize": 10,
                         "xtick.labelsize": 9, "ytick.labelsize": 9,
                         "legend.fontsize": 9, "pdf.fonttype": 42,
                         "svg.fonttype": "none"})

    root = ROOT / "examples/fe_walter/coupled/outputs"
    rule_path = root / "2016/daily.csv"
    llm_path = root / "gemma4_2016_comparison/daily.csv"
    summary_path = root / "2016/summary.json"
    old = pd.read_csv(rule_path)
    new = pd.read_csv(llm_path)
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    seasonal_criteria = json.loads(SEASONAL_CRITERIA.read_text(encoding="utf-8"))
    groups = {
        "rule": old.loc[old["method"].eq("rule")].reset_index(drop=True),
        "llm_available": new.loc[new["engine"].eq("framework") & new["method"].eq("llm_available")].reset_index(drop=True),
        "llm_knowledge": new.loc[new["engine"].eq("framework") & new["method"].eq("llm_knowledge")].reset_index(drop=True),
    }
    dates = pd.date_range("2016-01-01", "2016-12-31").strftime("%Y-%m-%d").tolist()
    initial = float(summary["initial_storage_m3"])
    if not np.isfinite(initial):
        raise ValueError("initial storage must be finite")
    reference = groups["llm_available"]["inflow_cms"]
    checks = {}
    for method, group in groups.items():
        if len(group) != 366 or group["date"].nunique() != 366:
            raise ValueError(f"{method}: expected 366 rows with unique dates")
        if group["date"].tolist() != dates:
            raise ValueError(f"{method}: dates are not the ordered 2016 calendar")
        numeric = ["inflow_cms", "pool_elevation_end_ft", "controlled_release_cms",
                   "spill_cms", "storage_end_m3"]
        if method != "rule":
            numeric.append("storage_start_m3")
        if not np.isfinite(group[numeric].to_numpy(dtype=float)).all():
            raise ValueError(f"{method}: required numeric values must be finite")
        delta = (group["inflow_cms"] - reference).abs()
        if float(delta.max()) >= 1e-10:
            raise ValueError(f"{method}: inflow differs from the shared series")
        if method == "rule":
            start = float(group.loc[0, "storage_end_m3"] - (
                group.loc[0, "inflow_cms"] - group.loc[0, "controlled_release_cms"]
                - group.loc[0, "spill_cms"]) * 86400.0)
        else:
            start = float(group.loc[0, "storage_start_m3"])
        if abs(start - initial) >= 1e-8:
            raise ValueError(f"{method}: initial storage differs from the accepted state")
        checks[method] = {
            "rows": 366, "unique_dates": 366, "date_start": dates[0], "date_end": dates[-1],
            "max_inflow_difference_from_reference_cms": float(delta.max()),
            "initial_storage_m3": start,
        }

    columns = ["method", "date", "inflow_cms", "pool_elevation_end_ft",
               "controlled_release_cms", "spill_cms", "storage_end_m3"]
    frames = []
    for method, group in groups.items():
        part = group[columns].copy()
        part.insert(1, "method_label", LABELS[method])
        part.insert(2, "source_engine", "rule" if method == "rule" else "framework")
        part.insert(3, "source_export", "../2016/daily.csv" if method == "rule"
                    else "../gemma4_2016_comparison/daily.csv")
        frames.append(part)
    combined = pd.concat(frames, ignore_index=True)
    if len(combined) != 1098:
        raise ValueError("combined tutorial export must contain 1,098 rows")
    CURRENT.mkdir(parents=True, exist_ok=True)
    csv_path = CURRENT / "daily.csv"
    combined.to_csv(csv_path, index=False, lineterminator="\n")

    colors = {LABELS[method]: color for method, color in METHOD_COLORS.items()}
    figures = []
    fig, ax = plt.subplots(figsize=(paper_width_mm / 25.4, 82 / 25.4),
                           layout="constrained")
    for label, group in combined.groupby("method_label", sort=False):
        ax.plot(pd.to_datetime(group["date"]), group["pool_elevation_end_ft"],
                label=label, color=colors[label], linewidth=1.1)
    reference_dates, reference_levels = _seasonal_reference_points(seasonal_criteria)
    ax.plot(reference_dates, reference_levels, color="#111111", linestyle="--",
            linewidth=1.0, label="Seasonal pool reference")
    ax.set(ylabel="Water elevation (ft NGVD 29)", xlabel="2016",
           xlim=(pd.Timestamp(dates[0]), pd.Timestamp(dates[-1])))
    _add_elevation_legend(ax)
    _reserve_legend_headroom([ax], float(combined["pool_elevation_end_ft"].min()) - 5,
                             float(combined["pool_elevation_end_ft"].max()))
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b"))
    _save_figure_formats(fig, "daily_water_elevation", figures, raster_dpi)
    plt.close(fig)

    fig, axes = plt.subplots(3, 1, figsize=(paper_width_mm / 25.4, 125 / 25.4),
                             sharex=True, sharey=True, layout="constrained")
    ymax = float(combined[["controlled_release_cms", "inflow_cms"]].max().max()) * CMS_TO_CFS
    for panel, (ax, (label, group)) in enumerate(zip(
            axes, combined.groupby("method_label", sort=False), strict=True)):
        ax.bar(pd.to_datetime(group["date"]), group["controlled_release_cms"] * CMS_TO_CFS,
               width=1, color=colors[label], linewidth=0)
        ax.plot(pd.to_datetime(group["date"]), group["inflow_cms"] * CMS_TO_CFS,
                color="#2878B5", linewidth=0.8, drawstyle="steps-mid",
                label="Upstream simulated inflow")
        ax.set(ylabel="Water release (cfs)", ylim=(0, ymax),
               xlim=(pd.Timestamp(dates[0]), pd.Timestamp(dates[-1])))
        ax.set_title(f"({chr(97 + panel)}) {label}", loc="left", fontweight="bold", pad=4)
        ax.legend(frameon=False, loc="upper left", fontsize=9)
    _reserve_legend_headroom(axes, 0, ymax, flow=True)
    axes[-1].set_xlabel("2016")
    axes[-1].xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    axes[-1].xaxis.set_major_formatter(mdates.DateFormatter("%b"))
    _save_figure_formats(fig, "controlled_release_daily", figures, raster_dpi)
    plt.close(fig)

    fig = plot_reservoir_operations(combined, seasonal_criteria)
    _save_figure_formats(fig, "reservoir_operations", figures, raster_dpi)
    plt.close(fig)

    manifest = {
        "schema_version": "fe-walter-current-tutorial.v1",
        "purpose": "Saved-data teaching comparison; no new provider request, hydrology run, or reservoir simulation.",
        "methods": list(LABELS.values()),
        "period": {"start": dates[0], "end": dates[-1], "days_per_method": 366},
        "figure_layout": {"width_mm": paper_width_mm, "png_dpi": raster_dpi,
                          "minimum_font_pt": 9, "pdf_fonttype": 42,
                          "svg_labels": "editable text", "legend_font_pt": 9,
                          "primary_figure": "reservoir_operations",
                          "primary_height_mm": 160,
                          "panels": {"a": "Water elevation",
                                     **{chr(98 + index): f"Water release ({label})"
                                        for index, label in enumerate(LABELS.values())}},
                          "release_bar_width_days": 0.72,
                          "common_inflow": "Blue upstream simulated daily step trace on every release panel; cfs and common dates.",
                          "method_colors": METHOD_COLORS,
                          "legend_placement": (
                              "Upper left inside each panel; measured y-axis headroom keeps legends above data. "
                              "Elevation legend: two aligned columns, short reference entries above paired LLM labels."),
                          "seasonal_reference": (
                              "Winter 1300 ft and summer 1370 ft references with vertical switches "
                              "on May 15 and October 15, as agreed for the display. These mid-month "
                              "markers summarize R-ZONE seasonal levels, not physical water-level jumps. "
                              "Saved operation targets and study audit windows are unchanged.")},
        "flow_display": {"unit": "cfs", "source_unit": "m3/s", "factor": CMS_TO_CFS,
                         "cubic_foot_m3": 0.028316846592,
                         "source_csv": "daily.csv retains its original *_cms values and units."},
        "units": {"inflow_cms": "m3/s", "controlled_release_cms": "m3/s",
                  "spill_cms": "m3/s", "pool_elevation_end_ft": "ft N.G.V.D.",
                  "storage_end_m3": "m3"},
        "validation": {
            "date_policy": "Exact ordered dates; no interpolation.",
            "inflow_policy": "Absolute tolerance 1e-10 m3/s for CSV serialization.",
            "initial_state_policy": "LLM storage_start_m3 and Rule-based first-step mass-balance reconstruction.",
            "expected_initial_storage_m3": initial, "methods": checks,
        },
        "provenance_note": (
            "These saved curves retain the prompts and context recorded by their source runs; "
            "no new daily or live-date context was supplied for this rendering."
        ),
        "sources": {
            "rule_rows": {"path": "../2016/daily.csv", "sha256": _sha(rule_path)},
            "llm_framework_rows": {"path": "../gemma4_2016_comparison/daily.csv", "sha256": _sha(llm_path)},
            "initial_state": {"path": "../2016/summary.json", "sha256": _sha(summary_path)},
            "seasonal_criteria": {"path": "../../../seasonal_pool_criteria.json",
                                  "sha256": _sha(SEASONAL_CRITERIA)},
            "reference_timing": {"path": "../../../knowledge/operating_rules.md",
                                 "sha256": _sha(OPERATING_KNOWLEDGE)},
        },
        "artifacts": {},
    }
    for path in [csv_path, *figures]:
        manifest["artifacts"][path.name] = _sha(path)
    (CURRENT / "provenance.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return manifest


def md(text: str) -> dict:
    return {"cell_type": "markdown", "id": "m", "metadata": {}, "source": text.strip().splitlines(True)}


def code(source: str) -> dict:
    return {"cell_type": "code", "id": "c", "metadata": {}, "source": source.strip().splitlines(True),
            "execution_count": None, "outputs": []}


def main_cells() -> list[dict]:
    return [
        md('''# F.E. Walter: from weather to a daily reservoir decision

Follow the maintained 2016 configuration from `experiment.yaml` through
hydrology, the reservoir network, a Rule-based operator, and the two LLM
methods: **Rule-based**, **LLM without additional operating knowledge**, and **LLM with additional operating knowledge**. All three use the same inflow, initial state, and physical parameters.

This notebook reads committed files only. It makes no model request and runs no
hydrology or reservoir simulation.

Read the flow from weather through HydroCNHS to saved inflow, then reservoir operations.

![Weather to inflow workflow](../docs/figures/fe-walter-weather-workflow.svg)

[Maintained walkthrough](fe_walter.md) · [Current results](../examples/fe_walter/coupled/README.md#current-saved-2016-results)'''),
        md("## Setup"), code(SETUP),
        md('''## 1. Start from the experiment file

The entry names the physical case, dates, output, agent file, hydrology file,
auditors, and extensions. The LLM entries change the agent and add a model
profile while retaining the same physical case and hydrology.'''),
        code('''coupled = ROOT / "examples/fe_walter/coupled"
current_config = coupled
for title, name in (("Rule-based entry", "experiment.yaml"),
                    ("LLM without additional operating knowledge entry", "llm_available.yaml"),
                    ("LLM with additional operating knowledge entry", "llm_knowledge.yaml")):
    display(ReadableText(title, (current_config / name).read_text(encoding="utf-8")))'''),
        md('''## 2. Follow hydrology into the reservoir network

The accepted HydroCNHS model turns prepared weather and catchment inputs into
daily inflow. `hydrology.yaml` binds routed flow to `FEW_INFLOW`.
`reservoirs.json` maps it to node `FEWalter`, with physical case ID `fe_walter`.
Agent `fe_operator` must name graph node `FEWalter`.

![Reservoir and agent mapping](../docs/figures/reservoir-agent-mapping.svg)'''),
        code('''hydrology = (coupled / "hydrology.yaml").read_text(encoding="utf-8")
case = json.loads((coupled / "reservoirs.json").read_text(encoding="utf-8"))
physical = case["network"]["reservoirs"]["FEWalter"]["physical"]
display(ReadableText("Complete hydrology.yaml", hydrology))
display(pd.DataFrame([{"inflow node": "FEW_INFLOW", "reservoir node": "FEWalter",
    "physical case ID": physical["reservoir_id"], "agent ID": "fe_operator",
    "initial storage (m³)": physical["initial_storage_m3"], "daily step (s)": physical["dt_seconds"]}]))'''),
        md('''## 3. Change the decision method

The Rule-based agent selects a registered rule. The available-information LLM
receives daily state, seasonal instruction, and short history. The
retrieved-knowledge LLM adds selected operating guidance. Model identity and
sampling controls are settings and provenance, not method names.

![Prompt and context workflow](../docs/figures/prompt-context-workflow.svg)'''),
        code('''for title, name in (("Rule-based agent", "agents.rule.yaml"),
                    ("LLM without additional operating knowledge agent", "agents.llm_available.yaml"),
                    ("LLM with additional operating knowledge agent", "agents.llm_knowledge.yaml")):
    display(ReadableText(title, (coupled / name).read_text(encoding="utf-8")))
display(ReadableText("Model settings and provenance", (current_config / "models.yaml").read_text(encoding="utf-8")))'''),
        md('''## 4. Inspect actual prompt and retrieved context

The saved pairs contain the exact request messages and replies. The parser
converts cfs to m³/s, then common physics enforces water availability and release
bounds. These records are examples from the saved run.'''),
        code('''saved = coupled / "outputs/gemma4_2016_comparison"
labels = {"llm_available": "LLM without additional operating knowledge", "llm_knowledge": "LLM with additional operating knowledge"}
for method, label in labels.items():
    pair = json.loads((saved / f"{method}_pair.json").read_text(encoding="utf-8"))
    record = pair["engines"]["framework"]
    display(ReadableText(f"{label}: saved request messages",
                         json.dumps(record["provider_request"]["messages"], indent=2, ensure_ascii=False)))
    display(ReadableText(f"{label}: saved reply", record["raw_provider_reply"]["message"]["content"]))
    display(pd.DataFrame([{"method": label, "saved date": pair["date"],
                           "controlled release (cfs)": record["physics"]["controlled_release_cms"] * CMS_TO_CFS,
                           "end elevation (ft)": record["physics"]["pool_elevation_end_ft"]}]))'''),
        md('''## 5. Compare the three current teaching trajectories

The builder combines Rule-based rows from `outputs/2016/daily.csv` with the two
framework LLM rows from `outputs/gemma4_2016_comparison/daily.csv`. It verifies
366 unique ordered dates per method, common inflow, shared initial state, and
units. It performs no interpolation. Four panels share operation dates:
(a) end-of-day water elevation in feet NGVD 29; (b–d) daily water release in cfs,
one method per panel. Water release means implemented controlled release and
excludes spill. Blue lines show the upstream simulated inflow on the same flow scale.
Release below inflow retains water; release above inflow draws from storage.
The seasonal reference switches vertically between the 1300 ft winter target and
1370 ft summer ceiling on May 15 and October 15. These mid-month markers summarize
seasonal targets, rather than daily physical water-level changes. Saved operation
and audit settings are unchanged. The source CSV retains m³/s.'''),
        code('''current = coupled / "outputs/current_tutorial"
daily = pd.read_csv(current / "daily.csv")
seasonal_criteria = json.loads((ROOT / "examples/fe_walter/seasonal_pool_criteria.json").read_text(encoding="utf-8"))
provenance = json.loads((current / "provenance.json").read_text(encoding="utf-8"))
display(daily.assign(controlled_release_cfs=daily["controlled_release_cms"] * CMS_TO_CFS)
    .groupby("method_label", sort=False).agg(rows=("date", "size"),
    unique_dates=("date", "nunique"), maximum_release_cfs=("controlled_release_cfs", "max")))
display(pd.DataFrame(provenance["validation"]["methods"]).T)'''),
        code('''from tutorials.build_notebooks import plot_reservoir_operations
fig = plot_reservoir_operations(daily, seasonal_criteria)
display(fig)'''),
        md('''## 6. Run a new experiment deliberately

These commands are documentation and are not executed by this notebook. Copy
the chosen entry, set a new `run_id` and output, then check and prepare before
allowing network use.

```powershell
Copy-Item examples/fe_walter/coupled/llm_available.yaml examples/fe_walter/coupled/my-run.yaml
# Edit my-run.yaml: set a new run_id and output.
reservoir-experiment check examples/fe_walter/coupled/my-run.yaml
reservoir-experiment prepare examples/fe_walter/coupled/my-run.yaml
reservoir-experiment run examples/fe_walter/coupled/my-run.yaml --allow-network
reservoir-experiment verify <new-output-path>/operation
```

Use `experiment.yaml` for Rule-based operation or copy `llm_knowledge.yaml` for
LLM with additional operating knowledge. [Technical engine evidence and historical audits](../examples/fe_walter/engine_comparison.md)
remain outside this main research narrative.'''),
    ]


def advanced_cells() -> list[dict]:
    return [
        md('''# Advanced tutorial: a small generic multi-reservoir configuration

This notebook reads `examples/multiple_reservoirs`. It explains IDs, topology,
method mixing, and state separation without executing a simulation or provider.'''),
        md("## Setup"), code(SETUP),
        md('''## 1. Begin with complete maintained source files

The experiment delegates hydrology, physical network, agents, models,
information, auditors, and extensions to separate files. Paths are relative to
the file that declares them.'''),
        code('''example = ROOT / "examples/multiple_reservoirs"
for title, name in (("Rule-only experiment", "experiment.yaml"),
                    ("Mixed-method experiment", "experiment.llm.yaml"),
                    ("Physical network", "reservoirs.yaml"), ("Hydrology bindings", "hydrology.yaml")):
    display(ReadableText(title, (example / name).read_text(encoding="utf-8")))'''),
        md('''## 2. Keep node, reservoir, and agent IDs distinct

`inlet_a` and `inlet_b` are nodes. `lake_a` and `lake_b` are reservoir keys.
`operator_a` and `operator_b` are agents. Each agent's `reservoir_id` must match
one reservoir key, and its history belongs only to that reservoir.'''),
        code('''import yaml
network = yaml.safe_load((example / "reservoirs.yaml").read_text(encoding="utf-8"))["network"]
agents = yaml.safe_load((example / "agents.llm.yaml").read_text(encoding="utf-8"))
display(pd.DataFrame([{"agent ID": a, "reservoir ID": s["reservoir_id"],
    "inflow node": network["reservoirs"][s["reservoir_id"]]["inflow_node"], "type": s["type"]}
    for a, s in agents.items()]))
display(ReadableText("Mixed Rule-based and LLM agents", (example / "agents.llm.yaml").read_text(encoding="utf-8")))'''),
        md('''## 3. Choose topology explicitly

The fixture has independent parallel branches: `inlet_a → lake_a → river_a`
and `inlet_b → lake_b → river_b`. A parallel confluence points both reservoirs
to one junction. A series layout sends an upstream reservoir to a downstream
reservoir inlet. Apply each local inflow once and justify every unit hydrograph.'''),
        code('''display(pd.DataFrame([
    {"layout": "independent", "connections": "lake_a→river_a; lake_b→river_b", "outlets": "river_a, river_b"},
    {"layout": "parallel", "connections": "lake_a→junction; lake_b→junction", "outlets": "junction"},
    {"layout": "series", "connections": "lake_a→inlet_b; lake_b→outlet", "outlets": "outlet"}]))'''),
        md('''## 4. Mix methods without mixing state

The mixed file assigns an LLM to `lake_a` and a Rule-based operator to `lake_b`.
Separate agent IDs, reservoir IDs, histories, and outputs prevent one reservoir's
decision history from becoming another's state. A shared model profile does not
create shared conversation history.'''),
        code('''display(pd.DataFrame([{"agent ID": a, "reservoir ID": s["reservoir_id"],
    "method": "LLM" if s["type"] == "llm" else "Rule-based",
    "local retrieval": bool(s.get("customization", {}).get("context_providers")),
    "state key": f"{a}:{s['reservoir_id']}"} for a, s in agents.items()]))'''),
        md('''## 5. Adapt the fixture

Replace synthetic forcing, basin parameters, reservoir physics, topology,
routing, prompts, knowledge, model settings, and auditors with site evidence.
First check hydrology, units, mass balance, topology, and state isolation with an
offline or Rule-based operator; enable an LLM after the physical path is clear.

[Generic configuration](../docs/USER_GUIDE.md) · [HydroCNHS setup](../docs/HYDROLOGY_SETUP.md) ·
[Multiple-reservoir source files](../examples/multiple_reservoirs/)'''),
    ]


def _rich_data(value) -> dict:
    if hasattr(value, "_repr_markdown_"):
        rendered = value._repr_markdown_()
        if rendered is not None:
            data = {"text/markdown": rendered, "text/plain": rendered}
            if hasattr(value, "_repr_html_"):
                data["text/html"] = value._repr_html_()
            return data
    if hasattr(value, "_repr_html_"):
        rendered = value._repr_html_()
        if rendered is not None:
            return {"text/html": rendered, "text/plain": repr(value)}
    if value.__class__.__module__.startswith("matplotlib") and value.__class__.__name__ == "Figure":
        image = io.BytesIO(); value.savefig(image, format="png", dpi=120, bbox_inches="tight")
        return {"image/png": base64.b64encode(image.getvalue()).decode("ascii"), "text/plain": repr(value)}
    return {"text/plain": str(value)}


def _execute(cells: list[dict], notebook_name: str) -> None:
    namespace = {"__name__": "__main__"}; count = 0
    for cell in cells:
        if cell["cell_type"] != "code":
            continue
        count += 1; displays = []
        namespace["display"] = lambda *values: displays.extend(values)
        stream = io.StringIO(); source = "".join(cell["source"])
        with (contextlib.redirect_stdout(stream),
              patch("socket.socket.connect", side_effect=AssertionError("tutorial network forbidden")),
              patch("urllib.request.build_opener", side_effect=AssertionError("tutorial HTTP forbidden")),
              patch("urllib.request.urlopen", side_effect=AssertionError("tutorial HTTP forbidden"))):
            exec(compile(source, notebook_name, "exec"), namespace)
        cell["execution_count"] = count
        cell["outputs"] = ([{"output_type": "stream", "name": "stdout", "text": stream.getvalue().splitlines(True)}]
                           if stream.getvalue() else [])
        cell["outputs"].extend({"output_type": "display_data", "metadata": {}, "data": _rich_data(v)} for v in displays)


def _notebook(cells: list[dict], name: str, execute: bool) -> dict:
    for index, cell in enumerate(cells):
        cell["id"] = ("m" if cell["cell_type"] == "markdown" else "c") + str(index)
    if execute:
        _execute(cells, name)
    return {"nbformat": 4, "nbformat_minor": 5,
            "metadata": {"kernelspec": {"name": "python3", "language": "python", "display_name": "Python 3"},
                         "language_info": {"name": "python", "version": platform.python_version()},
                         "tutorial_mode": "saved-evidence-only",
                         "execution_method": "ordered pure-Python cells with socket/urllib blocked"},
            "cells": cells}


def build(*, execute: bool) -> list[dict]:
    os.chdir(ROOT); _prepare_current_outputs()
    receipts = []
    for name, cells in {"main.ipynb": main_cells(), "advanced.ipynb": advanced_cells()}.items():
        path = TUTORIALS / name
        path.write_text(json.dumps(_notebook(cells, name, execute), indent=1, ensure_ascii=False) + "\n",
                        encoding="utf-8", newline="\n")
        receipts.append({"path": str(path.relative_to(ROOT)), "executed": execute, "sha256": _sha(path)})
    return receipts


def check() -> list[dict]:
    reports = []
    for name in NOTEBOOKS:
        path = TUTORIALS / name; notebook = json.loads(path.read_text(encoding="utf-8"))
        assert notebook["metadata"]["tutorial_mode"] == "saved-evidence-only"
        cells = [c for c in notebook["cells"] if c["cell_type"] == "code"]
        source = "\n".join("".join(c["source"]) for c in cells)
        assert not any(token in source for token in ("run_settings(", "subprocess.", "urlopen(", "requests.", "ollama.chat"))
        assert all(c.get("execution_count") is not None for c in cells)
        mime = {m for c in cells for o in c.get("outputs", []) for m in o.get("data", {})}
        assert "text/html" in mime
        if name == "main.ipynb":
            assert "image/png" in mime
        reports.append({"path": str(path.relative_to(ROOT)), "cells": len(notebook["cells"]), "mime_types": sorted(mime), "sha256": _sha(path)})
    manifest = json.loads((CURRENT / "provenance.json").read_text(encoding="utf-8"))
    for source in manifest["sources"].values():
        assert _sha(CURRENT / source["path"]) == source["sha256"]
    for name, digest in manifest["artifacts"].items():
        assert _sha(CURRENT / name) == digest
    return reports


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true"); parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if not args.execute and not args.check:
        parser.error("choose --execute or --check")
    result = []
    if args.execute:
        result.extend(build(execute=True))
    if args.check:
        result.extend(check())
    print(json.dumps(result, indent=2, ensure_ascii=False))
