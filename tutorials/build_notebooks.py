"""Build executable lessons and historical teaching figures.

Execution blocks socket and urllib access. The selected operation lesson runs
local hydrology and Rule-based operation; historical lessons read saved results.
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
import runpy
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
TUTORIALS = ROOT / "tutorials"
CURRENT = ROOT / "tests/fixtures/fe_walter_history/coupled_outputs/current_tutorial"
SEASONAL_CRITERIA = ROOT / "examples/fe_walter/seasonal_pool_criteria.json"
OPERATING_KNOWLEDGE = ROOT / "examples/fe_walter/knowledge/operating_rules.md"
NOTEBOOKS = ("operation.ipynb", "main.ipynb", "advanced.ipynb")
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
             "Target pool elevation", LABELS["llm_knowledge"]]
    legend = axis.legend(
        [by_label[label] for label in order], [_legend_label(label) for label in order],
        loc="upper left", ncol=2, alignment="left", frameon=False, fontsize=9,
        handlelength=2.4, handleheight=1.5, handletextpad=0.65,
        columnspacing=1.8, labelspacing=0.65)
    # Explicit bottom alignment avoids font-specific descender offsets between
    # equal legend rows (Arial differs from DejaVu Sans on Matplotlib 3.11).
    for text in legend.get_texts():
        text.set_verticalalignment("bottom")
    return legend


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
            release.set_title(f"({chr(98 + index)}) {label}", loc="left", fontweight="bold")
            release.legend(loc="upper left", frameon=False, fontsize=9,
                           handlelength=2.1, borderaxespad=0.35)
        if seasonal_criteria is None:
            seasonal_criteria = json.loads(SEASONAL_CRITERIA.read_text(encoding="utf-8"))
        seasonal_dates, seasonal_levels = _seasonal_reference_points(seasonal_criteria)
        elevation.plot(seasonal_dates, seasonal_levels, color="#111111", linestyle="--",
                       linewidth=1.0, label="Target pool elevation", zorder=5)
        elevation.set(title="(a)", ylabel="Water elevation\n(ft)")
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

    root = ROOT / "tests/fixtures/fe_walter_history/coupled_outputs"
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
            linewidth=1.0, label="Target pool elevation")
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
                              "Target pool elevation: winter 1300 ft and summer 1370 ft references with vertical switches "
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
    return _walkthrough_cells()


def operation_cells() -> list[dict]:
    """Load the focused five-year lesson only when that notebook is requested."""
    # The direct CLI starts with tutorials/ on sys.path, rather than its parent.
    # Load the sibling source explicitly so installed package paths are irrelevant.
    lesson = runpy.run_path(str(TUTORIALS / "operation.py"))
    return lesson["build_cells"](md=md, code=code)


def _walkthrough_cells() -> list[dict]:
    """Build the canonical FE Walter lesson from the actual configuration files.

    File contents are read during notebook execution, so saved teaching outputs
    and the downloadable settings have one source. Execution only loads settings
    and saved results; the run commands remain Markdown instructions.
    """
    setup = code(SETUP + '''
def show_file(name, *, expanded=True):
    # Resolve example paths from the repository root in any notebook working directory.
    path = ROOT / name
    text = path.read_text(encoding="utf-8")
    class FileContents:
        def __repr__(self):
            return text
        def _repr_html_(self):
            content = f'<pre class="prompt-text config-source">{html.escape(text)}</pre>'
            if expanded:
                return content
            return f'<details><summary>{html.escape(path.name)} — complete text</summary>{content}</details>'
    display(FileContents())

coupled = ROOT / "examples/fe_walter/coupled"
''')
    setup["metadata"]["tags"] = ["hide-input"]
    return [
        md('''# F.E. Walter: historical 2016 configuration walkthrough

## Goal

Start with `experiment.yaml`, follow its file references, and change the reservoir
operator from **Rule-based** to either **LLM without additional operating knowledge**
or **LLM with additional operating knowledge**. Then inspect the saved 2016 results.

This lesson preserves the 2016 configuration and evidence route. For the current
2021–2025 prepared operation, start with [operation.ipynb](operation.ipynb).

Read the notebook in order:

1. [Experiment](#1-start-with-experimentyaml)
2. [Hydrology](#2-connect-hydrology)
3. [Reservoir and network](#3-define-the-reservoir-and-water-connections)
4. [Rule-based operator and audit](#4-assign-the-rule-based-operator)
5. [LLM operator](#5-switch-to-an-llm-operator)
6. [Model settings](#6-set-the-model-parameters)
7. [Prompts and knowledge](#7-read-the-prompts-and-operating-knowledge)
8. [Check settings](#8-check-the-three-configurations)
9. [Run instructions](#9-run-your-own-experiment)
10. [Saved results](#10-read-the-saved-2016-results)
11. [Downstream flow](#11-compare-flow-at-the-downstream-station)

## Setup

Complete [installation](../docs/GETTING_STARTED.md) in a local clone. Install JupyterLab in that
environment with `python -m pip install jupyterlab`. Open `tutorials/main.ipynb` in Jupyter or VS Code,
select that Python environment, and run cells from top to bottom. Keep the notebook
inside the clone so its relative file links work.

This lesson reads settings and saved data. It makes no model request and runs no
hydrology or reservoir simulation. Ollama is needed only when you later choose to
run an LLM experiment. Open the setup cell below to inspect imports and file helpers.

[Example folder](../examples/fe_walter/) · [Site and data](../examples/fe_walter/README.md)'''),
        setup,
        md('''## 1. Start with experiment.yaml

The experiment file connects the other settings. Begin with the Rule-based entry:
[experiment.yaml](../examples/fe_walter/coupled/experiment.yaml), in the
[coupled folder](../examples/fe_walter/coupled/). The next cell displays the complete
file, including its comments. File paths are resolved relative to the file that
declares them.'''),
        code('''show_file("examples/fe_walter/coupled/experiment.yaml")'''),
        md('''| Field | What to enter and why |
|---|---|
| `schema_version` | Required settings format accepted by the loader; independent of the package version. Keep this value. |
| `run_id` | A label recorded with the run. Choose a new label for a new experiment. |
| `case` | Path to the physical reservoir and network file, here `reservoirs.json`. |
| `output` | Directory for this run's generated files. Set a new directory as well as a new `run_id`. |
| `start_date`, `end_date` | Inclusive operation dates. This example has 366 daily steps in 2016. |
| `max_calls` | Run-wide LLM attempt budget: `0` for Rule-based; `null` in the LLM entries leaves it uncapped. Per-decision retries are set separately. |
| `agents.file` | File assigning the operator to the reservoir. See step 4. |
| `auditors.file` | File defining the checks selected by an operator. See step 4. |
| `hydrology.file` | File connecting the native hydrology model and weather to network inflow. See step 2. |
| `extensions` | Python files registering the example's rule or decision backend. Keep the supplied paths for this example. |

The following steps open each referenced file. Keep the shared hydrology and
physical case when comparing decision methods.'''),
        md('''## 2. Connect hydrology

[hydrology.yaml](../examples/fe_walter/coupled/hydrology.yaml) connects an accepted
HydroCNHS model to the reservoir experiment. HydroCNHS is the hydrological software;
the model defines the subcatchments and flow outlets. Here it uses GWLF runoff
and Lohmann routing to calculate upstream flow before daily reservoir operation.'''),
        code('''show_file("examples/fe_walter/coupled/hydrology.yaml")'''),
        md('''| Field | Input and connection |
|---|---|
| `model` | The bundled [native model YAML](../data/accepted/fe_walter_hydrology.yaml), including accepted catchment and routing parameters. |
| `forcing` | The bundled [1989–2025 weather table](../data/accepted/fe_walter_forcing_1989_2025.csv.gz). Daily precipitation is in mm, temperature in °C, and PET in cm. |
| `zero_flow_nodes` | Declares the aggregation outlet as a node with no additional local runoff. Upstream routed water still reaches it. |
| `inflow_bindings.FEW_INFLOW.routed` | Sends the hydrology outlet `__AGGREGATION_OUTLET__` to reservoir inlet `FEW_INFLOW`. |
| `inflow_bindings.Downstream.constant` | Adds 0 m³/s of local inflow at the downstream node. Reservoir outflow is routed there separately. |

`model` is a YAML key. The manual uses `hydrology.model` to mean its position in
the experiment settings; it is a field location, rather than a function call.

The weather table contains Daymet precipitation and temperature and PET calculated
with the Hamon method. The native model has a longer record for hydrological setup;
the experiment selects only 2016 for reservoir operation. During preparation,
HydroCNHS produces inflow for these operation dates. The reservoir then advances
one day at a time. These LLM settings provide daily reservoir state, inflow and
decision history; they do not pass the complete weather record to the LLM.

To study downstream conditions, connect tributary inflow through
`inflow_bindings`. Downstream observations, demand or operating limits can be
selected through a [decision information profile](../docs/INFORMATION.md).
The generic LLM path can insert a selected profile through `$information`.
The FE Walter `reference_v3_7` backend appends the selected profile to its native
user message. Both LLM methods also support fixed prompt variables and custom
retrieval callbacks. The optional example after step 7 shows the settings.
Observation timestamps and availability determine what the operator may see;
completed downstream simulation steps can inform later decisions. The supplied
annual comparison keeps its original inputs.

See [site and data](../examples/fe_walter/README.md) for sources and the PET equation.
Use [HydroCNHS tutorials](https://github.com/cylin928/HydroCNHS/tree/main/tutorials) for model construction
and calibration. The diagram summarizes how the prepared data connect.

![Weather, hydrology and reservoir operation](../docs/figures/fe-walter-weather-workflow.svg)'''),
        md('''## 3. Define the reservoir and water connections

[reservoirs.json](../examples/fe_walter/coupled/reservoirs.json) defines water storage,
release limits and the directed network. JSON is displayed without comments so
the file remains valid; the tables below explain its fields.'''),
        code('''show_file("examples/fe_walter/coupled/reservoirs.json")
case = json.loads((coupled / "reservoirs.json").read_text(encoding="utf-8"))
physical = case["network"]["reservoirs"]["FEWalter"]["physical"]'''),
        md('''| Name or field | Meaning |
|---|---|
| `schema_version` | Physical-case format; `network.schema_version` identifies the network format. Keep the supplied supported versions. |
| `FEW_INFLOW` | Inlet receiving the routed HydroCNHS flow from step 2. |
| `FEWalter` | Reservoir node in the operation network. The agent's `reservoir_id` must match this name. |
| `physical.reservoir_id: fe_walter` | Physical profile identifier, distinct from the network node name. |
| `connections` | Sends `FEWalter` outflow to `Downstream`. The supplied `[1.0]` unit hydrograph passes it through in the same daily step; this is an explicit routing assumption. |
| `outlet: Downstream` | Network outlet where routed outflow is recorded. |
| `live_readiness` | Readiness declaration for this teaching case. Its notes record the initial-state and routing assumptions. |

Physical fields are required for storage and release calculations. The next table
reads their actual values from the JSON.'''),
        code('''units = {"capacity_m3": "m³", "dead_storage_m3": "m³", "initial_storage_m3": "m³",
         "minimum_release_cms": "m³/s", "maximum_release_cms": "m³/s", "dt_seconds": "s"}
display(pd.DataFrame([
    {"field": key, "value": f"{physical[key]:,.6f}".rstrip("0").rstrip("."), "unit": unit}
    for key, unit in units.items()
]).set_index("field"))'''),
        md('''`capacity_m3` is the storage ceiling; `dead_storage_m3` is the lower storage bound.
`initial_storage_m3` initializes the first day and is an assumed initial condition,
rather than an observed 1 January 2016 value. Release limits are approximately
50–10,000 cfs. `dt_seconds: 86400` gives one daily step.

The engine updates storage using inflow minus controlled release and spill over
the time step. Direct reservoir precipitation, evaporation, seepage and withdrawals
are zero in this configuration. Catchment PET is already part of the upstream
hydrology. The daily storage and elevation records describe the resulting state;
the plotting code reads those saved records. See the [water balance](../examples/fe_walter/README.md#reservoir-experiment)
for the equation and assumptions.

The agent receives reservoir state and proposes a release. Water then follows the
network connections shown below.

![Reservoir, water connections and operator](../docs/figures/reservoir-agent-mapping.svg)'''),
        md('''## 4. Assign the Rule-based operator

[agents.rule.yaml](../examples/fe_walter/coupled/agents.rule.yaml) assigns operator
`fe_operator` to node `FEWalter`. The rule extension registered in `experiment.yaml`
provides the Hanasaki policy.'''),
        code('''show_file("examples/fe_walter/coupled/agents.rule.yaml")'''),
        md('''| Field | Meaning |
|---|---|
| `fe_operator` | Agent ID used for its own state and decision history. |
| `reservoir_id` | Network node controlled by this agent: `FEWalter`. |
| `type: rule_based`, `rule: hanasaki` | Select the registered rule and its decision function. |
| `rule_parameters` | Policy settings: `purpose`, coefficient `alpha`, and the [inflow statistics JSON](../data/benchmark/fe_walter_statistics.json). |
| `auditors` | Names of checks defined in `auditors.yaml`. |

This rule uses storage, inflow and inflow statistics. Seasonal pool criteria are
used in evaluating the results; this rule does not use those criteria as daily
water-level targets.

[auditors.yaml](../examples/fe_walter/coupled/auditors.yaml) defines the shared
`release_limits` check selected by all three agents.'''),
        code('''show_file("examples/fe_walter/coupled/auditors.yaml")'''),
        md('''| Field | Meaning |
|---|---|
| `release_limits` | Check profile referenced by `agents.*.auditors`. |
| `type: release_bounds` | Registered check comparing the proposed release with physical limits in m³/s. |
| `version` | Version recorded for the check definition. |

The auditor records compliance. The physical engine separately implements release
and water-availability limits. Seasonal compliance is recorded without resampling
an LLM response or forcing its release to a seasonal target.'''),
        md('''## 5. Switch to an LLM operator

Choose one of the supplied experiment entries in the [same folder](../examples/fe_walter/coupled/).
Each retains the shared hydrology, physical case and dates.

| Method | Experiment entry | Agent file |
|---|---|---|
| Rule-based | [experiment.yaml](../examples/fe_walter/coupled/experiment.yaml) | [agents.rule.yaml](../examples/fe_walter/coupled/agents.rule.yaml) |
| LLM without additional operating knowledge | [llm_available.yaml](../examples/fe_walter/coupled/llm_available.yaml) | [agents.llm_available.yaml](../examples/fe_walter/coupled/agents.llm_available.yaml) |
| LLM with additional operating knowledge | [llm_knowledge.yaml](../examples/fe_walter/coupled/llm_knowledge.yaml) | [agents.llm_knowledge.yaml](../examples/fe_walter/coupled/agents.llm_knowledge.yaml) |

Read the two complete LLM entries and their agent definitions below. In an LLM
entry, `models.file` adds the model profiles, `agents.file` selects the LLM agent,
and `extensions` registers its decision backend. The entries also use distinct
run labels and output directories.'''),
        code('''show_file("examples/fe_walter/coupled/llm_available.yaml")
show_file("examples/fe_walter/coupled/agents.llm_available.yaml")'''),
        code('''show_file("examples/fe_walter/coupled/llm_knowledge.yaml")
show_file("examples/fe_walter/coupled/agents.llm_knowledge.yaml")'''),
        md('''| Agent field | Meaning |
|---|---|
| `type: llm` | Select an LLM operator for the same reservoir node. |
| `model_profile: reservoir_model` | Select the named profile in `models.yaml` (step 6). |
| `customization.backend` | Registered backend that constructs requests and parses responses. The supplied `reference_v3_7` ID is retained for compatibility. |
| `parameters.reference.profile` | Select the FE Walter case's prompt variables and physical profile. |
| `method` | Compatibility IDs `zeroshot` and `dkp` select the two LLM methods in the table above. |
| `consultation_mode: daily` | Request one decision per operation day, subject to the configured retry policy. |
| `response_validation: policy` | Validate the structured decision using the supplied policy schema. |
| `system_prompt`, `system_prompt_mode` | Load the complete custom system instructions from the specified text file. |
| `seasonal_criteria_file` | Add the date's seasonal window and water-level condition from the shared criteria JSON. |
| `prompt_storage` | Controls whether storage is displayed in the user message; `false` retains the supplied prompt format. |
| `hide_availability_line`, `dkp_no_missing_inputs` | Control availability and missing-input text in the supplied prompts. |
| `zeroshot_knowledge: target` | Retain the baseline target instructions for the method without additional operating knowledge. |
| `dkp` | Knowledge file used by the method with additional operating knowledge. |

Retain these settings for the supplied comparison. When adapting the example,
change one source at a time and check the resolved configuration before running.'''),
        md('''## 6. Set the model parameters

[models.yaml](../examples/fe_walter/coupled/models.yaml) defines `reservoir_model`,
which both LLM agents select. The same profile keeps their generation settings
aligned. The notebook only displays this file.'''),
        code('''show_file("examples/fe_walter/coupled/models.yaml")'''),
        md('''| Field | Meaning |
|---|---|
| `provider`, `base_url` | Ollama and its local HTTP service address. |
| `model` | Required model tag for a live run. Install that tag before running an LLM experiment. |
| `temperature` | Sampling temperature, here `0.7`. Different replies can lead to different subsequent reservoir states. |
| `max_tokens` | Maximum generated tokens per response; mapped to Ollama `num_predict`. |
| `num_ctx` | Context-window size in tokens. |
| `think` | Provider thinking-mode setting. |
| `keep_alive` | How long Ollama retains the loaded model after use. |
| `seed` | Optional sampling seed; `null` leaves it unspecified. |
| `timeout_seconds` | Timeout per HTTP attempt in seconds. |
| `api_key_env` | Optional environment-variable name containing a provider key; unused for this local profile. |
| `max_attempts`, `retry_delay_seconds` | At most two attempts per decision, separated by two seconds. |

Keep secrets in environment variables. See [model providers](../docs/MODEL_PROVIDERS.md)
for other supported provider profiles.'''),
        md('''## 7. Read the prompts and operating knowledge

The system prompt states the task and response format. The user message supplies
the current date, reservoir conditions and recent decision history. Both methods
receive seasonal instructions; the knowledge method adds retrieved operating
guidance. The LLM proposes release; the engine then converts cfs to m³/s and
applies the physical constraints.

Read the complete current prompt files:
[available_information.txt](../examples/fe_walter/prompts/available_information.txt)
and [retrieved_knowledge.txt](../examples/fe_walter/prompts/retrieved_knowledge.txt).
The filenames are retained as configuration references; the table in step 5 gives
the current method names.'''),
        code('''show_file("examples/fe_walter/prompts/available_information.txt", expanded=False)
show_file("examples/fe_walter/prompts/retrieved_knowledge.txt", expanded=False)'''),
        md('''The knowledge method reads
[operating_rules.md](../examples/fe_walter/knowledge/operating_rules.md) from the
[knowledge folder](../examples/fe_walter/knowledge/). It holds case-specific
operating guidance used for retrieval. The shared
[seasonal_pool_criteria.json](../examples/fe_walter/seasonal_pool_criteria.json)
defines the seasonal windows, their water-level conditions and transition dates.
The backend derives the applicable window from the simulation date and adds it
to the daily prompt, without prescribing a release. Expand either file below.'''),
        code('''show_file("examples/fe_walter/knowledge/operating_rules.md", expanded=False)
show_file("examples/fe_walter/seasonal_pool_criteria.json", expanded=False)'''),
        md('''The saved 2016 results in step 10 were generated before this daily seasonal
context was added. Displaying the current files does not change those historical
requests or trajectories. The [saved prompt comparison](../examples/fe_walter/prompt_review.md)
shows the actual October requests and replies, alongside the proposed correction.

The diagram summarizes how instructions, state and optional knowledge form a request.

![Prompt, daily state and optional knowledge](../docs/figures/prompt-context-workflow.svg)'''),
        md('''### Optional: add downstream observations and retrieved passages

Use a copy of an LLM entry and its agent file. Add the experiment's
`information.file` reference to
[fe_walter_information.yaml](config/fe_walter_information.yaml). The complete
file below selects a downstream flow in cfs. Its
[CSV](../tests/fixtures/fe_walter_information/gauge.csv) contains synthetic
interface data; replace it with your observations for a study.'''),
        code('''show_file("tutorials/config/fe_walter_information.yaml")'''),
        md('''In the agent's existing `customization` block, retain `backend` and
`parameters`, then add these optional fields:

```yaml
information: downstream_conditions  # Profile ID from the information file.
prompt_variables:
  study_note: Your study-specific instructions.
context_providers:
  operating_context:                 # Label shown in the added prompt section.
    extension: saved_retrieval       # Registry ID declared in the experiment.
    config:
      passages_file: ../../../tests/fixtures/fe_walter_information/passages.json
      query: downstream operating guidance
    preview:                         # A check-time value; no retrieval is executed.
      query: preview only
      passages: []
```

From the `coupled` folder, the experiment additions are
`information: {file: ../../../tutorials/config/fe_walter_information.yaml}` and
`saved_retrieval: ../extensions/retrieval/__init__.py` inside `extensions`.
The existing backend registration stays in that mapping. Relative paths start
from the file that declares them.

| Field | What reaches the request |
|---|---|
| `information` | Selected station values, units and availability under Additional decision information. |
| `prompt_variables` | Fixed text or JSON under a section labelled by its key. |
| `context_providers` | The callback's text or JSON, with its query and document IDs. |
| `preview` | Only the configuration preview. The callback supplies the decision-time value. |

The [local retrieval adapter](../examples/fe_walter/extensions/retrieval/__init__.py)
reads saved synthetic passages through `build_context(config)`. Register your
own callback with the same interface to connect a vector database. It receives
an immutable `DecisionContext` and returns a `ContextValue` containing the query,
passages and provenance. Required unavailable inputs and callback errors stop
before a provider request. See the [adapter guide](../examples/fe_walter/extensions/retrieval/README.md)
for timestamps, source pins, retry and resume behavior. These cells only display
settings; they perform no retrieval, model request or simulation.'''),
        md('''## 8. Check the three configurations

`load_coupled_settings` is a Python function that reads the experiment and resolves
its referenced files. It validates the settings without calling a provider or
calculating hydrology. The next cell checks all three entries. Expect 366 days,
zero network calls, and planned LLM decisions of 0, 366 and 366 respectively.'''),
        code('''from llm_reservoir_agent.coupled import load_coupled_settings

entries = {"Rule-based": "experiment.yaml",
           "LLM without additional operating knowledge": "llm_available.yaml",
           "LLM with additional operating knowledge": "llm_knowledge.yaml"}
checks = []
for method, filename in entries.items():
    settings = load_coupled_settings(coupled / filename)
    report = settings.report
    checks.append({"method": method, "days": report["days"],
                   "network calls": report["network_calls"],
                   "planned LLM decisions": report["planned_llm_calls"]})
display(pd.DataFrame(checks).set_index("method"))'''),
        md('''## 9. Run your own experiment

The commands below are instructions for a future run; the notebook does not execute
them. Work from the repository root. Copy the chosen entry within the `coupled`
folder so its relative references still resolve. In the copy, set both a new
`run_id` and a new `output` directory.

| Command | What it does |
|---|---|
| `check` | Resolve and validate settings without inference or hydrology. |
| `prepare` | Calculate and save upstream inflow using the configured HydroCNHS model. |
| `run` | Advance daily reservoir operation; LLM entries require explicit network permission. |
| `verify` | Check the saved operation records and physical consistency. Seasonal performance is evaluated separately. |

For an LLM experiment, start the configured provider and install the model first.
The example below selects the method without additional operating knowledge.

```powershell
Copy-Item examples/fe_walter/coupled/llm_available.yaml examples/fe_walter/coupled/my-run.yaml
# Edit my-run.yaml: set a new run_id and output directory.
reservoir-experiment check examples/fe_walter/coupled/my-run.yaml
reservoir-experiment prepare examples/fe_walter/coupled/my-run.yaml
reservoir-experiment run examples/fe_walter/coupled/my-run.yaml --allow-network
reservoir-experiment verify <new-output-path>/operation
```

For Rule-based operation, copy `experiment.yaml` and omit `--allow-network`.
For the other LLM method, copy `llm_knowledge.yaml` and retain the network flag.
Use [running instructions](../docs/RUNNING.md) to inspect generated files or resume
an interrupted run. Continue below to read results that are already available.'''),
        md('''## 10. Read the saved 2016 results

The [saved daily CSV](../tests/fixtures/fe_walter_history/coupled_outputs/current_tutorial/daily.csv)
contains 366 dates per method. Its [provenance](../tests/fixtures/fe_walter_history/coupled_outputs/current_tutorial/provenance.json)
identifies the source runs and validation. The teaching table combines Rule-based
rows from `outputs/2016/daily.csv` with framework LLM rows from
`outputs/gemma4_2016_comparison/daily.csv`. All methods share inflow and initial
storage. The following cells read saved values and draw them without interpolation.'''),
        code('''current = ROOT / "tests/fixtures/fe_walter_history/coupled_outputs/current_tutorial"
daily = pd.read_csv(current / "daily.csv")
seasonal_criteria = json.loads((ROOT / "examples/fe_walter/seasonal_pool_criteria.json").read_text(encoding="utf-8"))
provenance = json.loads((current / "provenance.json").read_text(encoding="utf-8"))
display(daily.groupby("method_label", sort=False).agg(
    rows=("date", "size"), unique_dates=("date", "nunique"),
    first_date=("date", "min"), last_date=("date", "max")))'''),
        md('''Four panels share operation dates. Panel (a) shows end-of-day water elevation;
panels (b–d) show each method's daily water release. Blue lines show the upstream simulated inflow
on the same flow scale. Water release is implemented controlled release and excludes
spill. When release exceeds inflow, storage supplies the difference; when inflow
exceeds total outflow, storage rises until capacity is reached.

The target pool elevation reference switches vertically between the 1300 ft winter
target and 1370 ft summer ceiling on May 15 and October 15. These display markers
summarize the targets; the criteria file retains the full seasonal windows. The
summer ceiling is an upper bound, rather than a fixed required elevation.

The plotting function is shared by the notebook and paper exports. The cell below
only plots saved data.'''),
        code('''from tutorials.build_notebooks import plot_reservoir_operations

fig = plot_reservoir_operations(daily, seasonal_criteria)
display(fig)'''),
        md('''*Figure 1. F.E. Walter reservoir operation, 1 January–31 December 2016.
Elevation is in feet NGVD 29; release and upstream simulated inflow are in cfs.
The source CSV retains flows in m³/s. LLM trajectories retain the prompts used by
their source runs, before daily seasonal context was added.*

Download the accepted [PDF](../tests/fixtures/fe_walter_history/coupled_outputs/current_tutorial/reservoir_operations.pdf),
[SVG](../tests/fixtures/fe_walter_history/coupled_outputs/current_tutorial/reservoir_operations.svg)
or [600 dpi PNG](../tests/fixtures/fe_walter_history/coupled_outputs/current_tutorial/reservoir_operations.png).
See [output files](../examples/fe_walter/notebook.md) for the saved-data inventory
and [results](../examples/fe_walter/results.md) for interpretation. Detailed engine
comparisons and historical audits remain in the [technical reference](../examples/fe_walter/engine_comparison.md).'''),
        md('''## 11. Compare flow at the downstream station

The [watershed map](../tests/fixtures/fe_walter_history/downstream_outputs/watershed.png) separates
water entering FE Walter from runoff joining the river below the dam. The
[downstream daily CSV](../tests/fixtures/fe_walter_history/downstream_outputs/daily.csv) contains
saved release plus spill routed to USGS 01447800, lateral runoff and observations.
This cell reads the saved comparison; it makes no model request or hydrology run.

The old reservoir inlet included the whole gauge watershed. These curves hold
its historical releases fixed. The [downstream reference](../examples/fe_walter/downstream/README.md)
explains the corrected configuration, transferred parameters and boundary precision.
USGS observations are used only for evaluation.'''),
        code('''from examples.fe_walter.downstream.plot import plot_streamflow

downstream = ROOT / "tests/fixtures/fe_walter_history/downstream_outputs"
gauge_daily = pd.read_csv(downstream / "daily.csv")
assert gauge_daily.groupby("method")["date"].nunique().eq(366).all()
fig = plot_streamflow(gauge_daily)
display(fig)'''),
        md('''*Figure 2. Conditional downstream daily mean discharge (cfs), 2016.
Each saved method is compared against USGS 01447800. Grey shading marks the
20-day initial-channel assumption; 346 days remain for paired evaluation.
Boundary-corrected coupled LLM trajectories have not been run.*'''),

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
    if hasattr(value, "_repr_png_"):
        rendered = value._repr_png_()
        if rendered is not None:
            if isinstance(rendered, tuple):
                rendered = rendered[0]
            if isinstance(rendered, bytes):
                rendered = base64.b64encode(rendered).decode("ascii")
            return {"image/png": rendered, "text/plain": repr(value)}
    if hasattr(value, "_repr_svg_"):
        rendered = value._repr_svg_()
        if rendered is not None:
            return {"image/svg+xml": rendered, "text/plain": repr(value)}
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
            if notebook_name == "operation.ipynb":
                # Match Jupyter's final-expression display for the executable lesson.
                import ast
                tree = ast.parse(source)
                last = tree.body.pop() if tree.body and isinstance(tree.body[-1], ast.Expr) else None
                exec(compile(tree, notebook_name, "exec"), namespace)
                if last is not None:
                    value = eval(compile(ast.Expression(last.value), notebook_name, "eval"), namespace)
                    if value is not None:
                        displays.append(value)
            else:
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
                         "tutorial_mode": "executable-rule-based" if name == "operation.ipynb" else "saved-evidence-only",
                         "execution_method": "ordered pure-Python cells with socket/urllib blocked"},
            "cells": cells}


def _retain_execution(cells: list[dict], name: str, path: Path) -> dict:
    """Keep verified outputs only when every executable cell is unchanged.

    Documentation builds must not erase the completed lesson or silently attach
    old outputs to changed computation. Explicit execution refreshes the record.
    """
    current = _notebook(cells, name, execute=False)
    previous = json.loads(path.read_text(encoding="utf-8"))
    old = [cell for cell in previous["cells"] if cell["cell_type"] == "code"]
    new = [cell for cell in current["cells"] if cell["cell_type"] == "code"]
    if ([cell["source"] for cell in new] != [cell["source"] for cell in old]
            or previous["metadata"].get("execution_dependencies") != _operation_dependencies()
            or not old
            or [cell.get("execution_count") for cell in old] != list(range(1, len(old) + 1))
            or any(output["output_type"] == "error" for cell in old for output in cell.get("outputs", []))
            or sum("image/png" in output.get("data", {}) for cell in old for output in cell.get("outputs", [])) != 2
            or not any("text/html" in output.get("data", {}) for cell in old for output in cell.get("outputs", []))):
        raise ValueError("Operation lesson needs a completed execution matching its code cells")
    for target, source in zip(new, old, strict=True):
        target["execution_count"] = source["execution_count"]
        target["outputs"] = source["outputs"]
    current["metadata"] = previous["metadata"]
    return current


def _operation_dependencies() -> dict[str, str]:
    """Bind retained results to their current case inputs and implementation."""
    case = ROOT / "examples/fe_walter/operation"
    provenance = json.loads((case / "provenance.json").read_text(encoding="utf-8"))
    paths = {case / name for name in provenance["originals"]}
    paths.update(case / name for name in provenance["artifacts"])
    engineering = json.loads((case / "engineering-sources-v4.json").read_text(encoding="utf-8"))
    paths.update(ROOT / engineering["dependencies"][name]["current_path"]
                 for name in provenance["shared_dependencies"])
    paths.update((ROOT / "src/llm_reservoir_agent").rglob("*.py"))
    paths.update(case.rglob("*.py"))
    paths.add(case / "provenance.json")
    paths.add(case / "engineering-sources-v4.json")
    retained = case / "hydrology/calibration-lineage-summary.json"
    if retained.is_file():
        paths.add(retained)
    return {path.relative_to(ROOT).as_posix(): hashlib.sha256(
        path.read_bytes().replace(b"\r\n", b"\n") if path.suffix == ".py" else path.read_bytes()).hexdigest()
        for path in sorted(paths)}


def build(*, execute: bool, notebook: str | None = None) -> list[dict]:
    """Build lessons; the operation lesson executes only when explicitly selected.

    A complete build retains that lesson's matching execution outputs.
    Select operation.ipynb with execute=True to verify its real CPU simulation.
    """
    os.chdir(ROOT)
    if notebook is None:
        _prepare_current_outputs()
    elif notebook not in NOTEBOOKS:
        raise ValueError(f"Unknown notebook: {notebook}")
    receipts = []
    builders = {
        "operation.ipynb": operation_cells,
        "main.ipynb": main_cells,
        "advanced.ipynb": advanced_cells,
    }
    selected = NOTEBOOKS if notebook is None else (notebook,)
    for name in selected:
        cells = builders[name]()
        path = TUTORIALS / name
        run_cells = execute and (name != "operation.ipynb" or notebook == name)
        document = (_retain_execution(cells, name, path)
                    if name == "operation.ipynb" and notebook is None
                    else _notebook(cells, name, run_cells))
        if name == "operation.ipynb" and run_cells:
            document["metadata"]["execution_dependencies"] = _operation_dependencies()
        path.write_text(json.dumps(document, indent=1, ensure_ascii=False) + "\n",
                        encoding="utf-8", newline="\n")
        receipts.append({"path": str(path.relative_to(ROOT)), "executed": run_cells, "sha256": _sha(path)})
    return receipts


def check() -> list[dict]:
    reports = []
    for name in NOTEBOOKS:
        path = TUTORIALS / name; notebook = json.loads(path.read_text(encoding="utf-8"))
        expected_mode = "executable-rule-based" if name == "operation.ipynb" else "saved-evidence-only"
        assert notebook["metadata"]["tutorial_mode"] == expected_mode
        cells = [c for c in notebook["cells"] if c["cell_type"] == "code"]
        source = "\n".join("".join(c["source"]) for c in cells)
        forbidden = ("subprocess.", "urlopen(", "requests.", "ollama.chat", "allow_network=True")
        assert not any(token in source for token in forbidden)
        if name != "operation.ipynb":
            assert "run_settings(" not in source
            assert all(c.get("execution_count") is not None for c in cells)
        mime = {m for c in cells for o in c.get("outputs", []) for m in o.get("data", {})}
        if name != "operation.ipynb":
            assert "text/html" in mime
        if name == "main.ipynb":
            assert "image/png" in mime
        if name == "operation.ipynb":
            _retain_execution(operation_cells(), name, path)
            assert "check_preparation" in source
            assert "prepare_coupled(simulation)" in source
            assert "run_settings(operation_settings, runtime_root=ROOT)" in source
            assert "plot_run(run_output" in source
            counts = [c.get("execution_count") for c in cells]
            assert counts == list(range(1, len(cells) + 1))
            assert "image/png" in mime and "text/html" in mime
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
    parser.add_argument("--notebook", choices=NOTEBOOKS,
                        help="Build only this notebook; preserve existing figure exports and other notebooks")
    args = parser.parse_args()
    if not args.execute and not args.check:
        parser.error("choose --execute or --check")
    result = []
    if args.execute:
        result.extend(build(execute=True, notebook=args.notebook))
    if args.check:
        result.extend(check())
    print(json.dumps(result, indent=2, ensure_ascii=False))
