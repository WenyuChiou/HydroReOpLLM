# HydroOpsLLM User Manual

**Hydrological Simulation with Large Language Model Reservoir Operations**

Configure reservoir operations within a coupled hydrological simulation.
Learn the common setup and LLM decision workflow first. Then use F.E. Walter to
design a reservoir-operation study from site information, data and prompts.

![HydroOpsLLM cover](figures/hydroopslm-cover.png)

:::: {container} reading-route

::: {container} route-step

[01 · Understand the framework](README.md)

Hydrology, reservoir decisions and the records connecting them.


:::

::: {container} route-step

[02 · Configure a reservoir agent](CONFIGURATION.md)

Choose Rule-based or LLM, model parameters, prompts and available information.


:::

::: {container} route-step

[03 · Design the F.E. Walter study](../examples/fe_walter/README.md)

Understand the site, operating purpose and data, then follow its configuration and results.

:::

::::

## Contents

| Read in this order | What you will learn |
|---|---|
| [Overview](README.md) and [Installation](GETTING_STARTED.md) | What the package adds and how to install it. |
| [Inputs and outputs](INPUT_OUTPUT.md) | Experiment YAML, data formats, units and output files that differ from native HydroCNHS. |
| [Configure an agent](CONFIGURATION.md) and [Build a simulation](BUILD_SIMULATION.md) | Select a rule or LLM, map reservoirs and choose prompts/model settings. |
| [F.E. Walter case study](../examples/fe_walter/README.md) and [worked tutorial](../tutorials/fe_walter.md) | Start with the map, reservoir purpose and data; then design prompts, execute and interpret the study. |
| [Results](RESULTS_GUIDE.md) and [Recovery](RUNNING.md) | Inspect decisions, audits, implemented flows and interrupted runs. |
| [Python API documentation](API_REFERENCE.md) | Function parameters, returns and extension contracts. |
| [Configuration reference](PARAMETER_REFERENCE.md) and [Code structure](CODE_STRUCTURE.md) | Look up fields and their implementation. |

Use [HydroCNHS tutorials](https://github.com/cylin928/HydroCNHS/tree/main/tutorials)
for unchanged hydrological modeling and calibration. This manual documents our
added inputs, agent configuration, LLM behavior, coupling and records.

## The framework

![HydroOpsLLM concept](figures/hydrocnhs-coupling-framework-en.png)

Continuous upstream rainfall–runoff and routing are precomputed with HydroCNHS.
The daily loop then connects a rule or LLM decision, response validation, reservoir
physics, downstream routing and committed-state feedback through the native Dam API.
Response validation checks the action contract, diagnostic audit evaluates behavior,
and the recorder preserves evidence.


## Companion notebooks

{download}`Main walkthrough <_notebook_downloads/main.ipynb>` ·
{download}`Multiple reservoirs <_notebook_downloads/advanced.ipynb>`

These downloads retain the original notebooks and saved outputs.
Catchment modelling and calibration/validation follow the [HydroCNHS manual](https://cylin928.github.io/HydroCNHS/).
[Sources and citation](REFERENCE.md) explain the original framework and the added operation methods.

[繁體中文](index.zh-TW.md)
