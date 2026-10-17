# Overview

[English](README.md) | [繁體中文](README.zh-TW.md)

HydroOpsLLM couples reservoir decisions to hydrological simulation with HydroCNHS.
Preparation first computes full-period weather-driven hydrology and selects the
reservoir inflow boundaries. During daily operation, the LLM uses available
information to propose a release.

The reservoir calculation determines implemented release, spill and storage,
then routes outflow downstream. Updated conditions inform the next decision,
forming a repeated simulation cycle. The current case uses daily time steps.
A rule-based agent can use the same reservoir calculation for comparison.
Each reservoir selects `type: rule_based` with a registered rule, or `type: llm`
with a model profile and explicit prompt. Reservoir decisions do not alter the
precomputed weather-to-runoff simulation.

## Read the manual

| Step | Chapter | What to do |
|---|---|---|
| 1 | [Installation](GETTING_STARTED.md) | Install the package and check the command-line entry. |
| 2 | [Inputs and outputs](INPUT_OUTPUT.md) | Separate global, hydrology, reservoir/coupling and agent settings; check data units. |
| 3 | [Build a simulation](BUILD_SIMULATION.md), [configure an agent](CONFIGURATION.md) and [model providers](MODEL_PROVIDERS.md) | Learn the common setup, switch Rule-based to LLM, then set the model, prompt and optional knowledge. |
| 4 | [F.E. Walter case study](../examples/fe_walter/README.md) and [worked tutorial](../tutorials/fe_walter.md) | Connect the map, operating purpose and data to actual YAML, prompt design and daily decisions. |
| 5 | [Results](RESULTS_GUIDE.md) and [Recovery](RUNNING.md) | Read the latest annual results, inspect records and resume interrupted runs. |
| 6 | [Python API](API_REFERENCE.md) and [code structure](CODE_STRUCTURE.md) | Find function contracts, extension points and their implementation modules. |

For catchment construction and calibration, follow the linked
[HydroCNHS prerequisites](HYDROLOGY_SETUP.md).

## Core workflow

![HydroOpsLLM core workflow](figures/hydrocnhs-coupling-framework-en.png)

Continuous upstream hydrology is precomputed. The daily cycle then renders a
decision, validates its response, applies physics, routes outflow downstream and
commits the transition for the next decision. Response validation checks the
action contract; diagnostic audit evaluates the decision; the recorder preserves
the evidence. These are separate responsibilities.
