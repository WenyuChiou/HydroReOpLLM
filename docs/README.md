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

![HydroOpsLLM core workflow](figures/hydrocnhs-coupling-framework-en.png)

Continuous upstream hydrology is precomputed. The daily cycle then renders a
decision, validates its response, applies physics, routes outflow downstream and
commits the transition for the next decision. Response validation checks the
action contract; diagnostic audit evaluates the decision; the recorder preserves
the evidence. These are separate responsibilities.

Start with [Installation](GETTING_STARTED.md), read [Inputs and outputs](INPUT_OUTPUT.md),
then [configure an agent](CONFIGURATION.md) and follow the
[FE Walter tutorial](../tutorials/fe_walter.md).
