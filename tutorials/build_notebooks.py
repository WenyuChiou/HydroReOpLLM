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
        md('''# Main tutorial: one FE Walter decision, end to end

This walkthrough follows one bounded three-day case from input and YAML through
the decision method, current checks, saved execution, verification, and bound
audit/trace evidence. It compares a deterministic Hanasaki-based rule with two
already-completed local Ollama runs. No model is called while this notebook runs.

![HydroOpsLM coupling concept](../docs/figures/hydrocnhs-coupling-framework-en.png)

The decision path is **info → system/user prompt → saved rule or model output →
current action-contract recheck → implemented release → next info**. Historical
events remain historical; a current recheck never becomes a claimed past event.'''),
        md('''## Setup

The notebook reads repository snapshots only. The builder blocks network access
and records displayed tables and figures as rich notebook outputs.'''),
        code(SETUP),
        md('''## 1. Input: the same inflow, physical state, losses, and routing

The inflow is simulated, already aggregated and routed to the reservoir node.
Initial storage **2,457,848.279729185 m³ (1,992.61 acre-ft)** is an integration
assumption. Losses are zero and `UH=[1.0]` is identity routing, not a calibrated
downstream reach.

![FE Walter study map](../docs/figures/fe-walter-study-map.png)'''),
        code('''inflow = pd.read_csv(ROOT / "cases/fe_walter_reference/inflows.csv")
inflow = inflow.loc[inflow["node"] == "FEW_INFLOW", ["date", "local_inflow_cms"]]
inflow = inflow.rename(columns={"local_inflow_cms": "inflow (m³/s)"})
case = json.loads((ROOT / "cases/fe_walter_ollama_demo/case.json").read_text(encoding="utf-8"))
physical = case["network"]["reservoirs"]["FEWalter"]["physical"]
assumptions = pd.DataFrame([
    ("initial storage", physical["initial_storage_m3"], "m³"),
    ("minimum release", physical["minimum_release_cms"], "m³/s"),
    ("maximum release", physical["maximum_release_cms"], "m³/s"),
    ("evaporation / seepage", 0.0, "m³/day"),
    ("downstream unit hydrograph", str(case["network"]["connections"][0]["unit_hydrograph"]), "dimensionless"),
], columns=["item", "value", "unit"])
display(inflow)
display(assumptions)'''),
        md('''## 2. YAML and local check

The rule snapshot uses the same Ollama-case file as the LLM snapshots and frozen
1996–2015 Hanasaki statistics. `load_settings` performs the same local planning
check as the CLI `check` command and makes no provider request.'''),
        code('''configs = {
    "Rule": "tutorials/config/fe_walter_tutorial_benchmark.yaml",
    "Zero-shot": "examples/fe_walter/zero_shot/experiment.ollama.yaml",
    "DKP": "examples/fe_walter/dkp/experiment.ollama.yaml",
}
plans = []
for method, relative in configs.items():
    report = load_settings(ROOT / relative).report
    plans.append({
        "method": method,
        "dates": f"{report['start_date']} to {report['end_date']}",
        "days": report["days"],
        "planned model calls": report["planned_llm_calls"],
        "max calls": report["max_calls"],
        "configuration": relative,
    })
display(pd.DataFrame(plans))'''),
        md('''## 3. Rule or prompt: inspect preserved decision evidence

The two LLM paths below read real saved Ollama evidence (`gemma3:4b`, temperature
0.7, three completed calls per method, no retries). The complete first-day
system and user prompts are displayed as readable text. DKP adds conditionally
retrieved knowledge; zero-shot does not. Raw records remain linked below.

[Zero-shot raw traces](../results/fe_walter_ollama_2016_01/zero_shot/raw/) ·
[DKP raw traces](../results/fe_walter_ollama_2016_01/dkp/raw/)'''),
        code('''saved = ROOT / "results/fe_walter_ollama_2016_01"
zero_flow = load_decision_flow(saved / "zero_shot", timestep=0)
dkp_flow = load_decision_flow(saved / "dkp", timestep=0)
info = zero_flow["info"]
display(pd.DataFrame([{
    "date": zero_flow["prompt_variables"]["date"],
    "inflow (m³/s)": info["inflow_cms"],
    "starting storage (m³)": info["state"]["storage_m3"],
    "method": "Zero-shot saved Ollama",
}]))
display(ReadableText("Complete saved system prompt", zero_flow["system_prompt"]))
display(ReadableText("Complete saved zero-shot user prompt", zero_flow["prompt"]))
display(ReadableText("Complete saved DKP system prompt", dkp_flow["system_prompt"]))
display(ReadableText("Complete saved DKP user prompt with retrieved knowledge", dkp_flow["prompt"]))'''),
        code('''rule_decisions = jsonl(ROOT / "results/fe_walter_tutorial_benchmark_2016_01/decisions.jsonl")
rule_output = pd.DataFrame([{
    "date": row["timestamp"],
    "rule output: requested release (m³/s)": row["action"]["release_cms"],
    "decision ID": row["decision_id"],
} for row in rule_decisions])
llm_outputs = pd.DataFrame([
    {"method": "Zero-shot", "saved native reply": zero_flow["saved_native_reply"],
     "normalized requested release (m³/s)": zero_flow["proposal"]["release_cms"]},
    {"method": "DKP", "saved native reply": dkp_flow["saved_native_reply"],
     "normalized requested release (m³/s)": dkp_flow["proposal"]["release_cms"]},
])
display(rule_output)
display(llm_outputs)'''),
        md('''## 4. Run and verify: default to saved snapshots

The default tutorial does **not** run a simulation or model. It verifies three
saved snapshots and reads their committed trajectories. The deterministic rule
snapshot has zero network calls. Both LLM snapshots retain their original audit
outcomes: zero-shot has **2 PASS / 1 FAIL**, DKP has **3 FAIL**, and
`operating_strategy_accepted` is `null` for all three methods.'''),
        code('''outputs = {
    "Rule": ROOT / "results/fe_walter_tutorial_benchmark_2016_01",
    "Zero-shot": saved / "zero_shot",
    "DKP": saved / "dkp",
}
verification_rows = []
for method, output in outputs.items():
    result = verify_run(output, require_offline=(method == "Rule"))
    verification_rows.append({
        "method": method,
        "verification": result["status"],
        "days": result["days"],
        "audit counts": str(result["audit_counts"]),
        "network calls": result["observed_network_calls"],
        "max system residual (m³)": result["max_system_balance_residual_m3"],
        "operating strategy accepted": result["operating_strategy_accepted"],
    })
display(pd.DataFrame(verification_rows))'''),
        code('''frames = []
for method, output in outputs.items():
    trajectory = pd.read_csv(output / "reservoir_trajectory.csv")
    audits = jsonl(output / "audit.jsonl")
    trajectory["date"] = trajectory["date"].str[:10]
    trajectory["method"] = method
    trajectory["audit"] = [row["status"] for row in audits]
    frames.append(trajectory[["method", "date", "inflow_cms", "target_release_cms",
                              "controlled_release_cms", "total_outflow_cms", "spill_cms", "storage_end_m3", "audit"]])
comparison = pd.concat(frames, ignore_index=True).rename(columns={
    "inflow_cms": "inflow (m³/s)",
    "target_release_cms": "requested release (m³/s)",
    "controlled_release_cms": "implemented release (m³/s)",
    "total_outflow_cms": "total outflow (m³/s)",
    "spill_cms": "spill (m³/s)",
    "storage_end_m3": "end storage (m³)",
})
display(comparison)'''),
        code('''fig, ax = plt.subplots()
for method, group in comparison.groupby("method", sort=False):
    ax.plot(group["date"], group["total outflow (m³/s)"], marker="o", label=method)
ax.plot(inflow["date"], inflow["inflow (m³/s)"], color="black", linestyle="--", label="Inflow")
ax.set(title="Same FE Walter case: implemented outflow", ylabel="Flow (m³/s)", xlabel="Date")
ax.legend(ncol=2)
fig.autofmt_xdate(rotation=20)
export = ROOT / "tutorials/assets/fe_walter_three_method.png"
export.parent.mkdir(parents=True, exist_ok=True)
fig.savefig(export, dpi=160, bbox_inches="tight", metadata={"Software": "HydroOpsLM tutorial"})
display(fig)'''),
        md('''## 5. Audit and trace: preserved verdicts versus current revalidation

`load_decision_flow` binds each decision to its raw provider record, saved audit,
implemented physics, and next observation. `current_recheck` parses the saved
action against today’s common action contract. It is explicitly a **current
recheck**, not evidence that a historical checker event existed.'''),
        code('''chain = pd.DataFrame([
    ("info", zero_flow["prompt_variables"]["date"], "historical saved observation"),
    ("provider completion", str(zero_flow["provider_evidence"]["completion"]), "historical saved provider evidence"),
    ("requested release", zero_flow["saved_requested_action"]["release_cms"], "historical saved action, m³/s"),
    ("action contract", zero_flow["current_recheck"]["action_contract"], "current revalidation only"),
    ("strategy audit", zero_flow["saved_audit"]["status"], "historical saved verdict"),
    ("implemented total outflow", zero_flow["saved_implemented_physics"]["total_outflow_cms"], "historical physics, m³/s"),
    ("next storage", zero_flow["next_info"]["state"]["storage_m3"], "next historical info, m³"),
], columns=["stage", "value", "evidence meaning"])
display(chain)
display(pd.DataFrame([zero_flow["trace_files"]]))'''),
        md('''## Optional explicit live rerun

With the named model already available locally, copy either YAML to a new file
in the same directory. Edit its `run_id` and `output` to new values;
keeping the copy beside the original preserves relative input paths.
The provided YAMLs are bounded to three calls and configure no retry.
These commands are documentation; the notebook builder never executes them.

```powershell
Copy-Item examples/fe_walter/zero_shot/experiment.ollama.yaml examples/fe_walter/zero_shot/my-run.yaml
# Edit my-run.yaml: use a new run_id and output before continuing.
python run_experiment.py check examples/fe_walter/zero_shot/my-run.yaml
python run_experiment.py run examples/fe_walter/zero_shot/my-run.yaml --allow-network
python run_experiment.py verify <new-output-path>
python tutorials/inspect_decision_flow.py <new-output-path>
```

For DKP, use `examples/fe_walter/dkp/experiment.ollama.yaml` as the source and
`examples/fe_walter/dkp/my-run.yaml` as the copy in the same sequence.

[Formal YAML/module manual](../docs/USER_GUIDE.md) ·
[Native HydroCNHS hydrology and C&V](../docs/HYDROLOGY_SETUP.md) ·
[Saved Ollama evidence](../results/fe_walter_ollama_2016_01/README.md)'''),
    ]


def advanced_cells() -> list[dict]:
    return [
        md('''# Advanced tutorial: topology, passive outlets, and your own data

This notebook reads the accepted 31-day, three-reservoir snapshot. It does not
run a new network simulation. The example demonstrates parallel tributary
topology, isolated reservoir state, a physical passive outlet, and the settings
that must change for another catchment.

![Accepted three-reservoir month](../results/three_reservoir_month_2016_01/figures/overview.png)'''),
        md('''## Setup

All tables and plots come from `results/three_reservoir_month_2016_01/baseline`
and its accepted causality comparison.'''),
        code(SETUP),
        md('''## 1. Read the saved topology

FE Walter and Beltzville contribute to the Lehigh branch; Prompton contributes
to the Lackawaxen branch. These are parallel tributaries, not a three-dam
cascade. The managed outlet is the sum of these contributions, not full river
discharge.'''),
        code('''month = ROOT / "results/three_reservoir_month_2016_01"
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
[Accepted three-reservoir evidence](../results/three_reservoir_month_2016_01/RESULTS.md)'''),
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
