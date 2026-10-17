# Overview

[English](README.md) | [繁體中文](README.zh-TW.md)

![HydroOpsLLM: reservoir operations built on HydroCNHS](figures/hydroopslm-cover.png)

HydroOpsLLM adds LLM reservoir operators to HydroCNHS. You keep your hydrological
model and choose how each reservoir makes release decisions: **Rule-based** or
**LLM**.

HydroCNHS first uses precipitation, temperature and potential evapotranspiration
(PET) to calculate daily reservoir inflow. HydroOpsLLM saves this inflow for the
operation period. Each day, an agent uses the inflow and current reservoir state
to request a release. The reservoir calculation determines the actual release,
spill and remaining storage, then routes the outflow downstream. The next day
starts from the updated state.

The simulation has two stages: calculate upstream inflow, then run
daily reservoir operations and downstream routing. Reservoir decisions do not
change the upstream rainfall–runoff calculation.

## Read the manual

| Step | Chapter | What you will do |
|---|---|---|
| 1 | [Installation](GETTING_STARTED.md) | Install the package and check the command. |
| 2 | [Inputs and configuration](INPUT_OUTPUT.md) | Separate experiment, hydrology, reservoir and agent settings. |
| 3 | [Configure agents](CONFIGURATION.md) | Select a rule or an LLM, then set the model, prompt and optional knowledge. |
| 4 | [FE Walter tutorial](../tutorials/fe_walter.md) | Follow a real case from `experiment.yaml` to daily operation. |
| 5 | [Results](RESULTS_GUIDE.md) | Read water levels and controlled release. |
| 6 | [Troubleshooting](TROUBLESHOOTING.md) | Find an input, response or interruption problem. |
| 7 | [API reference](API_REFERENCE.md) | Find the functions behind the settings. |

For basin construction and calibration, follow the
[HydroCNHS tutorials](https://github.com/cylin928/HydroCNHS/tree/main/tutorials).
This manual explains the added reservoir and LLM workflow.

## Core workflow

![HydroOpsLLM core workflow](figures/hydrocnhs-coupling-framework-en.png)

*Figure 1. HydroCNHS provides upstream hydrology and routing. The selected agent
requests a controlled release; reservoir physics applies it and updates storage.
Response validation checks the model reply, audits evaluate configured operating
criteria, and the recorder saves the decision and physical result.*
