# HydroReOpLLM User Manual

[English](index.md) | [繁體中文](index.zh-TW.md)

**Hydrological Simulation with Large Language Model Reservoir Operations**

Add LLM reservoir operators to your HydroCNHS simulation. Learn the common
settings first, then follow a complete case study and adapt it to your research.

![HydroReOpLLM cover](figures/hydroopslm-cover.png)

## Contents

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
| [FE Walter case study](CASE_STUDIES.md) | Apply the settings to the reservoir, data and saved results. |
| [Results](RESULTS_GUIDE.md) | Read water elevation and controlled release. |
| [Troubleshooting](TROUBLESHOOTING.md) | Diagnose input, response and interruption problems. |
| [API reference](API_REFERENCE.md) | Find functions and extension interfaces. |

Use the [HydroCNHS tutorials](https://github.com/cylin928/HydroCNHS/tree/main/tutorials)
for basin construction, hydrological parameters and calibration. This manual
focuses on reservoir agents and the LLM workflow added by HydroReOpLLM.

## Tutorial notebook

Open the [FE Walter tutorials folder](../tutorials/), follow its README, or
{download}`download the notebook <_notebook_downloads/main.ipynb>`.

The notebook reads saved data. It makes no model request and does not rerun
hydrology. [Sources and citation](REFERENCE.md) identifies the
framework and case references.
