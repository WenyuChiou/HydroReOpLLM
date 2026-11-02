# HydroReOpLLM User Manual

:::::{container} manual-intro

Hydrological simulation · Reservoir operations

Build a Daily reservoir experiment with your hydrological model, a single
reservoir or a connected network, and Rule-based or LLM operators.

:::{container} start-links

[Install the package →](GETTING_STARTED.md)

[Browse the examples](CASE_STUDIES.md)

:::

:::::

## How it works

HydroCNHS calculates catchment inflow. Each reservoir operator requests a
release using the current reservoir state and the information you provide.
Reservoir physics updates storage and spill; routing carries the outflow downstream.

![HydroCNHS hydrology connected to LLM reservoir decisions, reservoir physics and downstream routing](figures/hydrocnhs-coupling-framework-en.png)

The LLM reply is checked before use. Operating-rule checks record whether a
decision follows the selected rules; a valid reply alone does not show good operation.

## Read in order

| Step | What to set up |
|---|---|
| [1. Installation](GETTING_STARTED.md) | Install the package and check the command. |
| [2. Configuration files](INPUT_OUTPUT.md) | See the files that make up a simulation. |
| [3. Global settings](GLOBAL_SETTINGS.md) | Set dates, the run name and output directory. |
| [4. Hydrology](HYDROLOGY_SETUP.md) | Connect the hydrological model and weather. |
| [5. Reservoirs and network](BUILD_SIMULATION.md) | Set storage, release limits and water connections. |
| [6. Operators and prompts](CONFIGURATION.md) | Choose a rule or LLM and supply its prompt. |
| [7. Available information](INFORMATION.md) | Add observations, forecasts or operational knowledge. |
| [8. Run the simulation](RUNNING.md) | Check the configuration, prepare inflow and run operations. |
| [9. Read the results](RESULTS_GUIDE.md) | Inspect release, storage, downstream flow and decision records. |
| [10. Complete examples](CASE_STUDIES.md) | Apply the settings to a single reservoir, a network or FE Walter. |

Use the sidebar to return to a chapter. Detailed API, developer checks and
historical research records are grouped under **Reference**.

For basin construction and calibration, see the
[HydroCNHS tutorials](https://github.com/cylin928/HydroCNHS/tree/main/tutorials).
