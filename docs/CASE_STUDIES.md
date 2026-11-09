# F.E. Walter: apply the settings

Use this case after the global, hydrology, reservoir, LLM and information
chapters. It connects the configuration layers to one reservoir and the three
methods: Rule-based, LLM without operational knowledge, and LLM with
operational knowledge.

## Choose where to start

| Your starting point | Operation period | Input and workflow | Open |
|---|---|---|---|
| Reproduce the paper’s MOSART-Urban baseline | 1 January 2021–31 December 2025 | Read `inflows.csv`; `check → run → verify` | [Five-year paper baseline](../examples/fe_walter/operation/README.md#paper-baseline-with-mosart-urban) |
| Start from the hydrological model and weather | 1 January–31 December 2016 | Prepare inflow from model and forcing; `check → prepare → run → verify` | [Historical coupled weather-driven example](../examples/fe_walter/coupled/README.md) |

Start with the five-year MOSART-Urban baseline using prepared daily inputs. Choose the 2016 coupled example to apply the weather-driven workflow
from the preceding configuration chapters. Each entry has its own dates and
settings; keep the files from your chosen example together.

## Read the case from settings to results

The table below follows the **2021–2025 prepared-inflow entry**.

| Layer | Case setting | Where to open it |
|---|---|---|
| Global simulation | Daily operations, 1 January 2021–31 December 2025 | [experiment.mosart.yaml](../examples/fe_walter/operation/experiment.mosart.yaml) |
| Inflow | Prepared upstream and local daily inflows | [inflows.csv](../examples/fe_walter/operation/inflows.csv) and [case input guide](../examples/fe_walter/operation/README.md) |
| Reservoir and river network | Physical limits, water connections and initial state | [case.mosart.json](../examples/fe_walter/operation/case.mosart.json) |
| Rule-based operator | MOSART-Urban flood-control rule | [agents.mosart.yaml](../examples/fe_walter/coupled/agents.mosart.yaml) |
| Separate LLM configurations | Provider, prompt and knowledge references | [Without knowledge](../examples/fe_walter/operation/llm_available.yaml) / [With knowledge](../examples/fe_walter/operation/llm_knowledge.yaml) |
| Additional information | Add a station observation or retrieval input | [Available information](INFORMATION.md#add-an-observed-station-series) |
| Daily performance | KGE and RMSE for MOSART-Urban and the saved LLM settings | [Table 3](results/fe_walter/completed/README.md#daily-performance-against-observations) |

The paper baseline and the saved LLM runs have separate configurations and
initialization. The results page gives the scoring dates and observation
definitions and labels the historical Hanasaki comparisons.

## Select the material you need

| Material | Period | Use |
|---|---|---|
| [MOSART-Urban paper baseline](../examples/fe_walter/operation/README.md#paper-baseline-with-mosart-urban) | Daily 2021–2025 | Run and verify the rule-based baseline |
| [Table 3 and historical comparisons](results/fe_walter/completed/README.md) | Daily 2021–2025 and fixed Hourly Ida/Rain events | Read current KGE/RMSE and archived figures |
| [Historical illustration](../examples/fe_walter/results.md) | Daily 2016 | Inspect the older teaching example; do not use it as the current result |

The [site and data guide](../examples/fe_walter/README.md) describes the reservoir
and observations. The [notebook guide](../examples/fe_walter/notebook.md) links
the optional executable notebooks and downloads. You can download the settings
and view the plots within this manual; repository sources are supplementary.
