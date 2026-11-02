# F.E. Walter: apply the settings

Use this case after the global, hydrology, reservoir, LLM and information
chapters. It connects the configuration layers to one reservoir and the three
methods: Rule-based, LLM without operational knowledge, and LLM with
operational knowledge.

## Choose where to start

| Your starting point | Operation period | Input and workflow | Open |
|---|---|---|---|
| Use prepared daily inflows | 1 January 2021–31 December 2025 | Read `inflows.csv`; `check → run → verify` | [Five-year operation lesson](../examples/fe_walter/operation/README.md) |
| Start from the hydrological model and weather | 1 January–31 December 2016 | Prepare inflow from model and forcing; `check → prepare → run → verify` | [Coupled weather-driven example](../examples/fe_walter/coupled/README.md) |

Start with the five-year lesson to follow reservoir operation using prepared
inputs. Choose the 2016 coupled example to apply the weather-driven workflow
from the preceding configuration chapters. Each entry has its own dates and
settings; keep the files from your chosen example together.

## Read the case from settings to results

The table below follows the **2021–2025 prepared-inflow entry**.

| Layer | Case setting | Where to open it |
|---|---|---|
| Global simulation | Daily operations, 1 January 2021–31 December 2025 | [experiment.yaml](../examples/fe_walter/operation/experiment.yaml) |
| Inflow | Prepared upstream and local daily inflows | [inflows.csv](../examples/fe_walter/operation/inflows.csv) and [case input guide](../examples/fe_walter/operation/README.md) |
| Reservoir and river network | Physical limits, water connections and initial state | [case.json](../examples/fe_walter/operation/case.json) |
| Rule-based operator | Hanasaki reference and rule parameters | [agents.rule.yaml](../examples/fe_walter/operation/agents.rule.yaml) |
| LLM operators | Provider, prompt and knowledge references | [Without knowledge](../examples/fe_walter/operation/llm_available.yaml) / [With knowledge](../examples/fe_walter/operation/llm_knowledge.yaml) |
| Additional information | Add a station observation or retrieval input | [Available information](INFORMATION.md#add-an-observed-station-series) |
| Saved comparison | Versioned plots, metrics and downloadable values | [Daily / Hourly teaching snapshot](results/fe_walter/completed/README.md) |

The settings above belong to the configurable five-year teaching lesson. The
completed research comparison has its own frozen configuration and initialization;
its [result page](results/fe_walter/completed/README.md) states the
actual period, three accepted seeds and observation definitions. These result
sets must not be interchanged merely because they use the same reservoir.

## Select the material you need

| Material | Period | Use |
|---|---|---|
| [Executable operation lesson](../examples/fe_walter/operation/README.md) | Daily 2021–2025 | Follow the configuration and run a Rule-based lesson in a new folder |
| [Completed comparison](results/fe_walter/completed/README.md) | Daily 2021–2025 and fixed Hourly Ida/Rain events | Read the accepted three-method figures and updated Table 3 |
| [Historical illustration](../examples/fe_walter/results.md) | Daily 2016 | Inspect the older teaching example; do not use it as the current result |

The [site and data guide](../examples/fe_walter/README.md) describes the reservoir
and observations. The [notebook guide](../examples/fe_walter/notebook.md) links
the optional executable notebooks and downloads. You can download the settings
and view the plots within this manual; repository sources are supplementary.
