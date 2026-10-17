# HydroOpsLLM User Manual

**Hydrological Simulation with Large Language Model Reservoir Operations**

Add LLM reservoir operators to your HydroCNHS simulation. Start with the common
settings, follow the FE Walter example, then adapt its agent design to your study.

![HydroOpsLLM cover](figures/hydroopslm-cover.png)

## Contents

| Read in this order | What you will learn |
|---|---|
| [Overview](README.md) | How inflow, decisions, reservoir physics and routing connect. |
| [Installation](GETTING_STARTED.md) | Install and check the package. |
| [Inputs and configuration](INPUT_OUTPUT.md) | Set the experiment, hydrology and reservoirs. |
| [Configure agents](CONFIGURATION.md) | Select Rule-based or LLM; set prompts and model parameters. |
| [FE Walter tutorial](../tutorials/fe_walter.md) | Follow the actual configuration files step by step. |
| [Results](RESULTS_GUIDE.md) | Read water elevation and controlled release. |
| [Troubleshooting](TROUBLESHOOTING.md) | Resolve an input, response or interruption problem. |
| [API reference](API_REFERENCE.md) | Find functions, extension interfaces and code modules. |

Use the [HydroCNHS tutorials](https://github.com/cylin928/HydroCNHS/tree/main/tutorials)
for basin construction, hydrological parameters and calibration. This manual
focuses on reservoir agents and the LLM workflow added by HydroOpsLLM.

## Companion notebooks

{download}`FE Walter results notebook <_notebook_downloads/main.ipynb>` ·
{download}`Multiple-reservoir configuration <_notebook_downloads/advanced.ipynb>`

The notebooks use saved data or inspect configuration files. They do not request
a model or rerun hydrology. [Sources and citation](REFERENCE.md) identifies the
framework and case references.

[繁體中文](index.zh-TW.md)
