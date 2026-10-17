"""Build and validate the two saved-evidence HydroOpsLM tutorials.

The executable cells only read accepted repository snapshots. Execution blocks
socket and urllib access, never calls a provider, and records rich HTML/PNG MIME
outputs without requiring a Jupyter kernel.
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
ASSETS = TUTORIALS / "assets"
NOTEBOOKS = ("main.ipynb", "advanced.ipynb")
OLD_NOTEBOOKS = tuple(f"{index:02d}_{name}.ipynb" for index, name in enumerate((
    "overview", "input_and_map", "yaml", "benchmark", "zero_shot", "dkp",
    "audit_trace", "multi_and_custom", "ollama_workflow",
)))


SETUP = '''from pathlib import Path
import html, json, re, sys
ROOT = next(p for p in [Path.cwd(), *Path.cwd().parents] if (p / "src/hydrocnhs").is_dir())
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))
import pandas as pd
import matplotlib.pyplot as plt
from llm_reservoir_agent.workflow import load_settings
from llm_reservoir_agent.verification import verify_run
from tutorials.inspect_decision_flow import load_decision_flow

class ReadableText:
    """Render preserved text as a readable notebook block."""
    def __init__(self, title, text):
        self.title, self.text = title, text
    def _repr_markdown_(self):
        fence = "`" * max(4, 1 + max((len(run) for run in re.findall(r"`+", self.text)), default=0))
        return f"#### {self.title}\\n\\n{fence}text\\n{self.text}\\n{fence}"
    def _repr_html_(self):
        return f'<h4>{html.escape(self.title)}</h4><pre class="prompt-text">{html.escape(self.text)}</pre>'

def jsonl(path):
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines()]

pd.set_option("display.max_colwidth", 120)
plt.rcParams.update({"figure.figsize": (9, 4.8), "axes.grid": True, "figure.dpi": 120})
'''


def md(text: str) -> dict:
    return {
        "cell_type": "markdown",
        "id": "m-placeholder",
        "metadata": {},
        "source": text.strip().splitlines(True),
    }


def code(source: str) -> dict:
    return {
        "cell_type": "code",
        "id": "c-placeholder",
        "metadata": {},
        "source": source.strip().splitlines(True),
        "execution_count": None,
        "outputs": [],
    }


def main_cells() -> list[dict]:
    return [
        md('''# Main tutorial: F.E. Walter weather to daily operation

Follow the current 2016 example: **Rule-based**, **LLM with available
information**, and **LLM with retrieved knowledge**. All methods share the
accepted hydrology, physical initial state and routing. The model is selected
inside `current/models.yaml`; the experiment filename identifies the method.

This notebook reads committed annual results and recorded provider messages.
It makes no model request and runs no hydrology or reservoir simulation.

![HydroOpsLM coupling concept](../docs/figures/hydrocnhs-coupling-framework-en.png)

[Configuration walkthrough](fe_walter.md) ·
[Current annual comparison](../examples/fe_walter/coupled/README.md#verified-2016-results)'''),
        md('''## Setup

The builder blocks socket and urllib access. Tables and plots below are
recreated from saved files, including the independent Anik engine comparison.'''),
        code(SETUP),
        md('''## 1. Read the shared physical case and accepted inflow

The native weather model covers 1989–2025 and supplies the selected 366 days of
2016. Initial storage **2,457,848.279729185 m³ (1,992.61 acre-ft)** is an
assumption. Reservoir losses are zero; downstream `UH=[1.0]` is identity routing.

![F.E. Walter catchment](../docs/figures/fe-walter-catchment.png)'''),
        code('''coupled = ROOT / "examples/fe_walter/coupled"
annual = coupled / "outputs/gemma4_2016_comparison"
summary = json.loads((annual / "summary.json").read_text(encoding="utf-8"))
daily = pd.read_csv(annual / "daily.csv")
case = json.loads((coupled / "reservoirs.json").read_text(encoding="utf-8"))
physical = case["network"]["reservoirs"]["FEWalter"]["physical"]
labels = {"rule": "Rule-based", "llm_available": "LLM with available information",
          "llm_knowledge": "LLM with retrieved knowledge"}
display(pd.DataFrame([{"field": key, "value": physical[key]}
                      for key in ("initial_storage_m3", "capacity_m3", "minimum_release_cms",
                                  "maximum_release_cms", "dt_seconds")]))
inflow = daily.loc[(daily["engine"] == "framework") & (daily["method"] == "llm_available"),
                   ["date", "inflow_cms"]]
display(inflow.head().rename(columns={"inflow_cms": "prepared inflow (m³/s)"}))
display(pd.DataFrame([summary["period"]]))'''),
        md('''## 2. Choose an experiment and check its settings

Start with `current/experiment.yaml` for Rule-based operation. The LLM entries
select the same case agent and `current/models.yaml`. A local check validates
references and previews placeholder observations; it does not simulate inflow
or contact the provider. The configured model is `gemma4:12b`, temperature 0.7,
2048 output tokens, context 16384, thinking off and a 120-second timeout.
Each daily decision allows at most two attempts, with a two-second retry delay.
The LLM entries have no total call cap (`max_calls: null`).'''),
        code('''from llm_reservoir_agent.coupled import load_coupled_settings
import yaml
configs = {"Rule-based": "experiment.yaml",
           "LLM with available information": "llm_available.yaml",
           "LLM with retrieved knowledge": "llm_knowledge.yaml"}
plans = []
for method, name in configs.items():
    path = coupled / "current" / name
    report = load_coupled_settings(path).report
    plans.append({"method": method, "days": report["days"],
                  "planned daily model decisions": report["planned_llm_calls"],
                  "max calls": report["max_calls"], "configuration": str(path.relative_to(ROOT))})
display(pd.DataFrame(plans))
display(ReadableText("Selected model profile: current/models.yaml",
                     (coupled / "current/models.yaml").read_text(encoding="utf-8")))'''),
        md('''## 3. Inspect actual prompts, reply and implemented release

The saved pairs contain complete provider requests and replies from the current
annual comparison. Both snapshots are from 2 January 2016. The engines differ
in the available-information pair and agree in the retrieved-knowledge pair.
The available-information method receives
daily state and history; the retrieved-knowledge method also receives selected
operating document sections. The approved seasonal targets and response fields
remain visible in the actual messages.

The parser converts cfs to m³/s; common physics applies water availability,
release bounds and spill. The implemented outcome updates the next day's state.
These are preserved execution records, not new provider calls.'''),
        code('''pairs = {}
for slug in ("llm_available", "llm_knowledge"):
    pair = json.loads((annual / f"{slug}_pair.json").read_text(encoding="utf-8"))
    pairs[slug] = pair
    record = pair["engines"]["framework"]
    request = record["provider_request"]
    display(ReadableText(f"{labels[slug]}: saved date {pair['date']}",
                         json.dumps({"model": request["model"], "options": request["options"],
                                     "think": request["think"]}, indent=2)))
    for message in request["messages"]:
        display(ReadableText(f"{labels[slug]}: complete {message['role']} message", message["content"]))
    display(ReadableText(f"{labels[slug]}: complete response schema", json.dumps(request["format"], indent=2)))
    display(ReadableText(f"{labels[slug]}: actual saved reply",
                         record["raw_provider_reply"]["message"]["content"]))
    display(pd.DataFrame([record["physics"]]))'''),
        md('''## 4. Compare saved annual trajectories

The two LLM trajectories below are the HydroOpsLLM arms of the current Gemma 4
comparison. The Rule-based trajectory is the preserved annual baseline, with
the same accepted inflow and physical state; it requires zero model calls.
Older LLM trajectories in that baseline export are excluded. No saved result
is overwritten or relabeled as a new execution.'''),
        code('''baseline = pd.read_csv(coupled / "outputs/2016/daily.csv")
rule = baseline.loc[baseline["method"] == "rule"].copy()
framework = daily.loc[daily["engine"] == "framework"].copy()
comparison = pd.concat([rule, framework], ignore_index=True)
comparison["method label"] = comparison["method"].map(labels)
for slug, group in comparison.groupby("method"):
    assert len(group) == 366 and group["date"].nunique() == 366
    assert group["date"].tolist() == inflow["date"].tolist()
    assert (abs(group["inflow_cms"].to_numpy() - inflow["inflow_cms"].to_numpy()) < 1e-10).all()
display(comparison[["method label", "date", "inflow_cms", "controlled_release_cms",
                    "spill_cms", "pool_elevation_end_ft", "storage_end_m3"]].groupby("method label", sort=False).head(3))'''),
        code('''fig, axes = plt.subplots(2, 1, figsize=(11, 7), sharex=True)
for method, group in comparison.groupby("method label", sort=False):
    dates = pd.to_datetime(group["date"])
    axes[0].plot(dates, group["pool_elevation_end_ft"], label=method)
    axes[1].plot(dates, group["controlled_release_cms"], label=method)
axes[0].axhline(1300, color="gray", linestyle=":")
axes[0].axhline(1370, color="gray", linestyle=":")
axes[0].set(ylabel="End-of-day pool (ft NGVD29)", title="Saved 2016 F.E. Walter operation")
axes[1].set(ylabel="Controlled release (m³/s)", xlabel="2016 date")
axes[0].legend(loc="upper left", fontsize=8)
fig.tight_layout()
export = ROOT / "tutorials/assets/fe_walter_three_method.png"
export.parent.mkdir(parents=True, exist_ok=True)
fig.savefig(export, dpi=160, bbox_inches="tight", metadata={"Software": "HydroOpsLM tutorial"})
display(fig)'''),
        md('''## 5. Read completion, physics and operating outcomes separately

The saved comparison records 366 completed days and 366 actual HTTP attempts
for each LLM arm, with no retry or fallback. The table reports the saved
seasonal end-pool checks for each engine. Winter means November 1–March 14,
within 1297–1303 ft. Completion and water balance do not establish acceptable
operation: read the November 1 and seasonal results alongside the trajectories.

Independent replies at temperature 0.7 can produce different trajectories.
The same-reply replay in the saved summary isolates engineering equivalence.'''),
        code('''rows = []
for name, arm in summary["arms"].items():
    engine, slug = name.split("-", 1)
    compliance = arm["seasonal_end_pool_compliance"]
    rows.append({"method": labels[slug], "engine": engine,
                 "completed days": arm["completed_days"], "actual HTTP attempts": arm["http_attempts"],
                 "winter compliant days": compliance["winter"]["compliant_days"],
                 "winter days": compliance["winter"]["days"],
                 "November 1 end pool (ft)": compliance["november_1_end_pool_ft"],
                 "saved max balance residual (m³)": arm["max_mass_balance_residual_m3"]})
display(pd.DataFrame(rows))
current_balance = (daily["storage_end_m3"] - daily["storage_start_m3"]
                   - (daily["inflow_cms"] - daily["controlled_release_cms"] - daily["spill_cms"]) * 86400)
display(pd.DataFrame([{"check": "current arithmetic recheck of saved CSV water balance",
                       "max absolute residual (m³)": current_balance.abs().max(),
                       "saved rows checked": len(daily)}]))
display(pd.DataFrame([{"method": labels[slug],
                      "exact native requests replayed": values["same_real_reply_replay"]["native_payloads_exact"],
                      "exact framework requests replayed": values["same_real_reply_replay"]["framework_payloads_exact"]}
                     for slug, values in summary["comparisons"].items()]))'''),
        md('''## Optional new execution

The notebook never executes the commands below. Keep an experiment copy beside
its source, choose a new `run_id` and `output`, and review the model profile.
`check` is offline; `prepare` computes hydrology, unless verified preparation is
explicitly reused. Only the LLM `run` requests decisions with `--allow-network`.

```powershell
Copy-Item examples/fe_walter/coupled/current/llm_available.yaml examples/fe_walter/coupled/current/my-run.yaml
# Edit my-run.yaml: choose a new run_id and output.
reservoir-experiment check examples/fe_walter/coupled/current/my-run.yaml
reservoir-experiment prepare examples/fe_walter/coupled/current/my-run.yaml
reservoir-experiment run examples/fe_walter/coupled/current/my-run.yaml --allow-network
reservoir-experiment verify <new-output-path>/operation
```

For LLM with retrieved knowledge, copy `current/llm_knowledge.yaml` instead.

[Full configuration and audit/trace walkthrough](fe_walter.md) ·
[Saved comparison summary](../examples/fe_walter/coupled/outputs/gemma4_2016_comparison/summary.json) ·
[Recorded available-information pair](../examples/fe_walter/coupled/outputs/gemma4_2016_comparison/llm_available_pair.json) ·
[Recorded retrieved-knowledge pair](../examples/fe_walter/coupled/outputs/gemma4_2016_comparison/llm_knowledge_pair.json)'''),
    ]


def advanced_cells() -> list[dict]:
    return [
        md('''# Advanced tutorial: topology, passive outlets, and your own data

This notebook reads the accepted 31-day, three-reservoir snapshot. It does not
run a new network simulation. The example demonstrates parallel tributary
topology, isolated reservoir state, a physical passive outlet, and the settings
that must change for another catchment.

![Accepted three-reservoir month](../examples/fe_walter/reference_outputs/multi_reservoir_month/figures/overview.png)'''),
        md('''## Setup

All tables and plots come from `examples/fe_walter/reference_outputs/multi_reservoir_month/baseline`
and its accepted causality comparison.'''),
        code(SETUP),
        md('''## 1. Read the saved topology

FE Walter and Beltzville contribute to the Lehigh branch; Prompton contributes
to the Lackawaxen branch. These are parallel tributaries, not a three-dam
cascade. The managed outlet is the sum of these contributions, not full river
discharge.'''),
        code('''month = ROOT / "examples/fe_walter/reference_outputs/multi_reservoir_month"
baseline = month / "baseline"
experiment = json.loads((baseline / "experiment.json").read_text(encoding="utf-8"))
network = experiment["network"]
reservoir_rows = []
for name, settings in network["reservoirs"].items():
    physical = settings["physical"]
    reservoir_rows.append({
        "reservoir": name,
        "mode": settings["operation_mode"],
        "initial storage (m³)": physical["initial_storage_m3"],
        "minimum release (m³/s)": physical["minimum_release_cms"],
        "maximum release (m³/s)": physical["maximum_release_cms"],
    })
connections = pd.DataFrame([{
    "source": edge["source"], "target": edge["target"],
    "unit hydrograph": str(edge["unit_hydrograph"]),
} for edge in network["connections"]])
display(pd.DataFrame(reservoir_rows))
display(connections)'''),
        md('''## 2. Passive outlet and state isolation

Prompton has no LLM agent. Its saved discharge is computed from a provisional
storage–discharge curve and daily water balance. The two pulse experiments show
that changing one controlled reservoir changes its own subsequent storage and
downstream contribution while sibling natural inflow and physical transitions
remain byte-for-byte equivalent.'''),
        code('''summary = json.loads((baseline / "summary.json").read_text(encoding="utf-8"))["summary"]
comparison = json.loads((month / "comparison.json").read_text(encoding="utf-8"))
passive = network["reservoirs"]["Prompton"]["passive_outlet"]
status = pd.DataFrame([{
    "days": summary["days"],
    "reservoirs": summary["reservoir_count"],
    "reservoir-days": sum(summary["completed_reservoir_days"].values()),
    "model calls": summary["observed_network_calls"],
    "audit counts": str(summary["audit_counts"]),
    "operating strategy accepted": summary["operating_strategy_accepted"],
    "passive rating validated": passive["provenance"]["operationally_validated"],
}])
pulses = pd.DataFrame([{
    "scenario": name,
    "reservoir": values["reservoir"],
    "date": values["date"],
    "release increment (m³/s)": values["requested_increment_cms"],
    "final own-storage decrease (m³)": values["final_storage_decrease_m3"],
    "siblings unchanged": values["sibling_natural_inflow_and_physical_transitions_equal"],
} for name, values in comparison["scenarios"].items()])
display(status)
display(pulses)'''),
        code('''trajectory = pd.read_csv(baseline / "reservoir_trajectory.csv")
trajectory["date"] = trajectory["date"].str[:10]
display(trajectory[["date", "reservoir_id", "inflow_cms", "total_outflow_cms", "storage_end_m3"]].head(9).rename(columns={
    "inflow_cms": "inflow (m³/s)", "total_outflow_cms": "outflow (m³/s)",
    "storage_end_m3": "end storage (m³)"}))
fig, ax = plt.subplots()
for reservoir, group in trajectory.groupby("reservoir_id"):
    ax.plot(group["date"], group["storage_end_m3"] / 1e6, label=reservoir)
ax.set(title="Saved January 2016 reservoir storage", ylabel="Storage (million m³)", xlabel="Date")
ax.legend()
dates = trajectory["date"].drop_duplicates().tolist()
ax.set_xticks([dates[index] for index in (0, 7, 14, 21, 30)])
ax.tick_params(axis="x", rotation=45)
export = ROOT / "tutorials/assets/three_reservoir_month.png"
export.parent.mkdir(parents=True, exist_ok=True)
fig.savefig(export, dpi=160, bbox_inches="tight", metadata={"Software": "HydroOpsLM tutorial"})
display(fig)'''),
        md('''## 3. Routing and audit limits

The accepted snapshot independently verifies native routing and mass balance,
but `UH=[1]` remains uncalibrated. All 93 strategy audits are `UNKNOWN` because
this fixture has no operating-policy auditor. File and physics acceptance do
not establish strategy quality or live readiness.'''),
        code('''checks = pd.DataFrame([
    ("max system residual", summary["max_system_balance_residual_m3"], "m³"),
    ("final channel storage", summary["final_channel_storage_m3"], "m³"),
    ("natural inputs changed", comparison["natural_hydrologic_inputs_changed"], "boolean"),
    ("routing calibrated", comparison["routing_calibrated"], "boolean"),
    ("outlet is full river", comparison["outlet_represents_full_river"], "boolean"),
    ("delayed reservoir transitions unchanged", comparison["delay"]["reservoir_transitions_unchanged"], "boolean"),
    ("delayed final in-transit storage", comparison["delay"]["final_in_transit_storage_m3"], "m³"),
], columns=["check", "value", "unit"])
display(checks)'''),
        md('''## 4. Bring your own catchment

Use the generic YAML/module manual for syntax and the native HydroCNHS workflow
for forcing, routing, calibration, and validation. Do not copy FE Walter facts,
capacities, prompts, knowledge, targets, or auditors into another reservoir.'''),
        code('''own_data = pd.DataFrame([
    ("Hydrology", "Own forcing, basin geometry, parameters, C&V period", "Native HydroCNHS setup"),
    ("Network", "Reservoir nodes, junctions, local inflow applied once, calibrated UH", "Case JSON"),
    ("Physics", "Storage limits, initial state, outlets, losses, units", "Reservoir physical profile"),
    ("Decision", "Own prompt, knowledge, schema, model budget", "Experiment YAML / modules"),
    ("Audit", "Versioned reservoir-specific operating rules", "Auditor configuration"),
    ("Readiness", "Offline fixtures, conservation, routing, provenance, explicit live approval", "Verification evidence"),
], columns=["layer", "replace with site-specific evidence", "where to configure"])
display(own_data)'''),
        md('''[Generic YAML settings](../docs/USER_GUIDE.md) ·
[Module interfaces](../docs/LLM_MODULES.md) ·
[Native HydroCNHS hydrology and C&V](../docs/HYDROLOGY_SETUP.md) ·
[Accepted three-reservoir evidence](../examples/fe_walter/reference_outputs/multi_reservoir_month/README.md)'''),
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
        image = io.BytesIO()
        value.savefig(image, format="png", dpi=120, bbox_inches="tight",
                      metadata={"Software": "HydroOpsLM tutorial"})
        return {
            "image/png": base64.b64encode(image.getvalue()).decode("ascii"),
            "text/plain": repr(value),
        }
    return {"text/plain": str(value)}


def _execute(cells: list[dict], notebook_name: str) -> None:
    namespace = {"__name__": "__main__"}
    execution_count = 0
    for cell in cells:
        if cell["cell_type"] != "code":
            continue
        execution_count += 1
        displays = []

        def display(*values):
            displays.extend(values)

        namespace["display"] = display
        stream = io.StringIO()
        source = "".join(cell["source"])
        with (
            contextlib.redirect_stdout(stream),
            patch("socket.socket.connect", side_effect=AssertionError("tutorial network forbidden")),
            patch("urllib.request.build_opener", side_effect=AssertionError("tutorial HTTP forbidden")),
            patch("urllib.request.urlopen", side_effect=AssertionError("tutorial HTTP forbidden")),
        ):
            exec(compile(source, notebook_name, "exec"), namespace)
        cell["execution_count"] = execution_count
        outputs = []
        if stream.getvalue():
            outputs.append({
                "output_type": "stream", "name": "stdout",
                "text": stream.getvalue().splitlines(True),
            })
        outputs.extend({
            "output_type": "display_data", "metadata": {}, "data": _rich_data(value),
        } for value in displays)
        cell["outputs"] = outputs


def _notebook(cells: list[dict], name: str, execute: bool) -> dict:
    for index, cell in enumerate(cells):
        cell["id"] = ("m" if cell["cell_type"] == "markdown" else "c") + str(index)
    if execute:
        _execute(cells, name)
    return {
        "nbformat": 4,
        "nbformat_minor": 5,
        "metadata": {
            "kernelspec": {"name": "python3", "language": "python", "display_name": "Python 3"},
            "language_info": {"name": "python", "version": platform.python_version()},
            "tutorial_mode": "saved-evidence-only",
            "execution_method": "ordered pure-Python cells with socket/urllib blocked",
        },
        "cells": cells,
    }


def build(*, execute: bool) -> list[dict]:
    os.chdir(ROOT)
    ASSETS.mkdir(parents=True, exist_ok=True)
    specs = {"main.ipynb": main_cells(), "advanced.ipynb": advanced_cells()}
    receipts = []
    for name, cells in specs.items():
        notebook = _notebook(cells, name, execute)
        path = TUTORIALS / name
        path.write_text(json.dumps(notebook, indent=1, ensure_ascii=False) + "\n",
                        encoding="utf-8", newline="\n")
        receipts.append({
            "path": str(path.relative_to(ROOT)),
            "code_cells": sum(cell["cell_type"] == "code" for cell in cells),
            "executed": execute,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        })
    return receipts


def check() -> list[dict]:
    forbidden = ("run_settings(", "subprocess.", "urlopen(", "requests.", "ollama.chat")
    reports = []
    for old in OLD_NOTEBOOKS:
        if (TUTORIALS / old).exists():
            raise AssertionError(f"obsolete notebook remains: {old}")
    for name in NOTEBOOKS:
        path = TUTORIALS / name
        notebook = json.loads(path.read_text(encoding="utf-8"))
        if notebook.get("nbformat") != 4 or notebook.get("metadata", {}).get("tutorial_mode") != "saved-evidence-only":
            raise AssertionError(f"invalid notebook metadata: {name}")
        code_cells = [cell for cell in notebook["cells"] if cell["cell_type"] == "code"]
        source = "\n".join("".join(cell["source"]) for cell in code_cells)
        hits = [token for token in forbidden if token in source]
        if hits:
            raise AssertionError(f"forbidden executable path in {name}: {hits}")
        if any(cell.get("execution_count") is None for cell in code_cells):
            raise AssertionError(f"unexecuted code cell in {name}")
        mime_types = {
            mime for cell in code_cells for output in cell.get("outputs", [])
            for mime in output.get("data", {})
        }
        if not {"text/html", "image/png"} <= mime_types:
            raise AssertionError(f"missing rich table/figure output in {name}: {sorted(mime_types)}")
        reports.append({
            "path": str(path.relative_to(ROOT)),
            "cells": len(notebook["cells"]),
            "code_cells": len(code_cells),
            "mime_types": sorted(mime_types),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        })
    for asset in (ASSETS / "fe_walter_three_method.png", ASSETS / "three_reservoir_month.png"):
        if not asset.is_file() or asset.stat().st_size == 0:
            raise AssertionError(f"missing standalone plot: {asset.relative_to(ROOT)}")
    return reports


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true", help="build both notebooks and execute saved-data cells")
    parser.add_argument("--check", action="store_true", help="validate the two executed notebooks without rewriting")
    args = parser.parse_args()
    if not args.execute and not args.check:
        parser.error("choose --execute or --check")
    result = []
    if args.execute:
        result.extend(build(execute=True))
    if args.check:
        result.extend(check())
    print(json.dumps(result, indent=2, ensure_ascii=False))
