# HydroReOpLLM User Manual

:::::{container} manual-intro

Hydrological simulation · Reservoir operations

Configure a reservoir experiment, connect its hydrology, and choose how an LLM
uses the information available to each operator.

Built on HydroCNHS. Use the same workflow for a single reservoir or a connected
network, with your own model provider, prompts and operational knowledge.

:::{container} start-links

[Install the package →](GETTING_STARTED.md)

[See the Daily workflow](DAILY_WORKFLOW.md)

:::

:::::

## Start with the whole system

HydroCNHS turns weather into catchment inflow. Each reservoir operator uses
that inflow, storage and your selected information to request release. Reservoir
physics applies the limits and spill, then routes the water downstream.

:::::{container} reading-route

:::{container} route-step

### 01 · Understand the flow

See how hydrology, reservoir decisions and routing connect before editing files.

[Read the overview →](README.md)

:::

:::{container} route-step

### 02 · Configure your model

Work from simulation dates to catchments, reservoirs, operators and information.

[Open the configuration guide →](INPUT_OUTPUT.md)

:::

:::{container} route-step

### 03 · Follow a complete case

Use FE Walter to connect the settings to a real reservoir and inspect saved output.

[Explore the case study →](CASE_STUDIES.md)

:::

:::::


## Configure, run and inspect

Follow the chapters in order for your first model. Use the left-hand navigation
and search when returning to a particular setting.

| Chapter | What you will learn |
|---|---|
| [Overview](README.md) | Understand inflow, decisions, reservoir physics and routing. |
| [Installation](GETTING_STARTED.md) | Install the package and check its command. |
| [Daily workflow map](DAILY_WORKFLOW.md) | See the whole setup and choose coupled hydrology or prepared inflows. |
| [Configuration overview](INPUT_OUTPUT.md) | See the files and the order in which to fill them. |
| [Global settings](GLOBAL_SETTINGS.md) | Set dates, run identity and output paths. |
| [Hydrology](HYDROLOGY_SETUP.md) | Supply the accepted native model and weather. |
| [Reservoirs and network](BUILD_SIMULATION.md) | Connect inflow, storage and downstream paths. |
| [Agents and LLM](CONFIGURATION.md) | Select a rule or a model, prompt and optional context. |
| [Available information](INFORMATION.md) | Add an observation, forecast or target and expose it to the chosen agent. |
| [Check and run](RUNNING.md) | Check files, prepare inflow, run operations and verify records. |
| [FE Walter case study](CASE_STUDIES.md) | Apply the settings to the reservoir, data and saved results. |
| [Results](RESULTS_GUIDE.md) | Read water elevation and controlled release. |
| [Saved Daily / Hourly comparison](../examples/fe_walter/completed_results/README.md) | A versioned three-run example with its original figures and metrics. |
| [Troubleshooting](TROUBLESHOOTING.md) | Diagnose input, response and interruption problems. |

:::{container} saved-example-note

**About saved results.** The downloadable case is a fixed teaching snapshot,
not a live view of ongoing research. Its dates, run count and original metric
definitions belong to that snapshot; consult its source records when comparing
it with a newer experiment.

Current article labels are **LLM without operational knowledge** and
**LLM with operational knowledge**. Historical files retain their original
method labels and model replies.

:::

<details>
<summary>API, configuration details and developer reference</summary>

- [API reference](API_REFERENCE.md)
- [Configuration field reference](PARAMETER_REFERENCE.md)
- [Variables and units](VARIABLES_AND_UNITS.md)
- [43-module inventory](MODULE_INVENTORY.md)
- [Project structure and complete file index](CODE_STRUCTURE.md)
- [Time scales](TIME_SCALES.md) and [YAML time settings](YAML_TIME_SCALES.md)
- [Hourly GWLF](HOURLY_GWLF.md) and [groundwater initialization](GWLF_GROUNDWATER.md)
- [Developer QA matrix](DAILY_QA.md)

</details>

Use the [HydroCNHS tutorials](https://github.com/cylin928/HydroCNHS/tree/main/tutorials)
for basin construction, hydrological parameters and calibration. This manual
focuses on reservoir agents and the LLM workflow added by HydroReOpLLM.

## Tutorial notebook

Open the [FE Walter tutorials folder](../tutorials/), follow its README, or
{download}`download the notebook <_notebook_downloads/main.ipynb>`.

The notebook reads saved data. It makes no model request and does not rerun
hydrology. [Sources and citation](REFERENCE.md) identifies the
framework and case references.

## Framework diagram

![HydroReOpLLM overview](figures/hydroopslm-cover.png)
