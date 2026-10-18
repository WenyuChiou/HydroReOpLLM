# Overview

[English](README.md) | [繁體中文](README.zh-TW.md)

HydroOpsLLM adds LLM reservoir operators to HydroCNHS. You keep your hydrological
model and choose how each reservoir makes release decisions: **Rule-based** or
**LLM**.

![HydroOpsLLM: reservoir operations built on HydroCNHS](figures/hydroopslm-cover.png)

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

| Chapter | What you will learn |
|---|---|
| [Overview](README.md) | Understand inflow, decisions, reservoir physics and routing. |
| [Installation](GETTING_STARTED.md) | Install the package and check its command. |
| [Configuration overview](INPUT_OUTPUT.md) | See the files and the order in which to fill them. |
| [Global settings](GLOBAL_SETTINGS.md) | Set dates, run identity and output paths. |
| [Hydrology](HYDROLOGY_SETUP.md) | Supply the accepted native model and weather. |
| [Reservoirs and network](BUILD_SIMULATION.md) | Connect inflow, storage and downstream paths. |
| [Agents and LLM](CONFIGURATION.md) | Select a rule or a model, prompt and optional context. |
| [Check and run](RUNNING.md) | Check files, prepare inflow, run operations and verify records. |
| [Case studies](CASE_STUDIES.md) | Follow complete examples after learning the settings. |
| [Results](RESULTS_GUIDE.md) | Read water elevation and controlled release. |
| [Troubleshooting](TROUBLESHOOTING.md) | Diagnose input, response and interruption problems. |
| [API reference](API_REFERENCE.md) | Find functions and extension interfaces. |

For basin construction and calibration, follow the
[HydroCNHS tutorials](https://github.com/cylin928/HydroCNHS/tree/main/tutorials).
This manual explains the added reservoir and LLM workflow.

## Core workflow

The diagram below separates the upstream hydrology calculation from daily
reservoir decisions. Follow the arrows from weather to inflow, then through
release, storage and downstream flow.

![HydroOpsLLM core workflow](figures/hydrocnhs-coupling-framework-en.png)

*Figure 1. HydroCNHS provides upstream hydrology and routing. The selected agent
requests a controlled release; reservoir physics applies it and updates storage.
Response validation checks the model reply, audits evaluate configured operating
criteria, and the recorder saves the decision and physical result.*
