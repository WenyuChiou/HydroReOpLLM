# Daily simulation workflow

Set up a study from the whole simulation down to each reservoir operator.
HydroCNHS calculates catchment inflows; the selected Rule-based or LLM agents
request releases; common reservoir physics and river routing update the system.
You configure these parts in files rather than editing the engine.

## Configuration map

```text
experiment.yaml       dates, output and references to the files below
  hydrology.yaml     HydroCNHS model, weather and inflow-node bindings
  reservoirs.yaml    reservoir limits, initial storage and water connections
  agents.*.yaml      one operator per reservoir
  models.yaml        model provider, endpoint and generation settings
  information.yaml   optional observations, forecasts or operating targets
  prompts/           system and user message text
```

Each path is relative to the file that declares it. Keep the folder together
when copying a study. Start with the [complete configuration template](TEMPLATES.md)
and replace its clearly marked `YOUR_...` values with your study settings.

## Follow the setup chapters in order

| Step | Set up | What you decide |
|---|---|---|
| 1 | [Installation](GETTING_STARTED.md) | Python environment and package installation |
| 2 | [Global simulation](GLOBAL_SETTINGS.md) | Run name, output folder and inclusive Daily operation dates |
| 3 | [HydroCNHS hydrology](HYDROLOGY_SETUP.md) | Model/forcing files, hydrological warm-up and inflow bindings |
| 4 | [Reservoirs and network](BUILD_SIMULATION.md) | Initial storage, capacities, release limits and upstream/downstream links |
| 5 | [LLM and prompts](CONFIGURATION.md) | Operator, model profile, endpoint and message files |
| 6 | [Available information](INFORMATION.md) | Optional data the agent may see, when it becomes available and where it enters the prompt |
| 7 | [Run the simulation](RUNNING.md) | Check settings, prepare hydrology, run operations and inspect saved results |
| 8 | [F.E. Walter example](CASE_STUDIES.md) | Apply those settings to the article's case and read the completed comparison |

You do not need to run developer tests to use the model. `check` checks your
study configuration; it does not make a model request or run a calibration.

## Choose the input route

Most new HydroCNHS studies use the **coupled** route. If you already have
prepared local inflow series, use the prepared-inflow route instead. The files
have different schemas; do not substitute one case file for the other.

| Route | Entry and inputs | Commands |
|---|---|---|
| Coupled hydrology | `hydroops-coupled-simulation.v2`; split hydrology, reservoirs, agents and model files | `check`, then `prepare`, then `run` |
| Prepared inflow | `llm-reservoir-experiment.v1` or the documented prepared v2 case; saved inflows and physical network | `check`, then `run`; no hydrology preparation needed |

For the coupled template after filling its settings:

```shell
reservoir-experiment check study/experiment.yaml
reservoir-experiment prepare study/experiment.yaml
reservoir-experiment run study/experiment.yaml --allow-network
```

`--allow-network` is needed for the configured LLM service calls; omit it for a
Rule-based run. `run` reuses a matching preparation. Use a new output directory
for a new experiment, then follow [Results](RESULTS_GUIDE.md) to read storage,
requested/actual release, spill and downstream flow.

For a complete prepared-inflow teaching example:

```shell
reservoir-experiment check examples/daily_offline/single.yaml
reservoir-experiment run examples/daily_offline/single.yaml
reservoir-experiment verify runs/daily-single
```

The [single-dam and three-dam examples](DAILY_EXAMPLES.md) supply every input and
use simple invented inflows and fixed releases to show the configuration route.
They are optional learning examples, not a prerequisite or a calibrated study.
The [multi-reservoir guide](MULTI_RESERVOIR.md) shows the weather-driven route.

## Where the article example fits

After the setup chapters, open [F.E. Walter](CASE_STUDIES.md). Its case page
distinguishes the executable five-year Rule-based lesson, the completed
2021–2025 LLM comparison and the historical 2016 illustration. Read each result
with the configuration and initial state that produced it.
