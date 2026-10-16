# Overview

[English](README.md) | [繁體中文](README.zh-TW.md)

HydroOpsLLM couples reservoir decisions to hydrological simulation with HydroCNHS.
The hydrological model supplies streamflow to the reservoir. At each time step,
the LLM uses available information to propose a release.

The reservoir calculation determines implemented release, spill and storage,
then routes outflow downstream. Updated conditions inform the next decision,
forming a repeated simulation cycle. The current case uses daily time steps.
A rule-based agent can use the same reservoir calculation for comparison.

![HydroOpsLLM core workflow](figures/hydrocnhs-coupling-framework-en.png)

[Full-resolution PNG](figures/hydrocnhs-coupling-framework-en.png) · [Vector PDF, 180 mm](figures/hydrocnhs-coupling-framework-en.pdf).

Start with [Installation](GETTING_STARTED.md), then [build a simulation](BUILD_SIMULATION.md)
and follow the [FE Walter case](../examples/fe_walter/README.md).
