# HydroCNHS + LLM Reservoir Agent user manual

[English](README.md) | [繁體中文](README.zh-TW.md)

Follow the [root README](../README.md) for installation and your first run.
This manual separates native hydrological model setup from the added LLM reservoir
modules. The [official HydroCNHS documentation](https://cylin928.github.io/HydroCNHS/)
covers the original model builder, coupling APIs, calibration and data collector.

| Step | Read | What you will configure or check |
|---|---|---|
| 1 | [Hydrology setup](HYDROLOGY_SETUP.md) | Basin areas, forcing, GWLF/ABCD parameters, routing and C&V |
| 2 | [Input preparation](../tutorials/01_input_and_map.ipynb) | Daily inflow, units, reservoir profiles and GIS |
| 3 | [Experiment settings](USER_GUIDE.md) | YAML, dates, network, agents, decision backend and output |
| 4 | [Policy design](policy_design.md) | Observations, prompts, optional knowledge and action schema |
| 5 | [Audit plugins](auditor_plugins.md) | Versioned checks and decision/physics/trace records |
| 6 | [Tutorials](../tutorials/README.md) | Offline daily simulation, verification and results |
| 7 | [Multiple reservoirs / your own data](../tutorials/07_multi_and_custom.ipynb) | Topology, independent decision units and passive outlets |

[Examples](../examples/README.md) provide complete configurations.
[Advanced native workflows](ADVANCED_WORKFLOWS.md) cover the retained HydroCNHS capabilities.
Before using a real provider, follow [live readiness](LIVE_READINESS.md).

The manual is currently browsable in the repository; the official site above is
the upstream HydroCNHS site. This repository does not yet have a published documentation site.
