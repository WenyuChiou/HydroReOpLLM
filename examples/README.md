# HydroOpsLM examples

[English](README.md) | [繁體中文](README.zh-TW.md)

These examples run through this repository's `check → run → verify` workflow and
native HydroCNHS Dam API. Each case supplies its inputs and decision strategy;
the framework owns reservoir physics, routing, outputs and audit/trace.

| Example | Start here | Scope |
|---|---|---|
| FE Walter: three decision methods | [Walkthrough](fe_walter/README.md) | Shared inflow and physics; benchmark, zero-shot and DKP |
| Multiple reservoirs | [Lesson 07](../tutorials/07_multi_and_custom.ipynb) | Controlled reservoirs, passive outlet and river connections |
| Your catchment | [Hydrology setup](../docs/HYDROLOGY_SETUP.md) | Native runoff, parameters, routing and C&V |

Start with the [tutorial](../tutorials/README.md). Offline LLM replies are synthetic
fixtures for interface checks. Live templates retain temperature **0.7** and require
a separate readiness decision. Root-level ABM files remain native loader compatibility
modules; [archive](../archive/README.md) lists historical experiment entries.
