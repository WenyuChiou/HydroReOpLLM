"""Cells for the read-only 2021–2025 F.E. Walter operation lesson."""
from __future__ import annotations

from collections.abc import Callable


def build_cells(*, md: Callable[[str], dict], code: Callable[[str], dict]) -> list[dict]:
    """Return cells that inspect prepared inputs and saved baseline evidence."""
    setup = code(r'''
from pathlib import Path
import html, json, re, sys

ROOT = next(p for p in [Path.cwd(), *Path.cwd().parents]
            if (p / "src/llm_reservoir_agent").is_dir())
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

import pandas as pd
from IPython.display import Image

class ReadableText:
    def __init__(self, title, text, expanded=True):
        self.title, self.text, self.expanded = title, text, expanded
    def _repr_markdown_(self):
        fence = "`" * max(4, 1 + max((len(run) for run in re.findall(r"`+", self.text)), default=0))
        return f"#### {self.title}\n\n{fence}text\n{self.text}\n{fence}"
    def _repr_html_(self):
        content = f'<pre class="config-source">{html.escape(self.text)}</pre>'
        if self.expanded:
            return f'<h4>{html.escape(self.title)}</h4>{content}'
        return f'<details><summary>{html.escape(self.title)} — complete text</summary>{content}</details>'

def show_file(relative_path, title=None, *, expanded=True):
    path = ROOT / relative_path
    display(ReadableText(title or path.name, path.read_text(encoding="utf-8"), expanded))

operation = ROOT / "examples/fe_walter/operation"
pd.set_option("display.max_colwidth", 120)
''')
    setup["metadata"]["tags"] = ["hide-input"]

    return [
        md('''# F.E. Walter: prepare a five-year operation comparison

## Goal

Follow the current 2021–2025 route from frozen hydrology inputs to one completed
Rule-based baseline and two prepared LLM methods. The notebook reads committed
files, checks the offline preparation, and displays saved figures. It does not
download data, recompute hydrology, advance reservoir state, or call a model.

The older [main notebook](main.ipynb) remains the historical 2016 configuration
walkthrough. Its saved LLM trajectories predate the daily seasonal context and
are not five-year results.

Read this lesson in order:

1. [Open the prepared experiment](#1-open-the-prepared-experiment)
2. [Trace the shared physical case](#2-trace-the-shared-physical-case)
3. [Read the Rule-based comparator](#3-read-the-rule-based-comparator)
4. [Switch to either LLM method](#4-switch-to-either-llm-method)
5. [Run the offline preflight](#5-run-the-offline-preflight)
6. [Inspect saved baseline evidence](#6-inspect-saved-baseline-evidence)

## Setup

Complete [installation](../docs/GETTING_STARTED.md), open
`tutorials/operation.ipynb` from the repository clone, select that environment,
and run cells in order. All paths below resolve from the repository root.'''),
        setup,
        md('''## 1. Open the prepared experiment

Open [experiment.yaml](../examples/fe_walter/operation/experiment.yaml) in the
[case folder](../examples/fe_walter/operation/). The operation entry uses
`llm-reservoir-experiment.v2`, which loads the frozen
network and daily local-inflow CSV. The complete maintained YAML is shown below;
comments are part of the teaching source. The dates are inclusive, so 2021-01-01
through 2025-12-31 contains 1,826 operation decisions.'''),
        code('''show_file(
    "examples/fe_walter/operation/experiment.yaml",
    "Complete Rule-based five-year experiment YAML",
)'''),
        md('''| Field | Purpose | Required value for this lesson |
|---|---|---|
| `schema_version` | Select the prepared-operation settings contract. | `llm-reservoir-experiment.v2` |
| `case` | Load the shared reservoir, routed network, and frozen inflow source. | `case.json` |
| `start_date`, `end_date` | Bound the daily operation period. | 2021-01-01 through 2025-12-31 |
| `agents.file` | Select one decision method while retaining the same physical case. | `agents.rule.yaml` here |
| `extensions` | Register the case-specific seeded Hanasaki adapter. | `__init__.py` |'''),
        md('''## 2. Trace the shared physical case

All three methods begin at **4,287,715.370246947 m³** on 2021-01-01 and use the
same prepared local inflows. The coupled hydrology stage already simulated
1989–2025 upstream and lateral runoff and routed it to the operation boundaries.
The operation lesson therefore reads `inflows.csv`; it does not rerun that stage.

The channel queues start empty on 2021-01-01, so the first 21 days are excluded
from primary downstream scores. They remain in the daily files and figures.'''),
        code('''show_file("examples/fe_walter/operation/case.json", "Complete shared physical case")
show_file("examples/fe_walter/operation/provenance.json", "Complete input provenance", expanded=False)

case = json.loads((operation / "case.json").read_text(encoding="utf-8"))
provenance = json.loads((operation / "provenance.json").read_text(encoding="utf-8"))
inflows = pd.read_csv(operation / "inflows.csv", dtype={"date": str, "node": str})
physical = case["network"]["reservoirs"]["FEWalter"]["physical"]
display(pd.DataFrame([
    {"item": "Operation dates", "value": inflows["date"].nunique(), "unit": "unique dates"},
    {"item": "Local inflow boundaries", "value": inflows["node"].nunique(), "unit": "nodes"},
    {"item": "Initial storage", "value": physical["initial_storage_m3"], "unit": "m³"},
    {"item": "Capacity", "value": physical["capacity_m3"], "unit": "m³"},
    {"item": "Primary routing exclusion", "value": provenance["warmup"]["routing_primary_excluded_days"], "unit": "days"},
]))'''),
        md('''Read the complete [physical case](../examples/fe_walter/operation/case.json)
and [inflow CSV](../examples/fe_walter/operation/inflows.csv). In the JSON,
`network.reservoirs.FEWalter.physical` contains the storage and release settings.
The last two rows below identify the inflow connection and downstream reaches.

| Field | Meaning | Unit |
|---|---|---|
| `capacity_m3` | Maximum modeled total storage at the 1,450 ft flood pool. | m³ |
| `dead_storage_m3` | Protected lower computational bound; current field value remains uncertain. | m³ |
| `initial_storage_m3` | Shared storage at local midnight on 2021-01-01. | m³ |
| `minimum_release_cms`, `maximum_release_cms` | Physical bounds on controlled release. | m³/s |
| `dt_seconds` | Fixed duration of an operation step. | seconds |
| `network.reservoirs.FEWalter.inflow_node` | Node supplying reservoir inflow, `FEW_INFLOW`. | ID |
| `network.connections` | Directed reaches and their daily routing weights. | Weights sum to 1 |

The **135,532,852.34 m³** capacity corresponds approximately to the
1,450 ft flood-control pool in the saved conversion. The 49.34 m³ inactive/dead
storage floor has not been independently confirmed. Reservoir evaporation and
seepage are zero in this fixed comparison.

The [hydrology settings](../examples/fe_walter/operation/hydrology/hydrology.yaml)
connect each native outlet to one local inflow node. The
[accepted native model](../examples/fe_walter/operation/hydrology/model.yaml) and
[weather file](../examples/fe_walter/operation/hydrology/forcing.csv.gz) are retained
for reproducibility. This lesson reuses their saved inflows.'''),
        md('''## 3. Read the Rule-based comparator

The completed baseline uses the generic published Hanasaki flood-control
comparator with `alpha: 0.85` from [Hanasaki et al. (2006), Eq. 3](https://doi.org/10.1016/j.jhydrol.2005.11.011).
This fixed generic setting provides the comparison baseline.
Its first coefficient is seeded from the prior operating year: storage
**21,914,228.648262143 m³** on 2020-05-01 gives
**k = 0.19022285020658533**. Each later May 1 refresh uses that method's own
simulated beginning-of-day storage. Every method still shares the physical
2021-01-01 initial storage shown above.'''),
        code('''show_file("examples/fe_walter/operation/agents.rule.yaml", "Complete Rule-based agent settings")
show_file("examples/fe_walter/operation/initialization.json", "Complete Rule-based initialization")
show_file("examples/fe_walter/operation/hydrology/hydrology.yaml", "Complete hydrology boundary settings")
show_file("examples/fe_walter/coupled/auditors.yaml", "Complete release auditor settings")'''),
        md('''## 4. Switch to either LLM method

The two prepared alternatives reuse the actual complete agents, model profile,
system prompts, and optional operating-knowledge document. Their physical case,
dates, inflows, auditors, model settings, and output schema stay aligned. Their
method names are:

- **LLM without additional operating knowledge**
- **LLM with additional operating knowledge**

Neither five-year LLM method has been executed, so this section contains settings
only. The historical 2016 LLM curves must not be interpreted as 2021–2025 results.'''),
        code('''for title, path in [
    ("Five-year entry: LLM without additional operating knowledge", "examples/fe_walter/operation/llm_available.yaml"),
    ("Five-year entry: LLM with additional operating knowledge", "examples/fe_walter/operation/llm_knowledge.yaml"),
    ("Complete agent: without additional operating knowledge", "examples/fe_walter/coupled/agents.llm_available.yaml"),
    ("Complete agent: with additional operating knowledge", "examples/fe_walter/coupled/agents.llm_knowledge.yaml"),
    ("Complete shared model settings", "examples/fe_walter/coupled/models.yaml"),
    ("Complete prompt: available information", "examples/fe_walter/prompts/available_information.txt"),
    ("Complete prompt: retrieved knowledge", "examples/fe_walter/prompts/retrieved_knowledge.txt"),
    ("Complete operating-knowledge document", "examples/fe_walter/knowledge/operating_rules.md"),
]:
    show_file(path, title, expanded=False)'''),
        md('''## 5. Run the offline preflight

`check_preparation()` verifies hashes, complete dates, finite nonnegative inflows,
the common physical case, separate future output paths, shared model settings,
saved result coverage, and the distinction between engineering and scientific
readiness. It loads settings for inspection only.'''),
        code('''from examples.fe_walter.operation.preflight import check_preparation

readiness = check_preparation()
display(ReadableText("Offline preparation report", json.dumps(readiness, indent=2)))
display(pd.DataFrame(readiness["methods"]))'''),
        md('''The lower hydrology has completed C&V: calibration uses 1990–2010,
and independent validation uses 2011–2020. The five-year model retains the selected
`seed-314159` runoff and routing parameters. Validation KGE is 0.869 and NSE is
0.875 under an observed White Haven boundary. The preflight checks this lineage
alongside the shared inputs and reports `live_ready: true`.

The short dam-to-White Haven reach and its small local catchments retain transferred
parameters. Lehighton C&V constrains combined runoff and routing; individual tributaries
were not separately gauged. These scope limits remain in the report. Running this
notebook reads saved evidence only; LLM execution requires a separate decision.'''),
        md('''## 6. Inspect saved baseline evidence

Only the Rule-based comparator has a complete 1,826-day saved result. Controlled
release excludes spill. The primary flow scores omit the first 21 routing days;
White Haven also excludes 126 provisional observation records. All dates remain
visible in the plots.'''),
        code('''summary = json.loads((operation / "outputs/summary.json").read_text(encoding="utf-8"))
scores = [
    {"measure": "Water elevation MAE", "value": summary["water_elevation"]["MAE_ft"], "unit": "ft", "records": summary["water_elevation"]["n"]},
]
for station, values in summary["streamflow"].items():
    scores.append({"measure": f"{station} KGE (2009)", "value": values["KGE_2009"], "unit": "dimensionless", "records": values["n"]})
display(pd.DataFrame(scores))

sensitivity = summary["alpha_sensitivity"]
display(pd.DataFrame([
    {"alpha": summary["adopted_alpha"], "status": "retained generic comparator", "evaluation MAE (ft)": sensitivity["evaluation"]["baseline"]["MAE_ft"], "lower-bound days": 0},
    {"alpha": sensitivity["candidate_alpha"], "status": "not adopted", "evaluation MAE (ft)": sensitivity["evaluation"]["calibrated"]["MAE_ft"], "lower-bound days": sensitivity["candidate_days_at_lower_bound"]},
]))'''),
        code('''display(Image(filename=str(operation / "outputs/reservoir_operations.png"), width=900))'''),
        md('''*Saved Rule-based reservoir evidence, 2021–2025. The upper panel compares
simulated and observed water elevation; the lower panel separates controlled
release, upstream simulated inflow, and spill.*'''),
        code('''display(Image(filename=str(operation / "outputs/downstream_streamflow.png"), width=900))'''),
        md('''*Saved downstream daily mean streamflow at White Haven and Lehighton.
Observation gaps remain gaps; quality masks affect scores rather than plotted dates.*'''),
        md('''The non-adopted alpha candidate reduced water-elevation MAE from 88.61 ft
to 57.75 ft, but worsened downstream flow scores and requested unavailable water
on 329 days. The fixed comparison therefore retains `alpha: 0.85` and labels the
candidate as sensitivity evidence.

## Next steps

- Download the [saved baseline files and figures](../examples/fe_walter/operation/README.md).
- Treat the Rule-based series as a generic comparator, not a calibrated optimum.
- Read the [completed hydrology C&V](../examples/fe_walter/downstream/validation.md)
  and retain its observed-boundary scope when interpreting operation differences.
- When LLM runs are eventually authorized and completed, compare them against these
  same inputs and masks; do not substitute the historical 2016 curves.'''),
    ]
