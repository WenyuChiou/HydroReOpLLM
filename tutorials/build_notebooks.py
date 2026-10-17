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
NOTEBOOKS = ("main.ipynb", "advanced.ipynb")
LABELS = {
    "rule": "Rule-based",
    "llm_available": "LLM with available information",
    "llm_knowledge": "LLM with retrieved knowledge",
}

SETUP = '''from pathlib import Path
import html, json, re, sys
ROOT = next(p for p in [Path.cwd(), *Path.cwd().parents] if (p / "src/hydrocnhs").is_dir())
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))
import pandas as pd
import matplotlib.pyplot as plt

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


def _prepare_current_outputs() -> dict:
    """Combine the three approved saved arms and render two figures."""
    import matplotlib.dates as mdates
    import matplotlib.pyplot as plt
    import numpy as np
    import pandas as pd

    plt.rcParams.update({"font.family": "Arial", "font.size": 11,
                         "axes.titlesize": 12, "axes.labelsize": 11,
                         "legend.fontsize": 11})

    root = ROOT / "examples/fe_walter/coupled/outputs"
    rule_path = root / "2016/daily.csv"
    llm_path = root / "gemma4_2016_comparison/daily.csv"
    summary_path = root / "2016/summary.json"
    old = pd.read_csv(rule_path)
    new = pd.read_csv(llm_path)
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
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

    colors = {LABELS["rule"]: "#3b6ea8", LABELS["llm_available"]: "#d97932",
              LABELS["llm_knowledge"]: "#2f8f68"}
    figures = []
    fig, ax = plt.subplots(figsize=(10.5, 4.8))
    for label, group in combined.groupby("method_label", sort=False):
        ax.plot(pd.to_datetime(group["date"]), group["pool_elevation_end_ft"],
                label=label, color=colors[label], linewidth=1.45)
    ax.axhline(1300, color="#666", linestyle=":", linewidth=1)
    ax.axhline(1370, color="#666", linestyle=":", linewidth=1)
    ax.set(title="Daily water elevation, 2016", ylabel="End-of-day elevation (ft NGVD 29)", xlabel="Date")
    ax.legend(frameon=False)
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b"))
    fig.tight_layout()
    for ext in ("png", "svg", "pdf"):
        path = CURRENT / f"daily_water_elevation.{ext}"
        fig.savefig(path, bbox_inches="tight", **({"dpi": 300} if ext == "png" else {}))
        if ext == "svg":
            path.write_bytes(("\n".join(line.rstrip() for line in path.read_text(encoding="utf-8").splitlines()) + "\n").encode("utf-8"))
        figures.append(path)
    plt.close(fig)

    fig, axes = plt.subplots(3, 1, figsize=(10.5, 8), sharex=True, sharey=True)
    ymax = float(combined["controlled_release_cms"].max()) * 1.04
    for ax, (label, group) in zip(axes, combined.groupby("method_label", sort=False), strict=True):
        ax.bar(pd.to_datetime(group["date"]), group["controlled_release_cms"],
               width=1, color=colors[label], linewidth=0)
        ax.set(ylabel="m³/s", ylim=(0, ymax))
        ax.text(0.01, 0.88, label, transform=ax.transAxes, fontweight="bold", va="top")
    axes[0].set_title("Daily controlled release, 2016")
    axes[-1].set_xlabel("Date")
    axes[-1].xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    axes[-1].xaxis.set_major_formatter(mdates.DateFormatter("%b"))
    fig.tight_layout()
    for ext in ("png", "svg", "pdf"):
        path = CURRENT / f"controlled_release_daily.{ext}"
        fig.savefig(path, bbox_inches="tight", **({"dpi": 300} if ext == "png" else {}))
        if ext == "svg":
            path.write_bytes(("\n".join(line.rstrip() for line in path.read_text(encoding="utf-8").splitlines()) + "\n").encode("utf-8"))
        figures.append(path)
    plt.close(fig)

    manifest = {
        "schema_version": "fe-walter-current-tutorial.v1",
        "purpose": "Saved-data teaching comparison; no new provider request, hydrology run, or reservoir simulation.",
        "methods": list(LABELS.values()),
        "period": {"start": dates[0], "end": dates[-1], "days_per_method": 366},
        "units": {"inflow_cms": "m3/s", "controlled_release_cms": "m3/s",
                  "spill_cms": "m3/s", "pool_elevation_end_ft": "ft N.G.V.D.",
                  "storage_end_m3": "m3"},
        "validation": {
            "date_policy": "Exact ordered dates; no interpolation.",
            "inflow_policy": "Absolute tolerance 1e-10 m3/s for CSV serialization.",
            "initial_state_policy": "LLM storage_start_m3 and Rule-based first-step mass-balance reconstruction.",
            "expected_initial_storage_m3": initial, "methods": checks,
        },
        "sources": {
            "rule_rows": {"path": "../2016/daily.csv", "sha256": _sha(rule_path)},
            "llm_framework_rows": {"path": "../gemma4_2016_comparison/daily.csv", "sha256": _sha(llm_path)},
            "initial_state": {"path": "../2016/summary.json", "sha256": _sha(summary_path)},
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
methods: **Rule-based**, **LLM with available information**, and **LLM with
retrieved knowledge**. All three use the same saved inflow and physical state.

This notebook reads committed files only. It makes no model request and runs no
hydrology or reservoir simulation.

![Weather-to-operation workflow](../docs/figures/fe-walter-weather-workflow.svg)

[Maintained walkthrough](fe_walter.md) · [Current results](../examples/fe_walter/coupled/README.md#current-saved-2016-results)'''),
        md("## Setup"), code(SETUP),
        md('''## 1. Start from the experiment file

The entry names the physical case, dates, output, agent file, hydrology file,
auditors, and extensions. The LLM entries change the agent and add a model
profile while retaining the same physical case and hydrology.'''),
        code('''coupled = ROOT / "examples/fe_walter/coupled"
current_config = coupled / "current"
for title, name in (("Rule-based entry", "experiment.yaml"),
                    ("LLM with available information entry", "llm_available.yaml"),
                    ("LLM with retrieved knowledge entry", "llm_knowledge.yaml")):
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
                    ("LLM with available information agent", "agents.llm_available.yaml"),
                    ("LLM with retrieved knowledge agent", "agents.llm_knowledge.yaml")):
    display(ReadableText(title, (coupled / name).read_text(encoding="utf-8")))
display(ReadableText("Model settings and provenance", (current_config / "models.yaml").read_text(encoding="utf-8")))'''),
        md('''## 4. Inspect actual prompt and retrieved context

The saved pairs contain the exact request messages and replies. The parser
converts cfs to m³/s, then common physics enforces water availability and release
bounds. These records are examples from the saved run.'''),
        code('''saved = coupled / "outputs/gemma4_2016_comparison"
labels = {"llm_available": "LLM with available information", "llm_knowledge": "LLM with retrieved knowledge"}
for method, label in labels.items():
    pair = json.loads((saved / f"{method}_pair.json").read_text(encoding="utf-8"))
    record = pair["engines"]["framework"]
    display(ReadableText(f"{label}: saved request messages",
                         json.dumps(record["provider_request"]["messages"], indent=2, ensure_ascii=False)))
    display(ReadableText(f"{label}: saved reply", record["raw_provider_reply"]["message"]["content"]))
    display(pd.DataFrame([{"method": label, "saved date": pair["date"],
                           "controlled release (m³/s)": record["physics"]["controlled_release_cms"],
                           "end elevation (ft)": record["physics"]["pool_elevation_end_ft"]}]))'''),
        md('''## 5. Compare the three current teaching trajectories

The builder combines Rule-based rows from `outputs/2016/daily.csv` with the two
framework LLM rows from `outputs/gemma4_2016_comparison/daily.csv`. It verifies
366 unique ordered dates per method, common inflow, shared initial state, and
units. It performs no interpolation. The first figure reports end-of-day pool
elevation in feet NGVD 29. The second reports daily controlled release in m³/s;
spill is excluded.'''),
        code('''current = coupled / "outputs/current_tutorial"
daily = pd.read_csv(current / "daily.csv")
provenance = json.loads((current / "provenance.json").read_text(encoding="utf-8"))
display(daily.groupby("method_label", sort=False).agg(rows=("date", "size"),
    unique_dates=("date", "nunique"), maximum_release_cms=("controlled_release_cms", "max")))
display(pd.DataFrame(provenance["validation"]["methods"]).T)'''),
        code('''import matplotlib.dates as mdates
colors = {"Rule-based": "#3b6ea8", "LLM with available information": "#d97932",
          "LLM with retrieved knowledge": "#2f8f68"}
fig, ax = plt.subplots(figsize=(10.5, 4.8))
for label, group in daily.groupby("method_label", sort=False):
    ax.plot(pd.to_datetime(group["date"]), group["pool_elevation_end_ft"],
            label=label, color=colors[label], linewidth=1.45)
ax.axhline(1300, color="#666", linestyle=":", linewidth=1)
ax.axhline(1370, color="#666", linestyle=":", linewidth=1)
ax.set(title="Daily water elevation, 2016", ylabel="End-of-day elevation (ft NGVD 29)", xlabel="Date")
ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2)); ax.xaxis.set_major_formatter(mdates.DateFormatter("%b"))
ax.legend(frameon=False); fig.tight_layout(); display(fig)'''),
        code('''fig, axes = plt.subplots(3, 1, figsize=(10.5, 8), sharex=True, sharey=True)
ymax = float(daily["controlled_release_cms"].max()) * 1.04
for ax, (label, group) in zip(axes, daily.groupby("method_label", sort=False), strict=True):
    ax.bar(pd.to_datetime(group["date"]), group["controlled_release_cms"],
           width=1, color=colors[label], linewidth=0)
    ax.set(ylabel="m³/s", ylim=(0, ymax)); ax.text(0.01, 0.88, label, transform=ax.transAxes, fontweight="bold", va="top")
axes[0].set_title("Daily controlled release, 2016"); axes[-1].set_xlabel("Date")
axes[-1].xaxis.set_major_locator(mdates.MonthLocator(interval=2)); axes[-1].xaxis.set_major_formatter(mdates.DateFormatter("%b"))
fig.tight_layout(); display(fig)'''),
        md('''## 6. Run a new experiment deliberately

These commands are documentation and are not executed by this notebook. Copy
the chosen entry, set a new `run_id` and output, then check and prepare before
allowing network use.

```powershell
Copy-Item examples/fe_walter/coupled/current/llm_available.yaml examples/fe_walter/coupled/current/my-run.yaml
# Edit my-run.yaml: set a new run_id and output.
reservoir-experiment check examples/fe_walter/coupled/current/my-run.yaml
reservoir-experiment prepare examples/fe_walter/coupled/current/my-run.yaml
reservoir-experiment run examples/fe_walter/coupled/current/my-run.yaml --allow-network
reservoir-experiment verify <new-output-path>/operation
```

Use `experiment.yaml` for Rule-based operation or copy `llm_knowledge.yaml` for
LLM with retrieved knowledge. [Technical engine evidence and historical audits](../examples/fe_walter/engine_comparison.md)
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
