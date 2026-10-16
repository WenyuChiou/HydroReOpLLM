# Code structure and the daily operation loop

The installed code separates reusable hydrology and reservoir operation from
regional data preparation and teaching cases. Start with
[Build a weather-to-operation simulation](BUILD_SIMULATION.md) before reading the
modules below.

## Installed reusable packages

```text
src/
  hydrocnhs/                         Native rainfall-runoff, routing and Dam API
  llm_reservoir_agent/
    weather.py                       Validate weather and run full-period hydrology
    coupled.py                       Compile the two-stage coupled simulation
    workflow.py                      check / prepare / run / verify / resume CLI
    network.py                       Daily native Dam and downstream routing host
    physics.py                       Release limits, storage balance and spill
    configured_backend.py            General prompt, provider and bounded retries
    information.py                   Causal decision-information selection
    audit.py                         Normalize, serialize and hash reported audits
    auditor.py                       Compose explicit diagnostic checks around a backend
    recovery.py                      Verify and reconstruct an interrupted prefix
```

`experiment.py` writes the durable operation records used by verification. The
console command `reservoir-experiment` enters `workflow.py`; users do not need to
wire these modules together in a custom script.

## Optional plugins and example-only sources

`src/llm_reservoir_agent/plugins/anik_v3_7.py` preserves the optional F.E. Walter
reference prompt and response behavior. It is a decision plugin, not a regional
weather, GIS or hydrology-preparation module.

The former `src/delaware_operations` material now lives under
`examples/fe_walter/legacy/`. It remains as source-only historical compatibility
material and is not installed as the common runtime.

Regional GIS processing, weather extraction, calibration/validation evidence,
benchmark statistics, F.E. Walter thresholds, prompts and knowledge documents
belong under `examples/` and `data/`. They are case evidence rather than defaults
for another basin.

## The two execution stages

### Stage 1: prepare weather-derived boundaries

`coupled.load_coupled_settings()` validates the coupled YAML, physical case,
operation method and complete weather inputs without running hydrology or calling
a model. `weather.simulate_weather()` then runs the accepted agent-free native
model over its complete start/end period. `coupled.prepare_coupled()` selects the
requested operation dates and compiles a pinned ordinary reservoir experiment.

Preparation writes no reservoir decisions. It records `model_requests: 0` and
keeps hydrological warm-up separate from the physical case's initial storage.

### Stage 2: operate and route daily

For each operation day:

1. `network.py` supplies the prepared incremental local flows to the native host.
2. The selected backend receives the current inlet, beginning storage and allowed history.
3. A rule or LLM returns a requested controlled release.
4. Response parsing and configured audits record their evidence.
5. `physics.py` limits the request by operating bounds and available water, then computes spill and ending storage.
6. `network.py` injects total outflow—implemented controlled release plus spill—into native downstream routing once.
7. The journals commit the action, physics and routing results before the next day can use them.

This is causal daily operation over a prepared natural-flow boundary. Weather is
not recomputed in response to the reservoir decision, and same-day downstream
flow is not returned to that day's agent.

## Configuration ownership

| File or section | Responsibility |
|---|---|
| Native HydroCNHS YAML | Full hydrology period, subbasins, GWLF/ABCD parameters and Lohmann routing |
| Weather CSV | Complete daily precipitation, temperature and PET for every weather-driven unit |
| `reservoir-physical-case.v1` | Reservoir physics, initial storage and operation-network connections |
| Coupled YAML `hydrology` | Model/forcing paths, zero-flow nodes and non-overlapping inlet bindings |
| Coupled YAML `agents` | Rule, general configured LLM, or optional preserved example method |
| Prompt/information/auditors | Operating instructions, causal fields and explicit diagnostics |

Changing only the operation method does not require hydrology recalibration. Use
`hydrology.prepared_from` to reuse verified boundaries when all hydrology inputs,
dates, bindings, code and runtime still match.

## Failure and recovery boundaries

An invalid response or retry does not advance reservoir physics. A committed day
contains the implemented outcome used by the next day. If execution stops,
`recovery.py` checks and reconstructs the saved prefix in a new output directory;
it never modifies the interrupted run.

Read [Weather and inflow inputs](WEATHER_INPUTS.md) for the binding contract and
the [F.E. Walter coupled example](../examples/fe_walter/coupled/README.md) for a
concrete configuration.
